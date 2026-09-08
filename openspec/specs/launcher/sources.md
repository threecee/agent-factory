review: pending

# Launcher sources

## 1. Requirement sources

- **Refuse invalid starts before side effects:** `harness/run-lifecycle.md §11`; `harness/tests/test_launch_lane.sh 1c`.
- **Bind evidence to one run:** `harness/run-lifecycle.md §2`, `§5`; `harness/tests/test_launch_lane.sh 3a`; `harness/tests/test_launch_lane.sh 8b`; `harness/tests/test_launch_lane.sh 8c`.
- **Serialise starts with repository writes:** `harness/run-lifecycle.md §4`; `harness/tests/test_launch_lane.sh 10c`.
- **Enforce the pinned revision at start:** `harness/run-lifecycle.md §4`; `harness/tests/test_launch_lane.sh 11a`; `harness/tests/test_launch_lane.sh 11c`.
- **Preserve read-only lane delivery:** `harness/run-lifecycle.md §8`; `harness/tests/test_launch_lane.sh 12a`; `harness/tests/test_launch_lane.sh 12c`.

## 2. Divergences

- None observed between the lifecycle document, launcher behavior, and shell cases.

## 3. Registry coverage

- Covered scope: `harness/launch_lane.sh` and the launcher test fixture.
- Uncovered globs: none; the launcher shell surface is covered as a whole.
