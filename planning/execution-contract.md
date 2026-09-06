# Execution contract — measurement baseline and the two-round limit

This file is the ONE home of two rules every lane is dispatched under: what
must be measured and handed over before a lane changes anything (§2), and how
many complete rounds a task gets before it is parked and split (§3). The
standing lane brief (lane-brief-template.md) links here and fills the
parameters in §8; it never restates these rules. The report schema
(../harness/report-schema.md) carries the fields the contract needs;
../interpretation/investigation-practice.md explains why the rules exist.
Section numbers are stable — briefs cite them.

## 1. Vocabulary

- **Task** — the unit of work the board item names. Its identity is the board
  item ID (issue number), never the lane name.
- **Lane** — one dispatch of one task into its own worktree, under one brief.
- **Acceptance apparatus** — the command, browser, served instance or
  measurement rig that decides whether the delivery actually works. It is a
  property of the task, not of the agent: a coding CLI without a browser is a
  fact about the current harness, not a permanent limitation.
- **Wrapper** — the orchestrator-side process that commits the lane's work
  and, when the lane cannot, runs the apparatus. **Lander** — the wrapper of
  the landing train (../verification/lander-duties.md).
- **Proof owner** — whoever runs the final apparatus check for a given
  observation. Named in the brief before work begins, never discovered at
  handback.
- **Round** — one authoring pass on the same unsplit task PLUS its prescribed
  proof attempt, including an apparatus rerun owned by the wrapper or lander
  when the lane cannot run it. A round without the proof attempt is not a
  round; it is an unfinished one.

## 2. Measurement baseline — evidence follows the task

1. **The orchestrator attaches, before dispatch,** every kind of evidence the
   task implies: logs, DOM snapshots, screenshots, profiles, numeric
   observations, failing test IDs — each with its exact source path or the
   exact command that produced it. Attach all kinds that exist; never an
   empty placeholder for a kind that does not, never a pasted log body where
   a path will do.
2. **The lane inventories before it authors:** the named call sites, tests
   and decisions the task touches, and the baseline counts, recorded as
   `measurements:` in its report. A lane that cannot measure something
   neither side can run STOPS and says so rather than inventing a number.
3. **The lane ties every observation to a revision.** When the lane can run
   the apparatus itself, the gate lines in its report are the proof and no
   table is needed. When it cannot — a real browser, a served instance, a
   device, a paid external call — the brief's task delta assigns the rerun
   to a named proof owner and the lane's report carries one `revision_table`
   row per measured observation:

   | Observation | Evidence attachment | Revision made | Rerun / proof owner |
   |---|---|---|---|
   | what failed, with the measured value | exact log/snapshot/profile path or command output artifact | the change addressing it | who runs which exact apparatus check |

4. **The table is a delivery contract, not proof.** The proof owner fills the
   final proof from a FRESH rerun of the same apparatus over the whole
   observed run, and that rerun is part of the round (§3). One speculative
   fix for the first observed failure is not a deliverable.
5. **A partial rerun is reported as partial.** If the owner reruns a subset
   (one step, fakes instead of the real provider), the report names what was
   run and what was not; a green subset never stands in for the whole.

### Worked example — a lane without browser access

Task #412: "The flow recorder fails at step 4 of the onboarding flow." The
lane runs in a sandbox with no browser. Under this contract the brief's task
delta reads:

```text
Task: #412  (round 1 of 2)
Apparatus: real Chromium via `make record FLOW=onboarding` — NOT runnable in
  this sandbox.
Proof owner: wrapper — reruns `make record FLOW=onboarding` on the lane's
  head SHA and attaches the new recorder log.
Measurement attachments:
  - recorder log: <bank>/412/round-1/recorder.log  (fails 00:41 at step 4,
    "element not visible: #continue")
  - DOM snapshot at failure: <bank>/412/round-1/step-4.dom.html
  - screenshot: <bank>/412/round-1/step-4.png  (panel "Details" collapsed)
  - timing: steps 1–3 took 0.8 s / 1.1 s / 0.9 s; step 4 timed out at 30 s
  - failing test id: tests/flows/test_onboarding.py::test_step_4_continue
```

The lane's report then carries, for every failure visible in the attached
run (not only the first one it fixed):

```yaml
revision_table:
  - observation: step 4 "element not visible: #continue" at 00:41; panel "Details" collapsed in step-4.dom.html
    evidence: <bank>/412/round-1/step-4.dom.html, <bank>/412/round-1/recorder.log
    revision: recorder expands the "Details" panel before locating #continue (src/recorder/steps.py:88)
    proof_owner: 'wrapper: make record FLOW=onboarding on head_sha, whole flow, real Chromium'
```

What the reader can check: the attachment names are paths, not adjectives;
the proof owner is a role plus the exact command; the rerun covers the whole
flow, so a second hidden element in step 6 is found in the same round rather
than the next one. The source factory adopted this after one recorder fix
took seven single-locator rounds; that history motivates the rule and does
not measure its effect.

## 3. Rounds — count complete rounds, per task identity

1. **A task gets at most two rounds.** Each round is an authoring pass plus
   its proof attempt (§1). A wrapper rerun that never happened means the
   round is not finished, not that it passed.
2. **The count follows the task identity** — the board item ID — across
   redispatches, renamed lanes, new briefs, fresh sessions and different
   agents. Renaming the lane does not reset it. The wrapper reads the
   previous report for the same `task:` before dispatching and writes
   `round: 2` into the brief and the report.
3. **After the second round without green proof, do not dispatch a third.**
   PARK the unsplit task (§6) and do one of:
   - issue narrower lane briefs, each independently provable by an
     apparatus the assigned owner can actually run; or
   - route the task through the spec ceremony (core-model.md, rung 2) when
     the failure is a specification question.
   The parked report names the split boundaries or the open question and
   the exact evidence still missing.
4. **A hard ceiling** — build/verify passes or wall-clock hours, set in the
   brief — also PARKs the lane. It cannot exceed the two-round limit.
5. **Only the orchestrator resets the count**, by an explicit, logged
   restart-from-document (a fresh lane from the brief with the count at
   zero). A reset must be written in the orchestration record before the
   dispatch; a lane or wrapper cannot self-grant one.

### Worked example — a rename does not buy a third round

- Round 1: lane `rec-fix` on task #412 expands the panel. Wrapper reruns the
  recorder in real Chromium: step 4 passes, step 6 fails ("#submit
  disabled"). Round 1 is complete and red.
- Round 2: lane `rec-fix-b` (same task, new name) enables the submit button
  after validation. Wrapper reruns: step 6 passes, step 7 times out.
  Round 2 is complete and red.
- The orchestrator now wants to dispatch `recorder-onboarding-v3`. Wrong:
  `task: 412` already carries `round: 2`. Right: PARK #412 with a report
  that lists the three observed failures and their evidence, then dispatch
  two independent tasks — #418 "step 7 waits for the confirmation route"
  (provable by `tests/flows/test_onboarding.py::test_step_7`, runnable in
  the sandbox) and #419 "recorder asserts visibility before every click"
  (provable only by the wrapper's full-flow rerun) — each with its own
  counter at round 1.
- What must NOT happen: a brief titled "#412 attempt 3", a third rerun on
  a new lane name, a lowered assertion so step 7 "passes", or a reset the
  orchestrator did not write down.

## 4. Decision versus repetition

A round counts repetition on the same approach. Three other situations look
like failure but are not rounds; they carry their own caps, in their own
homes:

1. **A scope or product question surfaces.** File it immediately as a board
   decision item (board-protocol.md, Decision needed) with the observed
   evidence, the unresolved boundary and a recommendation. Continue the
   reversible part that does not presuppose the answer; STOP only when no
   such part exists or the answer crosses a first-contact stop (§5). Never
   guess to keep moving. "Needs-user never stalls the run"
   (../interpretation/choices-ledger-README.md) applies inside authorization
   and reversibility; it never overrides a first-contact stop.
2. **Distinct root-cause hypotheses keep failing.** Three DIFFERENT fixes,
   each from a different hypothesis, each failing, means the model of the
   defect is wrong — STOP and escalate an architecture question. Owner:
   ../interpretation/investigation-practice.md. This is a STOP, not a
   PARK, because what remains is a design question, not a resumable build.
3. **The agent process dies** (crash, kill, exit without a reviewable
   result). Re-dispatch once, after confirming the dead run is quiescent
   (the working tree stops changing — hash `git diff` twice). A second
   death STOPs. Never re-dispatch into a known-exhausted quota or capacity
   wall; when such a wall kills lanes mid-wave, PARK the survivors with
   their sentinels current and resume on a positive capacity check, not on
   a timer. Owner of the process mechanics: `harness/run-lifecycle.md`
   (introduced by PR2).

## 5. First-contact STOPs (parameterized locally)

A lane STOPs on first contact with any of the following, with a report, and
does not attempt a workaround: a needed-but-unassigned number (ADR,
migration — adr-and-numbers.md); a semantics change that cannot be isolated
from the reversible part; a change to a boundary the target repo has
declared guarded; a governance inconsistency (e.g. a future-dated approval).
The target repo lists its guarded boundaries in §8 of its brief; this
package ships the method of naming and testing a boundary, not any
particular boundary.

## 6. PARK, STOP and who pushes

**PARK** leaves reusable partial state. A parked lane:
- files its report with `status: parked`, the round number, and a resume
  checklist (branch, head SHA, done, remaining, exact next step, why);
- files the remainder where the target repo tracks open work (a board item
  or the backlog row the planning gate governs) and links the report;
- leaves the worktree in place. Nobody cleans up a parked lane; an idle
  lane with unpushed work is usually mid-verify.

**STOP** halts and escalates to the orchestrator: a first-contact stop (§5),
a second process death, the third failed distinct hypothesis, or — at wave
level — three parked tasks or all lanes blocked.

**Push responsibility** (this resolves the old template's contradiction
between "Never push" and "PARK … push branch"):
1. The **lane agent never pushes** anything. Coding CLIs often cannot commit
   in linked worktrees, and a push from inside a lane bypasses the wrapper's
   commit, identity and gate checks.
2. The **wrapper pushes the lane branch** at every handback — built, parked,
   blocked or failed — right after it commits, so a parked lane's work is on
   the remote before the worktree is left alone. "Push branch" in the PARK
   checklist is a wrapper duty.
3. **Only the lander pushes main**, gated on the verify verdict
   (../verification/lander-duties.md).

**Never weaken a criterion to pass.** No baseline lowered, no assertion
deleted, no gate edited to go green. PARK instead.

## 7. Provenance and what is still provisional

- The two-round rule replaced a "same task fails verification three times"
  rule in the source factory after a retrospective in which one recorder fix
  consumed seven rounds and nine of twenty-nine verify runs were red on the
  first round. That count is the motivation. The source factory has NOT yet
  documented that the rule lowered its red-first-round share; treat any such
  claim as unmeasured.
- The measurement-first handover was adopted after a browser-blind lane
  discovered one locator per round. The worked examples above are
  anonymized reconstructions of that shape, not transcripts.

## 8. Parameters the standing brief fills

| Parameter | Filled by | Example |
|---|---|---|
| `task` | orchestrator | board item ID |
| `round` | wrapper, from the previous report for the same task | `1 of 2` |
| `apparatus` | orchestrator | the exact command / browser / rig, and whether the lane can run it |
| `proof_owner` | orchestrator, per observation | `wrapper: <exact command>` |
| `attachments` | orchestrator | paths or commands, one per evidence kind that exists |
| `ceiling` | orchestrator | `≤ 4 verify passes or 3 h` (never more than two rounds) |
| `first_contact_stops` | target repo | number allocation, isolated semantics, guarded boundaries |
| `park_destination` | target repo | board item, or backlog row governed by the planning gate |
