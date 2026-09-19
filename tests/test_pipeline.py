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
from pathlib import Path

import pytest

from studykb.chunk import to_chunks
from studykb.config import CalendarCfg, ChunkCfg, load_config
from studykb.extract import pdf, vtt
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
    assert chunk_id("a.pdf", "p.1", 0) == chunk_id("a.pdf", "p.1", 0)
    assert chunk_id("a.pdf", "p.1", 0) != chunk_id("a.pdf", "p.1", 1)
    assert chunk_id("a.pdf", "p.1", 0) != chunk_id("b.pdf", "p.1", 0)


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
