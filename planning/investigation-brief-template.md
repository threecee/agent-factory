# Read-only investigation brief

A read-only investigation is a lane that reads a frozen evidence package and
the pinned source, answers precise competing questions with citations, and
returns a proposed causal model. It changes no code. Its output is the input
to a fix brief (lane-brief-template.md), never a substitute for one.

This template is the home of the brief shape and the boundary to the fix
brief. The reasons live in `../interpretation/investigation-practice.md`;
what makes a report trustworthy lives in `../verification/falsification.md`
(§7–§9); the evidence-package convention lives in `../harness/artifact-bank.md`
(introduced by PR5); the run identity, the stdout-extraction rule and the
report path live in `../harness/run-lifecycle.md` (introduced by PR2). Round
counting (§3) and the measurement contract (§2) follow
`execution-contract.md`. Nothing here needs tool support: the brief is a
markdown file, the evidence is a directory, the report is a markdown file,
and every check in §10 is a read or a shell one-liner.

## 0. When to dispatch one — and when not to

Dispatch a read-only investigation when **all three** hold:

1. The cause is uncertain: the orchestrator holds at least one hypothesis it
   cannot confirm by a direct check in minutes.
2. A fix brief written now would have to *guess* the mechanism, the failing
   test or the invariants to pin.
3. The evidence can be frozen (a copied datastore, a log, a manifest, a run
   receipt) and pinned to a commit.

Do **not** dispatch one for a defect that is already reproduced with a
one-line mechanism (a failing test with an obvious cause, a typo, a missing
import). There the fix brief's own root-cause paragraph is enough. Inventing
a mandatory investigation phase for trivial reproduced failures is process
rot, not rigor.

## 1. Header

- Investigation: `<name>` — one per defect, named after the symptom, not the
  suspected cause
- Repository pin: `<repo>@<sha>` — the commit the failing run was built from,
  never a branch name
- Evidence package: `<bank-path>/<run-id>/` — frozen per `harness/artifact-bank.md`;
  list every file the investigator may open and how to open it read-only
  (for a database copy: the immutable/read-only URI; for a log: its path and
  the time window)
- Run identity: `<run-id>` — the investigation's own run ID
  (`harness/run-lifecycle.md`), distinct from the failed run's ID
- Report path: `<scratchpad>/<name>-result.md`, exported to the investigator
  as an environment variable; the wrapper banks the accepted report next to
  the evidence it interprets
- Model/effort: parameters chosen by the operator's dated policy
  (`../harness/model-policy.md`, introduced by PR7), stated here so the report
  carries its provenance — never a model name as an eternal default

## 2. Mandate (read-only, verbatim in every brief)

- Read code and the evidence package. **Change no code, run no model calls,
  start no servers, write nothing into the evidence package.**
- Every claim cites `file:line` or a query/probe with its result. A claim
  without a citation is a hypothesis, and is labeled as one.
- Answer each question with one of **supported / refuted / unknown** and the
  evidence for that verdict. "Unknown" with a stated observation gap is a
  valid answer; a guess dressed as a finding is not.
- Where the evidence cannot decide, say what evidence *would* decide it.
- Return the report in the named format below. If the sandbox cannot write
  the report file, print it as the final stdout block: the wrapper extracts,
  validates and banks it (`harness/run-lifecycle.md`). Exit 0 without an
  extractable report is not a deliverable.

## 3. Symptom and observed state

State what was observed, with timestamps and counts, and nothing about why.
Include the failing run's receipt (job/attempt table, error codes), the state
it left behind (row counts by status, files present), and the user-visible
consequence. Separate *observed* from *inferred*: the issue body that
triggered the investigation usually mixes the two — quote its observations,
re-file its explanation under §5 as a hypothesis.

## 4. Evidence package and code scope

- Evidence: the files from §1, each with its role (the datastore copy, the
  run log, the manifest, the wrapper that ran it).
- Timeline: the known boundaries (start/end of each attempt, arrival of
  external inputs, completion of neighboring jobs), in one time zone.
- Code to read: the functions on the suspected path, named with their
  role ("the publisher that compares identities", "the progress setter that
  rejects regression", "the ingest hook that runs the provider-less
  precompute"). Point, do not explain — the explanation is the
  investigator's job.

## 5. Competing hypotheses

List every hypothesis in play, including the orchestrator's own and the one
in the issue body, each as a falsifiable statement with the evidence that
would refute it:

| # | Hypothesis | Refuted by |
|---|---|---|
| H1 | `<mechanism A>` | `<query/probe that would show A did not happen>` |
| H2 | `<mechanism B>` | `<…>` |
| H? | Something not listed | The investigator must say so explicitly |

Two rules: the orchestrator's leading hypothesis goes in as a hypothesis,
not as the framing of the questions (a brief that presumes the cause gets
the cause it presumed); and the table must leave room for a mechanism nobody
listed — the best investigations find one.

## 6. Questions the report must answer with evidence

Precise, numbered, each answerable by a query or a code citation:

1. Which component changed between `<state at prepare>` and
   `<state at publish>`, per attempt boundary? Distinguish external triggers
   from self-induced change.
2. Which code path wrote `<the surprising rows>` at `<time>` — path X or
   path Y?
3. Is `<the count>` expected under the current policy, or does it double-count?
4. Ranked minimal fix proposals: for each, files/functions, the red→green
   tests to write, the invariants to pin, and the risk.

Questions of the form "why did it fail" get essays. Questions of the form
"which of these two paths wrote row R at time T" get evidence.

## 7. Report format (the deliverable)

```markdown
# Root cause
<one sentence naming the mechanism(s)> — then the evidence: file:line, queries, results.

## Hypothesis verdicts
| # | Hypothesis | Verdict (supported/refuted/unknown) | Evidence |

## Drift / timeline per attempt
| time | what changed | which component wrote it | evidence |

## <one section per question in §6>

## Ranked fix proposals
For each: files/functions · red→green tests · invariants to pin · risk.

## Uncertainties and observation gaps
What the evidence could not decide, and what would.
```

The report is a **proposed causal model**. It becomes a mandate only after
§8.

## 8. Boundary to the fix brief

The orchestrator, not the investigator, turns the report into a fix brief:

1. **Falsify the report's load-bearing claims with a direct check** on the
   same frozen evidence (re-run the decisive query; read the cited lines).
   A report that reads well has been wrong before
   (`../interpretation/investigation-practice.md`).
2. **Record the correction.** Where the report refutes the issue body or the
   orchestrator's own hypothesis, write the correction into the issue thread
   and the train's choices protocol
   (`../interpretation/choices-ledger-README.md`) — the wrong hypothesis is
   part of the record, not deleted.
3. **Write the fix brief** from lane-brief-template.md with:
   - the mechanism, one paragraph, citing the report by its banked path;
   - the mandate as red→green items in order (test first, see it fail, fix),
     each naming the test file and the falsification: revert this item, these
     tests go red again;
   - the invariants to pin, stated as tests;
   - **non-goals and STOP conditions** taken from the report's rejected
     proposals and risks (a proposal the report ranked as insufficient alone
     is a non-goal, with the reason);
   - what remains **unknown**, carried as an observability criterion (persist
     the cause class), never rewritten into a proven cause;
   - the measurement that the later run must produce, and who runs it
     (`execution-contract.md` §2).
4. **State the proof limits.** One investigation that changed the mandate
   shows the pattern works; it does not prove a general time saving. A fix
   train green in one pass is one instance. Say which measurements are still
   pending.

## 9. Worked example (anonymized)

**Symptom.** A background warmer that generates model-backed summaries for
the windows of a 25k-message case reports `partial_failure` after 46 minutes
and 444 published results; a retry fails after 5 minutes and 30 results. The
case had five sources ingested one after another during the warm. The state
left behind: several hundred "unavailable" summary rows current, most
model-backed rows stale or superseded, and the user sees "summary
unavailable" although the model provider was configured and reachable
(zero rate-limit responses in the log).

**Issue body's explanation (re-filed as H1).** Every attempt boundary
coincided with a derivation job being re-queued and, for the last one, with
25 media-description jobs finishing; both touch fields that feed the input
identity, so background work moved the identity under the warmer.

**Orchestrator's second hypothesis (H2).** In the retry window no
derivation or description job completed, so the drift must be
self-induced: the warmer's own incremental publishing (or a concurrent sweep
holding a lock) moved a version field that feeds the identity.

**Brief.** Evidence package: the datastore copy (opened with the read-only
URI), the run log, the manifest, the wrapper script; pin: the commit the run
was built from. Code scope: the plan publisher that compares identity sets,
the per-attempt progress setter, the ingest hook that runs the provider-less
precompute after each source, the identity builder, the sweep. Questions:
(1) which identity component changed per boundary, external vs self-induced;
(2) which path wrote the "unavailable"/floor rows at the last boundary; (3)
is the retry's 1090 pending windows expected; (4) ranked fixes with tests,
invariants, risk.

**Report (excerpt of the verdicts).**

| # | Hypothesis | Verdict | Evidence |
|---|---|---|---|
| H1 | derivation re-queue / description completions drove the drift | **refuted** | Query on the frozen copy: the derivation rows never ran (four superseded before start, one still queued with `attempts=0`); description rows feed a *different* digest (the projection's), not the summary identity (`projection_service:463` vs `dependencies:269`). What did change at each boundary was the arrival of sources 2–5: a global filter digest prefixed into every window scope plus a global coupling version — 201/297/398 common windows, 100 % scope+digest changed, 0 % dependency-set changed |
| H2 | attempt 2 was self-induced identity drift | **refuted as stated; cause unknown** | No identity-feeding write in the attempt-2 window (last alias/language/media/embedding writes all predate it); the warmer adds identities before the cache lookup and its own rows are not inputs to the identity builder. The actual exception was not persisted: the failure recorder collapses every exception into the same error code. Categories still possible: provider error, lease loss, other runtime error |
| H3 (unlisted) | the plan's internal retry is dead on arrival after a checkpoint | **supported** | `run_attempt:152` publishes `completed = 0` on every new attempt; `set_progress:767–771` rejects regression → `cannot regress progress 444 -> 0`; the retry loop at `:253` catches only the stale exception, not this `ValueError`. `max_attempts = 3` therefore works once in practice |
| Q2 | who wrote the floor at the last boundary | **ingest path, not the stale fallback** | `ingest/executor:253–254` runs the provider-less precompute after *every* source with no provider argument; five floor generations (97/201/297/400/499 windows) time-align exactly with the five ingest completions; every "unavailable" row carries the reason written only when the provider is absent. The stale publisher cannot have written them: the identity check throws before publish |
| Q3 | is 1090 expected | **yes** | 594 + 37 + 1 summary windows + 499 hotspots − 41 exact current hits; 171 exact-match model rows are `stale` and are counted again because the cache lookup requires `status = current` |

Observation gaps recorded: attempt 2's exception (not persisted); receipt
says 444 completed, the copy holds 443 distinct rows (whether the last item
was reused idempotently is not preserved); the earlier run's database that
produced the "640 windows" comparison was not in the package.

**Fix brief that followed (the mandate).** Mechanism paragraph citing the
banked report. Mandate in order, red→green each: **A** publisher diffs
identity sets instead of all-or-nothing, retry rebases progress from the
stored count and never writes 0 over a positive value, the retry loop
catches runtime errors and the failure recorder persists `{type, message}`
(tests: checkpoint 2, provoke stale, prove the retry does not attempt
`2 → 0`; add a source mid-batch, unchanged windows kept without new model
calls, changed ones re-queued, receipt succeeds). **B** provider-less
precompute runs once, when the case has no other queued/running ingest job,
and never over a stronger exact-input row (test: five ingest jobs → one floor
generation). **C** exact-input precedence: a floor/unavailable row cannot
stale or supersede a current model-backed row with identical
`(type, scope, scope_id, input_digest)`; a *different* digest still retires
the old row (tests: model→exact floor, floor→model, same scope/different
digest). **D** the standup gate prints the persisted cause class per failed
warmer. **Non-goal, with reason:** a quiescence barrier before the warmer
(the report's proposal (c)) — the queued derivation job had `attempts = 0`,
so a barrier only moves the failure to the deadline. **STOP** if A requires
weakening the monotonic-progress invariant (rebase, do not weaken) or if B
cannot decide quiescence without reading other cases' jobs. **Unknown
carried forward:** attempt 2's cause stays unknown; item A's cause-class
persistence is the observability criterion, and the next run's log must
show it. **Measurement owed:** the first warm after the fix reports the
number of plan attempts (expected ≤ 3, first receipt `success`); owner: the
orchestrator's rerun, not the lane.

**What was falsified, and what is still provisional.** The lane's
falsification: reverting A's progress rebase made two acceptance tests red;
restoring made them green. The train assembled and verified green in one
pass, and the lander's diff read (recorded as a medium-confidence choice)
noted that the publisher still compares the whole identity set — each
attempt re-prepares and sees checkpointed windows as cache hits, so four
source arrivals during one warm can still exhaust three attempts; the
receipt-level retry then converges without the regression error. **Not yet
shown:** convergence of the full 25k-message case after the fix, and the
plan-attempt count — both are owed by a later rerun. This example
demonstrates that a read-only investigation can overturn two plausible
hypotheses and reshape the mandate before code changes; it is one instance,
not evidence of a general time saving.

## 10. Acceptance checklist

A **brief** is complete when a stranger can: open every evidence file
read-only from §1 alone; find each hypothesis in §5 stated so that a query
could refute it, including the orchestrator's own; and answer every §6
question with a citation or a query rather than prose.

A **report** is accepted when: every hypothesis has a verdict with cited
evidence; at least one decisive query/citation has been re-run by the
orchestrator and matched; every "unknown" names the observation gap; the fix
proposals name tests, invariants and risk; and the investigator's diff is
empty (`git -C <wt> status --porcelain` prints nothing beyond the report
file, if the report was written inside the tree at all).

A **fix brief derived from it** is complete when it names the mechanism with
the report's banked path, every mandate item's red→green test and its
falsification, the non-goals with the report's reason, the STOP conditions,
what remains unknown and how it becomes observable, and the measurement the
later run owes with its owner.
