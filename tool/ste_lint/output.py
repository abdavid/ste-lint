from __future__ import annotations

import json

from ste_lint.engine.findings import Finding

SARIF_LEVEL = {"error": "error", "warning": "warning", "info": "note"}


def render(findings: list[Finding], fmt: str, meta: dict) -> str:
    if fmt == "json":
        return json.dumps({"meta": meta, "findings": [f.to_dict() for f in findings]}, indent=2, ensure_ascii=False)
    if fmt == "sarif":
        rules = sorted({f.rule for f in findings})
        return json.dumps({
            "version": "2.1.0",
            "$schema": "https://json.schemastore.org/sarif-2.1.0.json",
            "runs": [{
                "tool": {"driver": {"name": "ste-lint", "version": meta.get("version"),
                                     "rules": [{"id": r, "shortDescription": {"text": f"ASD-STE100 rule {r}"}} for r in rules]}},
                "results": [{
                    "ruleId": f.rule, "level": SARIF_LEVEL[f.severity], "message": {"text": f.message},
                    "locations": [{"physicalLocation": {"artifactLocation": {"uri": f.file},
                                                        "region": {"startLine": f.line, "startColumn": f.col, "endColumn": f.end_col}}}],
                } for f in findings],
            }],
        }, indent=2)
    if not findings:
        return "No findings."
    lines = [f"{f.file}:{f.line}:{f.col}: {f.severity} {f.rule} '{f.text}' — {f.message}"
             + (f" [→ {f.suggestion}]" if f.suggestion else "") for f in findings]
    counts = {s: sum(1 for f in findings if f.severity == s) for s in ("error", "warning", "info")}
    lines.append(f"{counts['error']} errors, {counts['warning']} warnings, {counts['info']} info")
    return "\n".join(lines)
