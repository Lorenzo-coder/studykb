"""Notebooks and Python files -> Units.

Both are code, and on this corpus that is not a compromise: across the seven
tutorial notebooks there are 846 characters of markdown against 22,000 of
Python. Indexing "just the prose" would have indexed nothing.

Neither format needs a dependency. A notebook is JSON, which `json` reads; a
Python file is text, which `ast` can point at.

**Outputs are dropped.** They are execution artefacts — an array, a warning, a
base64 PNG — and indexing them buries the code that produced them under its own
exhaust.

Locators are what make a code chunk worth citing. A notebook says which cells
(`cells 4-9`); a Python file says which definition (`solve_qubo (line 42)`), so
a hit sends you to a name you can search for rather than to a file you then have
to read.
"""

from __future__ import annotations

import ast
import json
from pathlib import Path

from ..chunk import CHARS_PER_TOKEN
from ..config import Config
from ..types import Unit


def extract_notebook(path: Path, cfg: Config) -> list[Unit]:
    """One Unit per run of cells, up to the chunk ceiling.

    A cell is the wrong unit: these notebooks run to 53 cells, most of them two
    or three lines, and one chunk per cell floods the index with fragments too
    small to answer anything. Consecutive cells are accumulated instead, up to
    the same ceiling the chunker uses, so a Unit is a readable stretch of
    notebook rather than a single import.
    """
    ceiling = cfg.chunk.target_tokens * CHARS_PER_TOKEN
    cells = json.loads(path.read_text()).get("cells", [])

    units: list[Unit] = []
    buf: list[str] = []
    first = 1

    def flush(last: int) -> None:
        if not buf:
            return
        span = f"cells {first}-{last}" if last > first else f"cell {first}"
        units.append(Unit(locator=span, text="\n\n".join(buf), provenance="text-layer"))
        buf.clear()

    for i, cell in enumerate(cells, start=1):
        text = "".join(cell.get("source", [])).strip()
        if not text:
            continue
        # Fenced, so a retrieved passage reads as code instead of as prose that
        # happens to contain colons.
        if cell.get("cell_type") == "code":
            text = f"```python\n{text}\n```"
        if buf and sum(len(b) for b in buf) + len(text) > ceiling:
            flush(i - 1)
            first = i
        if not buf:
            first = i
        buf.append(text)
    flush(len(cells))
    return units


def extract_python(path: Path) -> list[Unit]:
    """One Unit per top-level function or class, plus one for the rest."""
    source = path.read_text()
    try:
        tree = ast.parse(source)
    except SyntaxError:
        # A file that will not parse is still worth searching; it just loses its
        # per-definition locators.
        return [Unit(locator="whole file", text=source, provenance="text-layer")]

    units: list[Unit] = []
    claimed: set[int] = set()
    for node in tree.body:
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            continue
        segment = ast.get_source_segment(source, node)
        if not segment:
            continue
        units.append(
            Unit(
                locator=f"{node.name} (line {node.lineno})",
                text=segment,
                provenance="text-layer",
                heading=node.name,
            )
        )
        claimed.update(range(node.lineno, (node.end_lineno or node.lineno) + 1))

    # Imports, constants, the `if __name__` block: in a script this is often
    # where the actual work happens, so it is kept rather than skipped.
    rest = "\n".join(
        line for n, line in enumerate(source.splitlines(), start=1) if n not in claimed
    ).strip()
    if rest:
        units.insert(0, Unit(locator="module level", text=rest, provenance="text-layer"))
    return units
