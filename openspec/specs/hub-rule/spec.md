# Hub rule

## Purpose

For readers on the documentation-navigation journey, this capability keeps hubs concise while making every rule home reachable and testable under [ADR-0003](../../../decisions/0003-hub-pointers-with-one-sentence-glosses.md).

## Requirements

### Requirement: Pair each hub pointer with one gloss

The system SHALL represent a mechanism in a hub with a pointer to its rule home and no more than one sentence explaining why to follow it.

#### Scenario: A mechanism is added to a hub

- **WHEN** an author adds the mechanism to a root guide or installation guide
- **THEN** the entry points to its single rule home and supplies one concise gloss

### Requirement: Resolve every cited target

The system SHALL report a finding for any cited repository path, numbered section, continuation section, or quoted heading that does not resolve.

#### Scenario: A target heading is removed

- **WHEN** a hub still cites that heading
- **THEN** documentation verification is red and identifies the hub and missing target

### Requirement: Reject unbound continuation sections

The system SHALL report a continuation section that has no preceding repository path in the same paragraph.

#### Scenario: A paragraph begins with a continuation

- **WHEN** documentation verification reads that paragraph
- **THEN** it reports the continuation as unbound

### Requirement: Verify the complete documentation tree

The system SHALL support checking all Markdown documents while resolving relative pointers from each citing document.

#### Scenario: A nested document cites a sibling pillar

- **WHEN** complete-tree verification reads the nested document
- **THEN** the pointer is resolved from the citing document's location
