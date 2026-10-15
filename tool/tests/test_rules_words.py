def rules(fs):
    return sorted(f.rule for f in fs)


def test_clean_sentence_has_no_findings(lint):
    assert lint("Remove the cover.") == []


def test_unapproved_word_with_alternative(lint):
    [f] = lint("Consult the manual.")
    assert f.rule == "1.1" and f.severity == "error"
    assert f.text == "Consult" and f.suggestion == "refer" and f.fix == "refer"
    assert f.line == 1 and f.col == 1 and f.end_col == 8
    assert "REFER (v)" in f.message


def test_unknown_word_is_warning(lint):
    [f] = lint("Remove the flange.")
    assert f.rule == "1.1-unknown" and f.severity == "warning" and f.text == "flange"


def test_no_entry_for_used_pos_is_unknown_not_wrong_alternative(lint):
    # "contaminated" is only in the mini dictionary as an unapproved
    # adjective (alt "dirty"); used here as a past-tense VERB, spaCy tags it
    # VERB/VBD so no dictionary entry matches this token's part of speech.
    # It must not be reported as "not approved (adj). Use: DIRTY" -- that
    # would suggest an adjective as a fix for a verb, which is nonsensical.
    [f] = lint("It contaminated the oil.")
    assert f.rule == "1.1-unknown" and f.severity == "warning" and f.text == "contaminated"


def test_possessive_determiner_is_treated_as_adjective(lint):
    # spaCy tags "its"/"your" as PRON (tag_ PRP$) when used as possessive
    # determiners, but STE classifies them as adjectives (its/adj, your/adj
    # in the dictionary), distinct from the pronoun forms "it"/"you".
    assert lint("Remove its cover.") == []
    assert lint("Remove your cover.") == []


def test_than_in_comparative_is_treated_as_conjunction(lint):
    # spaCy tags "than" ADP (preposition) in the common comparative pattern
    # "more/less than ...", but the dictionary approves "than" only as a
    # conjunction. It must not be flagged 1.2 ("approved only as conj").
    fs = lint("The screw is more than the pump.")
    assert all(f.text.lower() != "than" for f in fs)


def test_allowlisted_technical_noun_not_flagged(lint):
    assert lint("Remove the flange.", technical_nouns={"flange/n"}) == []


def test_wrong_pos(lint):
    # spaCy tags sentence-initial "Test" as VERB; the mini lexicon has test/v
    # (unapproved) and test/n (approved) => branch "approved_any" => rule 1.2.
    [f] = lint("Test the system.")
    assert f.rule == "1.2" and "DO A TEST" in f.message.upper()


def test_wrong_pos_when_only_other_pos_approved(lint):
    # "Oil the valve." has spaCy tag "Oil" as NOUN (matching the approved
    # oil/n entry exactly, producing no finding), so it doesn't exercise this
    # rule. "Pump the fuel." reliably tags "Pump" as VERB against an entry
    # that is only approved as a noun (pump/n, no pump/v).
    fs = lint("Pump the fuel.")
    assert [f.rule for f in fs] == ["1.2"]
    assert "approved only as n" in fs[0].message


def test_wrong_verb_form(lint):
    [f] = lint("The screws are removing.")
    assert f.rule in ("1.4", "3.5")


def test_numbers_codes_and_placeholders_skipped(lint):
    # "P/N" and "12-345" tokenize into multiple tokens (P, /, N and 12, -,
    # 345), so they never appear as single-token finding text either; the
    # assertion below still guards against it.
    fs = lint("Tighten the screw to 5 Nm. See URL and CODE. Use part P/N 12-345.")
    assert all(f.text not in ("5", "Nm", "URL", "CODE", "12-345", "P/N") for f in fs)


def test_unit_after_number_is_skipped(lint):
    assert all(f.text != "Nm" for f in lint("Tighten the screw to 5 Nm."))


def test_unit_word_without_number_is_not_skipped(lint):
    assert any(f.text == "nm" for f in lint("The nm is dirty."))


def test_disable_rule(lint):
    assert lint("Remove the flange.", disable={"1.1-unknown"}) == []


def test_severity_override(lint):
    [f] = lint("Remove the flange.", severity_overrides={"1.1-unknown": "info"})
    assert f.severity == "info"


def test_finding_position_in_wrapped_markdown_paragraph(mini_lexicon, nlp):
    from ste_lint.config import Config
    from ste_lint.engine.pipeline import lint_blocks
    from ste_lint.inputs.markdown import extract_markdown

    md = "# Title\n\nRemove the cover.\nInstall the pump.\n  Then consult the manual.\n"
    blocks = extract_markdown(md, "a.md")
    [f] = [f for f in lint_blocks(blocks, mini_lexicon, Config.default(), nlp) if f.rule == "1.1"]
    assert f.text == "consult"
    assert f.line == 5
    line5 = "  Then consult the manual."
    assert f.col == line5.index("consult") + 1 == 8
    assert f.end_col == f.col + len("consult") <= len(line5) + 1


def test_finding_context_collapses_whitespace(mini_lexicon, nlp):
    from ste_lint.config import Config
    from ste_lint.engine.pipeline import lint_blocks
    from ste_lint.inputs.base import TextBlock

    block = TextBlock("Consult   the\tmanual.", "paragraph", "f", 1)
    [f] = lint_blocks([block], mini_lexicon, Config.default(), nlp)
    assert f.context == "Consult the manual."
    assert f.col == 1 and f.end_col == 8  # offsets come from the original text
