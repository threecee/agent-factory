review: pending

# Landing sources

## 1. Requirement sources

- **Require a current green train receipt:** `verification/landing-modes.md §2`; `verification/tests/test_git_hooks.sh 2e`; `verification/tests/test_git_hooks.sh 8d`.
- **Default to pull-request landing:** `verification/landing-modes.md §1`, `§4`, `§5`; `decisions/0004-pr-default-with-owner-signed-direct-push.md`; `verification/tests/test_git_hooks.sh 8a`; `verification/tests/test_landing_protections.sh 23g`.
- **Archive capability deltas before final verification:** `planning/capability-specs.md §4`; `harness/tests/test_capability_spec_flow.sh 4`.
- **Register and close out a successful landing:** `verification/landing-modes.md §6`; `verification/tests/test_git_hooks.sh 8f`; `verification/tests/test_git_hooks.sh 8g`; `verification/tests/test_landing_protections.sh 21`.

## 2. Divergences

- None observed between the landing modes, guards, close-out gate, and shell cases.

## 3. Registry coverage

- Covered scope: landing rules, landing protection gates, tracked push hooks, and archive flow.
- Uncovered globs: none; host configuration examples are evidence for the same observable landing capability.
