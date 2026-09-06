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
| Train lands | Boarded items → Done (closing the issue auto-moves it), then **archive**; then the derived-view check below, if the project has such a view |
| New deferred intention | File it with a full body, status → Deferred |
| Needs owner ruling | Status → Decision needed |
| Scope/product question surfaces mid-lane | File a decision item NOW (evidence, boundary, recommendation), status → Decision needed; the lane continues its reversible part (execution-contract.md §4) |
| Task parked after its second round | The item stays In flight until the split is filed; file each split as its own item (Planned, own round counter), link the parked report from the original body, then move the original → Deferred (gate: the splits) or → Decision needed when the failure is a spec question |
| Item obsoleted by evidence | Close with the evidence cited, → Dropped/Done, archive |

API-created items get no automatic status — set it explicitly.

## Authority, pagination and derived views

1. **The Project is the authority.** Every other rendering of the plan — a
   progress page, a README status table, a wiki, a generated dashboard — is
   a derived view. When a view and the Project disagree, the view is wrong
   by definition; correct the view, never the Project to match it. No view
   is required; a project that has none skips every rule below that mentions
   one.
2. **Enumerate the whole board, never a default page.** `gh project
   item-list` returns 30 rows unless told otherwise, and a sweep that reads
   30 of 80 items silently leaves 50 untouched. Always pass an explicit
   limit ABOVE the item count and assert the result is shorter than the
   limit:

   ```sh
   gh project item-list <number> --owner <owner> --limit 200 --format json \
     | jq -e '.items | length < 200' >/dev/null || echo "raise --limit"
   ```

   A count equal to the limit means the page was truncated: raise the limit
   and re-read before acting. The same rule holds for the GraphQL API
   (follow `pageInfo.hasNextPage` to the end) and for any view's export.
3. **Derived-view check at landing (only if a view exists).** After the
   sweep, for every boarded issue compare three facts: the issue's state on
   GitHub, its Status on the Project, and what the view shows (status and,
   if the view carries one, the landing SHA). Every difference is recorded
   in the train's choices protocol and fixed on the view. The failure it
   guards against — illustrative, not a recorded incident: an owner reads a
   stale "in progress" on a page and re-orders work that already landed.
   Provenance: the source factory's issue tracker named this as a CANDIDATE
   lander duty; it was not found as an explicit duty in that factory's
   operational law, it was never automated there, and the factory ships no
   page adapter. Medium confidence — a recommended manual check, and the
   lander's checkpoint (verification/lander-duties.md §5) points here.
4. **A view must not become a second plan.** A view may show more (burn-
   down, grouping, links) but never carries a status the Project lacks; new
   intentions are filed on the Project first.

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
