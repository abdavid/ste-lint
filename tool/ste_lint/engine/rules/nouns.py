from __future__ import annotations

from types import SimpleNamespace

from ste_lint.engine.findings import Finding
from ste_lint.engine.posmap import PLACEHOLDERS, hyphen_chain_len
from ste_lint.engine.registry import RuleContext, Sentence, make_finding, rule

MAX_NOUNS = 3


def _units(sent: Sentence, ctx: RuleContext) -> list[list]:
    """Group tokens into units: allowlisted multi-word technical nouns become one unit,
    and hyphenated compounds (e.g. 'self-locking') are merged into one unit."""
    toks = list(sent.span)
    covered: dict[int, int] = {}  # token index -> unit length
    for item in ctx.config.technical_nouns:
        term = item.partition("/")[0].lower()
        if " " not in term:
            continue
        words = term.split()
        for i in range(len(toks) - len(words) + 1):
            if [t.lower_ for t in toks[i:i + len(words)]] == words:
                covered[i] = len(words)
    units, i = [], 0
    while i < len(toks):
        n = covered.get(i) or hyphen_chain_len(toks, i)
        units.append(toks[i:i + n])
        i += n
    return units


@rule("2.1", severity="error")
def check_noun_cluster(sent: Sentence, ctx: RuleContext) -> list[Finding]:
    out = []
    run: list[list] = []

    def flush():
        if len(run) > MAX_NOUNS:
            first, last = run[0][0], run[-1][-1]
            cluster = sent.span.doc.text[first.idx:last.idx + len(last.text)]
            span = SimpleNamespace(idx=first.idx, text=cluster)
            out.append(make_finding(sent, ctx, "2.1", span,
                                    f"Noun cluster of {len(run)} words: '{cluster}'. Use no more than three nouns in a cluster; rewrite with prepositions or hyphens."))

    for unit in _units(sent, ctx):
        first, last = unit[0], unit[-1]
        is_noun = (
            (first.pos_ in ("NOUN", "PROPN") or last.pos_ in ("NOUN", "PROPN"))
            and first.text not in PLACEHOLDERS
            and last.text not in PLACEHOLDERS
        )
        if is_noun:
            run.append(unit)
        else:
            flush()
            run = []
    flush()
    return out
