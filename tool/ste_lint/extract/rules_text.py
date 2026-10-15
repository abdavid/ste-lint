from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path

from ste_lint import RULES_PATH

RULE_HEAD = re.compile(r"^\s*Rule (\d+\.\d+)\s+(.*)$")
SECTION_HEAD = re.compile(r"^\s*Section \d+ [–-] ")
FURNITURE = re.compile(r"^\s*(Issue 9|Page 1-|\d{4}-\d{2}-\d{2}|ASD-STE100 Simplified Technical English)")


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


def slice_part1(out: str) -> str:
    start = out.find("Section 1 – Words\nSummary of the rules")
    if start < 0:
        start = out.find("Summary of the rules")
    if start < 0:
        raise RuntimeError("Part 1 'Summary of the rules' anchor not found in PDF text")
    end = out.find("Part 2 – Dictionary\n", start)
    return out[start:end if end > 0 else None]


def extract_part1_text(pdf: Path) -> str:
    try:
        result = subprocess.run(
            ["pdftotext", "-layout", str(pdf), "-"], check=True, capture_output=True, text=True
        )
    except FileNotFoundError as e:
        raise RuntimeError("pdftotext not found — install poppler") from e
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"pdftotext failed: {e.stderr}") from e
    return slice_part1(result.stdout)


def build_rules(pdf: Path, out_path: Path = RULES_PATH) -> int:
    rules = parse_rules(extract_part1_text(pdf))
    out_path.write_text(json.dumps(rules, indent=1, ensure_ascii=False))
    return len(rules)


def load_rules() -> dict[str, dict]:
    if not RULES_PATH.exists():
        return {}
    return json.loads(RULES_PATH.read_text())
