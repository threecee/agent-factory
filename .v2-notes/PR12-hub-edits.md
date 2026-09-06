# PR12 — requested edits to the shared hub files

PR12 does not touch `INSTALL.md`, `README.md` or `user-level/README.md`
(HUB FILES RULE). The integrator applies the edits below verbatim. Each
edit points to the home; none duplicates it.

Homes introduced or extended by PR12:

- `harness/guards.md` — NEW; the one home of every rule about guards.
- `harness/guards/` — NEW; the dispatcher, shared primitives and three
  example rules (`verdict`, `identity`, `no-verify`), with `falsify`.
- `harness/adapters/` — NEW; the Claude Code settings block example, the
  entry script, the text-only reminders script, the AGENTS.md paragraph.
- `harness/tests/test_guards.sh` — NEW; the proof.
- `harness/run-lifecycle.md` §11 — preconditions before launch and what a
  lane can be forced to (documented, not shipped as a second launcher).
- `harness/report-schema.md` § Machine check at handback — the result lint.
- `verification/falsification.md` rule 15 — a guard is mounted only after
  its falsification receipt exists.

Overlap note for the integrator: PR13 extends
`harness/adapters/factory_reminders.sh` (the `ci_signal.sh` forward line
and `landing-in-progress.json` writer land there) and resolves the forward
rows of the guards table in `harness/guards.md` §6 (M-1, M-7, M-8, M-9,
M-10, M-11, M-12, M-13, M-17 → `verification/protections.md`). Keep the
table's rows; PR13 only replaces "introduced by PR13" with the landed
section. No gate scripts are added by PR12, so the `24` count literals
(README, INSTALL 2.1, gates/README) do not move; PR13 moves them.

---

## 1. `user-level/README.md`

**Anchor:** after item 7 ("**Model policy (required before the first
dispatch):** …"), append item 8.

**Insert (verbatim):**

```markdown
8. **Guard switches (optional):** `FACTORY_GUARD_DISABLED=1` only while the
   guard apparatus itself is down; `FACTORY_GUARD_ALLOW=<id>` per rule,
   preferably as a prefix on the command itself so it stands in the
   transcript. Both are logged and ledgered as orchestrator entries, never
   committed; record the reason and the date. The parameters a guard reads
   (gate names, CLI name and token, port range, disk floor) are the repo's
   operations-doc bindings of `../harness/guards.md` §8, not user-level
   settings.
```

## 2. `INSTALL.md`

**Edit 2a — Step 5 (Harness).** After item 7 ("Optional, measurement-gated:
`harness/bulk-read-contract.md` …") append item 8:

```markdown
8. Optional, measurement-gated: `harness/guards.md`. Run
   `bash harness/tests/test_guards.sh`, copy `harness/guards/` and
   `harness/adapters/` beside your scripts (imports are package-relative),
   bind the §8 parameters in the operations doc, run
   `python3 harness/guards/guard_dispatch.py falsify --lane install --out <dir>`
   and bank the log, then register the adapter block from
   `harness/adapters/claude-code-settings.json.example` as a deliberate
   step — the package registers nothing. Coding CLIs get the
   `AGENTS.md.example` paragraph. Every rule that applies is written into
   the operations doc as a reviewed diff naming the guard, the switch and
   the falsification.
```

**Edit 2b — Step 7 (Smoke test).** After item 5 ("Falsify the round counter
…") append item 6:

```markdown
6. Mount the guards for the smoke train from assembly start; record every
   refusal and switch in the ledger; a false positive without a named
   alternative goes to WARN.
```

## 3. `README.md`

**Edit 3a — "Shared infrastructure" paragraph.** Replace

```
the
measurement-gated bounded bulk-read contract, and the model policy: roles
```

with

```
the
measurement-gated bounded bulk-read contract, the harness guards (one
dispatcher, rules that fail open, switches that leave a trace, adapters as
short mappings — `harness/guards.md`), and the model policy: roles
```
