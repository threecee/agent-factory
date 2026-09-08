---
id: ADR-0002
status: Accepted
code:
  - harness/guards/guard_dispatch.py
  - harness/guards/_common.py
tests:
  - harness/tests/test_guards.sh 5g
  - harness/tests/test_guards.sh 5h
---

# ADR-0002: Switches precede guards and leave a trace

## 1. Context

A guard can misclassify an action or depend on an apparatus that is temporarily unavailable. Mounting it without a usable escape creates an operator lockout; allowing silent escapes destroys the audit chain. The operational switch contract has one home in `../harness/guards.md §4`.

## 2. Decision

Every switchable guard has its switch before the guard is mounted. Every use records the rule identifier and the source of the switch in the shared event trail, and the corresponding owner-facing choice is carried into the train ledger. Conditions intentionally defined without a switch say so explicitly.

## 3. Consequences

Operators retain a bounded recovery path and reviewers can distinguish a green path from an overridden one. Adding a guard now includes proving both its ordinary behavior and its switch behavior before mounting.

## 4. Evidence

The dispatcher resolves switch sources and owns the shared event append. The cited shell cases assert the number of switch records and the source carried by each record.
