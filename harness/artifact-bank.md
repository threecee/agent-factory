# Artifact bank — pristine acceptance and the durable-artifact lifecycle

The bank is the out-of-repo, out-of-scratchpad store for everything a future
run, review or owner would want again. This document is the single home for:
what is banked (§1), how a banked source is accepted as *pristine* (§3–§5),
how a copy of it is exercised (§6), how the source is renewed (§7) and how a
stranger finds a result without the conversation that produced it (§9).
Section numbers are stable; briefs and recipes cite them.

Two facts separate a bank from a scratchpad: **regeneration cost** and
**reproducibility**. If re-deriving a result is expensive or impossible, or if
someone must later show which state a number was measured on, the bytes belong
in the bank. Everything else is rebuildable from the repository and is never
banked.

The bank root, the seed, the renewal cadence and the retention rule are
**local choices** (the installer records them — see §10). This document ships
no product code: no database models, no healing routine, no WAL ritual, no
weekly rhythm. It ships the contract those local pieces must satisfy.

## 1. Artifact classes and where they live

| Class | Examples | Lives in | Lifetime |
|---|---|---|---|
| **Source** (pristine) | a frozen, seed-built instance every evaluation copies from | bank, read-only after acceptance | until renewed (§7); a superseded source is kept as history, never rewritten |
| **Handover copy** (working copy) | the served instance an eval or a demo actually runs against | a working directory outside the bank | reaped when its run ends (§8) |
| **Run output** | screenshots, transcripts, trajectories, scores, per-step timings, parity receipts | bank, written **as produced** | permanent, or the local retention rule |
| **Receipt / provenance** | manifest + README of a source or a run (§4, §9) | bank, inside the artifact it describes | with the artifact |
| **Build recipe + log** | the exact script that built a source, its filtered log | bank, inside the source (`build/`) | with the source |
| **Evidence bundle** | frozen database copy + manifest + log + wrapper output for a read-only investigation | bank | until the issue closes, then the retention rule |
| **Ephemeral** | virtualenvs, test-worker temp trees, caches, served-app instance directories, probe/smoke scratch, session logs | never banked | reaped |

An evidence bundle is frozen before the investigation starts: copy the
state, hash every file, and cite the hashes from the investigation brief
(`planning/investigation-brief-template.md`) so the
investigator's claims can be checked against exactly what was read.

A **worktree is not storage** either: generated corpora, score files and
instance databases that live only in a lane's gitignored tree die with the
worktree (`harness/worktree-ritual.md`, teardown). A handover copy is not
storage because it is mutated by the run. Only the bank is storage.

## 2. Bank as produced; copy, never move

1. Bank each artifact **when it is produced**, not at exit. A run that banks
   at exit banks nothing when it is killed, force-collected or times out —
   the report-first rule (`harness/report-schema.md`) applied to bytes.
2. **Copy** into the bank while any run, lane or pending wave may still read
   the original path; move only when every reader is known to be finished.
3. A banked source is **read-only** from the moment it is accepted. The build
   of a new artifact from it hashes the source's state files before and after
   the build and refuses if they differ (`source bank changed during the
   build`). Serving, recording, learning or "just confirming one thing" on a
   banked source is a defect, not a shortcut: the next copy inherits it.
4. A target name that already exists is a refusal, never an overwrite. Put
   identity in the name (seed or source id + period or build SHA) so that a
   second build of the same thing fails closed.

## 3. Isolation: a copy is not isolated until every reference points into it

Manifest-hash parity between two copies proves they started as the same
bytes. It does **not** prove they are independent. A source that records an
absolute file reference (a corpus directory, a model cache, a media root, a
lexicon file), an active job lease, or a provider role that a serve process
will resolve at runtime hands every copy the *same* external thing. The first
copy's ordinary write path then changes the second copy's starting state, and
a wave measured on the second copy is measured on a state nobody can rebuild.

**Worked example** (`harness/examples/copy-isolation.sh`, POSIX sh, run it):

```
-- manifest parity: identical bytes in both copies
<sha256>  copy-A/instance/state.json
<sha256>  copy-B/instance/state.json
-- isolation check on copy A (expected: REFUSE)
OUTSIDE  <work>/scratch/corpus
REFUSE: 1 reference(s) outside <work>/copy-A, 0 unresolvable
-- copy B reads (expected: A's term leaked in):
term-1
term-learned-by-A
-- isolation check on copy A with a symlinked corpus (expected: REFUSE)
OUTSIDE  <work>/copy-A/instance/corpus
REFUSE: 1 reference(s) outside <work>/copy-A, 0 unresolvable
-- isolation check on copy A with a dead path under its root (expected: REFUSE)
MISSING  <work>/copy-A/instance/corpus-not-relocated
REFUSE: 0 reference(s) outside <work>/copy-A, 1 unresolvable
-- isolation check on copy A after relocation (expected: ACCEPT)
inside   <work>/copy-A/instance/corpus
ACCEPT: isolated
-- source unchanged: <sha256>
OK: red (shared) -> red (symlinked) -> red (unresolvable) -> green (relocated), source untouched
```

`<work>` is a fresh temporary directory and `<sha256>` differs on every run
(the toy `state.json` embeds that directory's path), so check the *shape*:
the two copies' hashes equal each other, the source's before/after hashes
equal each other, and the verdicts appear in the order shown. The script
exits 1 with `example broken: …` if any step does not.

The check is one rule: **enumerate every absolute path the copy's state
records, resolve it physically (`pwd -P`, i.e. through symlinks), and require
it to sit under the copy's root.** Relocating means copying the data into
the copy and rewriting the pointer; a symlink resolves to the shared
directory and is refused by the same rule. A recorded path that does not
resolve at all is refused **by name** (`MISSING`), never accepted because its
string happens to start with the copy's root: an unresolvable reference is
one the copy has not relocated, and a lexical prefix test is exactly the
check that gets it wrong. The example's extraction line (`grep` over one
JSON file) is the toy; in a real product the paths live in configuration,
database rows and manifests — enumerate **all** of them (an inventory of
every column or key that stores a path is part of the installer's
parameterization, §10), not the one you happened to notice.

Before a source is accepted as pristine, the acceptance gate checks four
things beyond hash parity, each fail-closed with a named reason:

| Check | Refuses when | Why a hash cannot see it |
|---|---|---|
| **File references** | any recorded path resolves outside the artifact, or does not resolve at all (`MISSING`, named per path) | the path string is identical in every copy, and a dead string hashes the same as a live one |
| **Job leases** | a non-terminal job row's lease has expired, or any non-terminal work remains after reconciliation | a dead lease is inherited by every copy and blocks the first one that polls for readiness |
| **Declared roles** | a role the receipt says was configured left outputs marked unavailable at the live read path (§4, §5) | the receipt is copied, not recomputed |
| **Missing derived results** | a derived result the recipe expects (an index, a warm cache, a count matching the source's snapshot) is absent or drifted without a named reason | absence has no hash |

Every drift the gate *accepts* needs a named reason that is written into the
manifest and README (`accepted_reason`); silence is a refusal. Zero of a
result the recipe promised (zero items, zero windows) is always a refusal —
a warm that ran against a fake identity looks exactly like one that never
ran.

## 4. The receipt distinguishes an intended stand-in from a promised-but-failed role

A pristine built with a fake provider is a legitimate artifact: it proves
plumbing, runs offline and is the right bed for deterministic functional
tests. A pristine built with a *configured* model whose outputs came back
unavailable is a broken artifact that will make every downstream number
model-off without a red signal. Both contain rows marked `unavailable`. The
receipt must tell them apart, and it must do so from **persisted
configuration**, never by inferring from an output's model id or from the
absence of errors in a log.

Per configured role (embedding, reasoning, vision, …) the receipt records
the configured value and the outcome. Four outcomes, four verdicts:

| Configured role | Outputs at the live read path | Verdict | Receipt line |
|---|---|---|---|
| real provider | delivered | accept | `reason: <provider/model> delivered; unavailable_live=0` |
| real provider | some `unavailable` | **refuse** — promised but failed | `REFUSE: configured role left unavailable artifacts: reason=<n>` |
| `fake` (deliberate stand-in) | honestly `unavailable` / inactive | accept **and disclose** with counts per type | `reason=fake (deliberately unavailable: <type-a>=214, <type-b>=3)` |
| off / not configured | absent | accept, disclose as not promised | `vision: off (not promised)` |

Minimal receipt shape (JSON; field names are the installer's, the four
outcomes are not):

```json
{
  "artifact": "small-seed-2026-09-06-pristine",
  "built_from": {
    "seed": "small-seed@<sha256>",
    "code": "<repo sha>",
    "recipe": "build/build-pristine.sh@<sha>"
  },
  "source_unchanged": {"before": "<sha256>", "after": "<sha256>"},
  "roles": {
    "embed":  {"configured": "fake",  "outcome": "deliberately_inactive"},
    "reason": {"configured": "<provider/model>", "outcome": "delivered",
               "unavailable_live": 0, "unavailable_superseded": 12},
    "vision": {"configured": false, "outcome": "not_promised"}
  },
  "jobs": {"nonterminal": 0, "expired_leases": 0},
  "references": {"outside_artifact": 0},
  "accepted_drift": [{"what": "item_count <source>→<target>",
                      "reason": "<named product change>"}]
}
```

Rules:

1. A fake stand-in is keyed on the **persisted** configuration value
   (`configured: "fake"`), not on a model id string in an output row. A
   reasoning row can carry `model_id=unavailable` for a real provider too.
2. Every role a fake stands in for is written in the README in plain words
   so that a reader who never opens the manifest knows the artifact's numbers
   are plumbing, not model quality (`interpretation/evaluation-practice.md`).
3. A fake stand-in for one role does not excuse another: `embed: fake` with
   `reason: <real>` still refuses unavailable reasoning outputs.
4. A run on a copy inherits the copy's role receipt; the run's own receipt
   adds what the *serve process* actually resolved (a configured provider
   whose client was closed at startup is "promised but failed" at run time
   even when the source was accepted — that is the readiness smoke's job,
   `verification/evaluation-readiness.md` §2.1 "Role liveness" and §2.2
   rule 8).

## 5. History versus live: count what the consumer reads

An `unavailable` row is only a live defect if the consumer's read path would
show it. A row that was unavailable last month and has a valid current
successor on the same scope is history; deleting it to turn a gate green
destroys the record, and counting it as live makes a source that once ran
without a model *permanently* unbuildable under a configured one. The
opposite error is as bad: accepting every old row hides work that a
configured role promised and has not delivered yet.

The bank contract therefore requires the receipt to show **both** numbers —
`unavailable_live` (the scope's newest result at the consumer's selection)
and `unavailable_superseded` (older revisions with a valid successor) — and
the verdict in §4 is taken on the live number only. "Newest" is defined by
the **same identity and selection the consumer uses** (a digest, a revision
pointer), never by file mtime or insertion order: a copied file's mtime is
copy order, not publication order, and a source with two publications of
the same scope has been mis-selected exactly that way.

Do not copy a coarse "count every unavailable row" gate into a new factory.
The worked gate example that governs acceptance here — history with a valid
successor passes, a live unavailable under a promised role refuses, a newer
mtime with the wrong digest is rejected — lives in
`verification/examples/identity-and-history.md` §1–§2, with the planted
false red / false green in `verification/falsification.md` §10–§11. The
principle is settled; the source factory's own precise gate was still an
open fix at the time of writing, so treat its numbers as an illustration of
the failure (hundreds counted, one live), not as a tested correction factor.

## 6. Exercise the handover copy, never the source

The artifact someone receives is a different artifact from the one you
built. A source that was verified in place and then copied has not been
verified: the copy can have a stale reference (§3), a lease that expired
during the copy, or a role that resolves differently on the receiving
machine. So:

1. **Standup the copy**, not the source. The source is never served,
   recorded on, or written to. If a workflow needs to serve "the pristine",
   it serves a copy of it under a fresh run id (`harness/run-lifecycle.md`
   §2).
2. Run the isolation check (§3) and the readiness smoke
   (`verification/evaluation-readiness.md` §2) **on the copy** before the
   expensive step starts, and write the copy's own parity receipt (source
   manifest hash, build SHA, provider pins without keys — the rows of
   evaluation-readiness §4). Two runs
   are comparable only when those fields match; a mismatch is reported as
   "not comparable", never as a product signal
   (`interpretation/evaluation-practice.md`).
3. **Verify the source's hash after the run.** A changed hash means the copy
   was not isolated after all; the run's numbers are invalid and the source
   must be renewed (§7) before anyone copies from it again.
4. A copy whose run mutated shared state (a term learned, a job written into
   a shared directory) cannot be repaired by editing the source back: the
   state at stamping time is gone. Renew.

## 7. Renewal: regenerate from seed, on a locally chosen cadence

A chain source → copy → next source inherits everything the gate did not
catch: expired leases, unavailable outputs from a model-off run months ago,
placeholders a background warmer never superseded. Break the chain:

1. The renewed source is built **from the seed** (the small, complete,
   deliberately authored dataset under version control or in the bank with
   its own hash), never from the previous source.
2. The cadence is local — per release, per week, per train that changes the
   schema or the role configuration — and is written down (§10). Choose it
   by the question "what is the oldest state I would accept a number on?".
3. Renewal produces a **new** artifact name; the previous source stays as
   history and is never rewritten (§2.4).
4. A standup used to produce the source is **ephemeral**: stand it up in a
   working directory, let it finish every background job, checkpoint, then
   hand it to the build recipe and delete the working directory once the
   bank's README has been read back. Paths recorded during the standup must
   be **deliberately dead** at build time so the recipe's relocation step is
   forced to rewrite them into the artifact (a path that still resolves is
   silently shared — §3); never satisfy the relocation with a symlink.
5. The build refuses when required environment identity (model identity,
   detector versions, egress declaration) is missing, rather than building a
   source that a later serve will call "not current".

What the seed must contain — every situation a run needs, extended rather
than swapped for a large dataset — is an evaluation-practice rule, not a
bank rule: `interpretation/evaluation-practice.md`, "Small bed, complete
situations". The bank only requires that whatever seed is chosen has a hash
and is the thing renewal starts from.

## 8. Reaping working copies

Handover copies, served instances, recorder output directories and smoke
scratch are reaped when the run they belong to ends — at the latest at the
train landing that follows — the same way lane worktrees are. Tear down by
port and by path, never by process-name grep. Before reaping, confirm every
durable output was banked (§2.1) — a receipt whose paths point into a reaped
directory is a lie.

## 9. Findable without the conversation

A new operator with no memory of the session must be able to locate an
artifact, know what it is, and know how much to trust it. Every banked
artifact therefore carries, inside itself:

- `README.md` — what it is, one paragraph; a **PROVENANCE** block naming the
  seed (id + hash), the code SHA, the recipe (path + hash), the role
  configuration per §4 in plain words (no keys, ever), the counts the gate
  saw, every accepted drift with its reason, the date and who built it;
  known deviations from the recipe.
- `manifest.json` (or the product's own receipt) with the machine-readable
  form of the same facts, §4 shape.
- `build/` — the recipe as run and a filtered log. A recipe kept only in a
  scratchpad or a chat is a recipe nobody can re-run.

Reports and memories point at the **artifact name** in the bank, never at a
scratchpad or worktree path (`interpretation/memory-conventions.md`). A
report line like `results: <scratch>/wave-3/summary.json` is a decayed
pointer the moment the session ends.

## 10. What the installer writes down (local policy)

Record these in the target repo's operations document, next to the section
that cites this file; none of them ship with the factory:

| Parameter | Decide | Example (illustrative only) |
|---|---|---|
| Bank root | one durable, out-of-repo, out-of-scratchpad directory, chosen at user level (`user-level/README.md`) | `~/<project>-bank/` |
| What counts as durable | the project's own list per §1 | eval waves, demo recordings, funded corpora, evidence bundles |
| Path inventory | every configuration key, manifest field and database column that stores a path (§3) | `corpus_dir`, `media_root`, `model_cache` |
| Seed | the small complete dataset and where its hash lives | `seed/small-case/` + `seed.sha256` |
| Renewal cadence | when a new source is built from seed (§7) | each train that changes schema or role config |
| Role names | which configured roles the receipt reports (§4) | `embed`, `reason`, `vision` |
| Retention | how long run outputs and evidence bundles stay | run outputs indefinitely; bundles until issue close + 90 days |
| Readiness contract | what "all background work finished" means for a copy before an expensive run (`verification/evaluation-readiness.md` §2.1, "Background work") | every item reports its terminal status |

A factory that has not written these down has a scratchpad with a longer
name, not a bank.
