review: pending

# Choices ledger sources

## 1. Requirement sources

- **Give every choice one stable identity:** `interpretation/choices-ledger-README.md §2`; `verification/tests/test_landing_protections.sh 23`.
- **Record a verdict and confidence:** `interpretation/choices-ledger-README.md §1`; `verification/tests/test_landing_protections.sh 23`.
- **Resolve unsound choices before landing:** `interpretation/choices-ledger-README.md §1`; `verification/tests/test_landing_protections.sh 23`.
- **Carry overrides into the train record:** `interpretation/choices-ledger-README.md §1`; `harness/tests/test_guards.sh 5g`; `verification/tests/test_landing_protections.sh 23g`.
- **Preserve detailed scenarios with the handback:** `interpretation/choices-ledger-README.md §3`; `harness/report-schema.md` “Rules”; `harness/tests/test_launch_lane.sh 12c`.

## 2. Divergences

- None observed between the ledger protocol, report schema, landing lint, and shell cases.

## 3. Registry coverage

- Covered scope: the choices protocol, result handback, landing lint, and switch event trail.
- Uncovered globs: none; the ledger is a document protocol with no separate feature-registry glob.
