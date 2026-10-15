from __future__ import annotations

import json
import re
import statistics
from pathlib import Path

from ste_lint import RULES_PATH

RULE_HEAD = re.compile(r"^\s*Rule (\d+\.\d+)\s+(.*)$")
SECTION_HEAD = re.compile(r"^\s*Section \d+ [–-] ")
FURNITURE = re.compile(r"^\s*(Issue 9|Page 1-|\d{4}-\d{2}-\d{2}|ASD-STE100 Simplified Technical English)")
START_ANCHOR = "Summary of the rules"
END_ANCHOR = "Part 2 – Dictionary\n"
ROW_TOLERANCE = 3.0


def parse_rules(text: str) -> dict[str, dict]:
    lines = [l.rstrip() for l in text.splitlines() if not FURNITURE.match(l)]
    starts: dict[str, tuple[int, str]] = {}
    for i, l in enumerate(lines):
        m = RULE_HEAD.match(l)
        if m:
            starts[m.group(1)] = (i, m.group(2).strip())  # last occurrence wins
    rules: dict[str, dict] = {}
    for rid, (start, title) in starts.items():
        body: list[str] = []
        for l in lines[start + 1:]:
            if RULE_HEAD.match(l) or SECTION_HEAD.match(l):
                break
            body.append(l)
        rules[rid] = {"id": rid, "title": title, "body": "\n".join(body).strip()}
    return rules


def _part1_bounds(out: str) -> tuple[int, int]:
    start = out.find(f"Section 1 – Words\n{START_ANCHOR}")
    if start < 0:
        start = out.find(START_ANCHOR)
    return start, (out.find(END_ANCHOR, start) if start >= 0 else -1)


def slice_part1(out: str) -> str:
    start, end = _part1_bounds(out)
    if start < 0:
        raise RuntimeError(f"Part 1 '{START_ANCHOR}' anchor not found in PDF text")
    return out[start:end if end > 0 else None]


def page_text(words: list[dict]) -> str:
    """Lay out pdfplumber words as plain text, keeping indentation, column gaps and blank lines."""
    if not words:
        return ""
    char_w = statistics.median((w["x1"] - w["x0"]) / len(w["text"]) for w in words)
    left = min(w["x0"] for w in words)
    rows: list[list] = []  # [top, bottom, words]
    for w in sorted(words, key=lambda w: (w["top"], w["x0"])):
        if rows and abs(rows[-1][0] - w["top"]) <= ROW_TOLERANCE:
            rows[-1][1] = max(rows[-1][1], w["bottom"])
            rows[-1][2].append(w)
        else:
            rows.append([w["top"], w["bottom"], [w]])
    lines: list[str] = []
    prev_bottom = None
    for top, bottom, row in rows:
        if prev_bottom is not None and top - prev_bottom > 0.9 * (bottom - top):
            lines.append("")
        line, prev_x1 = "", 0.0
        for w in sorted(row, key=lambda w: w["x0"]):
            col = round((w["x0"] - left) / char_w)
            if line and w["x0"] - prev_x1 < 2 * char_w:
                line += " "
            elif len(line) < col:
                line = line.ljust(col)
            elif line:
                line += " "
            line += w["text"]
            prev_x1 = w["x1"]
        lines.append(line.rstrip())
        prev_bottom = bottom
    return "\n".join(lines)


def extract_part1_text(pdf: Path) -> str:
    import pdfplumber

    pages: list[str] = []
    with pdfplumber.open(pdf) as doc:
        for page in doc.pages:
            pages.append(page_text(page.extract_words(x_tolerance=1.5, y_tolerance=2)))
            text = "\f".join(pages)
            if _part1_bounds(text)[1] > 0:
                break
    return slice_part1(text)


def build_rules(pdf: Path, out_path: Path = RULES_PATH) -> int:
    rules = parse_rules(extract_part1_text(pdf))
    out_path.write_text(json.dumps(rules, indent=1, ensure_ascii=False))
    return len(rules)


def load_rules() -> dict[str, dict]:
    if not RULES_PATH.exists():
        return {}
    return json.loads(RULES_PATH.read_text())
