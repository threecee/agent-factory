---
name: audit-choices
description: Audit decisions an implementing agent made beyond the brief, without changing code. Use before handoff or landing, when integrating delegated work, or when a working fix may rest on an unexamined choice.
---

# Audit Choices

Given a good decision, an agent implements it faithfully; wherever the task is
underspecified, it makes the decision itself — silently, and the diff won't
flag it. Reviewing thousands of changed lines doesn't scale, and it inspects
the execution, which was probably fine. The audit that scales is of the
**choices**: surface every decision the implementer made on its own, judge
that list, and record the verdicts.

## Trigger

Use when an implementation contains choices the user did not explicitly make.

## Checklist

Follow the Workflow below without modifying the audited tree.

## Workflow

1. **Elicit and trace back.** When an implementer reports done, ask: *"While
   working on this, which choices did you make that you're not confident of?
   List all."* — but treat the self-report as a starting point, not the
   boundary: agents under-report, and a digest of the handback written by a
   helper is input of the same rank, never the boundary either. Trace the
   history yourself — the session's steps, subagent reports, diffs, commits
   — and collect every decision that
   is in the work but not in the original spec or prompt. Sweep the
   architectural categories, not just the suspect fixes: data shapes and
   formats, storage and naming schemes, API contracts and their error
   behavior, dependencies added, concurrency/perf tradeoffs, scope
   interpretations, patterns future code will imitate. Auditing your own
   session, trace your own steps the same way. Choices the plan explicitly
   delegated to the implementer are discretion, not audit items.
2. **Triage each choice on evidence.** Forced by the plan, or invented?
   Invented ones get the scrutiny: is this the general solution, or a fix
   shaped to the one failing case? Verdict per choice: **sound**, **unsound**,
   or **needs-user** — and alongside the verdict, a **confidence**: how sure
   the audit is that the user would have made this same call. Confidence is
   what ranks the report. Reserve needs-user for genuinely user-only calls
   (taste, product direction, external cost); every needs-user entry records a
   recommended provisional call that is reversible, so an unsupervised caller
   can proceed without waiting. The audit never stalls a run: each entry is a
   judgment handed over for action or review, not a question that halts.
3. **State the corrected decision, don't sketch a patch.** For each unsound
   choice, the entry names the decision the work should be redone from — the
   property that must hold in general — not an edit to layer on top. A patch
   on top of a bad decision preserves the decision; the redo itself is the
   caller's, after the ledger is reviewed.
4. **Bank every choice in the ledger** (below), and promote load-bearing
   sound ones into the plan's handoff so later passes inherit them as givens
   instead of re-deciding.
5. **Present the ledger: grouped by verdict, ranked by confidence.** The
   audit's deliverable is the ledger, handed to whoever acts next — the
   calling workflow mid-run, the user at run's end. Each verdict group maps
   to an action — needs-user (decide, with the provisional calls), unsound
   (redo, with the corrected decisions), sound (acknowledge: the
   architecture the user now owns) — and within each group choices are
   ranked by confidence, least confident first. When the ledger is long,
   open the report with the two or three least-confident choices overall,
   whatever their group: the "review these first" line. Sound is not
   skippable. Only trivial discretion (internal naming, cosmetic calls)
   compresses to a one-line count.

   **Write every entry ELI5 — by default, not on request.** The reader
   didn't live the session: write each entry in the
   [eli5](../eli5/SKILL.md) register — a concrete scenario walked end to
   end (the triggering event, what the work does today, what the unbuilt
   alternative would do), every term of art defined at first use, and
   pseudocode at the level of the decision when the choice is about control
   flow, ordering, or timing. "A gated ask is dropped, not deferred" is a
   headline, not an entry. A compressed entry that makes the user ask
   "explain this one" has failed; the ledger must stand alone without the
   diff, the spec, or the transcript.


Ledger format, rules, and detailed examples: [full guide](references/full-guide.md).
## Done

The audit is done when every invented choice in the pass has a ledger entry
with an ID and a verdict, every unsound entry names the corrected decision to
redo from, every needs-user entry carries a reversible provisional call, every
scenario is stored beside the ledger rather than in a scratchpad, and the
ledger has been presented — grouped by verdict, least-confident-first within
each group, every entry readable ELI5 without follow-up questions — to
whoever acts next, with the tree untouched. A handback that shows the diff
instead of the choices, or a "fix" applied during the audit, is not done.
