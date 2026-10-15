from __future__ import annotations

from ste_lint.engine.findings import Finding
from ste_lint.engine.registry import RuleContext, Sentence, make_finding, paragraph_rule

MAX_SENTENCES = 6


@paragraph_rule("6.6", severity="warning")
def check_paragraph_length(sents: list[Sentence], ctx: RuleContext, first: bool, last: bool) -> list[Finding]:
    if len(sents) <= MAX_SENTENCES:
        return []
    f = make_finding(sents[0], ctx, "6.6", sents[0].span, f"Paragraph has {len(sents)} sentences (maximum {MAX_SENTENCES}).")
    return [f] if f else []
