#!/usr/bin/env bash
# A planted tracked or untracked path selects its one matching legs-table row;
# an unmatched path selects no row.
set -u

HERE="$(cd "$(dirname "$0")" && pwd)"
RUNNER="$HERE/../select_diff_triggered_legs.sh"
command -v git >/dev/null 2>&1 || { echo "need git"; exit 2; }
[ -f "$RUNNER" ] || { echo "not ok - diff-triggered legs runner is missing"; exit 1; }

T="$(mktemp -d "${TMPDIR:-/tmp}/diff triggered legs.XXXXXX")"
trap 'rm -rf "$T"' EXIT
REPO="$T/repo"
TABLE="$T/legs table.md"
mkdir -p "$REPO"
git -C "$REPO" init -q -b main
git -C "$REPO" config user.email test@example.invalid
git -C "$REPO" config user.name test
git -C "$REPO" config commit.gpgsign false
printf 'seed\n' > "$REPO/README.md"
git -C "$REPO" add README.md
git -C "$REPO" commit -q -m seed
PIN="$(git -C "$REPO" rev-parse HEAD)"

DOCS_ROW='| `docs/**` | `check-docs` | documentation | `docs/patterns.md` |'
GATE_ROW='| `verification/gates/**` | `check-gates --hard` | criteria not weakened | `verification/guards.md` |'
UI_ROW='| `src/ui/**` | `check-copy`, `check-a11y` | interface contract | `docs/ui.md` |'
printf '%s\n' \
  '| touches (globs) | run (exact command from `<wt>`) | proves | reads first |' \
  '|---|---|---|---|' \
  "$DOCS_ROW" \
  "$GATE_ROW" \
  "$UI_ROW" > "$TABLE"

mkdir -p "$REPO/verification/gates" "$REPO/notes"
printf 'gate\n' > "$REPO/verification/gates/check.sh"
printf 'unmatched\n' > "$REPO/notes/local.txt"
out="$(cd "$REPO" && bash "$RUNNER" "$PIN" "$TABLE")" || {
  echo "not ok - runner rejected an untracked-path selection"
  exit 1
}
[ "$out" = "$GATE_ROW" ] || {
  echo "not ok - a matching untracked path did not select exactly its row"
  printf 'wanted: %s\ngot: %s\n' "$GATE_ROW" "$out"
  exit 1
}

rm -rf "$REPO/verification"
out="$(cd "$REPO" && bash "$RUNNER" "$PIN" "$TABLE")" || {
  echo "not ok - runner rejected an unmatched-path selection"
  exit 1
}
[ -z "$out" ] || {
  echo "not ok - an unmatched path selected a row"
  printf 'got: %s\n' "$out"
  exit 1
}

mkdir -p "$REPO/src/ui"
printf 'interface\n' > "$REPO/src/ui/app.js"
git -C "$REPO" add src/ui/app.js
git -C "$REPO" commit -q -m interface
out="$(cd "$REPO" && bash "$RUNNER" "$PIN" "$TABLE")" || {
  echo "not ok - runner rejected a tracked-path selection"
  exit 1
}
[ "$out" = "$UI_ROW" ] || {
  echo "not ok - a matching tracked path did not select exactly its row"
  printf 'wanted: %s\ngot: %s\n' "$UI_ROW" "$out"
  exit 1
}

echo "diff-triggered legs: tracked, untracked, and unmatched selection ok"
