---
name: ste-lint
description: Lint or write text in ASD-STE100 Simplified Technical English. Use when the user mentions STE, Simplified Technical English, asks whether a word is "approved", wants documentation checked or rewritten for STE, or a repo contains .ste-lint.toml.
---

# ste-lint

Deterministic linter for ASD-STE100 Issue 9 (dictionary + writing rules). Never judge
STE compliance from memory — always ask the tool.

CLI: `~/.claude/skills/ste-lint/tool/bin/ste` (alias below as `ste`).

## Always first

```bash
ste doctor
```
If `dictionary` or `rules` is false, stop and tell the user they can either:
- build from their own PDF: `make -C ~/.claude/skills/ste-lint dictionary PDF=<path>`, or
- download it from the official ASD-STE100 website: `make -C ~/.claude/skills/ste-lint download`.

The PDF is copyright ASD. Run `download` only after the user agrees to it in this
conversation, and then with `YES=1` (it cannot prompt you). Never fetch the PDF any other
way or from any other site.

## Commands you will use

| Need | Command |
|---|---|
| Is word X approved? | `ste lookup X` (add `--pos v`) — status: approved / mixed / unapproved / unknown |
| Many words at once | `ste lookup --batch words.txt` |
| Replacement for unapproved word | `ste suggest X` |
| Is this sentence/paragraph STE? | `ste check "TEXT" --format json [--mode procedural]` |
| Lint files | `ste lint PATH... --format json` |
| Why does rule N.M exist? | `ste explain N.M` |
| Accept a technical noun/verb | `ste allow word/n` or `ste allow word/v --verb` |

Exit codes: 0 clean, 1 findings at or above fail-on, 2 usage/data error.

Status `mixed` means some senses of the word are approved and others are not (e.g. `check`:
the noun is approved, the verb is not) — pass `--pos` to disambiguate, or read the
`approved_pos` list in the JSON result before deciding.

`lookup` is form-based: it matches a headword or one of the approved forms the dictionary
lists (`removed` → REMOVE), but it does not lemmatize, so plurals, `-ing` forms, and
inflections of unapproved words (`screws`, `removing`, `consulted`) come back `unknown`.
Always look up the base form (`consult`, `screw`) before concluding a word is unknown;
`ste check`/`ste lint` lemmatize on their own.

## Workflows

Read `reference/workflow.md` for the full procedures. Summary:

1. **Lint** — run `ste lint --format json`, group findings by rule, show a table
   (file:line, word, rule, suggestion). Apply only mechanical fixes (`fix` field
   non-null) after the user confirms. Leave judgment rules to the user.
2. **Write / rewrite** — draft, then `ste check` every paragraph. For each unsure word run
   `ste lookup`. Iterate until only `1.1-unknown` warnings remain. Then triage unknowns.
3. **Unknown triage** — for each `1.1-unknown`: approved alternative exists → replace;
   legitimate technical noun/verb → propose `ste allow`; typo → fix. One batched confirm.
4. **Judgment rules** — apply `reference/judgment-rules.md` by reading; cite rule ids.

Rule ids are ASD-STE100 Issue 9 numbers. Machine-checked: 1.1 (+`1.1-unknown`), 1.2,
1.4, 2.1, 3.5 (-ing), 3.6 (passive), 5.1/6.3 (20/25-word limits), 5.2, 5.3, 6.6, 8.1,
8.3 — see the README table. Everything else is a judgment rule.

## Guardrails

- Never claim a word is approved without a `lookup` result.
- Never edit `tool/ste_lint/data/*.json`, and never copy, commit, or upload those files or
  the PDF: they contain ASD copyright material for the user's own local use.
- Always report residual finding counts after edits.
- Procedural text (instructions) uses `--mode procedural`; descriptive text uses the default.
