from __future__ import annotations

from .base import TextBlock, join_lines


def extract_plain(text: str, file: str) -> list[TextBlock]:
    blocks: list[TextBlock] = []
    buf: list[tuple[str, int]] = []

    def flush():
        nonlocal buf
        if buf:
            joined, segments = join_lines(buf)
            blocks.append(TextBlock(joined, "paragraph", file, buf[0][1], segments=segments))
            buf = []

    for i, line in enumerate(text.splitlines(), start=1):
        if line.strip():
            buf.append((line, i))
        else:
            flush()
    flush()
    return blocks
