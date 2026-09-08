# Skill routing by factory step

This file is the home of the routing table INSTALL step 4 asks you to
translate into the repo's operations doc. It says which vendored skill a
factory step reaches for and where the overlap is resolved; it does not
restate any skill. Harness-neutral: a skill that names a harness-specific
dispatch form (`claude -p`, `codex exec`) is read through the repo's own
dispatch translation. Where a step is governed by a package doc, that doc
owns the rule and the skill executes it.

## The table

| Factory step | Skill(s) | When and how; the owning doc |
|---|---|---|
| Foggy work before planning | `explore-unknowns` | Before a lane brief is written for unfamiliar terrain (new subsystem, unclear requirement). The map feeds the spec or the brief. |
| Design / specification | `brainstorming` → `write-spec` | Multi-slice or risky work is sliced into independently verifiable pieces; `writing-plans` remains for single-document plans. Spec shape: `../planning/core-model.md` rung 2. |
| Implementation from a spec | `implement-spec` (or `implement-spec-with-codex` when a coding CLI authors) | The orchestrator runs the loop; the lane authors in its worktree under the standing brief (`../planning/lane-brief-template.md`); the wrapper commits (`../harness/worktree-ritual.md`). |
| Implementation — test discipline | `test-driven-development` + `write-tests` + `verification-before-completion` | Test first; `write-tests` owns test quality (pin behaviour, not implementation — `../verification/verify-portfolio.md` "Known vacuity classes"); fresh evidence before any done claim. |
| Bug / root-cause lane | `systematic-debugging` | Root cause before a fix is proposed. When the cause is uncertain the read-only investigation brief precedes the fix brief (`../planning/investigation-brief-template.md` §0 says when). |
| **Choices audit (every handback)** | `audit-choices` | **Mandatory transaction point.** Verdict per choice, one stable ID, scenario stored with the train — `../interpretation/choices-ledger-README.md` owns the protocol. Unsound → fix round before assembly. |
| Assembly / closeout | `review` (sequences `refactor-clean` → `code-review` → `write-docs`) | On the assembled train before full verify, in that order. `independent-lane-review` / `requesting-code-review` where reviewer independence is required; panel models come from the operator's model policy (`../harness/model-policy.md`), never from this table. |
| Move / split / rename / delete | `refactor-clean` | Runs the consumer inventory first (`../interpretation/investigation-practice.md` "Consumer inventory"). |
| Lane end | `finishing-a-development-branch` | Translated to the wrapper/lander split: the wrapper pushes the branch, only the lander pushes main (`../planning/execution-contract.md` §6). |
| Visual verification | `screenshot-critique` · `compare-screenshots` · `preview-shots` | `screenshot-critique` before any visual defect is declared fixed (a second, unprimed look); `compare-screenshots` judges A/B; `preview-shots` when the owner views locally. |
| Performance work | `audit-performance` | Bounded-work / forward-progress checks when hunting freezes or latency; complements instrument-first (`../interpretation/investigation-practice.md`). |
| Owner-facing explanation | `eli5` | Reports and the choices ledger are written in this register. |
| Second opinion | `codex` / `claude` | Harness-symmetric second opinions; model and effort per the operator's policy, not the skill's built-in default (`../harness/model-policy.md` §4). |
| Spec closeout | `close-spec` | Archive a shipped spec and rewrite it for the later reader. |
| Bounded bulk reading (pilot) | `bulk-reader` · `log-triage` · `handback-digest` | Inert until `../harness/bulk-read-contract.md` §4 is bound and §5/§7 have run; never registered by installing. |
| Skill authoring | `write-skills` + `eval-skills` | A change to a vendored skill goes through these; the lock is regenerated with `verify_skills_lock.py --update` and the reason recorded in ATTRIBUTION.md. |
| Parallel dispatch | `../harness/run-lifecycle.md` (launcher) · `../harness/worktree-ritual.md` (one lane, one writer) | Parallelism is the launcher's, never a skill's. |

## Rules

1. **Overlap is resolved by the row, not by the newest skill.** Where two
   skills could apply, the step's row names the one that owns it.
2. **Trivial lanes skip the skill pass.** A version bump or a one-row docs
   change follows the brief and the ordinary gates; a skill pass there is
   ceremony. The choices audit has the same exemption: a trivial pass with
   no choices of its own yields one line in the ledger, not an empty ritual.
3. **No model names in skills.** A skill that carries a default model or
   effort (`claude` does, upstream) is overridden by the operator's dated
   policy at dispatch (`../harness/model-policy.md` §4); the package does
   not edit upstream defaults, it parameterizes past them.
4. **Translation, not duplication.** The repo's operations doc carries this
   table translated to its own paths and dispatch forms; it does not copy
   the skills' procedures into the lane brief.
5. **Provenance is the lock.** `skills-lock.json` (verified by
   `verify_skills_lock.py --check`) is the only mechanism that says the
   installed skills are the shipped ones; a routing table over unlocked
   skills routes to unknown text.
