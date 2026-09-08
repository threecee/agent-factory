# Lander duties — the landing train

The orchestrator (lander) assembles and lands; lanes never push main. This
file owns the ORDER of a train and the batch, resume and sweep rules. The
project's concrete commands and its resource contract live in
`../harness/train-plan.md` — fill that in once, then land from it.

## 1. Order of operations

1. Create the train worktree from the CURRENT origin/main SHA. Run the
   resource contract (train-plan §3) first and refuse to start on any stop it
   reports; it runs again at step 8.
2. `--no-ff` merge each lane's PINNED handback SHA (never branch names).
   Resolve every boarder to a full commit SHA and record it in the train's
   choices protocol before the first merge.
   - Archive every boarder's delta; commit the merged specs and archived
     changes with the train. Run this in stable order after the last merge and
     before step 3 (`../planning/capability-specs.md §4`).
3. Assembly cross-checks: one migration head; number registry consistent
   (regenerated indexes from multiple lanes merge-conflict here — resolve by
   regenerating once on the assembled tree); counter-like edits from parallel
   lanes merged "clean" can still be wrong — set base+N at assembly. Never
   predict a conflict; compute it (`git merge-tree --write-tree A B`,
   git ≥ 2.38 — the one version requirement this file has). Re-derive the
   change kind from `git diff --name-only <BASE>..HEAD` with the repo's
   classifier and write `kind: <declared>→<derived>` into the ledger
   (`../planning/execution-contract.md` §9 owns the rose/fell
   consequences; a kind that rose selects its legs at step 6).
4. The choices ledger for the train is committed WITH the train.
5. Build every product the gates or the suite READ, on the assembled tree,
   on every run — whether or not a file under that product's source changed
   (verify-portfolio.md, "Build inputs exist before verify"). Stamp the build
   with its input identity so a stale build is detectable, not assumed.
6. Cheap gates by direct exit code on the assembled tree, in the order the
   train plan lists them — including every legs-table row whose glob
   matches `git diff --name-only <BASE>..HEAD` on the assembled tree
   (verify-portfolio.md, "Legs that bring lane-green closer to
   train-green", leg (c)); the kind re-derived at step 3 selects the same
   rows and adds none. Generated-artifact drift checks (docs site, index
   files, mirrored CSS) belong here: two lanes regenerating the same artifact
   separately is the most common first-round red, and it is cheaper to find
   in a minute than after the suite.
7. Import-root probe: prove the interpreter/bundler under test resolves the
   package from the ASSEMBLED tree, not the primary checkout (train-plan §2,
   row "import root"). Refuse any path outside the tree.
8. Flip every boarded NUMBERS claim `claimed → landed` on the train and
   commit the flip before the final run. Then resource-check immediately
   before the heavy step (train-plan §3), and run FULL verify on that exact
   assembled HEAD. A verify leg that skipped for an
   absent bed is not green on a train that touches its journey — read that
   leg's own PASSED line (evaluation-readiness §3 rule 13 owns what a skip
   may satisfy). If a mid-verify edit becomes necessary, STOP the verify
   first; never mutate a tree under a running verify (each such mutation
   costs a full re-run).
9. Re-confirm currency: fetch; if origin/main moved, READ what landed before
   rebasing — a non-ff rejection during an incident usually means a parallel
   session fixed the same thing (stand down if their fix is complete).
   Re-resolve every boarding branch head in the seconds before the push and
   compare with what was merged; abort on any mismatch.
10. Land in the project's landing mode (`landing-modes.md`; declared in
    train-plan §5, default `pr`) — GATED mechanically on the verify verdict
    (the receipt read as train-plan §4.1 says, never two statements in one
    unconditional block; the smoke test shipped a red train exactly that way
    once) AND on landing authority (§7): a live ruling from the owner for
    THIS train, recorded on the item, or an active standing policy (a
    user-level file; the factory ships none active) that covers it with no
    hold category firing. Neither → hold (§7 rule 2); do not merge, do not
    push. Both modes first push the integration branch and post the
    `local-verify` status on the receipt's `HEAD=` (landing-modes §2). Then,
    `pr`: open or update the train pull request with the ledger as body,
    write the PR URL on the boarded items, read and adjudicate the check
    rollup, and on authority `gh pr merge <n> --merge --match-head-commit
    <HEAD=>` — never `--squash`, `--rebase`, `--auto` or `--admin`
    (landing-modes §4.5); `direct-push` (the override; `override reason:` in
    the ledger): `<verdict check> && git push origin HEAD:main`. The harness
    landing guard and the git pre-push hook are the mechanical form of this
    step (`protections.md` §1). Authority governs WHETHER the lander may
    land unattended; it never changes the verify gate.
11. Registration and close-out (§8, one list for both modes): confirm
    origin/main CONTAINS the receipt HEAD — the ancestor check reads
    contains, never equals, because in pr mode main's tip is the merge
    commit and `HEAD=` its second parent; in pr mode confirm the pull
    request reads merged; delete the remote train branch (`git push origin
    --delete train/<name>`, both modes). Confirm the verified NUMBERS state
    from step 8 reached origin/main.
    Board sweep (§5), then ONE `landed` notification per boarded item
    (planning/board-protocol.md § Notifications — keyed on the train HEAD,
    never re-sent). Fast-forward the primary checkout. Reap lane worktrees
    and branches only after each boarding SHA is confirmed an ancestor of
    main (`git merge-base --is-ancestor <sha> origin/main`).

## 2. Batch rule — independent lanes share a train

1. Assemble every READY, MUTUALLY INDEPENDENT lane in the same train, so one
   combined verification and one choices protocol prove the batch. Four
   trains for four ready lanes repeat the build and the full suite four times
   and never test the combination until the last one lands. In pr mode this
   is one pull request per train, never one per lane (`landing-modes.md` §4).
2. Independent means: no lane depends on another's branch; no two lanes claim
   the same scarce number (migration, ADR); no two lanes edit the same
   contract region — computed with `git merge-tree --write-tree` (§1 step
   3), not predicted. A textual conflict is not a reason to split the train; it is
   resolved on the train (§3). Semantic incompatibility found by the suite
   is a reason to REVERT the offending merge commit and land the rest.
3. Readiness alone is never a reason to give a non-blocking lane its own
   train. A single-lane train is allowed only for a documented blocker.
4. **Blocker exception.** A lane may take its own train when it fixes a
   defect at the project's highest priority level that blocks work the owner
   has already approved. The protocol records the priority level, the blocked
   work, and who declared it. The level's name and meaning are the project's
   (train-plan §5); the factory does not define "P1".
5. The install smoke test (INSTALL step 7) runs one single-lane train on
   purpose. That is the install ritual, not the batch policy.

**Worked example.** Monday, four lanes are ready with pinned handback SHAs:
`api-validation` (a request-validation bug fix), `chip-label` (a frontend
label component), `deps-monthly` (the month's dependency group), `docs-typo`
(a one-line docs fix). `git merge-tree --write-tree` between each pair is
clean; NUMBERS shows no shared claims; none branches from another. They
board train `t-42` together: one worktree, four `--no-ff` merges, one
cross-check pass, one build, one cheap-gate pass, one full verify, one
protocol with four lane sections. The same morning, lane `warmer-converge`
fixes a defect the project has ranked at its top level because a
PO-approved evaluation programme cannot start until it lands. It takes train
`t-43` alone; its protocol reads: "single-lane train — priority P1 (project
definition: blocks approved work), blocks: evaluation programme #NNN,
declared by: orchestrator, ruling: owner". Landing `t-43` first and rebasing
`t-42` onto the new main is the normal order; `t-42` re-runs from step 3.
Both land in the project's declared mode — `pr` unless train-plan §5 says
otherwise — and each ledger's `## Landing` section records it
(`landing-modes.md` §1).

## 3. Conflict and resume — the continue contract

A conflict stops the train at the first conflicting merge and leaves the
tree in place. Resume on the SAME tree; never rebuild it from scratch to
avoid the conflict, and never re-merge the boarders that already landed on
it. The criteria:

1. **Precondition — a clean, committed tree.** `git status --porcelain` is
   empty. An uncommitted conflict resolution is REFUSED, because the green
   receipt must name the exact tested HEAD.
2. **No new boarders on continue.** A resumed run accepts no lane arguments.
   A boarder that arrived after the conflict is merged `--no-ff` BY HAND on
   the train tree, committed, and its SHA added to the protocol BEFORE the
   resumed run; otherwise it waits for the next train.
3. **Skip only what already happened.** The resumed run skips fetch, worktree
   creation and merging; it records the tree's base (`git merge-base
   origin/main HEAD`) and HEAD as full SHAs and starts at the cross-checks
   (§1 step 3), then build, cheap gates, import-root probe, resource check,
   full verify.
4. **Environment links are re-established idempotently.** A missing link to
   the shared environment (venv, env file, node_modules) is created; an
   existing regular file or a link pointing elsewhere is refused, never
   overwritten, and its contents are never printed into the run log.
5. **A new run id, and the old receipt stays.** Every attempt is
   `<train>-<attempt>` and owns `<run-id>.log` and `<run-id>.exit`. Existing
   receipts are never overwritten; the failed attempt's log and exit file
   survive the resumed attempt. The verdict is read as train-plan §4.1 says
   (that section owns the rule); bank receipts that must outlive the
   session (`harness/run-lifecycle.md` §9; the bank's own lifecycle is
   `harness/artifact-bank.md`).
6. **A red step after which the fix is committed on the train tree** resumes
   the same way: commit, new run id, continue. Expect several attempts on a
   large train — the source factory's protocols record three verify rounds
   on a fourteen-lane train and four attempts on a seven-boarder train —
   and count them in the protocol.

**Worked example.** Train `t-42`, run `t-42-1`: the third merge conflicts in
one spec table (two lanes updated the same row). The lander resolves it by
taking the row that is true after the newer decision, commits on the train
tree, merges the fourth boarder by hand `--no-ff` (it was not reached), and
runs `t-42-2 --continue`. `t-42-1.exit` reads `EXIT=1`; `t-42-2.exit` reads
`EXIT=0 BASE=<main sha> HEAD=<train sha>`. Both receipts are kept; the
protocol cites both run ids.

## 4. Resource check before the heavy run

The full suite, a served instance, an evaluation wave and a delegated agent's
test run compete for the same machine, and a verdict from a contended machine
is adjudicated, not trusted (verify-portfolio.md). The lander therefore runs
the project's resource contract (train-plan §3) at train creation AND
immediately before full verify — a lane or standup that started during the
build must not race the suite. The check is a snapshot, not a lock
(train-plan §3.6 owns what it does and does not claim). The lander's rule,
owned here: no dispatch and no standup while a train is between its
resource check and its verdict, and no claim of race-free coordination the
project has not implemented and tested.

## 5. Board sweep and the derived-view check

1. Boarded items → Done (closing the issue auto-moves it), then archive.
   Enumerate the FULL board with an explicit limit above the item count
   (planning/board-protocol.md, "Authority, pagination and derived views").
2. Deferred findings from the train (a reverted lane, a follow-up the suite
   exposed) are filed as board items in the same sweep, with the train's SHA
   in the body.
3. **Derived-view check — only if the project has one.** Run the check
   that planning/board-protocol.md ("Authority, pagination and derived
   views", item 3) owns, and record its differences in the train protocol.
   If the project keeps no page besides the board, the protocol says
   "derived view: none" and the step is done. A difference is fixed by
   regenerating the view — never by hand-editing it to match the board and
   never by editing the board to match it; if the view cannot be
   regenerated before the session ends, the landing summary says so. It is
   a candidate duty (medium confidence, see its home), not a proven routine.
4. Fast-forward the primary checkout; reap worktrees only after the ancestor
   check in §1 step 11.

## 6. What this file does not claim

- No assembler script ships with the factory. The order above was executed
  by a repository-owned script in one source factory on a handful of
  multi-lane trains after a first, partly manual fourteen-lane attempt
  (train-plan §8 has the honest account); the transferable part is the
  order, the criteria and the receipts. Script it in your project AFTER you
  have landed at least one train by hand from train-plan.md, so the script
  encodes commands you have watched succeed and fail.
- Serialized verification (one full verify at a time) is a rule of THIS
  file's owner, the lander (§4); it is not enforced by any lock the factory
  provides (train-plan §3.6).
- No merge automation ships. The merge (pr mode) and the push (direct-push
  mode) are attended by the lander after the ruling is read; no auto-merge,
  no merge queue, no bot approval (`landing-modes.md` §4.5, §9).

## 7. Landing authority

Steps 1–9 produce a verified train. Step 10 asks a different question: who
said this train may land NOW? The answer lives in one place — the operator's
landing policy, `../user-level/landing-policy.example.md`, which is
INACTIVE as shipped. Read it as the owner's grant, never as a template.

1. Run the policy check from the landing policy §1. `NO AUTHORITY` is the
   default and is not an error.
2. **No authority → hold.** Keep the train worktree and its verify log
   intact; do NOT reap. File a decision brief on the blocked item from
   `../planning/decision-brief-template.md` (options with consequences, one
   recommendation, what continues meanwhile). Status → Decision needed.
   Write the key `<item> <train sha> held` on the item, then send ONE
   notification (`../planning/board-protocol.md` § Notifications; with no
   policy file the brief comment carrying the key IS the notification).
   Wait. Do nothing irreversible. The irreversible step held is the MERGE in
   pr mode — the pull request stays open as the hold artifact, the brief on
   the item and linked from the pull request; an owner's approval on the
   pull request is one accepted record of the ruling, copied to the item —
   and the PUSH in direct-push mode (`landing-modes.md` §4.4, §5).
3. **On the ruling:** the ruling is on the item (copy it there verbatim if it
   came by chat). Re-run step 9 — origin/main may have moved during the hold;
   if it did, re-confirm boarding SHAs and re-verify the re-assembled tree
   (§3, a new attempt) — then step 10. A hold of two hours is normal; a hold
   that outlives the train's base is a re-assembly, not a force-push: the
   strict branch policy refuses the stale merge and the receipt's `BASE=` is
   no longer origin/main (`landing-modes.md` §3).
4. **Authority → land**, only if ALL hold: the policy covers this train's
   kind (e.g. a single P1 fix lane against an In-flight, owner-approved
   item — the owner's definition, not the package's; §2 rule 4); every
   `requires:` line of the policy is met by steps 1–9; NO `holds:` category
   fires. The non-removable floor of that list is enumerated ONCE, in the
   landing policy §2 `holds:` — read it there; this file does not repeat it.
   Any floor entry firing → rule 2, even under authority.
5. **After an autonomous landing:** the train's choices ledger names the
   policy (file, `valid_until`, `signed`) and the item it landed for; the
   `landed` notification is the owner's first contact with it. The owner
   may revoke the policy; the landing stands (it was verified) and the next
   train holds.

Worked reading: a train carrying one lane (a warmer-convergence fix that
blocked an owner-approved evaluation rerun), verify green on the assembled
tree, five sound choices, no migration. Policy absent → held with an A/B
brief; the owner ruled A after about two hours; the train landed (source
factory, one occurrence). Policy ACTIVE with `covers: P1 fix` → the same
train lands at step 10 and the owner reads `<item> <sha> landed`. Same train
with one unsound entry, or with a migration → held in BOTH cases. The
autonomous column has not been exercised in the source factory at the time
of writing; it is the owner's stated policy, not a measured routine. In pr
mode the held train is an open pull request with the ledger as its body; in
direct-push mode it is a pushed integration branch with the status posted
and main untouched (`landing-modes.md` §4.4, §5).

## 8. Close-out — identical in both modes

After the landing registered (step 11), the following are the lander's open
duties, whatever the mode; every check reads CONTAINS, never equals:

Number close-out began before landing: step 8 flipped every boarded claim
`claimed → landed` on the train before the final run. The flip is part of the
verified train `HEAD=`; close-out only confirms that state reached origin/main.
Provenance: source factory Varde w137, 2026-09-08.

1. origin/main contains the receipt `HEAD=`
   (`git merge-base --is-ancestor <HEAD=> origin/main`).
2. In pr mode, the pull request reads merged (`gh pr view <n> --json state`).
3. The remote train branch is gone: `git push origin --delete train/<name>`.
4. origin/main contains the already-verified NUMBERS flips.
5. Board sweep (§5) and ONE `landed` notification per boarded item, keyed
   on the train HEAD — the merge SHA may be named in the comment, never in
   the key (`../planning/board-protocol.md` § Notifications).
6. The primary checkout fast-forwarded (`git -C <primary> pull --ff-only
   origin main`).
7. Merged worktrees reaped — after the ancestor check and the
   worktree-ritual teardown checks (`../harness/worktree-ritual.md`).
8. Served instances torn down by port.
9. The build product fresh when the train touched its inputs.
10. Disk above the floor.

`verification/gates/check_landing_closeout.py --state <state file>` prints
the open ones as commands; a `Stop`-hook adapter may deliver this list and
performs none of it (`protections.md` §6). A hold and a landing in either
mode end with the same ten items.
