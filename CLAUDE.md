# studykb

Config-driven knowledge base for study corpora. Ingests books, slides, papers
and lecture transcripts; serves them over MCP with a citation on every passage.

## The rule that matters

**Never read a source file into your context.** No PDFs, no `.vtt`, and not the
mirrors under `vault/90-extracted/`. Call `kb_search` and work from the passages
it returns — they already carry their citation. Reading a 700-page book to
answer one question is the single most expensive mistake available here.

Same for the corpus: don't `ls` it to "see what's there". `kb_sources` answers
that in one call.

## Commands

```bash
uv run studykb doctor                              # check endpoint, models, Qdrant, paths
uv run studykb ingest --corpus qml-master --dry-run
uv run studykb ingest --corpus qml-master          # incremental; unchanged sources cost nothing
uv run studykb ingest --corpus qml-master --only vision
uv run studykb search "variational circuit" -m M4
uv run pytest
```

uv only. Never pip, in the shell or in the Dockerfile.

## Where things are

| what | where |
|---|---|
| how to index (models, thresholds) | `config/default.yaml` |
| what to index (globs, modules) | `corpora/<domain>/corpus.yaml` |
| manual file→module overrides | `corpora/<domain>/MANIFEST.md` |
| prompts sent to models | `prompts/*.j2` |
| your notes, syllabus, extractions | the vault, outside this repo |

Changing behaviour means editing config or a prompt. If a corpus-specific fact
is about to go into `src/`, it belongs in `corpus.yaml` instead.

## Reading a result

Every passage carries a `provenance`:

- `text-layer` — read from the file.
- `ocr` — tesseract on a scan. Verify anything exact.
- `local-vlm` — a **description of a figure** written by a 7B vision model. It
  is not a transcription. Never quote a formula or circuit from it; cite it as a
  description and open the page.
- `asr` / `asr-corrected` — lecture captions, the second pass repaired with a
  glossary. The course is taught in non-native English; treat exact wording as
  approximate and timestamps as reliable.

`p.149` is the **PDF page**, the number you type into a viewer — not the number
printed on the paper. In a book with front matter the two differ by a dozen
pages. Cite the PDF page; it is the one that opens the right screen.

## Agent playbooks

`docs/agents/` — pick by task: `ingest-runbook.md` (operating a run),
`tagging.md` (assigning modules), `note-synthesis.md` (writing module notes),
`thesis-research.md` (thesis work).
