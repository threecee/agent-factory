---
name: refactor-clean
description: Refactor toward one clear owner per concept instead of adding sediment. Use when a change reveals duplication, obsolete paths, compatibility wrappers, parallel abstractions, or an overloaded module.
---

# Clean Refactoring

Replace the old shape with the simpler shape the codebase would want if it were
designed today. Refactoring is not adding a compatibility layer beside the problem;
it is moving ownership until every concept has exactly one clear home. That cuts
both ways: merging N duplicated owners into one, and splitting one over-loaded
module into the several owners it was hiding.


## Trigger

Use when the current shape obscures ownership or makes a small behavior change disproportionately costly.

## Checklist

## Workflow

1. Name the concept that lacks one clear owner — duplicated across several owners,
   or several concepts fused into one over-loaded module. Identify the thing(s)
   that should each have one owner: environment, pricing rule, geometry source,
   state machine, data contract, renderer phase, API shape, UI state, or test
   oracle.
2. Find every current owner and consumer. Treat wrappers, aliases, pass-local
   constants, copied structs, and "temporary" branches as sediment until proven
   otherwise. Consumers are more than importers: a test in another language
   that reads the file as text, a tool whose baseline is keyed by the file's
   path, a test that patches a dotted name, a driver executed by a test from a
   research directory. Before the first move, split, rename or delete, run the
   consumer inventory in `interpretation/investigation-practice.md`
   ("Consumer inventory") and decide live-versus-historical per file from
   executing readers, not from the directory a file sits in.
3. Promote the concept to its natural home. Pick the module that would own it from
   scratch, then make old call sites consume that owner directly.
4. Delete or collapse the stale path in the same pass when feasible. If a bridge must
   remain, make it tiny, named as compatibility, and give it a removal condition.
5. Verify behavior through consumers, not just the new module. A clean refactor is
   only proven when the surfaces that used to diverge now report or exercise the
   same source of truth — and when each consumer's own apparatus has run (the
   frontend contract, the path-keyed SAST gate, the docgen run), not only the
   module's suite. A moved line is a NEW finding to a path-keyed baseline: fix
   the code, never relieve the baseline for the move. A guard that patches a
   name and stays green proves the name existed, not that the path was taken;
   pin it at the owner and show it red on a planted call before the refactor
   leans on it.


## Done

Done when each concept has one clear owner, stale paths are removed or explicitly bounded, and every affected consumer proves the new invariant.

Detailed refactoring rules and examples: [full guide](references/full-guide.md).
