# Mechanism patterns

## 1. Guard rule module shape

code: `harness/guards/rules/no_verify.py`

A rule declares one stable identifier, the events it observes, one check that returns a shared verdict shape, and planted falsification cases. The dispatcher owns loading, switch resolution, channel rendering, and trace writes so individual rules do not fork the guard protocol.

## 2. Falsification by planting

code: `harness/tests/test_guards.sh`

Copy the apparatus to a throwaway tree, plant one violation or corrupt one expectation, observe the precise red result, then run the unmodified tree green. The plant identifies which mutation the proof can actually catch.

## 3. Run-bound receipts

code: `harness/launch_lane.sh`

Every start, log, result, exit record, and verdict carries the same immutable run identity. A verdict checks both identity and freshness, so an earlier success cannot be mistaken for the present run.

## 4. Sentinels

code: `verification/gates/lane_sentinel.py`

A small progress artifact is written first and refreshed at meaningful leg boundaries. Monitoring uses its freshness to distinguish active work from a missed wake-up, but the sentinel never substitutes for the final deliverable.

## 5. Wrappers

code: `harness/worktree-ritual.md`

A wrapper owns mechanical boundaries around an author: isolated worktree creation, pinned dispatch, writer locking, result linting, falsification, and the lane-branch handoff. It does not invent intent or land the default branch.

## 6. Ratchets

code: `verification/gates/check_ruff_ratchet.py`

A ratchet compares current findings with a committed per-rule baseline, refuses increases, and changes the baseline only through an explicit update path. Improvements lower future tolerance instead of creating room for unrelated regressions.

## 7. Hub pointers

code: `verification/tests/test_hub_pointers.sh`

A navigational document points to the one rule home and adds one sentence of orientation. Tree verification resolves paths, numbered sections, continuation sections, and quoted headings, including references made from nested documents.

## 8. Portable and stack-specific gates

code: `verification/gates/README.md`

Decision and repository-history gates with standard-library boundaries are ported as-is. Build, lint, migration, and domain gates are selected only when the target has that stack or concern, then reimplemented against the same observable contract rather than copied blindly.
