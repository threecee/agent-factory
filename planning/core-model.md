# Core model — define why, what, how

Every piece of work moves through the same ladder. Skipping a rung is how
factories rot into vibes.

## The ladder

1. **Why — a board item.** Every intention lives on the GitHub Projects board
   (the planning source of truth, see board-protocol.md). An item's body must
   answer: what problem exists, why it matters, and — for anything not
   immediately buildable — what gate defers it and what would unlock it.
   An empty body is a planning bug.
2. **What — a full spec.** Everything with status Planned carries a spec:
   GOAL (one sentence), NON-GOALS, CURRENT STATE (file paths and line numbers
   the spec author personally verified — never remembered), CONTRACTS/SEAMS,
   STEPS (independently verifiable slices, each with its own verification
   gate), PLAYABLE CHECKPOINT (what a human can see/click and when), OPEN
   QUESTIONS (each with a recommended answer), and safety considerations
   where the domain has them. For risky or multi-slice features, run the
   write-spec ceremony: three independent drafters with distinct biases
   (fewest-slices / risk-first / seam-quality), then the orchestrator
   synthesizes — never anoints — a canonical plan.
3. **Owner approval.** Specs are approved by the product owner before
   dispatch. Approval of a MOVE (deferred → planned) is not approval of the
   PLAN; keep the two decisions separate.
4. **How — the standing lane brief.** Dispatch happens from ONE template
   (lane-brief-template.md), parameterized per lane: pinned repo SHA, own
   worktree, assigned ADR/migration numbers (or an explicit STOP rule),
   the spec as contract, the pregate block, the report schema. Briefs are
   never re-authored by hand per lane; drift in the template is a reviewed
   change.

## Decision hygiene

- Decisions of record go into ADRs (adr-and-numbers.md). Working decisions
  agents make on the owner's behalf go into the choices ledger
  (../interpretation/choices-ledger-README.md) — both exist precisely so the
  owner can review decisions instead of diffs.
- Anything the owner must rule on gets board status **Decision needed** and,
  when volume warrants, an interactive decision document (one card per
  decision: the problem, the plan, action buttons) rather than a chat scroll.
- Date everything with the actual current date; a future-dated approval is a
  governance bug an honest lane will refuse to build on. (This happened.)
