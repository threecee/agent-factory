#!/usr/bin/env bash
# Falsifies path-scoped selection of open improvement items.
set -u

HERE="$(cd "$(dirname "$0")" && pwd -P)"
LOOKUP="$HERE/../lookup_open_improvements.sh"
T="$(mktemp -d "${TMPDIR:-/tmp}/open improvement lookup test.XXXXXX")"
trap 'rm -rf "$T"' EXIT
REGISTRY="$T/continuous-improvement.md"

cat > "$REGISTRY" <<'EOF'
# Improvement fixture

<!-- open-improvements:start -->
| Status | Path glob | Improvement item |
|---|---|---|
| open | `harness/**` | `IMP-H` — read the harness guard evidence |
| closed | `harness/**` | `IMP-CLOSED` — retired harness item |
| open | `planning/**` | `IMP-P` — read the planning contract |
<!-- open-improvements:end -->
EOF

[ -x "$LOOKUP" ] || {
  echo "not ok - lookup is not executable: $LOOKUP"
  exit 1
}

harness_out="$("$LOOKUP" "$REGISTRY" harness/guards/)"; harness_rc=$?
[ "$harness_rc" -eq 0 ] || {
  echo "not ok - harness lookup exited $harness_rc"
  exit 1
}
[ "$harness_out" = '`IMP-H` — read the harness guard evidence' ] || {
  printf 'not ok - harness lookup selected the wrong items: %s\n' "$harness_out"
  exit 1
}

multiple_out="$("$LOOKUP" "$REGISTRY" harness/guards/ harness/tests/)"; multiple_rc=$?
[ "$multiple_rc" -eq 0 ] && [ "$multiple_out" = "$harness_out" ] || {
  printf 'not ok - an item matching two planned paths was not emitted once: rc=%s out=%s\n' "$multiple_rc" "$multiple_out"
  exit 1
}

planning_out="$("$LOOKUP" "$REGISTRY" planning/)"; planning_rc=$?
[ "$planning_rc" -eq 0 ] || {
  echo "not ok - planning lookup exited $planning_rc"
  exit 1
}
[ "$planning_out" = '`IMP-P` — read the planning contract' ] || {
  printf 'not ok - planning lookup selected the wrong items: %s\n' "$planning_out"
  exit 1
}

invalid_out="$("$LOOKUP" "$REGISTRY" 2>&1)"; invalid_rc=$?
[ "$invalid_rc" -eq 2 ] && printf '%s\n' "$invalid_out" | grep -q '^lookup_open_improvements:' || {
  printf 'not ok - missing planned paths were not refused: rc=%s out=%s\n' "$invalid_rc" "$invalid_out"
  exit 1
}

echo 'lookup-open-improvements: open harness item selected for harness/guards/, deduplicated, and excluded from planning/'
