"""studykb command line.

    uv run studykb doctor
    uv run studykb ingest --corpus qml-master [--dry-run] [--only vision]
    uv run studykb search "variational quantum circuit" --module M4
    uv run studykb serve
"""

from __future__ import annotations

import datetime as dt
import re
import shutil
from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

from . import index, metrics, pipeline, prompts, search as search_mod
from .config import load_config, load_corpus
from .limits import SOURCE_COLUMN_WIDTH, UNASSIGNED_LISTED, VANISHED_LISTED
from .llm import LLM

app = typer.Typer(add_completion=False, help="Config-driven knowledge base for study corpora.")
console = Console()

STAGES = ("ocr", "extract", "asr_cleanup", "vision", "embed")


def _hms(seconds: float) -> str:
    s = int(seconds)
    return f"{s // 3600}h{s % 3600 // 60:02d}m" if s >= 3600 else f"{s // 60}m{s % 60:02d}s" if s >= 60 else f"{s}s"


def _k(n: int) -> str:
    """Compact counts, so the cost table fits an 80-column terminal."""
    return f"{n/1e6:.1f}M" if n >= 1e6 else f"{n/1e3:.0f}k" if n >= 1000 else str(n)


def _cost_table(run) -> Table:
    """What the run actually cost, per stage.

    Wall time is the number that decides whether to start a run before lunch;
    the rest says where it went. `gpu` is whole-card draw while the stage ran,
    so it is an upper bound on this process's share.
    """
    t = Table(title="cost")
    for col, just in (("stage", "left"), ("time", "right"), ("sources", "right"),
                      ("items", "right"), ("per item", "right"), ("calls", "right"),
                      ("tokens in/out", "right"), ("Wh", "right"), ("peak W", "right")):
        t.add_column(col, justify=just)
    for m in run.stages:
        if not m.seconds:
            continue
        t.add_row(
            m.stage, _hms(m.seconds), str(m.sources), str(m.items),
            f"{m.per_item:.1f}s" if m.items else "—",
            str(m.llm_calls) or "—",
            f"{_k(m.tokens_in)}/{_k(m.tokens_out)}" if m.llm_calls else "—",
            f"{m.gpu_wh:.1f}" if m.gpu_wh else "—",
            f"{m.gpu_peak_w:.0f}" if m.gpu_peak_w else "—",
        )
    total = sum(m.seconds for m in run.stages)
    wh = sum(m.gpu_wh or 0 for m in run.stages)
    t.caption = f"run {run.run_id} · {_hms(total)} total" + (f" · {wh:.1f} Wh on the GPU" if wh else "")
    return t


def _ellipsis(text: str, width: int) -> str:
    """Keep the end of a path: the filename tells them apart, the folder does not."""
    return text if len(text) <= width else "…" + text[-(width - 1):]


def _load(corpus: str, config: Path | None, root: Path | None = None):
    """Load config + corpus, applying the corpus-level overrides."""
    cfg = load_config(config)
    corp = load_corpus(corpus)
    if root:
        corp.root = root
    if corp.collection:
        cfg.storage.collection = corp.collection
    if corp.vault:
        cfg.storage.vault = corp.vault
    # One state file per corpus. Sharing it makes two corpora lie to each other:
    # every source of corpus A looks "missing from disk" while ingesting B, and
    # B's empty collection makes the reconciliation guard wipe A's embed state.
    cfg.storage.state_db = cfg.storage.state_db.with_name(
        f"{cfg.storage.state_db.stem}-{corp.domain}{cfg.storage.state_db.suffix}"
    )
    return cfg, corp


@app.command()
def doctor(config: Path = typer.Option(None, "--config")) -> None:
    """Check everything ingest depends on, before a long run discovers it."""
    ok = True
    cfg = load_config(config)
    console.print(f"[bold]endpoint[/]  {cfg.llm_endpoint}")

    try:
        with LLM(cfg) as llm:
            available = llm.available_models()
        console.print(f"[green]✓[/] LLM endpoint reachable, {len(available)} models")
        for role, name in (
            ("embed", cfg.models.embed.name),
            ("vlm", cfg.models.vlm.name),
            ("vlm fallback", cfg.models.vlm.fallback),
            ("llm", cfg.models.llm.name),
        ):
            if not name:
                continue
            # ollama reports "qwen3:8b"; some backends drop the tag.
            hit = name in available or any(m.split(":")[0] == name.split(":")[0] for m in available)
            console.print(f"  {'[green]✓[/]' if hit else '[red]✗[/]'} {role}: {name}"
                          + ("" if hit else "   → ollama pull " + name))
            ok &= hit
    except Exception as exc:  # noqa: BLE001
        console.print(f"[red]✗[/] LLM endpoint unreachable: {exc}")
        ok = False

    try:
        client = index.connect(cfg)
        collections = {c.name for c in client.get_collections().collections}
        exists = cfg.storage.collection in collections
        console.print(
            f"[green]✓[/] Qdrant at {cfg.storage.qdrant_url}"
            + (f", collection '{cfg.storage.collection}' has {index.total(client, cfg)} chunks"
               if exists else f", collection '{cfg.storage.collection}' not created yet")
        )
    except Exception as exc:  # noqa: BLE001
        console.print(f"[red]✗[/] Qdrant unreachable at {cfg.storage.qdrant_url}: {exc}")
        ok = False

    ocr_bin = cfg.extract.ocr.cmd[0]
    if cfg.extract.ocr.enabled:
        found = shutil.which(ocr_bin)
        console.print(f"{'[green]✓[/]' if found else '[yellow]![/]'} {ocr_bin}"
                      + ("" if found else " missing (scanned PDFs will be skipped)"))

    for label, path in (("vault", cfg.storage.vault), ("state dir", cfg.storage.state_db.parent)):
        writable = path.exists() and path.is_dir()
        console.print(f"{'[green]✓[/]' if writable else '[red]✗[/]'} {label}: {path}")
        ok &= writable

    console.print(f"[green]✓[/] prompts: {len(list(prompts.PROMPT_DIR.glob('*.j2')))} templates")
    raise typer.Exit(0 if ok else 1)


@app.command()
def ingest(
    corpus: str = typer.Option(..., "--corpus", help="Domain name under corpora/, or a path to corpus.yaml"),
    config: Path = typer.Option(None, "--config"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Report what would run, write nothing"),
    only: list[str] = typer.Option(None, "--only", help=f"Run only these stages: {', '.join(STAGES)}"),
    root: Path = typer.Option(None, "--root", help="Override corpus.root (the manifest says /corpus, which only exists in the container)"),
) -> None:
    """Ingest a corpus. Incremental: unchanged sources cost nothing."""
    cfg, corp = _load(corpus, config, root)
    if bad := set(only or []) - set(STAGES):
        raise typer.BadParameter(f"unknown stage(s): {', '.join(sorted(bad))}")

    report = pipeline.ingest(
        cfg, corp, dry_run=dry_run, only=set(only) if only else None, log=console.print
    )

    table = Table(title="dry run — nothing written" if dry_run else "ingest")
    table.add_column("stage")
    table.add_column("sources" if dry_run else "processed", justify="right")
    for stage in STAGES:
        table.add_row(stage, str(report.stages.get(stage, 0)))
    console.print(table)
    if report.chunks:
        console.print(f"indexed [bold]{report.chunks}[/] chunks")
    if report.unassigned:
        console.print(f"\n[yellow]{len(report.unassigned)} sources with no module[/] "
                      f"— add them to {corp.manifest_dir / 'MANIFEST.md'}:")
        for rel in report.unassigned[:UNASSIGNED_LISTED]:
            console.print(f"  | {rel} |  |")
    if report.empty:
        console.print(f"\n[yellow]{len(report.empty)} sources produced no chunks[/] "
                      f"— they are indexed nowhere. Likely a PDF with no real text layer: "
                      f"check OCR, or set type: slides in MANIFEST.md to force captioning.")
        for rel in report.empty:
            console.print(f"  {rel}")
    if report.vanished:
        console.print(f"\n[yellow]{len(report.vanished)} known sources are missing from disk[/] "
                      f"(chunks kept; `studykb forget <path>` to drop them)")
        for rel in report.vanished[:VANISHED_LISTED]:
            console.print(f"  {rel}")
    for err in report.errors:
        console.print(f"[red]error[/] {err}")
    if report.run and any(m.seconds for m in report.run.stages):
        console.print()
        console.print(_cost_table(report.run))
        console.print("[dim]`studykb stats` compares this against previous runs.[/]")


@app.command()
def stats(
    corpus: str = typer.Option(..., "--corpus"),
    config: Path = typer.Option(None, "--config"),
    run: str = typer.Option(None, "--run", help="Break one run down by stage"),
    limit: int = typer.Option(10, "-n", help="How many runs to list"),
) -> None:
    """What past ingests cost: time, model calls, tokens, watt-hours."""
    from .state import State

    cfg, _ = _load(corpus, config)
    with State(cfg.storage.state_db) as st:
        if run:
            # Prefix match: the history table shortens the id to fit, so what
            # you can read is what you can paste.
            full = [r[0] for r in metrics.history(st.conn, 1000) if r[0].startswith(run)]
            if len(full) != 1:
                raise typer.BadParameter(
                    f"no run matching {run!r}" if not full
                    else f"{run!r} matches {len(full)} runs: {', '.join(full)}"
                )
            rows = metrics.stages_of(st.conn, full[0])
            run = full[0]
            t = Table(title=f"run {run}")
            for c, j in (("stage","left"),("time","right"),("src","right"),("items","right"),
                         ("calls","right"),("model","right"),("tok in/out","right"),
                         ("Wh","right"),("peak W","right"),("err","right")):
                t.add_column(c, justify=j, no_wrap=True)
            for (stage, sec, src, items, calls, msec, ti, to, wh, pw, err) in rows:
                if not sec:
                    continue          # a stage that never ran is not a measurement
                t.add_row(stage, _hms(sec), str(src), str(items), str(calls),
                          _hms(msec), f"{_k(ti)}/{_k(to)}",
                          f"{wh:.1f}" if wh else "—", f"{pw:.0f}" if pw else "—",
                          str(err) if err else "")
            console.print(t)
            return

        rows = metrics.history(st.conn, limit)
        if not rows:
            console.print("No runs recorded yet. They are written when `ingest` finishes.")
            return
        t = Table(title=f"last {len(rows)} runs · {corpus}")
        for c, j in (("run","left"),("when","left"),("time","right"),("items","right"),
                     ("calls","right"),("tok in/out","right"),("Wh","right"),("err","right")):
            t.add_column(c, justify=j, no_wrap=True)
        for (rid, _dom, started, sec, items, calls, ti, to, wh, _pw, err) in rows:
            t.add_row(rid, dt.datetime.fromtimestamp(started).strftime("%d/%m %H:%M"),
                      _hms(sec), _k(items), _k(calls), f"{_k(ti)}/{_k(to)}",
                      f"{wh:.1f}" if wh else "—", str(err) if err else "")
        console.print(t)
        console.print("[dim]`studykb stats --corpus <c> --run <id>` breaks one run down by stage.[/]")


@app.command()
def forget(
    source: str = typer.Argument(..., help="Source path, as reported by ingest"),
    corpus: str = typer.Option(..., "--corpus"),
    config: Path = typer.Option(None, "--config"),
) -> None:
    """Drop a source's chunks and its ingest state."""
    cfg, _ = _load(corpus, config)
    client = index.connect(cfg)
    index.drop_source(client, cfg, source)
    from .state import State

    with State(cfg.storage.state_db) as st:
        st.forget(source)
    console.print(f"dropped [bold]{source}[/]")


@app.command()
def figure(
    source: str = typer.Argument(..., help="Part of the source's name, case-insensitive; must match one PDF"),
    page: int = typer.Argument(..., help="PDF page, as in the citation: p.12 -> 12"),
    clip: str = typer.Option(None, "--clip", help="x0,y0,x1,y1 as fractions of the page, e.g. 0,0.2,0.6,0.9"),
    corpus: str = typer.Option(..., "--corpus"),
    root: Path = typer.Option(None, "--root"),
    config: Path = typer.Option(None, "--config"),
) -> None:
    """Cut a figure out of a source page into vault/assets/, for a note to embed.

    The page is rendered, not its images extracted: most figures in these PDFs
    are vector drawings, which have no embedded image to pull out.
    """
    import pymupdf

    cfg, corp = _load(corpus, config, root)
    pdfs = [str(f.relative_to(corp.root)) for f in corp.root.rglob("*.pdf")]
    found = search_mod.matching(pdfs, source)
    if len(found) != 1:
        raise typer.BadParameter(f"{len(found)} PDFs match: {found[:5]}", param_hint="SOURCE")
    rel = found[0]
    stem = re.sub(r"[^a-z0-9]+", "-", Path(rel).stem.lower())[:40].strip("-")
    out = cfg.storage.vault / "assets" / f"{stem}-p{page}{'-clip' if clip else ''}.png"
    out.parent.mkdir(parents=True, exist_ok=True)
    with pymupdf.open(corp.root / rel) as doc:
        pg = doc[page - 1]
        area = None
        if clip:
            x0, y0, x1, y1 = (float(v) for v in clip.split(","))
            r = pg.rect
            area = pymupdf.Rect(r.x0 + x0 * r.width, r.y0 + y0 * r.height, r.x0 + x1 * r.width, r.y0 + y1 * r.height)
        pg.get_pixmap(matrix=pymupdf.Matrix(2, 2), clip=area).save(out)
    console.print(f"{rel} p.{page} -> [bold]{out.relative_to(cfg.storage.vault)}[/]")


@app.command()
def search(
    query: str = typer.Argument(...),
    module: str = typer.Option(None, "--module", "-m"),
    type_: str = typer.Option(None, "--type", "-t"),
    source: str = typer.Option(None, "--source", "-s", help="Only files whose path contains this, case-insensitive"),
    authority: str = typer.Option(None, "--authority", "-a", help="reference (books, papers) or course"),
    k: int = typer.Option(None, "-k"),
    corpus: str = typer.Option(None, "--corpus", help="Needed only when the corpus has its own collection"),
    config: Path = typer.Option(None, "--config"),
) -> None:
    """Query the index from the shell."""
    cfg = _load(corpus, config)[0] if corpus else load_config(config)
    with LLM(cfg) as llm:
        try:
            hits = search_mod.search(index.connect(cfg), cfg, llm, query,
                                     module=module, type_=type_, source=source,
                                     authority=authority, k=k)
        except ValueError as e:
            raise typer.BadParameter(str(e), param_hint="--source") from e
    console.print(search_mod.format_hits(hits))


@app.command()
def review(
    corpus: str = typer.Option(..., "--corpus"),
    what: list[str] = typer.Option(None, "--what", help="summary, extraction, chunks, captions, retrieval; default all"),
    config: Path = typer.Option(None, "--config"),
    root: Path = typer.Option(None, "--root"),
    out: Path = typer.Option(None, "--out", help="Where to write the reports (default: <vault>/95-review)"),
) -> None:
    """Write reports for a human to check before the index is trusted."""
    from . import review as review_mod

    cfg, corp = _load(corpus, config, root)
    # Inside the vault, so Obsidian renders them — captions.md is only useful
    # when the page images next to it actually display.
    paths = out or cfg.storage.vault / "95-review"
    paths.mkdir(parents=True, exist_ok=True)
    wanted = set(what) if what else {"summary", "extraction", "chunks", "captions", "retrieval"}

    if "summary" in wanted:
        rows, checks = review_mod.summary(cfg, corp)
        table = Table(title=f"corpus: {corp.domain}")
        # Source titles here run past 90 characters. Only that column is
        # clamped; clamping the rest shreds the numbers instead.
        table.add_column("source", no_wrap=True, width=SOURCE_COLUMN_WIDTH)
        for i, col in enumerate(review_mod.SUMMARY_COLUMNS[1:], start=1):
            table.add_column(col, justify="right" if i >= 3 else "left")
        for row in rows:
            table.add_row(_ellipsis(row[0], SOURCE_COLUMN_WIDTH), *row[1:])
        console.print(table)
        for c in checks:
            console.print(f"{c.mark} [bold]{c.name}[/] — {c.detail}")
        console.print(f"[green]✓[/] {review_mod.summary_report(cfg, corp, paths)}")

    if "extraction" in wanted:
        console.print(f"[green]✓[/] {review_mod.extraction_report(cfg, corp, paths)}")
    if "chunks" in wanted:
        console.print(f"[green]✓[/] {review_mod.chunks_report(cfg, corp, paths)}")
    if "captions" in wanted:
        console.print(f"[green]✓[/] {review_mod.caption_report(cfg, corp, paths)}")
    if "retrieval" in wanted:
        queries = corp.manifest_dir / "queries.yaml"
        if queries.exists():
            console.print(f"[green]✓[/] {review_mod.retrieval_report(cfg, corp, paths, queries)}")
        else:
            console.print(f"[yellow]![/] no {queries} — skipping retrieval review")


@app.command()
def serve(
    corpus: str = typer.Option(..., "--corpus"),
    config: Path = typer.Option(None, "--config"),
    host: str = typer.Option("0.0.0.0", "--host"),
    port: int = typer.Option(8077, "--port"),
) -> None:
    """Run the MCP + HTTP server."""
    from .server import run

    run(*_load(corpus, config), host=host, port=port)


if __name__ == "__main__":
    app()
