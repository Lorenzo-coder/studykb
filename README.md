# studykb

A knowledge base for a study corpus. It ingests books, slides, papers and
lecture transcripts, indexes them with local models, and serves them over MCP so
an assistant can answer from the material — with a citation on every passage
pointing at a page number or a timestamp in the recording.

Built for one master's degree, but it knows nothing about that subject: what to
index lives in `corpora/<domain>/corpus.yaml`, how to index lives in
`config/default.yaml`. Point it at a different manifest and it indexes a
different subject, with no code change.

## Why the citations matter

Retrieval that cannot tell you *where* something came from is a plausible-sounding
paraphrase generator. Every chunk here carries a `locator` (`p.142`,
`@00:34:12`) and a `provenance`, so a generated note can be checked against the
page or the minute of the lecture it claims to summarise.

`provenance` is not decoration:

| value | meaning |
|---|---|
| `text-layer` | read from the file |
| `ocr` | tesseract on a scan — verify anything exact |
| `local-vlm` | a **description of a figure** by a 7B vision model, not a transcription |
| `asr` / `asr-corrected` | lecture captions, the second pass repaired with a glossary |

A 7B vision model does not reliably read a quantum circuit or a dense
derivation. Its captions make a slide *findable*; they are never a source.

## Setup

Requires: Docker with the Compose **v2** plugin, and [ollama](https://ollama.com)
on the host with a GPU.

```bash
cp .env.example .env          # set CORPUS_DIR and VAULT_DIR

ollama pull bge-m3 qwen2.5vl:7b granite3.2-vision:2b qwen3:8b

docker compose up -d qdrant
docker compose run --rm studykb doctor
docker compose run --rm studykb ingest --corpus qml-master --dry-run
docker compose run --rm studykb ingest --corpus qml-master
```

### ollama settings

On an 8 GB card these are the difference between a usable context and a cramped
one. In `/etc/systemd/system/ollama.service.d/override.conf`:

```ini
[Service]
Environment="OLLAMA_FLASH_ATTENTION=1"
Environment="OLLAMA_KV_CACHE_TYPE=q8_0"
Environment="OLLAMA_MAX_LOADED_MODELS=1"
```

`MAX_LOADED_MODELS=1` matters most: ingest runs stage by stage precisely because
the embedder, the vision model and the text model cannot share 8 GB, and without
this ollama will try anyway.

### Serving

```bash
docker compose --profile serve up -d
```

Then register it with Claude Code:

```bash
claude mcp add --transport http studykb http://127.0.0.1:8077/mcp
```

Tools: `kb_search`, `kb_outline`, `kb_lecture`, `kb_sources`.

## Using it

[docs/HOWTO.md](docs/HOWTO.md) is the step-by-step guide: what to run, what you
should see, and what to do when you see something else.

## Development

```bash
uv sync
uv run pytest
uv run studykb --help
```

uv only — never pip, including in the Dockerfile.

## What is deliberately not here

- **A reranker.** Hybrid search covers most of the benefit at no cost. Add one
  when a concrete query is found to fail, not before.
- **A provider abstraction.** ollama, LM Studio and the hosted APIs all speak
  OpenAI-compatible HTTP; switching is a URL in config.
- **A database for notes.** Notes are markdown in the vault, already readable by
  Obsidian and by grep.
- **A web UI.** `GET /search` and the MCP tools are the interface.
