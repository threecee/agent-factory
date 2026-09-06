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
  boarding SHA is confirmed an ancestor of main. Retiring a worktree is
  destructive in two ways `git log` does not show — check both first:
  1. **Gitignored valuables.** `git -C <wt> status --ignored --porcelain`
     lists what lives only in this tree (generated corpora, score files,
     instance databases, run output). Anything durable per
     `harness/artifact-bank.md` §1 is banked BEFORE removal; receipts
     in-tree with data in the worktree is the pattern that has lost paid
     data. `git status --porcelain` (not `git log`) shows uncommitted work —
     preserve it as a patch file if the branch is being purged.
  2. **Symlinks into the primary.** List them
     (`find <wt> -maxdepth 3 -type l -not -path '*/.git/*'`), unlink, then
     remove, then confirm the primary's `.venv`/`.env`/`node_modules` still
     exist. Never `worktree remove --force` a tree holding live symlinks.
- Working copies a lane stood up from this tree (served instances, recorder
  output) live outside the worktree and are reaped with it — by port and by
  path, never by process-name grep (`harness/artifact-bank.md` §8;
  `harness/run-lifecycle.md`, introduced by PR2, owns the run id that names
  them).

- **The `git add -A` trap:** the wrapper's commit must never swallow the
  symlinked env dirs (.venv/.env/node_modules). Keep them in .gitignore in the
  TARGET repo before the first lane, or the committed symlink becomes a
  self-loop after merge (breaks every venv-relative command with exit 127).
