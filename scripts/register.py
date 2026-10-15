"""Add words to a section of the STE register in the glossary.

Usage: python3 register.py GLOSSARY SECTION FILE
  GLOSSARY  the markdown file that has the register
  SECTION   names | norwegian | domain | verbs
  FILE      one entry per line: `word` or `word | gloss`

The script keeps the section sorted, and it skips a word that is there.
Then run allowlist.py.
"""

import re
import sys
from pathlib import Path

SECTIONS = {
    "names": "### Technical Names",
    "norwegian": "### Norwegian words",
    "domain": "### Domain words",
    "verbs": "### Technical Verbs",
}


def main() -> None:
    if len(sys.argv) != 4 or sys.argv[2] not in SECTIONS:
        print(__doc__)
        raise SystemExit(2)
    glossary = Path(sys.argv[1])
    heading = SECTIONS[sys.argv[2]]
    entries = [l.strip() for l in Path(sys.argv[3]).read_text().splitlines()]
    entries = [l for l in entries if l and not l.startswith("#")]

    text = glossary.read_text()
    start = text.index(heading)
    end = text.find("\n### ", start + 1)
    end = len(text) if end < 0 else end
    lines = text[start:end].split("\n")
    items = [l for l in lines if l.startswith("- `")]
    intro = [l for l in lines if not l.startswith("- `")]
    while intro and intro[-1] == "":
        intro.pop()

    def word_of(item: str) -> str:
        return re.match(r"- `([^`]+)`", item).group(1).lower()

    have = {word_of(i) for i in items}
    added = 0
    for entry in entries:
        word, _, gloss = entry.partition(" | ")
        if word.lower() in have:
            continue
        items.append(f"- `{word}`" + (f" — {gloss.strip()}" if gloss.strip() else ""))
        have.add(word.lower())
        added += 1
    items.sort(key=word_of)

    block = "\n".join(intro) + "\n\n" + "\n".join(items) + "\n"
    glossary.write_text(text[:start] + block + text[end:])
    print(f"{sys.argv[2]}: {added} added, {len(items)} entries")


if __name__ == "__main__":
    main()
