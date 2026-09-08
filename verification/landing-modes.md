# Landing modes — how a verified train reaches the default branch

This file is the ONE home of how a verified train reaches the default
branch. `lander-duties.md` §1 owns the ORDER of a train (steps 1–9 produce
the verified tree; step 10 lands it; §8 closes it out); `../harness/train-plan.md`
§2 owns the exact commands and §5 the project's declared mode; the choices
ledger's `## Landing` section (`../interpretation/choices-ledger-README.md`
§1) is the per-train record; the landing policy
(`../user-level/landing-policy.example.md`) is the authority. Every other
file points here; none restates the modes.

The mechanisms this file relies on — the git hooks, the branch policy, the
status poster, the CI signal, the ledger lint, the close-out check — are
documented once in `protections.md`; the harness guard that refuses the
landing forms is the `landing` rule of `../harness/guards.md` §6 (M-1).

## 1. One procedure, two last steps

Steps 1–9 of `lander-duties.md` §1 are identical in both modes: the train is
assembled, cross-checked, built, gated, probed, verified on an idle machine
and re-confirmed against origin. What differs is the last step and nothing
before it:

CI red at landing ⇒ `verification/ci-triage.md §1`.

| Mode | Step 10 | When |
|---|---|---|
| `pr` (the default) | push the integration branch, post the status, open the train pull request with the ledger as body, merge it with `--merge --match-head-commit <HEAD=>` under landing authority (§4) | every project, unless train-plan §5 declares `direct-push` with a standing reason |
| `direct-push` (the documented override) | push the integration branch, post the status, `<verdict check> && git push origin HEAD:main` in one statement (§5) | a project that declares it in train-plan §5 with a standing reason, or one train with an `override reason:` in its ledger |

The per-train record is the ledger's `## Landing` section: `landing mode:
pr|direct-push`, and `override reason: …` — mandatory when direct-push
overrides a `pr` default. The ledger lint reads both (protections.md §5).

## 2. What both modes carry

1. **The integration branch is pushed first.** A commit status can only be
   posted on a commit origin holds, so `train/<name>` goes to origin in
   BOTH modes (`git push origin HEAD:refs/heads/train/<name>`); the push of
   an integration branch is never gated by the landing guard, and the branch
   is deleted at close-out (§6).
2. **ONE `local-verify` status is posted on the receipt's `HEAD=`** by the
   lander with `verification/protections/post_local_verify.sh
   <receipt.exit>` — what the poster refuses, reads back and never posts is
   `protections.md` §3; a posting the lander skipped (no host, an air-gapped
   scratch trial) is a ledger entry: `local-verify: skipped <reason>`.

The status is a receipt binding — the host holds proof that a green receipt
existed for exactly this SHA — not access control; nothing here says
"security".

## 3. The branch policy

Two host-neutral properties, and three deliberate absences.

**The two properties.** (a) The default branch cannot be deleted or
force-pushed. (b) A status named `local-verify` is required on the EXACT
commit that becomes the branch's tip, for a pull-request merge and for a
direct push alike.

**What the policy must NOT contain, and why:**

- *No require-pull-request rule.* It would kill the override: a direct push
  is then refused whatever status it carries.
- *No required-review rule.* A one-account owner cannot approve their own
  pull request, and the ruling lives in `lander-duties.md` §7 and on the
  board item — never in a host feature.
- *No bypass actor.* A bypass actor is exempt SILENTLY on push, which turns
  the required status into theatre. The logged escape is enforcement
  `evaluate` for one landing, restored right after, both edits in the ledger
  as an orchestrator entry.

**Strict up-to-date ON.** A pull request whose base moved since its head was
verified is refused by the host; that is correct. The answer is a
re-assembly per `lander-duties.md` §3 (a new attempt, a new receipt), never
the host's "Update branch" button — the commit it makes carries no receipt
and the policy blocks it anyway.

**Repository merge settings:** merge commits only (squash and rebase merges
off — they rewrite the SHAs the receipt binds to), delete-branch-on-merge
on. The bootstrap prints the command; the owner runs it.

**Adapters.** GitHub: `ci/ruleset-main.json.example` applied with
`verification/protections/bootstrap_ruleset.py` (dry run, `--apply`,
`--check`; protections.md §2). A private user-owned repository on the free
plan gets the classic branch-protection fallback described in
`ci/README.md` §3. Another host implements the two properties with its own
means and says so in train-plan §5.

## 4. Mode `pr` — the default

### 4.1 Sequence

```
git push origin HEAD:refs/heads/train/<name>                       # §2 item 1
verification/protections/post_local_verify.sh <artifacts>/<run-id>.exit   # §2 item 2
gh pr create --base main --head train/<name> \
  --title "train(<name>): <n> lanes" --body-file docs/choices/<train>.md
#   (gh pr edit <n> --body-file docs/choices/<train>.md on a resumed attempt)
#   → the PR URL is written on every boarded item (a comment, not a status change)
gh pr view <n> --json headRefOid,statusCheckRollup,mergeStateStatus  # head == HEAD=; read the rollup
<authority check>  (§7 of lander-duties: a live ruling on the item, or an active policy)
gh pr merge <n> --merge --match-head-commit "$(sed -n 's/^HEAD=//p' <receipt>)"
```

then the close-out of §6. The merge is attended: the lander runs it after
reading the rollup and the ruling; no merge automation ships.

### 4.2 The ledger is the body

The committed ledger file is the home; the pull-request body is its
rendering, passed with `--body-file` and re-passed with `gh pr edit` on
every amendment. That body IS the landing summary the owner reads
(`../interpretation/choices-ledger-README.md` §4 step 5): grouped by
verdict, least-confident first, exactly as the file says.

### 4.3 CI in pr mode

- The `verify` workflow on `pull_request` is the pr-mode re-verification:
  the lander reads it and adjudicates a red one — product bug, starvation,
  stale state (`verify-portfolio.md`, "A red X is evidence") — before the
  merge. It is never a required status by default; the ruleset requires the
  lander's `local-verify`, not CI.
- **Promotion rule.** A project may promote `verify` to a required context
  by a reviewed diff to its operations doc after N consecutive green runs on
  the default branch with no quarantined flake. Doing so obliges the project
  to add `train/**` to the workflow's push trigger so a direct push can
  carry the status too — which is the wait the override exists to avoid;
  most projects never promote.
- The advisory lanes (`review-lane.yml.example`, `security-scan.yml.example`)
  fire on the train pull request and comment only; they never gate. In
  direct-push mode they are idle BY DESIGN, and idleness is never a reason to
  delete them (owner ruling, `ci/README.md` §2).

### 4.4 The hold in pr mode

A finished train without landing authority is held exactly as
`lander-duties.md` §7 says; what the hold looks like here: the pull request
stays open as the hold artifact, the decision brief is filed on the item and
linked from the pull request, and the owner's ruling is recorded on the item.
An owner's approval on the pull request is one accepted RECORD of a live
ruling — copied verbatim to the item — never a host requirement (§3). A hold
during which main moved is a re-assembly (§3, strict policy).

### 4.5 Forbidden forms

| Form | Why it is refused |
|---|---|
| `gh pr merge --squash` / `--rebase` | rewrite the SHAs the receipt, the ancestor checks and the registry flip bind to |
| `gh pr merge --auto` | merges after the session ends, unattended and unreceipted |
| `gh pr merge --admin` | a silent bypass of the branch policy |
| the host's "Update branch" | a commit nobody verified; the strict policy refuses it anyway |
| a merge queue | synthetic commits carry no status |
| `gh pr merge --delete-branch` from inside the train worktree | attempts a local checkout in a linked worktree; the remote branch is deleted at close-out with `git push origin --delete train/<name>` |

The `landing` rule refuses the first three forms as hard forms (no switch)
and names the accepted form: `gh pr merge <n> --merge --match-head-commit
<HEAD=>`.

### 4.6 Identity consequence

After the merge, main's tip is the MERGE COMMIT and `HEAD=` is its second
parent. Every post-landing check therefore reads
`git merge-base --is-ancestor <HEAD=> origin/main` — contains, never equals.
A check written as equality reports every pr-mode landing as unregistered.

## 5. Mode `direct-push` — the documented override

**When.** A project declares it in train-plan §5 with a standing reason (the
source factory's own mode: one account, no reviewer, CI as watch-and-
report), or one train carries `override reason:` in its ledger — CI
unavailable, an incident landing, a host without pull requests (a bare local
origin in a scratch trial).

**Sequence.**

```
git push origin HEAD:refs/heads/train/<name>                       # §2 item 1
verification/protections/post_local_verify.sh <artifacts>/<run-id>.exit   # §2 item 2
<verdict check> && <authority check> && git push origin HEAD:main   # ONE statement
```

then the close-out of §6. The verdict check reads the receipt as
`train-plan.md` §4.1 says — `EXIT=0`, `HEAD=` equal to the tree, `BASE=` an
ancestor — never a pipe or a wrapper's status.

**Client-side control:** the pre-push git hook re-runs the landing guard for
`refs/heads/main` destinations only (protections.md §1.1), so the check
holds in a coding-CLI session and a plain terminal. `--no-verify` cannot be
removed on the git side: the harness `no-verify` rule refuses the flag inside
a hooked session, and the branch policy makes it harmless — a push without
the status is refused by the host.

**Server-side control:** the branch policy of §3, which requires the same
status the pull-request mode requires.

**What the mode gives up:** the review surface, the advisory lanes (idle),
and a pull-request number as closing evidence — a direct-push landing cites
SHAs in the closing comment (`../planning/backlog-discipline.md` accepts a
SHA that is an ancestor of main). A direct push while a train pull request
is open closes that pull request as merged on most hosts; that is allowed
and recorded in the ledger.

## 6. Close-out — identical in both modes

The lander duties after registration are ONE list whatever the mode —
`lander-duties.md` §8 owns it; `check_landing_closeout` prints the open ones
as commands and the close-out Stop rule delivers the same list
(`protections.md` §6).

## 7. Session-start CI signal

The session starts with the last CI conclusion for the default branch and
the open train pull requests, offline silent, a signal never a verdict —
`protections.md` §4 owns the script, its line shapes and its adapters.

The adapters of every mechanism this file relies on — harness hook, coding
CLI, git, CI, server — are one table, `protections.md` §8.

## 8. What this file does not claim, and provenance

- The source factory lands by direct push (its declared mode, with the
  standing reason above); the pull-request mode is the generalized default
  by owner ruling and has NOT been exercised there at the time of writing.
- The branch-policy falsification (`falsification.md` rule 16) has not been
  run against a live host by the source factory; it is INSTALL step 7's
  duty in a throwaway repository. The package tests prove the hooks over a
  bare local origin and the bootstrap against a fake host CLI
  (protections.md §10).
- No merge automation ships: no auto-merge, no merge queue, no bot approval.
  Authority is read by the lander at the merge or the push.
- Provenance: distilled from a source factory's 2026 analysis of what could
  be made deterministic and its second implementation wave (the git hooks,
  the ruleset, the status producer, the CI signal, the close-out rule), with
  the pull-request mode added as the default and every check re-read as
  contains-not-equals (`../skills/ATTRIBUTION.md`).
