# Numbers registry

## Purpose

For orchestrators on the decision-authoring journey, this capability makes globally scarce identifiers visible before parallel work can collide, supporting the durable decisions in [ADR-0006](../../../decisions/0006-three-durable-artifacts.md).

## Requirements

### Requirement: Reserve a number before authoring

The system SHALL expose a claimed registry row before any numbered artifact using that number is authored.

#### Scenario: A new decision needs a number

- **WHEN** the orchestrator allocates the next available identifier
- **THEN** the registry shows the number, owner, date, state, and purpose before the decision file exists

### Requirement: Centralise number allocation

The system SHALL accept number allocations only from the orchestrator role.

#### Scenario: A lane discovers an unallocated numbered artifact

- **WHEN** authoring would require a new number
- **THEN** the lane stops and reports the allocation need instead of choosing a number

### Requirement: Maintain one lifecycle row per number

The system SHALL represent each allocated number with one row whose state changes in place from claimed to landed or released.

#### Scenario: A claimed artifact lands

- **WHEN** close-out confirms the numbered artifact is on the default branch
- **THEN** its existing registry row is changed to landed without adding a duplicate

### Requirement: Detect stale claimed state

The system SHALL report a claimed number as drift when its numbered artifact already exists on the default branch.

#### Scenario: Registry close-out was missed

- **WHEN** verification observes the artifact on the default branch and its row still says claimed
- **THEN** verification reports a hard finding naming the number
