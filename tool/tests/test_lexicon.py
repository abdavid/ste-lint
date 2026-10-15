import json

import pytest

from ste_lint.engine.lexicon import Lexicon


@pytest.fixture
def lex(fixtures):
    return Lexicon.from_dict(json.loads((fixtures / "mini_dictionary.json").read_text()))


def test_by_form_returns_all_pos(lex):
    ids = sorted(e.id for e in lex.by_form("test"))
    assert ids == ["test/n", "test/v"]


def test_by_form_is_case_insensitive_and_uses_inflections(lex):
    assert [e.id for e in lex.by_form("Removed")] == ["remove/v"]


def test_approved_for(lex):
    assert lex.approved_for("test", "n").id == "test/n"
    assert lex.approved_for("test", "v") is None
    assert lex.approved_for("zzz", "n") is None


def test_unapproved_entry_alternatives(lex):
    [e] = lex.by_form("consult")
    assert e.approved is False
    assert e.alternatives[0].word == "refer"
    assert e.examples_ste == ("REFER TO THE MANUAL.",)


def test_load_missing_file_has_helpful_error(tmp_path):
    with pytest.raises(FileNotFoundError, match="build-dictionary"):
        Lexicon.load(tmp_path / "nope.json")
