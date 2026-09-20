# Extraction (document intelligence)

`src/studykb/extract/` — `pdf.py`, `pptx.py`, `vtt.py`, `ocr.py`

Turns a file into a list of [units](../glossary.md#unit): one page, one slide,
one five-minute transcript window. `extract_units(path, cfg)` dispatches on the
file extension.

The one thing every extractor must get right is the **locator**. Everything
downstream inherits it, and a wrong one makes every citation built on it a lie.

## PDF — `pdf.py`

```python
pages = pymupdf4llm.to_markdown(path, page_chunks=True)
```

`page_chunks=True` is what keeps page boundaries, so the page number becomes the
locator. Formulas survive as approximate text: good enough to *find* the
passage, not meant for reading the maths — that is what opening the page is for.

Two things in this file exist because of specific failures.

### `text_layer_stats` — does this PDF actually have text?

Naively: characters divided by pages. That was wrong on real material.

A 137-page deck flattened to vector art by iLovePDF still carried an identical
copyright footer on every page — 210 characters each. Counted naively it looked
like a document with a text layer, so it skipped OCR, extracted to nothing, and
was indexed as nothing, all while the run reported success.

So the function subtracts **boilerplate** first: any line appearing on at least
`_BOILERPLATE_SHARE` (60%) of pages is furniture — a running header, a page
number, a copyright footer, a watermark. What is left is real text.

```python
seen = Counter(line for lines in per_page for line in set(lines))
boilerplate = {line for line, n in seen.items() if n >= max(2, pages * 0.6)}
```

`ponytail:` it matches lines exactly, so a footer containing a page number is
not caught. Normalise digits here if that shows up.

### `_graphics_per_page` — is there anything to look at?

```python
len(page.get_images()) + len(page.get_drawings())
```

`get_drawings()` matters as much as `get_images()`: decks flattened to vectors
carry every diagram as vector art and report **zero** images. Counting only
bitmaps meant those pages were never sent for captioning.

The count, not just a boolean, is stored on the unit — a cover has about one, a
blank page none, a real figure page dozens. [enrichment.md](enrichment.md)
explains what the number is used for.

## PPTX — `pptx.py`

One unit per slide. **Speaker notes are included**: in lecture decks they often
carry the sentence the slide only gestures at.

No graphics count here: captioning only handles PDFs, so a slide's pictures are
never counted.

## Captions — `vtt.py`

Captions are grouped into windows of `transcript.window_seconds` (default 300),
and the window's start time becomes the locator: `@00:34:12`.

Consecutive identical lines are dropped. Rolling captions repeat the previous
line as they scroll, and keeping the duplicates would multiply the token count
for no extra information.

Both `.vtt` and `.srt` are handled; `_seconds` accepts `,` or `.` as the decimal
separator because SRT uses one and WebVTT the other.

## OCR — `ocr.py`

Runs only when `needs_ocr` says so:

```python
pages, mean_chars = text_layer_stats(path)
return pages > 0 and mean_chars < cfg.extract.ocr.trigger_chars_per_page   # 120
```

Measured, never guessed from the filename or the metadata.

`run_ocr` writes a **copy** under the state directory and leaves the original
untouched:

- the corpus is mounted read-only in the container;
- some of this material exists in one copy only, and a pipeline that rewrites
  originals in place is one bad run away from losing a book;
- it writes to `.partial.pdf` and then `rename`s, so a killed run never leaves a
  half-written file behind.

Exit code 6 is treated as success: with `--skip-text` it means "this already has
text", which is the outcome we want.

Downstream stages read `Source.readable`, which is the OCR'd copy when one
exists and the original otherwise.

## Status

The PDF, PPTX and VTT paths run against real material. **The OCR path has never
run end to end** — no source in the corpus has needed it. See
[DELIVERY.md](../DELIVERY.md) step 2.3.

## Gate

```bash
uv run studykb review --corpus <name> --what summary --what extraction
```

In `SUMMARY.md` the `pages` column reads with-text/total. `0/137` is a document
that extracted to nothing. Then open `extraction.md` for the source in question:
one row per page, with the start of the text.
