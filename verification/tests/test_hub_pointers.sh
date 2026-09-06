#!/bin/sh
# test_hub_pointers.sh — every `<pillar>/<file> §N` pointer in the hub files resolves.
#
# The README and INSTALL are hubs: pointers plus one-sentence glosses, no rule of
# their own. A pointer that names a file that is not there, or a section that does
# not exist, is the hub's only way of being wrong — so it is tested like a gate
# (verification/falsification.md rule 5: teeth are proven by planting).
#
# What is read — each file is read one PARAGRAPH at a time (blank-line separated,
# whitespace squeezed), so a pointer wrapped across a line break is one token:
#   * every backticked `<pillar>/<path>` whose first segment is one of
#     planning | verification | interpretation | harness | skills | user-level (an
#     optional `bash `/`sh `/`python3 ` prefix inside the backticks is ignored),
#     with an optional ` §N` or ` §N.M` right after the closing backtick or inside
#     it. The file must exist; when a section is cited the file must carry a
#     heading numbered N (`## N.`, `### N.M`, `## §N`). Files with unnumbered
#     sections are therefore cited section-less — a `§` into one of them is a
#     finding, by design; a numbered RULE in a list (`falsification.md` rule 7)
#     is cited as "rule 7", never as `§7`;
#   * a standalone `§N` (the continuation form `` `pillar/file.md §1`, `§7` `` and
#     the range form `` `§1`–`§4` ``) binds to the LAST pillar path named in the
#     same paragraph and is checked against that file; one with no path before
#     it in its paragraph is a finding (UNBOUND);
#   * a quoted heading right after a path — `` `pillar/file.md` "Statuses" ``,
#     also with a comma or a `§` before the quote, and a `, "Second"` list — must
#     open a heading line (`## Statuses …`) or a bold lead (`**Statuses.**` at
#     the start of a paragraph, a list item or a table row) in that file; the
#     quoted text starts with a capital.
# Every pointer read counts; the check prints `pointers=<n> sections=<m>` on
# stderr, and the self-test holds the hub count above a floor so a regex that
# matches nothing cannot pass silently (the non-vacuity check).
#
# Modes:
#   hub  (default)  README.md and INSTALL.md at the root; pointers are root-relative
#   --tree          every *.md under the root except `<root>/skills/` (the locked
#                   skill set is upstream text under its own lock test); a `../`
#                   pointer resolves from the file's own directory, a bare pillar
#                   pointer from the root
#   --skills <dir>  where the `skills` pillar resolves (default `<root>/skills`);
#                   an installed repo passes the directory INSTALL step 4 filled
#                   (`.agents/skills`), since the doc root carries no skills/
#   --installed     adds the placeholder leg over `<root>/planning/` — the one
#                   directory the installer resolves (INSTALL step 1.1): any
#                   `{{…}}` residue there is a finding. The other pillars keep
#                   their parameter names by design (`harness/bulk-read-contract.md`
#                   §4 and the bulk-read skills name `{{PARAM}}` rows), so a
#                   faithful copy of the chapters is green under this flag; case 8
#                   asserts exactly that on the package's own tree with
#                   `planning/` resolved.
#
# Cases (exit 0 = all hold):
#   1 the package hub is green (0 findings); 1b it read at least the floor of
#     pointers (non-vacuity)
#   2 a planted dead path is red, naming the path and the hub file
#   3 a planted wrong §-number is red, naming the section and the hub file;
#     3d a planted `, `§99`` continuation is red naming §99 and the path it bound
#     to; 3e a pointer wrapped across a line break is read whole (red on §99);
#     3f a planted quoted heading that no heading line opens is red naming it
#   4 INSTALL's stated counts equal the tree (gate scripts under
#     verification/gates, locked skills in skills/skills-lock.json)
#   5 `--installed` on a scratch tree with a planted {{PLACEHOLDER}} under
#     planning/ is red naming it; the same tree without the flag is green; a
#     placeholder outside planning/ is not a finding (the documented scope)
#   6 `--tree` on a scratch tree resolves a `../pillar/file.md §N` pointer from the
#     citing file's directory (green), and a dead one is red
#   7 `--tree` on the package itself is green (every chapter pointer resolves;
#     skills/ excluded by the mode)
#   8 `--tree --installed` over a copy of the package's chapter tree with the
#     planning/ placeholders resolved, `--skills` pointing at the skill set kept
#     elsewhere, is green — the INSTALL step 7.3 run
#
# Run:  sh verification/tests/test_hub_pointers.sh
#       sh verification/tests/test_hub_pointers.sh --check [--tree] [--installed] [--skills <dir>] [<root>]
#         (the check alone: prints one finding per line on stdout, exit 1 on any;
#          `pointers=<n> sections=<m>` on stderr)
set -u
SELF="$(cd "$(dirname "$0")" && pwd -P)/$(basename "$0")"
HERE="$(cd "$(dirname "$0")/../.." && pwd -P)"
PILLARS='planning|verification|interpretation|harness|skills|user-level'
POINTER_FLOOR=250

# paragraphs <file> — one line per paragraph, whitespace squeezed
paragraphs() { awk 'BEGIN{RS="";ORS="\n"}{gsub(/[ \t\n]+/," ");print}' "$1"; }

# scan <root> <mode:hub|tree> <installed:0|1> <skills dir> — one finding per line
# on stdout, plus one `COUNT pointer` / `COUNT section` line per pointer read
# (the caller separates and sums them). A pointer into the `skills` pillar
# resolves under <skills dir> (default `<root>/skills`), because an installed
# repo keeps the locked skill set where INSTALL step 4 puts it, not under the
# doc root.
scan() {
  root="${1%/}"; mode="$2"; installed="$3"; skills="${4%/}"
  if [ "$mode" = tree ]; then
    files="$(find "$root" -name '*.md' -not -path '*/node_modules/*' -not -path '*/.git/*' -not -path "$root/skills/*" | LC_ALL=C sort)"
  else
    files="$root/README.md
$root/INSTALL.md"
  fi
  printf '%s\n' "$files" | while IFS= read -r f; do
    [ -n "$f" ] || continue
    if [ ! -f "$f" ]; then printf 'MISSING-HUB %s\n' "$f"; continue; fi
    dir="$(dirname "$f")"
    paragraphs "$f" | while IFS= read -r para; do
      last=""; lastbase=""
      printf '%s\n' "$para" | grep -oE '`(bash |sh |python3 )?(\.\./)*[a-z-]+/[A-Za-z0-9_./-]+( §[0-9][0-9.]*)?`( §[0-9][0-9.]*)?(,? (§)?"[A-Z][^"`]+")*|`§[0-9][0-9.]*`' | while IFS= read -r tok; do
        case "$tok" in
          '`§'*)  # a continuation: bind to the last pillar path in this paragraph
            section="${tok#\`§}"; section="${section%\`}"
            if [ -z "$last" ]; then printf 'UNBOUND %s: `§%s` with no path before it in its paragraph\n' "$f" "$section"; continue; fi
            path="$last"; target="$lastbase/$last"; headings=""
            ;;
          *)
            inner="${tok#\`}"
            path="${inner%%\`*}"
            rest="${inner#*\`}"
            section=""
            case "$rest" in " §"[0-9]*) section="${rest# §}"; section="${section%%[!0-9.]*}";; esac
            headings="$(printf '%s' "$rest" | grep -oE '"[A-Z][^"`]+"' | tr -d '"')"
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
            case "$first" in planning|verification|interpretation|harness|user-level) ;; skills) base="${skills%/skills}"; rel="skills/${rel#*skills/}";; *) last=""; continue;; esac
            last="$rel"; lastbase="$base"
            target="$base/$rel"
            ;;
        esac
        printf 'COUNT pointer\n'
        if [ ! -e "$target" ]; then printf 'DEAD %s: %s\n' "$f" "$path"; continue; fi
        if [ -n "$section" ]; then
          printf 'COUNT section\n'
          section="${section%.}"
          esc="$(printf '%s' "$section" | sed 's/\./\\./g')"
          if ! grep -Eq "^#{1,4} (§)?${esc}([. ]|$)" "$target"; then
            printf 'NOSECTION %s: %s §%s\n' "$f" "$path" "$section"
          fi
        fi
        if [ -n "$headings" ]; then
          printf '%s\n' "$headings" | while IFS= read -r h; do
            [ -n "$h" ] || continue
            printf 'COUNT section\n'
            if ! grep -E '^(#{1,4} |[ ]*([-*]|[0-9]+\.)[ ]+\*\*|\*\*|\|[ ]*\*\*)' "$target" | grep -qF -- "$h"; then
              printf 'NOHEADING %s: %s "%s"\n' "$f" "$path" "$h"
            fi
          done
        fi
      done
    done
    if [ "$installed" = 1 ]; then
      case "$f" in "$root/planning/"*)
        grep -n '{{[A-Za-z_][A-Za-z0-9_]*}}' "$f" | sed "s|^|PLACEHOLDER $f:|";;
      esac
    fi
  done
}

if [ "${1:-}" = "--check" ]; then
  shift; mode=hub; installed=0; root="$HERE"; skills=""
  while [ $# -gt 0 ]; do
    case "$1" in --tree) mode=tree;; --installed) installed=1;; --skills) shift; skills="$1";; *) root="$1";; esac
    shift
  done
  [ -n "$skills" ] || skills="${root%/}/skills"
  raw="$(scan "$root" "$mode" "$installed" "$skills")"
  pointers="$(printf '%s\n' "$raw" | grep -c '^COUNT pointer$' || true)"
  sections="$(printf '%s\n' "$raw" | grep -c '^COUNT section$' || true)"
  printf 'pointers=%s sections=%s\n' "$pointers" "$sections" >&2
  out="$(printf '%s\n' "$raw" | grep -v '^COUNT ' || true)"
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
# findings on stdout (captured by the caller); the count line lands in $T/err
run() { env -i PATH="$PATH" HOME="${HOME:-/}" TMPDIR="${TMPDIR:-/tmp}" sh "$SELF" --check "$@" 2>"$T/err"; }
count() { grep -c . || true; }

out="$(run "$T/pkg")"; code=$?
check "1 package hub is green" 0 "$code"
[ -n "$out" ] && printf '%s\n' "$out" | sed 's/^/     /'
read_pointers="$(sed -n 's/^pointers=\([0-9]*\) .*/\1/p' "$T/err")"
if [ "${read_pointers:-0}" -ge "$POINTER_FLOOR" ]; then echo "ok   1b the hub scan read $read_pointers pointers (floor $POINTER_FLOOR; $(cat "$T/err"))"; else echo "FAIL 1b the hub scan read only ${read_pointers:-0} pointers (floor $POINTER_FLOOR) — the regex matches too little"; fail=1; fi

printf '\nplanted: `planning/no-such-file.md §1`\n' >> "$T/pkg/README.md"
out="$(run "$T/pkg")"; code=$?
check "2 planted dead path is red" 1 "$code"
check "2b exactly one finding" 1 "$(printf '%s\n' "$out" | count)"
printf '%s' "$out" | grep -q "DEAD .*README.md: planning/no-such-file.md" && echo "ok   2c the finding names the path and the hub file" || { echo "FAIL 2c message: $out"; fail=1; }
cp "$HERE/README.md" "$T/pkg/README.md"

printf '\nplanted: `planning/execution-contract.md §99`\n' >> "$T/pkg/README.md"
out="$(run "$T/pkg")"; code=$?
check "3 planted wrong section is red" 1 "$code"
check "3b exactly one finding" 1 "$(printf '%s\n' "$out" | count)"
printf '%s' "$out" | grep -q "NOSECTION .*README.md: planning/execution-contract.md §99" && echo "ok   3c the finding names the section and the hub file" || { echo "FAIL 3c message: $out"; fail=1; }
cp "$HERE/README.md" "$T/pkg/README.md"

printf '\nplanted: `planning/execution-contract.md §1`, `§99`\n' >> "$T/pkg/README.md"
out="$(run "$T/pkg")"; code=$?
check "3d a planted \`, \`§99\`\` continuation is red" 1 "$code"
printf '%s' "$out" | grep -q "NOSECTION .*README.md: planning/execution-contract.md §99" && echo "ok   3d2 the continuation bound to the last path in its paragraph" || { echo "FAIL 3d2 message: $out"; fail=1; }
cp "$HERE/README.md" "$T/pkg/README.md"

printf '\nplanted: a pointer wrapped across a line (`planning/execution-contract.md\n§99`).\n' >> "$T/pkg/README.md"
out="$(run "$T/pkg")"; code=$?
check "3e a pointer wrapped across a line break is read whole (red on §99)" 1 "$code"
printf '%s' "$out" | grep -q "NOSECTION .*README.md: planning/execution-contract.md §99" && echo "ok   3e2 the finding names the wrapped pointer" || { echo "FAIL 3e2 message: $out"; fail=1; }
cp "$HERE/README.md" "$T/pkg/README.md"

printf '\nplanted: `planning/board-protocol.md` "No Such Heading"\n' >> "$T/pkg/README.md"
out="$(run "$T/pkg")"; code=$?
check "3f a planted quoted heading is red" 1 "$code"
printf '%s' "$out" | grep -q 'NOHEADING .*README.md: planning/board-protocol.md "No Such Heading"' && echo "ok   3f2 the finding names the heading and the file" || { echo "FAIL 3f2 message: $out"; fail=1; }
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
out="$(run --tree "$T/inst")"; code=$?
check "6 --tree resolves a ../pillar pointer from the citing file's directory" 0 "$code"
printf '\nSee `../harness/gone.md`.\n' >> "$T/inst/planning/a.md"
out="$(run --tree "$T/inst")"; code=$?
check "6b --tree: a dead ../pillar pointer is red" 1 "$code"
printf '%s' "$out" | grep -q "DEAD .*planning/a.md: ../harness/gone.md" && echo "ok   6c the finding names the dead path" || { echo "FAIL 6c message: $out"; fail=1; }
printf '# a\n\nSee `../harness/b.md §2`.\n' > "$T/inst/planning/a.md"

printf '\n{{ZZ_PLANTED}}\n' >> "$T/inst/planning/a.md"
printf '\n{{ZZ_OUTSIDE}}\n' >> "$T/inst/harness/b.md"
out="$(run --tree "$T/inst")"; code=$?
check "5 a {{PLACEHOLDER}} is green without --installed" 0 "$code"
out="$(run --tree --installed "$T/inst")"; code=$?
check "5b --installed makes the planted placeholder under planning/ red" 1 "$code"
printf '%s' "$out" | grep -q "PLACEHOLDER .*planning/a.md:.*{{ZZ_PLANTED}}" && echo "ok   5c the finding names the placeholder and the file" || { echo "FAIL 5c message: $out"; fail=1; }
check "5d a placeholder outside planning/ is not a finding (the documented scope)" 1 "$(printf '%s\n' "$out" | count)"

out="$(run --tree "$HERE")"; code=$?
check "7 --tree on the package itself is green (skills/ excluded by the mode)" 0 "$code"
[ -n "$out" ] && printf '%s\n' "$out" | sed 's/^/     /'

mkdir -p "$T/copy"
for d in planning verification interpretation harness user-level; do cp -R "$HERE/$d" "$T/copy/$d"; done
for f in "$T"/copy/planning/*.md; do
  sed 's/{{[A-Za-z_][A-Za-z0-9_]*}}/resolved-by-the-installer/g' "$f" > "$f.tmp" && mv "$f.tmp" "$f"
done
out="$(run --tree --installed "$T/copy" --skills "$HERE/skills")"; code=$?
check "8 --tree --installed over the chapter tree with planning/ resolved (--skills elsewhere) is green (INSTALL step 7.3)" 0 "$code"
[ -n "$out" ] && printf '%s\n' "$out" | sed 's/^/     /'

exit $fail
