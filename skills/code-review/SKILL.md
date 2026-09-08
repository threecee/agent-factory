---
name: code-review
description: Review a current diff for correctness, stale references, ownership, test quality, unnecessary compatibility, and cleanup. Use when asked to audit code or before work is handed off.
allowed-tools: Read Grep Glob Bash
---

# Code Review

Review the diff or specified files against these principles.


## Trigger

Use for a current staged or unstaged diff, or the change named by the caller.

## Checklist

1. Check names, comments, and references against current reality.
2. Check ownership boundaries, API scope, data access, and compatibility paths.
3. Check tests through observable consumer behavior and the real toolchain.
4. Check cleanup, dead code, and every incidental changed path.
5. Report each finding with a file and line, grouped by category.

Detailed review rules and examples: [full guide](references/full-guide.md).
## Your task

Review: $ARGUMENTS

If no arguments given, review `git diff --staged` or `git diff` (unstaged changes).

For each issue found, cite the file and line number. Group by category. End with a clean/not-clean verdict.
