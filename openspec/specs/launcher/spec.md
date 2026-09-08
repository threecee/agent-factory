# Launcher

## Purpose

For wrappers on the lane-launch journey, this capability starts isolated work only from a bound contract and preserves trustworthy run evidence under [ADR-0005](../../../decisions/0005-child-processes-drop-hook-repository-pins.md).

## Requirements

### Requirement: Refuse invalid starts before side effects

The system SHALL refuse a launch with a missing required binding before starting work or creating run artifacts.

#### Scenario: A required brief is absent

- **WHEN** a wrapper requests a start without a readable brief
- **THEN** the request is refused and identifies the missing binding
- **AND** no lane process or run artifact is created

### Requirement: Bind evidence to one run

The system SHALL bind start evidence, logs, reports, exit evidence, and verdicts to one immutable run identifier.

#### Scenario: Old evidence is present

- **WHEN** a verdict is requested for a newer run
- **THEN** evidence from an older run cannot approve the newer run

### Requirement: Serialise starts with repository writes

The system SHALL delay a lane start until an active write to the same worktree has released its lock.

#### Scenario: A delayed start overlaps a commit

- **WHEN** the start delay expires while a repository write holds the lock
- **THEN** the lane process starts only after that write completes

### Requirement: Enforce the pinned revision at start

The system SHALL refuse to start work when the worktree revision differs from the revision in the launch contract.

#### Scenario: The worktree moved after briefing

- **WHEN** the launcher reaches a worktree whose current revision is not the pinned revision
- **THEN** the start is refused before the lane process runs

### Requirement: Preserve read-only lane delivery

The system SHALL allow a read-only lane to deliver a valid run-bound report through its captured output.

#### Scenario: A read-only lane completes

- **WHEN** the lane emits one marked valid report and exits successfully
- **THEN** the wrapper stores that report and its receipts under the same run identity
