
This is about architecture more than bugs. An implementation can work
perfectly and still rest on decisions the user never made — a data shape, a
storage location, a dependency, an API contract, a tradeoff of memory for
speed — and every one of them is load-bearing for future work. The user needs
to know them not because they're wrong, but because they now own them.

This is purely a decision audit — it is not about modifying code, and it can
be called at any time. The job is to **trace back**: walk every step this
session has taken, and every step each subagent took (a live implementer
traces its own; otherwise reconstruct from its reports, transcripts, and
diffs), and surface every single decision that was made on the user's behalf
that was not in the original spec or prompt. The ledger of those decisions
replaces reading the code as the user's review surface — that is the whole
point. Acting on the verdicts (redoing an unsound choice, applying a
provisional call) belongs to the caller: the implementing workflow mid-run,
or the user after reading the report.

Two ways in, same audit:

- **Called by a workflow** (per pass or per slice): audit that pass, append
  its entries to the ledger, and return; the workflow presents the
  accumulated ledger when it hands back.
- **Called directly by the user**: audit the whole body of work in front of
  you (session, branch, or named change) and present the report immediately.
  Recommend; change nothing.

## The Choices Ledger

A dedicated file that outlives every pass: `choices.md` beside the plan
(`specs/<feature>/choices.md` when a spec owns the work). In the factory the
ledger is the train protocol, `docs/choices/<train>.md`, and
`interpretation/choices-ledger-README.md` owns its protocol (IDs, where the
scenario is stored, handback → protocol); the entry format is the same. One
entry per audited choice:

- **ID** — stable from first mention: `<lane>-<n>` (or `O-<n>` for the
  orchestrator's own), continued — not restarted — for choices the audit
  finds that the implementer did not report. The same ID goes into the
  self-report, the sidecar, the ledger, the fix commit and any amendment.
- **When** — pass or commit it landed in.
- **The choice** — a one-line headline, then the ELI5 scenario: the
  triggering event, what the work does today, what the unbuilt alternative
  would do, with terms of art defined in place.
- **The gap** — what the plan left unspecified that forced it.
- **The reach** — what future work this decision constrains or enables; why
  the user needs to know it exists.
- **Verdict** — sound / unsound / needs-user, with a one-line why. For
  unsound: the corrected decision to redo from. For needs-user: the
  recommended provisional call and how to reverse it.
- **Confidence** — how sure the audit is that the user would have made the
  same call (low / medium / high). Ranks the report, ascending.

Rules of the ledger:

- Banked is settled: a choice already in the ledger (or promoted into the
  plan) is a given for later passes — never re-listed, never re-decided.
- The ledger is a plan-quality signal. Entries clustering around one slice or
  area mean the plan is foggy there — reslice or send that part back through
  the spec rather than triaging the same class of choice forever.
- **ELI5 survives every rewrite.** The entry format above — headline plus the
  walked scenario with terms defined in place — is the *storage* format, not
  presentation polish. When entries are consolidated, merged, re-audited at
  close, or copied into a final ledger, each surviving entry keeps (or
  regains) its full scenario. The known failure mode is exactly this
  compression: a closeout rewrite that shrinks banked entries to their
  headlines produces a ledger the reader must interrogate — "The checkpoint
  loads rows in mailbox order and rejects the list when a later reference
  has an earlier createdAt" reads as settled, but only the walked version
  (two sessions, per-session sequence numbers that can't be compared, the
  shared insert-timestamp clock) lets a reader actually judge the choice. A
  consolidation that drops scenarios has failed even if every fact survives —
  and so has one that keeps the scenario but leans on labels the build
  invented ("the retry envelope", "the evidence seam") without defining them
  where they're used.
- **The scenario is stored where the ledger is stored.** An entry whose
  scenario lives only in a scratchpad, a session, or a chat has no scenario:
  the next reader has none of those. Unsound and needs-user entries carry
  the scenario inline; a sound entry may point to a sidecar only if the
  sidecar is committed or banked beside the ledger under the same ID. A
  corrected entry names the proof a stranger can re-run (test id, commit,
  banked log), and an amended verdict keeps its ID with the amendment
  appended and dated — a new ID severs the proof from the decision.

## Rules

- **"It works" is not a verdict on the choice.** The recurring smell is the
  coincidental fix: a resized buffer, bumped timeout, or special case whose
  magnitude happens to cover the failing input while the underlying cause
  stays dormant. Ask what property *guarantees* the fix in general; if the
  answer is "this case passes," the choice is unsound even though the code is
  green.
- Declared success is the point of maximum risk — the implementer's confidence
  is highest exactly when its unexamined choices are about to be merged. Never
  skip the audit because the result looks clean.
- An empty list on nontrivial work is a red flag, not a pass. Probe: what did
  the task leave unspecified? Something filled those gaps.
- The audit changes no code, tests, or build state. Finding an unsound choice
  is the deliverable, not a license to fix it — record the corrected decision
  and leave the tree exactly as audited, so the ledger and the tree agree on
  what the caller is deciding about. Evidence-gathering is fair game: read
  anything, run the existing tests, write transient probes — but remove every
  probe before handback.
