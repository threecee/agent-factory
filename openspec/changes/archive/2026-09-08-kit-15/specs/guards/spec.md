# Guards delta

## ADDED Requirements

### Requirement: Compare declared and delivered change kinds

The system SHALL compare the change kind declared for a lane with the kind derived from the receipt-bound committed train diff before landing.

#### Scenario: Delivered risk rises

- **WHEN** a documentation-only declaration delivers a source change that has not been recorded after its selected checks
- **THEN** the landing attempt is refused
- **AND** the refusal identifies the newly selected verification consequences

#### Scenario: Delivered rise is recorded

- **WHEN** the selected checks have passed and the train record names the derived source kind
- **THEN** the same rise is not refused again by the kind guard

#### Scenario: Delivered risk falls

- **WHEN** a source declaration delivers only documentation
- **THEN** the landing attempt is not refused for the kind change
- **AND** the fall is exposed as context for the train record

#### Scenario: Classifier apparatus fails

- **WHEN** the bound repository classifier exits unsuccessfully or emits an unknown kind
- **THEN** the landing attempt is allowed through this guard with a diagnostic naming the repair
