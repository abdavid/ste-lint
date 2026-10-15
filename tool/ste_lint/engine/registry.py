from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from ste_lint.config import Config
from ste_lint.engine.findings import Finding
from ste_lint.engine.lexicon import Lexicon
from ste_lint.inputs.base import TextBlock


@dataclass
class Sentence:
    span: object  # spacy Span
    block: TextBlock
    mode: str

    @property
    def text(self) -> str:
        return self.span.text


@dataclass
class RuleContext:
    lexicon: Lexicon
    config: Config


RuleFn = Callable[[Sentence, RuleContext], list[Finding]]


@dataclass
class RuleSpec:
    id: str
    severity: str
    modes: tuple[str, ...]
    kinds: tuple[str, ...] | None
    fn: RuleFn


RULES: dict[str, RuleSpec] = {}

ParagraphRuleFn = Callable[[list[Sentence], RuleContext, bool, bool], list[Finding]]
PARAGRAPH_RULES: dict[str, RuleSpec] = {}


def rule(id: str, severity: str, modes=("procedural", "descriptive"), kinds=None):
    def deco(fn: RuleFn) -> RuleFn:
        RULES[id] = RuleSpec(id, severity, tuple(modes), tuple(kinds) if kinds else None, fn)
        return fn

    return deco


def paragraph_rule(id: str, severity: str, modes=("descriptive",)):
    def deco(fn: ParagraphRuleFn) -> ParagraphRuleFn:
        PARAGRAPH_RULES[id] = RuleSpec(id, severity, tuple(modes), ("paragraph",), fn)
        return fn

    return deco


def make_finding(sent: Sentence, ctx: RuleContext, rule_id: str, target, message: str,
                 severity: str | None = None, suggestion: str | None = None, fix: str | None = None) -> Finding | None:
    if rule_id in ctx.config.disable or rule_id.split("-")[0] in ctx.config.disable:
        return None
    spec = RULES.get(_base(rule_id)) or PARAGRAPH_RULES.get(_base(rule_id))
    sev = ctx.config.severity_overrides.get(rule_id) or severity or spec.severity
    start = target.idx if hasattr(target, "idx") else target.start_char
    end = start + len(target.text)
    line, col = sent.block.position(start)
    end_line, end_col = sent.block.position(end)
    if end_line != line:
        # The target wraps onto a later source line; report up to the end of
        # the line the finding starts on (findings carry a single line).
        end_col = col + (_segment_end(sent.block, start) - start)
    return Finding(rule=rule_id, severity=sev, file=sent.block.file, line=line, col=col,
                   end_col=end_col, text=target.text, message=message,
                   suggestion=suggestion, fix=fix, context=" ".join(sent.text.split()))


def _segment_end(block: TextBlock, offset: int) -> int:
    """Offset in block.text just past the end of the source line containing ``offset``."""
    for seg in block.segments:
        if seg[0] > offset:
            return seg[0] - 1  # the joining space
    return len(block.text)


def _base(rule_id: str) -> str:
    if rule_id in RULES or rule_id in PARAGRAPH_RULES:
        return rule_id
    base = rule_id.split("-")[0]
    if base in RULES or base in PARAGRAPH_RULES:
        return base
    return "1.x"
