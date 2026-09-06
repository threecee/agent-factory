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
   path and the path does not contain `example`; it has a line
   `status: ACTIVE` and no line `status: INACTIVE`; `valid_until` is a real
   `YYYY-MM-DD` date and today is not later than it (the policy is valid
   through that day, expired from the next); `granted_by` and `signed` are
   filled with something other than the `<placeholder>` of §2. Anything
   else — file missing, `INACTIVE`, expired, a placeholder date, unsigned,
   an `example` in the path — means **no authority**. This paragraph and
   the check below are the same list; if one changes, both change.
3. The check, run by the lander before any push (adapt the path):

   ```sh
   p=~/.claude/landing-policy.md
   today=$(date +%Y%m%d)
   until=$(sed -n 's/^valid_until: *\([0-9]\{4\}\)-\([0-9]\{2\}\)-\([0-9]\{2\}\).*/\1\2\3/p' "$p" 2>/dev/null | head -1)
   if test -f "$p" \
      && case "$p" in *example*) false;; *) true;; esac \
      && grep -Eq '^status: *ACTIVE([[:space:]]|$)' "$p" \
      && ! grep -Eq '^status: *INACTIVE' "$p" \
      && grep -Eq '^granted_by: *[^<[:space:]]' "$p" \
      && grep -Eq '^signed: *[^<[:space:]]' "$p" \
      && test -n "$until" && test "$until" -ge "$today"
   then echo AUTHORITY
   else echo "NO AUTHORITY -> hold + decision brief"
   fi
   ```

   POSIX sh/bash/zsh, locale-independent: the date is matched as digits
   and compared as an integer (`YYYYMMDD`), never as a string — string
   comparison of `<YYYY-MM-DD>` against a date is collation-dependent and
   fails OPEN under `LC_ALL=C`. A trailing comment on the `valid_until`
   line (the §2 template keeps one) is ignored by the match. A field
   whose first character is `<` is a placeholder and fails. Against this
   example file the check prints `NO AUTHORITY` (the status line says
   `INACTIVE`). That is the correct result for a fresh install.

   Falsify it once on the machine, on scratch copies of this file with
   the path adapted, under `LC_ALL=C` as well as the login locale; the
   expected outputs are the definition of §1.2, not a courtesy:

   | Scratch copy | Expected |
   |---|---|
   | this file unchanged | `NO AUTHORITY` |
   | all fields filled, `status: ACTIVE`, `valid_until` next year | `AUTHORITY` |
   | same, `valid_until` last year | `NO AUTHORITY` |
   | same, `valid_until` = today, with the template's trailing `# renew…` comment | `AUTHORITY` (valid through the day) |
   | same, `valid_until` = yesterday | `NO AUTHORITY` |
   | ONLY the two `status:` lines flipped to ACTIVE, every `<placeholder>` left | `NO AUTHORITY` |
   | all filled and ACTIVE, but `signed: <owner initials + date>` left | `NO AUTHORITY` |
   | all filled and ACTIVE, `granted_by:` empty | `NO AUTHORITY` |
   | all filled and ACTIVE, copy saved under a path containing `example` | `NO AUTHORITY` |

   A check that prints `AUTHORITY` for any row but the second and fourth
   is a bug in the check, and no train lands on it until it is fixed.
4. No authority is not an error. It routes the finished train to the hold
   path in `../verification/lander-duties.md` § Landing authority: train kept
   intact, decision brief filed, one notification, wait.

## 2. Fields (every one is filled by the owner, none has a default)

```yaml
status: INACTIVE                 # ACTIVE | INACTIVE
granted_by: <owner name or role> # the person who can be asked "did you mean this?"
granted_to: lander               # the role, never a model or vendor name
valid_from: <YYYY-MM-DD>
valid_until: <YYYY-MM-DD>        # short; renew deliberately. Valid through this day; expired = INACTIVE
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

# What STOPS even with authority. All five entries below are the package
# floor and may not be removed or narrowed; the owner may only add. This
# list is the ONE home of the floor — lander-duties and board-protocol
# point here, they do not repeat it.
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
  (a separate `harness/` document, if the package ships one) and the repo
  anchor.
- A second source of truth for the protocol. If a rule about briefs,
  transitions or notifications is needed, it goes to
  `../planning/board-protocol.md`, and this file links to it.
- A grant by installation. If a future installer step offers to activate
  this file, that step is a bug: the owner activates, in person.
