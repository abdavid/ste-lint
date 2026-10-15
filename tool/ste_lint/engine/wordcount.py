from __future__ import annotations

from ste_lint.engine.posmap import UNIT, hyphen_chain_len


def count_words(span) -> int:
    """STE 8.6 word count.

    - a hyphenated compound (e.g. "self-locking") counts as one word
    - a number immediately followed by a unit (e.g. "5 Nm") counts as one word
    - a contraction split by the tokenizer (e.g. "do" + "n't") counts as one word
    - punctuation counts as zero words
    - everything else (placeholders, abbreviations, part numbers, ...) is a single
      token already, so it naturally counts as one word
    """
    toks = [t for t in span if not t.is_space]
    n, i = 0, 0
    length = len(toks)
    while i < length:
        t = toks[i]
        if t.is_punct:
            i += 1
            continue
        n += 1
        if t.like_num and i + 1 < length and UNIT.match(toks[i + 1].text):
            i += 2
            continue
        i += hyphen_chain_len(toks, i)
        # a contraction fragment glued to the previous token, e.g. "do" + "n't"
        if i < length and toks[i - 1].whitespace_ == "" and "'" in toks[i].text:
            i += 1
    return n
