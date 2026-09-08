review: pending

# Lane brief sources

## 1. Requirement sources

- **Bind a lane to one task and revision:** `planning/lane-brief-template.md §1`; `harness/tests/test_launch_lane.sh 3a`; `harness/tests/test_launch_lane.sh 11a`.
- **Parameterise the standing contract:** `planning/lane-brief-template.md §2`.
- **Select gates from the complete lane change set:** `planning/lane-brief-template.md §4`; inferred coverage scenario from the approved issue 22 brief because no package shell case exercises the untracked-file selector yet.
- **Bound authoring rounds:** `planning/lane-brief-template.md §6`; `planning/execution-contract.md §3`–`§6`.

## 2. Divergences

- The launcher does not parse the round field; the wrapper remains the proof owner for rejecting a third round, as the installation smoke test records.

## 3. Registry coverage

- Covered scope: `planning/lane-brief-template.md` and its wrapper-facing launch boundary.
- Uncovered globs: none; the kit has no separate feature-registry glob for this mechanism.
