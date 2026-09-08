#!/bin/bash
# Fail when a Git-tracked text file contains a Nordic letter outside the
# reviewed exceptions in english-only-allowlist.txt.
set -u

HERE="$(cd "$(dirname "$0")" && pwd -P)"
ROOT="$(cd "$HERE/../.." && pwd -P)"
ALLOWLIST="$HERE/english-only-allowlist.txt"
TAB="$(printf '\t')"
NORDIC_PATTERN="$(printf '\303\246|\303\270|\303\245|\303\206|\303\230|\303\205')"

if [ ! -f "$ALLOWLIST" ]; then
  printf 'english-only: missing allowlist: %s\n' "$ALLOWLIST" >&2
  exit 2
fi

allowlist_error=0
line_number=0
while IFS= read -r line || [ -n "$line" ]; do
  line_number=$((line_number + 1))
  case "$line" in
    ''|'#'*) continue ;;
    *"$TAB"*)
      path="${line%%"$TAB"*}"
      reason="${line#*"$TAB"}"
      case "$path" in
        ''|/*) allowlist_error=1 ;;
      esac
      case "$reason" in
        *[![:space:]]*) ;;
        *) allowlist_error=1 ;;
      esac
      if [ "$allowlist_error" -ne 0 ]; then
        printf 'english-only: invalid allowlist entry at line %s; use <repo-relative path><TAB><reason>\n' "$line_number" >&2
      fi
      ;;
    *)
      allowlist_error=1
      printf 'english-only: invalid allowlist entry at line %s; use <repo-relative path><TAB><reason>\n' "$line_number" >&2
      ;;
  esac
done < "$ALLOWLIST"
[ "$allowlist_error" -eq 0 ] || exit 2

is_allowlisted() {
  wanted="$1"
  while IFS= read -r entry || [ -n "$entry" ]; do
    case "$entry" in
      ''|'#'*) continue ;;
    esac
    listed_path="${entry%%"$TAB"*}"
    [ "$listed_path" = "$wanted" ] && return 0
  done < "$ALLOWLIST"
  return 1
}

findings=0
while IFS= read -r -d '' path; do
  [ -f "$ROOT/$path" ] || continue
  is_allowlisted "$path" && continue
  matches="$(LC_ALL=C grep -nE "$NORDIC_PATTERN" "$ROOT/$path")"
  grep_status=$?
  case "$grep_status" in
    0)
      findings=1
      printf '%s\n' "$matches" | while IFS= read -r match; do
        printf '%s:%s\n' "$path" "$match"
      done
      ;;
    1) ;;
    *)
      printf 'english-only: could not scan %s\n' "$path" >&2
      exit 2
      ;;
  esac
done < <(git -C "$ROOT" ls-files -z -- '*.md' '*.sh' '*.py' '*.yml' '*.yaml' '*.json' '*.example')

if [ "$findings" -ne 0 ]; then
  printf 'english-only: Nordic letters found in tracked text\n' >&2
  exit 1
fi

printf 'english-only: tracked text is clear\n'
