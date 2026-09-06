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
| Needs owner ruling | Status → Decision needed, with a decision brief (§ Decision needed) |
| Finished train, no landing authority | Train held intact; decision brief on the blocked item; Status → Decision needed; ONE `held` notification |
| Owner rules on a brief | Ruling recorded on the item verbatim; Status → In flight / Done / Dropped per the ruling; ONE `decided` notification |
| Train lands under standing authority | Boarded items → Done, archive; ONE `landed` notification; no ruling requested |
| Item obsoleted by evidence | Close with the evidence cited, → Dropped/Done, archive |

API-created items get no automatic status — set it explicitly. `gh project
item-list` defaults to 30 rows — always pass `--limit 100`.

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
   by a template. Installing the factory grants no authority; the default
   is the hold.
4. A hold is measured (start, ruling, length) and cited by the train's
   choices ledger. Long repeated holds are the owner's evidence for or
   against granting standing authority; the brief does not ask for it.
5. Standing authority moves the push decision only. The verification
   (`../verification/lander-duties.md` steps 1–8) and the non-removable
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
3. The channel is chosen locally in the landing policy (`notify.channel`),
   not here; the key is portable across channels.
4. A notification is a pointer to the item, not a summary of it: item id,
   transition, train SHA, one line. The reader opens the brief.
5. A train re-assembled with a different HEAD is a new key; its `held`
   notification is legitimate even if the previous one was answered.

Worked check: a train held at 03:00 gets `#X abc123 held`; the fix is
updated on the same item at 05:00 (same options, same HEAD → NO new
notification, it is an update comment); the owner rules at 06:04
(`#X abc123 decided`); the push lands at 06:10 (`#X abc123 landed`). Three
notifications for one item, however many times the watcher polled.

## Derived views

The GitHub Project is the plan. Any local or generated page that shows
progress — a dashboard, a static status page, a README table — is a VIEW
of it, and a stale view causes real damage: an item landed and closed on
the board still reads "in progress" on the page, and the owner orders the
same work again.

1. No derived page is required. If none exists, this section is empty for
   the repo.
2. If one exists, the board is authority and the page is checked against
   it after every board sweep (`../verification/lander-duties.md`
   § Derived views): item id, status, and the landing SHA the page claims,
   over the FULL item set with pagination (`--limit 100`; never a default
   page of 30).
3. A discrepancy is a bug in the page or its generator, recorded on the
   board as such; it is never resolved by editing the board to match the
   page.
4. A page is never promoted to a second plan: it has no statuses of its
   own, no items the board lacks, and no gate reads it.

Confidence: this check was a named candidate in the source factory's
retrospective and its landing scripts flip and archive board items, but
the source factory had not made the page comparison an explicit lander
duty at the time of writing. It is a recommended refinement, not a
routine with a track record.

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
