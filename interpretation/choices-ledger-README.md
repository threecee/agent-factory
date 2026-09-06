# The choices ledger — understand what was actually decided

Given a good spec, an agent implements it faithfully; wherever the spec is
underspecified, it decides SILENTLY — and the diff won't flag it. Reviewing
thousands of changed lines doesn't scale; auditing the CHOICES does.

This file owns the factory's choices protocol: when the audit runs, what an
entry is, where its rationale lives, and how a lane's self-report becomes a
train entry. The `audit-choices` skill owns HOW a choice is found and judged;
`harness/report-schema.md` owns the shape of the lane's self-report. Neither
duplicates the rules below.

## 1. Protocol (a transaction point, same rank as the board)
- Every lane handback is audited with the `audit-choices` skill: the lane's
  mandatory `choices:` self-report is the starting point, never the boundary
  (agents under-report — trace the diff yourself). A handback digest written
  by a helper is input of the same rank: it shortens the reading, it does not
  bound the audit.
- Entries go to `docs/choices/<train>.md`, committed WITH the train. One
  entry per invented decision: the choice (headline + walked ELI5 scenario),
  the gap that forced it, the reach, verdict (sound/unsound/needs-user),
  confidence.
- **Unsound is resolved before assembly.** The corrected decision is written
  into the entry BEFORE the fix round is briefed, so the fix is judged against
  a stated decision rather than the decision being inferred from the fix.
- Needs-user gets a reversible provisional call — the run never stalls.
  "Never stalls" is bounded by the lane's authorization: a STOP rule in the
  brief (an inseparable semantics change, an unassigned number) still stops;
  the provisional call covers only what is reversible.
- The landing summary presents the ledger to the owner grouped by verdict,
  least-confident first. Flag the ones worth the owner's eyes explicitly.
- Banked is settled: never re-list, never re-decide.
- Orchestrator errors the lanes' falsification catches (wrong dates, stale
  instructions) belong in the ledger too, attributed honestly.
- Assembly and verify findings are entries too. A red gate on the assembled
  train that no lane's proof set ran — a reader of moved source, a baseline
  bound to a file path — is recorded as an orchestrator entry with its fix
  commit, so the next lane of that shape inherits the lesson as a given.
- A mechanical lane (a version bump, one documentation row) with no choices
  of its own gets one line in the protocol, not an empty ritual.
- A guard denial the orchestrator overrode, and every switch use, is an
  orchestrator entry (`O-<n>`) with the rule id, the reason and the
  events-log line it corresponds to; a switch without a ledger entry is a
  finding at landing (../harness/guards.md §4).

## 2. One ID per choice, everywhere it is mentioned
- A choice gets a stable ID when it is first written down and keeps it:
  `<lane>-<n>` for a lane's choices (`routes-split-3`), `O-<n>` for
  orchestrator choices, numbered in order of appearance. The fully qualified
  form `<train>/<lane>-<n>` is unique across the repo's history.
- The lane numbers its own `choices:` entries. Choices the audit finds that
  the lane did not report continue the lane's sequence and are marked
  `(found by audit)` — never a second numbering, never a renumbering.
- The same ID appears in every place the choice is mentioned: the lane's
  `choices:` self-report, the lane's scenario sidecar, the train protocol, a
  fix-round brief, the fix commit message (`fixes <train>/<lane>-<n>`), and
  any later amendment. A reader who meets the ID in any of them can reach the
  others with `grep` and `git log --grep`, without the conversation.
- An amended verdict keeps its ID. The amendment is appended under the same
  heading, dated, with the proof that forced it. A new ID would sever the
  proof from the decision it proves.

## 3. Where the scenario lives: in the protocol, or in a banked sidecar
The walked scenario is the storage format, not presentation polish
(`audit-choices`, "ELI5 survives every rewrite"). Where it is stored:

1. The train protocol carries the scenario inline for every **unsound** and
   **needs-user** entry, and for every sound entry the owner is asked to look
   at. These are the entries the owner reads; each must stand alone.
2. A sound entry may carry headline + verdict + confidence + gap in the
   protocol and keep its scenario in the lane's sidecar `<lane>-choices.md`
   — **only if the sidecar is durable**: committed under
   `docs/choices/<train>/` with the train, or banked in the artifact bank
   (`harness/artifact-bank.md`) with the bank path written
   into the protocol. Sidecar sections are keyed by choice ID and headline.
3. A path into an orchestration scratchpad, a session, or a chat is not a
   reference. "Scenarios in the session sidecars" satisfies nothing: the next
   operator has no session. If a sidecar was never banked, the scenarios are
   copied into the protocol before the train lands — the lander checks this
   as part of `verification/lander-duties.md`.
4. Proof lives with the verdict. A corrected entry names the proof a stranger
   can re-run: test id, commit, log path in the bank. "Fixed on the train"
   without an identifier is a headline, not an entry.

## 4. From handback to protocol
1. The lane files `choices:` in its result (ID, headline, verdict,
   confidence, one-line gap) and writes the scenarios to its sidecar; the
   terse shape is `harness/report-schema.md` (rule 5), with the `id:` field
   of §2 first in every entry. One field name, `choices:`, in one language;
   no parallel field for the same thing.
2. The orchestrator runs `audit-choices` on the handback. Self-report and
   digest are inputs; the diff and the commits are walked regardless.
3. Entries are appended to `docs/choices/<train>.md` under the lane's
   heading, IDs preserved. Unsound → fix round before the train is
   assembled (rule 1); the fix commit cites the ID.
4. Assembly and verify findings are appended as orchestrator entries with the
   same discipline, each with its fix commit and the test or gate id that
   went red.
5. The protocol is committed with the train; the landing summary presents it
   (rule 1). A protocol that cites a scratchpad is not ready to land (§3).

## Worked example
`examples/simplification-review.md` walks one depersonalized train from the
consumer inventory through an unsound choice to the corrected choice and its
proof, with one ID carried through self-report, protocol, amendment and fix
commit — and ends with what a reviewer who was not in the session can find.
