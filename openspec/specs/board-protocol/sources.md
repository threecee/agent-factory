review: pending

# Board protocol sources

## 1. Requirement sources

- **Treat the full board as planning truth:** `planning/board-protocol.md` “Authority, pagination and derived views”.
- **Apply state transitions at transaction points:** `planning/board-protocol.md` “Transaction points (the part sessions historically drop)”; `verification/tests/test_landing_protections.sh 21` exercises visible post-landing duties.
- **Expose decisions that require the owner:** `planning/board-protocol.md` “Decision needed”.
- **Emit one notification for each transition:** `planning/board-protocol.md` “Notifications”.

## 2. Divergences

- None observed between the current protocol and its exercised landing boundary.

## 3. Registry coverage

- Covered scope: `planning/board-protocol.md`, `harness/bootstrap_board.sh`, and landing close-out behavior.
- Uncovered globs: none; the kit has no separate feature-registry glob for this mechanism.
