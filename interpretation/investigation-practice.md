# Investigation practice

- **Instrument first.** Reproduce with attribution before hypothesizing.
  Enumerate the reachable set instead of concluding from one observed bucket.
- **Measure before dispatch, hand over the whole observed run.** A lane that
  cannot run the acceptance apparatus (a browser-blind sandbox fixing a
  recorder) sees only what it is given. Given one failure it fixes one
  locator per round; given the whole run — log, DOM snapshot, screenshot,
  timings — it addresses every visible failure in one pass and names who
  reruns the apparatus. That is why the execution contract
  (../planning/execution-contract.md §2) makes attachments and the proof
  owner part of the brief, not of the handback. The source factory adopted
  it after a seven-round recorder fix; it has not measured the effect.
- **Root-cause before fix.** A bug lane documents the root cause before any
  fix is proposed. Three failed DIFFERENT hypotheses mean the model of the
  defect is wrong — stop and escalate an architecture question, never
  attempt a fourth. This rule is about the model of the defect; it is not
  the round counter. The two-round limit
  (../planning/execution-contract.md §3) counts complete rounds on the same
  approach; a task can hit either first, and they resolve differently: a
  wrong model is a STOP (design question), an exhausted count is a PARK
  (resumable, split).
- **Second opinions are cheap.** Read-only investigation agents (different
  model family than the implementer) fed with precise questions and file
  scopes return root causes in minutes; falsify THEIR claims with a direct
  check before acting (an investigator once reported a workflow "active on
  every push" — the file's trigger block said otherwise). The brief shape
  for such an agent is `../planning/investigation-brief-template.md`.

## Investigate before the fix lane gets its mandate

Why a read-only investigation precedes the fix brief when the cause is
uncertain; the brief itself is `../planning/investigation-brief-template.md`,
the trust rules are `../verification/falsification.md` §7–§9.

- **Coincidence recruits the wrong fix.** A job that stops after many model
  calls, at the same minute a neighboring job finishes, invites a brief that
  orders "wait for the neighbor". In the worked example in the template,
  a query on the frozen evidence showed the suspected neighbors never wrote
  to the identity the job depends on; the driver was input arriving during
  the run, and a second, unhypothesized mechanism (a retry that tried to
  reset already-stored progress) made every retry dead on arrival. A fix
  brief written from the coincidence would have built a barrier that moves
  the failure to the deadline.
- **Pin the source and freeze the evidence first.** The investigator reads a
  copied datastore, the run log and the manifest at the commit the run was
  built from (`../harness/artifact-bank.md`). Evidence
  that keeps moving under the investigation cannot refute anything.
- **Ask competing questions, not open ones.** "Which of path X and path Y
  wrote row R at time T" is answerable by a query; "why did it fail" is
  answered by an essay. The orchestrator's own hypothesis enters the brief
  as one row in the hypothesis table, never as the framing.
- **Every hypothesis ends supported, refuted or unknown — with a source.**
  A refutation cites the query or line that rules the mechanism out. An
  "unknown" names the observation gap (the exception that was not persisted,
  the earlier run's database that was not in the package). Both are
  findings; a guess is not.
- **Preserve the gaps into the mandate.** What the investigation could not
  decide becomes an observability criterion in the fix brief (persist the
  cause class; the next run's log must show it), not a sentence that
  quietly upgrades "unknown" to "proven". A failed attempt with an
  unrecorded exception stays "cause unknown" even after the fix lands.
- **The report is a proposed causal model.** It becomes a mandate only after
  the orchestrator re-runs at least one decisive check on the same evidence
  and records where the report overturned the issue body or the
  orchestrator's own hypothesis — in the issue thread and the train's
  choices protocol, so the wrong hypothesis stays part of the record.
- **Do not invent a phase for trivial defects.** A reproduced failure with a
  one-line mechanism gets the fix brief's root-cause paragraph, not an
  investigation lane. The trigger is uncertainty the orchestrator cannot
  remove with a direct check in minutes.
- **One success is not a time saving.** The worked example changed the
  mandate and its train verified green in one pass; that shows the pattern
  can work. Claims about rounds saved need the round counts from
  `../planning/execution-contract.md` §3 across several
  investigations, and the measurement the fix promised (here: plan attempts
  on the full case after the fix) is owed by a later run, not by the report.
- **Probes carry the caller's arguments** — copy the call site verbatim.
  A probe with its own defaults tests a different program.
- **Never signal-probe a live process** without a handler — attach by
  file-mtime and sampling profilers instead.

## Consumer inventory before a simplification, move, split or rename

"The frontend never calls it" is an observation about one consumer. A module
that looks redundant can still be run by a release script, read as text by a
test written in another language, or executed by a research driver.
Simplification is measured through consumers, never through line counts: a
change that fixes the dependency direction at a net +1 production line is
still a simplification; a split that saves nothing and scatters one concept
across files a reader must reassemble is not. This section owns the method;
`skills/refactor-clean` applies it, `examples/simplification-review.md`
walks it once end to end.

1. **Inventory first, one row per protected element.** Before deleting,
   moving, splitting or renaming, write the table and attach it to the brief:

   | Element | Why it is protected (what breaks, for whom) | Observed consumers (file:line, how found) | Realistic gain | Functional risk | Proof that permits the change |
   |---|---|---|---|---|---|

   Every consumer cell is marked *extracted* (read from a call site, a test,
   a log) or *inferred* (from a graph, a grep, a name); only extracted rows
   justify a deletion. The target repo chooses its own protected set from its
   own consequences — this factory ships the table, not a list.

2. **Consumers include readers, not only importers.** Search for the old path
   and the old symbol as strings, across every language in the repo and
   across test, tool, script and CI directories — not only the language the
   code is written in. Start from this set and extend it:
   - importers and callers. For routes, a method+path cross against the
     client is the proof; a tail-segment grep once found 2 of 15;
   - tests and contracts in another language that read the file AS TEXT
     (`readFileSync`, `readFile`, `read_text`, `open(`, fixture loaders): a
     TypeScript copy contract that opens a Python source file is a consumer
     of that path and is invisible to every Python tool;
   - tools that attribute findings by file path: SAST and lint baselines,
     complexity ratchets, coverage caps. A moved line is a NEW finding in
     the new file. Fix the code; never relieve the baseline for a move;
   - tests that patch by dotted name (`monkeypatch.setattr(mod, "name", …)`,
     `jest.mock`, `vi.mock`). The name vanishing turns the test red — and the
     test being green never proved the path was taken (rule 5);
   - scripts executed by a ritual, a make target, CI, or another test
     (`runpy.run_path`, `subprocess`, `exec`): live even in a research
     directory;
   - CLI entry points: the package's script table, make targets, release
     and deploy recipes — a function with no importer can still be the
     documented operator entrance, and deleting it removes a supported path;
   - generated artifacts regenerated from source (system documentation, API
     inventories, help text): they drift red one gate later.

   Starting points, not an exhaustive proof — the inventory is the proof:

   ```
   rg -n '<old/path>' --glob '!node_modules' .                       # the old path as text, every language
   rg -n '<old_symbol>' tests/ tools/ scripts/ frontend/ .github/    # the old symbol outside its package
   rg -n '(readFileSync|readFile|read_text|run_path|monkeypatch\.setattr|vi\.mock|jest\.mock)\(' tests/ frontend/
   grep -n '<old/path>' <every baseline file the verify portfolio keys by path>
   ```

3. **Live versus historical is decided per file, by executing readers.** A
   file is live when something executes or reads it — a test, a gate, a
   script in a ritual — whatever directory it sits in. A file is historical
   when nothing does: design notes, plans, research READMEs, archived specs,
   closed decision records. Historical text is never edited to keep its
   pointers "correct"; its pointers are true for the date it carries, and git
   holds the present. Live consumers follow the move. Getting this wrong in
   either direction is an unsound choice — rewriting history, or breaking a
   live driver — and the decision per file is recorded in the lane's choices.

4. **Run the consumer's apparatus, not only the lane's suite.** A frontend
   contract, a SAST gate, a slow browser suite, a docgen run that reads the
   moved file: the lane runs it, or names the wrapper as rerun owner, before
   handback. The train assembler runs them anyway; each late finding costs an
   assembly round.

5. **A green rename is not preserved behaviour.** When a guard proves "this
   path is never called" by replacing a name with a bomb, establish that the
   path WOULD be called before trusting it: plant a direct call and watch the
   guard fire; count the side effect the guard claims to prevent and
   attribute any residual count to its real producer. A guard that never had
   a real caller was vacuous. Replace it with one pinned at the owner (the
   store, the job kind, the boundary), falsified by the planted call, with a
   neighbouring allowed case that must still pass.

6. **Record the inventory where the choice is judged.** The rows go into the
   brief's measurements and, per element the lane decided about, into the
   choices ledger (`choices-ledger-README.md`) with the element's live or
   historical status and the proof that was run.
