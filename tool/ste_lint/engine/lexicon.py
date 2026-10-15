from __future__ import annotations

import json
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path

from ste_lint import DICTIONARY_PATH


@dataclass(frozen=True)
class Alternative:
    word: str
    pos: str | None


@dataclass(frozen=True)
class Entry:
    id: str
    word: str
    pos: str
    approved: bool
    forms: tuple[str, ...]
    no_other_forms: bool
    meaning: str
    alternatives: tuple[Alternative, ...]
    examples_ste: tuple[str, ...]
    examples_non_ste: tuple[str, ...]

    def to_dict(self) -> dict:
        return {
            "id": self.id, "word": self.word, "pos": self.pos, "approved": self.approved,
            "forms": list(self.forms), "meaning": self.meaning,
            "alternatives": [{"word": a.word, "pos": a.pos} for a in self.alternatives],
            "examples": {"ste": list(self.examples_ste), "non_ste": list(self.examples_non_ste)},
        }


class Lexicon:
    def __init__(self, issue: str, sha: str, entries: list[Entry]):
        self.issue, self.sha = issue, sha
        self._entries = entries
        self._by_form: dict[str, list[Entry]] = defaultdict(list)
        self._by_lemma: dict[str, list[Entry]] = defaultdict(list)
        self.multiword_first: dict[str, list[Entry]] = defaultdict(list)
        for e in entries:
            self._by_lemma[e.word].append(e)
            for f in e.forms:
                self._by_form[f].append(e)
            if " " in e.word:
                self.multiword_first[e.word.split()[0]].append(e)

    @classmethod
    def from_dict(cls, data: dict) -> "Lexicon":
        entries = [
            Entry(
                id=d["id"], word=d["word"], pos=d["pos"], approved=d["approved"],
                forms=tuple(f.lower() for f in d["forms"]), no_other_forms=d.get("no_other_forms", False),
                meaning=d.get("meaning", ""),
                alternatives=tuple(Alternative(a["word"], a.get("pos")) for a in d.get("alternatives", [])),
                examples_ste=tuple(d.get("examples", {}).get("ste", [])),
                examples_non_ste=tuple(d.get("examples", {}).get("non_ste", [])),
            )
            for d in data["entries"]
        ]
        return cls(data.get("issue", "?"), data.get("source_sha256", ""), entries)

    @classmethod
    def load(cls, path: Path | None = None) -> "Lexicon":
        path = path or DICTIONARY_PATH
        if not path.exists():
            raise FileNotFoundError(f"{path} missing — run: ste build-dictionary <asd-ste100-issue-9.pdf>")
        return cls.from_dict(json.loads(path.read_text()))

    def entries(self) -> list[Entry]:
        return list(self._entries)

    def by_form(self, form: str) -> list[Entry]:
        return list(self._by_form.get(form.lower(), []))

    def by_lemma(self, lemma: str) -> list[Entry]:
        return list(self._by_lemma.get(lemma.lower(), []))

    def approved_for(self, form: str, pos: str) -> Entry | None:
        for e in self.by_form(form):
            if e.approved and e.pos == pos:
                return e
        return None
