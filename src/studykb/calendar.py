"""The real syllabus, read from the course timetable.

The master publishes no syllabus document; the timetable spreadsheet is the only
place that says what each lecture actually covers. Parsing it gives modules,
dates, teachers and lecture topics for free, which beats trying to reconstruct
the same information from transcripts.

The sheet is built for humans: dates and module names are written once and left
blank on continuation rows, and the same module appears under slightly different
spellings ("4 - From Quantum Computing to Quantum AI" vs "4 - From Quantum
Computing to QML"). Both are handled here, so the mess stays out of the rest of
the codebase.
"""

from __future__ import annotations

import datetime as dt
import re
from dataclasses import dataclass
from pathlib import Path

from .config import CalendarCfg
from .limits import HEADER_SCAN_ROWS

_MODULE_NO = re.compile(r"^\s*(\d+)\s*[-–—]?\s*(.*)$", re.DOTALL)
_BREAK = re.compile(r"(?i)\b(break|holiday|vacanz)")
_ASSESSMENT = re.compile(r"(?i)(assessment[^|]*)")
_ASSESSED_MODULES = re.compile(r"(?i)modules?\s+([\d,\s]*\d)(?:\s+and\s+(\d+))?")

# Column layout of the timetable as shipped, used when the header row does not
# name a field. Read-only.
_POSITIONAL = {"date": 0, "day": 1, "time": 2, "mode": 5, "module": 6, "topic": 7, "teacher": 8, "institution": 9}


@dataclass
class Lecture:
    date: dt.date | None
    time: str
    module: str                # "M8"
    topic: str
    teacher: str
    institution: str
    mode: str                  # "Online" | "In person"
    is_assessment: bool = False


@dataclass
class Module:
    id: str                    # "M8"
    title: str
    lectures: list[Lecture]

    @property
    def teachers(self) -> list[str]:
        seen: dict[str, None] = {}
        for lec in self.lectures:
            for name in (n.strip() for n in lec.teacher.split(",")):
                if name and name.upper() != "TBD":
                    seen.setdefault(name, None)
        return list(seen)

    @property
    def date_range(self) -> tuple[dt.date | None, dt.date | None]:
        dates = sorted(lec.date for lec in self.lectures if lec.date)
        return (dates[0], dates[-1]) if dates else (None, None)


def _clean(value: object) -> str:
    if value is None:
        return ""
    if isinstance(value, (dt.date, dt.datetime)):
        return value.isoformat()
    return " ".join(str(value).split())


def _as_date(value: object) -> dt.date | None:
    if isinstance(value, dt.datetime):
        return value.date()
    if isinstance(value, dt.date):
        return value
    text = _clean(value)
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d/%m/%y"):
        try:
            return dt.datetime.strptime(text, fmt).date()
        except ValueError:
            continue
    return None


def parse(xlsx: Path, cfg: CalendarCfg) -> list[Module]:
    import openpyxl

    wb = openpyxl.load_workbook(xlsx, data_only=True, read_only=True)
    ws = wb[cfg.sheet] if cfg.sheet and cfg.sheet in wb.sheetnames else wb.worksheets[0]
    rows = [list(r) for r in ws.iter_rows(values_only=True)]
    wb.close()

    header_idx, col = _find_header(rows, cfg)
    modules: dict[str, Module] = {}
    # Continuation rows leave date, module and teacher blank; carry them forward.
    cur_date: dt.date | None = None
    cur_module: str | None = None
    cur_teacher = ""
    cur_inst = ""

    for row in rows[header_idx + 1 :]:
        get = lambda key: _clean(row[col[key]]) if col.get(key) is not None and col[key] < len(row) else ""  # noqa: E731

        joined = " ".join(_clean(c) for c in row if c is not None)
        if not joined or _BREAK.search(joined):
            continue

        if (d := _as_date(row[col["date"]] if col.get("date") is not None else None)) is not None:
            cur_date = _fix_year_typo(d, cur_date)

        raw_module = get("module")
        topic = get("topic")
        if raw_module and (parsed := _MODULE_NO.match(raw_module)):
            module_id = f"M{int(parsed.group(1))}"
            if module_id != cur_module:
                # Carried-forward teacher belongs to the previous module.
                cur_teacher, cur_inst = "", ""
            cur_module = module_id
            title = " ".join(parsed.group(2).split())
            mod = modules.setdefault(cur_module, Module(cur_module, title, []))
            # Keep the longest spelling seen; the short ones are abbreviations.
            if len(title) > len(mod.title):
                mod.title = title

        # Assessments sit in their own rows with no module column, so they must
        # be read before the carry-forward logic claims them for the wrong one.
        if match := _ASSESSMENT.search(joined):
            label = " ".join(match.group(1).split())
            for mid in _assessed_modules(label) or ([cur_module] if cur_module else []):
                modules.setdefault(mid, Module(mid, "", [])).lectures.append(
                    Lecture(
                        date=cur_date,
                        time=get("time"),
                        module=mid,
                        topic=label,
                        teacher="",
                        institution="",
                        mode=get("mode"),
                        is_assessment=True,
                    )
                )
            continue

        if teacher := get("teacher"):
            cur_teacher = teacher
        if inst := get("institution"):
            cur_inst = inst

        if not topic or cur_module is None:
            continue

        modules[cur_module].lectures.append(
            Lecture(
                date=cur_date,
                time=get("time"),
                module=cur_module,
                topic=topic,
                teacher=cur_teacher,
                institution=cur_inst,
                mode=get("mode"),
            )
        )

    return [modules[k] for k in sorted(modules, key=lambda m: int(m[1:]))]


def _assessed_modules(label: str) -> list[str]:
    """'Assessment of modules 1, 2 and 3' -> ['M1', 'M2', 'M3']."""
    match = _ASSESSED_MODULES.search(label)
    if not match:
        return []
    numbers = re.findall(r"\d+", " ".join(g for g in match.groups() if g))
    return [f"M{int(n)}" for n in numbers]


def _fix_year_typo(parsed: dt.date, previous: dt.date | None) -> dt.date:
    """Repair the hand-typed year slips in the timetable.

    The sheet contains 2025-03-07 and 2025-09-25 where the surrounding rows are
    2026: a year typo, and left alone it reorders the syllabus and breaks
    date-to-module resolution. The timetable runs forward, so a date that jumps
    backwards by most of a year, and lands right again with a year added, is one
    of these.

    ponytail: assumes a strictly forward-ordered sheet; if the calendar ever
    lists make-up lectures out of order, drop this and fix the source file.
    """
    if previous is None or parsed >= previous:
        return parsed
    if (previous - parsed).days > 300:
        try:
            bumped = parsed.replace(year=parsed.year + 1)
        except ValueError:  # 29 February
            return parsed
        if bumped >= previous:
            return bumped
    return parsed


def _find_header(rows: list[list], cfg: CalendarCfg) -> tuple[int, dict[str, int]]:
    """Locate the header row and map logical fields to column indices.

    Matching is by header text so that inserting a column does not silently
    shift every field; positional defaults are the fallback.
    """
    wanted = cfg.columns or {}
    for i, row in enumerate(rows[:HEADER_SCAN_ROWS]):
        cells = [_clean(c).lower() for c in row]
        if "date" not in cells:
            continue
        col: dict[str, int] = {}
        for field, header in wanted.items():
            target = " ".join(str(header).split()).lower()
            if target in cells:
                col[field] = cells.index(target)
        if "date" in col or wanted == {}:
            return i, col or _POSITIONAL
        return i, {**_POSITIONAL, **col}
    return 0, _POSITIONAL


def to_markdown(modules: list[Module]) -> dict[str, str]:
    """One syllabus page per module, for the Obsidian vault."""
    out: dict[str, str] = {}
    for mod in modules:
        start, end = mod.date_range
        span = f"{start} → {end}" if start else "date TBD"
        lines = [
            f"# {mod.id} — {mod.title}",
            "",
            f"- **Period:** {span}",
            f"- **Teachers:** {', '.join(mod.teachers) or 'TBD'}",
            f"- **Lectures:** {len(mod.lectures)}",
            "",
            "| Date | Time | Topic | Teacher | Mode |",
            "|---|---|---|---|---|",
        ]
        for lec in mod.lectures:
            mark = " ⚠️" if lec.is_assessment else ""
            lines.append(
                f"| {lec.date or ''} | {lec.time} | {lec.topic}{mark} | {lec.teacher} | {lec.mode} |"
            )
        lines += ["", "## Notes", "", "<!-- your notes go below; studykb never overwrites this file -->", ""]
        out[mod.id] = "\n".join(lines)
    return out


def glossary_terms(modules: list[Module]) -> list[str]:
    """Lecture titles and teacher names, for the ASR-cleanup prompt.

    These are exactly the words auto-captions get wrong.
    """
    terms: set[str] = set()
    for mod in modules:
        terms.add(mod.title)
        terms.update(mod.teachers)
        for lec in mod.lectures:
            if lec.topic and not lec.is_assessment:
                terms.add(lec.topic)
    return sorted(t for t in terms if len(t) > 2)
