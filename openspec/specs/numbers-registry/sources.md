review: pending

# Numbers registry sources

## 1. Requirement sources

- **Reserve a number before authoring:** `planning/adr-and-numbers.md` “The number registry (NUMBERS.md)”.
- **Centralise number allocation:** `planning/adr-and-numbers.md` “The number registry (NUMBERS.md)”.
- **Maintain one lifecycle row per number:** `planning/adr-and-numbers.md` “The number registry (NUMBERS.md)”; `verification/lander-duties.md §8`.
- **Detect stale claimed state:** `verification/protections.md §7`; `verification/tests/test_landing_protections.sh 24`.

## 2. Divergences

- The kit registry is rooted beside the kit's decision records, while installed projects use the parameterised decision directory described by the installation runbook.

## 3. Registry coverage

- Covered scope: `decisions/NUMBERS.md`, numbered files under `decisions/`, registry drift checks, and landing close-out.
- Uncovered globs: none; migration identifiers remain an installed-project concern outside this kit mechanism.
