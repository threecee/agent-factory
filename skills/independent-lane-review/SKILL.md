---
name: independent-lane-review
description: Run a fresh-context, multi-model adversarial review of a lane before train assembly or on demand. Reviewers re-derive brief compliance and proof from git without trusting the builder narrative.
---

# Independent Lane Review

Before the lander assembles a train (`docs/OPERATIONS.md` §5), dispatch a **multi-model
adversarial panel** — 2–3 fresh subagents per lane, each on a **different model** — to
re-derive the lane's result from its diff, its brief, and git, *not* from the
orchestrator's account of it. Each panellist runs the same three checks independently, and
**cross-model agreement is the confidence weight** on what they find. The panel's verdict
feeds the lander's accept/reopen decision **alongside** the orchestrator's own §5 check,
never instead of it.

Detailed panel composition, scoring, dispatch, and trial protocol: [full guide](references/full-guide.md).
## What each reviewer re-derives

Every panellist independently derives three findings from the diff and the tree at
`{BASE_SHA}`/`{HEAD_SHA}` — not from any prose the lane wrote about itself:

1. **Diff-to-brief fit.** Does `git diff {BASE_SHA} {HEAD_SHA}` actually implement the
   stated root cause / requirements? A fix that changes a different surface than the one
   the brief traced the defect to is a finding even when the suite is green.
2. **The red→green proof is real.** `docs/OPERATIONS.md` §6 binds every bug fix to a
   failing-first criterion — red on the unfixed code, green on the fix, asserting on the
   failure message. The reviewer does **not** take the lane's word that this happened. It
   re-runs the cited test itself: `{BASE_SHA}` must **fail** (for the *right* reason, §6
   step 4), `{HEAD_SHA}` must **pass**. A proof that only passes at head, or whose base
   failure is for an unrelated reason, is not a real red→green.
3. **Scope creep.** Anything in the diff beyond what the brief scoped — an opportunistic
   refactor, a second unrelated fix, a new dependency, a baseline bump — is surfaced for
   the lander to weigh, not silently accepted because the suite stayed green.

The rubric also folds in three **quality lenses** — subtract-before-add,
minimize-reader-load, migrate-then-delete (defined in [lane-reviewer.md](lane-reviewer.md)).
Their findings are advisory unless one crosses into a correctness or scope problem.


## Checklist

Use the re-derivation questions above with identical crafted context, independent proof runs, and a final adjudication against git.
## When to use

- **Standing (on trial):** once per lane, before the lander assembles a train
  (`docs/OPERATIONS.md` §5), for every lane whose branch will enter it.
- **On demand:** any time a single lane's self-report is load-bearing and you want it
  checked by reviewers who never heard the lane's story — a bug-fix lane whose root cause is
  contested, a lane that thrashed, a lane whose branch may have moved under it.

The gap this closes is concrete. Lanes have shipped a secret literal their own pre-commit
suite could not see; a lane's branch has silently come to point at a force-pushed-away
commit; a landing merge has silently done nothing on its first attempt. None was caught by a
fresh reader — each was caught only because the same orchestrator happened to re-derive
state from disk. A standing multi-model cold review catches this class without relying on
that vigilance, and weights each finding by whether more than one model could re-derive it.


## Done

Done when every finding is adjudicated from git, agreement is recorded as confidence rather than majority vote, and the lane has an accept-or-reopen recommendation.
