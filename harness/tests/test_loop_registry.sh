#!/usr/bin/env bash
# Exercises registry roundtrip and both liveness modes with an injected clock.
set -u

HERE="$(cd "$(dirname "$0")" && pwd)"
REGISTRY="$HERE/../loop_registry.sh"
T="$(mktemp -d "${TMPDIR:-/tmp}/loop registry test.XXXXXX")"
trap 'rm -rf "$T"' EXIT
F="$T/loops.tsv"
export LOOP_REGISTRY_FILE="$F"

LOOP_REGISTRY_NOW=100 "$REGISTRY" add live lane owner 200 'kill 1' "pid:$$"
LOOP_REGISTRY_NOW=100 "$REGISTRY" add dead eval owner 200 'true' 'pid:99999999'
LOOP_REGISTRY_NOW=100 "$REGISTRY" add receipt watch owner 200 'true' "exit_file:$T/done receipt"
LOOP_REGISTRY_NOW=100 "$REGISTRY" add late serve owner 99 'true' "pid:$$"
touch "$T/done receipt"
LOOP_REGISTRY_NOW=100 "$REGISTRY" check >/dev/null 2>&1 && { echo 'not ok - unhealthy registry check was green'; exit 1; }

out="$(LOOP_REGISTRY_NOW=100 "$REGISTRY" list)"
printf '%s\n' "$out" | grep -q $'^live\tlane\towner\t.*\t200\tkill 1\tpid:' || { echo 'not ok - live row did not roundtrip'; exit 1; }
printf '%s\n' "$out" | grep -q $'^dead\t.*\tstale$' || { echo 'not ok - finished pid not stale'; exit 1; }
printf '%s\n' "$out" | grep -q $'^receipt\t.*\tfinished$' || { echo 'not ok - exit file not finished'; exit 1; }
printf '%s\n' "$out" | grep -q $'^late\t.*\toverdue$' || { echo 'not ok - injected clock did not mark overdue'; exit 1; }
LOOP_REGISTRY_NOW=100 "$REGISTRY" done live
LOOP_REGISTRY_NOW=100 "$REGISTRY" list | grep -q $'^live\t.*\tfinished$' || { echo 'not ok - done did not finish'; exit 1; }

echo 'loop-registry: add/done/list/check, dead pid, exit file and injected overdue clock ok'
