# Syllabus from the timetable

`src/studykb/calendar.py` · 264 lines

The master publishes no syllabus document. The timetable spreadsheet is the only
record of what each lecture covered, so it is parsed into modules, dates,
teachers and topics.

That output feeds three things: module assignment during
[discovery](discovery.md), the syllabus pages in the vault, and the glossary
used by [ASR cleanup](enrichment.md).

## The sheet is built for humans

Every irregularity is absorbed here so it stays out of the rest of the codebase.

### Continuation rows

Dates, module names and teachers are written once and left blank on the rows
below. Parsing carries them forward — and **resets the teacher when the module
changes**, or the carried name leaks into the next module.

### Inconsistent module names

`4 - From Quantum Computing to Quantum AI` and `4 - From Quantum Computing to
QML` are the same module. `_MODULE_NO` takes the leading number as the id and
keeps the longest title seen, on the assumption that the short ones are
abbreviations.

### Year typos

The real sheet contains `2025-03-07` and `2025-09-25` sitting between 2026 rows.
Left alone, they reorder the syllabus and break date-to-module resolution.

```python
if (previous - parsed).days > 300:
    bumped = parsed.replace(year=parsed.year + 1)
    if bumped >= previous:
        return bumped
```

`ponytail:` this assumes a forward-ordered sheet. If the timetable ever lists
make-up lectures out of order, delete this and fix the source file instead.

### Assessment rows

They sit in their own rows with no module column, so they must be read **before**
the carry-forward logic claims them for whatever module came last. "Assessment of
modules 1, 2 and 3" produces one entry in each of M1, M2 and M3.

### Header matching

`_find_header` matches columns by header text, so inserting a column does not
silently shift every field. Positional defaults are the fallback.

## Output

`to_markdown` writes one page per module into `vault/00-syllabus/M*.md`: period,
teachers, and a table of every lecture with date, time, topic and mode.
Assessments are flagged ⚠️.

`_write_syllabus` preserves anything below a `## Notes` heading, so regenerating
never overwrites what you wrote there.

`glossary_terms` returns lecture titles and teacher names — exactly the words
auto-captions get wrong.

## Status

Parsing is covered by tests against the real spreadsheet, including the year
typos and the assessment fan-out. **The generated vault pages have never been
checked against the source by eye.** See [DELIVERY.md](../DELIVERY.md) step 4.1.

## Gate

Today, manual: open `vault/00-syllabus/M8.md` beside the spreadsheet and compare
the lecture list. A `review --what syllabus` is on the roadmap.
