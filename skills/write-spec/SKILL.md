---
name: write-spec
description: Break risky or multi-step features into independently verifiable, human-reviewable slices. Use when work needs explicit seams, research, playable checkpoints, or a durable implementation handoff.
---

# Write Spec

Turn a large feature into a ladder of small contracts. Each rung should be
understandable to the human, testable by an agent, and useful before the
whole feature is done.


## Trigger

Use for feature planning that needs multiple reviewable slices or durable handoff state.

## Checklist

Apply the First Principles below before writing the plan.

## First Principles

1. **Grill before planning.** Ask one question at a time until you know the
   desired outcome, non-goals, review surface, sacred contracts, missing
   assets, and first useful playable checkpoint. Give your recommended
   answer with each question so the user can accept, reject, or edit it.
   Inspect the repo instead of asking questions the code can answer.
   Close the interview by asking whether the plan must carry backward
   compatibility or data migrations — the default is **neither**: hard
   cutovers, no compat shims, no migration scaffolding, no deploy-order
   dances. Only the user opting in puts them in the plan.

2. **Slice at API seams.** Each slice should behave like a tiny library where
   possible: named module boundary, typed inputs/outputs, deterministic
   fixtures, and tests at the seam. If a slice needs three unrelated systems
   booted before it can be checked, sharpen the seam.

3. **Research the fog.** When the feature depends on an unfamiliar domain,
   high-fidelity visual target, named reference, benchmark, external repo,
   library, or "how do people usually do this?" question, do targeted online
   research before finalizing slices. Prefer primary sources: official docs,
   source repos, papers, case studies, talks, and shipped examples. If a
   reference implementation exists, add a replication spike before translation
   or approximation.

4. **Make progress visible.** For visual or interactive work, every slice
   should produce something playable: a route, fixture page, harness, CLI
   probe, or HTML visualization the human can run, inspect, screenshot, and
   critique. Tests prove contracts; demos expose taste and intent.

5. **Optimize feedback loops.** Slice so the next useful question can be
   answered quickly. Prefer tiny runnable surfaces, hot-reloadable harnesses,
   sample fixtures, and self-contained workbenches over plans that require the
   whole feature to exist before anyone can learn from it. For asset-heavy
   work, plan an asset app/workbench where humans and artists can add samples,
   upload replacements, preview them live, and see validation failures fast.

6. **Use the repo's natural shape.** If the repo is a monorepo, plan apps and
   packages instead of forcing everything into the current app. Give each
   testable surface a first-class route or command; avoid piling new behavior
   behind opaque query flags when a small dedicated app would be clearer.

7. **Do not block on missing inputs.** If art, data, credentials, or external
   assets are missing, plan generated placeholders plus a replacement contract.
   The feature should advance with placeholders, while a separate handoff path
   explains exactly what the human or external partner must provide later.

8. **Draft in parallel, then synthesize.** For any multi-slice feature, don't
   trust one pass to find the right cut. Fan out a few independent drafts and
   merge the best into one plan (see the Workflow). Divergence is the point —
   so engineer it on two axes: give each draft a different *bias* (a lens it
   optimizes for) and, when more than one model family is available, a mix of
   *models*. Blind, differently-biased drafts surface slices, seams, and risks
   a lone plan misses — and where they independently agree, you know the cut
   is solid.

9. **Recursively uncover fog of war.** The first slice graph is a scouting pass,
   not proof the field is known. After drafting, inspect each high-risk slice as
   if it were its own feature. If it hides multiple variables, unknown external
   practice, unproven architecture, or "we'll figure it out during
   implementation," reslice that subset and repeat until every next slice has
   one question, one seam, one review surface, and one verdict.

10. **One visual variable per slice.** Visual slices fail when they ask one pass
   to match the final hero image. Split by the thing being judged: density,
   silhouette, colour, texture, lighting, fog, water placement, water material,
   label legibility, animation rhythm. Each slice gets a crop/mask and a verdict
   for that variable only. Whole-frame comparison belongs at compose/integration,
   after the variables have their own evidence.


Detailed workflow, file contracts, and handoff examples: [full guide](references/full-guide.md).
## Done

The feature plan is done when a fresh agent can start at slice 1 without the
conversation, and the human can review the roadmap without reverse-engineering
a wall of text.

Once the slices have all shipped, [close-spec](../close-spec/SKILL.md) archives
the plan to `specs/done/` and rewrites it from a build ladder into a durable
rationale record.
