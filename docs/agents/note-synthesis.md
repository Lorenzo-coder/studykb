# Writing module notes

Turn retrieved passages into study notes in the vault. The reader missed the
lecture and is catching up under time pressure, so the notes must be dense and
every claim must be checkable.

## Budget

- One lecture or one topic per pass. Never a whole module.
- At most **8 passages** per pass (`kb_search ... k=8`). If eight are not
  enough, the question is too broad — split it.
- Never read a PDF or a `90-extracted/` mirror. Ever.

## Procedure

1. `kb_outline <module>` once, to get the lecture list.
2. For each lecture topic: `kb_search "<topic>" module="<id>" k=8`.
3. If the topic is thin, one more search restricted to `type="transcript"` — the
   lecturer often says the thing the slide only names.
4. Write the file. Stop.

## Output

`vault/10-modules/<module>/<NN>-<slug>.md`

```markdown
# <Lecture topic>

> M8 · 2026-10-12 · Marco Corazza

## In one paragraph
<what this lecture is actually about, 3-5 sentences>

## Key points
- <claim> — [Schuld p.142]
- <claim> — [2026-10-12 @00:34:12]

## Worked through
<the derivation or the algorithm, only if the passages actually contain it>

## Open questions
- <what the passages did not answer>

## Sources
- [Schuld — Machine Learning with Quantum Computers p.142] provenance: text-layer
```

`## Worked through` is where the mathematics lives, in LaTeX: `$...$` inline and
`$$...$$` in display. The note is read rendered — `GET /read` serves the vault
with KaTeX — so a derivation that would be unreadable in a terminal belongs
here, in full, rather than being flattened into prose.

## Rules

- **Every claim carries its locator**, in brackets, inline. A sentence you
  cannot cite does not go in the notes.
- Never quote a formula from a passage marked `provenance=local-vlm`. That is a
  vision model describing a figure, not reading it. Write "see slide N" instead.
- Treat `asr`/`asr-corrected` wording as approximate. The timestamps are exact;
  the transcription of a technical term may not be.
- No filler. No "in this lecture we will see". No restating the heading.
- **The note has to stand on its own.** Whoever opens it did not read the chat
  that produced it. Nothing may be left implicit because it was said elsewhere.
- Put what the passages do not cover under **Open questions** rather than
  filling the gap from your own knowledge. The gap is the useful signal: it is
  what needs the recording, the book, or the lecturer.
