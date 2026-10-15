# Judgment rules (not machine-checked)

`ste lint` and `ste check` do not enforce these ASD-STE100 Issue 9 rules. Apply them by
reading the text, and cite the rule id in your explanation. The rule ids are the Issue 9
numbers. The one-line summaries below are this project's own wording, not the official
rule text: run `ste explain N.M` for the official text from your locally built
`rules.json`. The machine-checked rules are listed at the end for contrast.

## Section 1 — Words

- **1.3** An approved word keeps only the meaning the dictionary gives it. Check
  `ste lookup WORD` → `meaning`; if the sentence uses another sense, rewrite.
- **1.5** Words that fall into one of the technical-noun categories are allowed.
- **1.6** An unapproved word is allowed only as (part of) a technical noun.
- **1.7** A technical noun stays a noun; never turn it into a verb.
- **1.8** Prefer the technical nouns your organization or field has already approved.
- **1.9** Among candidate technical nouns, pick a short, easily understood one.
- **1.10** No regional words, slang, or jargon as technical nouns.
- **1.11** One item, one technical noun: no synonyms for the same thing.
- **1.12** Words that fall into one of the technical-verb categories are allowed.
- **1.13** A technical verb stays a verb; never turn it into a noun.
- **1.14** Spell in American English unless a directive for the document says otherwise.

## Section 2 — Multi-word nouns

- **2.2** A technical name longer than three words is first given in full; after that,
  a shorter form or hyphenation can be used.

## Section 3 — Verbs

- **3.1** Verb forms come from the dictionary only.
- **3.2** Only a small set of tenses and forms is allowed (infinitive, imperative,
  simple present, simple past, future, and the past participle used as an adjective).
- **3.3** Use a past participle as an adjective to describe a state ("the removed
  cover"), not to build tenses.
- **3.4** No helper-verb chains such as "have removed" or "is being removed".
- **3.7** Express an action with an approved verb rather than a noun phrase ("the
  ohmmeter shows 450 ohms", not "gives an indication of").

## Section 4 — Sentences

- **4.1** Keep sentences short and clear. The hard word limits are checked as 5.1 /
  6.3; clarity is a judgment call.
- **4.2** Do not shorten sentences by dropping words or using contractions.
- **4.3** Break complex text into a vertical list.
- **4.4** Link sentences on related topics with connecting words or phrases.
- **4.5** Where it fits, put an article or "this"/"these" in front of a noun.

## Section 5 — Procedures

- **5.4** If the reader must know a condition first, state it before the instruction
  ("If X, do Y").
- **5.5** Notes give information only; they never contain instructions.

## Section 6 — Descriptive writing

- **6.1** Introduce information step by step.
- **6.2** Use key words and phrases to make the structure of the text clear.
- **6.4** Group related information into paragraphs.
- **6.5** Keep each paragraph to a single topic.

## Section 7 — Safety instructions

- **7.1** Mark the level of risk with the correct signal word (warning, caution).
- **7.2** Open a safety instruction with a precise command or condition.
- **7.3** Explain the risk or the possible consequence.

## Section 8 — Punctuation and word counts

- **8.2** Hyphenate words that belong together as one unit.
- **8.4**–**8.7** are word-count conventions (a colon in a vertical list ends a sentence;
  text in parentheses, numbers and similar elements, and hyphenated words each count as
  one word). The tool's word counter applies them when it checks 5.1 / 6.3; they produce
  no findings of their own.

## Section 9 — Writing practices

- **9.1** When swapping in an approved word does not work, restructure the sentence.
- **9.2** Use approved words with care: some are limited to particular contexts.
- **9.3** Do not combine a verb and a particle into a phrasal verb.
- **9.4** Keep terminology and wording consistent throughout.

## Machine-checked rules (for contrast)

`ste lint` / `ste check` enforce these Issue 9 rules: 1.1 (approved words; plus the
synthetic `1.1-unknown` for words not in the dictionary), 1.2 (part of speech), 1.4
(approved forms), 2.1 (noun clusters of at most three words), 3.5 (-ing forms), 3.6
(active voice), 5.1 (20-word procedural sentences), 5.2 (one instruction per sentence),
5.3 (imperative form), 6.3 (25-word descriptive sentences), 6.6 (at most six sentences
per paragraph), 8.1 (no semicolons), 8.3 (parentheses).
