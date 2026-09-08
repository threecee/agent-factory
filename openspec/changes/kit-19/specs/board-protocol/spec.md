## ADDED Requirements

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
