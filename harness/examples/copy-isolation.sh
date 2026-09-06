#!/bin/sh
# Worked example for harness/artifact-bank.md §3: two copies of one banked
# source are hash-identical yet NOT isolated, because the source records a
# file reference that points outside the bank. The check refuses the copy
# (red), the reference is relocated into the copy, the check accepts (green),
# and the other copy is shown untouched. POSIX sh, no product code.
#
# Usage: sh harness/examples/copy-isolation.sh
# Exit 0 when the red→green sequence behaves as documented, 1 otherwise.
set -eu
work="$(mktemp -d)"
trap 'rm -rf "$work"' EXIT

# --- a toy "product": one instance whose state records where its data lives.
mkdir -p "$work/scratch/corpus" "$work/bank/source/instance"
printf 'term-1\n' > "$work/scratch/corpus/lexicon.txt"
: > "$work/bank/source/instance/data.db"
printf '{"db": "instance/data.db", "corpus_dir": "%s"}\n' \
  "$work/scratch/corpus" > "$work/bank/source/instance/state.json"
source_hash="$(shasum -a 256 "$work/bank/source/instance/state.json" | cut -d' ' -f1)"

# --- two handover copies of the same source.
cp -R "$work/bank/source" "$work/copy-A"
cp -R "$work/bank/source" "$work/copy-B"
echo "-- manifest parity: identical bytes in both copies"
( cd "$work" && shasum -a 256 copy-A/instance/state.json copy-B/instance/state.json )

# --- the isolation check: every absolute path a copy records must resolve
# INSIDE that copy. Adapt the extraction line to wherever YOUR product
# records paths (config, database rows, manifest); keep the verdict.
recorded_paths() {  # $1 = copy root
  grep -oh '"[a-z_]*": *"/[^"]*"' "$1"/instance/*.json | cut -d'"' -f4
}
check_isolation() {  # $1 = copy root; prints one line per reference, then a verdict
  root="$(cd "$1" && pwd -P)"
  recorded_paths "$root" | while IFS= read -r p; do
    real="$(cd "$p" 2>/dev/null && pwd -P || printf '%s' "$p")"
    case "$real/" in
      "$root"/*) printf 'inside   %s\n' "$p" ;;
      *)         printf 'OUTSIDE  %s\n' "$p" ;;
    esac
  done > "$root.isolation-report"
  cat "$root.isolation-report"
  n="$(grep -c '^OUTSIDE' "$root.isolation-report" || true)"
  if [ "$n" -eq 0 ]; then echo "ACCEPT: isolated"; return 0; fi
  echo "REFUSE: $n reference(s) resolve outside $root"; return 1
}

echo "-- isolation check on copy A (expected: REFUSE)"
if check_isolation "$work/copy-A"; then
  echo "example broken: shared reference was not detected"; exit 1
fi

# --- what sharing does: A "learns" a term through its normal write path,
# and B — never written to — now reads it.
corpus_A="$(recorded_paths "$work/copy-A" | head -n 1)"
printf 'term-learned-by-A\n' >> "$corpus_A/lexicon.txt"
echo "-- copy B reads (expected: A's term leaked in):"
cat "$(recorded_paths "$work/copy-B" | head -n 1)/lexicon.txt"

# --- a symlink is NOT a fix: it resolves to the same shared directory and
# the check must still refuse (this is the check's own falsification).
ln -s "$work/scratch/corpus" "$work/copy-A/instance/corpus"
printf '{"db": "instance/data.db", "corpus_dir": "%s"}\n' \
  "$work/copy-A/instance/corpus" > "$work/copy-A/instance/state.json"
echo "-- isolation check on copy A with a symlinked corpus (expected: REFUSE)"
if check_isolation "$work/copy-A"; then
  echo "example broken: symlinked reference was accepted"; exit 1
fi
rm "$work/copy-A/instance/corpus"

# --- the fix: relocate the reference INTO the copy (copy the data, rewrite
# the pointer), then re-check.
mkdir -p "$work/copy-A/instance/corpus"
cp "$work/scratch/corpus/lexicon.txt" "$work/copy-A/instance/corpus/"
printf '{"db": "instance/data.db", "corpus_dir": "%s"}\n' \
  "$work/copy-A/instance/corpus" > "$work/copy-A/instance/state.json"
echo "-- isolation check on copy A after relocation (expected: ACCEPT)"
check_isolation "$work/copy-A" || { echo "example broken: relocated copy refused"; exit 1; }

# --- the source stayed untouched throughout (hash before == hash after).
after_hash="$(shasum -a 256 "$work/bank/source/instance/state.json" | cut -d' ' -f1)"
[ "$source_hash" = "$after_hash" ] || { echo "example broken: source changed"; exit 1; }
echo "-- source unchanged: $source_hash"
echo "OK: red (shared) -> red (symlinked) -> green (relocated), source untouched"
