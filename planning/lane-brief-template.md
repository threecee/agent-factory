# Standing lane brief

The repo's operations doc is the authority; this template is its terse
execution summary. Harness-neutral by design: every instruction is a command,
a file or a git operation. The rules below have exactly one home each
(cited); this template parameterizes them, it never restates them.

## 1. Lane header
- Lane: `<lane-name>`
- Task: `<board item ID>` — the identity the round counter follows
  (execution-contract.md §3); `<lane-name>` may change, the task ID does not
- Round: `<1|2> of 2` — the wrapper fills this from the previous report for
  the same task; a third round is not dispatchable
- Repository pin: `<repo>@<sha>` — a commit SHA, never a branch name
- Primary checkout: `<primary>`  ·  Worktree: `<wt>`  ·  Branch: `<branch>`
- Orchestration scratchpad: `<scratchpad>`
- Assigned ADR number: `<NNNN>` or `none — STOP and report if one is needed`
- Assigned migration number: same rule
- Ceiling: `<N verify passes | H hours>` — reaching it PARKs (never more
  than the two-round limit)
- Model/effort: `<role> → <model> @ <effort>, policy ~/.claude/model-policy.md
  (valid_from <date>, review_by <date>), probed <date>` — filled by the
  wrapper from the operator's dated policy (../harness/model-policy.md §4);
  never a name typed from memory, never a template default

## 2. Standing hard rules
- Read the architecture/pattern docs first; a new seam duplicating an existing
  pattern is a review finding.
- The SPEC IS THE CONTRACT — deviation requires STOP + report, never silent
  reinterpretation.
- Never run the full verify (the lander does). Never use `--no-verify`.
- The lane agent never pushes. The wrapper pushes this lane's branch at every
  handback (built or parked); only the lander pushes main
  (execution-contract.md §6).
- Never write a literal secret, including in tests — generate with
  `secrets.token_urlsafe(16)` or the stack's equivalent.
- One lane, one writer. Helpers read and advise only. The wrapper commits
  (coding CLIs often cannot commit in linked worktrees).
- Name every sentinel/log after this lane — the scratchpad is shared.
- Environment symlinks (.venv/.env/node_modules) must be gitignored in the
  target repo; the wrapper's `git add -A` must never commit them.
- Tear down served instances by PORT and by path, never by process-name grep
  (../harness/artifact-bank.md §8).
- Guards may refuse a hard form (a verdict through a pipe, `--no-verify`,
  text-match process selection, a raw lane dispatch): the refusal names the
  exact alternative and a switch; using a switch is logged and goes into the
  train ledger with a reason, never silently (../harness/guards.md §4–§5).
- First-contact STOPs for this repo (execution-contract.md §5):
  {{FIRST_CONTACT_STOPS}}

## 3. Task
{{SPEC_REFERENCE_AND_LANE_SPECIFIC_SCOPE}}

### Measurement baseline (execution-contract.md §2)
- Acceptance apparatus: `<exact command / browser / rig>` —
  `runnable in this sandbox: yes|no`
- Proof owner when not runnable here: `<wrapper|lander>: <exact apparatus
  check>` — one owner per observation; the rerun covers the whole observed
  run, not the first fixed step
- Attachments (paths or commands only; one line per evidence kind that
  exists, none for kinds that do not):
  {{MEASUREMENT_ATTACHMENTS}}
- Before authoring, inventory the named call sites, tests and decisions and
  record baseline counts under `measurements:` in the report. If something
  cannot be measured by either side, STOP and say so.
- If the apparatus is not runnable here, the report carries one
  `revision_table` row per measured observation
  (../harness/report-schema.md).

For a bug-fix lane this section leads with the root-cause hypothesis and
where it was traced (../interpretation/investigation-practice.md) before it
states the fix.

## 4. Gates before commit (from `<wt>`, all green)
{{PREGATE_COMMAND_BLOCK}}
Task-specific: the verification gates from the spec's slices (locate real
test files with grep before running).

## 5. Report-first sentinel
- Sentinel `<scratchpad>/<lane>.sentinel.json` — machine-readable heartbeat,
  rewritten at every leg boundary and before any long-running step.
- Report `<scratchpad>/<lane>-result.md` per the report schema
  (../harness/report-schema.md), filed no matter how you exit, WITH the
  mandatory `choices:` self-report; when `choices:` is non-empty, the walked
  scenarios go in the sidecar `<scratchpad>/<lane>-choices.md`.

## 6. Circuit breakers (execution-contract.md §3–§6 is the home)
- Two complete rounds — authoring pass plus prescribed proof attempt,
  including the wrapper's/lander's apparatus rerun — without green proof →
  PARK the unsplit task; the orchestrator splits into independently provable
  lanes or routes to write-spec. The count follows the task ID across
  renames and sessions; no third round.
- A scope/product question → file a Decision-needed board item immediately
  with evidence and a recommendation; continue the reversible part. STOP only
  when no reversible part exists or a first-contact stop is crossed.
- Three DIFFERENT root-cause hypotheses each failing → STOP and escalate an
  architecture question; never attempt a fourth
  (../interpretation/investigation-practice.md).
- Process death → the wrapper re-dispatches once after confirming quiescence;
  a second death STOPs.
- Reaching the ceiling in §1 → PARK.
- PARK = report `status: parked` with round number + resume checklist,
  remainder filed at `{{PARK_DESTINATION}}`, worktree left in place; the
  wrapper pushes the branch.
- Never weaken a criterion to pass — no baseline lowered, no assertion
  deleted. PARK instead.
