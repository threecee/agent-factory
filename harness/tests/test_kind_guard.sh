#!/usr/bin/env bash
# test_kind_guard.sh — M-21 against committed diffs in throwaway repositories.
#
# Runs under bash 3.2+ (`bash harness/tests/test_kind_guard.sh`; exit 0 = both
# falsifications hold). The copied real adapter loads the kind rule beside its
# switched landing-parser dependency, and every assertion names M-21 output.
set -u

HERE="$(cd "$(dirname "$0")" && pwd)"
ROOT="${TEST_KIND_GUARD_ROOT:-$HERE/../..}"
ROOT="$(cd "$ROOT" && pwd -P)"
SRC="$ROOT/harness"
[ -d "$SRC/guards" ] && [ -d "$SRC/adapters" ] || {
  echo "need $SRC/guards and $SRC/adapters"
  exit 2
}
command -v python3 >/dev/null 2>&1 || { echo "need python3"; exit 2; }
command -v git >/dev/null 2>&1 || { echo "need git"; exit 2; }

T="$(mktemp -d "${TMPDIR:-/tmp}/kind-guard-test.XXXXXX")"
cleanup() { rm -rf "$T"; }
trap cleanup EXIT

COPY="$T/harness"
mkdir -p "$COPY"
cp -R "$SRC/guards" "$COPY/guards"
cp -R "$SRC/adapters" "$COPY/adapters"
find "$COPY/guards/rules" -maxdepth 1 -type f -name '*.py' \
  ! -name '__init__.py' ! -name '_*' ! -name 'kind.py' ! -name 'landing.py' -delete
find "$COPY" -name __pycache__ -type d -prune -exec rm -rf {} + 2>/dev/null
ENTRY="$COPY/adapters/factory_guard.py"

CLASSIFIER="$T/classify-kind"
printf '%s\n' \
  '#!/bin/sh' \
  'kind=docs-only' \
  'for path in "$@"; do' \
  '  case "$path" in README.md|docs/*|*.md) ;; *) kind=source ;; esac' \
  'done' \
  'printf "%s\n" "$kind"' > "$CLASSIFIER"
chmod +x "$CLASSIFIER"

REPO=""; STATE=""; LOG=""; OUT="$T/out"; ERR="$T/err"; RC=0
new_train() { # name changed-path declared-kind [recorded-kind]
  local name="$1" changed="$2" declared="$3" recorded="${4:-$3}" base head artifacts
  REPO="$T/$name"
  STATE="$T/$name-state"
  LOG="$T/$name-guard.jsonl"
  mkdir -p "$REPO"
  git -C "$REPO" init -q -b main
  git -C "$REPO" config user.email lander@example.invalid
  git -C "$REPO" config user.name lander
  printf '%s\n' seed > "$REPO/seed.txt"
  git -C "$REPO" add seed.txt
  git -C "$REPO" commit -q -m init
  base="$(git -C "$REPO" rev-parse HEAD)"
  git -C "$REPO" checkout -q -b train/wtest
  mkdir -p "$(dirname "$REPO/$changed")"
  printf '%s\n' changed > "$REPO/$changed"
  git -C "$REPO" add "$changed"
  git -C "$REPO" commit -q -m change
  artifacts="$T/$name-artifacts"
  mkdir -p "$REPO/docs/choices" "$artifacts"
  printf '%s\n' \
    '# Choices ledger — train wtest' \
    '' \
    '## Landing' \
    "receipts: $artifacts" \
    "kind: ${declared}→${recorded}" > "$REPO/docs/choices/wtest.md"
  git -C "$REPO" add docs/choices/wtest.md
  git -C "$REPO" commit -q -m ledger
  head="$(git -C "$REPO" rev-parse HEAD)"
  printf 'EXIT=0\nBASE=%s\nHEAD=%s\nLOG=%s\n' \
    "$base" "$head" "$artifacts/wtest-1.log" > "$artifacts/wtest-1.exit"
}

payload() {
  python3 - "$REPO" <<'PY'
import json
import sys

print(json.dumps({
    "hook_event_name": "PreToolUse",
    "tool_name": "Bash",
    "tool_input": {"command": "git push origin HEAD:main"},
    "cwd": sys.argv[1],
    "session_id": "kind-falsification",
}))
PY
}

run_guard() {
  printf '%s' "$(payload)" | env -i PATH="$PATH" HOME="$HOME" \
    CLAUDE_PROJECT_DIR="$REPO" FACTORY_GUARD_STATE_DIR="$STATE" \
    FACTORY_GUARD_LOG="$LOG" FACTORY_GUARD_KIND_CMD="$CLASSIFIER" \
    FACTORY_GUARD_ALLOW=landing \
    PYTHONDONTWRITEBYTECODE=1 python3 "$ENTRY" PreToolUse > "$OUT" 2> "$ERR"
  RC=$?
}

PASS=0; FAIL=0
check() {
  if [ "$2" -eq 0 ]; then
    PASS=$((PASS+1)); printf 'ok %d - %s\n' "$((PASS+FAIL))" "$1"
  else
    FAIL=$((FAIL+1)); printf 'not ok %d - %s\n    %s\n' "$((PASS+FAIL))" "$1" "$3"
  fi
}
has() { case "$1" in *"$2"*) return 0 ;; esac; return 1; }

new_train rise src/app.txt docs-only
run_guard
check "docs-only declaration with a source diff is refused" \
  "$( [ "$RC" -eq 2 ] && has "$(cat "$ERR")" 'GUARD kind: declared kind docs-only rose to source' && [ ! -s "$OUT" ]; echo $? )" \
  "rc=$RC out=$(cat "$OUT") err=$(cat "$ERR")"

new_train fall docs/guide.md source
run_guard
check "source declaration with a docs-only diff is recorded as context, not refused" \
  "$( [ "$RC" -eq 0 ] && has "$(cat "$OUT")" 'GUARD kind: delivered kind fell from source to docs-only; record' && [ ! -s "$ERR" ]; echo $? )" \
  "rc=$RC out=$(cat "$OUT") err=$(cat "$ERR")"

check "the falling-kind context is present in the guard verdict log" \
  "$( python3 - "$LOG" <<'PY'
import json
import pathlib
import sys

rows = [json.loads(line) for line in pathlib.Path(sys.argv[1]).read_text(encoding="utf-8").splitlines()]
raise SystemExit(0 if rows[-1]["verdicts"].get("kind") == "context" else 1)
PY
  echo $? )" "$(cat "$LOG" 2>/dev/null)"

new_train acknowledged src/app.txt docs-only source
run_guard
check "a risen kind already recorded after its selected legs is not refused again" \
  "$( [ "$RC" -eq 0 ] && python3 - "$LOG" <<'PY'
import json
import pathlib
import sys

rows = [json.loads(line) for line in pathlib.Path(sys.argv[1]).read_text(encoding="utf-8").splitlines()]
raise SystemExit(0 if rows[-1]["verdicts"].get("kind") == "allow" else 1)
PY
  echo $? )" "rc=$RC out=$(cat "$OUT") err=$(cat "$ERR") log=$(cat "$LOG" 2>/dev/null)"

printf 'kind guard: %d passed, %d failed\n' "$PASS" "$FAIL"
[ "$FAIL" -eq 0 ]
