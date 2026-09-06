#!/bin/sh
# ci_signal.sh — the session-start CI signal (verification/protections.md §4, mechanism M-12).
#
#   verification/protections/ci_signal.sh [--workflow verify.yml] [--branch main]
#
# The branch defaults to FACTORY_GUARD_DEFAULT_BRANCH (the §8 parameter the landing rule, the
# hooks and the close-out gate read), else main; the reminders script passes the same value.
# Prints nothing and exits 0 when `gh` is missing or `gh auth status` fails (offline is
# silent). Otherwise, line 1 is the last conclusion of the workflow on the default branch:
#   CI main: GREEN (<run id>, <sha8>)
#   CI main: RED <conclusion> (<run id>, <sha8>; <failing job names>) — a red X is three different
#     things (cancellation, zero-job fault, real failure): read gh run view <id> --log-failed before reporting
# Line 2 only when any exist — one line per open pull request whose head ref starts with train/:
#   Open trains: #<n> train/<name> head <sha8> local-verify=posted|missing verify=<conclusion|none>
# A signal, never a verdict: it suggests no merge and no push. The harness reminders script
# calls it at session start when it is executable (harness/guards.md §9, CI row).
set -u

WORKFLOW="verify.yml"; BRANCH="${FACTORY_GUARD_DEFAULT_BRANCH:-main}"
while [ $# -gt 0 ]; do
  case "$1" in
    --workflow) [ $# -ge 2 ] || exit 2; WORKFLOW="$2"; shift 2 ;;
    --branch) [ $# -ge 2 ] || exit 2; BRANCH="$2"; shift 2 ;;
    *) printf 'usage: %s [--workflow <file>] [--branch <name>]\n' "$0" >&2; exit 2 ;;
  esac
done

command -v gh >/dev/null 2>&1 || exit 0
gh auth status >/dev/null 2>&1 || exit 0

RUN=$(gh run list --workflow "$WORKFLOW" --branch "$BRANCH" --limit 1 --json databaseId,conclusion,headSha --jq '.[0] | "\(.databaseId) \(.conclusion) \(.headSha)"' 2>/dev/null)
if [ -n "$RUN" ]; then
  set -- $RUN
  ID=${1:-}; CONCLUSION=${2:-}; SHA=$(printf '%s' "${3:-}" | cut -c1-8)
  case "$CONCLUSION" in
    success) printf 'CI %s: GREEN (%s, %s)\n' "$BRANCH" "$ID" "$SHA" ;;
    ""|null) ;;
    *)
      JOBS=$(gh run view "$ID" --json jobs --jq '[.jobs[] | select(.conclusion == "failure") | .name] | join("; ")' 2>/dev/null)
      printf 'CI %s: RED %s (%s, %s%s) — a red X is three different things (cancellation, zero-job fault, real failure): read gh run view %s --log-failed before reporting\n' "$BRANCH" "$CONCLUSION" "$ID" "$SHA" "${JOBS:+; $JOBS}" "$ID"
      ;;
  esac
fi

TRAINS=$(gh pr list --state open --json number,headRefName,headRefOid,statusCheckRollup --jq '
  [ .[] | select(.headRefName | startswith("train/")) ]
  | map(
      "#\(.number) \(.headRefName) head \(.headRefOid[0:8]) local-verify="
      + (if ([.statusCheckRollup[]? | select((.context? // .name? // "") == "local-verify" and ((.state? // .conclusion? // "") | ascii_upcase) == "SUCCESS")] | length) > 0 then "posted" else "missing" end)
      + " verify="
      + (([.statusCheckRollup[]? | select((.name? // .context? // "") == "verify")] | .[0].conclusion? // .[0].state? // "none") | ascii_downcase)
    )
  | join("; ")' 2>/dev/null)
[ -n "$TRAINS" ] && printf 'Open trains: %s\n' "$TRAINS"
exit 0
