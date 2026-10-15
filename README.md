# ste-lint

A deterministic linter for [ASD-STE100](https://asd-ste100.org/) (Simplified Technical
English) Issue 9. It checks that text uses only approved dictionary words and follows the
mechanically-checkable STE writing rules, and it doubles as a Claude Code skill (see
`SKILL.md`) so Claude can check or rewrite text against STE without guessing from memory.

> **Independent project.** ste-lint is not affiliated with, endorsed by, or certified by
> ASD or the STEMG. ASD-STE100 is copyright ASD and an EU registered trade mark of ASD
> (No. 017966390). This repository contains no part of the specification: you build the
> dictionary locally from your own copy. A clean lint result is not a statement of
> compliance. See [Legal](#legal) and `NOTICE`.

## Prerequisites

- `git` and `make` (on macOS: `xcode-select --install`).
- macOS or Linux. Windows is not supported: `tool/bin/ste` is a bash wrapper and the
  Makefile assumes a POSIX shell (WSL should work but is untested).
- [`uv`](https://docs.astral.sh/uv/) to create the virtualenv and install the package
  (it also fetches Python 3.12 when needed).
- `pdftotext` from poppler, used by `make dictionary` / `make download` to read the PDF.
- Your own copy of the ASD-STE100 Issue 9 PDF from the official source. Either register
  through ASD's free
  [download form](https://www.asd-europe.org/standards-specifications/simplified-technical-english/download-asd-ste-100)
  (preferred: it tells ASD how STE is used), or run `make download`, which fetches it
  from the official ASD-STE100 website. Do not use copies from mirror sites.

`make install`, `make setup`, `make dictionary` and `make download` first run
`make deps`, which checks for `git`, `uv` and `pdftotext`. With Homebrew (macOS, or
Linux with Homebrew) it installs the missing ones (`brew install uv poppler`). Without
Homebrew it prints the commands for your system (for example
`sudo apt-get install poppler-utils`) and stops: it never runs `sudo` or an install
script for you. The Python packages and the spaCy model are installed into the
project's own virtualenv by `make setup`.

`make doctor` reports `uv` and `pdftotext` as booleans; they are informational only and
do not affect its exit code (linting needs neither once the dictionary is built).

## Install as a Claude Code skill

```bash
git clone https://github.com/abdavid/ste-lint.git
cd ste-lint
make install PDF=~/Downloads/asd-ste100-issue-9.pdf
```

No PDF yet? Run `make install`, then `make -C ~/.claude/skills/ste-lint download`.

`make install` puts a clean clone of this checkout at `~/.claude/skills/ste-lint` (pass
`DEST=...` to choose another directory), creates its virtualenv, downloads the spaCy
model, and builds the dictionary from your PDF. Without `PDF=`, it reuses a dictionary
already built in this checkout, or tells you how to build one later. Claude Code picks
up the skill in new sessions.

Run `make install` again to update: it pulls the installed clone (`git pull --ff-only`)
and refreshes its dependencies. An existing dictionary is kept.

## Development setup

To work on ste-lint itself in this checkout:

The ASD-STE100 dictionary and rule text are copyright ASD and are **not** included in
this repository (`tool/ste_lint/data/dictionary.json` and `rules.json` are gitignored).
Each user builds them locally from their own copy of the PDF, and the built files must
not be shared (see [Legal](#legal)).

```bash
# 1. Create the virtualenv, install the package, and download the spaCy model.
make setup

# 2. Build the dictionary and rules from your own ASD-STE100 Issue 9 PDF...
make dictionary PDF=~/Downloads/asd-ste100-issue-9.pdf
#    ...or download it from the official ASD-STE100 website and build from that.
make download            # asks first; YES=1 skips the question

# 3. Confirm everything is wired up.
make doctor
# {
#   "python": "3.12.x",
#   "spacy_model": true,
#   "dictionary": true,
#   "dictionary_path": "/path/to/ste-lint/tool/ste_lint/data/dictionary.json",
#   "rules": true,
#   "uv": true,
#   "pdftotext": true
# }

# 4. Run the test suite.
make test
```

`make doctor` reports `dictionary_path`, which honors the `STE_LINT_DICTIONARY`
environment variable if set — point it at an alternate dictionary.json (for example, one
shared by a team) instead of the default under `tool/ste_lint/data/`.

## CLI usage

The CLI is `tool/bin/ste`. When installed as the Claude Code skill it lives at
`~/.claude/skills/ste-lint/tool/bin/ste`.

```bash
# Is a word approved? status is approved / mixed / unapproved / unknown.
ste lookup utilize
ste lookup check                 # "mixed": approved as a noun, not as a verb
ste lookup check --pos v         # disambiguate by part of speech
ste lookup removed               # approved forms are indexed: finds REMOVE (v)
ste lookup --batch words.txt     # one word per line

# Approved alternative for an unapproved word.
ste suggest consult

# Print the rule text for a rule id.
ste explain 1.1

# Lint ad-hoc text (use - to read from stdin).
ste check "Consult the manual." --format json
ste check "Consult the manual." --format json --mode procedural --kind heading

# Lint files or directories.
ste lint docs/ --format json
ste lint --changed --fail-on error      # only files changed vs. git HEAD; needs a git repo
ste lint docs/ --jobs 4                 # parallelize across files
ste lint docs/ --no-cache               # skip the .ste-lint-cache/ result cache

# Accept a word as a technical noun or verb (writes to .ste-lint.toml).
ste allow webhook/n
ste allow deploy/v --verb
```

`ste lookup` is form-based, not lemma-based: a query matches a dictionary headword or
one of the approved forms the dictionary lists for it (`removed` and `removes` find
`REMOVE (v)`). It does not inflect or lemmatize, so plurals (`screws`), `-ing` forms
(`removing`), and inflections of unapproved words (`consulted` — the dictionary lists no
forms for unapproved entries) all return `unknown`. Query the base form instead
(`ste lookup consult` → `unapproved`). `ste lint` / `ste check` do lemmatize with spaCy,
so they still flag `consulted` under rule 1.1.

`ste lint` and `ste check` validate `--fail-on`, `--mode`, and `--format`; an invalid
value exits 2. `--format` accepts `text`, `json`, or `sarif`. `--mode` accepts
`procedural` (instructions/steps) or `descriptive` (default). Exit codes throughout:
`0` clean, `1` findings at or above `fail-on`, `2` usage or data error (including
`ste doctor` reporting a missing dictionary/model, an invalid `.ste-lint.toml`, or a file
that cannot be read — missing, a directory, or not UTF-8 text; findings for the other
files are still printed). An explicit path that is not a lintable file type is skipped
with a warning.

## Rules checked

Rule ids are the ASD-STE100 **Issue 9** rule numbers. The topic column is this
project's own summary, not the official rule title; `ste explain N.M` prints the official
text from your locally built `rules.json`.

| Rule | Topic (our summary) | What the linter checks | Severity | Mode |
|---|---|---|---|---|
| `1.1` | Dictionary words, technical nouns and technical verbs only | word is in the dictionary but not approved; alternatives suggested | error | both |
| `1.1-unknown` | (synthetic, under 1.1) | word is not in the dictionary at all (technical noun/verb or typo?) | warning | both |
| `1.2` | Part of speech | word approved as another part of speech only | error | both |
| `1.4` | Verb and adjective forms | inflection not in the entry's approved forms | error | both |
| `2.1` | Noun clusters | noun cluster longer than three words | error | both |
| `3.5` | "-ing" forms | -ing verb form that is not an approved noun/adjective | error | both |
| `3.6` | Active voice | passive construction | error (procedural) / warning (descriptive) | both |
| `5.1` | Sentence length, procedures | sentence over 20 words | error | procedural |
| `5.2` | One instruction per sentence | two imperatives joined by "and"/"then" | warning | procedural |
| `5.3` | Imperative instructions | instruction sentence without an imperative verb | warning | procedural |
| `6.3` | Sentence length, descriptions | sentence over 25 words | error | descriptive |
| `6.6` | Paragraph length | paragraph with more than six sentences | warning | descriptive |
| `8.1` | Semicolons | semicolon present | info | both |
| `8.3` | Parentheses | parenthetical text longer than five words | info | both |

Headings are exempt from the length rules. Every other Issue 9 rule is a judgment rule
(see `reference/judgment-rules.md`).

## Configuration

Project settings live in `.ste-lint.toml` at the repo root (or any parent directory of the
files being linted); user-wide defaults live in `~/.config/ste-lint/config.toml` and are
merged in first. Example `.ste-lint.toml`:

```toml
mode = "procedural"
fail_on = "warning"
dictionary_sha = "40d66f0cea84d1fff67f36d560c04eab4034c6bcf64014d43bd6d4c19795f3f0"
technical_nouns = ["webhook/n", "fuel pump/n"]
technical_verbs = ["deploy/v"]
disable = ["8.1"]
exclude = ["drafts", "docs/generated/**", "*.gen.md"]

[severity_overrides]
"1.1-unknown" = "info"

[inputs.strings]
include = ["src/**/*.json"]
```

- `technical_nouns` / `technical_verbs` — words accepted per rules 1.5–1.13, as
  `word/pos` (`ste allow` appends to these).
- `disable` — rule ids to skip entirely. Disabling a base id also disables its synthetic
  sub-ids: `disable = ["1.1"]` turns off both `1.1` and `1.1-unknown` (list
  `"1.1-unknown"` alone to keep `1.1`).
- `exclude` — glob patterns for files or directories to skip, matched against the path
  relative to the directory holding `.ste-lint.toml`, or to the linted directory when
  there is none (`*` and `?` do not cross `/`,
  `**/` matches any depth). A pattern without `/` also matches a single path component,
  so `"drafts"` skips every `drafts/` directory. `.git`, `node_modules`, `dist`, `build`,
  `target`, `.venv`, `venv`, `__pycache__` and `.ste-lint-cache` are always skipped when
  they occur inside the linted tree (a repo that itself lives under `/srv/build/` is fine).
- `severity_overrides` — per-rule severity, keyed by rule id (including synthetic ids
  like `1.1-unknown`).
- `fail_on` — default `--fail-on` value (`error`, `warning`, or `info`).

`mode`, `fail_on`, and every `severity_overrides` value are validated when the file is
loaded; an invalid value (for example `mode = "Procedural"`) makes `ste lint`, `ste check`,
and `ste allow` print `error: invalid mode 'Procedural' in /path/.ste-lint.toml: ...` and
exit 2.
- `dictionary_sha` — pin the dictionary build this project expects; useful to detect a
  stale or mismatched dictionary.json across machines.
- `[inputs.strings].include` — glob patterns (same syntax as `exclude`) for source files
  whose string literals should also be linted.

`ste lint` writes its result cache to `.ste-lint-cache/` next to `.ste-lint.toml` (or in
the current directory when there is no project file). Add `.ste-lint-cache/` to the
consuming repo's `.gitignore`.

## CI

```bash
tool/bin/ste lint docs --format sarif --fail-on error > results.sarif
```

Upload `results.sarif` as a code-scanning artifact (e.g. `github/codeql-action/upload-sarif`)
to surface findings as annotations.

### pre-commit

Add a `repo: local` hook to the consuming repo's `.pre-commit-config.yaml`, pointing
`entry` at the installed CLI (pre-commit's `language: system` runs it as-is, so the path
must be absolute or on `PATH`):

```yaml
- repo: local
  hooks:
    - id: ste-lint
      name: ste-lint
      entry: /Users/<you>/.claude/skills/ste-lint/tool/bin/ste lint --changed --fail-on error
      language: system
      pass_filenames: false
```

The hook lints only files changed vs. git HEAD (`--changed`) and fails the commit on any
`error`-severity finding. Make sure `.ste-lint-cache/` is in that repo's `.gitignore`.
(This repo also ships `.pre-commit-hooks.yaml`, but its relative `entry` only works when
the hook is run from this checkout, so prefer the `repo: local` form above.)

## Helper scripts

Standalone Python scripts (standard library only) in `scripts/`:

- `check_no_asd_text.py` — lists text in the repository that matches your locally built
  `dictionary.json` / `rules.json` (rule titles, rule text, dictionary meanings and
  examples). Run it before you publish or open a pull request; it exits 1 on a match.
- `allowlist.py GLOSSARY [OUT]` — writes a `.ste-lint.toml` allowlist from the STE
  register (Technical Names, Norwegian words, Domain words, Technical Verbs) in a
  markdown glossary.
- `register.py GLOSSARY SECTION FILE` — adds words to one section of that register,
  sorted and without duplicates.
- `rewrap.py FILE...` — rewraps markdown prose to 74 columns without ending a line on an
  article (the tagger then misreads it as a pronoun).

## Legal

The code and documentation in this repository are MIT-licensed (`LICENSE`). That
licence covers this project's own work only and grants no rights in ASD-STE100.

- **Not affiliated.** ste-lint is an independent project. It is not affiliated with,
  endorsed by, sponsored by, or certified by the Aerospace, Security and Defence
  Industries Association of Europe (ASD) or the Simplified Technical English Maintenance
  Group (STEMG).
- **Trade marks.** ASD-STE100 Simplified Technical English is an EU registered trade
  mark of ASD (No. 017966390). The name is used here only to identify the specification
  that the tool checks against.
- **Copyright.** The ASD-STE100 specification, including its rules, dictionary and
  examples, is copyright ASD. This repository does not contain it. Rule numbers and the
  short rule summaries in this repository are the project's own wording.
- **Downloading.** `make download` fetches the PDF from ASD's own website
  (`asd-ste100.org`) to your machine, for your own use, after you confirm. ste-lint
  never downloads from anywhere else and never uploads anything.
- **Your data stays yours.** `make dictionary` builds `tool/ste_lint/data/dictionary.json`
  and `rules.json` from the PDF (kept, gitignored, at `tool/ste_lint/data/asd-ste100-issue-9.pdf` by
  `make download`). The PDF and those files contain ASD material: keep them
  local, do not commit them, and do not share or publish them (for example in a bundle,
  a package, a shared network path, or a CI cache). Each user builds their own.
- **No compliance claim.** The linter is an aid for writers who know ASD-STE100. It
  checks only the rules listed above, it can be wrong, and a clean result does not mean
  that a text complies with ASD-STE100.

Contributions must not add text from the specification; see `CONTRIBUTING.md`.

## Known limitations

- A finding whose text wraps across two source lines (for example a long sentence
  flagged by 5.1/6.3) is reported on the line where it starts, with `end_col` clipped to
  the end of that line.
- Heading and list-item detection assumes a single space after the marker (`#`, `-`,
  `1.`, etc.); other spacing may not be recognized as that block kind.
- Unit abbreviations (e.g. `mm`, `kg`) are only skipped when they directly follow a
  number; the same abbreviation elsewhere is treated as ordinary text.
- Two ASD-STE100 headwords, `position/v` and `precaution/n`, are currently missing from
  the built dictionary because of a column-layout quirk on page 336 of the source PDF;
  `ste lookup position --pos v` and `ste lookup precaution --pos n` report `unknown`
  until this is fixed upstream in `build-dictionary`. The same quirk produces a bogus
  `precaution/adj` entry whose "meaning" is just `(n)`, so a bare `ste lookup precaution`
  reports `approved` with `approved_pos: ["adj"]` — treat that entry as the missing noun.

## Corpus accuracy

`tool/tests/test_corpus.py` lints the real dictionary's own example sentences (skipped
unless the PDF and built dictionary are present locally): of 3,145 "ste" examples, 15.7%
(495) still get a false-positive error, mostly from predicate adjectives spaCy tags as
verbs (`IS DAMAGED`) and words the dictionary itself marks unapproved yet uses in its own
examples. Of 2,008 "non_ste" examples, 83.7% (1,680) are flagged with an error and 98.6%
(1,980) with at least a warning (the gate asserts on the error rate; the all-findings rate is
reported alongside it since it is inflated by `1.1-unknown` on out-of-dictionary words).
The 15.7%-measured / 18%-threshold gap leaves only ~2 points of headroom, so the STE
threshold may need revisiting after a spaCy model upgrade.
