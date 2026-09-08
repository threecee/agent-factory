#!/usr/bin/env bash
# Print each diff-triggered legs-table row selected by the lane change set.
set -u

usage() {
  echo "usage: $0 <pin> [legs-table-file]" >&2
  exit 2
}

[ "$#" -ge 1 ] && [ "$#" -le 2 ] || usage
PIN="$1"
ROOT="$(git rev-parse --show-toplevel 2>/dev/null)" || {
  echo "diff-triggered legs: not inside a git worktree" >&2
  exit 2
}
TABLE="${2:-$ROOT/verification/verify-portfolio.md}"
[ -r "$TABLE" ] || {
  echo "diff-triggered legs: cannot read table: $TABLE" >&2
  exit 2
}

T="$(mktemp -d "${TMPDIR:-/tmp}/diff-triggered-legs.XXXXXX")" || exit 2
cleanup() { rm -rf "$T"; }
trap cleanup EXIT HUP INT TERM

git -C "$ROOT" diff --name-only "$PIN"...HEAD > "$T/changed" || exit 2
git -C "$ROOT" ls-files --others --exclude-standard >> "$T/changed" || exit 2
LC_ALL=C sort -u "$T/changed" > "$T/paths"

awk '
  /^[[:space:]]*\|[[:space:]]*touches \(globs\)[[:space:]]*\|/ {
    in_table = 1
    next
  }
  in_table && /^[[:space:]]*\|[[:space:]]*[-:]+[[:space:]]*\|/ { next }
  in_table && /^[[:space:]]*\|/ { print; next }
  in_table { exit }
' "$TABLE" > "$T/rows"

while IFS= read -r row || [ -n "$row" ]; do
  printf '%s\n' "$row" | awk -F '|' '
    {
      cell = $2
      while (match(cell, /`[^`]+`/)) {
        print substr(cell, RSTART + 1, RLENGTH - 2)
        cell = substr(cell, RSTART + RLENGTH)
      }
    }
  ' > "$T/patterns"
  while IFS= read -r pattern || [ -n "$pattern" ]; do
    while IFS= read -r path || [ -n "$path" ]; do
      case "$path" in
        $pattern)
          printf '%s\n' "$row"
          pattern=
          break
          ;;
      esac
    done < "$T/paths"
    [ -z "$pattern" ] && break
  done < "$T/patterns"
done < "$T/rows"

exit 0
