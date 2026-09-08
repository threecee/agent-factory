---
id: ADR-0003
status: Accepted
code:
  - README.md
  - INSTALL.md
  - verification/tests/test_hub_pointers.sh
tests:
  - verification/tests/test_hub_pointers.sh 2
  - verification/tests/test_hub_pointers.sh 3f
---

# ADR-0003: Hubs use pointers with one-sentence glosses

## 1. Context

The root guide and installation runbook must make a large kit navigable without becoming competing copies of its rules. Repeated rule prose drifts, while bare links do not tell a reader why to follow them. The current hub contract is introduced in `../README.md §0`.

## 2. Decision

A hub names a rule through a resolving repository pointer and adds no more than a one-sentence gloss. The linked document remains the single home of the rule. A deterministic tree check validates file paths, numbered sections, continuation sections, and quoted headings.

## 3. Consequences

Hub documents stay useful without acquiring a second policy surface. Renaming or removing a target requires updating its readers in the same change, and a planted dead pointer proves the check can detect drift.

## 4. Evidence

The pointer test scans the package hubs and the Markdown tree. Its cited cases plant a dead path and a missing quoted heading, then require a red verdict that identifies the broken pointer.
