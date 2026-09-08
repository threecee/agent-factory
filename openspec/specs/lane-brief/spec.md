# Lane brief

## Purpose

For wrappers and lane authors on the brief-to-lane journey, this capability supplies one parameterised execution contract whose artifact role follows [ADR-0006](../../../decisions/0006-three-durable-artifacts.md).

## Requirements

### Requirement: Bind a lane to one task and revision

The system SHALL identify each lane with its task, round, branch, repository revision, model, and effort.

#### Scenario: A wrapper receives a brief

- **WHEN** a lane is ready for dispatch
- **THEN** the wrapper can identify the exact task, round, branch, revision, model, and effort from the brief

### Requirement: Parameterise the standing contract

The system SHALL express repository-specific values as brief parameters while leaving standing rules at their cited homes.

#### Scenario: A brief is prepared for another repository

- **WHEN** an orchestrator fills the standing brief for that repository
- **THEN** the resulting brief contains its concrete bindings and resolving rule pointers
- **AND** it does not create a second statement of those rules

### Requirement: Select gates from the complete lane change set

The system SHALL select matching verification legs from both tracked changes and untracked files relative to the pinned revision.

#### Scenario: A lane creates an untracked matching file

- **WHEN** the lane evaluates its required verification legs
- **THEN** the leg whose path pattern matches the new file is selected

### Requirement: Bound authoring rounds

The system SHALL bound one task to two authoring rounds before requiring a parked handback or a new document.

#### Scenario: A task reaches the end of its second round

- **WHEN** required work remains after the second proof attempt
- **THEN** the lane reports a parked result with an exact resume checklist
