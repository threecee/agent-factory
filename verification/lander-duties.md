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
3. Assembly cross-checks: one migration head; number registry consistent
   (regenerated indexes from multiple lanes merge-conflict here — resolve by
   regenerating once on the assembled tree); counter-like edits from parallel
   lanes merged "clean" can still be wrong — set base+N at assembly. Never
   predict a conflict; compute it (`git merge-tree --write-tree A B`).
4. The choices ledger for the train is committed WITH the train.
5. Build every product the gates or the suite READ, on the assembled tree,
   on every run — whether or not a file under that product's source changed
   (verify-portfolio.md, "Build inputs exist before verify"). Stamp the build
   with its input identity so a stale build is detectable, not assumed.
6. Cheap gates by direct exit code on the assembled tree, in the order the
   train plan lists them. Generated-artifact drift checks (docs site, index
   files, mirrored CSS) belong here: two lanes regenerating the same artifact
   separately is the most common first-round red, and it is cheaper to find
   in a minute than after the suite.
7. Import-root probe: prove the interpreter/bundler under test resolves the
   package from the ASSEMBLED tree, not the primary checkout (train-plan §2,
   row "import root"). Refuse any path outside the tree.
8. Resource check immediately before the heavy step (train-plan §3), then
   FULL verify green on the assembled tree. If a mid-verify edit becomes
   necessary, STOP the verify first; never mutate a tree under a running
   verify (each such mutation costs a full re-run).
9. Re-confirm currency: fetch; if origin/main moved, READ what landed before
   rebasing — a non-ff rejection during an incident usually means a parallel
   session fixed the same thing (stand down if their fix is complete).
   Re-resolve every boarding branch head in the seconds before the push and
   compare with what was merged; abort on any mismatch.
10. Push HEAD:main GATED ON the verify verdict — mechanically
    (`make verify && git push …`), never as two statements in one
    unconditional block. (The smoke test shipped a red train exactly that way
    once.) Where the project's owner has chosen a landing authorization
    (user-level/landing-policy.example.md, introduced by PR11), it governs
    WHETHER the lander may push unattended; it never changes this gate.
11. Flip NUMBERS `claimed → landed`. Board sweep (§5). Fast-forward the
    primary checkout. Reap lane worktrees and branches only after each
    boarding SHA is confirmed an ancestor of main
    (`git merge-base --is-ancestor <sha> origin/main`).

## 2. Batch rule — independent lanes share a train

1. Assemble every READY, MUTUALLY INDEPENDENT lane in the same train, so one
   combined verification and one choices protocol prove the batch. Four
   trains for four ready lanes repeat the build and the full suite four times
   and never test the combination until the last one lands.
2. Independent means: no lane depends on another's branch; no two lanes claim
   the same scarce number (migration, ADR); no two lanes edit the same
   contract region — computed with `git merge-tree --write-tree`, not
   predicted. A textual conflict is not a reason to split the train; it is
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
   survive the resumed attempt. Judge completion from the exit file's
   `EXIT=<code>` line plus its `BASE=`/`HEAD=` lines — never from a pipe, a
   wrapper's status, or a log tail. Bank receipts that must outlive the
   session (harness/artifact-bank.md, introduced by PR5).
6. **A red step after which the fix is committed on the train tree** resumes
   the same way: commit, new run id, continue. Three rounds are normal for a
   ten-lane train; count them in the protocol.

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
build must not race the suite. The check is a snapshot, not a lock: it
detects what is running at probe time and nothing that starts afterwards.
The lander closes that window procedurally — no dispatch and no standup
while a train is between its resource check and its verdict — and never
claims race-free coordination it has not implemented and tested.

## 5. Board sweep and the derived-view check

1. Boarded items → Done (closing the issue auto-moves it), then archive.
   Enumerate the FULL board with an explicit limit above the item count
   (planning/board-protocol.md, "Authority, pagination and derived views").
2. Deferred findings from the train (a reverted lane, a follow-up the suite
   exposed) are filed as board items in the same sweep, with the train's SHA
   in the body.
3. **Derived-view check — only if the project has one.** If the project
   keeps any progress page besides the board (a dashboard, a README status
   table, a wiki page), compare, for every boarded issue: issue state on
   GitHub, board status, and what the page shows (status and, if it shows
   one, the landing SHA). Record every difference in the train protocol and
   correct the PAGE. Never edit the board to match a page. If there is no
   such page, the protocol says "derived view: none" and the step is done.
   The source factory recorded this as a lander candidate duty after an
   owner re-ordered already-landed work from a stale page; it was not an
   automated routine there. Treat it as a recommended manual check.
4. Fast-forward the primary checkout; reap worktrees only after the ancestor
   check in §1 step 11.

## 6. What this file does not claim

- No assembler script ships with the factory. The order above was executed
  by a repository-owned script in one source factory across roughly ten
  trains; the transferable part is the order, the criteria and the receipts.
  Script it in your project AFTER you have landed at least one train by
  hand from train-plan.md, so the script encodes commands you have watched
  succeed and fail.
- Serialized verification (one full verify at a time) is a rule of THIS
  file's owner, the lander; it is not enforced by any lock the factory
  provides.
