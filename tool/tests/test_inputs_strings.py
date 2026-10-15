from ste_lint.inputs.strings import extract_strings

JSON = '{\n "title": "Remove the cover",\n "count": 3,\n "nested": {"help": "Consult the manual before you start", "id": "ABC123", "color": "#fff"},\n "list": ["Tighten the screw", "x"]\n}'


def test_json_leaves():
    blocks = extract_strings(JSON, "a.json", ".json")
    assert [(b.key, b.line, b.text) for b in blocks] == [
        ("title", 2, "Remove the cover"),
        ("nested.help", 4, "Consult the manual before you start"),
        ("list[0]", 5, "Tighten the screw"),
    ]
    assert all(b.kind == "string_value" for b in blocks)


def test_yaml_and_properties():
    y = "a:\n  b: Remove the cover\nc: 5\n"
    assert [(b.key, b.line) for b in extract_strings(y, "a.yml", ".yml")] == [("a.b", 2)]
    p = "# c\nhello.msg=Remove the cover\nid=42\n"
    assert [(b.key, b.line, b.text) for b in extract_strings(p, "a.properties", ".properties")] == [("hello.msg", 2, "Remove the cover")]


def test_malformed_json_returns_empty_and_warns(capsys):
    blocks = extract_strings("{not valid json", "bad.json", ".json")
    assert blocks == []
    err = capsys.readouterr().err
    assert "warning: bad.json: cannot parse:" in err


def test_malformed_yaml_returns_empty_and_warns(capsys):
    blocks = extract_strings("a: [unclosed\n  - b: c\n", "bad.yaml", ".yaml")
    assert blocks == []
    err = capsys.readouterr().err
    assert "warning: bad.yaml: cannot parse:" in err


def test_duplicate_values_get_distinct_lines():
    j = '{\n "a": "Remove the cover",\n "b": "Remove the cover"\n}'
    blocks = extract_strings(j, "dup.json", ".json")
    assert [(b.key, b.line) for b in blocks] == [("a", 2), ("b", 3)]


def test_json_escaped_value_located_via_raw_encoding():
    j = '{\n "msg": "Say \\"hi\\" to everyone"\n}'
    blocks = extract_strings(j, "esc.json", ".json")
    assert blocks[0].line == 2
