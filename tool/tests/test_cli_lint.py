import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from ste_lint.cli import app

runner = CliRunner()


@pytest.fixture(autouse=True)
def use_mini_dictionary(monkeypatch, fixtures, tmp_path):
    # An env var (not a monkeypatched attribute) so it propagates to
    # multiprocessing workers spawned by `lint --jobs N` under the platform's
    # default start method ("spawn" on macOS), which re-imports ste_lint.cli
    # fresh in each worker and would otherwise lose any in-process patch.
    monkeypatch.setenv("STE_LINT_DICTIONARY", str(fixtures / "mini_dictionary.json"))
    # The result cache lives at the config root or the cwd; keep it inside
    # the test's tmp dir rather than the source tree.
    monkeypatch.chdir(tmp_path)


def test_check_json():
    r = runner.invoke(app, ["check", "Consult the manual.", "--format", "json"])
    assert r.exit_code == 1
    data = json.loads(r.output)
    assert data["meta"]["tool"] == "ste-lint"
    assert data["findings"][0]["rule"] == "1.1"


def test_check_clean_exit_zero():
    r = runner.invoke(app, ["check", "Remove the cover."])
    assert r.exit_code == 0 and r.output.strip() == "No findings."


def test_lint_file_text_and_fail_on(tmp_path: Path):
    p = tmp_path / "doc.md"
    p.write_text("# Title\n\nRemove the flange.\n")
    r = runner.invoke(app, ["lint", str(p)])
    assert r.exit_code == 0  # warning only, default fail-on error
    assert "1.1-unknown" in r.output and ":3:12:" in r.output
    r = runner.invoke(app, ["lint", str(p), "--fail-on", "warning"])
    assert r.exit_code == 1


def test_lint_sarif(tmp_path: Path):
    p = tmp_path / "doc.md"
    p.write_text("Consult the manual.\n")
    r = runner.invoke(app, ["lint", str(p), "--format", "sarif"])
    sarif = json.loads(r.output)
    res = sarif["runs"][0]["results"][0]
    assert res["ruleId"] == "1.1" and res["level"] == "error"
    assert res["locations"][0]["physicalLocation"]["region"]["startLine"] == 1


def test_lint_directory_uses_cache(tmp_path: Path):
    (tmp_path / "a.md").write_text("Consult the manual.\n")
    (tmp_path / "b.txt").write_text("Remove the cover.\n")
    r1 = runner.invoke(app, ["lint", str(tmp_path), "--format", "json"])
    r2 = runner.invoke(app, ["lint", str(tmp_path), "--format", "json"])
    assert json.loads(r1.output)["findings"] == json.loads(r2.output)["findings"]
    assert (tmp_path / ".ste-lint-cache").exists()


def test_cache_key_includes_path_so_identical_files_keep_their_own_name(tmp_path: Path):
    (tmp_path / "a").mkdir()
    (tmp_path / "b").mkdir()
    (tmp_path / "a" / "doc.md").write_text("Consult the manual.\n")
    (tmp_path / "b" / "doc.md").write_text("Consult the manual.\n")
    runner.invoke(app, ["lint", str(tmp_path / "a" / "doc.md"), "--format", "json"])
    r = runner.invoke(app, ["lint", str(tmp_path), "--format", "json"])
    files = sorted(f["file"] for f in json.loads(r.stdout)["findings"])
    assert files == [str(tmp_path / "a" / "doc.md"), str(tmp_path / "b" / "doc.md")]
    cached = list((tmp_path / ".ste-lint-cache").glob("*.json"))
    assert len(cached) == 2


def test_lint_invalid_fail_on(tmp_path: Path):
    p = tmp_path / "doc.md"
    p.write_text("Remove the cover.\n")
    r = runner.invoke(app, ["lint", str(p), "--fail-on", "bogus"])
    assert r.exit_code == 2
    assert "error: --fail-on must be one of error, warning, info" in r.stderr
    assert "Traceback" not in r.output


def test_lint_invalid_format(tmp_path: Path):
    p = tmp_path / "doc.md"
    p.write_text("Remove the cover.\n")
    r = runner.invoke(app, ["lint", str(p), "--format", "bogus"])
    assert r.exit_code == 2
    assert "error: --format must be one of text, json, sarif" in r.stderr
    assert "Traceback" not in r.output


def test_lint_changed_outside_git_repo(tmp_path: Path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    r = runner.invoke(app, ["lint", "--changed"])
    assert r.exit_code == 2
    assert "error: --changed requires a git repository" in r.stderr
    assert "Traceback" not in r.output


def test_lint_strings_input_json(tmp_path: Path):
    (tmp_path / ".ste-lint.toml").write_text('[inputs.strings]\ninclude = ["**/*.json"]\n')
    i18n = tmp_path / "src" / "i18n"
    i18n.mkdir(parents=True)
    (i18n / "en.json").write_text('{\n  "greeting": "Consult the manual"\n}\n')
    r = runner.invoke(app, ["lint", str(tmp_path), "--format", "json"])
    data = json.loads(r.output)
    assert any(f["file"].endswith("en.json") for f in data["findings"])


def test_lint_jobs_parallel_matches_serial(tmp_path: Path):
    (tmp_path / "a.md").write_text("Consult the manual.\n")
    (tmp_path / "b.txt").write_text("Remove the cover.\n")
    r1 = runner.invoke(app, ["lint", str(tmp_path), "--format", "json", "--no-cache"])
    r2 = runner.invoke(app, ["lint", str(tmp_path), "--format", "json", "--jobs", "2", "--no-cache"])
    assert r1.exit_code == r2.exit_code == 1
    assert json.loads(r1.output)["findings"] == json.loads(r2.output)["findings"]


def _git(cwd: Path, *args: str) -> None:
    import subprocess

    subprocess.run(["git", "-c", "user.name=t", "-c", "user.email=t@example.com", *args],
                   cwd=cwd, check=True, capture_output=True)


def test_lint_changed_filters_to_lintable_files(tmp_path: Path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    _git(tmp_path, "init", "-q")
    (tmp_path / "doc.md").write_text("Remove the cover.\n")
    (tmp_path / "code.py").write_text("x = 1\n")
    (tmp_path / "img.png").write_bytes(b"\x89PNG\r\n\x1a\n\x00")
    _git(tmp_path, "add", ".")
    _git(tmp_path, "commit", "-q", "-m", "init")
    (tmp_path / "doc.md").write_text("Consult the manual.\n")
    (tmp_path / "code.py").write_text("x = 2  # consult\n")
    (tmp_path / "img.png").write_bytes(b"\x89PNG\r\n\x1a\n\x01")
    (tmp_path / "new.md").write_text("Consult the manual.\n")  # untracked
    (tmp_path / "untouched.md").write_text("Consult the manual.\n")
    _git(tmp_path, "add", "untouched.md")
    _git(tmp_path, "commit", "-q", "-m", "untouched")
    r = runner.invoke(app, ["lint", "--changed", "--format", "json"])
    assert r.exit_code == 1, r.output + r.stderr
    files = sorted({f["file"] for f in json.loads(r.stdout)["findings"]})
    assert files == ["doc.md", "new.md"]


def test_lint_binary_file_reports_error_without_traceback(tmp_path: Path):
    p = tmp_path / "blob.md"
    p.write_bytes(b"\xff\xfe\x00\x00 not text \x80\x81")
    (tmp_path / "ok.md").write_text("Consult the manual.\n")
    r = runner.invoke(app, ["lint", str(p), str(tmp_path / "ok.md"), "--format", "json"])
    assert r.exit_code == 2
    assert f"error: {p}: not valid UTF-8" in r.stderr
    assert "Traceback" not in r.stderr and "Traceback" not in r.output
    # findings for the readable file are still printed
    assert json.loads(r.stdout)["findings"][0]["file"].endswith("ok.md")


def test_lint_missing_explicit_path_is_error(tmp_path: Path):
    missing = tmp_path / "nope.md"
    r = runner.invoke(app, ["lint", str(missing)])
    assert r.exit_code == 2
    assert f"error: {missing}: no such file" in r.stderr
    assert "Traceback" not in r.stderr


def test_lint_directory_skips_excluded_dirs(tmp_path: Path):
    for d in ("node_modules/pkg", ".git", "dist", "build", "target", "venv", "__pycache__"):
        (tmp_path / d).mkdir(parents=True)
        (tmp_path / d / "x.md").write_text("Consult the manual.\n")
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "real.md").write_text("Consult the manual.\n")
    r = runner.invoke(app, ["lint", str(tmp_path), "--format", "json"])
    files = {f["file"] for f in json.loads(r.output)["findings"]}
    assert files == {str(tmp_path / "docs" / "real.md")}


def test_lint_config_exclude_patterns(tmp_path: Path):
    (tmp_path / ".ste-lint.toml").write_text('exclude = ["drafts", "docs/generated/**", "*.gen.md"]\n')
    for rel in ("drafts/a.md", "sub/drafts/b.md", "docs/generated/c.md", "docs/generated/deep/d.md", "docs/e.gen.md"):
        (tmp_path / rel).parent.mkdir(parents=True, exist_ok=True)
        (tmp_path / rel).write_text("Consult the manual.\n")
    (tmp_path / "docs" / "keep.md").write_text("Consult the manual.\n")
    r = runner.invoke(app, ["lint", str(tmp_path), "--format", "json"])
    files = {f["file"] for f in json.loads(r.output)["findings"]}
    assert files == {str(tmp_path / "docs" / "keep.md")}


def test_lint_explicit_non_lintable_path_is_skipped_with_warning(tmp_path: Path):
    p = tmp_path / "img.png"
    p.write_bytes(b"\x89PNG")
    r = runner.invoke(app, ["lint", str(p)])
    assert r.exit_code == 0
    assert "skipped" in r.stderr and "No findings." in r.output


def test_lint_invalid_config_mode_exits_2(tmp_path: Path):
    (tmp_path / ".ste-lint.toml").write_text('mode = "Procedural"\n')
    (tmp_path / "doc.md").write_text("Remove the cover.\n")
    r = runner.invoke(app, ["lint", str(tmp_path)])
    assert r.exit_code == 2
    assert "error: invalid mode 'Procedural'" in r.stderr and "procedural, descriptive" in r.stderr
    assert "Traceback" not in r.stderr and "Traceback" not in r.output


def test_check_invalid_config_exits_2(tmp_path: Path):
    (tmp_path / ".ste-lint.toml").write_text('fail_on = "never"\n')
    r = runner.invoke(app, ["check", "Remove the cover."])
    assert r.exit_code == 2 and "invalid fail_on 'never'" in r.stderr


def test_lint_root_under_excluded_dir_name_is_still_linted(tmp_path: Path):
    # Excluded names (build, dist, ...) apply to directories inside the linted
    # tree, never to ancestors of it.
    root = tmp_path / "build" / "repo"
    (root / "docs").mkdir(parents=True)
    (root / "docs" / "doc.md").write_text("Consult the manual.\n")
    (root / "build").mkdir()
    (root / "build" / "gen.md").write_text("Consult the manual.\n")
    r = runner.invoke(app, ["lint", str(root), "--format", "json"])
    assert r.exit_code == 1, r.stderr
    assert {f["file"] for f in json.loads(r.stdout)["findings"]} == {str(root / "docs" / "doc.md")}
    r = runner.invoke(app, ["lint", str(root / "docs" / "doc.md"), "--format", "json"])
    assert r.exit_code == 1 and json.loads(r.stdout)["findings"][0]["rule"] == "1.1"


def test_lint_unreadable_file_reports_permission_error(tmp_path: Path):
    import os

    if os.geteuid() == 0:
        pytest.skip("root ignores file permissions")
    # (An unreadable *explicit* argument is already rejected by typer's Path
    # validation; the catch in _lint_one covers files found by recursion.)
    p = tmp_path / "locked.md"
    p.write_text("Consult the manual.\n")
    (tmp_path / "ok.md").write_text("Consult the manual.\n")
    p.chmod(0)
    try:
        r = runner.invoke(app, ["lint", str(tmp_path), "--format", "json"])
    finally:
        p.chmod(0o644)
    assert r.exit_code == 2 and f"error: {p}: permission denied" in r.stderr
    assert "Traceback" not in r.stderr and "Traceback" not in r.output
    assert json.loads(r.stdout)["findings"][0]["file"].endswith("ok.md")
