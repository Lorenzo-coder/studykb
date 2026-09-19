# Glossary

Eight terms carry the whole design. They appear in every subsystem document and
in most of the code.

---

### Corpus

A body of study material plus the rules for reading it: `corpora/<domain>/`.
Two files, both data, never code:

- `corpus.yaml` — where the sources are (globs), what type each one is, how
  files map to modules, an optional timetable, a glossary of terms, and the
  names of the resources this corpus owns (its Qdrant collection, its vault).
- `MANIFEST.md` — hand-written overrides for the files the rules cannot place,
  and the switch for sources that should stay out.

**Swapping the corpus is what makes studykb reusable.** Nothing in `src/` knows
what a quantum computer is. A corpus owns its collection, its vault and its
state file, so two corpora cannot damage each other — a lesson learned the hard
way, see [state.md](internals/state.md).

---

### Source

One file in the corpus: a book, a deck, a paper, a caption file. Identified
everywhere by `rel` — its path relative to the corpus root. That string is the
stable key: it appears in the state database, in every chunk payload, and in
every report.

A source has a `type` (`book`, `slides`, `paper`, `transcript`) which decides
how it is read and whether it is captioned.

---

### Unit

One page, one slide, or one five-minute window of a transcript. The output of
extraction, the input to chunking. Defined in `types.py`.

A unit is *not* what gets indexed. It is the natural division of the document
itself, which is why it carries the locator.

---

### Chunk

What search returns, and the only thing that is embedded. Produced from units by
`chunk.py`.

`chunk.target_tokens` is a **ceiling, not a target**: a unit shorter than it is
kept whole. Ordinary book pages are well under that ceiling, so in practice one
chunk is one page — which is why every locator points at exactly one page.
Transcript windows and captions are never split at all.

---

### Locator

Where the passage physically is: `p.142`, `slide 7`, `@00:34:12`.

This is the feature that justifies the whole project. Retrieval that cannot tell
you *where* something came from is a plausible-sounding paraphrase generator; a
locator can be opened and checked. Every generated note is built on locators, so
a wrong one silently poisons everything downstream.

`p.142` is the **PDF page** — the number you type into a viewer — not the number
printed on the paper. In a book with front matter the two differ by a dozen
pages.

---

### Provenance

How the text came to exist. Carried on every chunk, and not decoration:

| value | meaning | how much to trust it |
|---|---|---|
| `text-layer` | read from the file | it is the document |
| `ocr` | tesseract on a scan | verify anything exact |
| `local-vlm` | a 7B vision model **describing a figure** | a description, never a transcription. Never quote a formula from it |
| `asr` | automatic lecture captions | wording approximate, timestamps exact |
| `asr-corrected` | captions repaired by a local model against a glossary | same, plus the model may have invented terminology |

The system generates text as well as reading it. Provenance is what keeps the
difference visible after the two are sitting side by side in the same index.

---

### Stage

One step of ingestion: `ocr`, `extract`, `asr_cleanup`, `vision`, `embed`.

Stages run **across all sources**, not source by source. The embedder, the
vision model and the text model cannot fit in 8 GB of VRAM together, so each
model loads once per run rather than once per file, and the previous one is
evicted before the next stage starts.

---

### Fingerprint

A hash of everything a stage consumes, and the thing that decides whether the
stage runs again.

`state.db` records, per `(source, stage)`, the source checksum and the
fingerprint. A stage reruns only when one of the two changed. A stage's
fingerprint also folds in the fingerprints of the stages **upstream** of it, so
re-captioning a deck reindexes it — without that, new captions sat in a file the
embed stage never read again while the run reported success.

Config changes invalidate a stage automatically. **Code changes do not**: there
are manual version constants in `config.py::fingerprint` to bump when extraction
or OCR logic changes.
