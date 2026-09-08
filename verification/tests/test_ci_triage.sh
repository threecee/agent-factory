#!/usr/bin/env bash
# Exercises every CI class, failed-set diff, idle refusal and fix-lane delta shape.
set -u

HERE="$(cd "$(dirname "$0")" && pwd)"
TRIAGE="$HERE/../gates/ci_triage.py"
T="$(mktemp -d "${TMPDIR:-/tmp}/ci triage test.XXXXXX")"
trap 'rm -rf "$T"' EXIT
mkdir -p "$T/bin" "$T/deltas"
CALLS="$T/gh.calls"

printf '%s\n' '#!/bin/sh' 'exit 0' > "$T/bin/idle-ok"
printf '%s\n' '#!/bin/sh' 'exit 9' > "$T/bin/idle-red"
printf '%s\n' '#!/bin/sh' 'printf "%s\n" "$*" >> "$REPRO_CALLS"' > "$T/bin/reproduce"
chmod +x "$T/bin/idle-ok" "$T/bin/idle-red" "$T/bin/reproduce"
printf 'test_flaky\n' > "$T/flakes.txt"

printf '%s\n' '#!/bin/sh' 'printf "%s\n" "$*" >> "$GH_CALLS"' \
  'case "$*" in' \
  '*"run list"*) printf '\''%s\n'\'' '\''[{"databaseId":101,"conclusion":"failure","createdAt":"2026-09-08T12:00:00Z","headSha":"new","url":"https://example.invalid/101","name":"verify"},{"databaseId":100,"conclusion":"failure","createdAt":"2026-09-08T11:00:00Z","headSha":"old","url":"https://example.invalid/100","name":"verify"}]'\'' ;;' \
  '*"run view 101 --json jobs"*) printf '\''%s\n'\'' '\''{"jobs":[{"databaseId":1,"name":"cancelled-job","conclusion":"cancelled","startedAt":"2026-09-08T12:00:00Z","completedAt":"2026-09-08T12:01:00Z","steps":[{"name":"run"}]},{"databaseId":2,"name":"null-job","conclusion":"failure","startedAt":null,"completedAt":null,"steps":[]},{"databaseId":3,"name":"flake-job","conclusion":"failure","startedAt":"2026-09-08T12:00:00Z","completedAt":"2026-09-08T12:01:00Z","steps":[{"name":"test"}]},{"databaseId":4,"name":"real-job","conclusion":"failure","startedAt":"2026-09-08T12:00:00Z","completedAt":"2026-09-08T12:01:00Z","steps":[{"name":"test"}]},{"databaseId":5,"name":"environment-job","conclusion":"failure","startedAt":"2026-09-08T12:00:00Z","completedAt":"2026-09-08T12:01:00Z","steps":[{"name":"test"}]}]}'\'' ;;' \
  '*"run view 100 --json jobs"*) printf '\''%s\n'\'' '\''{"jobs":[{"databaseId":4,"name":"real-job","conclusion":"failure","steps":[{"name":"test"}]},{"databaseId":6,"name":"resolved-job","conclusion":"failure","steps":[{"name":"test"}]}]}'\'' ;;' \
  '*"--job 3 --log"*) printf '\''%s\n'\'' '\''tests/test_flaky.py::test_flaky FAILED'\'' ;;' \
  '*"--job 4 --log"*) printf '\''%s\n'\'' '\''tests/test_real.py::test_break FAILED'\'' ;;' \
  '*"--job 5 --log"*) printf '\''%s\n'\'' '\''runner lost network connection while downloading'\'' ;;' \
  '*"--job 1 --log"*|*"--job 2 --log"*) : ;;' \
  '*) echo "unsupported fake gh call: $*" >&2; exit 2 ;;' \
  'esac' > "$T/bin/gh"
chmod +x "$T/bin/gh"

export GH_CALLS="$CALLS" REPRO_CALLS="$T/repro.calls"
out="$(python3 "$TRIAGE" --gh "$T/bin/gh" --workflow verify --branch main --known-flakes "$T/flakes.txt" --idle-check "$T/bin/idle-ok" --test-command "$T/bin/reproduce" --delta-dir "$T/deltas" --json)" || { echo 'not ok - triage exited red'; exit 1; }
python3 -c 'import json,sys; d=json.load(sys.stdin); want={"cancelled","null-job","known-flake","real","environment"}; assert {j["class"] for j in d["jobs"]}==want; assert d["failed_set_diff"]=={"added":["cancelled-job","environment-job","flake-job","null-job"],"persisting":["real-job"],"resolved":["resolved-job"]}' <<< "$out" || { echo 'not ok - classes or failed-set diff'; echo "$out"; exit 1; }
[ "$(cat "$T/repro.calls")" = 'tests/test_real.py::test_break' ] || { echo 'not ok - reproduced anything except the real test id'; cat "$T/repro.calls"; exit 1; }
grep -q 'gh run rerun 101 --failed' <<< "$out" || { echo 'not ok - rerun command not printed'; exit 1; }
! grep -q '^run rerun' "$CALLS" || { echo 'not ok - script reran CI'; exit 1; }
delta="$(find "$T/deltas" -type f -name '*.md' | head -n 1)"
grep -q '^## 1\. Lane header' "$delta" && grep -q '^## 2\. Measurement baseline' "$delta" && grep -q '^## 3\. Task' "$delta" && grep -q 'planning/lane-brief-template.md §3' "$delta" && grep -q 'tests/test_real.py::test_break' "$delta" || { echo 'not ok - fix-lane delta shape'; cat "$delta"; exit 1; }

rm -rf "$T/refused"; : > "$T/repro.calls"
python3 "$TRIAGE" --gh "$T/bin/gh" --workflow verify --branch main --known-flakes "$T/flakes.txt" --idle-check "$T/bin/idle-red" --test-command "$T/bin/reproduce" --delta-dir "$T/refused" >/dev/null 2>&1
[ $? -ne 0 ] && [ ! -s "$T/repro.calls" ] && [ ! -e "$T/refused" ] || { echo 'not ok - idle refusal did not stop reproduction and delta writes'; exit 1; }

echo 'ci-triage: five classes, failed-set diff, real-only reproduction, idle refusal and delta shape ok'
