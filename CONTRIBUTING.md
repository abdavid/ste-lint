# Contributing

## Do not add ASD-STE100 content

The ASD-STE100 specification is copyright ASD and is not part of this repository (see
`NOTICE`). A pull request must not add text from it:

- no rule text or official rule titles (refer to a rule by its number, and describe it
  in your own words),
- no dictionary entries, meanings, or example sentences (STE or non-STE),
- no built data (`tool/ste_lint/data/dictionary.json`, `rules.json`,
  `build-report.json`), and no PDF or extract of it.

Test fixtures use invented words, meanings, and sentences that copy only the *layout* of
the PDF. Short facts that a linter must state, such as "CONSULT is not approved; use
REFER", are fine.

If you have built the data locally, run the check before you open a pull request:

```bash
python3 scripts/check_no_asd_text.py
```

It compares every tracked and new file with your local `dictionary.json` and `rules.json`
and lists text that matches. It exits 1 when it finds a match.

## Development

```bash
make setup
make dictionary PDF=path/to/your/asd-ste100-issue-9.pdf   # optional; corpus tests need it
make test
```
