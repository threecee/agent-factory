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
| Needs owner ruling | Status → Decision needed, with a decision brief (§ Decision needed) |
| Scope/product question surfaces mid-lane | File a decision item NOW (evidence, boundary, recommendation), status → Decision needed; the lane continues its reversible part (execution-contract.md §4) |
| Task parked after its second round | The item stays In flight until the split is filed; file each split as its own item (Planned, own round counter), link the parked report from the original body, then move the original → Deferred (gate: the splits) or → Decision needed when the failure is a spec question |
| Finished train, no landing authority | Train held intact; decision brief on the blocked item; Status → Decision needed; ONE `held` notification (§ Notifications) |
| Owner rules on a brief | Ruling recorded on the item verbatim; Status → In flight / Done / Dropped per the ruling; ONE `decided` notification |
| Train lands under standing authority | Boarded items → Done, archive; ONE `landed` notification; no ruling requested |
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

## Decision needed

Decision needed is a state with a document, not a label. An item enters it
only with a decision brief filed from `decision-brief-template.md` on the
item itself: problem → evidence → options with consequences → one
recommendation → what continues meanwhile → what is held. The owner rules
on the item; the ruling is copied there verbatim if it arrived elsewhere.

1. The brief is readable without the conversation; banked evidence only.
2. Reversible work never waits (investigation, assembly, verification,
   banking). Only the irreversible step is held: the push, the deletion,
   the expensive run.
3. A finished train is held ONLY when no landing authority covers it or a
   hold category fires. Whether authority exists is answered by the
   operator's landing policy (`../user-level/landing-policy.example.md`,
   inactive until the owner activates it), never by this protocol and never
   by a template; the lander's hold path is
   `../verification/lander-duties.md` §7. Installing the factory grants no
   authority; the default is the hold.
4. A hold is measured (start, ruling, length) and cited by the train's
   choices ledger. Long repeated holds are the owner's evidence for or
   against granting standing authority; the brief does not ask for it.
5. Standing authority moves the push decision only. The verification
   (`../verification/lander-duties.md` §1 steps 1–9) and the non-removable
   hold floor (`../user-level/landing-policy.example.md` §2 `holds:`, the
   one home of that list) are untouched by it: a train any floor entry
   fires on is held with a brief exactly as if no policy existed.

## Notifications

One notification per state transition, never one per poll, retry or
session resume.

1. Key: `<item id> <train HEAD sha | none> <transition>`; transitions are
   `held`, `decided`, `landed`, `reverted`. The key is written on the item
   (in the brief, the ruling, the landing comment) BEFORE the notification
   is sent.
2. Before sending, read the item: if the key is already there, do not send.
   A watcher that wakes twice, a wrapper that retries, a session resumed
   from a transcript — all of them find the key and stay silent.
3. The channel is local, not fixed here. With an ACTIVE landing policy it
   is `notify.channel` there. Without one — the default path, where no
   policy file exists — the channel is the item itself: the comment that
   carries the key (the brief, the ruling, the landing comment) IS the
   notification, and the owner's subscription to the board or issue
   delivers it. The key is portable across channels.
4. A notification is a pointer to the item, not a summary of it: item id,
   transition, train SHA, one line. The reader opens the brief.
5. A train re-assembled with a different HEAD is a new key; its `held`
   notification is legitimate even if the previous one was answered.

Worked check: a train held at 03:00 gets `#X abc123 held`; the fix is
updated on the same item at 05:00 (same options, same HEAD → NO new
notification, it is an update comment); the owner rules at 06:04
(`#X abc123 decided`); the push lands at 06:10 (`#X abc123 landed`). Three
notifications for one item, however many times the watcher polled.

A landing under standing authority changes nothing above: the Project stays
the plan and any progress page stays a derived view, checked after the
sweep exactly as "Authority, pagination and derived views" item 3 says. No
new page is required by the authority protocol.

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
