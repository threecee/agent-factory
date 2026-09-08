# Landing

## Purpose

For landers on the verified-train journey, this capability moves reviewed work to the default branch with explicit authority and complete close-out under [ADR-0004](../../../decisions/0004-pr-default-with-owner-signed-direct-push.md).

## Requirements

### Requirement: Require a current green train receipt

The system SHALL refuse a landing unless its verification receipt is green and bound to the exact train revision and base being landed.

#### Scenario: A receipt names another revision

- **WHEN** a landing is attempted with a green receipt for a different train revision
- **THEN** the landing is refused and both revisions are identified

### Requirement: Default to pull-request landing

The system SHALL use pull-request landing unless owner authority explicitly permits direct push with a recorded reason.

#### Scenario: Direct push overrides the default

- **WHEN** a train selects direct push against the pull-request default
- **THEN** the landing record contains the override reason before the landing can proceed

### Requirement: Archive capability deltas before final verification

The system SHALL archive every live capability delta in stable order before assembly cross-checks and final verification.

#### Scenario: A train contains live capability deltas

- **WHEN** the lander assembles the train
- **THEN** each delta is merged into current capability truth and moved to the archive before later checks read the train

### Requirement: Register and close out a successful landing

The system SHALL record the landed train and keep close-out duties visible until every required duty is complete.

#### Scenario: The default branch contains the train

- **WHEN** a landing completes successfully
- **THEN** the landing record names the mode and landed revision
- **AND** incomplete registry, board, notification, primary-update, or worktree duties remain visible
