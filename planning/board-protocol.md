# Board protocol — GitHub Projects as planning truth

The project board is not a mirror of work; it IS the plan. If the board and
reality disagree, one of them is a bug to fix now.

## Statuses

Planned (has an approved spec, dispatch-ready) · In flight (a lane is working
it) · Deferred (valid intention, named gate) · Decision needed (owner must
rule) · Blocked–external (gate outside the org's control) · Done (built-in) ·
Dropped (rejected or obsolete — record WHY in the body).

## Transaction points (the part sessions historically drop)

| Event | Board action |
|---|---|
| Work dispatched | Real issue (promote drafts), status → In flight |
| Train lands | Boarded items → Done (closing the issue auto-moves it), then **archive** |
| New deferred intention | File it with a full body, status → Deferred |
| Needs owner ruling | Status → Decision needed |
| Scope/product question surfaces mid-lane | File a decision item NOW (evidence, boundary, recommendation), status → Decision needed; the lane continues its reversible part (execution-contract.md §4) |
| Task parked after its second round | The item stays In flight until the split is filed; file each split as its own item (Planned, own round counter), link the parked report from the original body, then move the original → Deferred (gate: the splits) or → Decision needed when the failure is a spec question |
| Item obsoleted by evidence | Close with the evidence cited, → Dropped/Done, archive |

API-created items get no automatic status — set it explicitly. `gh project
item-list` defaults to 30 rows — always pass `--limit 100`.

## Task identity and the round counter

The board item ID is the task's identity. The execution contract's two-round
limit (execution-contract.md §3) is counted on that ID: the wrapper reads
the previous handback for the same `task:` before dispatching, and a lane
with a new name on the same item is round 2, not round 1. A third dispatch
on the same item is a protocol violation unless the orchestrator has logged a
restart-from-document. A split creates new items, each at round 1; the
original item's body links the parked report so the history is one click
away from the plan.

## Body discipline

A Deferred body names: the problem, why it is deferred, and what unlocks it.
A Done/Dropped body cites evidence (commit SHA, line numbers, or the
superseding item). Refresh stale bodies when triaging — a board whose bodies
lie is worse than no board.

## Periodic triage

Run a full-board triage on a cadence (or on owner request): verify every
Planned/Deferred/Blocked item against CURRENT code with primary-source
evidence, move what changed, close what evidence has obsoleted, and bring
large deviations back to the owner rather than silently re-deciding them.
