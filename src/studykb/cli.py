"""studykb command line.

    uv run studykb doctor
    uv run studykb ingest --corpus qml-master [--dry-run] [--only vision]
    uv run studykb search "variational quantum circuit" --module M4
    uv run studykb serve
"""

from __future__ import annotations

import shutil
from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

from . import index, pipeline, search as search_mod
from .config import load_config, load_corpus
from .llm import LLM
from .prompts import Prompts

app = typer.Typer(add_completion=False, help="Config-driven knowledge base for study corpora.")
console = Console()

STAGES = ("ocr", "extract", "asr_cleanup", "vision", "embed")


def _load(corpus: str, config: Path | None, root: Path | None = None):
    """Load config + corpus, applying the corpus-level overrides."""
    cfg = load_config(config)
    corp = load_corpus(corpus)
    if root:
        corp.root = root
    if corp.collection:
        cfg.storage.collection = corp.collection
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

    console.print(f"[green]✓[/] prompts: {len(list(Prompts().dir.glob('*.j2')))} templates")
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
        for rel in report.unassigned[:20]:
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
        for rel in report.vanished[:10]:
            console.print(f"  {rel}")
    for err in report.errors:
        console.print(f"[red]error[/] {err}")


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
def search(
    query: str = typer.Argument(...),
    module: str = typer.Option(None, "--module", "-m"),
    type_: str = typer.Option(None, "--type", "-t"),
    k: int = typer.Option(None, "-k"),
    corpus: str = typer.Option(None, "--corpus", help="Needed only when the corpus has its own collection"),
    config: Path = typer.Option(None, "--config"),
) -> None:
    """Query the index from the shell."""
    cfg = _load(corpus, config)[0] if corpus else load_config(config)
    with LLM(cfg) as llm:
        hits = search_mod.search(index.connect(cfg), cfg, llm, query, module=module, type_=type_, k=k)
    console.print(search_mod.format_hits(hits))


@app.command()
def review(
    corpus: str = typer.Option(..., "--corpus"),
    what: list[str] = typer.Option(None, "--what", help="extraction, captions, retrieval; default all"),
    config: Path = typer.Option(None, "--config"),
    root: Path = typer.Option(None, "--root"),
    out: Path = typer.Option(None, "--out", help="Where to write the reports (default: <corpus root>/review)"),
) -> None:
    """Write reports for a human to check before the index is trusted."""
    from . import review as review_mod

    cfg, corp = _load(corpus, config, root)
    paths = review_mod.ReviewPaths(out or corp.root / "review")
    wanted = set(what) if what else {"extraction", "captions", "retrieval"}

    table = Table(title=f"corpus: {corp.domain}")
    for col, just in (("source", "left"), ("type", "left"), ("module", "left"), ("chunks", "right")):
        table.add_column(col, justify=just)
    for rel, type_, module, n in review_mod.inventory(cfg, corp):
        table.add_row(rel[:60], type_, module or "—", str(n) if n else "[red]0[/]")
    console.print(table)

    if "extraction" in wanted:
        console.print(f"[green]✓[/] {review_mod.extraction_report(cfg, corp, paths)}")
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
