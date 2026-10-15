from __future__ import annotations

import re

from .base import TextBlock, join_lines, shift_segments

FENCE = re.compile(r"^(```|~~~)")
HEADING = re.compile(r"^(#{1,6})\s+(.*?)\s*#*$")
LIST_ITEM = re.compile(r"^(\s*)([-*+]|\d+[.)])\s+(.*)$")
MODE_COMMENT = re.compile(r"<!--\s*ste:mode\s+(procedural|descriptive)\s*-->")
TABLE_ROW = re.compile(r"^\s*\|.*\|\s*$")
TABLE_SEP = re.compile(r"^\s*\|?\s*:?-{2,}:?\s*(\|\s*:?-{2,}:?\s*)*\|?\s*$")
INLINE_CODE = re.compile(r"`[^`]*`")
URL = re.compile(r"https?://\S+")
LINK = re.compile(r"\[([^\]]*)\]\([^)]*\)")
IMAGE = re.compile(r"!\[[^\]]*\]\([^)]*\)")
EMPHASIS = re.compile(r"[*_]{1,3}(\S.*?\S|\S)[*_]{1,3}")
HRULE = ("---", "***")


def _pad(replacement: str, span_len: int) -> str:
    """Pad (or truncate) replacement with trailing spaces to match the original span length.

    A span shorter than the replacement becomes underscores, which the tokenizer
    skips, so a truncated placeholder such as "COD" never reaches the rules."""
    if len(replacement) > span_len:
        return "_" * span_len
    if len(replacement) == span_len:
        return replacement
    return replacement + " " * (span_len - len(replacement))


def clean_inline(s: str) -> str:
    """Replace inline markdown constructs with source-length-preserving placeholders.

    Every substitution keeps len(result) == len(match) so that character offsets
    within the string (used for block.col + char_index) stay accurate. Does NOT
    strip the result — stripping (with col adjustment) is the caller's job.
    """

    def image_repl(m: re.Match[str]) -> str:
        return " " * len(m.group(0))

    s = IMAGE.sub(image_repl, s)

    def link_repl(m: re.Match[str]) -> str:
        return _pad(m.group(1), len(m.group(0)))

    s = LINK.sub(link_repl, s)

    def code_repl(m: re.Match[str]) -> str:
        return _pad("CODE", len(m.group(0)))

    s = INLINE_CODE.sub(code_repl, s)

    def url_repl(m: re.Match[str]) -> str:
        return _pad("URL", len(m.group(0)))

    s = URL.sub(url_repl, s)

    def emphasis_repl(m: re.Match[str]) -> str:
        whole = m.group(0)
        inner = m.group(1)
        start = whole.find(inner)
        end = start + len(inner)
        return (" " * start) + inner + (" " * (len(whole) - end))

    s = EMPHASIS.sub(emphasis_repl, s)
    return s


def _finalize(text: str, col: int) -> tuple[str, int]:
    """Strip whitespace at block level: leading strip advances col by the same amount;
    trailing strip is offset-safe since nothing follows it."""
    lstripped = text.lstrip()
    lead = len(text) - len(lstripped)
    return lstripped.rstrip(), col + lead


def extract_markdown(text: str, file: str) -> list[TextBlock]:
    lines = text.splitlines()
    blocks: list[TextBlock] = []
    mode: str | None = None
    i = 0
    if lines and lines[0].strip() == "---":
        j = 1
        while j < len(lines) and lines[j].strip() != "---":
            m = re.match(r"^\s*ste_mode:\s*(procedural|descriptive)\s*$", lines[j])
            if m:
                mode = m.group(1)
            j += 1
        if j < len(lines):
            # closing '---' found: this is real front matter.
            i = j + 1
        else:
            # no closing '---': not front matter after all, don't swallow the document.
            # Reparse from line 1; the lone leading '---' is treated as a horizontal
            # rule below (and skipped) rather than as content.
            mode = None
            i = 0
    buf: list[tuple[str, int]] = []

    def flush():
        nonlocal buf
        if buf:
            joined, segments = join_lines(buf)
            txt, col = _finalize(clean_inline(joined), 1)
            blocks.append(TextBlock(txt, "paragraph", file, buf[0][1], col, mode,
                                    segments=shift_segments(segments, col - 1)))
            buf = []

    in_fence = None
    while i < len(lines):
        line = lines[i]
        n = i + 1
        i += 1
        if in_fence:
            if FENCE.match(line) and line.startswith(in_fence):
                in_fence = None
            continue
        fm = FENCE.match(line)
        if fm:
            flush()
            in_fence = fm.group(1)
            continue
        mc = MODE_COMMENT.search(line)
        if mc:
            flush()
            mode = mc.group(1)
            continue
        if line.startswith("    ") and not buf:
            continue
        if not line.strip():
            flush()
            continue
        if line.strip() in HRULE:
            flush()
            continue
        hm = HEADING.match(line)
        if hm:
            flush()
            txt, col = _finalize(clean_inline(hm.group(2)), len(hm.group(1)) + 2)
            blocks.append(TextBlock(txt, "heading", file, n, col, mode))
            continue
        lm = LIST_ITEM.match(line)
        if lm:
            flush()
            base_col = len(lm.group(1)) + len(lm.group(2)) + 2
            txt, col = _finalize(clean_inline(lm.group(3)), base_col)
            blocks.append(TextBlock(txt, "list_item", file, n, col, mode))
            continue
        if TABLE_ROW.match(line):
            flush()
            if TABLE_SEP.match(line):
                continue
            pos = 0
            for cell in line.strip().strip("|").split("|"):
                pos = line.find(cell, pos)
                txt, col = _finalize(clean_inline(cell), pos + 1)
                if txt:
                    blocks.append(TextBlock(txt, "table_cell", file, n, col, mode))
                pos += len(cell) + 1
            continue
        buf.append((line, n))
    flush()
    return blocks
