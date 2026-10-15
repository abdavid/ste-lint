from __future__ import annotations

import json
import tomllib
from dataclasses import dataclass, field
from pathlib import Path

PROJECT_FILE = ".ste-lint.toml"
GLOBAL_FILE = Path.home() / ".config" / "ste-lint" / "config.toml"
MODES = ("procedural", "descriptive")
SEVERITIES = ("error", "warning", "info")


class ConfigError(ValueError):
    """A config file has an invalid value."""


def _apply(c: "Config", d: dict) -> None:
    if "mode" in d:
        c.mode = d["mode"]
    c.technical_nouns |= set(d.get("technical_nouns", []))
    c.technical_verbs |= set(d.get("technical_verbs", []))
    c.disable |= set(d.get("disable", []))
    c.severity_overrides.update(d.get("severity_overrides", {}))
    if "fail_on" in d:
        c.fail_on = d["fail_on"]
    if "dictionary_sha" in d:
        c.dictionary_sha = d["dictionary_sha"]
    c.string_include += d.get("inputs", {}).get("strings", {}).get("include", [])
    c.exclude += list(d.get("exclude", []))


def _read(path: Path) -> dict:
    try:
        return tomllib.loads(path.read_text(encoding="utf-8-sig"))
    except tomllib.TOMLDecodeError as e:
        raise ConfigError(f"cannot parse {path}: {e}") from e


def _dump_toml(d: dict) -> str:
    def s(v):
        return json.dumps(v, ensure_ascii=False)

    lines = []
    for k in ("mode", "fail_on", "dictionary_sha"):
        if d.get(k) is not None:
            lines.append(f"{k} = {s(d[k])}")
    for k in ("technical_nouns", "technical_verbs", "disable"):
        if d.get(k):
            lines.append(f"{k} = [{', '.join(s(x) for x in sorted(d[k]))}]")
    if d.get("exclude"):
        lines.append(f"exclude = [{', '.join(s(x) for x in d['exclude'])}]")
    if d.get("severity_overrides"):
        lines.append("\n[severity_overrides]")
        lines += [f"{s(k)} = {s(v)}" for k, v in d["severity_overrides"].items()]
    if d.get("string_include"):
        lines.append("\n[inputs.strings]")
        lines.append(f"include = [{', '.join(s(x) for x in d['string_include'])}]")
    return "\n".join(lines) + "\n"


@dataclass
class Config:
    mode: str = "descriptive"
    technical_nouns: set[str] = field(default_factory=set)
    technical_verbs: set[str] = field(default_factory=set)
    disable: set[str] = field(default_factory=set)
    severity_overrides: dict[str, str] = field(default_factory=dict)
    fail_on: str = "error"
    string_include: list[str] = field(default_factory=list)
    exclude: list[str] = field(default_factory=list)
    dictionary_sha: str | None = None
    root: str | None = None

    @classmethod
    def default(cls) -> "Config":
        return cls()

    @classmethod
    def load(cls, start: Path | None = None) -> "Config":
        """Merge the global config file and the nearest project file above ``start``.

        Raises ConfigError for an invalid mode, fail_on, or severity override.
        """
        c = cls()
        if GLOBAL_FILE.exists():
            _apply(c, _read(GLOBAL_FILE))
            c.validate(GLOBAL_FILE)
        p = (start or Path.cwd()).resolve()
        for d in [p, *p.parents]:
            f = d / PROJECT_FILE
            if f.exists():
                _apply(c, _read(f))
                c.root = str(d)
                c.validate(f)
                break
        return c

    def validate(self, source: Path | None = None) -> None:
        where = f" in {source}" if source else ""
        if self.mode not in MODES:
            raise ConfigError(f"invalid mode {self.mode!r}{where}: must be one of {', '.join(MODES)}")
        if self.fail_on not in SEVERITIES:
            raise ConfigError(f"invalid fail_on {self.fail_on!r}{where}: must be one of {', '.join(SEVERITIES)}")
        for rule_id, sev in self.severity_overrides.items():
            if sev not in SEVERITIES:
                raise ConfigError(
                    f"invalid severity {sev!r} for rule {rule_id!r} in [severity_overrides]{where}: "
                    f"must be one of {', '.join(SEVERITIES)}")

    def project_file(self) -> Path:
        return Path(self.root or Path.cwd()) / PROJECT_FILE

    def add_allow(self, word_pos: str, verb: bool) -> None:
        f = self.project_file()
        d = _read(f) if f.exists() else {}
        key = "technical_verbs" if verb else "technical_nouns"
        d.setdefault(key, [])
        if word_pos not in d[key]:
            d[key].append(word_pos)
        flat = {**d, "string_include": d.get("inputs", {}).get("strings", {}).get("include", [])}
        f.write_text(_dump_toml(flat))
        (self.technical_verbs if verb else self.technical_nouns).add(word_pos)

    def is_allowed(self, lemma: str, pos: str) -> bool:
        lemma = lemma.lower()
        for item in self.technical_nouns | self.technical_verbs:
            w, _, p = item.partition("/")
            if w.lower() == lemma and (not p or p == pos):
                return True
        return False
