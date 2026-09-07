# Identity and history — worked examples

Three gates that went wrong by measuring a proxy (a total count, a file
mtime, a restart from zero) instead of what the consumer actually reads, and
the shape that survives. The principle is owned by
`interpretation/investigation-practice.md` (Identity and history); the
red/green norms by `../falsification.md` §10–§12; the acceptance receipt
that reports the counts by `harness/artifact-bank.md` §4–§5. This file owns
the examples. `identity_and_history.py` beside it is a stdlib-only model of all
three — run it once when installing, and run it with `--plant` to see each
planted defect go red:

```
python3 verification/examples/identity_and_history.py                  # exit 0
python3 verification/examples/identity_and_history.py --plant count-all        # §1 red
python3 verification/examples/identity_and_history.py --plant newest-mtime     # §2 red
python3 verification/examples/identity_and_history.py --plant restart-at-zero  # §3 red
python3 verification/examples/identity_and_history.py --plant weak-supersedes  # §3 red
```

Nothing here is a port: no database, no warmer, no product code. Port the
verdict table, then falsify your own gate the same way.

## §1 History, current, promised — three verdicts

**Setting.** A store of derived artifacts, one or more revisions per scope.
A producer role (a model) is configured to deliver; a fallback path writes
`unavailable` placeholders when the role is absent. The consumer reads, per
scope, the highest-revision row with `status = current`. A pristine/acceptance
gate must reject a build in which the configured role left unavailable output.

**The wrong gate** counts every row with `producer = unavailable`. On a source
that had been copied through several role-off runs it said `unavailable=666`;
the read path showed one unavailable scope. Deleting history to get green
would hide the cause; allowing all unavailable rows would hide the live one.

**The gate that follows the consumer** calls the consumer's own selection
and splits the rows into three populations. Planted rows and expected
verdicts (exactly what the script asserts):

| Rows (scope, rev, status, producer) | Population | Verdict | Receipt |
|---|---|---|---|
| `s1 r1 superseded unavailable` + `s1 r2 current model` | history | **pass** | `unavailable_superseded += 1` |
| `s4 r1 current unavailable` (role = model) | live | **fail** — `left LIVE unavailable artifacts: live=1 scopes=['s4']` | `unavailable_live = 1` |
| plan owes `s9`, no row at all | promised | **fail** — `promised but never delivered: ['s9']` | `promised_undelivered = 1` |
| same rows, role = `fake` | deliberate | **pass**, reported | `deliberately_unavailable = 3` |

Rules the table encodes:

1. The gate imports or re-implements the consumer's selection verbatim
   (`consumer_selects` in the script). If the consumer's rule changes, the
   gate changes with it — they are one contract with two callers.
2. The receipt always carries `unavailable_total`, `unavailable_live`,
   `unavailable_superseded` and `promised_undelivered` (the first two names
   are the bank receipt's, `harness/artifact-bank.md` §5). Green with a
   large history count is a green verdict AND an open question (rule 3
   below).
3. A deliberately fake role is a different evaluation type: its unavailable
   rows are reported, never rejected, and its numbers are plumbing-only
   (`harness/artifact-bank.md` §4, `interpretation/evaluation-practice.md`;
   the run-time readiness receipt is `../evaluation-readiness.md`,
   introduced by PR4).
4. "Promised" is computed from what the plan or configuration owes (the
   identity set), not from what happens to be stored — a store with zero
   rows is not clean, it is undelivered.

**Falsification** (`../falsification.md` §10): plant `count-all` — the gate
rejects the history-only fixture with `unavailable artifacts: 2`. That is
the false red. Remove the `s4` row from the live fixture with the correct
gate in place and the run must stay green; put it back and it must fail
naming `s4`. Message check: a failure that prints the total where the
consumer sees the live count has mis-described the failure.

**Source-factory status — UNFINISHED.** This is
[threecee/varde#669](https://github.com/threecee/varde/issues/669), still
open at the pinned revision: the gate there still counts every
`status == "unavailable"` row. The 666-versus-1 measurement was taken on an
old copy and is not a correction factor. More important, the later diagnosis
in [#670](https://github.com/threecee/varde/issues/670) showed those rows
were not dead history: the placeholders had been written by the fallback
path and the promised producer never converged, so the "history" was the
residue of a live defect. That is why rule 2 keeps both counts and why
`investigation-practice.md` rule 3 makes a large history count an
investigation trigger. Do not cite this section as proof that the source
factory has landed a consumer-keyed gate; cite it for the verdict table.

**Coordination.** The pristine acceptance receipt in
`harness/artifact-bank.md` §4–§5 reports `unavailable_live` and
`unavailable_superseded` per configured role and takes its verdict on the
live number only; this example's receipt adds `unavailable_total` and
`promised_undelivered`, and a bank installer is free to add the same two.
The bank contract does not copy the total-count gate (§5 says so in as many
words); this table is the acceptance it points to.

## §2 Newest mtime, wrong key

**Setting.** A consumer computes a digest of its inputs and loads the
snapshot named by that digest (`v1-<digest>.json`). An acceptance gate must
check "the snapshot the consumer will read has N items" before a copy is
declared serve-equivalent.

**The wrong gate** picked the newest file by mtime. A recursive copy
reversed mtimes, so a mid-index leftover (225 items) outranked the completed
snapshot (226 items) and the gate refused a good copy — while the consumer,
keyed by digest, had never been wrong.

**The gate that follows the consumer** recomputes the digest exactly as the
consumer does and loads that key. Planted fixture and verdicts:

| Store contents | mtime | Gate by mtime | Gate by consumer key |
|---|---|---|---|
| `v1-<digest(inputs)>.json` (226 items) | older | ignored | **chosen** |
| `v1-3dbf19deadbe.json` (225 items, wrong key) | newer | chosen — **red** | ignored |
| consumer's key file deleted | — | silently picks decoy | **fail** — `missing digest=<key>` |

Rules:

1. Identity is the content key the consumer computes, never the newest file,
   the last row, or the highest id. Copies, retries and parallel writers
   reorder all of those.
2. A missing key is a rejection ("not what the consumer would compute"),
   never a fallback to the newest candidate.
3. The gate must recompute the key the way the serving path does — same
   inputs, same version stamp. A gate that reads a stored key from the file
   it is judging is a self-comparison (`../verify-portfolio.md`, "Known
   vacuity classes").

**Falsification** (`../falsification.md` §11): plant `newest-mtime` — the gate
chooses the decoy: `gate chose the newer decoy 3dbf19deadbe over the
consumer's key … (items 225 vs 226)`. The decoy with a newer mtime is the
realistic case, not a corner; make it the fixture.

**Source-factory status — LANDED and falsified.** This is the
[#642 diagnosis](https://github.com/threecee/varde/issues/642#issuecomment-5551344471):
the fix keyed the gate by the served digest and added regression tests for
a stale-mtime decoy and a two-source relocation. It is the one example in
this file with a completed proof in the source factory.

## §3 Incremental plan — identity diff, exact precedence, progress

**Setting.** A long-running plan prepares a set of unit identities
`(unit, digest-of-input)`, sends each pending identity to an expensive step
(a model call), checkpoints results and a progress receipt `completed/total`,
and publishes when the set is done. Inputs can arrive while the plan runs
(a late source, a re-derived dependency), changing some identities.

**The wrong plan** compared the whole identity set at publish time and, on
any difference, threw the attempt away and restarted at zero. Two failures
compound: every checkpointed unit is re-sent to the expensive step, and the
receipt's own regression guard rejects `completed 444 -> 0` — so "stale"
became "terminal failure" after the guard did its job.

**The plan that follows identity** re-prepares, treats exact hits as cache
hits, computes only the symmetric difference, retires only what is no longer
desired, and rebases progress from the stored receipt. Script trace:

| Step | Inputs | Expensive calls | Receipt |
|---|---|---|---|
| attempt 1 | a=x, b=y, c=z | a, b, c | 3/3 |
| inputs move mid-plan | a=x, **b=y2**, c=z, **d=w** | b′, d only (a, c reused) | 5/5 (base 3 + 2 pending) |
| weak result arrives for b′ (floor/unavailable) | — | none | b′ stays `model` |
| retry (new attempt, same receipt) | unchanged | none | ≥ 5, never lower |

Rules (each is one assertion in the script):

1. **Unchanged identity is not recomputed** — assert on the exact set sent
   to the expensive step, not on a count.
2. **Changed identity is recomputed**; the old identity is retired because
   it is no longer desired, not because something newer exists.
3. **Exact precedence**: a weaker producer (fallback, floor, unavailable)
   with the SAME exact identity never supersedes a stronger current result.
   Precedence is exact, not scope-wide — a floor for a different identity in
   the same scope is still allowed to exist.
4. **Progress rebases from the durable receipt**: a new attempt starts at
   the stored `completed`; `total = completed + pending`. The store's guard
   against regression stays; the plan must never provoke it.
5. **Retry is a new attempt on the same receipt**, not a new receipt with
   its own progress, unless the platform makes that explicit — the reader
   must be able to tell "attempt 3 of one plan" from "second plan".
6. **Silence is scoped to what competes.** If the plan waits for the store
   to be quiet before a fallback write, "quiet" means no other producer for
   the same unit of contention (the same case / key space). A
   deployment-wide barrier lets an unrelated job starve this one, and a
   barrier alone does not converge a plan whose inputs keep moving.

**Falsification** (`../falsification.md` §12): plant `restart-at-zero` — the
receipt guard goes red: `cannot regress progress 3 -> 0`. Plant
`weak-supersedes` — `weak result superseded a stronger current one:
('floor', '?')`. Reverting the identity diff (recompute everything) fails
rule 1's exact-set assertion; that revert is the true "fix reverted" state
of this example.

**Source-factory status — PARTLY LANDED, convergence unmeasured.** The fix
for [#670](https://github.com/threecee/varde/issues/670) landed in one
train: progress rebased from the stored count, runtime failures preserved
with cause, weak results blocked from superseding an exact current model
row, fallback pre-compute run once at per-case quiescence. Its acceptance
test is the stable re-prepare after a source arrives mid-warm (exact windows
not re-sent, receipt `success`). Two limits stand: the publisher still
compares the whole identity set — each attempt re-prepares and sees exact
hits as cache hits, but several arrivals during one run can still exhaust
the attempt budget, and a receipt retry then converges on its own progress;
and the number of plan attempts on the large case (a 25k-message case) is
the measurement [#590](https://github.com/threecee/varde/issues/590) was
re-run to take, with the result not yet read. "Identity diff, not
all-or-nothing" is therefore a design rule with a partial proof, not a
claim that the whole pattern is implemented and proven there. The source
factory's own choices protocol for that lane records *medium* confidence on
exactly this point (that protocol is internal to the source factory and not
resolvable from this repository; the issue links above are).

## What to port, what to leave

Port: the consumer's selection as the gate's selection; the four-count
receipt; content keys over mtime; the three assertions of §3; both-direction
falsification. Leave: scope prefixes, status precedence tables, ingest
barriers, warmer constants and every store or model row of the source
factory — those are one product's answers, and the exclusions of the v2
analysis keep them there.
