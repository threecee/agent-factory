## MODIFIED Requirements

### Requirement: Select gates from the complete lane change set

The system SHALL mechanically list each matching verification leg and its command from both tracked changes and untracked files relative to the pinned revision.

#### Scenario: A lane creates an untracked matching file

- **WHEN** the lane evaluates its required verification legs
- **THEN** the leg whose path pattern matches the new file is listed with its command

#### Scenario: A lane changes a tracked matching file

- **WHEN** the lane evaluates its required verification legs
- **THEN** the leg whose path pattern matches the tracked change is listed with its command

#### Scenario: A lane changes only unmatched files

- **WHEN** no changed or untracked path matches a verification leg
- **THEN** no verification leg is listed
