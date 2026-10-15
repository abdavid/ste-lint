"""Find ASD-STE100 text in the files of this repository.

Usage: python3 scripts/check_no_asd_text.py [ROOT]
  ROOT  the repository root, default the current directory

The script needs the local build of the dictionary and the rules
(make dictionary). It reads every tracked file and every new file that git
does not ignore, and it shows each match with:
  - an official rule title (five words or more),
  - a run of eight words from the rule text,
  - a meaning or an example sentence from the dictionary (four words or more).

The exit code is 0 when there is no match, 1 when there is a match, and 2
when the built data is missing.
"""

import json
import re
import subprocess
import sys
from pathlib import Path

RUN = 8
SKIP_PREFIXES = ("tool/ste_lint/data/", ".idea/")
SKIP_SUFFIXES = (".lock", ".pdf")
# The name of ASD occurs in the rule text, and NOTICE must also give it.
NAME = "aerospace security and defence industries association of europe"


def norm(text: str) -> list[str]:
    return re.sub(r"[^a-z0-9]+", " ", text.lower()).split()


def runs(words: list[str], n: int):
    for i in range(len(words) - n + 1):
        yield " ".join(words[i:i + n])


def main() -> None:
    root = Path(sys.argv[1] if len(sys.argv) > 1 else ".").resolve()
    data = root / "tool" / "ste_lint" / "data"
    try:
        dictionary = json.loads((data / "dictionary.json").read_text())
        rules = json.loads((data / "rules.json").read_text())
    except FileNotFoundError:
        print("error: build the data first (make dictionary PDF=...)")
        raise SystemExit(2)

    titles, rule_runs = {}, {}
    for rid, rule in rules.items():
        title = norm(rule["title"])
        if len(title) >= 5:
            titles[" ".join(title)] = rid
        body = " ".join(norm(rule["body"])).replace(NAME, " ")
        for r in runs(body.split(), RUN):
            rule_runs.setdefault(r, rid)
    phrases = {}
    for e in dictionary["entries"]:
        for s in [e["meaning"], *e["examples"]["ste"], *e["examples"]["non_ste"]]:
            words = norm(s)
            if len(words) >= 4:
                phrases.setdefault(" ".join(words), e["id"])

    files = subprocess.run(
        ["git", "-C", str(root), "ls-files", "--cached", "--others", "--exclude-standard"],
        capture_output=True, text=True, check=True,
    ).stdout.splitlines()
    found = 0
    for name in files:
        if name.startswith(SKIP_PREFIXES) or name.endswith(SKIP_SUFFIXES):
            continue
        try:
            words = norm((root / name).read_text())
        except (UnicodeDecodeError, FileNotFoundError, IsADirectoryError):
            continue
        text = " " + " ".join(words) + " "
        hits = [f"rule {rid} title" for t, rid in titles.items() if f" {t} " in text]
        hits += sorted({f"rule {rule_runs[r]} text" for r in runs(words, RUN) if r in rule_runs})
        hits += [f"dictionary {eid}: {p[:70]}" for p, eid in phrases.items() if f" {p} " in text]
        if hits:
            found += 1
            print(f"{name}:")
            for h in hits:
                print(f"  {h}")
    raise SystemExit(1 if found else 0)


if __name__ == "__main__":
    main()
