"""Rewrap the prose of a markdown file to 74 columns.

Usage: python3 rewrap.py FILE...

The script keeps a code block, a table, a heading and an inline code span
as they are. It does not end a line with an article, because the tagger of
ste-lint then reads the article as a pronoun.
"""

import re
import sys
import textwrap
from pathlib import Path

WIDTH = 74
NB = "\x00"
LIST_PREFIX = re.compile(r"^(- \[ \] |- |\d+\. )")
ARTICLE_AT_END = re.compile(r"^(.*\S) (the|a|an|The|A|An|no|No)$")


def protect(line: str) -> str:
    """Keep an inline code span and a link on one line."""
    line = re.sub(r"`[^`]*`", lambda m: m.group(0).replace(" ", NB), line)
    return re.sub(r"\[[^\]]*\]\([^)]*\)", lambda m: m.group(0).replace(" ", NB), line)


def wrap_block(block: list[str]) -> list[str]:
    block = [protect(l) for l in block]
    first = block[0]
    m = LIST_PREFIX.match(first)
    if m:
        prefix = m.group(1)
        indent = " " * len(prefix)
        if not all(l.startswith(indent) for l in block[1:]):
            return block
        text = " ".join([first[len(prefix):]] + [l[len(indent):] for l in block[1:]])
        return textwrap.wrap(text, width=WIDTH, initial_indent=prefix, subsequent_indent=indent,
                             break_long_words=False, break_on_hyphens=False)
    if any(re.match(r"^(\s|#|\||>|!|\[|<)", l) for l in block):
        return block
    return textwrap.wrap(" ".join(block), width=WIDTH, break_long_words=False, break_on_hyphens=False)


def rewrap(text: str) -> str:
    out: list[str] = []
    block: list[str] = []
    in_fence = False

    def flush() -> None:
        nonlocal block
        if block:
            out.extend(wrap_block(block))
            block = []

    for line in text.split("\n"):
        if line.startswith("```"):
            flush()
            in_fence = not in_fence
            out.append(line)
        elif in_fence:
            out.append(line)
        elif line.strip() == "":
            flush()
            out.append(line)
        else:
            if LIST_PREFIX.match(line) and block:
                flush()
            block.append(line)
    flush()

    lines = "\n".join(out).replace(NB, " ").split("\n")
    in_fence = False
    for i, line in enumerate(lines):
        if line.startswith("```"):
            in_fence = not in_fence
            continue
        if in_fence or line.startswith("|"):
            continue
        m = ARTICLE_AT_END.match(line)
        if m and i + 1 < len(lines) and lines[i + 1].strip() and not lines[i + 1].startswith("```"):
            indent = re.match(r"^\s*", lines[i + 1]).group(0)
            lines[i] = m.group(1)
            lines[i + 1] = indent + m.group(2) + " " + lines[i + 1].lstrip()
    return "\n".join(lines)


def main() -> None:
    if len(sys.argv) < 2:
        print(__doc__)
        raise SystemExit(2)
    for path in sys.argv[1:]:
        p = Path(path)
        p.write_text(rewrap(p.read_text()))


if __name__ == "__main__":
    main()
