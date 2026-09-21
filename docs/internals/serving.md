# Serving

`src/studykb/server.py` · 96 lines

MCP tools plus a plain HTTP route. This is what makes the index worth building —
without it studykb would be an application that only talks to itself.

## The tools

| tool | returns |
|---|---|
| `kb_search(query, module, type, k)` | passages, each with citation and provenance |
| `kb_outline(module)` | a module's lecture-by-lecture outline, from the timetable |
| `kb_lecture(date)` | what was taught on a date: module, topic, teacher |
| `kb_sources()` | modules, teachers, and chunks indexed per module |

They are shaped so an agent can answer a question **without pulling a PDF into
its context**. That rule is the actual cost control, and it is written into
`CLAUDE.md`: reading a 700-page book to answer one question is the most
expensive mistake available here.

`kb_search`'s docstring tells the calling model that `provenance=local-vlm`
passages are descriptions of figures, not source text. The docstring is the only
place that instruction reaches a model calling the tool.

## HTTP alongside

```python
@mcp.custom_route("/search", methods=["GET"])
@mcp.custom_route("/healthz", methods=["GET"])
```

Same FastMCP app, so there is one process and one port. `/healthz` returns the
chunk count, which makes it a liveness check and a smoke test at once.

## Reading the vault

A terminal does not render LaTeX, and the notes are full of it. Three routes on
the same app turn the vault into a page:

| route | returns |
|---|---|
| `/read` | `viewer.html` — sidebar, filter, markdown rendered with KaTeX |
| `/read/list` | every `.md` under the vault, minus `90-extracted` |
| `/read/raw?p=<rel>` | one note, verbatim |

They live here rather than in a separate static server because this process
already holds `cfg.storage.vault` and already has the port. One process, one
port, no second thing to remember to start.

`server.vault_file()` is the trust boundary: `/read/raw` hands a query parameter
to the filesystem, so the path is resolved and rejected unless it stays inside
the vault and ends in `.md`. Binding to `127.0.0.1` is not the guard, it is the
reason a missing guard would go unnoticed. `tests/test_pipeline.py` covers it.

Markdown would eat the mathematics — `a_i … b_j` turns into italics, `\\`
disappears — so `viewer.html` pulls code and math out first, renders them, and
puts them back as placeholders once `marked` has run.

## The dialogue, on the page

`/chat` is a two-line protocol over one append-only file, `<vault>/.chat.jsonl`:
`POST` appends a message, `GET ?since=<n>` returns everything after the nth. The
page polls it; the agent running the study session tails the file and posts its
own replies back. Messages go through the viewer's markdown renderer, so an
answer carrying a derivation is as readable as a note.

**Both sides POST.** The container runs as root, so a file it creates is not
writable from the host — having the agent write through the route instead of
straight to the file removes that whole class of problem.

This is a bridge to a live session, not a service. Nothing answers when no agent
is tailing the file; the transcript simply stops.

## Lifetime

`build()` constructs the Qdrant client, the LLM client and the parsed calendar
**once**, at startup, and closes over them. Per-request construction would
re-read and re-parse the spreadsheet on every call.

## Running it

```bash
docker compose --profile serve up -d
claude mcp add --scope user --transport http studykb http://127.0.0.1:8077/mcp
```

User scope, not project scope: the tools are wanted from wherever you are
working, not only inside the repo.

The one-shot CLI service sits behind a `cli` profile so `compose up` does not
start a container that prints help and exits. `compose run` activates that
profile on its own.

## Status

Runs, and Claude Code connects. **Nothing validates the tools themselves** — a
tool could return wrong results and only a human would notice. See
[DELIVERY.md](../DELIVERY.md) step 4.2.

## Gate

```bash
curl -s localhost:8077/healthz     # {"ok":true,"chunks":N}
claude mcp list                    # studykb ✔ Connected
```
