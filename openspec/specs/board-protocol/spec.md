# Board protocol

## Purpose

For operators on the board-to-brief journey, this capability keeps task state, authority, and transitions inspectable in one planning surface under [ADR-0006](../../../decisions/0006-three-durable-artifacts.md).

## Requirements

### Requirement: Treat the full board as planning truth

The system SHALL present the complete board as the authoritative current set of planned work.

#### Scenario: Operator surveys planned work

- **WHEN** an operator requests the current planning state
- **THEN** every board item is included rather than only the first result page
- **AND** derived views do not replace the authoritative board

### Requirement: Apply state transitions at transaction points

The system SHALL move each item to the state prescribed for the observed lifecycle event.

#### Scenario: A lane starts

- **WHEN** a valid lane run starts for a planned item
- **THEN** the item is observable as in flight

#### Scenario: A train lands

- **WHEN** the train containing an item lands successfully
- **THEN** the item is completed and then archived

### Requirement: Expose decisions that require the owner

The system SHALL represent an unresolved owner choice as a decision-needed item with a readable decision brief.

#### Scenario: Execution reaches an owner choice

- **WHEN** progress requires authority or intent that has not been granted
- **THEN** the board exposes the decision-needed state and its decision brief

### Requirement: Emit one notification for each transition

The system SHALL emit no more than one notification for a single item transition.

#### Scenario: A landing completes an item

- **WHEN** close-out records the completed transition
- **THEN** observers receive one landed notification for that item

### Requirement: Read back an issue transition

The system SHALL report a selected issue's current project status and the time that status was last set without changing the board.

#### Scenario: Expected state is present

- **WHEN** an operator reads an issue back against its expected project state
- **THEN** the current project status and its last-set time are printed
- **AND** the check succeeds

#### Scenario: Item is missing or in the wrong state

- **WHEN** an issue is absent from the configured project or its project state differs from the expected state
- **THEN** the observed result is reported
- **AND** the check returns a non-success result

#### Scenario: The planning provider is unavailable

- **WHEN** the authoritative project cannot be read
- **THEN** the result explicitly says that the board was not verified
- **AND** the check returns a non-success result
