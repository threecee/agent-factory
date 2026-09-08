# Choices ledger

## Purpose

For owners and auditors on the lane-to-train journey, this capability preserves what agents decided while executing approved work as one of the durable artifacts in [ADR-0006](../../../decisions/0006-three-durable-artifacts.md).

## Requirements

### Requirement: Give every choice one stable identity

The system SHALL assign each reported execution choice one stable identifier wherever that choice is referenced.

#### Scenario: A lane reports a judgment

- **WHEN** the choice audit incorporates that judgment into the train record
- **THEN** the same choice identifier follows it through explanation and resolution

### Requirement: Record a verdict and confidence

The system SHALL state one explicit sound, unsound, or needs-user verdict and one confidence level for every choice.

#### Scenario: A choice lacks confidence

- **WHEN** the ledger is checked before landing
- **THEN** the incomplete entry is reported as a protocol finding

### Requirement: Resolve unsound choices before landing

The system SHALL prevent an unsound choice from reaching landing without an explicit corrective resolution.

#### Scenario: An unsound choice has no fix

- **WHEN** the train record is checked for landing
- **THEN** the unresolved choice is reported as a hard finding

### Requirement: Carry overrides into the train record

The system SHALL record guard refusals, switch uses, landing mode, and any landing override reason in the train ledger.

#### Scenario: An operator uses a guard switch

- **WHEN** the affected lane is included in a train
- **THEN** the ledger identifies the refusal, the switch use, and the operator's reason

### Requirement: Preserve detailed scenarios with the handback

The system SHALL bank any detailed choice scenarios outside the terse report while retaining a resolvable reference from that report.

#### Scenario: A handback reports one or more choices

- **WHEN** the result is accepted as a deliverable
- **THEN** its referenced scenario sidecar is preserved with the handback
