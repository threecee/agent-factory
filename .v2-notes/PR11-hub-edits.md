# PR11 — requested edits to the shared hub files

PR11 does not touch `INSTALL.md`, `README.md` or `user-level/README.md`
(HUB FILES RULE). The integrator applies the edits below verbatim. Each
edit points to the home; none duplicates it.

Homes introduced or extended by PR11:

- `user-level/landing-policy.example.md` — NEW, INACTIVE; the one home for
  local landing authority (who granted what, how long, what still stops).
- `planning/decision-brief-template.md` — NEW; the form a hold takes.
- `planning/board-protocol.md` — § Decision needed, § Notifications,
  § Derived views; three new transaction rows.
- `verification/lander-duties.md` — step 9/10 amended; § Landing authority,
  § Derived views.

Overlap note for the integrator: PR3 also touches `board-protocol.md` and
`lander-duties.md` (G5/G12). PR11 carries the G12 text in the two § Derived
views sections; if PR3 lands its own G12 wording, keep ONE of them (the
board-protocol section owns authority, the lander-duties section owns the
checkpoint) and drop the other's duplicate — never both.

---

## 1. `user-level/README.md`

**Anchor:** after item 3 ("User-level skills …"), append item 4.

**Insert (verbatim):**

```markdown
4. **Landing authority (optional, INACTIVE by default):** the factory grants
   no push authority by installing it. A finished train with no live ruling
   from the owner is HELD with a decision brief
   (`../planning/decision-brief-template.md`). If — and only if — the owner
   wants the lander to land verified P1 trains without a live ruling, the
   owner copies `landing-policy.example.md` to `~/.claude/landing-policy.md`,
   fills every field, sets `status: ACTIVE` and signs it. Nothing to install
   otherwise; the example stays inactive. The unsound-choice, migration, ADR,
   calibration and first-contact-STOP holds stop a train regardless of the
   policy (`landing-policy.example.md` §2 `holds:`).
```

## 2. `INSTALL.md`

**Edit 2a — Step 1 (Planning pillar), item 2.** Replace

```markdown
2. `planning/core-model.md` + `planning/board-protocol.md` are law, not
   inspiration: the board is the planning source of truth; every dispatch and
   landing has a board transaction (see the table in board-protocol).
```

with

```markdown
2. `planning/core-model.md` + `planning/board-protocol.md` are law, not
   inspiration: the board is the planning source of truth; every dispatch and
   landing has a board transaction (see the table in board-protocol). A
   ruling the owner must give is filed as a decision brief
   (`planning/decision-brief-template.md`, copied with the rest) — the owner
   reads the brief, never the conversation.
```

**Edit 2b — Step 6 (User level).** Replace

```markdown
## Step 6 — User level
Follow `user-level/README.md`: add the global CLAUDE snippet to the user's
`~/.claude/CLAUDE.md`, establish the memory conventions, install the
recommended user-level skills.
```

with

```markdown
## Step 6 — User level
Follow `user-level/README.md`: add the global CLAUDE snippet to the user's
`~/.claude/CLAUDE.md`, establish the memory conventions, install the
recommended user-level skills. Do NOT activate
`user-level/landing-policy.example.md` — it ships INACTIVE and only the
owner activates it, in person. Until then every finished train is held with
a decision brief (`verification/lander-duties.md` § Landing authority).
```

**Edit 2c — Step 7 (Smoke test), item 3.** Replace

```markdown
3. Land with `make verify && git push` — never an unconditional push after a
   verify you did not read.
```

with

```markdown
3. Land with `make verify && git push` — never an unconditional push after a
   verify you did not read — and only on the owner's live ruling for the
   smoke train (the owner is present for the smoke test; that ruling IS the
   authority, recorded on the smoke item). Do not treat the smoke landing
   as a grant of standing authority.
```

## 3. `README.md`

**Edit 3a — pillar table, `planning/` row, Contents cell.** Replace

```
Board protocol (GitHub Projects as planning truth), spec discipline, ADR + number registry, backlog discipline with closing evidence, the standing lane brief
```

with

```
Board protocol (GitHub Projects as planning truth; decision briefs, one notification per transition, derived views), spec discipline, ADR + number registry, backlog discipline with closing evidence, the standing lane brief
```

**Edit 3b — pillar table, `verification/` row, Contents cell.** Replace

```
lander duties for landing trains
```

with

```
lander duties for landing trains (push gated on verify AND on landing authority — held with a decision brief by default)
```

**Edit 3c — "Shared infrastructure" paragraph.** Replace

```
**`user-level/`** (what goes into `~/.claude` so the factory works
from any checkout).
```

with

```
**`user-level/`** (what goes into `~/.claude` so the factory works
from any checkout, plus the INACTIVE landing-policy example — the only
place push authority can be granted, and only by the owner).
```

**Edit 3d — core loop block.** Replace the line

```
    → FULL local verify green → push main → CI deploys
```

with

```
    → FULL local verify green → landing authority? (ruling or active
      policy; else HOLD with a decision brief) → push main → CI deploys
```
