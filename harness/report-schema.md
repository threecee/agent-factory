# Report schema (every lane, no matter how it exits)

The report is the lane's handback: terse YAML front matter that the wrapper,
the choices audit and the lander read. It carries what the execution
contract needs (../planning/execution-contract.md: task identity, round,
measurements, revision table, proof owner) and the choices self-report the
audit starts from (../interpretation/choices-ledger-README.md). Detail that
only an auditor opens lives in sidecars, referenced by path.

```yaml
---
lane: <lane-name>
task: <board item ID>            # the round counter follows THIS, not the lane name
round: <1|2>
status: built | parked | blocked | refused | failed
branch: <branch>
head_sha: <sha>
files_touched:
  - <path>
gates:
  - '<gate-id> ok|red <count/summary>'     # one line per gate; never the command line
pregate_clean: true|false
measurements:                    # baseline counts the lane inventoried before authoring
  - artifact: <source path or measurement name>
    observed: <measured fact/count>
revision_table:                  # omit unless an assigned apparatus rerun is needed
  - observation: <measured failure/value>
    evidence: <exact log/snapshot/profile path or command-output artifact>
    revision: <contract/change addressing it>
    proof_owner: '<wrapper|lander>: <exact apparatus check>'
choices:                         # MANDATORY self-report; omit only when there was nothing beyond the brief
  - {headline: <choice>, verdict: <sound|unsound|needs-user>, confidence: <H|M|L>, gap: <one-line gap>}
choices_sidecar: <scratchpad>/<lane>-choices.md   # required when choices is non-empty
proof:                           # omit if gates already contain all proof
  - '<red-to-green or live-probe reference: file:line, log path, or commit>'
park:                            # omit unless status is parked
  reason: <second ungreen round | ceiling | force-collected | first-contact stop>
  resume_checklist: >-
    <done, remaining, the exact next step, why it parked>
  remainder: <board item or backlog row filed for the remaining work>
report: |-                       # at most 8 lines; facts first; every hypothesis prefixed H:
  <text>
---
```

## Rules

1. **Omit empty or default fields;** absence means none. Exception: every
   `choices` entry carries exactly one explicit verdict.
2. **`gates:` is one line per gate** — `<gate-id> ok|red <count/summary>`.
   Never the command (it is standard in the brief's gate block); logs by
   path; a test selection as `<runner> -k "<expr>": N passed/M skipped`.
3. **`proof:` holds only what `gates:` does not** — red-to-green evidence and
   live probes — as `file:line`, log-path or commit references, not pasted
   output. A hedge ("should work now", "looks correct") is not proof.
4. **`report:` is at most eight lines,** never restates the task, never
   closes with a courtesy; facts before hypotheses, hypotheses prefixed `H:`.
5. **A `choices` entry is headline + verdict + `H|M|L` confidence + one-line
   gap.** The walked ELI5 scenario for each goes in the sidecar
   `<lane>-choices.md`, one section keyed by the exact headline, so the
   auditor opens detail per choice. The sidecar is part of the handback: it
   is banked with the report, never left in a scratchpad that is cleaned.
   Field name: this package uses `choices`; the source factory's `valg` is
   the same field — a converter maps it one-to-one, no other transition.
6. **Exact identifiers verbatim:** paths, symbols, SHAs, counts, environment
   names, test IDs. Never abbreviate an identifier, never round a count.
7. **Negations survive.** "did NOT change src/", "NOT runnable in this
   sandbox", "0 regressions" are facts the lander acts on; a rewrite that
   drops the negation reverses the meaning.
8. **Terse structured English only.** No invented shorthand, positional
   arrays or other encodings. The source factory benchmarked a micro-DSL on
   twelve real handbacks: 37.0 % fewer tokens, read correctly by one model
   family and produced with invalid grammar 12/12 by another; a classical-
   language encoding reached 24.0 %, below its 30 % bar. Neither was
   adopted. Those numbers are that one benchmark's, not a fresh measurement.
9. **Budget:** an ordinary result at or below 60 lines / 4 KB. Overflow moves
   to the sidecar or a referenced artifact — never by dropping a red gate,
   an identifier, a negation or a proof owner.
10. **Measure the whole handback,** not the main text: the report plus every
    sidecar the reader actually opened. A schema that shrinks the main file
    by pushing everything into sidecars the auditor must open anyway has
    saved nothing.

These are compression rules, not permission to omit a red gate, a failed
apparatus, an identifier, a decision gap or a rerun owner.

## Rewrite check (run on any old handback converted to this schema)

An old-style handback can be rewritten under this schema without loss if,
after the rewrite, all four still hold:

| Must survive | Check |
|---|---|
| every red gate | count `red` lines before and after; equal |
| every exact identifier | grep each test ID / SHA / path from the old text in the new text + opened sidecars; all present |
| every negation | list the "not / never / 0 / unchanged" statements; all present with the same polarity |
| every proof owner | each `revision_table` row still names role + exact apparatus check |

### Before / after — an anonymized handback

Before (old schema, representative excerpt; the full original ran to about
90 lines / 9 KB, repeating each command under `gates:`, its result under
`proof:` and both again under `report:`):

```yaml
gates:
  - command: "PYTHONPATH=/home/dev/wt/flow-fix/src /home/dev/repo/.venv/bin/python -m pytest tests/flows -q -m 'not slow'"
    result: "pass: 126 passed, 1 skipped, 12 deselected in 33.9s"
  - command: "PYTHONPATH=/home/dev/wt/flow-fix/src /home/dev/repo/.venv/bin/python -m pytest tests/flows/test_live.py -q"
    result: "fail: 58 passed, 2 failed — server bind EPERM at 127.0.0.1:0"
proof: >-
  Fresh final offline run: 126 passed, 1 skipped, 12 deselected in 33.9s.
  The live suite cannot bind a server in this sandbox; the two live checks
  remain assigned to the wrapper.
report: >-
  Root cause: the legacy route was made a viewer-gated 303 alias in round 1,
  but the recorder still advertised it as a capturable screen and waited for
  its old table selector after landing on the new screen. Removed it from
  the taxonomy, archetype and signature tables; kept the 303 alias. No src/,
  route, migration, ADR or dependency changed.
```

After (complete; 38 lines / 2,139 bytes measured with `wc -l -c` on the
block below, which parses as YAML):

```yaml
---
lane: flow-fix
task: 412
round: 2
status: built
branch: lane/flow-fix
head_sha: e69392f63aa035cef7b20b8708e2b36dc8de96ec
files_touched:
  - docs/generated/reference/surfaces.md
  - tests/flows/react_surfaces.py
  - tests/flows/test_live.py
gates:
  - 'pytest tests/flows ok 126 passed/1 skipped/12 deselected'
  - 'pytest tests/flows/test_live.py red 58 passed/2 failed; server bind EPERM at 127.0.0.1:0'
pregate_clean: true
measurements:
  - artifact: surface count over REACT_SURFACES, SURFACE_LAYOUT_ARCHETYPES, SURFACE_SIGNATURES
    observed: before 27/27/27 with legacy; after 26/26/26 without
revision_table:
  - observation: tests/flows/test_live.py::test_live_shoot_nav_screen timed out after the legacy alias redirected
    evidence: train w-prev failure, tests/flows/test_live.py::test_live_shoot_nav_screen
    revision: capture moved to seeded /people; asserts .people-table tbody tr
    proof_owner: 'wrapper: pytest tests/flows/test_live.py::test_live_shoot_nav_screen -q in real Chromium on head_sha'
  - observation: tests/flows/test_live.py::test_live_visual_audit timed out at the legacy screen
    evidence: train w-prev failure, tests/flows/test_live.py::test_live_visual_audit
    revision: legacy removed from taxonomy, archetype, signature and generated reference; 303 alias kept
    proof_owner: 'wrapper: pytest tests/flows/test_live.py::test_live_visual_audit -q in real Chromium on head_sha'
choices:
  - {headline: People screen as capture target, verdict: sound, confidence: H, gap: Brief named no replacement screen.}
  - {headline: Byte-compare generated reference only, verdict: sound, confidence: M, gap: Sandbox cannot bind the regeneration server.}
choices_sidecar: <scratchpad>/flow-fix-choices.md
proof:
  - 'red-green: tests/flows/test_react_surfaces.py::test_retires_legacy_capture failed before the fix, passes after'
report: |-
  Retired the legacy screen from the active taxonomy; its authenticated 303 alias is kept.
  No src/, route, migration, ADR or dependency changed.
  The sandbox cannot bind a server; the two live Chromium reruns remain assigned to the wrapper (revision_table).
---
```

Rewrite check on this pair: the red gate survives (`test_live.py red … 2
failed`); the exact IDs survive (`e69392f6…`, both `::test_live_*` IDs,
`127.0.0.1:0`); the negations survive ("No src/, route, migration, ADR or
dependency changed", "cannot bind"); the proof owner survives on both rows.
Whole-handback size is 2,139 bytes plus the sidecar the auditor opens for
the two choices — report that sum, not the main file alone.

## Sentinel

`<lane>.sentinel.json` is updated at every leg boundary so a slow-but-alive
lane is never read as stalled; watchers must prove liveness AND deliverable
(a sentinel's presence is not production). Stale exit files from earlier
rounds are a known trap — a verdict belongs to one run ID and one round; the
run-bound exit contract is `harness/run-lifecycle.md` (introduced by PR2).
