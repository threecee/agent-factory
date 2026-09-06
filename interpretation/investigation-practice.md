# Investigation practice

- **Instrument first.** Reproduce with attribution before hypothesizing.
  Enumerate the reachable set instead of concluding from one observed bucket.
- **Root-cause before fix.** A bug lane documents the root cause before any
  fix is proposed; three failed DIFFERENT hypotheses mean the model of the
  defect is wrong — stop and escalate, never attempt a fourth.
- **Second opinions are cheap.** Read-only investigation agents (different
  model family than the implementer) fed with precise questions and file
  scopes return root causes in minutes; falsify THEIR claims with a direct
  check before acting (an investigator once reported a workflow "active on
  every push" — the file's trigger block said otherwise).
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
