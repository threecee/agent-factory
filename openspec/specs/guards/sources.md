review: pending

# Guards sources

## 1. Requirement sources

- **Dispatch each event to applicable rules:** `harness/guards.md §3`; `harness/tests/test_guards.sh 6c`.
- **Fail open on apparatus failure:** `harness/guards.md §3`; `decisions/0001-guards-fail-open.md`; `harness/tests/test_guards.sh 6a`; `verification/tests/test_git_hooks.sh 9d`.
- **Trace every switch use:** `harness/guards.md §4`; `decisions/0002-switches-precede-guards-and-leave-a-trace.md`; `harness/tests/test_guards.sh 5g`; `harness/tests/test_guards.sh 5h`.
- **Keep rule switches independent:** `harness/guards.md §4`; `harness/tests/test_guards.sh 5f`.
- **Falsify shipped rules by planting violations:** `harness/guards.md §11`; `harness/tests/test_guards.sh 9a`; `harness/tests/test_guards.sh 9d`.

## 2. Divergences

- None observed between the dispatcher, rule modules, documented contract, and falsification receipt.

## 3. Registry coverage

- Covered scope: `harness/guards/*.py`, `harness/guards/rules/*.py`, tracked hook adapters, and their shell suites.
- Uncovered globs: none; rule-specific behavior remains sourced through the guards capability rather than duplicated here.
