#!/usr/bin/env bash
# One local registry for every autonomous lane, evaluation, watch, loop, and server.
# TSV columns: id, kind, owner, started_at, expected_end, stop_cmd, liveness, status.
set -u

die() { printf 'loop_registry: %s\n' "$*" >&2; exit 2; }
now_epoch() { printf '%s' "${LOOP_REGISTRY_NOW:-$(date +%s)}"; }
now_iso() { date -u +%Y-%m-%dT%H:%M:%SZ; }
registry_file() {
  if [ -n "${LOOP_REGISTRY_FILE:-}" ]; then printf '%s' "$LOOP_REGISTRY_FILE"
  elif [ -n "${LANE_SENTINEL_DIR:-}" ]; then printf '%s/loops.tsv' "$LANE_SENTINEL_DIR"
  else die 'set LOOP_REGISTRY_FILE or LANE_SENTINEL_DIR'; fi
}
flat() { case "$1" in *$'\t'*|*$'\n'*) return 1;; esac; return 0; }

write_statuses() { # registry now
  local file="$1" now="$2" tmp="$1.tmp.$$" id kind owner started expected stop live status ref
  [ -f "$file" ] || : > "$file"
  : > "$tmp"
  while IFS=$'\t' read -r id kind owner started expected stop live status; do
    [ -n "$id" ] || continue
    if [ "$status" != finished ]; then
      case "$live" in
        exit_file:*)
          ref="${live#exit_file:}"
          if [ -e "$ref" ]; then status=finished
          elif [ "$expected" != none ] && [ "$expected" -lt "$now" ]; then status=overdue
          else status=active; fi
          ;;
        pid:*)
          ref="${live#pid:}"
          if ! kill -0 "$ref" 2>/dev/null; then status=stale
          elif [ "$expected" != none ] && [ "$expected" -lt "$now" ]; then status=overdue
          else status=active; fi
          ;;
      esac
    fi
    printf '%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\n' "$id" "$kind" "$owner" "$started" "$expected" "$stop" "$live" "$status" >> "$tmp"
  done < "$file"
  mv "$tmp" "$file"
}

cmd_add() {
  [ "$#" -eq 6 ] || die 'usage: add <id> <kind> <owner> <expected-end-epoch|none> <stop-cmd> <pid:N|exit_file:PATH>'
  local file id="$1" kind="$2" owner="$3" expected="$4" stop="$5" live="$6"
  file="$(registry_file)"; mkdir -p "$(dirname "$file")" || die "cannot create registry directory"
  case "$id" in ''|*[!A-Za-z0-9._-]*) die 'id must match [A-Za-z0-9._-]+';; esac
  case "$kind" in lane|eval|watch|loop|serve) ;; *) die 'kind must be lane, eval, watch, loop, or serve';; esac
  case "$expected" in none) ;; ''|*[!0-9]*) die 'expected_end must be an epoch integer or none';; esac
  case "$live" in
    pid:*) case "${live#pid:}" in ''|*[!0-9]*) die 'pid liveness needs a numeric pid';; esac;;
    exit_file:?*) ;;
    *) die 'liveness must be pid:N or exit_file:PATH';;
  esac
  for value in "$id" "$kind" "$owner" "$expected" "$stop" "$live"; do flat "$value" || die 'fields cannot contain tabs or newlines'; done
  [ ! -f "$file" ] || ! awk -F '\t' -v id="$id" '$1==id {found=1} END {exit found ? 0 : 1}' "$file" || die "id already registered: $id"
  printf '%s\t%s\t%s\t%s\t%s\t%s\t%s\tactive\n' "$id" "$kind" "$owner" "$(now_iso)" "$expected" "$stop" "$live" >> "$file"
}

cmd_done() {
  [ "$#" -eq 1 ] || die 'usage: done <id>'
  local file id="$1" tmp found
  file="$(registry_file)"; [ -f "$file" ] || die "registry does not exist: $file"
  tmp="$file.tmp.$$"
  awk -F '\t' -v OFS='\t' -v id="$id" '$1==id {$8="finished"; found=1} {print} END {exit found ? 0 : 3}' "$file" > "$tmp"; found=$?
  if [ "$found" -ne 0 ]; then rm -f "$tmp"; die "id not registered: $id"; fi
  mv "$tmp" "$file"
}

cmd_list() {
  [ "$#" -eq 0 ] || die 'usage: list'
  local file; file="$(registry_file)"; mkdir -p "$(dirname "$file")"
  write_statuses "$file" "$(now_epoch)" || die 'cannot refresh registry'
  cat "$file"
}

cmd_check() {
  [ "$#" -eq 0 ] || die 'usage: check'
  local file; file="$(registry_file)"; mkdir -p "$(dirname "$file")"
  write_statuses "$file" "$(now_epoch)" || die 'cannot refresh registry'
  awk -F '\t' '$8=="overdue" || $8=="stale" {bad=1} END {exit bad ? 1 : 0}' "$file"
}

cmd="${1:-}"; [ "$#" -gt 0 ] && shift
case "$cmd" in
  add) cmd_add "$@";;
  done) cmd_done "$@";;
  list) cmd_list "$@";;
  check) cmd_check "$@";;
  *) die 'usage: loop_registry.sh add|done|list|check ...';;
esac
