# PR1 — hub-file edits (to be integrated by the hub owner)

PR1 does not edit `INSTALL.md`, `README.md` or `user-level/README.md`. The
exact edits it needs in those files are below, verbatim, anchored to the text
on main `06a45d06618cfec29ba2244a47bb7be6b590a83e`.

## INSTALL.md

### Edit 1 — Step 1, item 1 (anchor: `1. Copy \`planning/*.md\` → \`docs/\` and resolve every {{PLACEHOLDER}}.`)

Replace with:

```
1. Copy `planning/*.md` → `docs/` and resolve every {{PLACEHOLDER}}.
   `planning/execution-contract.md` is the one home of the measurement
   baseline and the two-round limit; the lane brief only parameterizes it
   (§8 of that file lists the parameters). Keep its section numbers —
   briefs cite them.
```

### Edit 2 — Step 1, item 3 (anchor: `3. Copy \`planning/lane-brief-template.md\` → \`.claude/templates/lane-brief.md\``)

Replace the item with:

```
3. Copy `planning/lane-brief-template.md` → `.claude/templates/lane-brief.md`
   and parameterize: the gate block with the repo's pregate commands,
   `{{FIRST_CONTACT_STOPS}}` with the repo's guarded boundaries and number
   rules, `{{PARK_DESTINATION}}` with where parked remainders are tracked
   (a board item, or the backlog row your planning gate governs). The
   per-lane fields (task ID, round, apparatus, proof owner, attachments,
   ceiling) are filled at dispatch, never in the template.
```

### Edit 3 — Step 5 (anchor: the paragraph beginning `Copy \`harness/launch_lane.sh\` to your orchestration scratchpad.`)

Replace `and \`harness/report-schema.md\` (sentinel + structured report +
mandatory \`choices:\` self-report + circuit breakers).` with:

```
and `harness/report-schema.md` (sentinel + structured report carrying
`task:`/`round:`, `measurements:`, `revision_table:` with a named proof
owner, the mandatory `choices:` self-report and its `<lane>-choices.md`
sidecar). Circuit breakers are not in the schema: they live in
`planning/execution-contract.md` §3–§6.
```

### Edit 4 — Step 7, item 1 (anchor: `1. Create one trivial board item, write a mini-spec, dispatch one lane from`)

Replace the item with:

```
1. Create one trivial board item, write a mini-spec, dispatch one lane from
   the standing brief, run the choices audit on the handback, assemble a
   single-lane train, run full verify, land, sweep the board. Fill the
   execution-contract fields for real even on the trivial task: `task:` is
   the item ID, `round: 1`, the apparatus is named, and if the lane cannot
   run it the proof owner is a role plus an exact command. Then run the
   rewrite check in `harness/report-schema.md` on the handback.
```

### Edit 5 — Step 7, add item 4 after item 3 (anchor: `A factory whose smoke test has not run is not installed — it is copied.`)

Insert before that closing sentence:

```
4. Falsify the round counter: re-dispatch the same item under a new lane
   name and confirm the wrapper writes `round: 2`; attempt a third and
   confirm it is refused without a logged restart-from-document.
```

## README.md

### Edit 1 — pillar table, `planning/` row (anchor: `| **\`planning/\`** | *Define why, what, how* |`)

Replace the Contents cell with:

```
Board protocol (GitHub Projects as planning truth), spec discipline, ADR + number registry, backlog discipline with closing evidence, the standing lane brief, and the execution contract (measurement baseline handed over before dispatch, a named proof owner, two complete rounds per task then park-and-split)
```

### Edit 2 — shared infrastructure paragraph (anchor: `**\`harness/\`** (lane launcher, worktree ritual, board bootstrap, report
schema)`)

Replace `report schema` with `report schema with a choices sidecar`.

### Edit 3 — core loop block (anchor: the line `    (agent authors; the wrapper commits; red/green falsification)`)

Replace with:

```
    (evidence attached first; agent authors; the wrapper commits and pushes
     the branch; the named proof owner reruns the apparatus; two rounds max)
```

## user-level/README.md

No edit needed for PR1.
