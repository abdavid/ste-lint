"""Turn pdfplumber word boxes into column-tagged text lines for the Part 2 dictionary pages."""
from __future__ import annotations

import re
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Iterator

POS_RE = r"\((n|v|adj|adv|prep|conj|pron|art|TN|TV)\)"
POS_ONLY = re.compile(rf"^{POS_RE},?$")
HEADWORD = re.compile(rf"^(?P<w>[A-Za-z][^()]*?(?:\([^()]*\))?[^()]*?)\s*{POS_RE},?$")

BODY_TOP, BODY_BOTTOM = 90.0, 715.0
HEADER_TOP = 90.0
ROW_BUCKET = 3.0
COL_TOLERANCE = 4.0
WRAP_MAX_DY = 16.0
FIRST_DICTIONARY_PAGE = 148  # 0-based index of "Page 2-1-A1"


@dataclass(frozen=True)
class Line:
    y: float
    col: int
    text: str
    x0: float
    page: int


def column_bounds(words: list[dict]) -> list[float] | None:
    hdr: dict[int, float] = {}
    for w in words:
        if w["top"] >= HEADER_TOP:
            continue
        t = w["text"]
        if t == "Word":
            hdr[1] = w["x0"]
        elif t == "ALTERNATIVES":
            hdr[2] = w["x0"]
        elif t == "STE" and 3 not in hdr:
            hdr[3] = w["x0"]
        elif t == "Non-STE":
            hdr[4] = w["x0"]
    if len(hdr) != 4:
        return None
    return [hdr[2] - COL_TOLERANCE, hdr[3] - COL_TOLERANCE, hdr[4] - COL_TOLERANCE]


def _col_of(x0: float, bounds: list[float]) -> int:
    for i, b in enumerate(bounds, start=1):
        if x0 < b:
            return i
    return 4


def page_lines(words: list[dict], page: int) -> list[Line]:
    bounds = column_bounds(words)
    if bounds is None:
        return []
    rows: dict[tuple[int, int], list[dict]] = defaultdict(list)
    for w in words:
        if BODY_TOP < w["top"] < BODY_BOTTOM:
            rows[(round(w["top"] / ROW_BUCKET), _col_of(w["x0"], bounds))].append(w)
    raw: list[list | None] = []
    for (yb, col), ws in sorted(rows.items()):
        ws.sort(key=lambda w: w["x0"])
        raw.append([yb * ROW_BUCKET, col, " ".join(w["text"] for w in ws), ws[0]["x0"]])
    i = 0
    while i < len(raw):
        entry = raw[i]
        if entry is None:
            i += 1
            continue
        y, col, text, x0 = entry
        if col == 1 and not HEADWORD.match(text):
            j = i + 1
            while j < len(raw) and (raw[j] is None or raw[j][1] != 1):
                j += 1
            if j < len(raw) and POS_ONLY.match(raw[j][2]) and raw[j][0] - y < WRAP_MAX_DY:
                raw[j][2] = f"{text} {raw[j][2]}"
                raw[j][0], raw[j][3] = y, x0
                raw[i] = None
        i += 1
    merged = sorted((e for e in raw if e is not None), key=lambda r: (r[0], r[1]))
    return [Line(y=y, col=col, text=text, x0=x0, page=page) for y, col, text, x0 in merged]


def iter_dictionary_lines(pdf_path: Path) -> Iterator[Line]:
    import pdfplumber

    with pdfplumber.open(str(pdf_path)) as pdf:
        for idx in range(FIRST_DICTIONARY_PAGE, len(pdf.pages)):
            yield from page_lines(pdf.pages[idx].extract_words(), page=idx + 1)
