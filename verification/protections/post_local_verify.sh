#!/bin/sh
# post_local_verify.sh — post the lander's local-verify status on the receipt's HEAD.
#
# The contract is verification/landing-modes.md §2; the mechanism table is
# verification/protections.md §3. One commit status, context `local-verify`, state success,
# description `EXIT=0 run=<run-id>`, posted on the receipt's HEAD= only after a green exit
# receipt for exactly that SHA — never by a lane, never without a receipt, idempotent by
# read-back (no local state file). The default-branch ruleset requires this context on the
# exact commit for both a pull-request merge and a direct push; it is a receipt binding,
# not access control.
#
#   verification/protections/post_local_verify.sh <receipt.exit> [--tree <train worktree>] [--context local-verify]
#
# Exit 0: posted, or already posted (the read-back found context/state success). Exit 1:
# refused or failed, with the exact next command on stderr. Exit 2: usage.
#
# Refuses EXIT≠0 naming the receipt; refuses HEAD= ≠ `git -C <tree> rev-parse HEAD` naming
# both SHAs; needs `gh` on PATH and `gh auth status` (else exit 1 printing the manual
# `gh api …` form); on HTTP 422 (origin does not hold the commit yet) exits 1 naming
# `git push origin HEAD:refs/heads/<current branch>`. Never posts any state but success,
# never rewrites a receipt, never posts LOG=. The run id is the receipt's basename.
set -u

usage() { printf 'usage: %s <receipt.exit> [--tree <dir>] [--context <name>]\n' "$0" >&2; exit 2; }

RECEIPT=""; TREE=""; CONTEXT="local-verify"
while [ $# -gt 0 ]; do
  case "$1" in
    --tree) [ $# -ge 2 ] || usage; TREE="$2"; shift 2 ;;
    --context) [ $# -ge 2 ] || usage; CONTEXT="$2"; shift 2 ;;
    -h|--help) usage ;;
    -*) usage ;;
    *) [ -z "$RECEIPT" ] || usage; RECEIPT="$1"; shift ;;
  esac
done
[ -n "$RECEIPT" ] || usage
[ -f "$RECEIPT" ] || { printf 'post_local_verify: receipt not found: %s\n' "$RECEIPT" >&2; exit 1; }
[ -n "$TREE" ] || TREE="$(pwd)"

# KEY=value receipt lines; the last occurrence wins (harness/train-plan.md §4).
rget() { grep "^$1=" "$RECEIPT" 2>/dev/null | tail -n 1 | cut -d= -f2-; }
EXIT_CODE="$(rget EXIT)"; HEAD_SHA="$(rget HEAD)"; BASE_SHA="$(rget BASE)"
RUN_ID="$(basename "$RECEIPT" .exit)"

if [ "$EXIT_CODE" != "0" ]; then
  printf 'post_local_verify: refused — %s says EXIT=%s, not 0. Fix the red leg and re-verify under the next run id; only a green receipt is posted.\n' "$RECEIPT" "${EXIT_CODE:-?}" >&2
  exit 1
fi
case "$HEAD_SHA" in
  [0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f]*) ;;
  *) printf 'post_local_verify: refused — %s carries no full HEAD= SHA. Re-run the receipt launcher.\n' "$RECEIPT" >&2; exit 1 ;;
esac
TREE_HEAD="$(git -C "$TREE" rev-parse HEAD 2>/dev/null)" || { printf 'post_local_verify: %s is not a git tree (--tree <train worktree>).\n' "$TREE" >&2; exit 1; }
if [ "$TREE_HEAD" != "$HEAD_SHA" ]; then
  printf 'post_local_verify: refused — the receipt is for HEAD=%s but %s is at %s; a receipt binds exactly one commit (harness/train-plan.md §4.1). Fix: re-verify this HEAD under a new run id, or point --tree at the tree that was verified.\n' "$HEAD_SHA" "$TREE" "$TREE_HEAD" >&2
  exit 1
fi
[ -z "$BASE_SHA" ] || git -C "$TREE" merge-base --is-ancestor "$BASE_SHA" "$HEAD_SHA" 2>/dev/null || {
  printf 'post_local_verify: refused — BASE=%s is not an ancestor of HEAD=%s; the receipt verified a tree main has moved away from (verification/lander-duties.md §3).\n' "$BASE_SHA" "$HEAD_SHA" >&2
  exit 1
}

DESCRIPTION="EXIT=0 run=$RUN_ID"
MANUAL="gh api repos/{owner}/{repo}/statuses/$HEAD_SHA -f state=success -f context=$CONTEXT -f description='$DESCRIPTION'"
if ! command -v gh >/dev/null 2>&1; then
  printf 'post_local_verify: gh is not on PATH — install it and log in (gh auth login), then run: %s\n' "$MANUAL" >&2
  exit 1
fi
if ! gh auth status >/dev/null 2>&1; then
  printf 'post_local_verify: gh is not authenticated — run gh auth login, then: %s\n' "$MANUAL" >&2
  exit 1
fi

# Idempotent by read-back: the combined status of the commit already carries the context in
# state success → nothing to post, no second API call is made.
POSTED="$(cd "$TREE" && gh api "repos/{owner}/{repo}/commits/$HEAD_SHA/status" --jq ".statuses[] | select(.context == \"$CONTEXT\" and .state == \"success\") | .context" 2>/dev/null)"
if [ -n "$POSTED" ]; then
  printf 'already posted %s on %s\n' "$CONTEXT" "$(printf '%s' "$HEAD_SHA" | cut -c1-8)"
  exit 0
fi

ERR="$(cd "$TREE" && gh api "repos/{owner}/{repo}/statuses/$HEAD_SHA" -f state=success -f "context=$CONTEXT" -f "description=$DESCRIPTION" 2>&1 >/dev/null)"; RC=$?
if [ "$RC" -ne 0 ]; then
  case "$ERR" in
    *"No commit found"*|*"HTTP 422"*|*" 422"*)
      BRANCH="$(git -C "$TREE" rev-parse --abbrev-ref HEAD 2>/dev/null)"
      printf 'post_local_verify: origin does not hold %s yet (%s). Push the integration branch first: git push origin HEAD:refs/heads/%s — then run this script again.\n' "$HEAD_SHA" "$ERR" "${BRANCH:-<branch>}" >&2
      ;;
    *) printf 'post_local_verify: gh api failed (exit %s): %s. Run by hand: %s\n' "$RC" "$ERR" "$MANUAL" >&2 ;;
  esac
  exit 1
fi
printf 'posted %s on %s (run %s)\n' "$CONTEXT" "$(printf '%s' "$HEAD_SHA" | cut -c1-8)" "$RUN_ID"
exit 0
