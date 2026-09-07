# Worked example: a simplification wave, from consumer inventory to proof

A depersonalized train, distilled from several real ones. Paths, names,
commit hashes and counts are illustrative; the shape of every step is not.
Read it to see what the choices protocol (`../choices-ledger-README.md`) and
the consumer inventory (`../investigation-practice.md`, "Consumer
inventory") look like when they are actually done — and what a reviewer who
was not in the session can find afterwards.

The repo: a Python service under `server/`, a TypeScript frontend under
`frontend/`, tests under `tests/`, research drivers under `research/`, and a
verify portfolio whose SAST gate keeps a baseline keyed by file path. Train
`t42` assembles two lanes: `synth-move` (move the synthetic-data generators
out of the runtime package) and `routes-split` (split a ~10k-line route
aggregate into owner modules).

## 1. The inventory, before dispatch

The simplification spec said the generators were "imported by six runtime
packages, and only for three constants". That is one consumer class. The
orchestrator's inventory, attached to both briefs as measurements:

| Element | Why protected | Observed consumers | Realistic gain | Functional risk | Proof that permits the change |
|---|---|---|---|---|---|
| `server/synth/constants.py` (`DEFAULT_LABEL`, `PLACEHOLDER_IMAGE`, `MEDIA_CATEGORIES`) | Runtime policy values; the runtime must own them | 12 runtime importers, not 6 (extracted: `rg -n 'from server.synth import' server/`); 1 seed script | ~100 lines out of the runtime; the generators (~3 000 lines) leave `server/` intact | Runtime reads a wrong constant if the owner moves | Importers point at the runtime owner; the runtime import-boundary gate proves the tools are outside the runtime import closure |
| `research/2026-06_texture/run_large.py` | Reproduces a published measurement | Executed by `tests/test_texture.py::test_large_driver_restamps_before_writing` via `runpy.run_path` (extracted) | none — it is not being simplified | The test goes red if the driver's import path breaks | That test stays green after the move |
| `research/2026-06_texture/README.md`, `docs/plans/2026-05_synth-plan.md`, `docs/notes/2026-04_generator-design.md` | Historical record | No executing reader (extracted: `rg` over `tests/`, `scripts/`, `Makefile`, `.github/`) | none | Rewriting history makes the record false for its own date | Left untouched |
| `research/2026-06_texture/run_small.py` | Sibling of the driver | No executing reader | none | none | Left untouched — historical by the live/historical rule, although it sits beside a live file |
| `server/web/routes_all.py` (~10k lines, ~180 routes) | The mounted API contract | Frontend client (method+path cross, ~180 rows); ~20 test files patch names on this module; `frontend/src/copy-contract.test.ts` reads it AS TEXT for required user-facing strings; the SAST baseline is keyed by this path; `tests/test_summary_job.py` reads its source for an enqueue site | Seven nameable owner modules; the aggregate thins to router composition | A route, an auth guard or a user string changes silently | A snapshot of the full mounted inventory (method + path + auth guard) identical before and after; every reader above re-pointed and green |

Two things to notice. Rows two and three are the live research driver and
the historical text: both sit in `research/`, and the directory decides
nothing — the executing reader does. Row five's consumer list is longer than
any lane would have written on its own; three of those readers were found
only by searching the OLD PATH as a string in every language and in the
baseline files, not by searching importers.

## 2. Lane `synth-move` — the handback

The lane's result, terse shape (`harness/report-schema.md`, rule 5, with the
`id:` field of `../choices-ledger-README.md` §2 first in every entry):

```yaml
choices:
  - {id: synth-move-1, headline: Runtime policy owns the constants, verdict: sound, confidence: H, gap: Owner module unspecified}
  - {id: synth-move-2, headline: plant_media_corpus becomes test-owned, verdict: sound, confidence: H, gap: Its only callers are tests}
  - {id: synth-move-3, headline: Generators live under tools/synth; root importable only from pytest and tool invocations, verdict: sound, confidence: H, gap: Destination unspecified}
  - {id: synth-move-4, headline: Quality gates follow the move, verdict: sound, confidence: H, gap: Gate config listed the old path}
  - {id: synth-move-5, headline: Import-boundary gate extended to prove tools are outside the runtime closure, verdict: sound, confidence: H, gap: Issue said six importers; measured twelve}
proof:
  - 'red-green: tests/test_runtime_import_boundaries.py::test_runtime_never_imports_synth red before, green after (commit 3f1c2a9)'
```

The five scenarios are in `synth-move-choices.md`, one section per ID,
which the wrapper commits to `docs/choices/t42/` with the train.

## 3. The audit finds the sixth choice

Walking the diff — not the self-report — the auditor finds five files under
`docs/notes/`, `docs/plans/` and `research/` edited to point at the new
namespace. The lane did not list it: from inside the lane it looked like
housekeeping, not a decision. Entry appended to `docs/choices/t42.md`,
scenario inline because the verdict is unsound:

> **t42/synth-move-6 (found by audit) — unsound, confidence high.**
> *Headline:* Historical documents were rewritten to point at the new
> namespace.
> *Scenario:* A design note from April describes the generator package as
> `server.synth`. That was true in April. The lane changed the note to say
> `tools.synth`, so the note now describes a layout that did not exist when
> the note was written, and the decision it records no longer matches the
> code it reasoned about. A reader a year from now, trying to understand why
> the generators were built the way they were, is misled by a document that
> claims to be from April. The alternative — leaving the note alone — costs
> nothing: git history and the current code say where the package is now.
> *Gap:* the brief said "update references" without saying which references
> are live.
> *Reach:* every future move in this repo; the same rule covers plans,
> research READMEs, closed specs and decision records.
> *Verdict:* unsound. *Corrected decision:* only live surfaces are updated —
> the decision records' code anchors, the backlog anchor, the living
> simplification spec. Historical text keeps its original pointers.
> *Action:* the wrapper restored the five files before committing; the
> lane's gates stayed green.

Note what the entry does not do: it does not sketch the patch. It states the
property that must hold, and the fix round is judged against that property.

## 4. The train falsifies the correction

First verify on the assembled train, one red:
`tests/test_texture.py::test_large_driver_restamps_before_writing`. The test
executes `research/2026-06_texture/run_large.py` through `runpy.run_path`,
and the driver imports the constants from the old namespace — it was one of
the five restored files.

The corrected decision was too coarse: "everything under `research/` is
historical" was a directory rule, and the inventory row had already said
otherwise. The amendment is appended under the SAME ID, dated, with proof:

> **t42/synth-move-6 — amendment (train verify, run 1, 2026-06-14).**
> The rule is "does the file have an executing consumer?", not "which
> directory is it in". `run_large.py` is executed by
> `tests/test_texture.py::test_large_driver_restamps_before_writing`
> (`runpy.run_path`), so it is a live consumer and its import follows the
> move (commit 5e2d7c1, "fixes t42/synth-move-6: live driver follows the
> move"). The README, the plan, the design note and the un-executed
> `run_small.py` stay untouched. Verify run 2: green.
> *Proof:* the test id above red in run 1 (`<bank>/t42/verify-1.log`), green
> in run 2 (`<bank>/t42/verify-2.log`).

Same ID in the protocol, in the fix commit message, in the bank's log names.
No new number: the decision being proven is the same decision, sharpened.

## 5. Lane `routes-split` — four assembly findings, none a product change

The lane split `server/web/routes_all.py` into seven owner modules, kept the
mounted inventory snapshot identical (~180 rows of method + path + auth
guard), re-pointed ~75 monkeypatch lines in ~20 test files to the actual
owners, and handed back green on its API test selection. The train needed
four assembly runs. Every finding was a reader of the moved source that the
lane's proof set did not include — and every one is on the inventory row.

**Run 1 — the path-keyed baseline.** Six `assert x is not None` lines moved
into `server/web/routes_case.py` and `routes_analysis.py`. The SAST gate
keys its baseline by file path, so six moved lines are six NEW findings.
Fixed as code — explicit `raise` with the named invariant — not by accepting
the six into the baseline. A baseline relief "for the move" is a weakened
criterion, and the factory does not grant one (`verification/verify-portfolio.md`,
"Ratchets move one way").

> **t42/O-4 — sound, confidence high.** *Scenario:* a baseline is a list of
> findings the repo has agreed to live with, keyed by where each one is. Move
> the line and the key changes; to the gate, a finding it had never seen
> appeared in a new file. The honest response is the one the gate asks for —
> make the finding go away in the code — because the alternative, teaching
> the baseline the new key, is exactly how a real new finding would be hidden
> next time. *Reach:* a move lane runs the path-keyed gates itself even when
> its pregate block does not list them.

**Run 2 — the TypeScript reader of a Python file.**
`frontend/src/copy-contract.test.ts` opened `server/web/routes_all.py` with
`readFileSync` to assert that the required user-facing string "Findings must
be ready before sampling." exists in the backend, and to enumerate the
interior-copy surface. The strings now live in the owner modules. The
contract was re-pointed to the seven modules; its requirement did not change
(7/7 green). This reader is invisible to every Python tool; it is found by
`rg -n 'server/web/routes_all' frontend/` — the old path as a string, in the
other language.

> **t42/O-5 — sound, confidence high.** *Scenario:* the frontend test
> suite contains a contract that the backend must carry certain sentences
> verbatim, and it checks by reading the backend file. Nothing in the Python
> import graph, the Python test suite or the Python gates knows this file
> exists. When the sentences moved, the contract failed for the right reason
> — the file it read no longer had them — and re-pointing it is the whole
> fix. *Reach:* cross-language contracts are importers the inventory must
> include; for any move X→Y, `rg` the old path in every language directory
> before dispatch.

**Run 3 — two source-reading Python tests, one of them a vacuous guard.**
(a) `tests/test_summary_job.py` read `routes_all.py` as text to locate the
summary job's enqueue site (its `scope_key="case"` contract); the site
moved; the test was re-pointed. (b)
`tests/test_translation_queue.py::test_queue_get_without_provider_does_not_materialize`
guarded "a GET never materializes the case" with
`monkeypatch.setattr(routes_all, "materialize_jobs", boom)`. The split
removed the last import of that name from the routes module, the attribute
disappeared, and the test went red.

Investigation before fixing (instrument first): with the guard removed and
a database row count taken around the GET, the count rose by one — and the
row was a request middleware's refresh enqueue, not a translation job. The
GET handler had never called `materialize_jobs` through that name. The guard
had been green for weeks without guarding anything: **a green test that
patches a name proves the name exists, not that the path is taken.**

Corrected guard, pinned at the owner and falsified:

```python
# pin (a): the routes module never regains the import
assert not hasattr(routes_case, "materialize_jobs")
# pin (b): enqueue of TRANSLATION_JOB_KIND is reachable only through warming.py
with owner_spy(JobStore, "enqueue") as calls:
    client.get(f"/api/v1/cases/{case_id}/translations")
assert [c for c in calls if c.kind == TRANSLATION_JOB_KIND] == []
```

Falsification: a planted direct `JobStore.enqueue(TRANSLATION_JOB_KIND, …)`
inside the GET handler turns pin (b) red; a planted enqueue of ANOTHER job
kind passes — the guard is about this path, not about every enqueue. Both
runs are banked as `<bank>/t42/guard-falsification.log`. No baseline, cap
or assertion was relieved on the train.

> **t42/O-6 — sound, confidence high.** *Scenario:* a test that says "this
> route never calls X" by swapping X for a bomb proves something only if the
> route would otherwise reach X. Here it never did, so the bomb was never
> reachable and the test passed for weeks for a reason unrelated to the
> behaviour it claimed to protect. When the name went away it failed, again
> for an unrelated reason. The corrected guard watches the thing that would
> actually change if the behaviour regressed — the job store's enqueue of
> that job kind — and was shown red on a planted regression and green on a
> neighbouring, allowed one. *Reach:* every "never calls" guard in the repo
> is suspect until it has been seen red on a planted call.

**Run 4 — green.** Full suite including the live browser leg; the inventory
snapshot identical; no product behaviour changed on the train.

## 6. What would have caught these before dispatch

The inventory row for `routes_all.py` already listed all four readers. The
lane's brief, however, listed the pregate block and an API test selection —
the lane ran what it was told. The remedy is not a longer brief; it is the
rule that a move/split lane's proof set IS the inventory's "proof" column,
and that the lane, or the named wrapper, runs each consumer's apparatus
before handback (`../investigation-practice.md`, rule 4). For this shape:

```
rg -n 'server/web/routes_all' --glob '!node_modules' .          # the old path as text, every language
rg -n 'routes_all' tests/ tools/ scripts/ frontend/ .github/    # the old symbol outside its package
rg -n '(readFileSync|readFile|read_text|run_path|monkeypatch\.setattr|vi\.mock|jest\.mock)\(' tests/ frontend/src/
grep -n 'routes_all' .sast-baseline.json .coverage-cap.json     # path-keyed baselines
```

Starting points, not an exhaustive proof; the inventory is the proof.

## 7. Closing the programme with its proof gaps stated

When the simplification programme is archived, its record is rewritten for
the reader who comes later — and "closed" is not evidence for anything the
programme never proved. The archived spec for this wave ends with a dated
list of what was promised and not delivered, in the same register as the
ledger:

> **Proof gaps at close (2026-06-15).** The visual evidence for the three
> user-facing lanes was not taken before landing; it rides on the next full
> evaluation run against a fresh copy, which has not happened at the time of
> archiving. The manifest cross-check for the second lane was described in
> the spec and never implemented. Neither gap is upgraded by this archive;
> both are board items with their own proof owner.

The choices ledger treats an archive the same way: a headline that says
"landed" in an archived spec is not a banked proof, and a later reader dates
the archive's claims against the protocols that came after it. A close
that lists no gaps on a multi-lane programme is a red flag, not a pass —
the same rule as an empty choices list on nontrivial work.

## 8. What a stranger finds afterwards

A reviewer who joins after the train has landed, with no scratchpad and no
transcript, opens `docs/choices/t42.md` and can:

- read `t42/synth-move-6` with its scenario inline, its corrected decision,
  its dated amendment, the fix commit `5e2d7c1` and the test id that was red
  then green — and re-run that test;
- follow `t42/synth-move-3` (sound, headline only in the protocol) to
  `docs/choices/t42/synth-move-choices.md` § `synth-move-3`, committed with
  the train, for its walked scenario;
- find `t42/O-6`'s falsification log in the artifact bank at the path the
  entry names (`harness/artifact-bank.md`), and re-plant
  the direct call to see the guard fire;
- run `git log --grep 't42/synth-move-6'` and land on the fixing commit.

What they will not find is a path under `/tmp`, a scratchpad directory, or
the words "see the session". Had any of those been the only reference, the
entry was not banked, and the lander should have copied the scenario into
the protocol before the train landed (`../choices-ledger-README.md` §3).

## 9. What this example is not

- Not a list of guards a repo must keep. The protected rows above are this
  repo's; yours come from your own inventory, with your own consequences in
  the "why protected" column.
- Not a claim that big files are wrong or that moved lines are deleted
  maintenance. `synth-move` saved ~100 runtime lines and moved ~3 000 intact;
  an earlier lane in the same programme fixed a dependency direction at net
  +1 production line and was still a simplification. Simplification is
  judged through consumers (`../investigation-practice.md`).
- Not a new audit skill. `audit-choices` did the audit; the protocol stored
  it; the train proved it.
