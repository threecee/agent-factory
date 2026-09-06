# PR6 — edits requested in hub files and in files owned by other PRs

PR6 does not touch `INSTALL.md`, `README.md` or `user-level/README.md`
(shared hub files, integrated later). The exact edits it needs are below.
A second section lists one-line pointers PR6 needs in files that other v2
PRs own; those PRs (or the integrator) apply them.

## INSTALL.md

**Anchor:** Step 3 — Interpretation pillar, item 1. Replace the item with:

```
1. Create `docs/choices/` with `interpretation/choices-ledger-README.md`. The
   choices audit is a TRANSACTION POINT: every lane handback is audited with
   the `audit-choices` skill and recorded in `docs/choices/<train>.md` BEFORE
   assembly; unsound choices are resolved before the train is built. Every
   choice carries one stable ID (`<train>/<lane>-<n>`) from self-report to
   fix commit, and its walked scenario is stored in the protocol or in a
   sidecar committed under `docs/choices/<train>/` — never in a scratchpad
   (README §2–§3). `interpretation/examples/simplification-review.md` shows
   one train done this way end to end.
```

**Anchor:** Step 3 — Interpretation pillar, item 3. Replace the item with:

```
3. Read `interpretation/investigation-practice.md` — instrument-first is the
   default for every debugging lane, and its "Consumer inventory" section is
   the mandatory pre-step for every lane that deletes, moves, splits or
   renames: one row per protected element, readers in every language and
   path-keyed tool baselines included, live-versus-historical decided per
   file by executing readers.
```

## README.md

**Anchor:** the three-pillars table, row `interpretation/`, column
"Contents". Replace the cell text with:

```
The choices ledger (every decision an agent made on your behalf, audited per handback, one stable ID per choice, scenarios stored with the train), memory conventions that outlive sessions, evaluation practice (persona loops, state parity, honest metrics), investigation practice (instrument-first; consumer inventory before any move, split or delete), a worked simplification-review example, the continuous-improvement loop
```

## user-level/README.md

No edit needed from PR6. (`audit-choices` is already in the recommended
minimum; the ID and durable-scenario rules live in the skill and the
interpretation README, which the repo-level install carries.)

## Pointers PR6 needs in files owned by other PRs

- `harness/report-schema.md` (PR1): each `choices:` entry carries `id:`
  (`<lane>-<n>`, numbered by the lane) before `headline:`; the sidecar
  `<lane>-choices.md` is keyed by the same IDs and is committed under
  `docs/choices/<train>/` by the wrapper, or banked per
  `harness/artifact-bank.md` (PR5). Suggested field line:
  `- {id: <lane>-<n>, headline: <choice>, verdict: <sound|unsound|needs-user>, confidence: <H|M|L>, gap: <one line>}`.
- `planning/lane-brief-template.md` (PR1): under the task section, one line:
  "A lane that deletes, moves, splits or renames attaches the consumer
  inventory (`interpretation/investigation-practice.md`, Consumer inventory)
  and runs each listed consumer's apparatus, or names the wrapper as its
  rerun owner, before handback."
- `verification/verify-portfolio.md` (PR2/PR3/PR4): add to "Known vacuity
  classes": "name-patching guards (a `monkeypatch`/`mock` of a dotted name
  that was never on the executed path — green until the name moves, red for
  an unrelated reason; pin at the owner and show it red on a planted call)"
  and "path-keyed baselines treat a moved line as a new finding — fix the
  code, never the baseline".
- `verification/lander-duties.md` (PR3): one checklist line before push:
  "the train protocol cites no scratchpad or session path; every unsound or
  needs-user entry has its scenario inline; sidecars referenced by sound
  entries are committed under `docs/choices/<train>/` or banked
  (`interpretation/choices-ledger-README.md` §3)".
