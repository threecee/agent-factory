---
id: ADR-0001
status: Accepted
code:
  - harness/guards/guard_dispatch.py
  - verification/protections/githooks/pre-commit
tests:
  - harness/tests/test_guards.sh 6a
  - verification/tests/test_git_hooks.sh 9d
---

# ADR-0001: Guards fail open on apparatus failure

## 1. Context

Guards offer immediate feedback in hook channels, but the surrounding harness or hook loader can fail independently of the work being attempted. Treating an apparatus crash as a product verdict would lock the operator out without proving that the attempted action is unsafe. The boundary between a guard and a gate is defined in `../harness/guards.md §1`.

## 2. Decision

A guard fails open when its rule, dispatcher, or hook loader cannot run. It emits a loud diagnostic that identifies the failed apparatus. A successfully evaluated hard finding may still refuse the action; fail-open applies to apparatus failure, not to a negative verdict.

## 3. Consequences

Operators can continue when advisory machinery breaks, while the diagnostic preserves the failure for repair. Decisions that require fail-closed enforcement remain gates or protected host rules rather than being represented as guards.

## 4. Evidence

The dispatcher isolates rule crashes and the tracked hook shims allow the git action when their driver is missing. The cited shell cases plant both failures and assert the observable open result and loud note.
