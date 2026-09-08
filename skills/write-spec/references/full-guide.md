
## Workflow

1. **Interview:** keep asking until you can name the slices without
   hand-waving. Stop when remaining unknowns can safely be discovered by the
   first slice.
2. **Research:** inspect the repo and research unfamiliar external practice
   before drafting when the feature names a reference, library, technique,
   standard, visual target, or performance pattern. Capture the discovered
   source/repo/article/paper links in the spec and turn any exemplar into a
   reproduction spike before a porting slice.
3. **Draft in parallel:** for a multi-slice feature, spawn **at least three
   independent subagents** to draft the whole plan — fresh context each, a git
   worktree apiece if they must run or build to validate, otherwise have them
   return the plan inline. Three is the floor, not the count: scale the pool
   with the feature's complexity, adding a drafter for each genuinely distinct
   approach or lens the problem supports. Give each the *same* brief from the
   interview and nothing else (never another draft) — but assign each a
   **distinct bias** so their divergence is structured, not accidental. The
   baseline trio:
   - **A — fewest-slices bias:** the smallest ladder that still ships; merge
     slices aggressively, question every rung.
   - **B — risk-first bias:** front-load the scariest unknowns; order slices so
     the plan dies fast if an assumption is wrong.
   - **C — seam-quality bias:** optimize API boundaries, ownership, and
     testability at each seam, even at the cost of more slices.

   Swap in or add lenses when the feature demands them (e.g. asset-pipeline
   bias, perf bias, migration-safety bias), but keep the biases orthogonal —
   grow the pool by adding a new lens, never by running the same lens twice.
   Also **mix model families**: if you're currently instructed to draft with
   codex, run at least one draft with claude — and vice versa — so the pool
   balances different models' blind spots, not just different prompts. Family
   means vendor (claude vs codex), not tier: every draft uses a
   state-of-the-art model; never diversify by dropping to a weaker tier of the
   same family. Each drafter: recon the real code and tests (measured facts,
   failed approaches, scope firewalls, greppable file/test names), then propose
   the slice graph, package/app boundaries, dependencies, API seams, playable
   deliverables, verification gates, and human review checkpoints. Skip the
   fan-out only for a genuinely single-slice problem.
4. **Synthesize:** read every draft and build the canonical plan yourself —
   don't anoint one. Take the strongest slicing, union the seams, risks, and
   firewalls each caught alone, and where drafts disagree pick the
   better-justified call and record the genuine alternative for the human. Where
   the drafts independently agree you're on firm ground; where they split is
   where to think hardest. When the feature has any visual surface, make
   [screenshot-critique](../../visual/screenshot-critique/SKILL.md) a standing
   verification gate in the README so every visual slice inherits it: the spec
   must tell the implementing agent to run an unbiased screenshot-critique as the
   last check on any visual shot before accepting it. Whenever a slice has
   something to compare its shot against — a prior look it changes, or a
   reference/inspiration image added for the feature — the spec must also name
   [compare-screenshots](../../visual/compare-screenshots/SKILL.md) as the gate
   that judges candidate-against-target: the telemetry and less-wrong verdict
   that screenshot-critique's single-shot eyes do not give.
5. **Recursive fog audit:** review the canonical graph slice by slice. For any
   slice with hidden variables, broad verbs ("make it realistic", "match the
   reference", "add the backend"), missing research, or more than one visual
   variable/API seam, run this same slicing logic on that slice as a sub-feature.
   Keep repeating until the next implementation slice can be accepted or rejected
   by one focused artifact. Record deferred variables as later slices, not prose
   inside the current slice. The exit test is the **decision budget**: a slice is
   fully specified when the implementing agent inherits decisions rather than
   making them — every freedom left open is either named as delegated in the
   slice file or the slice needs another pass.
6. **Materialize:** create `specs/<feature>/` when the feature has more than
   one slice or needs assets/visualizations.
7. **Refactor-clean the plan:** run [refactor-clean](../refactor-clean/SKILL.md)
   over the materialized spec — the plan is architecture too, and it must describe
   the shape the codebase would want if designed today, not the old shape with the
   feature bolted on. Name each concept that should have one owner (projection,
   environment, data contract, renderer phase, state machine, test oracle) and
   confirm no slice introduces a parallel abstraction, duplicated concept, or
   compatibility layer that a later slice must delete. Any transitional scaffolding
   a slice genuinely needs must be named as a short-lived seam with an explicit
   removal condition and the slice that removes it — collapsed the instant its
   consumers migrate, never carried to the end by default. Encode the resulting
   single-owner invariants and the end-state ("reads as designed today, not tacked
   on") in the README so every implementing pass inherits them.
8. **Scrollback audit:** the conversation dies; the spec survives. Before
   calling the plan done, sweep the full conversation and every earlier
   planning artifact (maps, interview notes, drafts) for content that exists
   only there — decisions with their rationale, rejected alternatives with
   why they lost, mid-stream scope changes, user-supplied constraints and
   throwaway remarks that decided something. Each either lands in its owning
   spec file or is deliberately dropped; a scope change propagates to every
   spot that references it, not just where it landed. Then re-read each
   surviving pre-plan artifact the spec supersedes (a map's kickoff prompt,
   open-questions list, or proposed plan) and mark superseded sections with
   a pointer to the plan — stale instructions must not be able to misroute a
   fresh agent. Done when every conversation decision is findable in the
   spec and no surviving artifact contradicts the ladder.
9. **Build slice by slice:** leave each slice with a runnable artifact and
   verification before depending on it. Keep each artifact small enough to
   iterate on quickly. Keep the README's "Next Agent Prompt" written as the
   handoff text a future agent should read and follow.
10. **Reslice when the work says so:** if implementation hits a snag and the slice
   starts changing unrelated variables — or the choices ledger keeps filling
   from one slice — stop broadening the patch. Update the spec
   first: split the slice into smaller contracts, name the frozen inputs, move the
   extra visual variables to later slices, and rewrite the Next Agent Prompt to
   resume from the first new slice. Then continue. Reslicing is progress, not
   failure.

## Plan Folder

Use `specs/<feature>.md` only for a small, single-slice problem. Large
features live in:

- `specs/<feature>/README.md` — goal, context, slice graph, review map,
  contracts, firewalls, known unknowns, and a "Next Agent Prompt" section with
  the current status, next pickup point, global TODO checklist, and handoff
  instructions for the next pass.
- `specs/<feature>/slices/<NN>-<name>.md` — one independently verifiable
  slice per file.
- `specs/<feature>/visualizations/*.html` — roadmap diagrams, prototypes,
  harness mockups, generated reports, contact sheets, or other
  human-reviewable artifacts.
- `specs/<feature>/assets/` — reference images, fixtures, captures, and other
  inputs needed to judge the work.

For visual work, keep feature-owned visual evidence in the spec folder:
inspiration images, reference screenshots, archived baselines, comparison
contact sheets, generated candidate captures, and critique artifacts. If those
files start outside the spec folder, copy them into the spec folder when they
become part of the feature's review context. Product snapshot folders may still
hold the active regression baselines their harnesses own, but do not rely on
those mutable outputs or external paths as the only record of what the feature
was judged against.

## Slice File Contract

Each slice file answers:

- What contract does this unlock?
- What is the API seam: module, functions/types, data shape, ownership?
- What can the human run or see?
- What tests, scenarios, screenshots, probes, or perf gates verify it?
- If the slice produces any visual shot (screenshot, GIF, contact sheet, or
  on-screen render), the slice file must instruct the implementing agent to run
  [screenshot-critique](../../visual/screenshot-critique/SKILL.md) as the last
  check before the slice is accepted — an unprimed second opinion the regression
  gates and the implementer's own inspection cannot supply. Write this as an
  explicit verification step in the slice, not as a passing mention.
- If the slice's shot has a target to compare against — a prior look it changes,
  or a reference/inspiration image added for the feature — the slice file must
  also instruct the agent to use
  [compare-screenshots](../../visual/compare-screenshots/SKILL.md) to judge
  candidate-against-target: telemetry plus a less-wrong verdict, not a check that
  the shot matches the reference. Write it as an explicit step too.
- For visual slices with a reference image, state the **slice variable** and the
  **crop/mask** used to judge it. Also list visible wrongness that is explicitly
  out of scope. Example: a grass-density slice compares lower-third coverage and
  falloff only; cliff shape, cliff texture, water, sky, and fog are later slices.
  A cliff-silhouette slice compares the ridge outline and depth rows only; rock
  texture and haze are later slices.
- What decisions are delegated to the implementer? Name the freedoms
  deliberately left open (internal structure, naming, reversible cosmetic
  calls). Everything else must be resolved by the slice: an unlisted decision
  the implementer has to invent is a spec gap that lands in the choices ledger
  ([audit-choices](../audit-choices/SKILL.md)), not implementer discretion.
- What must stay green?
- What feedback from the human would change this slice?
- If the slice has a human review checkpoint, the slice file must frame it as
  **non-blocking**: tell the implementing agent to open the shots for the user
  with [preview-shots](../../visual/preview-shots/SKILL.md), give a short window
  (~5 min) for a response, and — if the user stays silent — decide on the
  evidence, record the decision and rationale in the spec, close the opened shots
  (preview-shots cleans up Preview, so an overnight run never piles up windows),
  and proceed. Implementation never stalls waiting on sign-off; the checkpoint is
  a chance to course-correct a reversible call, not a gate that blocks the build.

## README Handoff Prompt

Every multi-slice spec README needs a "Next Agent Prompt" near the top. Write it
in second person, as the prompt a future agent should read when they resume the
feature. The README should not merely describe that it is live handoff state;
the section itself must directly tell the next agent what to do next. It should
include:

- Current status and last-updated date.
- The exact next pickup point.
- Active blockers or warnings.
- A global TODO checklist, with each item pointing to the owning slice.
- A direct instruction to the next agent to update this section before ending
  their pass.

The point is that a fresh agent can open the README and know what to do next
without reading the chat.
