---
name: independent-lane-review
description: Use before a landing train is assembled, or on demand for one lane, to run a multi-model adversarial panel of fresh-context reviewers that re-derive whether a lane's diff matches its brief and its red→green proof is real — never trusting the orchestrator's narration, with cross-model agreement as the confidence weight.
---

# Independent Lane Review

Before the lander assembles a train (`docs/OPERATIONS.md` §5), dispatch a **multi-model
adversarial panel** — 2–3 fresh subagents per lane, each on a **different model** — to
re-derive the lane's result from its diff, its brief, and git, *not* from the
orchestrator's account of it. Each panellist runs the same three checks independently, and
**cross-model agreement is the confidence weight** on what they find. The panel's verdict
feeds the lander's accept/reopen decision **alongside** the orchestrator's own §5 check,
never instead of it.

**Core principle:** the reviewers must start cold, and they must not share the builder's
blind spots. A lane's "done" claim checked only by the orchestrator who wrote its brief and
narrated its whole arc is checked by a party that already believes the narration. And a
single reviewer on the same model family that authored the code tends to miss what that
family tends to miss. So the panel's adversarial signal comes from **model diversity, not
assigned personas**: same crafted context, same rubric, different models — and the findings
that survive independent re-derivation on more than one model are the ones to trust most.

## The panel: who reviews, on what models

Dispatch **2–3 reviewers per lane**, each a fresh agent on a **different model**, per the
operator's dated model policy (`harness/model-policy.md` §2, the "investigation and
second-family review" role; the live file is `~/.claude/model-policy.md`). The policy names
the models; this skill names only the requirement — at least two model FAMILIES, and a
third from yet another family where the policy has one. Every panellist gets the **identical** crafted
context and rubric; the only thing that differs is the model. The dispatch template
([lane-reviewer.md](lane-reviewer.md)) carries a `[REVIEWER_MODEL]` slot so each dispatch
names its model.

Why diversity rather than personas: this factory's own whole-branch reviews have
repeatedly shown two model families catching *different* silent fail-open defects a green
suite could not see — an OpenAI pass and an Anthropic pass converging on distinct axes
(`docs/RESUME-STATE.md` records several waves of this). One reviewer model shares blind
spots with the one builder model; a second family does not. Assigning personas to
same-model reviewers does not buy that — the diversity has to be in the weights.

## Why every reviewer gets crafted context, never your history

Each panellist is dispatched with **exactly four inputs and nothing else**:

- `{DESCRIPTION}` — one or two lines: what the lane was supposed to change.
- `{REQUIREMENTS}` — the lane's stated requirements and its `ADR-NNNN` / design-note
  reference. The contract the diff is measured against.
- `{BASE_SHA}` — the commit the lane branched from (`origin/main` at dispatch).
- `{HEAD_SHA}` — the lane's branch head.

No panellist is **ever** given the orchestrator's conversation history. That history is the
thing being checked — it carries the lane's self-report, the rationalizations offered along
the way, and the orchestrator's own running conclusion. Feeding it to a reviewer reproduces
the blind spot this skill exists to close.

For the same reason, **no panellist is a fork.** A `subagent_type: "fork"` inherits the
orchestrator's full context and would defeat the mechanism. Each panellist is a **fresh**
agent — `subagent_type: "general-purpose"` (or `"claude"`) on its assigned model — whose
only knowledge of the lane is the four inputs above and what it reads from git itself.

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

## Cross-model agreement scoring

Collect the panellists' findings and rank each by how many independently surfaced it:

- **CONFIRMED-HIGH** — surfaced independently by every panellist. It survived re-derivation
  on more than one model; treat it as real. A CONFIRMED-HIGH correctness or scope finding
  blocks accept.
- **PLAUSIBLE** — surfaced by only one panellist. It gets **one adjudication pass**: a
  different panellist, or the orchestrator, re-derives it from git to confirm or dismiss,
  and records which. A PLAUSIBLE finding neither blocks nor is dropped until adjudicated.

Agreement weights attention; it is **not** a majority vote to average. A lone reviewer can
still be right — the adjudication pass exists precisely so one true finding is not
discarded — and unanimous reviewers can still be wrong, so re-derive a contested
CONFIRMED-HIGH from git if the orchestrator disagrees. The scoring ranks what to look at
first; **git is the arbiter.**

The panel returns one **verdict** per lane: **accept** (no unadjudicated PLAUSIBLE, no
CONFIRMED-HIGH correctness/scope finding) or **reopen-with-findings** (the ranked findings,
each tagged CONFIRMED-HIGH or PLAUSIBLE, named concretely — file, test, command — so the
lane can act without re-deriving them).

## How to dispatch

```bash
BASE_SHA=$(git -C <wt> rev-parse origin/main)   # the base the lane branched from
HEAD_SHA=$(git -C <wt> rev-parse HEAD)           # the lane's branch head
```

Dispatch 2–3 fresh subagents, **each on a different model**, each filling
[lane-reviewer.md](lane-reviewer.md) with the SAME `{DESCRIPTION}`, `{REQUIREMENTS}`,
`{BASE_SHA}`, `{HEAD_SHA}` and its own `[REVIEWER_MODEL]`. They run in parallel and do not
see one another. Then score agreement across their returns and act on the verdict at §5:

- **reopen-with-findings** → the lane fixes the named findings (CONFIRMED-HIGH first,
  adjudicated PLAUSIBLE next) before the branch enters the train. Do not land it on the
  strength of the orchestrator check alone.
- **accept** → proceed with the §5 assembly checks (migration heads, ratchet, full verify).
  The panel does not replace them; it runs before them.

## Trial protocol

The panel upgrade is on **trial**, not yet standing law. First outing: the **first train of
the next session**, run alongside the existing single-orchestrator §5 check. Keep the panel
only if **agreement-scoring demonstrably re-ranks findings versus a single reviewer** — it
produces at least one CONFIRMED-HIGH a lone reviewer would have left un-weighted, or one
PLAUSIBLE the adjudication pass correctly promotes or drops. If a run shows the panel
returns nothing a single fresh reviewer did not, revert to the single-reviewer form and
record why. Log the trial outcome in the lane's report so the keep/revert decision is
evidence, not preference.

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

## Red flags

**Never:**
- Give any reviewer the orchestrator's conversation history — it defeats the mechanism.
- Dispatch a panellist as a `fork` — a fork inherits the very context they must not have.
- Run every panellist on the same model — the diversity **is** the mechanism; same-model
  panellists reproduce each other's blind spots. Personas are not a substitute.
- Average the panel into a majority vote — agreement weights attention; a lone true finding
  still gets its adjudication pass, and git, not the tally, is the arbiter.
- Let a reviewer accept the lane's *narration* of red→green — each must re-run the proof
  itself against `{BASE_SHA}` and `{HEAD_SHA}`.
- Treat the verdict as replacing the §5 orchestrator check or the assembly gates — it runs
  alongside them, before them.

**If the reviewers and the orchestrator disagree:** the disagreement is the signal.
Re-derive the contested point from git, not from any narration.

See the dispatch template at [lane-reviewer.md](lane-reviewer.md).
