# Agent Factory

An agent-driven software factory covering the full SDLC — from idea to
production and continuous improvement. Distilled from a production factory
that ran multi-lane parallel builds, landing trains, and PO-governed decision
loops for months; everything repo-specific has been removed, everything
deterministic (gates, skills, CI, harness scripts) is included verbatim.

**Installation is agent-driven:** point an LLM agent (Claude Code, codex or
similar) at `INSTALL.md` inside your target repo. The agent parameterizes the
deterministic pieces against your language, build chain and domain.

## The three pillars

| Pillar | Question it answers | Contents |
|---|---|---|
| **`planning/`** | *Define why, what, how* | Board protocol (GitHub Projects as planning truth; decision briefs, one notification per transition, derived views), spec discipline, ADR + number registry, backlog discipline with closing evidence, the standing lane brief, the read-only investigation brief that precedes a fix brief when the cause is uncertain, and the execution contract (measurement baseline handed over before dispatch, a named proof owner, two complete rounds per task then park-and-split) |
| **`verification/`** | *Prove that it works* | 24 deterministic gate scripts (one-way ratchets, secret scanning with a working-tree leg, traceability, planning-doc teeth — classified by what ports to a non-Python repo, with a JavaScript ratchet and boundary test as the worked substitution), the verify portfolio, falsification norms (with a runnable identity-and-history example: gates follow the consumer's identity, falsified in both directions), evaluation readiness (pre-flight smoke, offline functional trial and AI evaluation kept apart, one receipt schema), CI in the pinned/secret-gated regime, lander duties for landing trains (push gated on verify AND on landing authority — held with a decision brief by default) |
| **`interpretation/`** | *Understand how it really works* | The choices ledger (every decision an agent made on your behalf, audited per handback, one stable ID per choice, scenarios stored with the train), memory conventions that outlive sessions, evaluation practice (what each evaluation type proves, intended product mode, state parity, honest metrics), investigation practice (instrument-first; investigate before the fix mandate; consumer inventory before any move, split or delete), a worked simplification-review example, the continuous-improvement loop |

Shared infrastructure: **`skills/`** (38 vendored agent skills under a
content lock — `skills-lock.json`, verified by `verify_skills_lock.py`,
falsified by its test — and the routing table by factory step,
`ROUTING.md`), **`harness/`** (parameterized lane launcher with run-bound
receipts and its test, the run lifecycle, worktree ritual, board bootstrap,
report schema with a choices sidecar, the train plan with its resource
contract, the artifact-bank contract — pristine acceptance, isolated copies,
receipts that tell a deliberate fake from a promised-but-failed role — the
measurement-gated bounded bulk-read contract, and the model policy: roles
and parameters are the factory's, model names are the operator's, dated,
probed and revisited — `harness/model-policy.md`),
**`user-level/`** (what goes into `~/.claude` so the factory works
from any checkout: the global snippet, the local bank root, the operator's
model-policy file from its example, plus the INACTIVE landing-policy
example — the only place push authority can be granted, and only by the
owner).

Tried against a foreign repo: `INSTALL.md` was run end to end on a Node
hello-world with no Python project on 2026-09-06
(`verification/examples/install-trial-node.md`). Seven of the 24 gate
scripts port as-is (with `python3` + PyYAML); the rest are stack-specific or
the source factory's domain choices, and the gates README says which.

## The core loop (one screen)

```
idea → board item (Planned, with a full spec) → PO approval
  → (uncertain cause) read-only investigation on frozen evidence → falsified causal model
  → lane brief from the standing template → parallel lane in its own worktree
    (evidence attached first; agent authors; the wrapper commits and pushes
     the branch; the named proof owner reruns the apparatus; two rounds max)
  → handback → CHOICES AUDIT (ledger entry per invented decision)
  → landing train (independent ready lanes share one): --no-ff pinned SHAs
    → cross-checks → build → cheap gates → resource check
    → FULL local verify green → landing authority? (ruling or active
      policy; else HOLD with a decision brief) → push main → CI deploys
  → board sweep (Done + archive) → evaluation on an isolated bank copy
    → findings → new board items
  → memory: lessons that survive the session
```

Three non-negotiables inherited from the source factory:
1. **Falsify the apparatus before the product** — a gate or test that has never
   been seen red proves nothing.
2. **Never weaken a criterion to pass** — ratchets move one way; baselines are
   updated only through each gate's own `--update` mechanism.
3. **Honesty on every surface** — unavailable is never rendered as empty;
   advisory output is labeled advisory.
