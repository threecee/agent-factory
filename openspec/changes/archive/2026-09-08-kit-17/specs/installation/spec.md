## ADDED Requirements

### Requirement: Expose installed kit identity

The system SHALL expose an installed kit record containing the exact kit version, installation date, and complete non-secret resolved-parameter mapping.

#### Scenario: Installation completes

- **WHEN** the installation smoke test and verification finish successfully
- **THEN** the target repository contains one current installation record
- **AND** the record identifies the kit version, installation date, and resolved parameters

### Requirement: Preserve update history

The system SHALL retain prior installation records when a target repository updates to another kit version.

#### Scenario: An update succeeds

- **WHEN** the installed-tree check and target verification pass for the newer kit
- **THEN** a new installation record is appended after every earlier record

#### Scenario: An update fails

- **WHEN** the installed-tree check or target verification is red
- **THEN** the existing installation records remain unchanged

### Requirement: Reject unresolved installation placeholders

The system SHALL report every unresolved installation placeholder in the installed Markdown tree.

#### Scenario: A copied pillar retains a placeholder

- **WHEN** installed-tree verification reads a placeholder outside the planning pillar
- **THEN** verification is red and identifies the containing file and placeholder
