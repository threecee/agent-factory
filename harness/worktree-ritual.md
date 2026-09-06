# Worktree ritual

```sh
git -C <primary> fetch -q origin
git -C <primary> worktree add -q -b lane/<name> <wt-root>/<name> <pinned-sha>
ln -sfn <primary>/.venv <wt>/.venv         # and .env; node_modules for frontend lanes
```
- Pin a SHA, never a branch (pull before pointing agents at a checkout).
- One lane, one writer; never stash/checkout/reset while a delegated agent
  writes there.
- pnpm/npm installs in a worktree mutate the shared store — if a real install
  is unavoidable (bundler vs symlink), re-install in the primary afterwards.
- Teardown: remove worktree + branch only after the train has landed and the
  boarding SHA is confirmed an ancestor of main — and only after the
  teardown checks below.

- **The `git add -A` trap:** the wrapper's commit must never swallow the
  symlinked env dirs (.venv/.env/node_modules). Keep them in .gitignore in the
  TARGET repo before the first lane, or the committed symlink becomes a
  self-loop after merge (breaks every venv-relative command with exit 127).
- **Ritual check** (`guards.md` §6, M-4): after `git worktree add` and before
  any lane is dispatched into the tree, a deterministic offline check must
  pass — shared env dirs are symlinks to the primary, the dependency dir is
  linked only when the lockfiles are byte-identical, the links are in
  `.git/info/exclude`, HEAD was cut from the current remote default branch.
  Findings name the exact `ln -s` command; a clean tree yields the
  import-root invocation form (the probe table below). The check never
  creates a link (`--fix` is explicit); installing dependencies inside a
  linked worktree is refused.
- **Destructive forms guarded by identity** (`guards.md` §6, M-16 rows
  `stash-live`, `restore-dirty`, `worktree-remove`, `second-writer`):
  stash/checkout/restore/reset/clean while a writer whose directory flag
  resolves to this tree is alive; restore over uncommitted changes;
  `worktree remove` / `branch -D` while the branch holds unpushed commits, a
  dirty tree, ritual symlinks, large ignored files or a parked result — a
  branch already merged into the remote default branch passes first, so
  close-out is never blocked.

## The worktree is a launcher parameter

The launcher (`harness/launch_lane.sh`, contract in `harness/run-lifecycle.md`
§3) takes the worktree as `LANE_WORKTREE`, makes it the CLI's cwd, and
substitutes `{worktree}` into the CLI's own directory flag. Its start receipt
records `worktree`, `head_at_start` and, with `LANE_PIN_SHA` set, refuses to
start on a HEAD that does not match the pin. The "one writer" rule above is
mechanical, not only a norm: the runner holds a per-worktree writer lock while
the CLI runs, and the wrapper commits under the same lock —

```sh
harness/launch_lane.sh with-writer-lock -- git -C "$WT" commit -m "..."
```

— so a staggered start cannot begin beside a commit (run-lifecycle §4). Before
any tree-wide git operation, check for a live lane by executable identity
(`launch_lane.sh running <cli> <token>`), never by a text match on the command
line (run-lifecycle §6).

## Prove which code the test imported

A shared environment is the trap: the symlinked `.venv` (or `node_modules`, or
a global module cache) resolves the package to the **primary** checkout, so a
naked test command in a worktree can silently test the primary tree and report
green — or red — against the wrong revision. The source factory's first red
train of a wave was exactly this. Two rules, one per side:

1. **Set the import root from the worktree, for every invocation.** Python:
   `PYTHONPATH=<wt>/src <primary>/.venv/bin/python …`, including inside tests
   that spawn a subprocess (pin it from the test file's own location,
   `Path(__file__).resolve().parents[N] / "src"`, never from the environment
   the test happened to inherit). Other stacks have their own equivalent —
   the requirement is the same: the resolution root is the worktree, set
   explicitly, not the shared cache's default.
2. **Let the process print where the package was loaded from, and refuse
   anything outside the tree.** Before a lane's proof run, and immediately
   before the assembled train's full verify (`verification/verify-portfolio.md`),
   run the probe and compare the printed origin with the worktree path:

   | Stack | Probe | Must resolve inside |
   |---|---|---|
   | Python | `python -c 'import <pkg>; print(<pkg>.__file__)'` | `<wt>/src/<pkg>/` |
   | Node | `node -p "require.resolve('<pkg>')"` (or `import.meta.resolve`) | `<wt>/…` — beware workspace symlinks that point at the primary |
   | Go | `go list -f '{{.Dir}}' <module>/...` | `<wt>/…`; check `replace` directives |
   | Rust | `cargo metadata --format-version 1 \| jq -r .workspace_root` | `<wt>` |
   | JVM | print the classpath entry that served a known class (`Class.getProtectionDomain().getCodeSource()`) | `<wt>/…/build/` |
   | Any | the documented entry point with a `--version`/`--where` that prints its own origin | `<wt>` |

   A green verify that imported the primary tree verified the wrong code; the
   probe output belongs in the lane's report (`proof:`) and in the train's
   receipt.

3. **Test the documented invocation, not the import.** `python scripts/x.py`
   has a different `sys.path` from `pytest`; a container `CMD` has a different
   root from the dev shell; a CLI entry point that works from the repo root
   may not work from the documented cwd. Run the entry the runbook documents,
   from the directory it documents, with the import root above.

## Teardown checks (destructive in ways `git log` does not show)

Retiring a worktree destroys three things `git log` never lists. Check all
three first:

1. **Gitignored valuables.** `git -C <wt> status --ignored --porcelain`
   lists what lives only in this tree (generated corpora, score files,
   instance databases, run output). Anything durable per
   `harness/artifact-bank.md` §1 is banked BEFORE removal (run receipts per
   `harness/run-lifecycle.md` §9); a receipt committed in-tree with its data
   left in the worktree is the pattern that has lost paid data. A lane that
   banks as it produces has nothing left to rescue here.
2. **Uncommitted work.** Read `git status --porcelain`, not only `git log`:
   an idle lane with uncommitted work is usually mid-verify, not abandoned.
   If the branch is being purged anyway, preserve the work as a patch file
   first.
3. **Symlinks into the primary.** List them
   (`find <wt> -maxdepth 3 -type l -not -path '*/.git/*'`), unlink, then
   remove, then confirm the primary's `.venv`/`.env`/`node_modules` still
   exist. Never `worktree remove --force` a tree holding live symlinks.

Working copies a lane stood up from this tree (served instances, recorder
output) live outside the worktree and are reaped with it — by port and by
path, never by process-name grep (`harness/artifact-bank.md` §8 owns that
rule; `harness/run-lifecycle.md` §2 owns the run id that names them).
