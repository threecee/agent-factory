#!/usr/bin/env bash
# test_git_hooks.sh — real `git commit` and `git push` through the tracked shims against a
# bare origin, plus the landing rule's pull-request forms through the harness entry.
#
# Runs under bash 3.2+ or zsh 5 (`bash verification/tests/test_git_hooks.sh`; exit 0 = all
# hold). Needs: python3, git, /bin/sh. Every temp path contains a space on purpose. The tree
# under test is a COPY of harness/ and verification/{protections,gates} under the temp dir
# (TEST_PROTECTIONS_ROOT=<dir containing harness/> selects another tree — how the
# self-falsification in verification/protections.md §10 ran the mutated scratch copies).
#
# Every git command runs under `env -i` with FACTORY_GUARD_STATE_DIR and FACTORY_GUARD_LOG
# under the temp dir, FACTORY_GUARD_OFFLINE=1, FACTORY_GIT_EMAIL declared, and every switch
# scrubbed — a direct call without the state-dir override writes into the primary checkout's
# events log (harness/guards.md §3).
#
# Cases (verification/protections.md §10 lists what each proves):
#   1  `git_hooks.py status` exits 1 before install naming core.hooksPath; 0 after; shims +x
#   2  direct push: `git push origin HEAD:main` without a receipt → rejected with GUARD landing,
#      origin/main unchanged; green receipt for HEAD → accepted; red receipt → rejected;
#      receipt for another HEAD → rejected naming both sha8
#   3  HEAD:refs/heads/train/x and HEAD:refs/heads/lane/y → accepted silently; delete main → rejected
#   4  commit-msg: source without trailer → rejected; trailer + record → accepted; `--amend -m`
#      dropping the trailer → rejected with "measured against HEAD~1"; dangling record →
#      rejected; docs-only → accepted; merge commit → accepted; bad subject → WARN, exit 0
#   5  pre-commit identity: config ≠ FACTORY_GIT_EMAIL → rejected; equal → accepted;
#      GIT_AUTHOR_EMAIL override → rejected; declaration unset → accepted with the WARN
#   6  switches through the git hooks: FACTORY_GUARD_ALLOW=landing in the environment → accepted
#      + an events-log allow-switch line; the state-dir allow file honoured from the linked worktree
#   8  landing rule via the harness entry: `gh pr merge 7 --merge --match-head-commit <HEAD>`
#      with a green receipt → allow; without → deny; --squash/--rebase/--auto/--admin → deny
#      naming the merge form; `gh pr create` from lane/* → deny; PostToolUse after the merge with
#      origin/main advanced by a merge commit whose SECOND PARENT is HEAD → state file (mode pr)
#      + duties context; origin/main not containing HEAD → exit 2
#   7  `git push --no-verify` bypasses the hook (git's own escape — the harness `no-verify`
#      rule, harness/tests/test_guards.sh case 4, is the only refusal of the flag); run last
set -u

HERE="$(cd "$(dirname "$0")" && pwd)"
ROOT="${TEST_PROTECTIONS_ROOT:-$HERE/../..}"
ROOT="$(cd "$ROOT" && pwd -P)"
[ -d "$ROOT/harness/guards" ] && [ -d "$ROOT/verification/protections" ] || { echo "need $ROOT/harness/guards and $ROOT/verification/protections"; exit 2; }
command -v python3 >/dev/null 2>&1 || { echo "need python3"; exit 2; }
command -v git >/dev/null 2>&1 || { echo "need git"; exit 2; }
PY="$(command -v python3)"

T="$(mktemp -d "${TMPDIR:-/tmp}/git hooks test.XXXXXX")"
T="$(cd "$T" && pwd -P)"
cleanup() { rm -rf "$T"; }
trap cleanup EXIT

PASS=0; FAIL=0; SKIP=0; N=0
ok()   { N=$((N+1)); PASS=$((PASS+1)); printf 'ok %d - %s\n' "$N" "$1"; }
bad()  { N=$((N+1)); FAIL=$((FAIL+1)); printf 'not ok %d - %s\n    %s\n' "$N" "$1" "${2:-}"; }
skip() { N=$((N+1)); SKIP=$((SKIP+1)); printf 'ok %d - SKIP %s\n' "$N" "$1"; }
check() { if [ "$2" -eq 0 ]; then ok "$1"; else bad "$1" "${3:-}"; fi; }
has() { case "$1" in *"$2"*) return 0 ;; esac; return 1; }

# ---------------------------------------------------------------- fixtures
COPY="$T/copy one"
mkdir -p "$COPY/verification"
cp -R "$ROOT/harness" "$COPY/harness"
cp -R "$ROOT/verification/protections" "$COPY/verification/protections"
cp -R "$ROOT/verification/gates" "$COPY/verification/gates"
find "$COPY" -name __pycache__ -type d -prune -exec rm -rf {} + 2>/dev/null
DRIVER="$COPY/verification/protections/git_hooks.py"
SHIMS="$COPY/verification/protections/githooks"
ENTRY="$COPY/harness/adapters/factory_guard.py"
STATE="$T/state dir"; LOG="$T/hooks.jsonl"
DECLARED="lander@example.invalid"
OUT="$T/out"; ERR="$T/err"; RC=0

# every command under a scrubbed environment; leading VAR=value operands are honoured by env
genv() {
  env -i PATH="$PATH" HOME="$HOME" GIT_TERMINAL_PROMPT=0 FACTORY_GUARD_STATE_DIR="$STATE" FACTORY_GUARD_LOG="$LOG" \
    FACTORY_GUARD_OFFLINE=1 FACTORY_GUARD_PYTHON="$PY" FACTORY_GIT_EMAIL="$DECLARED" "$@"
}
run() { genv "$@" > "$OUT" 2> "$ERR"; RC=$?; }
accepted() { [ "$RC" -eq 0 ] && ! has "$(cat "$ERR")" 'GUARD'; }
payload() { # event command cwd
  python3 -c 'import json,sys; print(json.dumps({"hook_event_name": sys.argv[1], "tool_name": "Bash", "tool_input": {"command": sys.argv[2]}, "cwd": sys.argv[3], "session_id": "hooks-test", "tool_response": {"stdout": "", "stderr": ""}}))' "$1" "$2" "$3"
}
hook() { # event payload — the real harness entry on the copy
  printf '%s' "$2" | genv python3 "$ENTRY" "$1" > "$OUT" 2> "$ERR"; RC=$?
}
receipt() { # name exit head
  printf 'EXIT=%s\nBASE=%s\nHEAD=%s\nLOG=%s\n' "$2" "$MAIN" "$3" "$ART/$1.log" > "$ART/$1.exit"
  printf 'log\n' > "$ART/$1.log"
  sleep 0.05
}

O="$T/origin.git"; P="$T/primary"; W="$T/train wt"; ART="$T/artifacts"
mkdir -p "$ART"
git init -q --bare -b main "$O"
git init -q -b main "$P"
git -C "$P" config user.email "$DECLARED"; git -C "$P" config user.name lander; git -C "$P" config commit.gpgsign false
git -C "$P" remote add origin "$O"
printf 'seed\n' > "$P/README.md"; git -C "$P" add README.md; git -C "$P" commit -q -m init
git -C "$P" push -q -u origin main
MAIN="$(git -C "$P" rev-parse HEAD)"
git -C "$P" checkout -q -b lane/alpha
mkdir -p "$P/src/pkg"; printf 'X = 1\n' > "$P/src/pkg/x.py"; git -C "$P" add -A; git -C "$P" commit -q -m 'feat(pkg): x'
git -C "$P" push -q origin lane/alpha
ALPHA="$(git -C "$P" rev-parse HEAD)"
git -C "$P" checkout -q main
git -C "$P" worktree add -q -b train/x "$W" main
git -C "$W" merge -q --no-ff lane/alpha -m "train(x): board alpha ($ALPHA)"
mkdir -p "$W/docs/choices"
cat > "$W/docs/choices/x.md" <<EOF
# Choices ledger — train x (hook test)

Audited with audit-choices, 2026-09-06.

## Lane \`alpha\` — boarded $ALPHA — one sound

**alpha-1** The lane keeps the constant in the runtime module (sound, H).

## Orchestrator choices

**O-1 — single boarder:** single-lane train — priority P1 (the hook test carries one lane) (sound, H).

## Landing

landing mode: direct-push
override reason: the test fixture has no pull-request host
receipts: $ART
local-verify: skipped (no host in the fixture)
EOF
git -C "$W" add -A; git -C "$W" commit -q -m 'train(x): choices ledger'
HEAD1="$(git -C "$W" rev-parse HEAD)"

# ---------------------------------------------------------------- case 1
( cd "$P" && genv python3 "$DRIVER" status --hooks-dir "$SHIMS" ) > "$OUT" 2> "$ERR"; RC=$?
check "1a status exits 1 before install and names core.hooksPath" "$( [ "$RC" -eq 1 ] && has "$(cat "$OUT")" 'core.hooksPath is «(unset)»'; echo $? )" "rc=$RC $(cat "$OUT" "$ERR")"
( cd "$P" && genv python3 "$DRIVER" install --hooks-dir "$SHIMS" ) > "$OUT" 2> "$ERR"; RC=$?
check "1b install sets core.hooksPath (absolute: the shims live outside the repo)" "$( [ "$RC" -eq 0 ] && [ "$(git -C "$P" config --get core.hooksPath)" = "$SHIMS" ]; echo $? )" "rc=$RC $(cat "$OUT" "$ERR") hooksPath=$(git -C "$P" config --get core.hooksPath)"
( cd "$P" && genv python3 "$DRIVER" status --hooks-dir "$SHIMS" ) > "$OUT" 2> "$ERR"; RC=$?
check "1c status exits 0 after install" "$( [ "$RC" -eq 0 ]; echo $? )" "rc=$RC $(cat "$OUT" "$ERR")"
check "1d the three shims are executable" "$( [ -x "$SHIMS/pre-commit" ] && [ -x "$SHIMS/commit-msg" ] && [ -x "$SHIMS/pre-push" ]; echo $? )"

# ---------------------------------------------------------------- case 2
run git -C "$W" push origin HEAD:main
check "2a push to main without a receipt → rejected with GUARD landing naming the receipt dir" "$( [ "$RC" -ne 0 ] && has "$(cat "$ERR")" 'GUARD landing: no exit receipt' && has "$(cat "$ERR")" "$ART"; echo $? )" "rc=$RC err=$(cat "$ERR")"
check "2b origin/main did not move" "$( [ "$(git -C "$O" rev-parse main)" = "$MAIN" ]; echo $? )"
receipt x-1 0 "$HEAD1"
run git -C "$W" push origin HEAD:main
check "2c push with a green receipt for HEAD → accepted, origin/main == HEAD" "$( accepted && [ "$(git -C "$O" rev-parse main)" = "$HEAD1" ]; echo $? )" "rc=$RC err=$(cat "$ERR")"
printf 'note\n' > "$W/docs/note.md"; run git -C "$W" add -A; run git -C "$W" commit -q -m 'docs(x): note'
HEAD2="$(git -C "$W" rev-parse HEAD)"
receipt x-2 1 "$HEAD2"
run git -C "$W" push origin HEAD:main
check "2d red receipt → rejected naming EXIT=1" "$( [ "$RC" -ne 0 ] && has "$(cat "$ERR")" 'the receipt is red (EXIT=1)'; echo $? )" "rc=$RC err=$(cat "$ERR")"
receipt x-3 0 "$MAIN"
run git -C "$W" push origin HEAD:main
check "2e receipt for another HEAD → rejected naming both sha8" "$( [ "$RC" -ne 0 ] && has "$(cat "$ERR")" 'the receipt is for another HEAD' && has "$(cat "$ERR")" "HEAD=$(printf '%s' "$MAIN" | cut -c1-8)" && has "$(cat "$ERR")" "Landing HEAD=$(printf '%s' "$HEAD2" | cut -c1-8)"; echo $? )" "rc=$RC err=$(cat "$ERR")"
check "2f origin/main still at the accepted push" "$( [ "$(git -C "$O" rev-parse main)" = "$HEAD1" ]; echo $? )"

# ---------------------------------------------------------------- case 3
run git -C "$W" push origin HEAD:refs/heads/train/x
check "3a the integration branch push is accepted silently" "$( accepted && [ "$(git -C "$O" rev-parse train/x)" = "$HEAD2" ]; echo $? )" "rc=$RC err=$(cat "$ERR")"
run git -C "$W" push origin HEAD:refs/heads/lane/y
check "3b a lane branch push is accepted silently" "$( accepted && [ "$(git -C "$O" rev-parse lane/y)" = "$HEAD2" ]; echo $? )" "rc=$RC err=$(cat "$ERR")"
run git -C "$W" push origin --delete main
check "3c deleting main is rejected" "$( [ "$RC" -ne 0 ] && has "$(cat "$ERR")" 'deletion of main is refused' && [ "$(git -C "$O" rev-parse main)" = "$HEAD1" ]; echo $? )" "rc=$RC err=$(cat "$ERR")"

# ---------------------------------------------------------------- case 4
printf 'Y = 1\n' > "$W/src/pkg/y.py"; run git -C "$W" add -A
run git -C "$W" commit -q -m 'feat(pkg): y'
check "4a a source commit without the trailer is rejected naming the trailer" "$( [ "$RC" -ne 0 ] && has "$(cat "$ERR")" 'GUARD commit-refs: the commit touches src/' && has "$(cat "$ERR")" 'without a «^Refs: (ADR-'; echo $? )" "rc=$RC err=$(cat "$ERR")"
mkdir -p "$W/docs/decisions"; printf '# ADR-0097\n' > "$W/docs/decisions/0097-x.md"; run git -C "$W" add -A
run git -C "$W" commit -q -m 'feat(pkg): y

Refs: ADR-0097'
check "4b with the trailer and the record in the same commit → accepted" "$( accepted; echo $? )" "rc=$RC err=$(cat "$ERR")"
run git -C "$W" commit -q --amend -m 'chore(pkg): reword without refs'
check "4c --amend -m dropping the trailer is rejected, measured against HEAD~1" "$( [ "$RC" -ne 0 ] && has "$(cat "$ERR")" 'measured against HEAD~1'; echo $? )" "rc=$RC err=$(cat "$ERR")"
run git -C "$W" commit -q --amend -m 'chore(pkg): reword

Refs: ADR-0097'
check "4d --amend -m keeping the trailer is accepted and the message keeps it" "$( accepted && has "$(git -C "$W" log -1 --format=%B)" 'Refs: ADR-0097' && ! has "$(git -C "$W" log -1 --format=%B)" 'without refs'; echo $? )" "rc=$RC err=$(cat "$ERR")"
printf 'Z = 1\n' > "$W/src/pkg/z.py"; run git -C "$W" add -A
run git -C "$W" commit -q -m 'feat(pkg): z

Refs: ADR-9999'
check "4e a dangling record number is rejected" "$( [ "$RC" -ne 0 ] && has "$(cat "$ERR")" 'names a decision record that does not exist'; echo $? )" "rc=$RC err=$(cat "$ERR")"
run git -C "$W" reset -q -- src/pkg/z.py; rm -f "$W/src/pkg/z.py"
printf 'd\n' > "$W/docs/d.md"; run git -C "$W" add -A
run git -C "$W" commit -q -m 'docs(x): d'
check "4f a docs-only commit needs no trailer" "$( accepted; echo $? )" "rc=$RC err=$(cat "$ERR")"
git -C "$P" checkout -q -b side; printf 's\n' > "$P/docs-side.md"; run git -C "$P" add -A; run git -C "$P" commit -q -m 'docs(side): s'
git -C "$P" checkout -q main
run git -C "$P" merge -q --no-ff side -m 'Merge branch side'
check "4g a merge commit is exempt" "$( accepted && [ "$(git -C "$P" rev-parse HEAD^2)" = "$(git -C "$P" rev-parse side)" ]; echo $? )" "rc=$RC err=$(cat "$ERR")"
printf 'b\n' > "$W/docs/bad.md"; run git -C "$W" add -A
run git -C "$W" commit -q -m 'Fix things'
check "4h a subject outside <type>(<scope>): form is a WARN on stderr, exit 0" "$( [ "$RC" -eq 0 ] && has "$(cat "$ERR")" 'GUARD commit-subject (warn)'; echo $? )" "rc=$RC err=$(cat "$ERR")"

# ---------------------------------------------------------------- case 5
git -C "$W" config user.email wrong@example.invalid
printf 'i\n' > "$W/docs/i.md"; run git -C "$W" add -A
run git -C "$W" commit -q -m 'docs(x): i'
check "5a config identity ≠ FACTORY_GIT_EMAIL → rejected naming both" "$( [ "$RC" -ne 0 ] && has "$(cat "$ERR")" 'GUARD commit-identity: the identity git will write is «wrong@example.invalid»' && has "$(cat "$ERR")" "$DECLARED"; echo $? )" "rc=$RC err=$(cat "$ERR")"
git -C "$W" config user.email "$DECLARED"
run git -C "$W" commit -q -m 'docs(x): i'
check "5b the declared identity → accepted" "$( accepted; echo $? )" "rc=$RC err=$(cat "$ERR")"
printf 'j\n' > "$W/docs/j.md"; run git -C "$W" add -A
run GIT_AUTHOR_EMAIL=employer@example.invalid git -C "$W" commit -q -m 'docs(x): j'
check "5c GIT_AUTHOR_EMAIL over a declared config → rejected via git var" "$( [ "$RC" -ne 0 ] && has "$(cat "$ERR")" '«employer@example.invalid» (author, git var)' && has "$(cat "$ERR")" 'unset GIT_AUTHOR_EMAIL GIT_COMMITTER_EMAIL EMAIL'; echo $? )" "rc=$RC err=$(cat "$ERR")"
run FACTORY_GIT_EMAIL= git -C "$W" commit -q -m 'docs(x): j'
check "5d declaration unset → accepted with the identity-not-declared WARN" "$( [ "$RC" -eq 0 ] && has "$(cat "$ERR")" 'identity not declared'; echo $? )" "rc=$RC err=$(cat "$ERR")"
check "5e the log shows only the declared identity" "$( [ "$(git -C "$W" log --format='%ae %ce' | tr ' ' '\n' | sort -u)" = "$DECLARED" ]; echo $? )" "$(git -C "$W" log --format='%ae %ce' | sort -u)"

# ---------------------------------------------------------------- case 6
HEADS="$(git -C "$W" rev-parse HEAD)"
run FACTORY_GUARD_ALLOW=landing git -C "$W" push origin HEAD:main
check "6a FACTORY_GUARD_ALLOW=landing in the environment → the push is accepted" "$( accepted && [ "$(git -C "$O" rev-parse main)" = "$HEADS" ]; echo $? )" "rc=$RC err=$(cat "$ERR")"
check "6b the events log carries an allow-switch line naming the env source" "$( grep 'allow-switch' "$STATE/factory-events.log" | grep -q 'env:FACTORY_GUARD_ALLOW=landing'; echo $? )" "$(cat "$STATE/factory-events.log" 2>/dev/null | tail -3)"
mkdir -p "$STATE"; printf 'commit-refs\n' > "$STATE/factory-guard-allow"
printf 'K = 1\n' > "$W/src/pkg/k.py"; run git -C "$W" add -A
run git -C "$W" commit -q -m 'feat(pkg): k without refs'
rm -f "$STATE/factory-guard-allow"
check "6c the state-dir allow file is honoured from the linked worktree (file: source logged)" "$( accepted && grep 'allow-switch' "$STATE/factory-events.log" | grep -q 'file:factory-guard-allow=commit-refs'; echo $? )" "rc=$RC err=$(cat "$ERR") $(tail -2 "$STATE/factory-events.log")"

# ---------------------------------------------------------------- case 8
printf 'p\n' > "$W/docs/p.md"; run git -C "$W" add -A; run git -C "$W" commit -q -m 'docs(x): p'
HEAD3="$(git -C "$W" rev-parse HEAD)"
receipt x-4 0 "$HEAD3"
hook PreToolUse "$(payload PreToolUse "gh pr merge 7 --merge --match-head-commit $HEAD3" "$W")"
check "8a gh pr merge --merge --match-head-commit <HEAD> with a green receipt → allow, silent" "$( [ "$RC" -eq 0 ] && [ ! -s "$OUT" ] && [ ! -s "$ERR" ]; echo $? )" "rc=$RC out=$(cat "$OUT") err=$(cat "$ERR")"
for flag in --squash --rebase --auto --admin; do
  hook PreToolUse "$(payload PreToolUse "gh pr merge 7 ${flag} --match-head-commit ${HEAD3}" "$W")"
  needle="«gh pr merge ${flag}»"
  check "8b gh pr merge ${flag} → deny naming the merge form" "$( [ "$RC" -eq 2 ] && has "$(cat "$ERR")" "${needle}" && has "$(cat "$ERR")" "--merge --match-head-commit ${HEAD3}"; echo $? )" "rc=$RC err=$(cat "$ERR")"
done
hook PreToolUse "$(payload PreToolUse "gh pr merge 7 --merge" "$W")"
check "8c gh pr merge without --match-head-commit → deny" "$( [ "$RC" -eq 2 ] && has "$(cat "$ERR")" 'without --match-head-commit'; echo $? )" "rc=$RC err=$(cat "$ERR")"
rm -f "$ART/x-4.exit"
hook PreToolUse "$(payload PreToolUse "gh pr merge 7 --merge --match-head-commit $HEAD3" "$W")"
check "8d without a green receipt for HEAD the merge is denied" "$( [ "$RC" -eq 2 ] && has "$(cat "$ERR")" 'GUARD landing:'; echo $? )" "rc=$RC err=$(cat "$ERR")"
git -C "$P" checkout -q lane/alpha
hook PreToolUse "$(payload PreToolUse "gh pr create --base main --head lane/alpha --title x --body y" "$P")"
git -C "$P" checkout -q main
check "8e gh pr create from a lane branch → deny: push the branch, the lander boards it" "$( [ "$RC" -eq 2 ] && has "$(cat "$ERR")" 'push the branch, the lander boards it'; echo $? )" "rc=$RC err=$(cat "$ERR")"
run git -C "$W" push origin HEAD:refs/heads/train/x
S="$T/merge scratch"; git clone -q "$O" "$S"; git -C "$S" config user.email "$DECLARED"; git -C "$S" config user.name lander
git -C "$S" merge -q --no-ff origin/train/x -m 'Merge pull request #7 from origin/train/x'
git -C "$S" push -q origin HEAD:main
MERGE="$(git -C "$O" rev-parse main)"
hook PostToolUse "$(payload PostToolUse "gh pr merge 7 --merge --match-head-commit $HEAD3" "$W")"
check "8f PostToolUse after the merge: origin/main's tip is the merge commit, HEAD its second parent → registered (contains, never equals)" "$( [ "$RC" -eq 0 ] && [ "$(git -C "$O" rev-parse main^2)" = "$HEAD3" ] && [ "$MERGE" != "$HEAD3" ] && has "$(cat "$OUT")" 'LANDER DUTIES' && has "$(cat "$OUT")" 'pr mode'; echo $? )" "rc=$RC out=$(cat "$OUT") err=$(cat "$ERR")"
check "8g the state file records mode pr, pr 7 and the receipt HEAD" "$( python3 -c 'import json,sys; d=json.load(open(sys.argv[1])); sys.exit(0 if d["mode"]=="pr" and d["pr"]==7 and d["head"]==sys.argv[2] and d["train"]=="x" else 1)' "$STATE/landing-in-progress.json" "$HEAD3"; echo $? )" "$(cat "$STATE/landing-in-progress.json" 2>/dev/null)"
rm -f "$STATE/landing-in-progress.json"
printf 'q\n' > "$W/docs/q.md"; run git -C "$W" add -A; run git -C "$W" commit -q -m 'docs(x): q'
hook PostToolUse "$(payload PostToolUse "git push origin HEAD:main" "$W")"
check "8h PostToolUse when origin/main does not contain HEAD → exit 2, did not register" "$( [ "$RC" -eq 2 ] && has "$(cat "$ERR")" 'did not register' && has "$(cat "$ERR")" 'git log HEAD..origin/main'; echo $? )" "rc=$RC err=$(cat "$ERR")"

# ---------------------------------------------------------------- case 7
git -C "$W" fetch -q origin; git -C "$W" reset -q --hard origin/main
printf 'n\n' > "$W/docs/n.md"; run git -C "$W" add -A; run git -C "$W" commit -q -m 'docs(x): n'
HEADN="$(git -C "$W" rev-parse HEAD)"
before="$(wc -l < "$LOG" | tr -d ' ')"
run git -C "$W" push --no-verify origin HEAD:main
after="$(wc -l < "$LOG" | tr -d ' ')"
check "7a git push --no-verify bypasses the hook by design (no receipt, accepted, nothing logged)" "$( accepted && [ "$(git -C "$O" rev-parse main)" = "$HEADN" ] && [ "$before" = "$after" ]; echo $? )" "rc=$RC err=$(cat "$ERR") before=$before after=$after"
check "7b the verdict log records every hooked git event" "$( python3 -c 'import json,sys; hooks={json.loads(l).get("git_hook") for l in open(sys.argv[1], encoding="utf-8") if l.strip()}; sys.exit(0 if {"pre-commit","commit-msg","pre-push"} <= hooks else 1)' "$LOG"; echo $? )"

# ---------------------------------------------------------------- summary
printf '\n# %d passed, %d failed, %d skipped (tmp: %s)\n' "$PASS" "$FAIL" "$SKIP" "$T"
[ "$FAIL" -eq 0 ]
