# Decision brief — what a Decision-needed item must carry

A decision brief is the document the owner reads INSTEAD of the conversation.
It is filed on the board item (status → Decision needed) the moment a
finished train, a lane, or a programme cannot proceed without a ruling. If
the owner cannot rule from the brief alone, the brief is incomplete — not
the owner.

The brief is the ONLY form a hold takes. A held train without a brief is a
train nobody can land; a brief without a held artifact is a question, and
questions do not stop the factory (`../interpretation/choices-ledger-README.md`:
needs-user gets a reversible provisional call).

## 1. The chain a brief must close

problem → evidence → options → recommendation → what continues meanwhile
→ decision → transition. Each link is a field below; a missing link is a
review finding on the brief, not on the reader.

## 2. Template

```markdown
**Decision needed — <item id> (<one-line title>)**  <date, real, UTC>

**Blocked:** <the owner-approved programme or item this holds; its board id
and status>.
**Artifact held:** <what is finished and waiting: train HEAD <sha>, boarded
lane SHAs, verify verdict + counts, choices audit verdict; or "none — the
question precedes the work">.

**Problem:** <two to four sentences: what was observed, where, under which
pinned code; the mechanism if known, "mechanism unknown" if not>.

**Evidence:** <banked paths or links, each pinned (SHA, run id, timestamp).
Say what each proves and what it does not. Investigations still running
are listed as running, not as findings.>

**Options:**
- **(A, recommended)** <action> → <consequence for the blocked programme,
  cost/time estimate, what it makes measurable>.
- **(B)** <action> → <consequence; which rule or earlier caveat it breaks
  or repeats>. <Advised against, and why.>
- (C …) only when a genuine third path exists; never pad.

**Recommendation:** <A/B, one sentence of reason>.
**Continues meanwhile (reversible, presupposes no answer):** <what runs,
what is banked, what is NOT started>.
**Held until decided:** <the push, the wave, the deletion …>.
**Board:** Status → Decision needed. Notification key:
`<item id> <train sha or "none"> held`.
```

The owner's reply completes the chain as a comment on the same item:

```markdown
**Decision <date>:** <A|B|other>. <One line of consequence: what lands,
what starts, what changes as standing policy, if anything.> Status → <In
flight | Done | Dropped>.
```

The lander's closing comment records the transition it executed:

```markdown
**Landed <date>:** <train sha> → main <sha>; <closed items>. <Next step
started.> Notification key: `<item id> <train sha> landed`.
```

Three comments, three transitions (`held`, `decided`, `landed`), three
notifications at most. `board-protocol.md` § Notifications owns
the keying rule that prevents a fourth.

## 3. Rules

1. **Readable without the conversation.** No "as discussed", no scratchpad
   paths, no session links as the only evidence. Banked evidence only
   (`../harness/artifact-bank.md`, introduced by PR5).
2. **Options carry consequences, not adjectives.** Each option names what
   it costs, what it breaks, and what it makes measurable. "Faster" is not
   a consequence; "repeats the previous run's caveat that the AI layers
   were unavailable, so the measurement is of the apparatus, not the
   product" is.
3. **Exactly one recommendation.** The lander recommends; the owner rules.
   A brief with no recommendation pushes the analysis onto the owner; a
   brief with two recommendations has not finished.
4. **Name the reversible part and keep it running.** Investigation,
   assembly, verification and banking never wait for a ruling. Only the
   irreversible step (push, delete, spend the expensive run) is held.
5. **Update, do not re-brief.** New evidence (a fix delivered and verified
   while the brief is open) is a dated update comment that keeps the same
   options and says whether the recommendation changed. The item stays in
   Decision needed until the owner rules.
6. **Record the ruling where the brief is.** A ruling given in chat is
   copied to the item by whoever received it, verbatim, dated. The choices
   ledger for the train cites the item, never the chat.
7. **A hold has a length.** Record how long the artifact was held (the
   source factory: about two hours for the example below). Repeated long
   holds on the same category are the evidence the owner needs to decide
   whether to grant standing authority
   (`../user-level/landing-policy.example.md`) — the brief does not ask for
   it.

## 4. Worked example (anonymized from the source factory)

The programme: an owner-approved evaluation rerun — an eight-persona
browser wave against a fresh, fully warmed copy of a large synthetic case
("a 25k-message case"). The factory's readiness rule: no AI evaluation
before every background warmer has finished on the served copy.

**Comment 1 — the hold (03:00 UTC):**

> **Decision needed — #EVAL-RERUN (persona wave, second run)**  2026-09-06
>
> **Blocked:** the rerun itself (In flight, owner-approved).
> **Artifact held:** none yet at 03:00 — the fresh warm-up is the blocker.
>
> **Problem:** the fresh AI-on warm-up of the 25k case did not converge:
> the timeline warmer failed both attempts (identity of its inputs moved
> under it during warming). The readiness rule cannot be met, and the
> pristine gate would reject the resulting copy anyway.
>
> **Evidence:** warm-up log, immutable database copy, manifest and wrapper
> banked under `<bank>/archive/<case>-standup-<blocker id>-<timestamp>/`.
> They show the two failures and their timing; they do NOT yet show the
> mechanism — a read-only root-cause investigation is running.
>
> **Options:**
> - **(A, recommended)** fix the blocker first (one lane), rebuild the
>   pristine, run the rerun → the wave then measures the product. Cost:
>   one lane + one train + a 2–3 h warm-up.
> - **(B)** run the wave now against the half-warm instance and label it an
>   apparatus measurement → breaks the readiness rule and repeats the
>   previous run's caveat ("AI layers unavailable"); the result could not
>   be compared with the baseline. Advised against.
>
> **Recommendation:** A.
> **Continues meanwhile:** the read-only investigation; the warm-up
> evidence is banked. **Held:** no wave is started.
> **Board:** Status → Decision needed. Key: `#EVAL-RERUN none held`.

**Comment 2 — the update (05:00 UTC, same item, same options):**

> **Update:** the fix is delivered and verified on train `<train sha>`
> (boarder `<lane sha>`): full verify green in the first run (frontend
> suite 2072, backend 7636 passed / 169 skipped / 2 xfailed), pregate
> clean, choices protocol ready (five sound, zero unsound). **Not pushed** —
> the landing is held for the ruling here.
> Under **A**: land the train (~5 min) → fresh warm-up (~2–3 h; measures
> how many plan attempts the warmer now needs) → pristine → copy + smoke →
> wave (~1 h). Under **B**: wave against the half-warm instance, labelled
> apparatus measurement. Recommendation unchanged: A.

**Comment 3 — the ruling (06:04 UTC, by the owner):**

> **Decision 2026-09-06: A.** Train landed (main `<sha>`, blocker closed).
> Rerun starts now: fresh warm-up under the landed code → pristine → copy
> + smoke → wave. Status → In flight.
> Standing policy from here: orchestrator-filed P1 fixes land autonomously
> with a verified train + choices protocol + notification afterwards.

**What the example proves and what it does not.** The hold path worked:
the train was held about two hours, the owner ruled from the brief, and
the train's choices protocol cites the item (its orchestrator entry "lane
dispatched without a ruling, landing held: the lane is reversible, the
train is assembled and verified, not pushed"). The standing policy in the
last line is the owner's grant; it is recorded in
`../user-level/landing-policy.example.md` § 4 as the right-hand column, and
the source factory had not yet exercised it when this was written. The
outcome of option A — the number of plan attempts and full convergence on
the large case — was still being measured by the rerun; this example does
not claim it.
