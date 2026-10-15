from __future__ import annotations

from ste_lint.engine.findings import Finding
from ste_lint.engine.posmap import is_skippable
from ste_lint.engine.registry import RuleContext, Sentence, make_finding, rule


@rule("3.5", severity="error")
def check_ing(sent: Sentence, ctx: RuleContext) -> list[Finding]:
    out = []
    lex = ctx.lexicon
    for tok in sent.span:
        if is_skippable(tok) or tok.tag_ != "VBG":
            continue
        lower = tok.text.lower()
        if lex.approved_for(lower, "n") or lex.approved_for(lower, "adj"):
            continue
        if ctx.config.is_allowed(lower, "n") or ctx.config.is_allowed(lower, "adj"):
            continue
        out.append(make_finding(sent, ctx, "3.5", tok,
                                f"'{tok.text}': do not use the -ing form. Use the infinitive, imperative, or a noun."))
    return out


@rule("3.6", severity="error")
def check_passive(sent: Sentence, ctx: RuleContext) -> list[Finding]:
    for tok in sent.span:
        if tok.dep_ == "auxpass" or tok.dep_ == "nsubjpass":
            vbn = tok.head if tok.head.tag_ == "VBN" else next((t for t in sent.span if t.tag_ == "VBN"), tok.head)
            sev = "warning" if sent.mode == "descriptive" else "error"
            f = make_finding(sent, ctx, "3.6", vbn,
                             "Passive voice. Write in the active voice (procedural: use the imperative).", severity=sev)
            return [f] if f else []
    return []
