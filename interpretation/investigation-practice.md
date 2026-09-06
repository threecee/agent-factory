# Investigation practice

- **Instrument first.** Reproduce with attribution before hypothesizing.
  Enumerate the reachable set instead of concluding from one observed bucket.
- **Root-cause before fix.** A bug lane documents the root cause before any
  fix is proposed; three failed DIFFERENT hypotheses mean the model of the
  defect is wrong — stop and escalate, never attempt a fourth.
- **Second opinions are cheap.** Read-only investigation agents (different
  model family than the implementer) fed with precise questions and file
  scopes return root causes in minutes; falsify THEIR claims with a direct
  check before acting (an investigator once reported a workflow "active on
  every push" — the file's trigger block said otherwise).
- **Probes carry the caller's arguments** — copy the call site verbatim.
  A probe with its own defaults tests a different program.
- **Never signal-probe a live process** without a handler — attach by
  file-mtime and sampling profilers instead.

## Identity and history — evidence follows the consumer

This section owns the principle; `verification/falsification.md` §7–§9 own
the red/green shape, and `verification/examples/identity-and-history.md`
carries the worked examples and a runnable model.

1. **A gate reads what the consumer reads.** Before counting stored
   artifacts (rows, snapshots, receipts), write down the consumer's selection
   — key, status filter, precedence between producers — and use exactly that.
   A count over rows the consumer never selects measures a different program:
   a gate that rejected a source for 666 unavailable rows was contradicted by
   the read path, which showed one unavailable scope. Deleting the history to
   get green hides the cause; allowing every unavailable row hides live gaps.
2. **Three populations, three verdicts.** Split stored evidence into
   *history* (a row the consumer no longer selects because a valid successor
   exists), *current* (the row the consumer selects now) and *promised*
   (identities the plan or configuration owes but nothing has delivered).
   History passes the history check; a current unavailable result under a
   role that promised delivery fails; a promised-undelivered identity fails
   with its own message. Report all counts in the receipt, always. A
   deliberately fake role is a different evaluation type, not a pass — see
   `verification/evaluation-readiness.md` (introduced by PR4).
3. **A large history count is a finding, not noise.** Precision is not
   silence. The 666 rows above were later traced to a producer that never
   converged (the successor rows were written by a fallback path, the
   promised producer never finished) — the same defect, not dead history.
   When the history count under a configured role is large or growing, open
   a read-only investigation (`planning/investigation-brief-template.md`,
   introduced by PR9) before trusting the green verdict.
4. **Newest is not identity.** File mtime, row insertion order and "latest"
   are proxies that copies, retries and parallel writers reorder. If the
   consumer resolves an artifact by a content key (a digest of its inputs, a
   revision it computes), the gate resolves by the same key and rejects
   "no artifact for this key" rather than falling back to the newest file.
   The proven case: a copy reversed mtimes so a mid-index snapshot outranked
   the completed one; the reader was keyed by digest and had never been wrong.
5. **Incremental plans diff by identity, never all-or-nothing.** When inputs
   move under a long-running plan, split the work by exact identity: reuse
   exact hits, recompute only the changed and new identities, retire the
   no-longer-desired ones, and rebase the progress meter from the durable
   receipt (never publish completed below what is stored). A weaker result
   (fallback, floor, unavailable) with the same exact identity never
   supersedes a stronger current one. Restarting at zero is a regression the
   store should refuse, and refusing it is what turns "stale" into
   "terminal failure" if the plan ignores the refusal.
6. **Scope silence to what actually competes.** A "wait until quiet" barrier
   is defined per unit of contention (the same case, the same key space),
   never deployment-wide — a global barrier lets an unrelated job starve
   this one indefinitely, and a barrier alone does not converge a plan whose
   inputs keep moving.

Provenance and limits: rule 4 is a landed, falsified correction in the
source factory. Rules 1–3 describe an OPEN source-factory issue (the gate at
the pinned revision still counts every unavailable row); rule 5 is landed in
one producer but its publisher still compares the whole identity set, and
the convergence measurement on the large case is pending. The examples file
states these limits per example; do not cite this section as proof that the
source factory has closed them.
