# Architecture

## 1. System boundary

The kit is a harness-neutral operating model for moving a change from intent to verified learning. Its core is documentation and deterministic local checks; adapters translate host events and commands into that core without becoming new policy homes. Repository language, build chain, feature registry, provider integrations, and hosting remain parameters supplied during installation.

Human judgment stays outside automation: the owner approves intent and landing authority, reviewers judge whether evidence is meaningful, and operators decide whether a recorded choice is sound. Automation may require those judgments to be present and well formed, but it does not manufacture them.

## 2. Data flow

`planning/board-protocol.md` → `planning/lane-brief-template.md` → lane worktree → `interpretation/choices-ledger-README.md` → `harness/train-plan.md` → `verification/landing-modes.md` → `interpretation/continuous-improvement.md`.

The board supplies task identity and approved intent. The brief binds a lane to a revision and proof contract; the lane returns evidence and choices. The ledger carries those choices into a train, the train combines pinned lane revisions, landing consumes the train receipt and authority, and interpretation turns observed outcomes into memory or new board work.

## 3. High-level components

### 3.1 Planning pillar

code: `planning/`

Defines why, current behavioral intent, approved execution contracts, board transactions, and globally allocated decision numbers.

### 3.2 Verification pillar

code: `verification/`

Owns deterministic gates, falsification practice, train proof, landing protections, and close-out checks.

### 3.3 Interpretation pillar

code: `interpretation/`

Owns the choices protocol, investigation and evaluation practice, memory conventions, and the feedback loop into planning.

### 3.4 Harness

code: `harness/`

Carries neutral execution machinery: launch contracts, run-bound receipts, guards, worktree ritual, train assembly guidance, and adapter seams.

## 4. Durable documents

Capability specs state current observable behavior. ADRs record architecture rationale and bind it to implementation and proof. This file and `PATTERNS.md` orient readers to boundaries and recurring code shapes. The choices ledger records decisions made while executing approved work. Their distinct roles follow `planning/capability-specs.md §1` and `decisions/0006-three-durable-artifacts.md`.

## 5. Key constraints

- Core doctrine contains no repository-specific package, organization, host, or domain literals; installation supplies parameters through documented adapter seams.
- Receipts and reports belong to one run identifier, so stale evidence cannot approve a later run.
- Guards fail open on apparatus failure and speak loudly when they do; fail-closed decisions live in gates, hooks, or host protections.
- A concept has one durable home. Hubs point to that home and add only a one-sentence gloss.
- The default branch contains no live capability-change directory after landing.
- Owner authority is explicit: pull-request landing is the default, and direct push requires a recorded owner-approved basis.

## 6. What remains deliberately outside the boundary

The kit does not choose product requirements, judge the quality of a proof, allocate authority by conversation, select provider credentials, or decide that an unsound choice is acceptable. Those are human acts recorded through the board, decision brief, policy, review, and ledger surfaces.
