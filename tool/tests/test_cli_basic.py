import json

from typer.testing import CliRunner

import ste_lint.extract.dictionary as dictionary_mod
from ste_lint import __version__, cli
from ste_lint.cli import app

runner = CliRunner()


def test_version():
    r = runner.invoke(app, ["--version"])
    assert r.exit_code == 0
    assert r.output.strip() == __version__


def test_doctor_reports_keys():
    r = runner.invoke(app, ["doctor"])
    assert '"spacy_model"' in r.output
    assert '"dictionary"' in r.output


def test_doctor_happy_path_exits_0(tmp_path, monkeypatch):
    dictionary_path = tmp_path / "dictionary.json"
    rules_path = tmp_path / "rules.json"
    dictionary_path.touch()
    rules_path.touch()
    monkeypatch.setattr(cli, "DICTIONARY_PATH", dictionary_path)
    monkeypatch.setattr(cli, "RULES_PATH", rules_path)

    r = runner.invoke(app, ["doctor"])

    data = json.loads(r.output)
    assert data["rules"] is True
    assert data["dictionary"] is True
    assert data["spacy_model"] is True
    assert r.exit_code == 0


def test_doctor_reports_uv_and_pdftotext_informationally(tmp_path, monkeypatch):
    dictionary_path = tmp_path / "dictionary.json"
    rules_path = tmp_path / "rules.json"
    dictionary_path.touch()
    rules_path.touch()
    monkeypatch.setattr(cli, "DICTIONARY_PATH", dictionary_path)
    monkeypatch.setattr(cli, "RULES_PATH", rules_path)
    monkeypatch.setattr(cli.shutil, "which", lambda name: None)

    r = runner.invoke(app, ["doctor"])

    data = json.loads(r.output)
    assert data["uv"] is False and data["pdftotext"] is False
    assert r.exit_code == 0  # missing build tools never fail doctor


def test_doctor_missing_data_exits_2(tmp_path, monkeypatch):
    dictionary_path = tmp_path / "dictionary.json"
    rules_path = tmp_path / "rules.json"
    monkeypatch.setattr(cli, "DICTIONARY_PATH", dictionary_path)
    monkeypatch.setattr(cli, "RULES_PATH", rules_path)
    monkeypatch.setattr(cli, "SPACY_MODEL", "bogus-model-name-not-installed")

    r = runner.invoke(app, ["doctor"])

    data = json.loads(r.output)
    assert data["rules"] is False
    assert data["dictionary"] is False
    assert data["spacy_model"] is False
    assert r.exit_code == 2


def test_build_dictionary_success_exits_0(tmp_path, monkeypatch):
    pdf = tmp_path / "dict.pdf"
    pdf.touch()
    report = {"entries": 3, "approved": 2, "unapproved": 1, "with_notes": [], "problems": []}
    monkeypatch.setattr(dictionary_mod, "build", lambda pdf, out_dir: report)

    r = runner.invoke(app, ["build-dictionary", str(pdf)])

    assert r.exit_code == 0
    assert json.loads(r.stdout) == report
    assert "Do not commit, publish, or redistribute" in r.stderr


def test_build_dictionary_problems_exits_2(tmp_path, monkeypatch):
    pdf = tmp_path / "dict.pdf"
    pdf.touch()
    report = {"entries": 3, "approved": 2, "unapproved": 1, "with_notes": [], "problems": ["bad/n: empty pos"]}
    monkeypatch.setattr(dictionary_mod, "build", lambda pdf, out_dir: report)

    r = runner.invoke(app, ["build-dictionary", str(pdf)])

    assert r.exit_code == 2
    assert json.loads(r.stdout) == report
    assert "BUILD PROBLEMS" in r.stderr


def test_build_dictionary_runtime_error_exits_2(tmp_path, monkeypatch):
    pdf = tmp_path / "dict.pdf"
    pdf.touch()

    def raise_boom(pdf, out_dir):
        raise RuntimeError("boom")

    monkeypatch.setattr(dictionary_mod, "build", raise_boom)

    r = runner.invoke(app, ["build-dictionary", str(pdf)])

    assert r.exit_code == 2
    assert "boom" in r.stderr
