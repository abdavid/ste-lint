from ste_lint.extract.pdf_words import Line, column_bounds, page_lines


def w(text, x0, top):
    return {"text": text, "x0": x0, "top": top}


HEADER = [w("Word", 72, 66.5), w("ALTERNATIVES", 180, 78.1), w("STE", 309.6, 78.1),
          w("EXAMPLE", 331.9, 78.1), w("Non-STE", 439.3, 78.1)]


def test_column_bounds_from_header():
    assert column_bounds(HEADER) == [176.0, 305.6, 435.3]


def test_column_bounds_missing_header():
    assert column_bounds([w("x", 72, 100)]) is None


def test_page_lines_groups_rows_and_columns():
    words = HEADER + [
        w("ABOUT", 72, 95.8), w("(prep)", 114, 95.8),
        w("Concerned", 180, 95.8), w("with", 237, 95.8),
        w("FOR", 309.6, 95.8), w("DATA", 336, 95.8),
        w("LOCATION", 309.6, 107.8),
    ]
    lines = page_lines(words, page=149)
    assert lines[0] == Line(y=96.0, col=1, text="ABOUT (prep)", x0=72, page=149)
    assert [l.text for l in lines] == ["ABOUT (prep)", "Concerned with", "FOR DATA", "LOCATION"]


def test_page_lines_merges_wrapped_pos():
    words = HEADER + [
        w("ACCIDENTAL", 72, 95.8),
        w("(adj)", 72, 107.8),
        w("That", 180, 95.8),
    ]
    lines = page_lines(words, page=149)
    assert [l.text for l in lines if l.col == 1] == ["ACCIDENTAL (adj)"]


def test_page_lines_wrapped_pos_keeps_reading_order():
    words = HEADER + [
        w("ACCIDENTAL", 72, 95.8),
        w("(adj)", 72, 107.8),
        w("That", 180, 95.8),
    ]
    lines = page_lines(words, page=149)
    assert [(l.col, l.text) for l in lines] == [(1, "ACCIDENTAL (adj)"), (2, "That")]


def test_page_lines_ignores_footer():
    words = HEADER + [w("ABOUT", 72, 95.8), w("(prep)", 114, 95.8), w("Issue", 72, 725.9), w("9", 100, 725.9)]
    assert [l.text for l in page_lines(words, page=1)] == ["ABOUT (prep)"]
