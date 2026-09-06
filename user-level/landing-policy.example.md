# Landing policy — local landing authority (EXAMPLE, INACTIVE)

```
status: INACTIVE            # this file grants nothing; see §1
```

This file is the ONE home for the question "may the lander push a verified
train to main without a live ruling from the owner?". Installing the factory
answers that question with **no**. The answer becomes **yes, within limits**
only when the owner of the target repo copies this file to the active path,
fills every field, sets `status: ACTIVE`, and signs it. Nothing in the
package, the templates or the skills grants push authority on its own.

The protocol that USES the answer — how a held train is presented, how a
decision is recorded, how transitions are announced — lives in
`../planning/board-protocol.md` (§ Decision needed, § Notifications) and
`../verification/lander-duties.md` (§ Landing authority). This file only says
WHO granted WHAT, for HOW LONG, and what still stops.

## 1. Activation and the check the lander runs

1. Active path: `~/.claude/landing-policy.md` (user level, outside every
   checkout, so one policy governs every repo the operator lands from). A
   repo may narrow it with its own `docs/landing-policy.md`; the narrower
   rule wins. Neither file is created by the installer.
2. A policy is active only when ALL hold: the file exists at the active
   path, it has a line `status: ACTIVE` and no line `status: INACTIVE`,
   `valid_until` is in the future, and `granted_by` and `signed` are
   filled. Anything else — file missing, `INACTIVE`, expired, unsigned, an
   `example` in the path — means **no authority**.
3. The check, run by the lander before any push (adapt the path):

   ```sh
   p=~/.claude/landing-policy.md
   test -f "$p" && grep -q '^status: ACTIVE' "$p" \
     && ! grep -q '^status: INACTIVE' "$p" \
     && expr "$(sed -n 's/^valid_until: *//p' "$p" | head -1)" \> "$(date +%F)" >/dev/null \
     && echo AUTHORITY || echo "NO AUTHORITY -> hold + decision brief"
   ```

   POSIX sh/bash/zsh; ISO dates compare as strings. Against this example
   file the check prints `NO AUTHORITY` (the status line says `INACTIVE`).
   That is the correct result for a fresh install. Falsify it once on the
   machine: a scratch copy with `status: ACTIVE` and a future `valid_until`
   must print `AUTHORITY`; the same copy with a past date must not.
4. No authority is not an error. It routes the finished train to the hold
   path in `../verification/lander-duties.md` § Landing authority: train kept
   intact, decision brief filed, one notification, wait.

## 2. Fields (every one is filled by the owner, none has a default)

```yaml
status: INACTIVE                 # ACTIVE | INACTIVE
granted_by: <owner name or role> # the person who can be asked "did you mean this?"
granted_to: lander               # the role, never a model or vendor name
valid_from: <YYYY-MM-DD>
valid_until: <YYYY-MM-DD>        # short; renew deliberately. Expired = INACTIVE
signed: <owner initials + date>  # a policy nobody signed is a draft

# What the authority covers. Everything not listed is NOT covered.
covers:
  - kind: P1 fix                 # see §3 for what P1 must mean locally
    requires:                    # ALL of these, or the train is held
      - full verify green on the ASSEMBLED tree, judged by exit code
      - choices audit done for every boarded lane; zero unsound entries
      - boarding SHAs re-confirmed after the last fetch
      - the blocked program is an owner-approved item currently In flight
      - the fix lane was filed against the blocker BEFORE the train was built
    then:
      - push main
      - board sweep
      - ONE notification per transition (board-protocol § Notifications)

# What STOPS even with authority. The first four are the package floor
# and may not be removed; the owner may only add.
holds:
  - an unresolved unsound entry in the choices ledger
  - a new migration / schema head, or any change to the migration chain
  - a new decision of record (ADR) or a change to an existing one
  - a calibration or baseline change (ratchet baselines, eval thresholds,
    scoring weights, allowlists)
  - anything a lane STOPped on first contact (unassigned number, semantics
    change, governance inconsistency)
  # local additions, e.g.:
  # - a change under <path the owner considers sensitive>
  # - a dependency bump above <policy>

# Where the ONE notification per transition goes, and how it is keyed.
notify:
  channel: <issue comment | push notification | chat DM | mail>
  key: "<item id> <train HEAD sha> <transition>"   # never re-sent for the same key
  transitions: [held, decided, landed, reverted]

revocation: <how the owner revokes — delete the file, or set INACTIVE>
```

## 3. What "P1" must mean locally

The package does not define P1; the owner does, in `covers[].kind`. A usable
definition names all three of: (a) a defect, (b) an owner-approved program
it blocks (a board item In flight), (c) who may file the fix lane. The source
factory's definition, anonymized: *a verified fix for a defect that blocks an
owner-approved, in-flight programme; the fix lane was filed by the
orchestrator against that blocker; the train carries nothing else.* A train
that carries a P1 fix plus unrelated lanes is NOT a P1 train — split it or
hold it.

"Verified" is not negotiable by the policy: it is exactly the lander's list
in `../verification/lander-duties.md` steps 1–8. Authority changes what happens
at step 9, never what precedes it.

## 4. Two worked readings of the same train

A train is finished: full verify green on the assembled tree, choices audit
done (no unsound), boarding SHAs re-confirmed. It carries one lane: a fix
for a warmer that failed to converge on a large case, which blocks an
owner-approved evaluation rerun. No migration, no ADR, no baseline change.

| | Policy absent or INACTIVE | Policy ACTIVE, `covers: P1 fix` |
|---|---|---|
| Step 9 (push) | **Held.** Train worktree kept; decision brief filed from `../planning/decision-brief-template.md`; item → Decision needed; ONE `held` notification | Push `HEAD:main`; item → Done; ONE `landed` notification |
| Owner's role | Reads the brief, rules A/B, the ruling is recorded on the item | Reads the notification after the fact; may revoke the policy |
| If the audit had ONE unsound entry | Held (unsound stops before assembly anyway) | **Held** — `holds[0]` fires regardless of authority |
| If the lane had added a migration | Held | **Held** — `holds[1]` |
| If the owner answers within minutes | Landed after the ruling; ONE `decided` + ONE `landed` notification | Lands at step 9 without waiting; ONE `landed` notification — the policy was not needed for this train |

The source factory ran the left column once (a train held about two hours
for an A/B ruling — the example in `../planning/decision-brief-template.md`)
and granted the right column immediately afterwards. At the time this
example was written, no autonomous P1 landing under that authority had
been observed by the author of this file; the right column is the owner's
stated policy, not a measured routine.

## 5. What this file must never become

- A template that ships ACTIVE. The example is INACTIVE and stays so.
- A place for model names, vendor names, ports, project IDs or paths other
  than the active path. Those belong in the operator's dated model policy
  (`../harness/model-policy.md`, introduced by PR7) and the repo anchor.
- A second source of truth for the protocol. If a rule about briefs,
  transitions or notifications is needed, it goes to
  `../planning/board-protocol.md`, and this file links to it.
- A grant by installation. If a future installer step offers to activate
  this file, that step is a bug: the owner activates, in person.
