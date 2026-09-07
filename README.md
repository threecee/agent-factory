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
| **`planning/`** | *Define why, what, how* | Board protocol (GitHub Projects as planning truth), spec discipline, ADR + number registry, backlog discipline with closing evidence, the standing lane brief, the read-only investigation brief that precedes a fix brief when the cause is uncertain, and the execution contract (measurement baseline handed over before dispatch, a named proof owner, two complete rounds per task then park-and-split) |
| **`verification/`** | *Prove that it works* | 24 deterministic gate scripts (one-way ratchets, secret scanning with a working-tree leg, traceability, planning-doc teeth), the verify portfolio, falsification norms, CI in the pinned/secret-gated regime, lander duties for landing trains |
| **`interpretation/`** | *Understand how it really works* | The choices ledger (every decision an agent made on your behalf, audited per handback, one stable ID per choice, scenarios stored with the train), memory conventions that outlive sessions, evaluation practice (persona loops, state parity, honest metrics), investigation practice (instrument-first; investigate before the fix mandate; consumer inventory before any move, split or delete), a worked simplification-review example, the continuous-improvement loop |

Shared infrastructure: **`skills/`** (35 vendored, hash-locked agent skills),
**`harness/`** (lane launcher, worktree ritual, board bootstrap, report
schema with a choices sidecar), **`user-level/`** (what goes into `~/.claude` so the factory works
from any checkout).

## The core loop (one screen)

```
idea → board item (Planned, with a full spec) → PO approval
  → (uncertain cause) read-only investigation on frozen evidence → falsified causal model
  → lane brief from the standing template → parallel lane in its own worktree
    (evidence attached first; agent authors; the wrapper commits and pushes
     the branch; the named proof owner reruns the apparatus; two rounds max)
  → handback → CHOICES AUDIT (ledger entry per invented decision)
  → landing train: --no-ff pinned SHAs → cross-checks → cheap gates
    → FULL local verify green → push main → CI deploys
  → board sweep (Done + archive) → evaluation → findings → new board items
  → memory: lessons that survive the session
```

Three non-negotiables inherited from the source factory:
1. **Falsify the apparatus before the product** — a gate or test that has never
   been seen red proves nothing.
2. **Never weaken a criterion to pass** — ratchets move one way; baselines are
   updated only through each gate's own `--update` mechanism.
3. **Honesty on every surface** — unavailable is never rendered as empty;
   advisory output is labeled advisory.
