---
name: finishing-a-development-branch
description: Use after implementation and tests are complete to choose and safely execute merge, pull-request, keep, or discard handling while respecting normal, linked, and harness-owned workspaces.
---

# Finishing a Development Branch

## Overview

Guide completion of development work by presenting clear options and handling chosen workflow.

**Core principle:** Verify tests → Detect environment → Present options → Execute choice → Clean up.

**Announce at start:** "I'm using the finishing-a-development-branch skill to complete this work."


## Trigger

Use only after implementation is complete and the relevant test suite has passed.

Detailed environment detection, option execution, cleanup, and safety rules: [full guide](references/full-guide.md).

## Checklist

## Quick Reference

| Option | Merge | Push | Keep Worktree | Cleanup Branch |
|--------|-------|------|---------------|----------------|
| 1. Merge locally | yes | - | - | yes |
| 2. Create PR | - | yes | yes | - |
| 3. Keep as-is | - | - | yes | - |
| 4. Discard | - | - | - | yes (force) |


## Done

Done when the chosen integration action is verified and only workspace state owned by this workflow has been cleaned up.
