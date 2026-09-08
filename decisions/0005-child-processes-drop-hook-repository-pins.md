---
id: ADR-0005
status: Accepted
code:
  - harness/guards/_common.py
  - harness/guards/rules/landing.py
tests:
  - harness/tests/test_guards.sh 9a
---

# ADR-0005: Child processes drop hook repository pins

## 1. Context

Git supplies repository-location variables to hooks. A guard that passes those variables to a child repository command can make the child inspect the shared hook repository rather than the worktree named by the guard, producing a verdict about the wrong tree. This protection boundary is documented in `../verification/protections.md §1`.

## 2. Decision

Children launched by hook-backed guard rules never inherit Git's repository and worktree pin variables. They retain the ordinary process environment after those hook-specific pins are removed and receive the intended repository location explicitly.

## 3. Consequences

Child checks observe the worktree selected by the rule rather than accidental hook state. New child-launch paths must use the same scrubbed environment boundary and include a planted pin in their falsification case.

## 4. Evidence

The shared guard utility builds the scrubbed environment and the landing rule uses it for registry checks. The guard falsification suite includes a planted repository pin and is exercised by the cited shell case.
