from studykb.search import _filter, matching

SOURCES = ["papers/exercise3.1.pdf", "papers/exercise3.2.pdf", "papers/exercise4.1.pdf",
           "transcripts/09 – Business Cases, NISQ Limits.docx"]


def test_fragment_matches_case_insensitive_and_several():
    assert matching(SOURCES, "EXERCISE3") == ["papers/exercise3.1.pdf", "papers/exercise3.2.pdf"]
    assert matching(SOURCES, "business cases") == ["transcripts/09 – Business Cases, NISQ Limits.docx"]
    assert matching(SOURCES, "nowhere") == []


def test_sources_become_a_must_condition():
    f = _filter("M7", None, None, ["a.pdf", "b.pdf"])
    keys = {c.key: c.match for c in f.must}
    assert keys["source"].any == ["a.pdf", "b.pdf"]
    assert keys["module"].value == "M7"
    assert _filter(None, None, None) is None
