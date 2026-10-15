import json

import pytest

from ste_lint.extract.dictionary import parse_entries, validate
from ste_lint.extract.pdf_words import Line


def L(y, col, text, page=150):
    return Line(y=y, col=col, text=text, x0=0.0, page=page)


def test_unapproved_with_alternative_and_examples():
    lines = [
        L(96, 1, "consult (v)"),
        L(96, 2, "REFER (v)"),
        L(96, 3, "FOR THE PIN"), L(108, 3, "NUMBERS, REFER"), L(120, 3, "TO THE WIRING"), L(132, 3, "DIAGRAM."),
        L(96, 4, "For the pin numbers,"), L(108, 4, "consult the wiring"), L(120, 4, "diagram."),
    ]
    [e] = parse_entries(lines)
    assert e["id"] == "consult/v"
    assert e["approved"] is False
    assert e["alternatives"] == [{"word": "refer", "pos": "v"}]
    assert e["examples"]["ste"] == ["FOR THE PIN NUMBERS, REFER TO THE WIRING DIAGRAM."]
    assert e["examples"]["non_ste"] == ["For the pin numbers, consult the wiring diagram."]


def test_approved_verb_forms_and_meaning():
    lines = [
        L(96, 1, "ACCEPT (v),"), L(108, 1, "ACCEPTS,"), L(120, 1, "ACCEPTED,"), L(132, 1, "ACCEPTED"),
        L(96, 2, "To agree that a result"), L(108, 2, "is good enough"),
        L(96, 3, "ACCEPT THE SEAL IF"), L(108, 3, "IT HAS NO CUTS."),
    ]
    [e] = parse_entries(lines)
    assert e["approved"] is True
    assert e["forms"] == ["accept", "accepts", "accepted"]
    assert e["meaning"] == "To agree that a result is good enough"
    assert e["examples"]["ste"] == ["ACCEPT THE SEAL IF IT HAS NO CUTS."]


def test_multiple_alternatives_each_get_their_examples():
    lines = [
        L(96, 1, "abnormal (adj)"),
        L(96, 2, "UNUSUAL (adj)"), L(96, 3, "MONITOR THE PUMP FOR"), L(108, 3, "UNUSUAL VIBRATION."), L(96, 4, "Monitor the pump for"), L(108, 4, "abnormal vibration."),
        L(130, 2, "INCORRECT (adj)"), L(130, 3, "IF THE GAUGE SHOWS AN"), L(142, 3, "INCORRECT VALUE, STOP."), L(130, 4, "If the gauge shows an"), L(142, 4, "abnormal value, stop."),
    ]
    [e] = parse_entries(lines)
    assert [a["word"] for a in e["alternatives"]] == ["unusual", "incorrect"]
    assert e["alternatives"][1]["examples"]["ste"] == ["IF THE GAUGE SHOWS AN INCORRECT VALUE, STOP."]
    assert e["examples"]["ste"] == ["MONITOR THE PUMP FOR UNUSUAL VIBRATION.", "IF THE GAUGE SHOWS AN INCORRECT VALUE, STOP."]


def test_for_other_meanings_marker_and_wrapped_alternative_pos():
    lines = [
        L(96, 1, "CONTACT (v)"),
        L(96, 2, "To talk to a person"), L(96, 3, "CONTACT THE SUPPLIER."),
        L(120, 2, "For other"), L(132, 2, "meanings, use:"),
        L(144, 2, "TOUCH"), L(156, 2, "(v)"), L(144, 3, "PUSH THE LEVER UNTIL IT TOUCHES THE STOP."), L(144, 4, "Push the lever until it contacts the stop."),
    ]
    [e] = parse_entries(lines)
    assert e["approved"] is True
    assert e["meaning"] == "To talk to a person"
    assert e["alternatives"] == [{"word": "touch", "pos": "v", "examples": {"ste": ["PUSH THE LEVER UNTIL IT TOUCHES THE STOP."], "non_ste": ["Push the lever until it contacts the stop."]}}]


def test_comparative_forms_and_no_other_forms():
    lines = [
        L(96, 1, "BAD (adj)"), L(108, 1, "(WORSE,"), L(120, 1, "WORST)"), L(96, 2, "Of low quality"),
        L(200, 1, "BE (v)"), L(212, 1, "IS, WAS,"), L(224, 1, "(also ARE, WERE)"), L(236, 1, "No other verb"), L(248, 1, "forms."), L(200, 2, "Function word"),
    ]
    bad, be = parse_entries(lines)
    assert bad["forms"] == ["bad", "worse", "worst"]
    assert be["forms"] == ["be", "is", "was", "are", "were"]
    assert be["no_other_forms"] is True


def test_parenthesised_headword():
    [e] = parse_entries([L(96, 1, "case (in case of) (conj)"), L(96, 2, "IF (conj)")])
    assert e["word"] == "case (in case of)"
    assert e["pos"] == "conj"


def test_wrapped_headword_does_not_corrupt_preceding_entry():
    # Regression test for the pending_prefix/buffered/_flush_to_old_entry path:
    # "chance" wraps onto a second column-1 row "(by chance) (n)" before it is
    # recognized as a headword. Column-2/3/4 rows on the first wrapped row's y
    # (the alternative ACCIDENTALLY and its examples) must NOT be committed to
    # the preceding entry ("chafed") while the wrap is still ambiguous.
    lines = [
        L(96, 1, "chafed (adj)"),
        L(96, 2, "WORN (adj)"),
        L(96, 3, "EXAMINE THE CABLE"), L(108, 3, "FOR WORN INSULATION."),
        L(96, 4, "Examine the cable for"), L(108, 4, "chafed insulation."),
        L(130, 1, "chance"),
        L(130, 2, "ACCIDENTALLY (adv)"),
        L(130, 3, "IF THE VALVE OPENS"),
        L(130, 4, "If the valve opens"),
        L(142, 1, "(by chance) (n)"),
        L(142, 3, "BY CHANCE, CLOSE IT"),
        L(142, 4, "by chance, close it"),
        L(154, 3, "AGAIN."),
        L(154, 4, "again."),
    ]
    e1, e2 = parse_entries(lines)

    assert e1["id"] == "chafed/adj"
    assert e1["alternatives"] == [{"word": "worn", "pos": "adj"}]
    assert e1["examples"]["ste"] == ["EXAMINE THE CABLE FOR WORN INSULATION."]
    assert e1["examples"]["non_ste"] == ["Examine the cable for chafed insulation."]

    assert e2["id"] == "chance (by chance)/n"
    assert e2["alternatives"] == [{"word": "accidentally", "pos": "adv"}]
    assert e2["examples"]["ste"] == ["IF THE VALVE OPENS BY CHANCE, CLOSE IT AGAIN."]
    assert e2["examples"]["non_ste"] == ["If the valve opens by chance, close it again."]


def test_validate_flags_problems():
    ok = {"id": "x/n", "word": "x", "pos": "n", "approved": False, "forms": ["x"], "no_other_forms": False,
          "meaning": "", "alternatives": [{"word": "y", "pos": "n"}], "examples": {"ste": [], "non_ste": []}, "page": 1}
    bad = dict(ok, id="z/v", word="z", pos="v", alternatives=[])
    assert validate([ok], check_count=False) == []
    assert any("z/v" in p for p in validate([bad], check_count=False))


def test_mini_fixture_matches_schema(fixtures):
    import jsonschema
    from ste_lint import DATA_DIR

    schema = json.loads((DATA_DIR / "schema.json").read_text())
    data = json.loads((fixtures / "mini_dictionary.json").read_text())
    jsonschema.validate(data, schema)


@pytest.mark.corpus
def test_real_dictionary_spot_checks():
    from ste_lint import DICTIONARY_PATH

    data = json.loads(DICTIONARY_PATH.read_text())
    by_id = {e["id"]: e for e in data["entries"]}
    assert 2100 <= len(by_id) <= 2300
    assert by_id["consult/v"]["alternatives"][0]["word"] == "refer"
    assert by_id["accept/v"]["forms"] == ["accept", "accepts", "accepted"]
    assert by_id["contact/v"]["approved"] is True
    assert any(a["word"] == "touch" for a in by_id["contact/v"]["alternatives"])
