from __future__ import annotations

from ste_lint.engine.findings import Finding
from ste_lint.engine.registry import RuleContext, Sentence, make_finding, rule
from ste_lint.engine.wordcount import count_words

LIMITS = {"procedural": 20, "descriptive": 25}
CLAUSE_STARTERS = {"if", "when", "before", "after", "to", "unless", "until", "while"}
TEXT_KINDS = ("paragraph", "list_item", "string_value", "table_cell")


def _check_length(sent: Sentence, ctx: RuleContext, rule_id: str, limit: int) -> list[Finding]:
    n = count_words(sent.span)
    if n <= limit:
        return []
    f = make_finding(sent, ctx, rule_id, sent.span, f"Sentence has {n} words (limit {limit} in {sent.mode} text).")
    return [f] if f else []


@rule("5.1", severity="error", modes=("procedural",), kinds=TEXT_KINDS)
def check_length_procedural(sent: Sentence, ctx: RuleContext) -> list[Finding]:
    """Rule 5.1: procedural sentences have at most 20 words."""
    return _check_length(sent, ctx, "5.1", LIMITS["procedural"])


@rule("6.3", severity="error", modes=("descriptive",), kinds=TEXT_KINDS)
def check_length_descriptive(sent: Sentence, ctx: RuleContext) -> list[Finding]:
    """Rule 6.3: descriptive sentences have at most 25 words."""
    return _check_length(sent, ctx, "6.3", LIMITS["descriptive"])


def _imperatives(span):
    return [t for t in span if t.tag_ == "VB" and t.dep_ in ("ROOT", "conj")
            and not any(c.dep_ in ("nsubj", "nsubjpass") for c in t.children)]


@rule("5.2", severity="warning", modes=("procedural",), kinds=TEXT_KINDS)
def check_one_instruction(sent: Sentence, ctx: RuleContext) -> list[Finding]:
    imps = _imperatives(sent.span)
    if len(imps) < 2:
        return []
    joined = any(t.lower_ in ("and", "then") for t in sent.span)
    if not joined:
        return []
    f = make_finding(sent, ctx, "5.2", imps[1], "More than one instruction in a sentence. Use one instruction per sentence.")
    return [f] if f else []


@rule("5.3", severity="warning", modes=("procedural",), kinds=("paragraph", "list_item", "string_value"))
def check_imperative(sent: Sentence, ctx: RuleContext) -> list[Finding]:
    toks = [t for t in sent.span if not t.is_punct and not t.is_space]
    if len(toks) < 3:
        return []
    if _imperatives(sent.span):
        return []
    if toks[0].lower_ in CLAUSE_STARTERS and any(t.tag_ == "VB" for t in toks[1:]):
        return []
    f = make_finding(sent, ctx, "5.3", sent.span.root, "Instruction is not in the imperative form.")
    return [f] if f else []
