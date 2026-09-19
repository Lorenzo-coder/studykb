"""MCP server (plus a plain HTTP search route).

This is the interface that makes the index worth building: without it studykb
would be an app that only talks to itself. The tools are shaped so an agent can
answer a question without ever pulling a PDF into its context — it gets the
passages it needs, each already carrying its citation.
"""

from __future__ import annotations

from fastmcp import FastMCP
from starlette.requests import Request
from starlette.responses import JSONResponse

from . import calendar as cal
from . import index, pipeline, search as search_mod
from .config import Config, Corpus
from .llm import LLM


def build(cfg: Config, corpus: Corpus) -> FastMCP:
    mcp = FastMCP("studykb")
    client = index.connect(cfg)
    llm = LLM(cfg)
    modules = pipeline._load_calendar(cfg, corpus, log=lambda *_: None)
    by_id = {m.id: m for m in modules}

    @mcp.tool
    def kb_search(query: str, module: str | None = None, type: str | None = None, k: int = 8) -> str:
        """Search the study corpus.

        Returns passages with a citation and a provenance marker. `module` is an
        id like "M8"; `type` is one of book, slides, paper, transcript, caption.

        Passages marked `provenance=local-vlm` are descriptions of a figure
        produced by a local vision model, not source text: cite them as
        descriptions and open the page for anything that must be exact.
        """
        hits = search_mod.search(client, cfg, llm, query, module=module, type_=type, k=k)
        return search_mod.format_hits(hits)

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
            module=params.get("module"), type_=params.get("type"),
            k=int(params.get("k", cfg.retrieval.k_final)),
        )
        return JSONResponse([h.__dict__ for h in hits])

    @mcp.custom_route("/healthz", methods=["GET"])
    async def healthz(_: Request) -> JSONResponse:
        return JSONResponse({"ok": True, "chunks": index.total(client, cfg)})

    return mcp


def run(cfg: Config, corpus: Corpus, *, host: str = "0.0.0.0", port: int = 8077,
        transport: str = "http") -> None:
    build(cfg, corpus).run(transport=transport, host=host, port=port)
