from __future__ import annotations

from ste_lint.engine.findings import Finding
from ste_lint.engine.posmap import is_skippable, ste_pos
from ste_lint.engine.registry import RuleContext, Sentence, make_finding, rule


def _fmt_alts(entry) -> str:
    return ", ".join(f"{a.word.upper()}{f' ({a.pos})' if a.pos else ''}" for a in entry.alternatives) or "(see dictionary)"


@rule("1.x", severity="error")
def check_words(sent: Sentence, ctx: RuleContext) -> list[Finding]:
    out: list[Finding] = []
    lex = ctx.lexicon
    for tok in sent.span:
        if is_skippable(tok):
            continue
        pos = ste_pos(tok)
        if pos is None:
            continue
        lower, lemma = tok.text.lower(), tok.lemma_.lower()
        if ctx.config.is_allowed(lemma, pos) or ctx.config.is_allowed(lower, pos):
            continue
        entries = lex.by_form(lower)
        form_miss = False
        if not entries:
            entries = lex.by_lemma(lemma)
            form_miss = True
        if not entries:
            out.append(make_finding(sent, ctx, "1.1-unknown", tok,
                                    f"'{tok.text}' is not in the STE dictionary. Approved word, technical noun/verb, or typo?",
                                    severity="warning"))
            continue
        if tok.tag_ == "VBG":
            continue  # rule 3.5 owns -ing forms
        approved_same = [e for e in entries if e.approved and e.pos == pos]
        approved_any = [e for e in entries if e.approved]
        if approved_same:
            e = approved_same[0]
            if form_miss and e.pos in ("v", "adj") and lower not in e.forms:
                out.append(make_finding(sent, ctx, "1.4", tok,
                                        f"'{tok.text}' is not an approved form of {e.word.upper()} ({e.pos}). Approved forms: {', '.join(f.upper() for f in e.forms)}."))
            continue
        if approved_any:
            poses = ", ".join(sorted({e.pos for e in approved_any}))
            ambiguous = tok.pos_ in ("NOUN", "VERB") and any(e.pos in ("n", "v") for e in approved_any)
            msg = f"'{tok.text}' is approved only as {poses}, not as {pos}."
            unapproved_same = [e for e in entries if not e.approved and e.pos == pos]
            if unapproved_same:
                msg += f" Use: {_fmt_alts(unapproved_same[0])}"
            out.append(make_finding(sent, ctx, "1.2", tok, msg + (" (POS tag may be wrong)" if ambiguous else ""),
                                    severity="warning" if ambiguous else None))
            continue
        same_pos = [x for x in entries if x.pos == pos]
        if not same_pos:
            # The dictionary has entries for this word, but none for the part
            # of speech it is used as here (e.g. "fuel"/"contaminated" only
            # listed as an unapproved verb/adjective, used here as a noun).
            # We have no information on this sense, so don't claim it is
            # "not approved" and suggest an alternative for a different word
            # sense (misleading) -- treat it like an unknown word instead.
            out.append(make_finding(sent, ctx, "1.1-unknown", tok,
                                    f"'{tok.text}' is not in the STE dictionary as {pos}. Approved word, technical noun/verb, or typo?",
                                    severity="warning"))
            continue
        e = same_pos[0]
        alts = e.alternatives
        fix = alts[0].word if len(alts) == 1 and (alts[0].pos in (None, pos)) and " " not in alts[0].word else None
        out.append(make_finding(sent, ctx, "1.1", tok,
                                f"'{tok.text}' ({e.pos}) is not approved. Use: {_fmt_alts(e)}",
                                suggestion=alts[0].word if alts else None, fix=fix))
    return out
