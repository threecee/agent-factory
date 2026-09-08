# Guards

## Purpose

For operators on protected command journeys, this capability gives immediate, auditable guidance without turning apparatus failure into lockout, as governed by [ADR-0001](../../../decisions/0001-guards-fail-open.md) and [ADR-0002](../../../decisions/0002-switches-precede-guards-and-leave-a-trace.md).

## Requirements

### Requirement: Dispatch each event to applicable rules

The system SHALL evaluate every available rule that declares the observed event and combine their verdicts for the caller.

#### Scenario: One applicable rule crashes

- **WHEN** another applicable rule returns a refusal for the same event
- **THEN** the caller still receives that refusal

### Requirement: Fail open on apparatus failure

The system SHALL allow the attempted action when a rule or hook loader cannot evaluate it and emit a loud diagnostic.

#### Scenario: A rule crashes

- **WHEN** an applicable rule raises an internal error
- **THEN** the action is allowed with a diagnostic naming the failed rule

### Requirement: Trace every switch use

The system SHALL record each used switch with the affected rule and the source that supplied the switch.

#### Scenario: An operator uses a rule switch

- **WHEN** a planted violation is allowed through that switch
- **THEN** the event trail records an allow-switch event with the rule and source

### Requirement: Keep rule switches independent

The system SHALL apply a rule-specific switch only to the rule or leg identified by that switch.

#### Scenario: A different rule is switched

- **WHEN** an event violates an unswitched rule
- **THEN** the unswitched rule can still refuse the action

### Requirement: Falsify shipped rules by planting violations

The system SHALL produce a run receipt showing the red and green result of every shipped falsification case.

#### Scenario: A falsification expectation is corrupted

- **WHEN** one planted case no longer observes its required result
- **THEN** the falsification run is red and names exactly that failed case

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
