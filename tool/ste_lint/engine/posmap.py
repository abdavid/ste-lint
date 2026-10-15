from __future__ import annotations

import re

PLACEHOLDERS = {"CODE", "URL"}
CODE_LIKE = re.compile(r"[\d_/\\#@]|^[A-Z]{2,}\d|^\w+-\w+-")
UNIT = re.compile(
    r"^(nm|n|kn|kg|g|mg|mm|cm|m|km|l|ml|liters?|litres?|psi|bar|mbar|kpa|mpa|pa|v|kv|mv|a|ma|w|kw|"
    r"hz|khz|mhz|°c|°f|c|f|k|%|in|ft|lb|lbs|oz|s|sec|ms|min|h|hr|hrs|rpm|db|mph|kph)\.?$",
    re.I,
)

_MAP = {
    "NOUN": "n", "PROPN": "n", "VERB": "v", "AUX": "v", "ADJ": "adj", "ADV": "adv",
    "ADP": "prep", "CCONJ": "conj", "SCONJ": "conj", "PRON": "pron", "DET": "art",
    "PART": "adv", "INTJ": None, "PUNCT": None, "NUM": None, "SYM": None, "SPACE": None, "X": None,
}


def ste_pos(token) -> str | None:
    if token.pos_ == "DET" and token.lower_ not in ("a", "an", "the"):
        return "adj"
    if token.tag_ == "PRP$":
        # Possessive determiners ("its", "your", "their", "his", "her", "our",
        # "my") are tagged PRON by spaCy, but STE classifies them as
        # adjectives, not pronouns.
        return "adj"
    if token.pos_ == "PART" and token.lower_ == "to":
        return "prep"
    if token.pos_ == "PART" and token.lower_ == "not":
        return "adv"
    if token.lower_ == "than":
        # spaCy tags "than" ADP in the extremely common comparative pattern
        # ("more/less than N units"), even though the dictionary approves
        # "than" only as a conjunction -- STE treats these comparatives as
        # elliptical clauses, not prepositional phrases.
        return "conj"
    return _MAP.get(token.pos_)


def hyphen_chain_len(toks: list, i: int) -> int:
    """Length of a hyphenated chain (e.g. 'self-locking' -> 'self', '-', 'locking')
    starting at token index i, merging repeated 'a-b-c' chains. Returns 1 if no chain."""
    n = len(toks)
    j = i
    while (
        j + 2 < n
        and toks[j].whitespace_ == ""
        and toks[j + 1].text == "-"
        and toks[j + 1].whitespace_ == ""
    ):
        j += 2
    return j - i + 1


def is_skippable(token) -> bool:
    t = token.text
    if token.is_punct or token.is_space or token.like_num or token.like_url or token.like_email:
        return True
    if t in PLACEHOLDERS or CODE_LIKE.search(t):
        return True
    if not any(ch.isalpha() for ch in t):
        return True
    if UNIT.match(t) and token.i > 0:
        prev = token.doc[token.i - 1]
        if prev.like_num or re.match(r"^\d", prev.text):
            return True
    return False
