---
id: ADR-0004
status: Accepted
code:
  - harness/guards/rules/landing.py
  - verification/gates/check_choices_protocol.py
  - user-level/landing-policy.example.md
tests:
  - verification/tests/test_git_hooks.sh 8a
  - verification/tests/test_landing_protections.sh 23g
---

# ADR-0004: Pull requests default, with owner-signed direct push

## 1. Context

A verified train still needs an auditable landing path and explicit authority. Pull requests preserve a host-visible hold and merge record; some repositories legitimately require a direct update path. The complete mode contract lives in `../verification/landing-modes.md §1`.

## 2. Decision

Pull-request mode is the default. Direct push is available only when an active owner-signed policy declares it with a standing reason, or when the train ledger records the explicit override reason and the owner authorizes that landing. Both modes use the same verified receipt and close-out duties.

## 3. Consequences

The ordinary path preserves review and host history. Direct push remains possible but cannot be inferred from convenience, prior chat, or a successful verification run; its authority and reason remain inspectable.

## 4. Evidence

The landing guard enforces receipt and merge shape, while the ledger check requires an override reason against the default. The cited shell cases prove the accepted pull-request merge and the refused direct-push ledger without a reason.
