---
name: implement-spec
description: Implement an approved spec through reviewable passes. Use for long or multi-pass work that must keep code, verification evidence, decisions, and handoff state aligned until the whole spec is complete.
---

# Implement Spec

Build the active spec to completion, one reviewable pass at a time. The spec is
the source of truth, but the architecture is allowed to improve when the code
teaches you the plan is stale.


## Trigger

Use when an approved spec defines the work and completion means closing the entire spec.

## Checklist

1. Read the repo primer, spec handoff, next slice, and named skills.
2. Reconcile the plan with current code, then implement one coherent pass.
3. Run focused contract checks and any required visual proof.
4. Review every changed path, clean artifacts, and keep the handoff current.
5. Audit choices and repeat until every slice, TODO, and recorded decision is closed.

## Done

Done only when every slice and global TODO is closed, all gates and whole-spec review are green, the handoff has no remaining pickup, and the spec is archived.

Detailed workflow, rules, evidence format, and handback requirements: [full guide](references/full-guide.md).
