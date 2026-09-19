# Review

`src/studykb/review.py` · 462 lines

Reports for a human to check **before the index is trusted**.

Three things go wrong in this pipeline and none of them raise an error:
extraction drops a page, a caption describes a figure that is not there, and
retrieval returns something plausible from the wrong source. A run that reports
success looks identical in all three cases.

## SUMMARY.md — the one screen

```bash
uv run studykb review --corpus <name>
```

Five checks. **Each one exists because this pipeline actually produced that
failure while reporting success:**

| check | the failure it catches |
|---|---|
| every source is indexed | the 137-page deck that extracted to nothing and was searchable nowhere |
| nothing was lost on the way in | 488 chunks produced against 478 stored — what a caption overwriting a page's text looks like from outside |
| no page with text was dropped | a page whose text never reached a chunk |
| chunks are worth indexing | title pages and part dividers each occupying a vector |
| captions carry content | the graphics floor letting covers and blanks through |

Then a row per source: type, module, pages as **with-text/total**, characters per
page, captions, and chunks as **indexed/produced** when the two differ.

`0/137` in the pages column is a document that extracted to nothing. Two numbers
in the chunks column mean something was lost between producing and storing.

## The other four

| file | answers | shape |
|---|---|---|
| `extraction.md` | did a page lose its text? | a row per page with the start of it |
| `chunks.md` | where does one chunk end and the next begin? | each chunk's opening and closing words |
| `captions.md` | is a caption describing something that is not there? | each page image with the model's claim under it |
| `retrieval.md` | does search return the right passage? | queries from `queries.yaml` with locators to open |

`extraction.md` and `chunks.md` are **references, not documents to read end to
end** — a row per page and per chunk, running to megabytes. Open them when
SUMMARY points at a source.

## Design decisions worth knowing

**`captions.md` renders the pages itself**, into `review/pages/`, rather than
relying on the ingest run having kept them. Rendering is seconds of CPU and it
works on captions generated at any time. Filenames are slugged to `p0023.png`
because source titles contain spaces and braces that break image links
everywhere except Obsidian.

**`chunks.md` shows seams, not text.** The text is already in `extraction.md`;
what you cannot see anywhere else is where a cut landed. A full dump of 488
chunks would be unreadable.

**Absences are explained.** `_why_no_captions` names why a source produced none —
captioning off for prose, no page above the graphics floor, vision not run yet.
Omitting a source silently reads as "it was not processed", which is exactly how
a correctly-excluded book came to look broken.

**`expect` in `queries.yaml` is a prompt to look, not a pass/fail.** Retrieval
that surfaces a better source than the one you guessed is not a failure.

## Reading order

1. `SUMMARY.md`. If all five are ✅, the data is intact — stop here.
2. Otherwise, go to the file that answers the failing check.
3. Before trusting any generated note, spot-check three locators from
   `retrieval.md` by opening them.
