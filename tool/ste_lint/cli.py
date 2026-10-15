import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

import typer

from ste_lint import DATA_DIR, DICTIONARY_PATH, RULES_PATH, SPACY_MODEL, __version__
from ste_lint.config import Config, ConfigError
from ste_lint.engine.findings import SEVERITY_RANK
from ste_lint.output import render

app = typer.Typer(add_completion=False, no_args_is_help=True)

TEXT_SUFFIXES = (".md", ".markdown", ".mdx", ".txt")
VALID_MODES = ("procedural", "descriptive")
VALID_FORMATS = ("text", "json", "sarif")


def _version(value: bool):
    if value:
        typer.echo(__version__)
        raise typer.Exit()


@app.callback()
def main(version: bool = typer.Option(False, "--version", callback=_version, is_eager=True)):
    """ASD-STE100 linter."""


@app.command()
def doctor():
    """Report whether data and model are available."""
    try:
        import spacy

        spacy.util.get_package_path(SPACY_MODEL)
        model_ok = True
    except Exception:
        model_ok = False
    dict_path = Path(os.environ["STE_LINT_DICTIONARY"]) if "STE_LINT_DICTIONARY" in os.environ else DICTIONARY_PATH
    report = {
        "python": sys.version.split()[0],
        "spacy_model": model_ok,
        "dictionary": dict_path.exists(),
        "dictionary_path": str(dict_path),
        "rules": RULES_PATH.exists(),
        # Informational only: needed for `make setup` / `build-dictionary`,
        # not for linting, so they never affect the exit code.
        "uv": shutil.which("uv") is not None,
        "pdftotext": shutil.which("pdftotext") is not None,
    }
    typer.echo(json.dumps(report, indent=2))
    required = ("spacy_model", "dictionary", "rules")
    raise typer.Exit(0 if all(report[k] for k in required) else 2)


@app.command("build-dictionary")
def build_dictionary(pdf: Path = typer.Argument(..., exists=True, readable=True)):
    """Extract the Part 2 dictionary from the ASD-STE100 PDF into data/dictionary.json."""
    from ste_lint.extract.dictionary import DATA_NOTICE, build

    try:
        report = build(pdf, DATA_DIR)
    except RuntimeError as e:
        typer.echo(str(e), err=True)
        raise typer.Exit(2)
    typer.echo(json.dumps(report, indent=2))
    typer.echo(DATA_NOTICE, err=True)
    if report["problems"]:
        typer.echo("BUILD PROBLEMS — dictionary written but failed validation", err=True)
        raise typer.Exit(2)


@app.command()
def lookup(
    words: list[str] = typer.Argument(None),
    pos: str = typer.Option(None, "--pos"),
    batch: Path = typer.Option(
        None, "--batch", exists=True, readable=True, dir_okay=False,
        help="file with one word per line",
    ),
):
    """Show dictionary entries for one or more words (JSON).

    status is "approved" if every matching entry is approved, "unapproved"
    if none are, "mixed" if some senses are approved and others are not, or
    "unknown" if no entry matches at all.
    """
    lex = _lexicon()
    query = list(words or [])
    if batch:
        query += [l.strip() for l in batch.read_text().splitlines() if l.strip()]
    result = []
    for w in query:
        entries = [e for e in lex.by_form(w) if pos is None or e.pos == pos]
        approved_pos = sorted({e.pos for e in entries if e.approved})
        if not entries:
            status = "unknown"
        elif all(e.approved for e in entries):
            status = "approved"
        elif any(e.approved for e in entries):
            status = "mixed"
        else:
            status = "unapproved"
        result.append({
            "query": w,
            "status": status,
            "approved_pos": approved_pos,
            "entries": [e.to_dict() for e in entries],
        })
    typer.echo(json.dumps(result if len(result) != 1 else result[0], indent=2, ensure_ascii=False))


@app.command()
def suggest(word: str):
    """Approved alternatives for an unapproved word (JSON)."""
    lex = _lexicon()
    entries = [e for e in lex.by_form(word) if not e.approved]
    typer.echo(json.dumps([
        {"id": e.id, "alternatives": [{"word": a.word, "pos": a.pos} for a in e.alternatives],
         "examples": {"ste": list(e.examples_ste), "non_ste": list(e.examples_non_ste)}}
        for e in entries
    ], indent=2, ensure_ascii=False))


def _lexicon():
    from ste_lint.engine.lexicon import Lexicon

    try:
        path = Path(os.environ["STE_LINT_DICTIONARY"]) if "STE_LINT_DICTIONARY" in os.environ else None
        return Lexicon.load(path)
    except FileNotFoundError as e:
        typer.echo(str(e), err=True)
        raise typer.Exit(2)


@app.command()
def explain(rule_id: str):
    """Print the STE rule text for a rule id such as 1.1 or 3.5."""
    from ste_lint.extract.rules_text import load_rules

    rules = load_rules()
    base = rule_id.split("-")[0]
    if base not in rules:
        typer.echo(f"Rule {rule_id} not found (run build-dictionary first?)", err=True)
        raise typer.Exit(2)
    r = rules[base]
    typer.echo(f"Rule {r['id']}: {r['title']}\n\n{r['body']}")


def _meta(lex):
    from ste_lint.engine.pipeline import load_nlp

    nlp = load_nlp()
    return {"tool": "ste-lint", "version": __version__, "issue": lex.issue, "dictionary_sha": lex.sha,
            "model": f"{SPACY_MODEL}-{nlp.meta['version']}"}


def _exit_for(findings, fail_on: str) -> int:
    return 1 if any(SEVERITY_RANK[f.severity] <= SEVERITY_RANK[fail_on] for f in findings) else 0


def _load_config(start: Path | None = None) -> Config:
    try:
        return Config.load(start)
    except ConfigError as e:
        typer.echo(f"error: {e}", err=True)
        raise typer.Exit(2)


def _require_choice(value: str, valid: tuple[str, ...], name: str) -> None:
    if value not in valid:
        typer.echo(f"error: --{name} must be one of {', '.join(valid)}", err=True)
        raise typer.Exit(2)


@app.command()
def check(text: str, mode: str = typer.Option(None), fmt: str = typer.Option("text", "--format"),
          kind: str = typer.Option("paragraph", "--kind")):
    """Lint ad-hoc text (use - to read stdin)."""
    from ste_lint.engine.pipeline import lint_text

    _require_choice(fmt, VALID_FORMATS, "format")
    if mode is not None:
        _require_choice(mode, VALID_MODES, "mode")
    if text == "-":
        text = sys.stdin.read()
    lex = _lexicon()
    config = _load_config()
    if mode:
        config.mode = mode
    findings = lint_text(text, lex, config, kind=kind)
    typer.echo(render(findings, fmt, _meta(lex)))
    raise typer.Exit(_exit_for(findings, config.fail_on))


EXCLUDED_DIRS = frozenset({".ste-lint-cache", ".git", "node_modules", "dist", "build", "target",
                           ".venv", "venv", "__pycache__"})


def _glob_re(pattern: str) -> "re.Pattern[str]":
    """Translate a path glob (``*``, ``?``, ``**``) to a regex matching a whole posix path.

    ``*``/``?`` never cross a ``/``; ``**/`` matches zero or more directories.
    """
    out, i = [], 0
    while i < len(pattern):
        c = pattern[i]
        if pattern.startswith("**/", i):
            out.append("(?:.*/)?")
            i += 3
        elif pattern.startswith("**", i):
            out.append(".*")
            i += 2
        elif c == "*":
            out.append("[^/]*")
            i += 1
        elif c == "?":
            out.append("[^/]")
            i += 1
        else:
            out.append(re.escape(c))
            i += 1
    return re.compile("".join(out) + r"\Z")


def _rel_posix(path: Path, config: Config, base: Path | None = None) -> str:
    """``path`` relative to the config root, else to ``base`` (the lint argument), else
    to the cwd. Ancestors of the root are never part of the result, so a repo that
    happens to live under e.g. ``/srv/build/`` is not excluded by its parent's name."""
    resolved = path.resolve()
    candidates = [Path(config.root)] if config.root else []
    candidates += [base] if base is not None else []
    candidates.append(Path.cwd())
    for root in candidates:
        try:
            return resolved.relative_to(root.resolve()).as_posix()
        except ValueError:
            continue
    return path.name


def _matches(rel: str, pattern: str) -> bool:
    rx = _glob_re(pattern)
    if rx.match(rel):
        return True
    # A pattern without "/" also matches any single path component, so
    # "drafts" excludes a drafts/ directory anywhere and "*.gen.md" a file name.
    return "/" not in pattern and any(rx.match(part) for part in rel.split("/"))


def is_lintable(path: Path, config: Config, base: Path | None = None) -> bool:
    """True if ``path`` is a file ste-lint should read: a text file (TEXT_SUFFIXES) or a
    file matching an ``[inputs.strings].include`` glob, and not under an always-excluded
    directory (.git, node_modules, build outputs, virtualenvs, the result cache) or a
    ``config.exclude`` pattern. Exclusions are matched against the path relative to the
    config root / ``base`` only, never against directories above it."""
    rel = _rel_posix(path, config, base)
    if any(part in EXCLUDED_DIRS for part in rel.split("/")[:-1]):
        return False
    if any(_matches(rel, pat) for pat in config.exclude):
        return False
    if path.suffix.lower() in TEXT_SUFFIXES:
        return True
    return any(_matches(rel, pat) for pat in config.string_include)


def _collect(paths: list[Path], config: Config) -> list[Path]:
    out: list[Path] = []
    for p in paths:
        if p.is_dir():
            out += [q for q in p.rglob("*") if q.is_file() and is_lintable(q, config, base=p)]
        elif not p.exists():
            out.append(p)  # reported by _lint_one as "no such file"
        elif is_lintable(p, config, base=p.parent):
            out.append(p)
        else:
            typer.echo(f"warning: {p}: skipped (not a lintable file type, or excluded)", err=True)
    return sorted(set(out))


def _changed_files() -> list[Path]:
    cmd = ["git", "diff", "--name-only", "HEAD"]
    diff = subprocess.run(cmd, capture_output=True, text=True)
    if diff.returncode != 0:
        first_line = next((l for l in diff.stderr.splitlines() if l.strip()), diff.stderr.strip())
        typer.echo(f"error: --changed requires a git repository ({first_line})", err=True)
        raise typer.Exit(2)
    tracked = diff.stdout.split()
    untracked = subprocess.run(["git", "ls-files", "--others", "--exclude-standard"], capture_output=True, text=True).stdout.split()
    return [Path(p) for p in tracked + untracked if Path(p).is_file()]


LINT_ERROR = None  # sentinel returned by _lint_one when a file could not be read


def _lint_one(args):
    path_str, lex_sha, config_json, use_cache = args
    from ste_lint.cache import Cache
    from ste_lint.engine.pipeline import lint_blocks, load_nlp
    from ste_lint.inputs.base import extract

    path = Path(path_str)
    config = Config(**json.loads(config_json))
    config.technical_nouns, config.technical_verbs, config.disable = set(config.technical_nouns), set(config.technical_verbs), set(config.disable)
    lex = _lexicon()
    nlp = load_nlp()
    cache = Cache(Path(config.root or Path.cwd()))
    try:
        data = path.read_bytes()
        key = Cache.key(data, lex_sha, config_json, nlp.meta["version"], _rel_posix(path, config), __version__)
        if use_cache and (hit := cache.get(key)) is not None:
            return hit
        findings = lint_blocks(extract(path), lex, config, nlp)
    except FileNotFoundError:
        typer.echo(f"error: {path}: no such file", err=True)
        return LINT_ERROR
    except IsADirectoryError:
        typer.echo(f"error: {path}: is a directory", err=True)
        return LINT_ERROR
    except UnicodeDecodeError:
        typer.echo(f"error: {path}: not valid UTF-8 text (binary file?)", err=True)
        return LINT_ERROR
    except PermissionError:
        typer.echo(f"error: {path}: permission denied", err=True)
        return LINT_ERROR
    if use_cache:
        cache.put(key, findings)
    return findings


@app.command()
def lint(paths: list[Path] = typer.Argument(None), fmt: str = typer.Option("text", "--format"),
         mode: str = typer.Option(None), fail_on: str = typer.Option(None, "--fail-on"),
         changed: bool = typer.Option(False, "--changed"), jobs: int = typer.Option(1, "--jobs"),
         no_cache: bool = typer.Option(False, "--no-cache")):
    """Lint files or directories."""
    _require_choice(fmt, VALID_FORMATS, "format")
    if mode is not None:
        _require_choice(mode, VALID_MODES, "mode")
    if fail_on is not None:
        _require_choice(fail_on, tuple(SEVERITY_RANK), "fail-on")
    lex = _lexicon()
    config = _load_config((paths or [Path.cwd()])[0])
    if mode:
        config.mode = mode
    if fail_on:
        config.fail_on = fail_on
    if config.dictionary_sha and config.dictionary_sha != lex.sha:
        typer.echo(f"warning: dictionary sha {lex.sha[:12]} != pinned {config.dictionary_sha[:12]}", err=True)
    if changed:
        files = sorted({p for p in _changed_files() if is_lintable(p, config)})
    else:
        files = _collect(paths or [Path.cwd()], config)
    cfg_json = json.dumps({**config.__dict__, "technical_nouns": sorted(config.technical_nouns),
                           "technical_verbs": sorted(config.technical_verbs), "disable": sorted(config.disable)}, sort_keys=True)
    work = [(str(f), lex.sha, cfg_json, not no_cache) for f in files]
    if jobs > 1:
        from multiprocessing import Pool

        with Pool(jobs) as pool:
            results = pool.map(_lint_one, work)
    else:
        results = [_lint_one(w) for w in work]
    errored = any(r is LINT_ERROR for r in results)
    findings = [f for r in results if r is not LINT_ERROR for f in r]
    findings.sort(key=lambda f: (f.file, f.line, f.col, f.rule))
    typer.echo(render(findings, fmt, _meta(lex)))
    raise typer.Exit(2 if errored else _exit_for(findings, config.fail_on))


@app.command()
def allow(word_pos: str, verb: bool = typer.Option(False, "--verb")):
    """Add a technical noun (default) or technical verb to .ste-lint.toml."""
    config = _load_config()
    config.add_allow(word_pos, verb)
    typer.echo(f"added {word_pos} to {config.project_file()}")
