from pathlib import Path

from ste_lint.engine.findings import Finding
from ste_lint.inputs.base import TextBlock, extract, extract_text
from ste_lint.inputs.markdown import clean_inline, extract_markdown
from ste_lint.inputs.plain import extract_plain

MD = """---
title: x
ste_mode: procedural
---
# Remove the cover

Remove the four screws. Then remove the cover.

- Tighten the `bolt` to 5 Nm
- See https://example.com/x for details

```bash
consult the docs
```

<!-- ste:mode descriptive -->
The pump | is | dirty.

| Part | Qty |
|------|-----|
| Pump | 2   |
"""


def test_markdown_blocks(tmp_path: Path):
    p = tmp_path / "a.md"
    p.write_text(MD)
    blocks = extract(p)
    kinds = [(b.kind, b.line, b.mode) for b in blocks]
    assert kinds[0] == ("heading", 5, "procedural")
    assert blocks[0].text == "Remove the cover"
    assert kinds[1] == ("paragraph", 7, "procedural")
    assert blocks[2].kind == "list_item" and blocks[2].col == 3 and blocks[2].text == "Tighten the CODE   to 5 Nm"
    assert blocks[3].text == "See URL" + " " * 19 + "for details"
    assert all("consult" not in b.text for b in blocks)
    assert blocks[4].mode == "descriptive" and blocks[4].kind == "paragraph"
    assert [b.text for b in blocks if b.kind == "table_cell"] == ["Part", "Qty", "Pump", "2"]


def test_unterminated_front_matter_is_not_swallowed():
    md = "---\ntitle: x\n# Heading\n\nSome paragraph.\n"
    blocks = extract_markdown(md, "a.md")
    assert any(b.kind == "heading" and b.text == "Heading" for b in blocks)
    assert any(b.kind == "paragraph" and b.text == "Some paragraph." for b in blocks)


def test_clean_inline_preserves_length():
    s = "See `code` at https://example.com/x and [text](http://y) plus *em* end."
    assert len(clean_inline(s)) == len(s)


def test_plain(tmp_path: Path):
    p = tmp_path / "a.txt"
    p.write_text("First para line one\nline two.\n\nSecond.\n")
    blocks = extract(p)
    assert [(b.line, b.text) for b in blocks] == [(1, "First para line one line two."), (4, "Second.")]


def test_extract_text():
    [b] = extract_text("Hello there.")
    assert b == TextBlock(text="Hello there.", kind="paragraph", file="<stdin>", line=1, col=1, mode=None, key=None,
                          segments=[(0, 1, 1)])


def test_plain_wrapped_paragraph_segments():
    [b] = extract_plain("First line\n  second line\nthird.\n", "a.txt")
    assert b.text == "First line second line third."
    assert b.segments == [(0, 1, 1), (11, 2, 3), (23, 3, 1)]
    assert b.position(0) == (1, 1)
    assert b.position(11) == (2, 3)      # "second" starts at col 3 on line 2
    assert b.position(18) == (2, 10)     # "line" on line 2
    assert b.position(23) == (3, 1)


def test_markdown_wrapped_paragraph_segments_survive_inline_cleanup():
    md = "Intro text\n![img](x.png) then *more* words\nlast line.\n"
    [b] = extract_markdown(md, "a.md")
    # clean_inline keeps lengths, so segment offsets still line up with the source.
    assert b.segments[1][1:] == (2, 1) and b.segments[2][1:] == (3, 1)
    off = b.text.index("last")
    assert b.position(off) == (3, 1)


def test_bom_is_stripped(tmp_path: Path):
    p = tmp_path / "bom.md"
    p.write_bytes("\ufeffRemove the cover.\n".encode("utf-8"))
    [b] = extract(p)
    assert b.text == "Remove the cover." and b.col == 1


def test_finding_to_dict():
    f = Finding(rule="1.1", severity="error", file="a.md", line=3, col=5, end_col=12, text="consult", message="m")
    d = f.to_dict()
    assert d["rule"] == "1.1" and d["suggestion"] is None and list(d)[0] == "rule"
