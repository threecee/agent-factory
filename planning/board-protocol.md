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
| Item obsoleted by evidence | Close with the evidence cited, → Dropped/Done, archive |

API-created items get no automatic status — set it explicitly. `gh project
item-list` defaults to 30 rows — always pass `--limit 100`.

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
