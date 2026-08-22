# Standing lane brief

The repo's operations doc is the authority; this template is its terse
execution summary. Harness-neutral by design: every instruction is a command,
a file or a git operation.

## 1. Lane header
- Lane: `<lane-name>`
- Repository pin: `<repo>@<sha>` — a commit SHA, never a branch name
- Primary checkout: `<primary>`  ·  Worktree: `<wt>`  ·  Branch: `<branch>`
- Orchestration scratchpad: `<scratchpad>`
- Assigned ADR number: `<NNNN>` or `none — STOP and report if one is needed`
- Assigned migration number: same rule

## 2. Standing hard rules
- Read the architecture/pattern docs first; a new seam duplicating an existing
  pattern is a review finding.
- The SPEC IS THE CONTRACT — deviation requires STOP + report, never silent
  reinterpretation.
- Never run the full verify (the lander does). Never use `--no-verify`.
  Never push.
- Never write a literal secret, including in tests — generate with
  `secrets.token_urlsafe(16)` or the stack's equivalent.
- One lane, one writer. Helpers read and advise only. The wrapper commits
  (coding CLIs often cannot commit in linked worktrees).
- Name every sentinel/log after this lane — the scratchpad is shared.
- Tear down served instances by PORT, never by process-name grep.

## 3. Task
{{SPEC_REFERENCE_AND_LANE_SPECIFIC_SCOPE}}

## 4. Gates before commit (from `<wt>`, all green)
{{PREGATE_COMMAND_BLOCK}}
Task-specific: the verification gates from the spec's slices (locate real
test files with grep before running).

## 5. Report-first sentinel
- Sentinel `<scratchpad>/<lane>.sentinel.json` — machine-readable heartbeat,
  rewritten at every leg boundary and before any long-running step.
- Report `<scratchpad>/<lane>-result.md` per the report schema
  (harness/report-schema.md), filed no matter how you exit, WITH the
  mandatory `choices:` self-report.

## 6. Circuit breakers
- Same task fails verification 3× → PARK (report status: parked + resume
  checklist + backlog row, push branch, leave the worktree).
- Three DIFFERENT root-cause hypotheses each failing → STOP and escalate an
  architecture question; never attempt a fourth.
- A needed-but-unassigned number, a semantics change, or a governance
  inconsistency (e.g. a future-dated approval) → STOP on first contact.
- Never weaken a criterion to pass — no baseline lowered, no assertion
  deleted. PARK instead.
