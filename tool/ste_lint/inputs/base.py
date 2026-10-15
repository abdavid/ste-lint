from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

KINDS = ("heading", "paragraph", "list_item", "table_cell", "string_value")
MODES = ("procedural", "descriptive")


@dataclass
class TextBlock:
    text: str
    kind: str
    file: str
    line: int
    col: int = 1
    mode: str | None = None
    key: str | None = None
    # One entry per source line that contributed to ``text`` when several
    # lines were joined into one block (wrapped paragraphs):
    # (offset of that line's first character in ``text``, source line, source col).
    # Empty for single-line blocks, which use ``line``/``col`` + offset.
    segments: list[tuple[int, int, int]] = field(default_factory=list)

    def position(self, offset: int) -> tuple[int, int]:
        """Map a character offset in ``text`` to a 1-based (line, col) in the source."""
        if not self.segments:
            return self.line, self.col + offset
        seg = self.segments[0]
        for cand in self.segments:
            if cand[0] <= offset:
                seg = cand
            else:
                break
        return seg[1], seg[2] + (offset - seg[0])


def join_lines(lines: list[tuple[str, int]]) -> tuple[str, list[tuple[int, int, int]]]:
    """Join raw source lines into one space-separated block text.

    ``lines`` is ``[(raw_line, line_number), ...]``. Each line is stripped; the
    returned segments record where each stripped line starts in the joined text
    and at which source column it began.
    """
    parts: list[str] = []
    segments: list[tuple[int, int, int]] = []
    offset = 0
    for raw, n in lines:
        stripped = raw.strip()
        lead = len(raw) - len(raw.lstrip())
        segments.append((offset, n, 1 + lead))
        parts.append(stripped)
        offset += len(stripped) + 1
    return " ".join(parts), segments


def shift_segments(segments: list[tuple[int, int, int]], lead: int) -> list[tuple[int, int, int]]:
    """Adjust segments after ``lead`` leading characters were stripped from the text."""
    return [(off - lead, line, col) for off, line, col in segments] if lead else list(segments)


def extract(path: Path) -> list[TextBlock]:
    suffix = path.suffix.lower()
    text = path.read_text(encoding="utf-8-sig")
    name = str(path)
    if suffix in (".md", ".markdown", ".mdx"):
        from .markdown import extract_markdown

        return extract_markdown(text, name)
    if suffix in (".json", ".yaml", ".yml", ".properties"):
        from .strings import extract_strings

        return extract_strings(text, name, suffix)
    from .plain import extract_plain

    return extract_plain(text, name)


def extract_text(text: str, file: str = "<stdin>", kind: str = "paragraph") -> list[TextBlock]:
    from .plain import extract_plain

    blocks = extract_plain(text, file)
    for b in blocks:
        b.kind = kind
    return blocks
