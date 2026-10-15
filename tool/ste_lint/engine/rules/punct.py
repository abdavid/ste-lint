from __future__ import annotations

import re
from types import SimpleNamespace

from ste_lint.engine.findings import Finding
from ste_lint.engine.registry import RuleContext, Sentence, make_finding, rule

PAREN = re.compile(r"\(([^()]*)\)")


@rule("8.1", severity="info")
def check_semicolon(sent: Sentence, ctx: RuleContext) -> list[Finding]:
    out = []
    for tok in sent.span:
        if tok.text == ";":
            f = make_finding(sent, ctx, "8.1", tok, "Do not use a semicolon; write two sentences or a list.")
            if f:
                out.append(f)
    return out


@rule("8.3", severity="info")
def check_parentheses(sent: Sentence, ctx: RuleContext) -> list[Finding]:
    out = []
    for m in PAREN.finditer(sent.text):
        if len(m.group(1).split()) > 5:
            span = SimpleNamespace(idx=sent.span.start_char + m.start(), text=m.group(0))
            f = make_finding(sent, ctx, "8.3", span, "Long parenthetical text; move it to its own sentence.")
            if f:
                out.append(f)
    return out
