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
  every push" — the file's trigger block said otherwise). The brief shape
  for such an agent is `../planning/investigation-brief-template.md`.

## Investigate before the fix lane gets its mandate

Why a read-only investigation precedes the fix brief when the cause is
uncertain; the brief itself is `../planning/investigation-brief-template.md`,
the trust rules are `../verification/falsification.md` §7–§9.

- **Coincidence recruits the wrong fix.** A job that stops after many model
  calls, at the same minute a neighboring job finishes, invites a brief that
  orders "wait for the neighbor". In the worked example in the template,
  a query on the frozen evidence showed the suspected neighbors never wrote
  to the identity the job depends on; the driver was input arriving during
  the run, and a second, unhypothesized mechanism (a retry that tried to
  reset already-stored progress) made every retry dead on arrival. A fix
  brief written from the coincidence would have built a barrier that moves
  the failure to the deadline.
- **Pin the source and freeze the evidence first.** The investigator reads a
  copied datastore, the run log and the manifest at the commit the run was
  built from (`../harness/artifact-bank.md`, introduced by PR5). Evidence
  that keeps moving under the investigation cannot refute anything.
- **Ask competing questions, not open ones.** "Which of path X and path Y
  wrote row R at time T" is answerable by a query; "why did it fail" is
  answered by an essay. The orchestrator's own hypothesis enters the brief
  as one row in the hypothesis table, never as the framing.
- **Every hypothesis ends supported, refuted or unknown — with a source.**
  A refutation cites the query or line that rules the mechanism out. An
  "unknown" names the observation gap (the exception that was not persisted,
  the earlier run's database that was not in the package). Both are
  findings; a guess is not.
- **Preserve the gaps into the mandate.** What the investigation could not
  decide becomes an observability criterion in the fix brief (persist the
  cause class; the next run's log must show it), not a sentence that
  quietly upgrades "unknown" to "proven". A failed attempt with an
  unrecorded exception stays "cause unknown" even after the fix lands.
- **The report is a proposed causal model.** It becomes a mandate only after
  the orchestrator re-runs at least one decisive check on the same evidence
  and records where the report overturned the issue body or the
  orchestrator's own hypothesis — in the issue thread and the train's
  choices protocol, so the wrong hypothesis stays part of the record.
- **Do not invent a phase for trivial defects.** A reproduced failure with a
  one-line mechanism gets the fix brief's root-cause paragraph, not an
  investigation lane. The trigger is uncertainty the orchestrator cannot
  remove with a direct check in minutes.
- **One success is not a time saving.** The worked example changed the
  mandate and its train verified green in one pass; that shows the pattern
  can work. Claims about rounds saved need the round counts from
  `../planning/execution-contract.md` (introduced by PR1) across several
  investigations, and the measurement the fix promised (here: plan attempts
  on the full case after the fix) is owed by a later run, not by the report.
- **Probes carry the caller's arguments** — copy the call site verbatim.
  A probe with its own defaults tests a different program.
- **Never signal-probe a live process** without a handler — attach by
  file-mtime and sampling profilers instead.
