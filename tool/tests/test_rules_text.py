import pytest

from ste_lint.extract.rules_text import parse_rules, slice_part1

SAMPLE = """Section 1 – Words
Summary of the rules
Rule 1.1 Pick words from this list:
- Words on the approved list
Rule 1.2 Keep each listed word in its listed word class.

Issue 9 Part 1 - Writing rules Page 1-1-1
2025-01-15
ASD-STE100 Simplified Technical English

Sample heading
Rule 1.1 Pick words from this list:
- Words on the approved list
- Technical nouns
This sample body mentions a word list.

Rule 1.2 Keep each listed word in its listed word class.
A word can belong to more than one word class.
Section 2 – Multi-word nouns
"""


def test_parse_rules_takes_last_occurrence_as_body():
    rules = parse_rules(SAMPLE)
    assert set(rules) == {"1.1", "1.2"}
    assert rules["1.1"]["title"] == "Pick words from this list:"
    assert "word list" in rules["1.1"]["body"]
    assert "Technical nouns" in rules["1.1"]["body"]
    assert "Page 1-1-1" not in rules["1.1"]["body"]
    assert rules["1.2"]["body"].strip().endswith("more than one word class.")


def test_slice_part1_returns_slice_between_anchors():
    text = "Highlights\nPart 2 – Dictionary\n...junk...\nSection 1 – Words\nSummary of the rules\nRule 1.1 X\nbody\nPart 2 – Dictionary\nIntroduction\n"
    sliced = slice_part1(text)
    assert sliced.startswith("Section 1 – Words\nSummary of the rules")
    assert "Rule 1.1 X" in sliced
    assert "Introduction" not in sliced


def test_slice_part1_raises_when_anchor_missing():
    with pytest.raises(RuntimeError, match="Summary of the rules"):
        slice_part1("no anchors here at all\n")
