"""The smallest set of checks that fail if the load-bearing logic breaks.

Not a suite. Four things are worth guarding, because each one is silent when it
goes wrong:

1. locators — a wrong page number or timestamp makes every citation a lie;
2. transcript windowing — timestamps must survive chunking;
3. incrementality — the whole design rests on stages not rerunning;
4. calendar parsing — it is the only syllabus that exists.
"""

from __future__ import annotations

import datetime as dt
import json
from pathlib import Path

import pytest

from studykb.chunk import to_chunks
from studykb.config import CalendarCfg, ChunkCfg, load_config
from studykb.extract import docx, pdf, vtt
from studykb.state import State, chunk_id

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture(scope="module")
def cfg():
    return load_config(Path(__file__).parents[1] / "config/default.yaml")


# -- 1. locators -----------------------------------------------------------
def test_pdf_pages_become_one_indexed_locators():
    units = pdf.extract(FIXTURES / "sample.pdf")
    assert [u.locator for u in units] == ["p.1", "p.2"]
    # The locator must point at the page that actually holds the text, or every
    # "open page N" in a generated note sends you to the wrong place.
    assert "Variational quantum circuit" in units[0].text
    assert "QUBO" in units[1].text


def test_text_layer_stats_sees_the_text():
    pages, mean_chars = pdf.text_layer_stats(FIXTURES / "sample.pdf")
    assert pages == 2
    assert mean_chars > 50, "a digital PDF must not be mistaken for a scan and sent to OCR"


# -- 2. transcript windows -------------------------------------------------
def test_transcript_windows_keep_their_start_time(cfg):
    units = vtt.extract(FIXTURES / "sample.vtt", cfg)
    assert [u.locator for u in units] == ["@00:00:01", "@00:06:10"]
    # Rolling captions repeat the previous line; keeping duplicates would
    # multiply the token count for no extra information.
    assert units[0].text.count("Welcome to the lecture") == 1
    assert all(u.provenance == "asr" for u in units)


def _docx(path: Path, paragraphs: list[str]) -> Path:
    """The smallest file python-docx-free extraction has to cope with."""
    import zipfile

    w = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
    body = "".join(f"<w:p><w:r><w:t>{p}</w:t></w:r></w:p>" for p in paragraphs)
    with zipfile.ZipFile(path, "w") as z:
        z.writestr("word/document.xml", f'<w:document xmlns:w="{w}"><w:body>{body}</w:body></w:document>')
    return path


def test_word_transcript_windows_start_at_the_speaker_mark(tmp_path, cfg):
    path = _docx(
        tmp_path / "lecture.docm",
        ["[Calogero Zarbo] 09:08:29", "Last time we talked about a specific use case.",
         "09:10:04", "It is a use case, so we cannot reproduce it.",
         "[Samuele Medici] 09:20:50", "It was this paper I was looking for."],
    )
    units = docx.extract(path, cfg)
    # 09:08:29 -> 09:10:04 is under the 300 s window, so those two stay together;
    # 09:20:50 is past it and opens the next one.
    assert [u.locator for u in units] == ["@09:08:29", "@09:20:50"]
    assert all(u.provenance == "asr" for u in units)
    # Who said it is part of what it is worth, so the name stays in the text.
    assert "[Samuele Medici]" in units[1].text


def test_a_cleaned_word_transcript_falls_back_to_paragraph_ranges(tmp_path, cfg):
    # Four of the thirty real files have every mark stripped out. Without a
    # bound they would arrive as one unit, and a transcript unit is never split
    # downstream — one unsearchable chunk for a three-hour lecture.
    budget = cfg.chunk.target_tokens * 4
    path = _docx(tmp_path / "cleaned.docx", ["word " * 200] * 10)
    units = docx.extract(path, cfg)
    assert len(units) > 1
    assert units[0].locator.startswith("¶")
    assert all(len(u.text) < budget * 2 for u in units)


def test_an_unbroken_wall_of_text_still_terminates(tmp_path, cfg):
    # No space to break on anywhere: the cut has to fall back to the budget
    # rather than walk backwards one character at a time.
    path = _docx(tmp_path / "wall.docx", ["x" * 20_000])
    units = docx.extract(path, cfg)
    assert len(units) == 7
    assert sum(len(u.text) for u in units) == 20_000


def test_a_time_in_running_speech_is_not_a_mark(tmp_path, cfg):
    path = _docx(
        tmp_path / "spoken.docm",
        ["[Stefano Martina] 09:05:00", "It is 9:05 now, and the run took 01:02:03 to finish."],
    )
    units = docx.extract(path, cfg)
    assert [u.locator for u in units] == ["@09:05:00"]


def test_chunking_does_not_split_a_transcript_window(cfg):
    units = vtt.extract(FIXTURES / "sample.vtt", cfg)
    chunks = to_chunks(
        units, source="t.vtt", source_title="t", type_="transcript", module="M7", cfg=cfg.chunk
    )
    assert [c.locator for c in chunks] == ["@00:00:01", "@00:06:10"]


def test_long_page_splits_but_every_piece_keeps_the_locator():
    from studykb.types import Unit

    unit = Unit(locator="p.42", text="\n\n".join(f"Paragraph {i}. " + "word " * 120 for i in range(12)))
    chunks = to_chunks(
        [unit], source="b.pdf", source_title="b", type_="book", module="M4",
        cfg=ChunkCfg(target_tokens=200, overlap_tokens=20),
    )
    assert len(chunks) > 1
    assert {c.locator for c in chunks} == {"p.42"}
    assert len({c.id for c in chunks}) == len(chunks), "chunk ids must be unique within a page"


# -- 3. incrementality -----------------------------------------------------
def test_chunk_ids_are_stable_across_runs():
    assert chunk_id("a.pdf", "p.1", 0, "book") == chunk_id("a.pdf", "p.1", 0, "book")
    assert chunk_id("a.pdf", "p.1", 0, "book") != chunk_id("a.pdf", "p.1", 1, "book")
    assert chunk_id("a.pdf", "p.1", 0, "book") != chunk_id("b.pdf", "p.1", 0, "book")
    assert chunk_id("a.pdf", "p.1", 0, "book") != chunk_id("a.pdf", "p.1", 0, "caption")


def test_stage_reruns_only_when_its_own_inputs_change(tmp_path):
    with State(tmp_path / "state.db") as st:
        assert st.needs("a.pdf", "embed", "sha1", "fp1"), "an unseen source must be processed"
        st.mark("a.pdf", "embed", "sha1", "fp1")

        assert not st.needs("a.pdf", "embed", "sha1", "fp1"), "unchanged input must cost nothing"
        assert st.needs("a.pdf", "embed", "sha2", "fp1"), "a changed file must be reprocessed"
        assert st.needs("a.pdf", "embed", "sha1", "fp2"), "a changed config must be reprocessed"
        assert st.needs("a.pdf", "vision", "sha1", "fp1"), "stages are gated independently"


def test_prompt_edit_invalidates_only_the_stages_that_use_prompts(cfg):
    before = cfg.fingerprint("p1")
    after = cfg.fingerprint("p2")
    assert before["vision"] != after["vision"]
    assert before["asr_cleanup"] != after["asr_cleanup"]
    # Re-embedding the corpus because a caption prompt changed would be hours of
    # GPU time for nothing.
    assert before["embed"] == after["embed"]
    assert before["extract"] == after["extract"]


def test_vanished_sources_are_reported_not_deleted(tmp_path):
    with State(tmp_path / "state.db") as st:
        st.see("a.pdf", "sha", "book", "M4")
        st.see("b.pdf", "sha", "book", "M4")
        assert st.vanished({"a.pdf"}) == ["b.pdf"]
        assert len(st.inventory()) == 2, "an unmounted volume must not silently drop the index"


# -- 4. calendar -----------------------------------------------------------
def test_year_typo_in_the_timetable_is_repaired():
    from studykb.calendar import _fix_year_typo

    # The real sheet has 2025-03-07 sitting between 2026 rows.
    assert _fix_year_typo(dt.date(2025, 3, 7), dt.date(2026, 3, 6)) == dt.date(2026, 3, 7)
    # A genuine same-week ordering must not be "repaired".
    assert _fix_year_typo(dt.date(2026, 3, 6), dt.date(2026, 3, 7)) == dt.date(2026, 3, 6)
    assert _fix_year_typo(dt.date(2026, 3, 7), None) == dt.date(2026, 3, 7)


def test_assessment_rows_map_to_every_module_they_cover():
    from studykb.calendar import _assessed_modules

    assert _assessed_modules("Assessment of modules 1, 2 and 3") == ["M1", "M2", "M3"]
    assert _assessed_modules("Assessment of module 8") == ["M8"]
    assert _assessed_modules("Quantum Tensor Network") == []


REAL_CALENDAR = Path.home() / "Scaricati/Calendario_MasterQML_2526 (updated 12 September 2026).xlsx.xlsx"


@pytest.mark.skipif(not REAL_CALENDAR.exists(), reason="course timetable not present")
def test_real_timetable_parses_into_nine_modules():
    from studykb import calendar as cal

    modules = cal.parse(
        REAL_CALENDAR,
        CalendarCfg(
            source=REAL_CALENDAR.name,
            sheet="A.Y._2025_2026",
            columns={
                "date": "Date", "time": "Time-\ntable", "mode": "Lesson type",
                "module": "Teaching", "topic": "Lesson title / topic",
                "teacher": "Instructor", "institution": "Institution / Company",
            },
        ),
    )
    assert [m.id for m in modules] == [f"M{i}" for i in range(1, 10)]

    m8 = next(m for m in modules if m.id == "M8")
    assert "Marco Corazza" in m8.teachers
    assert any("Thesis project" in lec.topic for lec in m8.lectures)
    # Every module must start after it ends nowhere: dates monotonic per module.
    for mod in modules:
        start, end = mod.date_range
        assert start and end and start <= end, f"{mod.id} has an inverted date range"


# -- 5. the quiet failures -------------------------------------------------
def test_a_repeated_footer_does_not_count_as_a_text_layer(tmp_path):
    """A 137-page deck flattened to vector art still carried an identical
    copyright footer on every page. Counting those characters made it look like
    it had text, so it skipped OCR and was indexed as nothing at all."""
    import pymupdf

    from studykb.extract.pdf import text_layer_stats

    doc = pymupdf.open()
    for _ in range(10):
        page = doc.new_page()
        page.insert_text((72, 560), "All rights reserved. Unauthorised reproduction is prohibited.", fontsize=8)
    path = tmp_path / "flattened.pdf"
    doc.save(str(path))
    doc.close()

    _, mean_chars = text_layer_stats(path)
    assert mean_chars == 0, "boilerplate repeated on every page is not content"


def test_real_text_survives_boilerplate_stripping(tmp_path):
    import pymupdf

    from studykb.extract.pdf import text_layer_stats

    doc = pymupdf.open()
    for i in range(10):
        page = doc.new_page()
        page.insert_text((72, 560), "All rights reserved.", fontsize=8)
        page.insert_text((72, 100), f"Page {i} carries its own substantive sentence about annealing.", fontsize=11)
    path = tmp_path / "real.pdf"
    doc.save(str(path))
    doc.close()

    _, mean_chars = text_layer_stats(path)
    assert mean_chars > 40


def test_clearing_a_stage_leaves_the_others_alone(tmp_path):
    """An empty collection means the embed state is lying and must be dropped —
    but the extraction and captions behind it are still valid and cost hours."""
    with State(tmp_path / "state.db") as st:
        st.mark("a.pdf", "embed", "sha", "fp")
        st.mark("a.pdf", "vision", "sha", "fp")
        assert st.clear_stage("embed") == 1
        assert st.needs("a.pdf", "embed", "sha", "fp")
        assert not st.needs("a.pdf", "vision", "sha", "fp")


def test_embed_gate_moves_when_an_upstream_stage_does(cfg):
    """Re-captioning a deck must re-index it. Gating embed on its own config
    alone left ten new captions sitting in a file embed never read again, while
    the run reported success and the index kept yesterday's content."""
    from studykb.pipeline import Source, _effective_fp

    slides = Source(path=Path("slides/deck.pdf"), rel="slides/deck.pdf", type="slides", vision="force")
    book = Source(path=Path("books/b.pdf"), rel="books/b.pdf", type="book", vision="never")

    before = cfg.fingerprint("p1")
    after = cfg.fingerprint("p2")   # a prompt edit: changes vision, not embed

    assert before["embed"] == after["embed"], "precondition: embed's own fingerprint is unchanged"
    assert _effective_fp(before, "embed", slides, cfg) != _effective_fp(after, "embed", slides, cfg)
    # A book is never captioned, so a caption-prompt edit must not cost it a
    # reindex it cannot benefit from.
    assert _effective_fp(before, "embed", book, cfg) == _effective_fp(after, "embed", book, cfg)


def test_two_corpora_do_not_share_a_state_file(tmp_path, monkeypatch):
    """A shared state file makes two corpora lie to each other: every source of
    corpus A reads as 'missing from disk' while ingesting B, and B's empty
    collection makes the reconciliation guard wipe A's embed state."""
    from studykb.cli import _load

    cfg_path = Path(__file__).parents[1] / "config/default.yaml"
    qml = _load("qml-master", cfg_path)[0].storage
    test = _load("test", cfg_path)[0].storage

    assert qml.state_db != test.state_db
    assert qml.collection != test.collection


def test_exclude_patterns_actually_exclude_subtrees():
    """`test-corpus/**` excluded nothing: pathlib's ** expands to directories
    only, so the review set was being indexed as course material."""
    from studykb.pipeline import _excluded

    patterns = ["test-corpus/**", "admin/**", "Bando *.pdf"]
    assert _excluded("test-corpus/books/conti.pdf", patterns)
    assert _excluded("test-corpus/slides/deck.pdf", patterns)
    assert _excluded("admin/receipt.pdf", patterns)
    assert _excluded("Bando Unico 25-26.pdf", patterns)
    assert not _excluded("Book/nielsen.pdf", patterns)
    assert not _excluded("slides/deck.pdf", patterns)


def test_a_caption_does_not_overwrite_the_page_it_describes(cfg):
    """Captions and body text share a source, a locator and an index. Leaving
    the type out of the chunk id made the caption upsert replace the page's own
    text: ten slides kept the model's description and lost what was printed."""
    from studykb.types import Unit

    page = Unit(locator="p.23", text="Pauli Gates. X or NOT.")
    caption = Unit(locator="p.23", text="A matrix and three circuit lines.", provenance="local-vlm")

    body = to_chunks([page], source="d.pdf", source_title="d", type_="slides", module="M4", cfg=cfg.chunk)
    caps = to_chunks([caption], source="d.pdf", source_title="d", type_="caption", module="M4", cfg=cfg.chunk)

    assert body[0].id != caps[0].id


# -- 5. code: notebooks and scripts ----------------------------------------
def test_notebook_cells_are_grouped_not_one_chunk_each(tmp_path, cfg):
    """53 cells of three lines each must not become 53 fragments.

    One chunk per cell is the obvious implementation and it floods the index
    with pieces too small to answer anything.
    """
    from studykb.extract import code

    nb = {"cells": [{"cell_type": "code", "source": [f"x = {i:03d}\n"]} for i in range(60)]}
    nb["cells"][0] = {"cell_type": "markdown", "source": ["# Title\n"]}
    nb["cells"].append({"cell_type": "code", "source": []})  # empty cells are dropped
    path = tmp_path / "t.ipynb"
    path.write_text(json.dumps(nb))

    units = code.extract_notebook(path, cfg)
    assert len(units) < 10, f"{len(units)} units from 61 small cells — not grouped"
    assert units[0].locator.startswith("cell"), units[0].locator
    assert "# Title" in units[0].text
    assert "```python" in units[0].text, "code cells must be fenced"
    # Every non-empty cell survives somewhere, and nothing is duplicated.
    joined = "\n".join(u.text for u in units)
    # cell 0 was overwritten with the markdown title, so the code cells are 1..59
    assert all(f"x = {i:03d}" in joined for i in range(1, 60))
    assert joined.count("x = ") == 59, "a cell was dropped or duplicated"


def test_python_locators_name_the_definition(tmp_path):
    """A code citation is only useful if it names something you can search for."""
    from studykb.extract import code

    path = tmp_path / "m.py"
    path.write_text(
        "import os\n\n\n"
        "def solve_qubo(q):\n    return q\n\n\n"
        "class Solver:\n    pass\n\n\n"
        'if __name__ == "__main__":\n    solve_qubo(1)\n'
    )
    units = code.extract_python(path)
    locators = [u.locator for u in units]
    assert locators[0] == "module level"
    assert any(l.startswith("solve_qubo (line ") for l in locators), locators
    assert any(l.startswith("Solver (line ") for l in locators), locators
    # Imports and the __main__ block are where a script does its work: keep them.
    assert "import os" in units[0].text
    assert "__main__" in units[0].text
    # A definition's body must not leak into the module-level unit.
    assert "return q" not in units[0].text


def test_unparseable_python_still_indexes(tmp_path):
    from studykb.extract import code

    path = tmp_path / "broken.py"
    path.write_text("def oops(:\n    pass\n")
    units = code.extract_python(path)
    assert [u.locator for u in units] == ["whole file"]
    assert "oops" in units[0].text


# -- 6. metrics ------------------------------------------------------------
def test_llm_counts_calls_tokens_and_time(monkeypatch, cfg):
    """A cost history nobody can trust is worse than none.

    Every model call goes through LLM._post, so a stage added later is measured
    without anyone remembering to wire it up. A failed call still counts: it
    burned the time it burned.
    """
    from studykb.llm import LLM

    class FakeResponse:
        def __init__(self, payload): self._p = payload
        def raise_for_status(self): pass
        def json(self): return self._p

    llm = LLM(cfg)
    calls = []

    def fake_post(path, json):
        calls.append(path)
        if len(calls) == 2:
            raise RuntimeError("endpoint died")
        return FakeResponse({"usage": {"prompt_tokens": 10, "completion_tokens": 4}})

    monkeypatch.setattr(llm.client, "post", fake_post)
    llm._post("/a", {})
    with pytest.raises(RuntimeError):
        llm._post("/b", {})
    llm._post("/c", {})

    c = llm.counters()
    assert c["calls"] == 3, "the failed call must still be counted"
    assert c["tokens_in"] == 20 and c["tokens_out"] == 8, "the failed call has no usage"
    assert c["seconds"] > 0


def test_stage_metrics_attribute_only_their_own_calls(cfg, tmp_path):
    """Two stages must not inherit each other's cost."""
    import sqlite3

    from studykb import metrics

    class FakeLLM:
        def __init__(self): self.n = 0
        def counters(self):
            return {"calls": self.n, "seconds": self.n * 1.0, "tokens_in": self.n * 7, "tokens_out": 0}

    llm = FakeLLM()
    run = metrics.Run(corpus="t")
    with run.stage("vision", llm) as m:
        llm.n += 5
        m.items = 5
    with run.stage("embed", llm) as m:
        llm.n += 2
        m.items = 2

    vision, embed = run.stages
    assert (vision.llm_calls, embed.llm_calls) == (5, 2)
    assert (vision.tokens_in, embed.tokens_in) == (35, 14)
    assert vision.per_item == pytest.approx(vision.seconds / 5)

    conn = sqlite3.connect(tmp_path / "s.db")
    run.save(conn)
    rows = metrics.stages_of(conn, run.run_id)
    assert [r[0] for r in rows] == ["vision", "embed"]
    assert metrics.history(conn)[0][0] == run.run_id


def test_gpu_meter_is_silent_without_nvidia_smi(monkeypatch):
    from studykb import metrics

    monkeypatch.setattr(metrics.shutil, "which", lambda _: None)
    g = metrics.GpuPower()
    g.start(); g.stop()
    assert not g.available and g.samples == 0 and g.wh == 0.0


def test_vault_file_refuses_everything_outside_the_vault(tmp_path):
    """The reading routes hand a query parameter to the filesystem.

    Fifth thing worth guarding: this one is silent in the worst way — a served
    file that should never have left the vault.
    """
    from studykb.server import vault_file

    vault = tmp_path / "vault"
    (vault / "10-modules").mkdir(parents=True)
    note = vault / "10-modules" / "03-grover.md"
    note.write_text("# Grover\n")
    (vault / "notes.txt").write_text("not a note")
    (tmp_path / "secret.md").write_text("outside")

    assert vault_file(vault, "10-modules/03-grover.md") == note
    for rel in ("../secret.md", "10-modules/../../secret.md", str(tmp_path / "secret.md"),
                "notes.txt", "10-modules", "missing.md", ""):
        assert vault_file(vault, rel) is None, rel
