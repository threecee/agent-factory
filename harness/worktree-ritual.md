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
  boarding SHA is confirmed an ancestor of main.
