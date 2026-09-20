# Assigning sources to modules

`ingest` lists files it could not place. Your job is to turn that list into rows
for `corpora/<domain>/MANIFEST.md`.

## Input

Use only:
- the unassigned file paths, as printed;
- `kb_outline <module>` or the module table in `MANIFEST.md`.

Do not open the files. A filename plus the module list is enough, and when it
isn't, the answer is "unknown", not a guess from reading 300 pages.

## Output

Markdown table rows, nothing else:

```
| books/Schuld - Machine Learning with Quantum Computers.pdf | M7 |  |
| slides/2026-09-19-annealing.pdf | M7 |  |
| code/tutorialGrover.ipynb | M4 |  |
```

- Column 2: a module id (`M1`–`M9`), or empty if you cannot tell.
- Column 3: `false` to exclude the file; empty means included.

## Rules

- Administrative paperwork (enrolment, fees, bookings, certificates) gets
  `false`. It is not study material and it pollutes retrieval.
- A source that legitimately spans modules gets its primary module. There is one
  module per source by design.
- Uncertain? Leave column 2 empty and say so. A wrong module is worse than no
  module: it makes `kb_search -m M8` quietly miss the thing you needed.
