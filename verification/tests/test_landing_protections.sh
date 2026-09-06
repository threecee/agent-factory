#!/usr/bin/env bash
# test_landing_protections.sh — the status poster, the ruleset bootstrap and the CI signal
# against a fake `gh` that RECORDS every call; the three new gates and the two gate legs run
# by the documented `python3 -m scripts.<gate>` form on a temp copy with planted violations;
# the close-out Stop rule's three-strike and escape through the harness entry.
#
# Runs under bash 3.2+ or zsh 5 (`bash verification/tests/test_landing_protections.sh`; exit
# 0 = all hold). Needs: python3 (with PyYAML for the check_backlog case), git, /bin/sh. Every
# temp path contains a space on purpose. The fake `gh` is first on PATH and answers from
# FAKE_GH_* variables; every poster/bootstrap case asserts the RECORDED call, never only the
# exit code (a poster that exits 0 without calling gh cannot pass). Every guard case sets
# FACTORY_GUARD_STATE_DIR (harness/guards.md §3).
#
# Cases (verification/protections.md §10 lists what each proves):
#   1–7   post_local_verify.sh: green receipt → one statuses call with context/state/description;
#         EXIT=2 → refused, no call; HEAD mismatch → refused naming both; already posted → no
#         call; 422 → exit 1 naming the integration-branch push; no gh → manual command;
#         unauthenticated → gh auth login
#   8–14  bootstrap_ruleset.py: empty listing → create (dry run writes nothing); --apply → one
#         POST whose body equals the example JSON; identical round-trip → unchanged, --check 0;
#         evaluate stored → update, --apply → PUT rulesets/<id>, --check 1; 403 → paid-plan hint;
#         no gh → --check offline exit 0, --strict exit 2; --enforcement evaluate → the reminder
#   15–20 ci_signal.sh: RED with the failing job and the --log-failed hint; GREEN exact line;
#         auth failure silent; no gh silent; an open train PR → the Open trains line; none → no line
#   21    check_landing_closeout: merged unreaped train tree → reap duty with unlink + remove;
#         remote train branch → duty; pr mode OPEN → duty, MERGED → none; origin/main containing
#         HEAD through a merge commit → no remote duty; primary behind → ff duty; floor 0 → silent
#   22    the closeout Stop rule through the harness entry: deny with the checklist; three → context;
#         allow-file word → allow; manual deletion → state-removed event
#   23    check_choices_protocol: missing → HARD; entry without ID; unsound without fix; hedge;
#         --at-push without ## Landing; complete → OK; --warn exit 0
#   24    drift leg: claimed row whose file is on origin/main → HARD naming the number; lane-only → silent
#   25    duplicate-id leg through check_backlog
#   26    check_gate_weakening: baseline grew; gate without test; assert loss; Gate-change trailer;
#         WARN exit 0; --hard exit 1
set -u

HERE="$(cd "$(dirname "$0")" && pwd)"
ROOT="${TEST_PROTECTIONS_ROOT:-$HERE/../..}"
ROOT="$(cd "$ROOT" && pwd -P)"
[ -d "$ROOT/harness/guards" ] && [ -d "$ROOT/verification/protections" ] && [ -d "$ROOT/verification/gates" ] || { echo "need harness/guards, verification/protections and verification/gates under $ROOT"; exit 2; }
command -v python3 >/dev/null 2>&1 || { echo "need python3"; exit 2; }
command -v git >/dev/null 2>&1 || { echo "need git"; exit 2; }
PY="$(command -v python3)"; GIT="$(command -v git)"

T="$(mktemp -d "${TMPDIR:-/tmp}/landing protections.XXXXXX")"
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
mkdir -p "$COPY/verification" "$T/scripts" "$T/fake bin" "$T/no gh bin"
cp -R "$ROOT/harness" "$COPY/harness"
cp -R "$ROOT/verification/protections" "$COPY/verification/protections"
cp -R "$ROOT/verification/gates" "$COPY/verification/gates"
cp "$ROOT"/verification/gates/*.py "$T/scripts/"
find "$COPY" "$T/scripts" -name __pycache__ -type d -prune -exec rm -rf {} + 2>/dev/null
PROT="$COPY/verification/protections"
ENTRY="$COPY/harness/adapters/factory_guard.py"
EXAMPLE="$ROOT/verification/ci/ruleset-main.json.example"
OUT="$T/out"; ERR="$T/err"; RC=0
GHLOG="$T/gh calls.log"; GHIN="$T/gh stdin.log"
ln -s "$PY" "$T/no gh bin/python3"; ln -s "$GIT" "$T/no gh bin/git"
cat > "$T/fake bin/gh" <<'EOF'
#!/bin/sh
# fake gh: records argv (and stdin for --input -), answers from FAKE_GH_* variables
printf '%s\n' "$*" >> "${FAKE_GH_LOG:?}"
case "$1 $2" in
  "auth status") [ "${FAKE_GH_AUTH:-0}" = "0" ] && exit 0; echo "You are not logged into any GitHub hosts" >&2; exit 1 ;;
  "run list") [ -n "${FAKE_GH_RUN:-}" ] && printf '%s\n' "$FAKE_GH_RUN"; exit 0 ;;
  "run view") printf '%s\n' "${FAKE_GH_JOBS:-}"; exit 0 ;;
  "pr list") [ -n "${FAKE_GH_TRAINS:-}" ] && printf '%s\n' "$FAKE_GH_TRAINS"; exit 0 ;;
  "pr view") printf '%s\n' "${FAKE_GH_PR_STATE:-MERGED}"; exit 0 ;;
esac
[ "$1" = "api" ] || { echo "fake gh: unsupported $*" >&2; exit 1; }
shift
METHOD=GET; P=""; INPUT=0
while [ $# -gt 0 ]; do
  case "$1" in
    -X) METHOD="$2"; shift 2 ;;
    --input) INPUT=1; shift 2 ;;
    repos/*) P="$1"; shift ;;
    *) shift ;;
  esac
done
[ "$INPUT" = 1 ] && { cat >> "${FAKE_GH_STDIN:?}"; printf '\n' >> "$FAKE_GH_STDIN"; }
[ -z "${FAKE_GH_API_FAIL:-}" ] || { printf '%s\n' "$FAKE_GH_API_FAIL" >&2; exit 1; }
case "$P" in
  */commits/*/status) printf '%s\n' "${FAKE_GH_STATUS_READBACK:-}" ;;
  */statuses/*) case "${FAKE_GH_POST:-ok}" in 422) echo "gh: No commit found for SHA (HTTP 422)" >&2; exit 1 ;; *) echo '{"id": 1}' ;; esac ;;
  */rulesets) case "$METHOD" in GET) printf '%s\n' "${FAKE_GH_RULESETS_LIST:-[]}" ;; *) echo '{"id": 99}' ;; esac ;;
  */rulesets/*) case "$METHOD" in GET) cat "${FAKE_GH_RULESET_GET:?}" ;; *) echo '{"id": 99}' ;; esac ;;
  *) echo "fake gh: unsupported api $METHOD $P" >&2; exit 1 ;;
esac
exit 0
EOF
chmod +x "$T/fake bin/gh"
# every command under a scrubbed environment with the fake gh first on PATH
genv() { env -i PATH="$T/fake bin:$PATH" HOME="$HOME" GIT_TERMINAL_PROMPT=0 FAKE_GH_LOG="$GHLOG" FAKE_GH_STDIN="$GHIN" "$@"; }
nogh() { env -i PATH="$T/no gh bin:/usr/bin:/bin" HOME="$HOME" GIT_TERMINAL_PROMPT=0 "$@"; }
run() { : > "$GHLOG"; : > "$GHIN"; genv "$@" > "$OUT" 2> "$ERR"; RC=$?; }
calls() { cat "$GHLOG"; }
gate() { # cwd [VAR=value ...] -- python3 -m scripts.<gate> args … (the documented invocation, on the temp copy)
  local dir="$1"; shift
  ( cd "$dir" && genv PYTHONPATH="$T" PYTHONDONTWRITEBYTECODE=1 "$@" ) > "$OUT" 2> "$ERR"; RC=$?
}
newrepo() { # dir — a committed main with origin/main pointing at it
  mkdir -p "$1"; git -C "$1" init -q -b main
  git -C "$1" config user.email t@example.invalid; git -C "$1" config user.name t; git -C "$1" config commit.gpgsign false
}

# ---------------------------------------------------------------- cases 1–7: the poster
R="$T/receipt repo"; newrepo "$R"; printf 'x\n' > "$R/README.md"; git -C "$R" add -A; git -C "$R" commit -q -m init
git -C "$R" checkout -q -b train/t-1; printf 'y\n' > "$R/y.md"; git -C "$R" add -A; git -C "$R" commit -q -m 'train(t-1): y'
HEAD="$(git -C "$R" rev-parse HEAD)"; BASE="$(git -C "$R" rev-parse HEAD~1)"; SHA8="$(printf '%s' "$HEAD" | cut -c1-8)"
ART="$T/art dir"; mkdir -p "$ART"
receipt() { printf 'EXIT=%s\nBASE=%s\nHEAD=%s\nLOG=%s\n' "$2" "$BASE" "$3" "$ART/$1.log" > "$ART/$1.exit"; }
receipt r-1 0 "$HEAD"
run "$PROT/post_local_verify.sh" "$ART/r-1.exit" --tree "$R"
check "1 green receipt → exit 0, posted line, exactly one statuses call with context/state/description" \
  "$( [ "$RC" -eq 0 ] && has "$(cat "$OUT")" "posted local-verify on $SHA8 (run r-1)" && [ "$(grep -c "statuses/$HEAD" "$GHLOG")" -eq 1 ] && grep -q "statuses/$HEAD -f state=success -f context=local-verify -f description=EXIT=0 run=r-1" "$GHLOG"; echo $? )" "rc=$RC out=$(cat "$OUT") err=$(cat "$ERR") calls=$(calls)"
receipt r-2 2 "$HEAD"
run "$PROT/post_local_verify.sh" "$ART/r-2.exit" --tree "$R"
check "2 EXIT=2 → refused naming the receipt, no gh call" "$( [ "$RC" -eq 1 ] && has "$(cat "$ERR")" 'r-2.exit says EXIT=2' && [ ! -s "$GHLOG" ]; echo $? )" "rc=$RC err=$(cat "$ERR") calls=$(calls)"
receipt r-3 0 "$BASE"
run "$PROT/post_local_verify.sh" "$ART/r-3.exit" --tree "$R"
check "3 HEAD mismatch → refused naming both SHAs, no gh call" "$( [ "$RC" -eq 1 ] && has "$(cat "$ERR")" "HEAD=$BASE" && has "$(cat "$ERR")" "is at $HEAD" && [ ! -s "$GHLOG" ]; echo $? )" "rc=$RC err=$(cat "$ERR")"
run env FAKE_GH_STATUS_READBACK=local-verify "$PROT/post_local_verify.sh" "$ART/r-1.exit" --tree "$R"
check "4 already posted (read-back) → exit 0 'already posted', no statuses call" "$( [ "$RC" -eq 0 ] && has "$(cat "$OUT")" 'already posted local-verify' && ! grep -q "statuses/" "$GHLOG" && grep -q "commits/$HEAD/status" "$GHLOG"; echo $? )" "rc=$RC out=$(cat "$OUT") calls=$(calls)"
run env FAKE_GH_POST=422 "$PROT/post_local_verify.sh" "$ART/r-1.exit" --tree "$R"
check "5 HTTP 422 → exit 1 naming the integration-branch push" "$( [ "$RC" -eq 1 ] && has "$(cat "$ERR")" 'git push origin HEAD:refs/heads/train/t-1'; echo $? )" "rc=$RC err=$(cat "$ERR")"
nogh "$PROT/post_local_verify.sh" "$ART/r-1.exit" --tree "$R" > "$OUT" 2> "$ERR"; RC=$?
check "6 no gh on PATH → exit 1 with the manual gh api command" "$( [ "$RC" -eq 1 ] && has "$(cat "$ERR")" "gh api repos/{owner}/{repo}/statuses/$HEAD -f state=success -f context=local-verify"; echo $? )" "rc=$RC err=$(cat "$ERR")"
run env FAKE_GH_AUTH=1 "$PROT/post_local_verify.sh" "$ART/r-1.exit" --tree "$R"
check "7 unauthenticated gh → exit 1 naming gh auth login, no statuses call" "$( [ "$RC" -eq 1 ] && has "$(cat "$ERR")" 'gh auth login' && ! grep -q 'statuses/' "$GHLOG"; echo $? )" "rc=$RC err=$(cat "$ERR")"

# ---------------------------------------------------------------- cases 8–14: the ruleset bootstrap
BOOT="$PROT/bootstrap_ruleset.py"
python3 - "$EXAMPLE" "$T/stored same.json" "$T/stored evaluate.json" "$T/listing.json" <<'EOF'
import json, sys
example = json.load(open(sys.argv[1], encoding="utf-8"))
def stored(enforcement):
    data = json.loads(json.dumps(example)); data["enforcement"] = enforcement
    data.update({"id": 1, "_links": {}, "source": "x", "node_id": "R_x", "created_at": "2026-09-06T00:00:00Z"})
    for rule in data["rules"]:
        if rule["type"] == "required_status_checks":
            rule["parameters"]["do_not_enforce_on_create"] = False
            for check in rule["parameters"]["required_status_checks"]:
                check["integration_id"] = None
    return data
json.dump(stored("active"), open(sys.argv[2], "w"))
json.dump(stored("evaluate"), open(sys.argv[3], "w"))
json.dump([{"id": 1, "name": example["name"], "target": "branch", "enforcement": "active"}], open(sys.argv[4], "w"))
EOF
LISTING="$(cat "$T/listing.json")"
run python3 "$BOOT" --file "$EXAMPLE"
check "8 empty listing → create, dry run writes nothing (only the GET was made)" "$( [ "$RC" -eq 0 ] && has "$(cat "$OUT")" 'main-local-verify: create' && has "$(cat "$OUT")" 'dry-run: nothing written' && [ "$(grep -c . "$GHLOG")" -eq 1 ] && ! grep -q 'POST\|PUT' "$GHLOG"; echo $? )" "rc=$RC out=$(cat "$OUT") calls=$(calls)"
run python3 "$BOOT" --file "$EXAMPLE" --apply
check "9 --apply → one POST whose body equals the example JSON, then the settings command printed" \
  "$( [ "$RC" -eq 0 ] && [ "$(grep -c -- '-X POST repos/{owner}/{repo}/rulesets --input -' "$GHLOG")" -eq 1 ] && python3 -c 'import json,sys; sys.exit(0 if json.load(open(sys.argv[1]))==json.loads(open(sys.argv[2]).read().strip().splitlines()[-1]) else 1)' "$EXAMPLE" "$GHIN" && has "$(cat "$OUT")" 'gh api -X PATCH repos/{owner}/{repo} -F allow_squash_merge=false'; echo $? )" "rc=$RC out=$(cat "$OUT") calls=$(calls) stdin=$(cat "$GHIN")"
run env FAKE_GH_RULESETS_LIST="$LISTING" FAKE_GH_RULESET_GET="$T/stored same.json" python3 "$BOOT" --file "$EXAMPLE" --check
check "10 identical round-tripped ruleset → unchanged, --check exit 0" "$( [ "$RC" -eq 0 ] && has "$(cat "$OUT")" 'unchanged (id 1)' && has "$(cat "$OUT")" 'verified against the host'; echo $? )" "rc=$RC out=$(cat "$OUT") err=$(cat "$ERR")"
run env FAKE_GH_RULESETS_LIST="$LISTING" FAKE_GH_RULESET_GET="$T/stored evaluate.json" python3 "$BOOT" --file "$EXAMPLE" --check
check "11a enforcement evaluate on the host → --check exit 1 naming update" "$( [ "$RC" -eq 1 ] && has "$(cat "$OUT")" 'update (id 1)' && has "$(cat "$ERR")" 'drift'; echo $? )" "rc=$RC out=$(cat "$OUT") err=$(cat "$ERR")"
run env FAKE_GH_RULESETS_LIST="$LISTING" FAKE_GH_RULESET_GET="$T/stored evaluate.json" python3 "$BOOT" --file "$EXAMPLE" --apply
check "11b --apply on drift → one PUT to rulesets/1 with the example body" "$( [ "$RC" -eq 0 ] && [ "$(grep -c -- '-X PUT repos/{owner}/{repo}/rulesets/1 --input -' "$GHLOG")" -eq 1 ] && python3 -c 'import json,sys; sys.exit(0 if json.load(open(sys.argv[1]))==json.loads(open(sys.argv[2]).read().strip().splitlines()[-1]) else 1)' "$EXAMPLE" "$GHIN"; echo $? )" "rc=$RC out=$(cat "$OUT") calls=$(calls)"
run env FAKE_GH_API_FAIL='HTTP 403: Upgrade to GitHub Pro or make this repository public to enable this feature.' python3 "$BOOT" --file "$EXAMPLE"
check "12 403 upgrade → exit 1 with the paid-plan hint and the classic fallback" "$( [ "$RC" -eq 1 ] && has "$(cat "$ERR")" 'paid plan' && has "$(cat "$ERR")" 'classic protection fallback'; echo $? )" "rc=$RC err=$(cat "$ERR")"
nogh python3 "$BOOT" --file "$EXAMPLE" --check > "$OUT" 2> "$ERR"; RC=$?
check "13a no gh → --check prints 'not verified (offline' and exits 0" "$( [ "$RC" -eq 0 ] && has "$(cat "$OUT")" 'not verified (offline'; echo $? )" "rc=$RC out=$(cat "$OUT") err=$(cat "$ERR")"
nogh python3 "$BOOT" --file "$EXAMPLE" --check --strict > "$OUT" 2> "$ERR"; RC=$?
check "13b no gh → --check --strict exits 2" "$( [ "$RC" -eq 2 ]; echo $? )" "rc=$RC out=$(cat "$OUT")"
run python3 "$BOOT" --file "$EXAMPLE" --enforcement evaluate
check "14 --enforcement evaluate carries the one-landing reminder and plans enforcement=evaluate" "$( [ "$RC" -eq 0 ] && has "$(cat "$OUT")" 'logged escape for ONE landing' && has "$(cat "$OUT")" 'enforcement=evaluate'; echo $? )" "rc=$RC out=$(cat "$OUT")"
check "14b the example payload has no pull-request rule, no review rule, no bypass actor, strict on" "$( python3 -c '
import json,sys; d=json.load(open(sys.argv[1])); types=[r["type"] for r in d["rules"]]
assert types == ["deletion","non_fast_forward","required_status_checks"], types
assert d["bypass_actors"] == [] and d["enforcement"] == "active" and d["target"] == "branch"
p = d["rules"][2]["parameters"]; assert p["strict_required_status_checks_policy"] is True and p["required_status_checks"] == [{"context": "local-verify"}]
assert d["conditions"]["ref_name"]["include"] == ["refs/heads/main"]' "$EXAMPLE"; echo $? )"

# ---------------------------------------------------------------- cases 15–20: the CI signal
CI="$PROT/ci_signal.sh"
run env FAKE_GH_RUN='34015490459 failure 806ca842f82719d025ea3eae1c564ab3859b64be' FAKE_GH_JOBS='make verify' "$CI"
check "15 RED main → the failing job and the --log-failed hint, never a verdict" "$( [ "$RC" -eq 0 ] && has "$(cat "$OUT")" 'CI main: RED failure (34015490459, 806ca842; make verify)' && has "$(cat "$OUT")" 'gh run view 34015490459 --log-failed' && ! has "$(cat "$OUT")" 'merge'; echo $? )" "rc=$RC out=$(cat "$OUT")"
run env FAKE_GH_RUN='1 success 0123456789abcdef0123456789abcdef01234567' "$CI"
check "16 GREEN main → the exact one line" "$( [ "$RC" -eq 0 ] && [ "$(cat "$OUT")" = 'CI main: GREEN (1, 01234567)' ]; echo $? )" "rc=$RC out=$(cat "$OUT")"
run env FAKE_GH_AUTH=1 FAKE_GH_RUN='1 failure abc' "$CI"
check "17 auth failure → silent, exit 0" "$( [ "$RC" -eq 0 ] && [ ! -s "$OUT" ]; echo $? )" "rc=$RC out=$(cat "$OUT")"
nogh "$CI" > "$OUT" 2> "$ERR"; RC=$?
check "18 no gh → silent, exit 0" "$( [ "$RC" -eq 0 ] && [ ! -s "$OUT" ] && [ ! -s "$ERR" ]; echo $? )" "rc=$RC out=$(cat "$OUT") err=$(cat "$ERR")"
run env FAKE_GH_RUN='1 success 0123456789abcdef0123456789abcdef01234567' FAKE_GH_TRAINS='#12 train/x head abcd1234 local-verify=posted verify=failure' "$CI"
check "19 an open train PR → the Open trains line with local-verify and verify" "$( [ "$RC" -eq 0 ] && has "$(cat "$OUT")" 'Open trains: #12 train/x head abcd1234 local-verify=posted verify=failure'; echo $? )" "rc=$RC out=$(cat "$OUT")"
run env FAKE_GH_RUN='1 success 0123456789abcdef0123456789abcdef01234567' "$CI"
check "20 no open train → no Open trains line (the train/* filter runs inside gh's jq: see protections.md §10)" "$( [ "$RC" -eq 0 ] && ! has "$(cat "$OUT")" 'Open trains'; echo $? )" "rc=$RC out=$(cat "$OUT")"

# ---------------------------------------------------------------- case 21: check_landing_closeout
O2="$T/closeout origin.git"; P2="$T/closeout primary"; W2="$T/closeout train"
git init -q --bare -b main "$O2"
newrepo "$P2"; git -C "$P2" remote add origin "$O2"; printf 'x\n' > "$P2/README.md"; git -C "$P2" add -A; git -C "$P2" commit -q -m init; git -C "$P2" push -q -u origin main
git -C "$P2" worktree add -q -b train/wc "$W2" main
printf 'l\n' > "$W2/landed.txt"; git -C "$W2" add -A; git -C "$W2" commit -q -m 'train(wc): board alpha'; git -C "$W2" push -q -u origin train/wc
TH="$(git -C "$W2" rev-parse HEAD)"
ln -s "$P2/.venv" "$W2/.venv"
git -C "$P2" merge -q --no-ff -m 'Merge pull request #7 from origin/train/wc' train/wc; git -C "$P2" push -q origin main
MERGED="$(git -C "$P2" rev-parse HEAD)"
STATE2="$T/closeout state"; mkdir -p "$STATE2"
state() { # mode pr denials
  python3 -c 'import json,sys; json.dump({"train":"wc","head":sys.argv[1],"mode":sys.argv[2],"pr":(int(sys.argv[3]) if sys.argv[3] else None),"boarders":{},"artifacts_dir":None,"default_branch":"main","pushed_at":"2026-09-06T12:00:00+00:00","denials":int(sys.argv[4])}, open(sys.argv[5],"w"))' "$TH" "$1" "$2" "$3" "$STATE2/landing-in-progress.json"
}
state direct-push "" 0
gate "$T" FACTORY_GUARD_OFFLINE=1 python3 -m scripts.check_landing_closeout --state "$STATE2/landing-in-progress.json" --primary "$P2" --floor-gb 0
check "21a merged, unreaped train tree → exit 1 with the reap duty naming unlink + worktree remove + branch -d" "$( [ "$RC" -eq 1 ] && has "$(cat "$OUT")" "[CLOSEOUT] [ ] reap $W2" && has "$(cat "$OUT")" "unlink $W2/.venv && git -C $P2 worktree remove $W2 && git -C $P2 branch -d train/wc"; echo $? )" "rc=$RC out=$(cat "$OUT") err=$(cat "$ERR")"
check "21b the remote train branch is a duty with the exact deletion command" "$( has "$(cat "$OUT")" 'remote branch train/wc still exists' && has "$(cat "$OUT")" 'git push origin --delete train/wc'; echo $? )" "$(cat "$OUT")"
check "21c origin/main contains HEAD through the merge commit → no remote duty (contains, never equals)" "$( [ "$MERGED" != "$TH" ] && [ "$(git -C "$O2" rev-parse main^2)" = "$TH" ] && ! has "$(cat "$OUT")" 'does not contain'; echo $? )" "$(cat "$OUT")"
check "21d floor 0 → no disk duty" "$( ! has "$(cat "$OUT")" 'disk:'; echo $? )"
state pr 7 0
gate "$T" FAKE_GH_PR_STATE=OPEN python3 -m scripts.check_landing_closeout --state "$STATE2/landing-in-progress.json" --primary "$P2" --floor-gb 0
check "21e pr mode with the pull request OPEN → duty naming the merge form" "$( [ "$RC" -eq 1 ] && has "$(cat "$OUT")" 'pull request #7 is not merged' && has "$(cat "$OUT")" "gh pr merge 7 --merge --match-head-commit $TH"; echo $? )" "$(cat "$OUT")"
gate "$T" FAKE_GH_PR_STATE=MERGED python3 -m scripts.check_landing_closeout --state "$STATE2/landing-in-progress.json" --primary "$P2" --floor-gb 0
check "21f pr mode MERGED → no pull-request duty; offline → a note, never an invented duty" "$( ! has "$(cat "$OUT")" 'is not merged'; echo $? )" "$(cat "$OUT")"
gate "$T" FACTORY_GUARD_OFFLINE=1 python3 -m scripts.check_landing_closeout --state "$STATE2/landing-in-progress.json" --primary "$P2" --floor-gb 0
check "21g offline pr mode → note 'not verified (offline)', no duty invented" "$( has "$(cat "$OUT")" 'not verified (offline)' && ! has "$(cat "$OUT")" 'is not merged'; echo $? )" "$(cat "$OUT")"
gate "$T" FACTORY_GUARD_OFFLINE=1 python3 -m scripts.check_landing_closeout --state "$STATE2/landing-in-progress.json" --primary "$P2" --floor-gb 999999
check "21h an unreachable floor → the disk duty" "$( has "$(cat "$OUT")" '[CLOSEOUT] [ ] disk:'; echo $? )" "$(cat "$OUT")"
git -C "$P2" reset -q --hard main~1
state direct-push "" 0
gate "$T" FACTORY_GUARD_OFFLINE=1 python3 -m scripts.check_landing_closeout --state "$STATE2/landing-in-progress.json" --primary "$P2" --floor-gb 0
check "21i primary behind → the fast-forward duty with the exact pull" "$( has "$(cat "$OUT")" 'fast-forward the primary' && has "$(cat "$OUT")" "git -C $P2 pull --ff-only origin main"; echo $? )" "$(cat "$OUT")"
git -C "$P2" pull -q --ff-only origin main

# ---------------------------------------------------------------- case 22: the closeout Stop rule through the harness entry
STATE3="$T/guard state"; LOG3="$T/guard.jsonl"
stop_payload() { python3 -c 'import json,sys; print(json.dumps({"hook_event_name":"Stop","session_id":sys.argv[1],"stop_hook_active":False,"cwd":sys.argv[2]}))' "$1" "$P2"; }
hook() { # event payload
  printf '%s' "$2" | genv FACTORY_GUARD_STATE_DIR="$STATE3" FACTORY_GUARD_LOG="$LOG3" FACTORY_GUARD_OFFLINE=1 FACTORY_GATES_DIR="$T/scripts" FACTORY_GUARD_DISK_FLOOR_GB=0 PYTHONDONTWRITEBYTECODE=1 python3 "$ENTRY" "$1" > "$OUT" 2> "$ERR"; RC=$?
}
mkdir -p "$STATE3"; cp "$STATE2/landing-in-progress.json" "$STATE3/landing-in-progress.json"
hook Stop "$(stop_payload s-1)"
check "22a Stop with open duties → exit 2, the checklist with the reap line and the escape" "$( [ "$RC" -eq 2 ] && has "$(cat "$ERR")" 'GUARD closeout: LANDER DUTIES OPEN' && has "$(cat "$ERR")" "[ ] reap $W2" && has "$(cat "$ERR")" "the word closeout in $STATE3/factory-guard-allow"; echo $? )" "rc=$RC err=$(cat "$ERR")"
check "22b the refusal was counted in the state file" "$( python3 -c 'import json,sys; sys.exit(0 if json.load(open(sys.argv[1]))["denials"]==1 else 1)' "$STATE3/landing-in-progress.json"; echo $? )"
python3 - "$STATE3/landing-in-progress.json" <<'EOF'
import json, sys; p = sys.argv[1]; d = json.load(open(p)); d["denials"] = 3; json.dump(d, open(p, "w"))
EOF
hook Stop "$(stop_payload s-1)"
check "22c after three refusals the stop is allowed with a loud note (exit 0, context)" "$( [ "$RC" -eq 0 ] && has "$(cat "$OUT")" '3 refusals used — the stop is allowed now' && [ ! -s "$ERR" ]; echo $? )" "rc=$RC out=$(cat "$OUT") err=$(cat "$ERR")"
printf 'closeout\n' > "$STATE3/factory-guard-allow"
hook Stop "$(stop_payload s-2)"
rm -f "$STATE3/factory-guard-allow"
check "22d the word closeout in the allow file → allow, logged as a switch use" "$( [ "$RC" -eq 0 ] && [ ! -s "$OUT" ] && [ ! -s "$ERR" ] && grep 'allow-switch' "$STATE3/factory-events.log" | grep -q 'file:factory-guard-allow=closeout'; echo $? )" "rc=$RC out=$(cat "$OUT") err=$(cat "$ERR") $(tail -2 "$STATE3/factory-events.log")"
rm -f "$STATE3/landing-in-progress.json"
hook Stop "$(stop_payload s-3)"
check "22e a state file deleted by hand → allow, one state-removed line in the events log" "$( [ "$RC" -eq 0 ] && [ "$(grep -c 'state-removed' "$STATE3/factory-events.log")" -eq 1 ]; echo $? )" "rc=$RC $(cat "$STATE3/factory-events.log")"
# reap for real, then the gate is silent
unlink "$W2/.venv"; git -C "$P2" worktree remove "$W2"; git -C "$P2" branch -q -d train/wc; git -C "$P2" push -q origin --delete train/wc
state direct-push "" 0
gate "$T" FACTORY_GUARD_OFFLINE=1 python3 -m scripts.check_landing_closeout --state "$STATE2/landing-in-progress.json" --primary "$P2" --floor-gb 0
check "21j reaped and the remote branch deleted → exit 0, every duty closed" "$( [ "$RC" -eq 0 ] && has "$(cat "$OUT")" 'every lander duty closed'; echo $? )" "rc=$RC out=$(cat "$OUT") err=$(cat "$ERR")"
cp "$STATE2/landing-in-progress.json" "$STATE3/landing-in-progress.json"
hook Stop "$(stop_payload s-4)"
check "22f Stop with every duty closed → silent, state file deleted, closeout event logged" "$( [ "$RC" -eq 0 ] && [ ! -s "$OUT" ] && [ ! -f "$STATE3/landing-in-progress.json" ] && grep -q 'closeout	closeout	lander duties closed' "$STATE3/factory-events.log"; echo $? )" "rc=$RC out=$(cat "$OUT") err=$(cat "$ERR")"

# ---------------------------------------------------------------- case 23: check_choices_protocol
LR="$T/ledger repo"; mkdir -p "$LR/docs/choices"
SHA40="0123456789abcdef0123456789abcdef01234567"
ledger() { cat > "$LR/docs/choices/t.md"; }
gate "$LR" python3 -m scripts.check_choices_protocol t --boarders alpha --at-push
check "23a missing ledger → HARD, exit 1" "$( [ "$RC" -eq 1 ] && has "$(cat "$OUT")" '[HARD] ledger missing'; echo $? )" "rc=$RC out=$(cat "$OUT")"
ledger <<EOF
# Choices ledger — train t (test)

## Lane \`alpha\` — boarded $SHA40 — one sound

**a choice without an id** was made (sound, H).

## Landing

landing mode: pr
pr: 7
receipts: $ART
local-verify: posted
EOF
gate "$LR" python3 -m scripts.check_choices_protocol t --boarders alpha --at-push
check "23b an entry without a stable ID → HARD naming the line" "$( [ "$RC" -eq 1 ] && has "$(cat "$OUT")" '[HARD] entry without a stable ID' && has "$(cat "$OUT")" 'a choice without an id'; echo $? )" "rc=$RC out=$(cat "$OUT")"
ledger <<EOF
# Choices ledger — train t (test)

## Lane \`alpha\` — boarded $SHA40 — one unsound

**alpha-1** The helper was inlined (unsound, L).

## Landing

landing mode: pr
pr: 7
receipts: $ART
local-verify: posted
EOF
gate "$LR" python3 -m scripts.check_choices_protocol t --boarders alpha --at-push
check "23c unsound without a fix note → HARD" "$( [ "$RC" -eq 1 ] && has "$(cat "$OUT")" '[HARD] unsound without a fix note'; echo $? )" "rc=$RC out=$(cat "$OUT")"
ledger <<EOF
# Choices ledger — train t (test)

## Lane \`alpha\` — boarded $SHA40 — one sound

**alpha-1** The helper stays (sound, H). It should work now.

## Landing

landing mode: pr
pr: 7
receipts: $ART
local-verify: posted
EOF
gate "$LR" python3 -m scripts.check_choices_protocol t --boarders alpha --at-push
check "23d a hedge phrase → HARD naming it" "$( [ "$RC" -eq 1 ] && has "$(cat "$OUT")" '[HARD] hedge phrase in the ledger: «should work now»'; echo $? )" "rc=$RC out=$(cat "$OUT")"
ledger <<EOF
# Choices ledger — train t (test)

## Lane \`alpha\` — boarded $SHA40 — one sound

**alpha-1** The helper stays (sound, H).

## Orchestrator choices

**O-1 — single boarder:** single-lane train — priority P1 (test) (sound, H).
EOF
gate "$LR" python3 -m scripts.check_choices_protocol t --boarders alpha
check "23e without --at-push the complete ledger passes (exit 0, 0 findings)" "$( [ "$RC" -eq 0 ] && has "$(cat "$OUT")" '0 finding(s)'; echo $? )" "rc=$RC out=$(cat "$OUT")"
gate "$LR" python3 -m scripts.check_choices_protocol t --boarders alpha --at-push
check "23f --at-push without ## Landing → HARD naming the section" "$( [ "$RC" -eq 1 ] && has "$(cat "$OUT")" '[HARD] missing section «## Landing»'; echo $? )" "rc=$RC out=$(cat "$OUT")"
ledger <<EOF
# Choices ledger — train t (test)

## Lane \`alpha\` — boarded $SHA40 — one sound

**alpha-1** The helper stays (sound, H).

## Orchestrator choices

**O-1 — single boarder:** single-lane train — priority P1 (test) (sound, H).

## Landing

landing mode: direct-push
receipts: $ART
local-verify: skipped (no host)
EOF
gate "$LR" python3 -m scripts.check_choices_protocol t --boarders alpha --at-push
check "23g direct-push against the pr default without an override reason → HARD" "$( [ "$RC" -eq 1 ] && has "$(cat "$OUT")" 'override reason'; echo $? )" "rc=$RC out=$(cat "$OUT")"
gate "$LR" python3 -m scripts.check_choices_protocol t --boarders alpha --at-push --default-mode direct-push
check "23h the same ledger under a declared direct-push default → OK" "$( [ "$RC" -eq 0 ]; echo $? )" "rc=$RC out=$(cat "$OUT")"
gate "$LR" python3 -m scripts.check_choices_protocol t --boarders alpha --at-push --warn
check "23i --warn prints [WARN] and exits 0" "$( [ "$RC" -eq 0 ] && has "$(cat "$OUT")" '[WARN] '; echo $? )" "rc=$RC out=$(cat "$OUT")"
gate "$LR" TRAIN_NAME=t python3 -m scripts.check_choices_protocol --boarders alpha
check "23j the train name comes from TRAIN_NAME when omitted" "$( [ "$RC" -eq 0 ] && has "$(cat "$OUT")" 'ledger t.md'; echo $? )" "rc=$RC out=$(cat "$OUT")"

# ---------------------------------------------------------------- case 24: the drift leg
DR="$T/drift repo"; newrepo "$DR"
mkdir -p "$DR/migrations/versions" "$DR/docs/decisions"
: > "$DR/migrations/versions/0001_x.py"
printf -- '---\nid: ADR-0001\nstatus: Accepted\n---\n# x\n' > "$DR/docs/decisions/0001-first.md"
printf '| kind | number | owner | date | status | note |\n| --- | --- | --- | --- | --- | --- |\n| migration | 0001 | lane/x | 2026-09-06 | claimed | |\n| adr | 0001 | lane/x | 2026-09-06 | claimed | |\n' > "$DR/docs/decisions/NUMBERS.md"
git -C "$DR" add -A; git -C "$DR" commit -q -m 'landed on main'; git -C "$DR" update-ref refs/remotes/origin/main HEAD
gate "$DR" python3 -c 'import pathlib, sys; from scripts import check_migration_heads as m; rows = m.parse_number_registry(pathlib.Path.cwd()); print("\n".join(m.migration_registry_problems(pathlib.Path.cwd()) + m.landed_claim_problems(pathlib.Path.cwd(), rows, "adr", [("0001", pathlib.Path("docs/decisions/0001-first.md"))])))'
check "24a claimed rows whose files are on origin/main → HARD naming both numbers and the flip" "$( has "$(cat "$OUT")" 'claimed migration number 0001 is landed on main; flip the row' && has "$(cat "$OUT")" 'claimed adr number 0001 is landed on main'; echo $? )" "rc=$RC out=$(cat "$OUT") err=$(cat "$ERR")"
git -C "$DR" checkout -q -b lane/new
: > "$DR/migrations/versions/0002_new.py"
printf '| kind | number | owner | date | status | note |\n| --- | --- | --- | --- | --- | --- |\n| migration | 0001 | lane/x | 2026-09-06 | landed | |\n| adr | 0001 | lane/x | 2026-09-06 | landed | |\n| migration | 0002 | lane/new | 2026-09-06 | claimed | |\n' > "$DR/docs/decisions/NUMBERS.md"
git -C "$DR" add -A; git -C "$DR" commit -q -m 'lane claim'
gate "$DR" python3 -c 'import pathlib; from scripts import check_migration_heads as m; print("\n".join(m.migration_registry_problems(pathlib.Path.cwd())))'
check "24b a claim whose file exists only on the lane branch → silent" "$( [ "$RC" -eq 0 ] && [ -z "$(cat "$OUT")" ]; echo $? )" "rc=$RC out=$(cat "$OUT") err=$(cat "$ERR")"

# ---------------------------------------------------------------- case 25: the duplicate-id leg
if python3 -c 'import yaml' 2>/dev/null; then
  gate "$DR" python3 -c 'from scripts.check_backlog import duplicate_row_id_problems as d; print("\n".join(d("| ID | Status |\n|---|---|\n| BL-A-1 | Planned |\n| BL-B-2 | Planned |\n| BL-A-1 | Done |\n")))'
  check "25a two rows with the same id → finding naming both lines" "$( [ "$RC" -eq 0 ] && has "$(cat "$OUT")" 'duplicate backlog row id `BL-A-1` appears 2 times (lines 3, 5)'; echo $? )" "rc=$RC out=$(cat "$OUT") err=$(cat "$ERR")"
  gate "$DR" python3 -c 'from scripts.check_backlog import duplicate_row_id_problems as d; print("\n".join(d("| ID | Status |\n|---|---|\n| BL-A-1 | Planned |\n| BL-B-2 | Planned |\n")))'
  check "25b unique ids → no finding" "$( [ "$RC" -eq 0 ] && [ -z "$(cat "$OUT")" ]; echo $? )" "rc=$RC out=$(cat "$OUT")"
  check "25c the leg is wired into check_backlog's main before the closing-evidence leg" "$( python3 - "$T/scripts/check_backlog.py" <<'EOF'
import pathlib, sys
text = pathlib.Path(sys.argv[1]).read_text(encoding="utf-8")
main = text[text.index("def main("):]
sys.exit(0 if 0 < main.index("duplicate_row_id_problems(") < main.index("closing_evidence(") else 1)
EOF
echo $? )"
else
  skip "25 check_backlog needs PyYAML (check_traceability imports it); not installed here"
fi

# ---------------------------------------------------------------- case 26: check_gate_weakening
GR="$T/weaken repo"; newrepo "$GR"; mkdir -p "$GR/scripts" "$GR/tests"
printf '{"E501": 10}\n' > "$GR/.ruff-baseline.json"
printf 'def main():\n    return 0\n' > "$GR/scripts/check_thing.py"
printf 'from scripts import check_thing\n\ndef test_a():\n    assert check_thing.main() == 0\n    assert True\n' > "$GR/tests/test_thing.py"
git -C "$GR" add -A; git -C "$GR" commit -q -m init; GB="$(git -C "$GR" rev-parse HEAD)"
weaken() { gate "$T" python3 -m scripts.check_gate_weakening --repo-root "$GR" --base "$GB" "$@"; }
git -C "$GR" checkout -q -b c1; printf '{"E501": 12}\n' > "$GR/.ruff-baseline.json"; git -C "$GR" commit -q -am 'chore: tweak baseline'
weaken
check "26a a baseline that grew without an --update commit → WARN naming the volumes, exit 0" "$( [ "$RC" -eq 0 ] && has "$(cat "$OUT")" '[WARN] .ruff-baseline.json: the tolerated volume grew 10 → 12'; echo $? )" "rc=$RC out=$(cat "$OUT") err=$(cat "$ERR")"
weaken --hard
check "26b --hard makes the finding the exit code" "$( [ "$RC" -eq 1 ] && has "$(cat "$OUT")" '[HARD] .ruff-baseline.json'; echo $? )" "rc=$RC out=$(cat "$OUT")"
git -C "$GR" checkout -q -b c1b "$GB"; printf '{"E501": 20}\n' > "$GR/.ruff-baseline.json"; git -C "$GR" commit -q -am 'chore(ruff): regenerate with check_ruff_ratchet --update on a clean primary HEAD'
weaken
check "26c the same growth with an --update commit touching the file → no finding" "$( [ "$RC" -eq 0 ] && ! has "$(cat "$OUT")" '[WARN]'; echo $? )" "rc=$RC out=$(cat "$OUT")"
git -C "$GR" checkout -q -b c2 "$GB"; printf 'def main():\n    return 1\n' > "$GR/scripts/check_thing.py"; git -C "$GR" commit -q -am 'feat: change gate'
weaken
check "26d a gate changed without a test naming it → WARN" "$( [ "$RC" -eq 0 ] && has "$(cat "$OUT")" '[WARN] scripts/check_thing.py changed without a paired test change'; echo $? )" "rc=$RC out=$(cat "$OUT")"
printf 'from scripts import check_thing\n\ndef test_a():\n    assert check_thing.main() == 1\n    assert True\n' > "$GR/tests/test_thing.py"; git -C "$GR" commit -q -am 'test: pair'
weaken
check "26e paired with a changed test naming the gate → no finding" "$( [ "$RC" -eq 0 ] && ! has "$(cat "$OUT")" '[WARN]'; echo $? )" "rc=$RC out=$(cat "$OUT")"
git -C "$GR" checkout -q -b c3 "$GB"; printf 'from scripts import check_thing\n\ndef test_a():\n    check_thing.main()\n' > "$GR/tests/test_thing.py"; git -C "$GR" commit -q -am 'test: drop asserts'
weaken
check "26f a net assert loss under tests/ → WARN with the counts" "$( [ "$RC" -eq 0 ] && has "$(cat "$OUT")" '[WARN] net 2 assert line(s) removed under tests/ (+0/−2; tests/test_thing.py)'; echo $? )" "rc=$RC out=$(cat "$OUT")"
git -C "$GR" checkout -q -b c4 "$GB"; printf '{"E501": 30}\n' > "$GR/.ruff-baseline.json"; git -C "$GR" commit -q -am 'chore: widen

Gate-change: ADR-0001'
weaken --hard
check "26g a Gate-change trailer documents the exception: printed, no finding, exit 0 even under --hard" "$( [ "$RC" -eq 0 ] && has "$(cat "$OUT")" '[INFO] documented exception Gate-change: ADR-0001 (' && ! has "$(cat "$OUT")" '[HARD]'; echo $? )" "rc=$RC out=$(cat "$OUT")"
check "26h no __pycache__ was written into the copied gates or the package" "$( [ -z "$(find "$COPY" "$T/scripts" -name __pycache__ -type d)" ]; echo $? )" "$(find "$COPY" "$T/scripts" -name __pycache__ -type d)"

# ---------------------------------------------------------------- summary
printf '\n# %d passed, %d failed, %d skipped (tmp: %s)\n' "$PASS" "$FAIL" "$SKIP" "$T"
[ "$FAIL" -eq 0 ]
