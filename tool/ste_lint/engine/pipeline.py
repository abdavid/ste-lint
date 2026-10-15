from __future__ import annotations

from functools import lru_cache

from ste_lint import SPACY_MODEL
from ste_lint.config import Config
from ste_lint.engine.findings import Finding
from ste_lint.engine.lexicon import Lexicon
from ste_lint.engine.registry import PARAGRAPH_RULES, RULES, RuleContext, Sentence
from ste_lint.inputs.base import TextBlock, extract_text


@lru_cache(maxsize=1)
def load_nlp():
    import spacy

    return spacy.load(SPACY_MODEL, disable=["ner"])


def _ensure_rules_loaded():
    from ste_lint.engine import rules  # noqa: F401  (imports register rules)


def block_mode(block: TextBlock, config: Config) -> str:
    if block.mode:
        return block.mode
    if block.kind == "string_value":
        return "procedural"
    return config.mode


def sentences_for(blocks: list[TextBlock], config: Config, nlp=None) -> list[Sentence]:
    nlp = nlp or load_nlp()
    out: list[Sentence] = []
    docs = nlp.pipe([b.text for b in blocks])
    for block, doc in zip(blocks, docs):
        mode = block_mode(block, config)
        for span in doc.sents:
            out.append(Sentence(span=span, block=block, mode=mode))
    return out


def run_rules(sentences: list[Sentence], ctx: RuleContext) -> list[Finding]:
    _ensure_rules_loaded()
    findings: list[Finding] = []
    for sent in sentences:
        for spec in RULES.values():
            if spec.id in ctx.config.disable:
                continue
            if sent.mode not in spec.modes:
                continue
            if spec.kinds and sent.block.kind not in spec.kinds:
                continue
            findings.extend(f for f in spec.fn(sent, ctx) if f is not None)

    by_block: dict[int, list[Sentence]] = {}
    order: list[int] = []
    for s in sentences:
        k = id(s.block)
        if k not in by_block:
            by_block[k] = []
            order.append(k)
        by_block[k].append(s)
    para_keys = [k for k in order if by_block[k][0].block.kind == "paragraph"]
    for idx, k in enumerate(para_keys):
        sents = by_block[k]
        for spec in PARAGRAPH_RULES.values():
            if spec.id in ctx.config.disable:
                continue
            if sents[0].mode not in spec.modes:
                continue
            findings.extend(f for f in spec.fn(sents, ctx, idx == 0, idx == len(para_keys) - 1) if f is not None)

    findings.sort(key=lambda f: (f.file, f.line, f.col, f.rule))
    return findings


def lint_blocks(blocks: list[TextBlock], lexicon: Lexicon, config: Config, nlp=None) -> list[Finding]:
    return run_rules(sentences_for(blocks, config, nlp), RuleContext(lexicon, config))


def lint_text(text: str, lexicon: Lexicon, config: Config, kind: str = "paragraph", file: str = "<stdin>") -> list[Finding]:
    return lint_blocks(extract_text(text, file=file, kind=kind), lexicon, config)
