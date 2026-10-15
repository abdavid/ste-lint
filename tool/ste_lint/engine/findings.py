from __future__ import annotations

from dataclasses import asdict, dataclass

SEVERITIES = ("error", "warning", "info")
SEVERITY_RANK = {s: i for i, s in enumerate(SEVERITIES)}


@dataclass(frozen=True)
class Finding:
    rule: str
    severity: str
    file: str
    line: int
    col: int
    end_col: int
    text: str
    message: str
    suggestion: str | None = None
    fix: str | None = None
    context: str = ""

    def to_dict(self) -> dict:
        return asdict(self)
