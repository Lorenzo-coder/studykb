"""MCP server (plus a plain HTTP search route).

This is the interface that makes the index worth building: without it studykb
would be an app that only talks to itself. The tools are shaped so an agent can
answer a question without ever pulling a PDF into its context — it gets the
passages it needs, each already carrying its citation.
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from fastmcp import FastMCP
from starlette.requests import Request
from starlette.responses import FileResponse, HTMLResponse, JSONResponse, PlainTextResponse

from . import calendar as cal
from . import index, pipeline, search as search_mod
from .config import Config, Corpus
from .llm import LLM

# The extraction mirrors are 32 MB of raw text: worth indexing, not worth reading.
VAULT_SKIP = {"90-extracted"}


def vault_file(root: Path, rel: str, suffixes: tuple[str, ...] = (".md",)) -> Path | None:
    """A vault note by its relative path, or None if the path does not earn one.

    The reading routes hand a query parameter to the filesystem, so this is the
    trust boundary. It stays even though the server binds to 127.0.0.1.
    """
    root = root.resolve()
    path = (root / rel).resolve()
    if not path.is_relative_to(root) or path.suffix not in suffixes or not path.is_file():
        return None
    return path


def build(cfg: Config, corpus: Corpus) -> FastMCP:
    mcp = FastMCP("studykb")
    client = index.connect(cfg)
    llm = LLM(cfg)
    modules = pipeline._load_calendar(cfg, corpus, log=lambda *_: None)
    by_id = {m.id: m for m in modules}

    @mcp.tool
    def kb_search(
        query: str, module: str | None = None, type: str | None = None,
        source: str | None = None, authority: str | None = None, k: int = 8,
    ) -> str:
        """Search the study corpus.

        Returns passages with a citation and a provenance marker. `module` is an
        id like "M8"; `type` is one of book, slides, paper, transcript, caption;
        `source` keeps only files whose path contains it, case-insensitive
        ("Business Cases", "exercise3"); `authority` is "reference" (books,
        papers) or "course" (slides, transcripts, lecture code).

        Passages marked `provenance=local-vlm` are descriptions of a figure
        produced by a local vision model, not source text: cite them as
        descriptions and open the page for anything that must be exact.
        """
        try:
            hits = search_mod.search(client, cfg, llm, query, module=module, type_=type, source=source,
                                     authority=authority, k=k)
        except ValueError as e:
            return str(e)
        return search_mod.format_hits(hits)

    @mcp.tool
    def kb_crosscheck(topic: str, module: str | None = None, k: int = 4) -> str:
        """Was a topic taught in the course, and what do books and papers say?

        Runs the search twice, once on course material and once on reference
        material, and returns both labelled. Use it to tell what is on the
        exam from what only the literature covers.
        """
        return search_mod.crosscheck(client, cfg, llm, topic, module=module, k=k)

    @mcp.tool
    def kb_outline(module: str) -> str:
        """Lecture-by-lecture outline of a module, from the course timetable."""
        mod = by_id.get(module.upper())
        if not mod:
            return f"Unknown module {module}. Known: {', '.join(by_id) or 'none — no calendar loaded'}"
        return cal.to_markdown([mod])[mod.id]

    @mcp.tool
    def kb_lecture(date: str) -> str:
        """What was taught on a date (YYYY-MM-DD): module, topic and teacher."""
        rows = [
            f"{lec.module} · {lec.time} · {lec.topic} — {lec.teacher} ({lec.mode})"
            for m in modules
            for lec in m.lectures
            if lec.date and lec.date.isoformat() == date
        ]
        return "\n".join(rows) if rows else f"No lecture on {date}."

    @mcp.tool
    def kb_sources() -> str:
        """Modules, their teachers, and how many chunks each has indexed."""
        counts = index.counts_by(client, cfg, "module", list(by_id)) if by_id else {}
        lines = [f"corpus: {corpus.domain} — {corpus.title}", ""]
        for mod in modules:
            start, end = mod.date_range
            lines.append(
                f"{mod.id:4} {counts.get(mod.id, 0):6} chunks  {start} → {end}  {mod.title}"
                f"  [{', '.join(mod.teachers)}]"
            )
        lines += ["", f"total indexed: {index.total(client, cfg)} chunks"]
        return "\n".join(lines)

    @mcp.custom_route("/search", methods=["GET"])
    async def http_search(request: Request) -> JSONResponse:
        params = request.query_params
        if not (query := params.get("q")):
            return JSONResponse({"error": "missing ?q="}, status_code=400)
        hits = search_mod.search(
            client, cfg, llm, query,
            module=params.get("module"), type_=params.get("type"), source=params.get("source"),
            authority=params.get("authority"), k=int(params.get("k", cfg.retrieval.k_final)),
        )
        return JSONResponse([h.__dict__ for h in hits])

    @mcp.custom_route("/healthz", methods=["GET"])
    async def healthz(_: Request) -> JSONResponse:
        return JSONResponse({"ok": True, "chunks": index.total(client, cfg)})

    @mcp.custom_route("/read", methods=["GET"])
    async def read_ui(_: Request) -> HTMLResponse:
        return HTMLResponse((Path(__file__).parent / "viewer.html").read_text())

    @mcp.custom_route("/read/list", methods=["GET"])
    async def read_list(_: Request) -> JSONResponse:
        root = cfg.storage.vault
        rels = (p.relative_to(root) for p in root.rglob("*.md"))
        return JSONResponse(sorted(str(r) for r in rels if not set(r.parts) & VAULT_SKIP))

    @mcp.custom_route("/read/raw", methods=["GET"])
    async def read_raw(request: Request) -> PlainTextResponse:
        path = vault_file(cfg.storage.vault, request.query_params.get("p", ""))
        if path is None:
            return PlainTextResponse("not found", status_code=404)
        return PlainTextResponse(path.read_text())

    @mcp.custom_route("/read/asset", methods=["GET"])
    async def read_asset(request: Request):
        """A figure a note embeds: a page cut from a source by `studykb figure`."""
        path = vault_file(cfg.storage.vault, request.query_params.get("p", ""), (".png",))
        if path is None:
            return PlainTextResponse("not found", status_code=404)
        return FileResponse(path)

    @mcp.custom_route("/chat", methods=["GET", "POST"])
    async def chat(request: Request) -> JSONResponse:
        """The dialogue, so it can happen on the page instead of in a terminal.

        Append-only. The page POSTs what the reader types; the agent driving the
        session appends its own lines straight to the file and tails it.
        """
        log = cfg.storage.vault / ".chat.jsonl"
        if request.method == "POST":
            text = (await request.body()).decode("utf-8", "replace")[:8000].strip()
            if not text:
                return JSONResponse({"error": "empty"}, status_code=400)
            # Both sides POST: the container owns the file, so nothing on the host
            # needs write permission on it.
            who = "claude" if request.query_params.get("who") == "claude" else "you"
            entry = {"t": datetime.now().isoformat(timespec="seconds"), "who": who, "text": text}
            with log.open("a") as fh:
                fh.write(json.dumps(entry, ensure_ascii=False) + "\n")
            return JSONResponse({"ok": True})
        raw = request.query_params.get("since", "0")
        since = int(raw) if raw.isdigit() else 0
        lines = log.read_text().splitlines() if log.exists() else []
        return JSONResponse([json.loads(line) for line in lines[since:] if line.strip()])

    return mcp


def run(cfg: Config, corpus: Corpus, *, host: str = "0.0.0.0", port: int = 8077,
        transport: str = "http") -> None:
    build(cfg, corpus).run(transport=transport, host=host, port=port)
