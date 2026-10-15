from __future__ import annotations

import hashlib
import json
from pathlib import Path

from ste_lint.engine.findings import Finding


class Cache:
    def __init__(self, root: Path):
        self.dir = root / ".ste-lint-cache"

    @staticmethod
    def key(file_bytes: bytes, lex_sha: str, config_repr: str, model: str, path: str, version: str) -> str:
        """Cache key for one file. ``path`` (relative to the cache root) is part of the
        key because findings carry the file name; ``version`` is the ste-lint version so
        a rule or renderer change never serves stale results."""
        h = hashlib.sha256()
        for part in (file_bytes, lex_sha.encode(), config_repr.encode(), model.encode(),
                     path.encode(), version.encode()):
            h.update(part)
            h.update(b"\0")
        return h.hexdigest()

    def get(self, key: str) -> list[Finding] | None:
        p = self.dir / f"{key}.json"
        if not p.exists():
            return None
        return [Finding(**d) for d in json.loads(p.read_text())]

    def put(self, key: str, findings: list[Finding]) -> None:
        self.dir.mkdir(exist_ok=True)
        (self.dir / f"{key}.json").write_text(json.dumps([f.to_dict() for f in findings]))
