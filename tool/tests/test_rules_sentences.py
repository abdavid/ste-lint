from ste_lint.engine.pipeline import load_nlp
from ste_lint.engine.wordcount import count_words


def ids(fs):
    return [f.rule for f in fs]


def test_count_words_rules_86(nlp):
    doc = nlp("Tighten the self-locking nut to 5 Nm, then do a test.")
    assert count_words(list(doc.sents)[0]) == 10


def test_length_procedural_limit_20_is_rule_5_1(lint):
    long = "Remove the cover and remove the screw and remove the valve and remove the pump and remove the fuel and remove the oil now."
    [f] = [f for f in lint(long, mode="procedural") if f.rule == "5.1"]
    assert "limit 20" in f.message
    assert "6.3" not in ids(lint(long, mode="procedural"))


def test_length_descriptive_limit_25_is_rule_6_3(lint):
    twenty_two = "The pump is a system with a valve and a cover and a screw and a fitting and a manual and oil."
    assert "6.3" not in ids(lint(twenty_two, mode="descriptive"))
    assert "5.1" not in ids(lint(twenty_two, mode="descriptive"))
    long = "The pump is a system with a valve and a cover and a screw and a fitting and a manual and oil and fuel and a cover."
    [f] = [f for f in lint(long, mode="descriptive") if f.rule == "6.3"]
    assert "limit 25" in f.message
    assert "5.1" not in ids(lint(long, mode="descriptive"))


def test_heading_exempt_from_length(lint):
    long = " ".join(["cover"] * 30)
    fs = lint(long, kind="heading")
    assert "6.3" not in ids(fs) and "5.1" not in ids(fs)


def test_one_instruction_per_sentence(lint):
    fs = lint("Remove the cover and tighten the screw.", mode="procedural")
    assert "5.2" in ids(fs)


def test_imperative_required_in_procedural(lint):
    assert "5.3" in ids(lint("You can remove the cover.", mode="procedural"))
    assert "5.3" not in ids(lint("If the pump is dirty, remove the cover.", mode="procedural"))
    assert "5.3" not in ids(lint("Remove the cover.", mode="procedural"))


def test_paragraph_too_many_sentences(lint):
    para = " ".join(["Remove the cover."] * 7)
    assert "6.6" in ids(lint(para, mode="descriptive"))


def test_single_sentence_paragraph_is_not_flagged(mini_lexicon, nlp):
    # Issue 9 has no rule against one-sentence paragraphs (the old synthetic
    # "6.4" check was removed); a short middle paragraph must be clean.
    from ste_lint.config import Config
    from ste_lint.engine.pipeline import lint_blocks
    from ste_lint.inputs.base import TextBlock

    blocks = [TextBlock("Remove the cover. Install the pump.", "paragraph", "f", 1),
              TextBlock("Tighten the screw.", "paragraph", "f", 3),
              TextBlock("Remove the cover. Install the pump.", "paragraph", "f", 5)]
    assert lint_blocks(blocks, mini_lexicon, Config.default(), nlp) == []


def test_semicolon_and_long_parenthesis(lint):
    fs = lint("Remove the cover; install the pump (the pump with the dirty oil and the screw).")
    assert {"8.1", "8.3"} <= set(ids(fs))
