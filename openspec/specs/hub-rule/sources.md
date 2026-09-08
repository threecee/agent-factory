review: pending

# Hub rule sources

## 1. Requirement sources

- **Pair each hub pointer with one gloss:** `README.md §0`; `decisions/0003-hub-pointers-with-one-sentence-glosses.md`.
- **Resolve every cited target:** `verification/tests/test_hub_pointers.sh 2`; `verification/tests/test_hub_pointers.sh 3`; `verification/tests/test_hub_pointers.sh 3f`.
- **Reject unbound continuation sections:** `verification/tests/test_hub_pointers.sh` case 3d and the scanner contract at the top of that file.
- **Verify the complete documentation tree:** `verification/tests/test_hub_pointers.sh 6`; `verification/tests/test_hub_pointers.sh 7`; `verification/tests/test_hub_pointers.sh 8`.

## 2. Divergences

- None observed between the hub prose and the planted pointer cases.

## 3. Registry coverage

- Covered scope: root hub documents and every Markdown file included by complete-tree mode.
- Uncovered globs: locked skill Markdown is intentionally excluded and verified by the separate skills lock.
