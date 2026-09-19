# Chunking

`src/studykb/chunk.py` · 86 lines

Units become [chunks](../glossary.md#chunk) — the only thing that gets embedded,
and the only thing search returns.

## The behaviour that surprises people

`chunk.target_tokens` is a **ceiling, not a target**:

```python
if len(text) <= target:
    return [text]
```

The default ceiling is 800 tokens ≈ 3,200 characters. A book page averages about
1,475. So on ordinary pages the splitter never fires: **one chunk is one page**.
On the test corpus, 398 of 403 book chunks were never split.

This is worth understanding rather than treating as a bug:

- **good** — every locator points at exactly one page, so every citation can be
  opened and checked;
- **cost** — chunks carry less context than the ceiling suggests, and a concept
  spanning a page break is cut with no overlap, because overlap only applies
  *within* a unit.

To actually get larger chunks you would have to merge consecutive pages, which
means locators become ranges (`p.13–15`) and lose that precision. For a study
knowledge base, precision wins.

## Splitting, when it does fire

Paragraph-aware and heading-aware, no semantic segmentation model:

1. split on markdown headings (`_HEADING`) when `split_on: headings`;
2. split those on blank lines;
3. accumulate paragraphs until the next would cross the ceiling, then emit and
   carry `overlap_tokens` of tail into the next chunk;
4. a single paragraph longer than 1.5× the ceiling — a dense page with no blank
   lines — is cut anyway, or one chunk would swallow the page.

Token counts are estimated at `CHARS_PER_TOKEN = 4`. A real tokenizer would add
a dependency and a model download to place a boundary marginally better.

## What is never split

```python
parts = [text] if type_ in ("transcript", "caption") else _split(text, cfg)
```

- **transcript windows** are already the right size, and splitting one would
  sever the timestamp from part of its own text;
- **captions** are single descriptions of single pages.

## Chunk ids

```python
chunk_id(source, locator, index, kind)
```

Deterministic (`uuid5`), so re-indexing a source overwrites its previous chunks
instead of duplicating them.

`kind` is part of the key and **has to be**. A page's caption shares a source, a
locator and an index with the page's own text — without `kind`, the caption
upsert replaced the text it was meant to complement. Ten slides kept the vision
model's description and lost what was actually printed on them, and the only
visible symptom was an ingest reporting 488 chunks against 478 in the
collection.

That symptom is now check number two in [review.md](review.md).

## Gate

```bash
uv run studykb review --corpus <name> --what chunks
```

`chunks.md` shows each chunk's opening and closing words. Scan the pairs for
cuts landing mid-derivation. The per-source header states the median size, how
many chunks fell below the ceiling, and how many are too small to ever be a
useful hit.
