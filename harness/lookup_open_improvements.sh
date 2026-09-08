#!/usr/bin/env bash
# Print open improvement items scoped to one or more planned repository paths.
set -u

die() {
  printf 'lookup_open_improvements: %s\n' "$*" >&2
  exit 2
}

[ "$#" -ge 2 ] || die 'usage: lookup_open_improvements.sh <registry.md> <planned-path>...'
registry="$1"
shift
[ -f "$registry" ] || die "registry does not exist: $registry"

for planned_path in "$@"; do
  case "$planned_path" in
    ./*) planned_path="${planned_path#./}" ;;
  esac
  case "$planned_path" in
    ''|/*|..|../*|*/..|*/../*) die "planned path must be repository-relative: $planned_path" ;;
  esac
done

rows="$(awk '
function trim(value) {
  sub(/^[[:space:]]+/, "", value)
  sub(/[[:space:]]+$/, "", value)
  return value
}
function reject(message) {
  print "lookup_open_improvements: " message > "/dev/stderr"
  bad = 1
}
BEGIN { FS = "\\|" }
$0 == "<!-- open-improvements:start -->" {
  if (started || inside) reject("duplicate registry start marker")
  started = 1
  inside = 1
  next
}
$0 == "<!-- open-improvements:end -->" {
  if (!inside) reject("registry end marker without a start marker")
  inside = 0
  ended = 1
  next
}
inside {
  line = trim($0)
  if (line == "") next
  if (substr(line, 1, 1) != "|" || substr(line, length(line), 1) != "|" || NF != 5) {
    reject("malformed registry row: " $0)
    next
  }
  status = trim($2)
  scope = trim($3)
  item = trim($4)
  if (status == "Status" && scope == "Path glob" && item == "Improvement item") next
  if (status ~ /^-+$/ && scope ~ /^-+$/ && item ~ /^-+$/) next
  if (status != "open" && status != "closed") {
    reject("status must be open or closed: " status)
    next
  }
  if (scope == "" || item == "") {
    reject("path glob and improvement item must be non-empty")
    next
  }
  if (scope ~ /^`.*`$/) scope = substr(scope, 2, length(scope) - 2)
  print status "\t" scope "\t" item
}
END {
  if (!started || !ended || inside) reject("registry markers are missing or unbalanced")
  exit bad ? 3 : 0
}
' "$registry")" || exit $?

matches=''
while IFS="$(printf '\t')" read -r status scope item; do
  [ -n "$status" ] || continue
  case "$scope" in
    ''|/*|..|../*|*/..|*/../*) die "path glob must be repository-relative: $scope" ;;
  esac
  [ "$status" = open ] || continue
  for planned_path in "$@"; do
    case "$planned_path" in
      ./*) planned_path="${planned_path#./}" ;;
    esac
    case "$planned_path" in
      $scope)
        matches="${matches}${item}
"
        break
        ;;
    esac
  done
done <<EOF
$rows
EOF

printf '%s' "$matches" | awk 'NF && !seen[$0]++'
