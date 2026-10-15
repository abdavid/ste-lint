from __future__ import annotations

import json
import re
import sys

from .base import TextBlock

SKIP = re.compile(r"^(https?://|#[0-9a-fA-F]{3,8}$|[A-Z0-9_\-]+$|\{[^}]*\}$)")


def _prose(v: str) -> bool:
    return isinstance(v, str) and len(v.split()) >= 2 and not SKIP.match(v.strip())


def _leaves(obj, prefix=""):
    if isinstance(obj, dict):
        for k, v in obj.items():
            yield from _leaves(v, f"{prefix}.{k}" if prefix else str(k))
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            yield from _leaves(v, f"{prefix}[{i}]")
    elif _prose(obj):
        yield prefix, obj


def _locate(lines: list[str], candidates: list[str], start: int) -> int:
    """Find the line (1-based) containing one of candidates, scanning from start.

    Each candidate is tried in order across the full remaining range before the
    next candidate is tried, so a raw-encoded candidate (e.g. JSON escapes) is
    preferred over a decoded fallback even if the fallback would match earlier.
    """
    for candidate in candidates:
        if not candidate:
            continue
        for i in range(start, len(lines)):
            if candidate in lines[i]:
                return i + 1
    return start + 1


def extract_strings(text: str, file: str, suffix: str) -> list[TextBlock]:
    lines = text.splitlines()
    blocks: list[TextBlock] = []
    if suffix == ".properties":
        for i, line in enumerate(lines, start=1):
            if not line.strip() or line.lstrip().startswith(("#", "!")):
                continue
            m = re.match(r"^\s*([^=:]+?)\s*[=:]\s*(.*)$", line)
            if m and _prose(m.group(2)):
                blocks.append(TextBlock(m.group(2).strip(), "string_value", file, i, len(line) - len(m.group(2)) + 1, None, m.group(1)))
        return blocks
    if suffix == ".json":
        try:
            data = json.loads(text)
        except json.JSONDecodeError as e:
            print(f"warning: {file}: cannot parse: {e}", file=sys.stderr)
            return []
    else:
        import yaml

        try:
            data = yaml.safe_load(text)
        except yaml.YAMLError as e:
            print(f"warning: {file}: cannot parse: {e}", file=sys.stderr)
            return []
    cursor = 0
    for key, value in _leaves(data):
        first_line = value.splitlines()[0]
        # JSON re-encodes escapes (e.g. `"` -> `\"`) in the source; search for the
        # raw encoded form first, falling back to the decoded value for YAML (which
        # has no such escaping) or when the raw form isn't found verbatim.
        candidates = [json.dumps(value)[1:-1], first_line] if suffix == ".json" else [first_line]
        line = _locate(lines, candidates, cursor)
        cursor = line  # resume the next scan *after* this match, not on the same line
        line_text = lines[line - 1] if line - 1 < len(lines) else ""
        match = next((c for c in candidates if c and c in line_text), first_line)
        col = line_text.find(match) + 1 if match in line_text else 1
        blocks.append(TextBlock(" ".join(value.split()), "string_value", file, line, max(col, 1), None, key))
    return blocks
