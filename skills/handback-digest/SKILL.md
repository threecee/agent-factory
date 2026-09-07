---
name: handback-digest
description: Draft one choices-ledger entry per choice in a lane handback, in the ledger's own ELI5 entry format, as the starting point for the orchestrator's audit-choices pass. Use after a lane files its handback and before the orchestrator writes verdicts into the train's choices ledger. The draft is never the verdict.
---

# Handback Digest

The handback-digest command reads a lane's handback (the report the launcher
places at `LANE_RESULT_PATH` — `<lane>.<run-id>.result.md`,
`harness/run-lifecycle.md` §3 — written to the fields in
`harness/report-schema.md`, plus the `<lane>-choices.md` sidecar its
`choices_sidecar:` field names whenever `choices:` is non-empty) and drafts
one structured entry per choice: headline, a
provisional verdict, confidence, and one concrete end-to-end scenario, with
terms defined in place. The rules live in `harness/bulk-read-contract.md`;
this skill is the invocation and the hand-over to the audit.

## Invocation

```sh
{{HANDBACK_DIGEST_CMD}} <path-to-handback> [--diff-stat]
```

- `--diff-stat` appends `git diff --stat` for the lane's tree as extra
  context for the draft; it adds file names and counts, not content.
- Same input boundary as the other shunts (repository + lane scratchpad;
  exit 2 refused, exit 3 every worker failed, nothing echoed);
  `{{ALLOW_EXTERNAL_FLAG}}` under the same condition.
- Invoked deliberately, never via a hook block: a handback is short by
  contract, so the digest is a drafting aid, not a context saver.

## What the draft must preserve

Score the draft against the handback before using it (contract §6): every
exact identifier — lane name, head SHA, issue numbers, gate names and their
red/green result, test names, the `proof` command — and every negation
("not run", "skipped", "deselected") must survive verbatim. A digest that
turns "gate X not run" into "gates green" is misstated, not merely
incomplete; discard it and narrow the question.

## Hand-over to the audit

The output is a DRAFT for the orchestrator's `skills/audit-choices` pass,
never the final verdict (contract §3 rule 7):

1. `audit-choices` traces the handback **and** the diff itself; the digest's
   list is a starting point, not the boundary — workers under-report as
   agents do.
2. Each draft entry carries the same fields the ledger stores (headline,
   walked scenario, gap, reach, verdict, confidence — see
   `interpretation/choices-ledger-README.md`) so the auditor edits an entry
   rather than re-typing it; the auditor writes the verdict and the entry
   into the train's ledger under the stable choice ID
   (`interpretation/choices-ledger-README.md` §2).
3. Never treat the digest as already reviewed, never paste it into the ledger
   unedited, and never let it edit any file (it does not).

## Escape hatch

`{{SHUNT_DISABLE}}` disables the bounded-read hooks for the session; it does
not gate this command, which is invoked on purpose. When every worker is
down, audit the handback directly — it is short by contract.

## Parameters

`{{HANDBACK_DIGEST_CMD}}`, `{{ALLOW_EXTERNAL_FLAG}}` and `{{SHUNT_DISABLE}}`
are bound in the repository's operations doc from
`harness/bulk-read-contract.md` §4.
