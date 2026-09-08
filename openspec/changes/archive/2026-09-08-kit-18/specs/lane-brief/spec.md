## ADDED Requirements

### Requirement: Surface path-scoped open improvement items

The system SHALL place every open improvement item whose declared path scope matches a lane's planned paths in the brief's reads-first guidance.

#### Scenario: An open item matches a planned path

- **WHEN** an open improvement item is scoped to `harness/**` and a lane plans to touch `harness/guards/`
- **THEN** the prepared brief includes that item in the applicable reads-first guidance

#### Scenario: An open item does not match a planned path

- **WHEN** an open improvement item is scoped to `harness/**` and a lane plans to touch `planning/`
- **THEN** the prepared brief does not include that item
