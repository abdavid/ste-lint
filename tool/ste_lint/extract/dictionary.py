"""Parse dictionary Lines into normalized entries; validate; build data files."""
from __future__ import annotations

import hashlib
import json
import re
from datetime import date
from pathlib import Path
from typing import Iterable

from .pdf_words import HEADWORD, POS_ONLY, POS_RE, Line, iter_dictionary_lines

ALT_LINE = re.compile(rf"^(?P<w>[A-Z][A-Z'’\-\. ]*?)\s*(?:{POS_RE})?,?$")
OTHER_MEANINGS = re.compile(r"^for other$|^meanings?,? use:?$|^for other meanings,? use:?$", re.I)
SENTENCE_SPLIT = re.compile(r"(?<=[.!?:])\s+(?=[A-Z0-9\"“(])")
NO_OTHER_FORMS = re.compile(r"^no other( verb)?( forms\.?)?$|^forms\.?$", re.I)
EXPECTED_MIN, EXPECTED_MAX = 2100, 2300
SPOT_CHECKS = {
    "about/prep": True, "consult/v": False, "contact/v": True, "accept/v": True,
    "abnormal/adj": False, "test/n": True, "utilize/v": False,
}


def _split_sentences(parts: list[str]) -> list[str]:
    text = " ".join(p.strip() for p in parts if p.strip())
    return [s.strip() for s in SENTENCE_SPLIT.split(text) if s.strip()] if text else []


def _norm_word(w: str) -> str:
    return re.sub(r"\s+", " ", w.strip().rstrip(",")).lower()


def _forms_from_line(text: str) -> list[str]:
    cleaned = re.sub(r"\balso\b", " ", text.strip("() "), flags=re.I)
    return [_norm_word(t) for t in re.split(r"[,\s]+", cleaned) if t.strip("(),")]


def _start_entry(raw: list[dict], word_text: str, pos: str, page: int) -> dict:
    word = _norm_word(word_text)
    entry = {
        "id": f"{word}/{pos}", "word": word, "pos": pos,
        "approved": word_text.strip().isupper(), "forms": [word],
        "no_other_forms": False, "meaning_parts": [], "alternatives": [],
        "own_ste": [], "own_non": [], "notes": [], "page": page,
    }
    raw.append(entry)
    return entry


def _handle_col234(ln: Line, entry: dict, pending_alt: dict | None) -> dict | None:
    if ln.col == 2:
        t = ln.text.strip()
        if OTHER_MEANINGS.match(t):
            return pending_alt
        if pending_alt is not None and POS_ONLY.match(t):
            pending_alt["pos"] = POS_ONLY.match(t).group(1)
            return None
        m = ALT_LINE.match(t)
        if m and re.search(r"[A-Z]", t) and not re.search(r"[a-z]", re.sub(POS_RE, "", t)):
            alt = {"word": _norm_word(m.group("w")), "pos": m.group(2), "y": ln.y, "ste": [], "non": []}
            entry["alternatives"].append(alt)
            return alt if alt["pos"] is None else None
        entry["meaning_parts"].append(t)
        return None
    target = None
    for alt in entry["alternatives"]:
        if alt["y"] <= ln.y + 1:
            target = alt
    key = "ste" if ln.col == 3 else "non"
    if target is None:
        entry["own_ste" if key == "ste" else "own_non"].append(ln.text)
    else:
        target[key].append(ln.text)
    return pending_alt


def parse_entries(lines: Iterable[Line]) -> list[dict]:
    raw: list[dict] = []
    cur: dict | None = None
    pending_alt: dict | None = None
    pending_prefix: dict | None = None
    # Lines seen while pending_prefix is unresolved: they might belong to `cur`
    # (if the wrap attempt fails) or to a brand-new entry (if it succeeds), so
    # defer committing them until we know which.
    buffered: list[Line] = []

    def _flush_to_old_entry() -> None:
        nonlocal pending_alt, pending_prefix, buffered
        if cur is not None:
            cur["notes"].append(pending_prefix["text"])
            for bl in buffered:
                pending_alt = _handle_col234(bl, cur, pending_alt)
        pending_prefix = None
        buffered = []

    for ln in lines:
        if ln.col == 1:
            m = HEADWORD.match(ln.text)
            if m:
                if pending_prefix is not None:
                    _flush_to_old_entry()
                cur = _start_entry(raw, m.group("w"), m.group(2), ln.page)
                pending_alt = None
                continue
            # ln.text alone is not a complete headword; maybe it completes a
            # wrapped headword split across two column-1 rows, e.g.
            # "chance" + "(by chance) (n)" or "process (in the" + "process of ) (prep)".
            if pending_prefix is not None:
                combined = f"{pending_prefix['text']} {ln.text}".strip()
                cm = HEADWORD.match(combined)
                if cm:
                    new_cur = _start_entry(raw, cm.group("w"), cm.group(2), pending_prefix["page"])
                    new_pending_alt = None
                    for bl in buffered:
                        new_pending_alt = _handle_col234(bl, new_cur, new_pending_alt)
                    cur, pending_alt = new_cur, new_pending_alt
                    pending_prefix, buffered = None, []
                    continue
                _flush_to_old_entry()
            if cur is None:
                continue
            stripped = ln.text.strip()
            if NO_OTHER_FORMS.match(stripped):
                cur["no_other_forms"] = True
            elif cur["no_other_forms"] and not re.search(r"[A-Z]{2,}", ln.text):
                pass  # trailing descriptive words of a "No other ... forms." sentence
            elif re.fullmatch(r"[A-Z'’\-(),\s]+(also[A-Z'’\-(),\s]+)?", stripped):
                for f in _forms_from_line(ln.text):
                    if f and f not in cur["forms"]:
                        cur["forms"].append(f)
            elif re.search(r"[a-z]", ln.text) or stripped.startswith("("):
                pending_prefix = {"text": ln.text, "page": ln.page}
            else:
                cur["notes"].append(ln.text)
            continue
        if pending_prefix is not None:
            buffered.append(ln)
            continue
        if cur is None:
            continue
        pending_alt = _handle_col234(ln, cur, pending_alt)
    if pending_prefix is not None:
        _flush_to_old_entry()
    return [_normalize(r) for r in raw]


def _normalize(r: dict) -> dict:
    own_ste = _split_sentences(r["own_ste"])
    own_non = _split_sentences(r["own_non"])
    own_nonempty = bool(own_ste or own_non)
    alt_groups = [
        (a, _split_sentences(a["ste"]), _split_sentences(a["non"])) for a in r["alternatives"]
    ]
    nonempty_alt_count = sum(1 for _, s, n in alt_groups if s or n)
    total_groups = (1 if own_nonempty else 0) + nonempty_alt_count

    alts = []
    ste_all = list(own_ste)
    non_all = list(own_non)
    keep_per_alt = total_groups > 1
    for a, s, n in alt_groups:
        ste_all += s
        non_all += n
        item = {"word": a["word"], "pos": a["pos"]}
        if keep_per_alt and (s or n):
            item["examples"] = {"ste": s, "non_ste": n}
        alts.append(item)
    return {
        "id": r["id"], "word": r["word"], "pos": r["pos"], "approved": r["approved"],
        "forms": r["forms"], "no_other_forms": r["no_other_forms"],
        "meaning": " ".join(r["meaning_parts"]).strip(), "alternatives": alts,
        "examples": {"ste": ste_all, "non_ste": non_all}, "page": r["page"],
        **({"notes": r["notes"]} if r["notes"] else {}),
    }


def validate(entries: list[dict], check_count: bool = True) -> list[str]:
    problems: list[str] = []
    if check_count and not (EXPECTED_MIN <= len(entries) <= EXPECTED_MAX):
        problems.append(f"entry count {len(entries)} outside [{EXPECTED_MIN}, {EXPECTED_MAX}]")
    by_id = {e["id"]: e for e in entries}
    for e in entries:
        if not e["pos"]:
            problems.append(f"{e['id']}: empty pos")
        if not e["approved"] and not e["alternatives"] and not e["meaning"]:
            problems.append(f"{e['id']}: unapproved entry has no alternatives and no meaning")
    if check_count:
        for eid, approved in SPOT_CHECKS.items():
            if eid not in by_id:
                problems.append(f"spot check: {eid} missing")
            elif by_id[eid]["approved"] != approved:
                problems.append(f"spot check: {eid} approved={by_id[eid]['approved']}, expected {approved}")
    return problems


DATA_NOTICE = (
    "Built locally from ASD-STE100 (copyright ASD, Brussels) for the use of the person who built it. "
    "Do not commit, publish, or redistribute this file. ste-lint is not affiliated with ASD."
)


def build(pdf: Path, out_dir: Path) -> dict:
    entries = parse_entries(iter_dictionary_lines(pdf))
    problems = validate(entries)
    sha = hashlib.sha256(pdf.read_bytes()).hexdigest()
    data = {"issue": "9", "built": date.today().isoformat(), "source_sha256": sha, "notice": DATA_NOTICE,
            "entries": entries}
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "dictionary.json").write_text(json.dumps(data, indent=1, ensure_ascii=False))
    report = {
        "entries": len(entries),
        "approved": sum(e["approved"] for e in entries),
        "unapproved": sum(not e["approved"] for e in entries),
        "with_notes": [e["id"] for e in entries if e.get("notes")],
        "problems": problems,
    }

    from .rules_text import build_rules

    report["rules"] = build_rules(pdf, out_dir / "rules.json")

    (out_dir / "build-report.json").write_text(json.dumps(report, indent=1))
    return report
