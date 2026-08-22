# The choices ledger — understand what was actually decided

Given a good spec, an agent implements it faithfully; wherever the spec is
underspecified, it decides SILENTLY — and the diff won't flag it. Reviewing
thousands of changed lines doesn't scale; auditing the CHOICES does.

## Protocol (a transaction point, same rank as the board)
- Every lane handback is audited with the `audit-choices` skill: the lane's
  mandatory `choices:` self-report is the starting point, never the boundary
  (agents under-report — trace the diff yourself).
- Entries go to `docs/choices/<train>.md`, committed WITH the train. One
  entry per invented decision: the choice (headline + walked ELI5 scenario),
  the gap that forced it, the reach, verdict (sound/unsound/needs-user),
  confidence.
- **Unsound is resolved before assembly.** Needs-user gets a reversible
  provisional call — the run never stalls.
- The landing summary presents the ledger to the owner grouped by verdict,
  least-confident first. Flag the ones worth the owner's eyes explicitly.
- Banked is settled: never re-list, never re-decide.
- Orchestrator errors the lanes' falsification catches (wrong dates, stale
  instructions) belong in the ledger too, attributed honestly.
