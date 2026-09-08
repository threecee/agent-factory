---
id: ADR-0006
status: Accepted
code:
  - planning/capability-specs.md
  - interpretation/choices-ledger-README.md
tests:
  - harness/tests/test_capability_spec_flow.sh
  - verification/tests/test_adr_anchors.sh
---

# ADR-0006: Three durable artifacts answer three questions

## 1. Context

Approved work produces several kinds of records. A build plan is useful while making a change but becomes misleading if it is treated as the current product contract, architecture rationale, or audit of choices made during execution. The artifact roles are defined in `../planning/capability-specs.md §1`.

## 2. Decision

The durable artifacts are capability specs for current observable behavior, ADRs for architecture rationale and implementation binding, and the choices ledger for decisions made while carrying out approved work. Architecture and pattern maps orient readers across those artifacts but do not create a fourth store of behavioral rules. Build specs are transient and are archived after delivery.

## 3. Consequences

Each question has one durable home and readers do not need to reconstruct current behavior from old change plans or pull-request prose. Changes that alter behavior update the matching capability; changes that alter rationale update or supersede an ADR; execution choices enter the ledger.

## 4. Evidence

The capability flow test exercises strict validation and archival, and the ADR anchor test requires every kit decision to retain resolvable implementation and proof links.
