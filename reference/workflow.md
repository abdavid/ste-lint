# Workflows

Three procedures: **lint** an existing document, **write/rewrite** new text, and
**triage** the `1.1-unknown` words that come out of either. All three assume
`ste doctor` already reported `dictionary: true` and `rules: true`.

## 1. Lint an existing document

1. Run:
   ```bash
   ste lint PATH... --format json
   ```
   Use `--changed` instead of `PATH...` to lint only files changed vs. git HEAD (requires
   a git repo — exits 2 otherwise). Add `--mode procedural` for instruction-style docs,
   `--fail-on warning|error` to change what counts as a failure, `--jobs N` to parallelize
   across files, `--no-cache` to force a full re-lint.
2. Group the JSON `findings` array by `rule`, then render a table:

   | file:line | word | rule | suggestion |
   |---|---|---|---|
   | docs/manual.md:12 | utilize | 1.1 | use |
   | docs/manual.md:20 | ...ing | 3.5 | (imperative form) |

   Sort by file, then by line, within each rule group. Use the finding's `text` field for
   "word", `rule` for "rule", and `suggestion` (or `message` if `suggestion` is null) for
   "suggestion".
3. Separate findings into:
   - **Mechanical** — `fix` field is non-null (safe, deterministic replacement).
   - **Judgment** — everything else, including all `1.1-unknown` findings and any rule in
     `reference/judgment-rules.md`.
4. Before touching any file, ask for confirmation using this exact wording (fill in the
   real counts and word lists):
   ```
   Apply N mechanical fixes (rule 1.1 single-alternative, 3.5 -ing forms)? Unknown words: list. Mark as technical nouns: list?
   ```
   - "N mechanical fixes" = count of findings with a non-null `fix`.
   - "Unknown words: list" = the distinct `text` values of `1.1-unknown` findings.
   - "Mark as technical nouns: list?" = the subset of those unknown words you believe are
     legitimate technical nouns/verbs (see step 3 of the triage procedure below); omit
     this clause if there are none.
5. On confirmation, apply only the mechanical fixes automatically. Leave judgment-rule
   findings and any unknowns not covered by the reply for the user to resolve by hand, and
   run the unknown-triage procedure (below) for the words that were approved.
6. Re-run `ste lint PATH... --format json` and report the residual finding count, broken
   down by rule.

## 2. Write or rewrite text

1. Draft the text.
2. Check each paragraph as you go:
   ```bash
   ste check "PARAGRAPH TEXT" --format json --mode procedural   # instructions/steps
   ste check "PARAGRAPH TEXT" --format json                     # descriptive text (default mode)
   ```
   For a heading or list item, pass `--kind heading` or `--kind list_item` so rules that
   are exempt or softened for those kinds are applied correctly.
3. For every word you are not certain about, run `ste lookup WORD` (add `--pos` if the
   word could be more than one part of speech) before using it. Never assert a word is
   approved from memory.
4. Revise and re-check until the only remaining findings are `1.1-unknown` warnings. Then
   run the unknown-triage procedure below.
5. After triage, re-check the whole text one more time and report the final finding count
   (should be 0, or only findings the user explicitly accepted).

## 3. Unknown-word triage

Run this whenever `1.1-unknown` findings remain (from lint or from check).

For each distinct unknown word:

1. Run `ste suggest WORD`. If an approved alternative exists and fits the sentence,
   replace the word with it.
2. If no alternative fits, decide whether the word is a legitimate technical noun or verb
   for this domain: it names a specific thing/process, is short, used consistently
   elsewhere in the document, and is not slang. If so, propose adding it via
   `ste allow WORD/n` (noun, default) or `ste allow WORD/v --verb` (verb).
3. If the word is a typo or a synonym for something already approved, fix the text instead
   of allow-listing it.
4. Batch every decision from steps 1-3 into a single confirmation before applying,
   following the confirmation wording from the lint procedure above (step 4) — do not ask
   about each word individually.
5. After the user confirms, apply the replacements and run `ste allow` for each accepted
   technical noun/verb, then re-check to confirm the `1.1-unknown` findings are gone.
