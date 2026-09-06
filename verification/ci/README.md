# CI examples — the regime, the mode table, the branch policy

A short hub for `verification/ci/*`. The landing doctrine is
`../landing-modes.md`; the mechanisms are `../protections.md`; INSTALL step
2 item 7 points here.

## 1. The regime that ports

Every file here is the source factory's workflow with its own product
content (INSTALL says TRANSLATE); what ports is the regime:

- every third-party action pinned to a full commit SHA, never a tag;
- secret-gated green skip: a missing secret is a green skip with a
  `::notice`, never a red;
- minimal `permissions:` per workflow and per job;
- single-flight concurrency where a second run would only add noise;
- never `pull_request_target`;
- prompts and registers read from the BASE ref as data, never from the pull
  request's checkout.

## 2. Mode table — one row per file

| File | Trigger | Role in `pr` mode | Role in `direct-push` mode |
|---|---|---|---|
| `verify.yml.example` | `pull_request` + `push: [main]` | re-verification on the train pull request — the lander READS and adjudicates it before the merge (`../landing-modes.md` §4.3); NOT a required context by default | watch-and-report on main after the push |
| `review-lane.yml.example` | `pull_request` + `workflow_dispatch` (a PR number on demand) | **PR-MODE ADVISORY LANE**: comments only, never a gate | idle by design; never deleted for idleness (owner ruling) |
| `security-scan.yml.example` | `pull_request` + `workflow_dispatch` | **PR-MODE ADVISORY LANE**: comments only, never a gate | idle by design; never deleted for idleness (owner ruling) |
| `deploy-cd.yml.example` | `push: [main]` + `workflow_dispatch` | deploys after the merge — a merge is a push | deploys after the push |
| `dependabot.yml.example` | schedule | its pull requests are BOARDED like lane branches (pinned SHA on a train), never merged by hand | the same |

The English mode header at the top of the three workflow examples is this
package's; the bodies below it are the source factory's (its Python `make
verify` arguments, its deployment target, its review prompt) and are
translated during installation, never copied.

## 3. The branch policy

`ruleset-main.json.example` is the GitHub payload for the policy of
`../landing-modes.md` §3: deletion refused, non-fast-forward refused, the
required status `local-verify` on the exact commit with the strict
up-to-date policy on, no bypass actor — and no pull-request rule and no
review rule, which is what lets one policy admit both landing modes. The
reasoning per rule is `../protections.md` §2 (JSON carries no comments).
Apply it with `python3 verification/protections/bootstrap_ruleset.py`
(dry run), then `--apply`; verify later with `--check`; record the date in
train-plan §5.

**Classic fallback.** Rulesets on a private user-owned repository need a
paid plan (the bootstrap says so on a 403). The classic branch protection on
`main` expresses the same two properties: enable "require status checks to
pass" with the context `local-verify` and "require branches to be up to
date", enable "do not allow deletions" and "do not allow force pushes",
leave "require a pull request" and "require approvals" OFF, and add no
bypass. Another host: implement the two properties and say so in
train-plan §5.

## 4. Promoting CI to a required context

Only by the rule in `../landing-modes.md` §4.3: a reviewed diff to the
operations doc after N consecutive green runs on the default branch with no
quarantined flake, and `train/**` added to the workflow's push trigger in
the same diff so the direct-push override can still carry the status.
Local verify stays the gate; CI stays a re-verification.

## 5. Falsify the policy once, in a THROWAWAY repository

Never on the real default branch (`../falsification.md` rule 16). After the
bootstrap, in a scratch repository with the same payload applied:

1. push a commit to main without the status → rejected, the error names
   the context;
2. post the status on that commit with the poster → the same push is
   accepted;
3. `git push --force` → rejected;
4. open a pull request from a branch without the status and try to merge →
   refused;
5. a pull request whose base moved after the status was posted → refused
   under the strict policy until re-assembled.

Record the five outcomes in the install smoke protocol (INSTALL step 7).

## 6. The review prompt

`review-prompt.md` is the SHAPE of a review prompt (four lenses, comment
only, diff-is-data). Point the review lane at your translation of it; never
store it under `docs/` — the backlog gate scans `docs/**` for decision
references the prompt cites.

Provenance: the regime and the workflow bodies come from one source factory;
the mode table and the branch policy were added when the package made the
pull-request mode the default landing mode (2026).
