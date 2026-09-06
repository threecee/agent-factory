# PR13 — requested edits to the shared hub files

PR13 does not touch `INSTALL.md`, `README.md` or `user-level/README.md`
(HUB FILES RULE). The integrator applies the edits below verbatim. Each
edit points to the home; none duplicates it.

Homes introduced or extended by PR13:

- `verification/landing-modes.md` — NEW; the one home of how a verified
  train reaches the default branch: `pr` (default) and `direct-push` (the
  documented override), what both carry, the branch policy, the hold,
  forbidden forms, the identity consequence, the close-out pointer.
- `verification/protections.md` — NEW; the one home of the protections
  outside the harness hook: git hooks (M-10), the ruleset (M-11), the status
  poster, the CI signal (M-12), the ledger lint (M-7), the close-out (M-13),
  the gate legs M-8/M-17a/M-17d, the adapter table, what the tests prove.
- `verification/ci/README.md` — NEW; the CI regime, the mode table, the
  branch policy and its classic fallback, the promotion rule, the
  throwaway-repo falsification.
- `verification/ci/ruleset-main.json.example` — NEW; the branch-policy
  payload. English mode headers on `verify.yml.example`,
  `review-lane.yml.example`, `security-scan.yml.example` (bodies unchanged).
- `verification/protections/` — NEW; `git_hooks.py` + `githooks/*`,
  `post_local_verify.sh`, `bootstrap_ruleset.py`, `ci_signal.sh`.
- `harness/guards/rules/` — five rule modules: `landing`, `pre_push`,
  `commit_msg`, `pre_commit`, `closeout` (plus `_gates`, `_landing_fixtures`,
  `_commit_fixtures`).
- `verification/gates/` — three gates: `check_landing_closeout.py`,
  `check_choices_protocol.py`, `check_gate_weakening.py`; two legs added to
  `check_migration_heads.py` (drift, M-8) and `check_backlog.py`
  (duplicate id, M-17a); `gates/README.md` says 27 and records the legs as
  deviations two and three.
- `verification/lander-duties.md` §8 — NEW; the close-out list, identical in
  both modes. `verification/falsification.md` rule 16 — NEW.
- `verification/tests/test_git_hooks.sh`, `verification/tests/test_landing_protections.sh` — NEW; the proof.

## Overlap note for the integrator — PR12 files (the "PR13: integration" commit)

PR12 owns `harness/guards.md` and `harness/tests/test_guards.sh`; PR13 edits
neither here (only `harness/adapters/factory_reminders.sh`, the extension
PR12's note reserved for PR13). Two integration edits resolve PR12's forward
references and its test:

1. `harness/guards.md` §6 rows M-1, M-7, M-8, M-9, M-10, M-11, M-12, M-13,
   M-17: replace "PR13" in the Home/Status columns with the landed section —
   M-1 → `../verification/protections.md` §1.1 + the `landing` rule
   (status shipped); M-7 → `../verification/protections.md` §5 (shipped);
   M-8 → `../verification/protections.md` §7 (shipped); M-9 →
   `../planning/board-protocol.md` item 5 (documented); M-10 →
   `../verification/protections.md` §1 (shipped); M-11 →
   `../verification/protections.md` §2 (shipped); M-12 →
   `../verification/protections.md` §4 (shipped); M-13 →
   `../verification/protections.md` §6 (shipped); M-17 →
   `../verification/verify-portfolio.md` "Legs that bring lane-green closer
   to train-green" + `../verification/protections.md` §7 (M-17a/M-17d
   shipped, the rest documented). §3, §9 and §14: "introduced by PR13" →
   the section names above; §7 "Three rules ship as code" → "Eight rules
   ship as code" with the five new ones listed by name and their falsification
   tables pointed at `../verification/protections.md` §10.
2. `harness/tests/test_guards.sh` `fresh_copy`: after
   `cp -R "$SRC/adapters" "$1/adapters"` add
   `mkdir -p "$1/verification" && cp -R "$SRC/../verification/gates" "$1/verification/gates"`
   — the landing and close-out rules read a gate, and a copy of `guards/` +
   `adapters/` alone has none (`verification/protections.md` §10). Verified
   on a patched scratch copy of the script against this branch: 91/91;
   without it, case 9 (falsify on the copy) is red (16 of 101 cases cannot
   replay). The case-9 header comment gains "the copy carries
   verification/gates beside the package".

The `24` count literals move to `27` here: `README.md` and `INSTALL.md`
(below); `gates/README.md` is edited directly by PR13.

---

## 1. `user-level/README.md`

**Anchor:** item 6 ("**Landing authority (optional, INACTIVE by default):**
…"), after "regardless of the policy."

**Append (verbatim):**

```markdown
   Authority is read by the lander at the merge (pr mode) or the push
   (direct-push mode); a pull-request approval is a record of a ruling,
   never a host requirement (`../verification/landing-modes.md` §4.4).
```

## 2. `INSTALL.md`

**Edit 2a — Step 2 item 1.** Replace "Of the 24 scripts, seven are
repo-agnostic decision gates (ADR index, traceability, backlog, number
registry, gitleaks, number provenance, sentinel)" with "Of the 27 scripts,
ten are repo-agnostic decision gates (ADR index, traceability, backlog,
number registry, gitleaks, number provenance, sentinel, and the three
protections gates: close-out, ledger lint, never-weaken — stdlib + git)"
and "Copy the seven to `scripts/`" with "Copy the ten to `scripts/`".

**Edit 2b — Step 2 item 7.** Replace the item with:

```markdown
7. Copy and adapt `verification/ci/*.example` → `.github/workflows/` per
   `verification/ci/README.md` (the regime that ports, the mode table per
   file, the branch policy). They are the source factory's files below an
   English mode header: Python `make verify` arguments, a deployment
   target, a review prompt in Norwegian that names that product's ADRs and
   modules. TRANSLATE every one; the REGIME is what ports: full commit-SHA
   pinning of every action (never tags), secret-gated green-skip (a
   missing secret is a green skip with a ::notice, never a red), minimal
   `permissions:`, single-flight concurrency where it matters. Then apply
   the branch policy once: `python3 verification/protections/bootstrap_ruleset.py`
   (dry run), then `--apply`; run the repository-settings command it
   prints; on a 403 use the classic fallback in `verification/ci/README.md`
   §3; record the date in train-plan §5. Local verify is the gate in both
   landing modes; CI re-verifies and deploys (`verification/landing-modes.md`
   §4.3). `verification/ci/review-prompt.md` is the SHAPE of a review
   prompt — point the review lane at your translation of it, never at the
   file itself, and never store it under `docs/`.
```

**Edit 2c — Step 2, append item 9** (after item 8, "Bind everything into
`make verify`…"):

```markdown
9. Wire the three protections gates: `python3 -m scripts.check_choices_protocol
   --warn` among the cheap gates of the train (WARN on the first train, HARD
   after — `verification/protections.md` §5), `python3 -m
   scripts.check_gate_weakening` over the train range (WARN first, `--hard`
   after), and `python3 -m scripts.check_landing_closeout --state …` as the
   close-out reading (`verification/lander-duties.md` §8). The drift leg and
   the duplicate-id leg run inside the registry and backlog gates you
   already wired.
```

**Edit 2d — Step 5 item 5.** After "No assembler script ships; land from the
plan by hand first (`verification/lander-duties.md` §6)." append:

```markdown
   Choose the landing mode in train-plan §5 — `pr` is the default; a
   project that declares `direct-push` writes its standing reason there
   (`verification/landing-modes.md` §1, §5).
```

**Edit 2e — Step 5, append item 9** (after item 8, the guards item):

```markdown
9. Install the tracked git hooks once in the primary —
   `python3 verification/protections/git_hooks.py install` (`core.hooksPath`,
   shared by every worktree; `status` exits 1 until done) — and declare the
   commit identity and the trailer form in the hook environment
   (`FACTORY_GIT_EMAIL`, `FACTORY_SOURCE_PREFIX`, `FACTORY_TRAILER_RE`,
   `FACTORY_DECISIONS_DIR`; `verification/protections.md` §1). Run
   `bash verification/tests/test_git_hooks.sh` and
   `bash verification/tests/test_landing_protections.sh` on the machine that
   will land.
```

**Edit 2f — Step 7 item 1.** Replace "run full verify through the receipt
launcher, land, sweep the FULL board" with "run full verify through the
receipt launcher, land in pr mode — push the train branch, post the
`local-verify` status from the receipt, open the pull request with the
ledger as its body, take the owner's live ruling as the authority, merge
with `gh pr merge <n> --merge --match-head-commit <HEAD=>`, close out per
`verification/lander-duties.md` §8 — then sweep the FULL board". Append
to the item: "A scratch trial with a bare local origin has no pull-request
host and lands by direct push, saying so in its ledger (`landing mode:
direct-push`, `override reason:`)."

**Edit 2g — Step 7 item 2.** Append: "Then the branch-policy falsification
of `verification/falsification.md` rule 16, in a THROWAWAY repository with
the same payload applied (`verification/ci/README.md` §5) — never on the
real main; record the five outcomes in the smoke protocol."

**Edit 2h — Step 7 item 4.** Replace "Land with the receipt read and `git
push`" with "Land with the receipt read and the merge or push".

## 3. `README.md`

**Edit 3a — the core loop.** Replace

```
    → FULL local verify green → landing authority? (ruling or active
      policy; else HOLD with a decision brief) → push main → CI deploys
```

with

```
    → FULL local verify green → landing authority? (ruling or active
      policy; else HOLD with a decision brief)
    → land: train branch pushed, local-verify status on the verified SHA,
      pull request with the choices ledger as body, merge (default) — or
      the documented direct-push override → CI re-verifies and deploys
```

**Edit 3b — the verification cell of the pillar table.** Replace "24
deterministic gate scripts" with "27 deterministic gate scripts", and after
"lander duties for landing trains (push gated on verify AND on landing
authority — held with a decision brief by default)" insert ", landing modes
(a branch policy that admits a PR merge or a direct push against one
receipt-bound status; PR-mode advisory review and security lanes; git hooks
that carry the landing check into any harness)".

**Edit 3c — the trial paragraph.** Replace "Seven of the 24 gate scripts
port as-is (with `python3` + PyYAML); the rest are stack-specific or the
source factory's domain choices, and the gates README says which." with
"Ten of the 27 gate scripts port as-is (with `python3` + PyYAML; the three
protections gates were added after the trial and need only stdlib + git);
the rest are stack-specific or the source factory's domain choices, and the
gates README says which."
