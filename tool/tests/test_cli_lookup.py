import json

from typer.testing import CliRunner

from ste_lint import cli
from ste_lint.cli import app

runner = CliRunner()


def test_lookup_unapproved_word(lexicon, monkeypatch):
    monkeypatch.setattr(cli, "_lexicon", lambda: lexicon)

    r = runner.invoke(app, ["lookup", "consult"])

    assert r.exit_code == 0
    data = json.loads(r.output)
    assert data["status"] == "unapproved"
    assert data["entries"][0]["alternatives"][0]["word"] == "refer"


def test_lookup_pos_filter(lexicon, monkeypatch):
    monkeypatch.setattr(cli, "_lexicon", lambda: lexicon)

    r = runner.invoke(app, ["lookup", "test", "--pos", "v"])

    data = json.loads(r.output)
    assert [e["id"] for e in data["entries"]] == ["test/v"]


def test_lookup_status_mixed_when_some_senses_approved(lexicon, monkeypatch):
    monkeypatch.setattr(cli, "_lexicon", lambda: lexicon)

    r = runner.invoke(app, ["lookup", "test"])

    data = json.loads(r.output)
    assert data["status"] == "mixed"
    assert data["approved_pos"] == ["n"]


def test_lookup_status_approved_when_filtered_to_approved_sense(lexicon, monkeypatch):
    monkeypatch.setattr(cli, "_lexicon", lambda: lexicon)

    r = runner.invoke(app, ["lookup", "test", "--pos", "n"])

    data = json.loads(r.output)
    assert data["status"] == "approved"
    assert data["approved_pos"] == ["n"]


def test_lookup_status_unapproved_when_filtered_to_unapproved_sense(lexicon, monkeypatch):
    monkeypatch.setattr(cli, "_lexicon", lambda: lexicon)

    r = runner.invoke(app, ["lookup", "test", "--pos", "v"])

    data = json.loads(r.output)
    assert data["status"] == "unapproved"
    assert data["approved_pos"] == []


def test_lookup_unknown_word(lexicon, monkeypatch):
    monkeypatch.setattr(cli, "_lexicon", lambda: lexicon)

    r = runner.invoke(app, ["lookup", "zzzznotaword"])

    data = json.loads(r.output)
    assert data["status"] == "unknown"
    assert data["entries"] == []


def test_lookup_multiple_words_returns_list(lexicon, monkeypatch):
    monkeypatch.setattr(cli, "_lexicon", lambda: lexicon)

    r = runner.invoke(app, ["lookup", "consult", "the"])

    data = json.loads(r.output)
    assert isinstance(data, list)
    assert [d["query"] for d in data] == ["consult", "the"]


def test_lookup_batch_file(lexicon, monkeypatch, tmp_path):
    monkeypatch.setattr(cli, "_lexicon", lambda: lexicon)
    batch = tmp_path / "words.txt"
    batch.write_text("consult\nthe\n")

    r = runner.invoke(app, ["lookup", "--batch", str(batch)])

    data = json.loads(r.output)
    assert [d["query"] for d in data] == ["consult", "the"]


def test_lookup_batch_missing_file_exits_cleanly(lexicon, monkeypatch, tmp_path):
    monkeypatch.setattr(cli, "_lexicon", lambda: lexicon)
    missing = tmp_path / "nope.txt"

    r = runner.invoke(app, ["lookup", "--batch", str(missing)])

    assert r.exit_code == 2
    assert "Traceback" not in r.output


def test_suggest_lists_alternatives(lexicon, monkeypatch):
    monkeypatch.setattr(cli, "_lexicon", lambda: lexicon)

    r = runner.invoke(app, ["suggest", "consult"])

    data = json.loads(r.output)
    assert data == [
        {
            "id": "consult/v",
            "alternatives": [{"word": "refer", "pos": "v"}],
            "examples": {"ste": ["REFER TO THE MANUAL."], "non_ste": ["Consult the manual."]},
        }
    ]


def test_lookup_missing_dictionary_exits_2(monkeypatch):
    def boom():
        cli.typer.echo("nope", err=True)
        raise cli.typer.Exit(2)

    monkeypatch.setattr(cli, "_lexicon", boom)

    r = runner.invoke(app, ["lookup", "consult"])

    assert r.exit_code == 2
