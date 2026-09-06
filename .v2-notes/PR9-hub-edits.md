# PR9 — requested hub-file edits (not applied in this branch)

PR9 carries G16 (read-only root-cause investigation as a testable brief
pattern). The hub files INSTALL.md, README.md and user-level/README.md are
shared by many PRs and are integrated later; the exact edits PR9 wants in
them are recorded here verbatim. Everything else PR9 touches is edited
directly in this branch.

## INSTALL.md

**Anchor:** "## Step 1 — Planning pillar", item 3
("Copy `planning/lane-brief-template.md` → `.claude/templates/lane-brief.md`
and parameterize the gate block with the repo's pregate commands.")

**Insert a new item after it (renumber the following items):**

```markdown
4. Copy `planning/investigation-brief-template.md` →
   `.claude/templates/investigation-brief.md`. It is the read-only lane a
   bug goes through BEFORE it gets a fix brief when the cause is uncertain:
   pinned SHA, frozen evidence package (harness/artifact-bank.md), competing
   hypotheses, verdicts with sources, no code change. Its §8 is the boundary
   to the fix brief; do not add a mandatory investigation phase for trivial
   reproduced defects (its §0 says when).
```

**Anchor:** "## Step 3 — Interpretation pillar", item 3
("Read `interpretation/investigation-practice.md` — instrument-first is the
default for every debugging lane.")

**Replace with:**

```markdown
3. Read `interpretation/investigation-practice.md` — instrument-first is the
   default for every debugging lane, and "investigate before the fix lane
   gets its mandate" is the default whenever the cause is uncertain (the
   brief is `planning/investigation-brief-template.md`; the trust rules are
   `verification/falsification.md` §7–§9).
```

**Anchor:** "## Step 2 — Verification pillar", item 4
("Read `verification/falsification.md` and apply it from day one.")

**Replace with:**

```markdown
4. Read `verification/falsification.md` and apply it from day one. Rules
   §7–§9 govern root-cause reports: falsify the causal model before the fix
   (or as the fix's first red test), refute only with a source, and keep an
   unknown cause unknown.
```

## README.md

**Anchor:** the "three pillars" table, row **`planning/`**, column
"Contents". Current text ends with "…the standing lane brief".

**Replace the cell's tail:**

`…backlog discipline with closing evidence, the standing lane brief, the read-only investigation brief that precedes a fix brief when the cause is uncertain`

**Anchor:** same table, row **`interpretation/`**, "Contents". Current text
contains "investigation practice (instrument-first)".

**Replace that fragment with:**

`investigation practice (instrument-first; investigate before the fix mandate)`

**Anchor:** "## The core loop (one screen)", the code block. Current line:

```
  → lane brief from the standing template → parallel lane in its own worktree
```

**Insert immediately before it:**

```
  → (uncertain cause) read-only investigation on frozen evidence → falsified causal model
```

## user-level/README.md

No edit requested by PR9. The investigation brief is a repo-level template;
the operator's model/effort choice for investigators comes from PR7's dated
model policy, which user-level/README.md will reference under PR7.
