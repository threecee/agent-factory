#!/bin/sh
# test_hub_pointers.sh — every `<pillar>/<file> §N` pointer in the hub files resolves.
#
# The README and INSTALL are hubs: pointers plus one-sentence glosses, no rule of
# their own. A pointer that names a file that is not there, or a section that does
# not exist, is the hub's only way of being wrong — so it is tested like a gate
# (verification/falsification.md rule 5: teeth are proven by planting).
#
# What is read: every backticked `<pillar>/<path>` whose first segment is one of
# planning | verification | interpretation | harness | skills | user-level (an
# optional `bash `/`sh `/`python3 ` prefix inside the backticks is ignored), with
# an optional ` §N` or ` §N.M` right after the closing backtick or inside it. The
# file must exist; when a section is cited the file must carry a heading numbered
# N (`## N.`, `### N.M`, `## §N`). Files with unnumbered sections are
# therefore cited section-less — a `§` into one of them is a finding, by
# design; a numbered RULE in a list (`falsification.md` rule 7) is cited as
# "rule 7", never as `§7`.
#
# Modes:
#   hub  (default)  README.md and INSTALL.md at the root; pointers are root-relative
#   --tree          every *.md under the root; a `../` pointer resolves from the
#                   file's own directory, a bare pillar pointer from the root
#   --installed     adds the placeholder leg: any `{{…}}` residue in a scanned
#                   file is a finding (an installed doc tree has resolved them all;
#                   the package itself carries them on purpose, so never pass this
#                   flag against the package)
#
# Cases (exit 0 = all hold):
#   1 the package hub is green (0 findings)
#   2 a planted dead path is red, naming the path and the hub file
#   3 a planted wrong §-number is red, naming the section and the hub file
#   4 INSTALL's stated counts equal the tree (gate scripts under
#     verification/gates, locked skills in skills/skills-lock.json)
#   5 `--installed` on a scratch tree with a planted {{PLACEHOLDER}} is red naming
#     it; the same tree without the flag is green
#   6 `--tree` on a scratch tree resolves a `../pillar/file.md §N` pointer from the
#     citing file's directory (green), and a dead one is red
#
# Run:  sh verification/tests/test_hub_pointers.sh
#       sh verification/tests/test_hub_pointers.sh --check [--tree] [--installed] [<root>]
#         (the check alone: prints one finding per line, exit 1 on any)
set -u
SELF="$(cd "$(dirname "$0")" && pwd -P)/$(basename "$0")"
HERE="$(cd "$(dirname "$0")/../.." && pwd -P)"
PILLARS='planning|verification|interpretation|harness|skills|user-level'

# scan <root> <mode:hub|tree> <installed:0|1> — one finding per line on stdout
scan() {
  root="$1"; mode="$2"; installed="$3"
  if [ "$mode" = tree ]; then
    files="$(find "$root" -name '*.md' -not -path '*/node_modules/*' -not -path '*/.git/*' | LC_ALL=C sort)"
  else
    files="$root/README.md
$root/INSTALL.md"
  fi
  printf '%s\n' "$files" | while IFS= read -r f; do
    [ -n "$f" ] || continue
    if [ ! -f "$f" ]; then printf 'MISSING-HUB %s\n' "$f"; continue; fi
    dir="$(dirname "$f")"
    grep -oE '`(bash |sh |python3 )?(\.\./)*[a-z-]+/[A-Za-z0-9_./-]+( §[0-9][0-9.]*)?`( §[0-9][0-9.]*)?' "$f" | while IFS= read -r tok; do
      inner="${tok#\`}"
      path="${inner%%\`*}"
      rest="${inner#*\`}"
      section="${rest# §}"
      [ "$rest" = "$section" ] && section=""
      case "$path" in
        "bash "*) path="${path#bash }";;
        "sh "*) path="${path#sh }";;
        "python3 "*) path="${path#python3 }";;
      esac
      # a `§N` may also stand inside the backticks: `pillar/file.md §N`
      case "$path" in *" §"*) section="${path##* §}"; path="${path%% §*}";; esac
      base="$root"; rel="$path"
      case "$rel" in ../*) base="$dir";; esac
      first="${rel#"${rel%%[!./]*}"}"; first="${first%%/*}"
      case "$first" in planning|verification|interpretation|harness|skills|user-level) ;; *) continue;; esac
      target="$base/$rel"
      if [ ! -e "$target" ]; then printf 'DEAD %s: %s\n' "$f" "$path"; continue; fi
      if [ -n "$section" ]; then
        section="${section%.}"
        esc="$(printf '%s' "$section" | sed 's/\./\\./g')"
        if ! grep -Eq "^#{1,4} (§)?${esc}([. ]|$)" "$target"; then
          printf 'NOSECTION %s: %s §%s\n' "$f" "$path" "$section"
        fi
      fi
    done
    if [ "$installed" = 1 ]; then
      grep -n '{{[A-Za-z_][A-Za-z0-9_]*}}' "$f" | sed "s|^|PLACEHOLDER $f:|"
    fi
  done
}

if [ "${1:-}" = "--check" ]; then
  shift; mode=hub; installed=0; root="$HERE"
  for a in "$@"; do
    case "$a" in --tree) mode=tree;; --installed) installed=1;; *) root="$a";; esac
  done
  out="$(scan "$root" "$mode" "$installed")"
  [ -z "$out" ] && exit 0
  printf '%s\n' "$out"; exit 1
fi

# ---- self-test on a throwaway copy (the package tree is never touched) ----
T="$(mktemp -d "${TMPDIR:-/tmp}/hub pointers.XXXXXX")"
trap 'rm -rf "$T"' EXIT
mkdir -p "$T/pkg"
for d in planning verification interpretation harness skills user-level; do cp -R "$HERE/$d" "$T/pkg/$d"; done
cp "$HERE/README.md" "$HERE/INSTALL.md" "$T/pkg/"
fail=0
check() { # label expected actual
  if [ "$2" = "$3" ]; then printf 'ok   %s\n' "$1"; else printf 'FAIL %s (expected %s, got %s)\n' "$1" "$2" "$3"; fail=1; fi
}
run() { env -i PATH="$PATH" HOME="${HOME:-/}" TMPDIR="${TMPDIR:-/tmp}" sh "$SELF" --check "$@"; }
count() { grep -c . || true; }

out="$(run "$T/pkg" 2>&1)"; code=$?
check "1 package hub is green" 0 "$code"
[ -n "$out" ] && printf '%s\n' "$out" | sed 's/^/     /'

printf '\nplanted: `planning/no-such-file.md §1`\n' >> "$T/pkg/README.md"
out="$(run "$T/pkg" 2>&1)"; code=$?
check "2 planted dead path is red" 1 "$code"
check "2b exactly one finding" 1 "$(printf '%s\n' "$out" | count)"
printf '%s' "$out" | grep -q "DEAD .*README.md: planning/no-such-file.md" && echo "ok   2c the finding names the path and the hub file" || { echo "FAIL 2c message: $out"; fail=1; }
cp "$HERE/README.md" "$T/pkg/README.md"

printf '\nplanted: `planning/execution-contract.md §99`\n' >> "$T/pkg/README.md"
out="$(run "$T/pkg" 2>&1)"; code=$?
check "3 planted wrong section is red" 1 "$code"
check "3b exactly one finding" 1 "$(printf '%s\n' "$out" | count)"
printf '%s' "$out" | grep -q "NOSECTION .*README.md: planning/execution-contract.md §99" && echo "ok   3c the finding names the section and the hub file" || { echo "FAIL 3c message: $out"; fail=1; }
cp "$HERE/README.md" "$T/pkg/README.md"

stated_gates="$(sed -n 's/.*Of the \([0-9][0-9]*\) scripts.*/\1/p' "$HERE/INSTALL.md" | head -1)"
actual_gates="$(ls "$HERE"/verification/gates/*.py | count)"
check "4 INSTALL's gate-script count (${stated_gates:-none stated}) equals verification/gates" "$actual_gates" "${stated_gates:-none}"
stated_skills="$(sed -n 's/.*verified: \([0-9][0-9]*\) skill(s).*/\1/p' "$HERE/INSTALL.md" | head -1)"
actual_skills="$(python3 -c 'import json,sys;print(len(json.load(open(sys.argv[1]))["skills"]))' "$HERE/skills/skills-lock.json")"
check "4b INSTALL's locked-skill count (${stated_skills:-none stated}) equals the lock" "$actual_skills" "${stated_skills:-none}"

mkdir -p "$T/inst/planning" "$T/inst/harness"
printf '# a\n\nSee `../harness/b.md §2`.\n' > "$T/inst/planning/a.md"
printf '# b\n\n## 1. One\n\n## 2. Two\n' > "$T/inst/harness/b.md"
out="$(run --tree "$T/inst" 2>&1)"; code=$?
check "6 --tree resolves a ../pillar pointer from the citing file's directory" 0 "$code"
printf '\nSee `../harness/gone.md`.\n' >> "$T/inst/planning/a.md"
out="$(run --tree "$T/inst" 2>&1)"; code=$?
check "6b --tree: a dead ../pillar pointer is red" 1 "$code"
printf '%s' "$out" | grep -q "DEAD .*planning/a.md: ../harness/gone.md" && echo "ok   6c the finding names the dead path" || { echo "FAIL 6c message: $out"; fail=1; }
printf '# a\n\nSee `../harness/b.md §2`.\n' > "$T/inst/planning/a.md"

printf '\n{{ZZ_PLANTED}}\n' >> "$T/inst/harness/b.md"
out="$(run --tree "$T/inst" 2>&1)"; code=$?
check "5 a {{PLACEHOLDER}} is green without --installed" 0 "$code"
out="$(run --tree --installed "$T/inst" 2>&1)"; code=$?
check "5b --installed makes the planted placeholder red" 1 "$code"
printf '%s' "$out" | grep -q "PLACEHOLDER .*harness/b.md:.*{{ZZ_PLANTED}}" && echo "ok   5c the finding names the placeholder and the file" || { echo "FAIL 5c message: $out"; fail=1; }

exit $fail
