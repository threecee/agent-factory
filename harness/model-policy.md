# Model policy — roles are the factory's, names are the operator's

This file is the one home of how a model and an effort level reach a lane.
The factory defines **roles** and the **parameters** that carry a choice;
the operator keeps a **dated policy** that binds each role to a model for a
stated period (`../user-level/model-policy.example.md` is the template,
`~/.claude/model-policy.md` the live file). No template, skill, launcher
or doc in this package names a model as an eternal default. Where this file
says "the source factory", it reports one operator's dated policy as
provenance (§10), not as a ranking.

## 1. Three things a new operator keeps apart

An inherited policy answers three different questions. Confusing them is
how a retired provider gets dispatched into, or a temporary exception
becomes the default.

| Question | Answered by | Test |
|---|---|---|
| **Role policy** — which model does role R get, at what effort, decided by whom? | the `roles:` table of the live policy, inside its validity window | Is today within `valid_from`..`review_by`? Is the row `active`? |
| **Availability** — does that model answer, right now, on this account? | a dated probe (§5), never the table | When was `last_probed`, with what result? A row is not a probe. |
| **History** — what was tried, retired, granted temporarily, and why? | `history:` and `authorizations:` with `revoked_at` set | Does the row have an end date or a `revoked_at`? Then it is history, not policy. |

A name in a table proves none of the three by itself. A working alias and
a working worker are also different things: an alias that resolves at the
provider can still front a model that cannot complete the role's task
(the source factory's bulk-read probe proved the worker answered, not that
the role was served — `bulk-read-contract.md` §3 rule 1).

## 2. Roles, not models

The factory names roles by what the work needs. The policy fills the model
column; nothing here does.

| Role | What it does | Effort rule | Who decides a deviation |
|---|---|---|---|
| Orchestration | briefs, rulings, choices audits, landing; authors only disclosed train fixes | match depth to the ruling's irreversibility | the owner changes the tier |
| Implementation lane | authors product, test and docs changes inside its worktree | default the policy's `effort`; lower for bounded mechanical bulk | orchestrator selects effort inside the role; owner changes model or tier |
| Cheap judging and reduction | drift judges, scoring, bulk classification, digests, bulk-read workers | volume dominates; escalate the *task* rather than treating effort as a substitute for a stronger tier | orchestrator assigns work inside the role; owner changes the tier |
| Investigation and second-family review | read-only root-cause digs (`../planning/investigation-brief-template.md`), model-diverse review panels | provider default unless the policy says otherwise | orchestrator selects the panel; owner changes the tier |
| Demanding analysis and verification | cross-cutting specs, throughput analysis, high-risk audits | high; adjusted by the irreversibility rule | **owner admits each piece of work** to this tier; the orchestrator records the rationale in the brief and the ledger |
| Product and evaluation identities | the product's own reasoner, evaluation drivers and judges | the product/eval profile, not lane effort | the product/eval decision track (§8) |

1. **Effort follows irreversibility, not diff size.** Normative docs,
   ratchets, migrations, cross-cutting constraints and high-risk
   verification get the high setting; reversible mechanical bulk gets the
   lower one. Set effort explicitly on every dispatch; never rely on a
   CLI default.
2. **A model or tier change is an owner decision** (`../planning/board-protocol.md`
   "Decision needed"). **An effort change inside an approved role is an
   orchestrator call**, recorded in the lane brief header and, when it
   deviates from the policy's default, as a choice in the ledger.
3. **A role deviation is always recorded**, even when it is allowed: which
   role, which row, why, and for which lane. The ledger is where the owner
   reads it (`../interpretation/choices-ledger-README.md`).
4. **A skill's built-in default is not policy.** Vendored skills that
   ship with a model or effort default (the `claude` skill does, upstream)
   are invoked with the policy's values; the default is what the skill does
   when nobody told it better.

## 3. The operator policy file

`~/.claude/model-policy.md` (user-level: it is a property of the operator's
accounts and machine, not of a repository). Required fields, all in the
example file:

| Field | Meaning | Rule |
|---|---|---|
| `valid_from` | the date the owner signed this version | never in the future (`../planning/core-model.md`, decision hygiene) |
| `review_by` | the date the names must be revisited | mandatory; past it, §3 rule 3 applies |
| `signed` | the owner's name | the policy is a grant, like the landing policy |
| `roles:` one row per §2 role | `model`, `provider`, `invocation`, `effort`, `state` (`active` \| `retired`), `last_probed`, `probe_result` | the row is unusable while `state` ≠ `active` or `last_probed` is older than the wave |
| `authorizations:` | temporary or local grants: `granted`, `by`, `scope`, `until`, `revoked_at` | every entry has an end condition; a lifted grant keeps its row with `revoked_at` set and moves to history |
| `history:` | retired rows and lifted grants with the reason | read for provenance, never for dispatch |

1. **One live policy.** Two files, or a table in the repo that disagrees
   with the user-level file, is two sources of truth; the user-level file
   wins and the repo's operations doc points at it by path.
2. **Names are revisited on `review_by`.** Providers rename, retire and
   reprice models; a name from before that date is a hypothesis about
   availability, not a fact. The source factory's roster was written with a
   two-day review horizon (§10) precisely because two of its rows had
   changed state within the same day.
3. **A policy past `review_by` is stale, not void.** Reversible lanes may
   still dispatch under it; the brief header says `policy: stale since
   <date>`; the orchestrator files ONE decision brief asking for the
   re-signed policy; no work is admitted to the demanding tier and no new
   authorization is granted until it is re-signed. This keeps the factory
   running without letting a stale roster silently become permanent.
4. **A `retired` row is never dispatched into.** Retirement is a fact
   about availability that has been promoted to policy; the row stays for
   history with the reason (a provider 404, a paid successor not admitted,
   a quota wall).

## 4. Parameters at dispatch

The launcher takes the CLI invocation verbatim as argv after `--`
(`run-lifecycle.md` §3: a provider override is "just more argv"); the
policy is what fills those tokens. Three places carry the choice, in this
order, and nowhere else:

1. **The lane brief header** (`../planning/lane-brief-template.md` §1 adds
   the line): `Model/effort: <role> → <model> @ <effort>, policy
   ~/.claude/model-policy.md (valid_from <date>, review_by <date>),
   probed <date>`. The lane never chooses; the brief tells it what it runs
   as, so the report carries provenance.
2. **The launcher argv**: the model and effort tokens as the CLI wants
   them, e.g. `-- <cli> exec --cd "{worktree}" -m <model> -c
   effort=<level> "{brief}"`. The launcher validates nothing about the
   model — it is not its business (`run-lifecycle.md` §3) — and records
   the argv in the start receipt, which is the provenance the train reads.
3. **The report**: `proof:` or `measurements:` may cite the model when a
   result depends on it (an evaluation always does — `verification/evaluation-readiness.md`
   §4 receipt roles); a ledger entry names the policy row when the lane
   deviated from it.

A template or skill that contains a model name as a literal default fails
this section; the fix is a placeholder and a pointer here, not a newer
name.

## 5. Availability is a probe, not a claim

1. **Never assert that a model exists, or does not, from a cached catalog
   or from memory.** Both lag the providers. The source factory once
   "proved" from a bundled catalog that a model the owner had just named
   did not exist; it had shipped after the snapshot. When a model is in
   question, check the live source (the provider's models endpoint or its
   published model list); when the operator names a model, take it as
   ground truth and find the exact id string.
2. **Probe before a wave.** One cheap call per intended provider and model
   (a one-token completion) that proves the endpoint answers on this
   account; record `last_probed` and `probe_result` on the row. Do not
   dispatch a wave into a known-exhausted limit; back off, re-probe, then
   escalate — a limit that dies mid-wave is a circuit breaker
   (`../planning/execution-contract.md` §3–§6), not a retry.
3. **Rate-limit and billing verdicts come from a named field**
   (`run-lifecycle.md` §7), never from a substring. A billing or auth
   failure outranks a rate limit: waiting fixes the second, not the first.
4. **A probe is for a wave, not forever.** Its date is on the row; a probe
   older than the wave it precedes is history.
5. **Alias ≠ worker.** A probe proves the endpoint answered. Whether the
   model can do the role's work is proven by the role's own acceptance:
   for a bulk-read worker, the worker-down trial and the off/on pilot
   (`bulk-read-contract.md` §5, §7); for an implementation lane, approved
   deliveries (§7 here).

## 6. Temporary capacity policies and local authorizations

A subscription hits its limit mid-wave; a free overflow provider is retired
by its host the same morning. The owner grants an exception: for two days,
lanes may run on a different harness's subagents and investigations on
another CLI's newer model. Three hours later the owner resets the quota
and lifts the exception. Three lanes ran under it. This happened in the
source factory on one day (§10); the rules are what survives it.

1. **An authorization is a row with an end.** `granted` (date and time),
   `by`, `scope` (which rule it lifts, for which roles), `until` (a date or
   an event), `revoked_at` (set when lifted early). An exception without an
   end condition is a policy change and goes through §2 rule 2.
2. **Lifting is recorded, never deleted.** The row keeps its dates and
   gains `revoked_at` and the reason; it moves under `history:` at the next
   re-signing. The lanes that ran under it are named in the same row, so a
   later reader of the choices ledger can see why those lanes carry a
   different model than the policy's default.
3. **An exception never becomes the default by expiry.** When `until`
   passes, the previous row is in force again; nobody has to act. If the
   owner wants the exception to continue, that is a new dated row.
4. **A retired provider is history, not a fallback.** A row that says
   "fallback: <retired provider>" is a stale instruction; the audit flags
   it, the next re-signing removes it.
5. **A standing bar may be lifted temporarily only by the owner, in the
   file.** A rule such as "no subagents of harness X without stated
   justification" is lifted by an authorization row, not by a chat
   message; the row is what the lane brief cites.
6. **A local authorization is not portable.** What an owner grants for one
   machine, one account and one period is that owner's; the factory ships
   none, exactly as it ships no landing authority
   (`../user-level/landing-policy.example.md`).

## 7. Evidence for a model choice

A model name is not evidence; approved deliveries are. When the owner asks
whether a tier is worth its cost, compare per approved task, over a stated
period and denominator: complete rounds per approved task
(`../planning/execution-contract.md` §3), first-round red trains, invalid
evaluations, rework, total time and actual model consumption (input and
output tokens of every role involved — a smaller orchestrator context can
cost more in total, `bulk-read-contract.md` §7). Log size is not token
consumption. A wave of one night is an example, not a control group.

The source factory did not have a controlled comparison showing that its
distribution of roles to models was optimal; its roster was an owner
decision with a review date. Treat any inherited roster the same way.
Measured consumption and the cost report a choice under this section cites
are defined in §11; a model choice without that receipt is not evidence.

## 8. The product/factory namespace boundary

A model that evaluates or serves the product does not thereby become a
factory worker, and factory tooling never uses the product's identity or
its sanctioned key. Evaluation identity is part of the measurement
(`../interpretation/evaluation-practice.md`): every swap is explicit in the
receipt, and a run whose product role was promised but not served is
reported as such (`artifact-bank.md` §5). The policy's product rows exist
so the boundary is written down, not so the factory dispatches into them.

## 9. Worked example — reading an inherited policy

A new operator inherits this file (excerpt) on 2026-09-12:

```yaml
valid_from: 2026-09-05
review_by: 2026-09-07
signed: <owner>
roles:
  - role: implementation lane
    model: <vendor-a-lane-model>
    provider: vendor-a subscription
    invocation: "<cli> exec --cd {worktree} -m <model> -c effort={effort}"
    effort: high
    state: active
    last_probed: 2026-09-05
    probe_result: ok
  - role: overflow
    model: <free-stealth-model>
    provider: aggregator
    state: retired
    reason: "aggregator returned 404 on 2026-09-05; paid successor not admitted"
authorizations:
  - granted: 2026-09-05T12:05
    by: <owner>
    scope: "lanes may run as harness-B subagents; investigations on <cli-c> <newer-model>"
    until: 2026-09-07T10:15
    revoked_at: 2026-09-05T14:25
    reason: "owner reset the vendor-a quota"
    lanes_ran_under: [c1-s2, c1-s3, c1-s4]
```

What the operator must conclude before dispatching anything:

| Question | Answer from the file | Rule |
|---|---|---|
| Which model does an implementation lane get today? | `<vendor-a-lane-model>` @ `high` — **but** the policy is stale (`review_by` 2026-09-07 < today) | §3 rule 3: dispatch reversible lanes with `policy: stale since 2026-09-07` in the header; file one decision brief for re-signing; admit nothing to the demanding tier |
| May the overflow row be used as a fallback? | No — `state: retired` with a reason | §3 rule 4, §6 rule 4 |
| Is the harness-B subagent exception active? | No — `revoked_at` is set; it is history | §6 rule 2; the three named lanes explain why the ledger shows a different model for them |
| Was `<vendor-a-lane-model>` available? | It answered on 2026-09-05; that probe is a week old | §5 rule 4: probe again before the wave; a row is not a probe |
| Can the operator rename the lane model to this month's newer version? | Not alone — a model change is an owner decision | §2 rule 2: decision brief, then a re-signed policy with a new `valid_from` |

An operator who reads the table as "lane model = X, fallback = Y, subagents
allowed" has confused all three questions of §1; the file is written so
that each answer is a field, not an inference.

## 10. Provenance and what is still provisional

- The roles in §2 and the effort-follows-irreversibility rule re-record a
  source factory's build-model policy: owner decisions dated 2026-07-28,
  2026-08-01, 2026-08-22 and 2026-09-05, written into that factory's map
  with a review date of 2026-09-07. The model names in it are deliberately
  not reproduced here: they were that owner's, for those accounts, for
  those dates.
- The §6 example is that factory's 2026-09-05 capacity exception: granted
  12:05, revoked 14:25 when the owner reset the quota; three lanes ran
  under it; the free overflow provider had been retired by its host the
  same morning. Its roster row for a "planned" worker chain still named
  the retired provider as fallback afterwards — the stale-fallback case of
  §6 rule 4 is observed, not hypothetical.
- The "never from a cached catalog" rule (§5) records one observed
  wrong-answer round trip in that factory.
- **Provisional:** no controlled comparison exists that the inherited role
  distribution is optimal (§7); the review of names ordered for 2026-09-07
  had not been performed when this file was written; the bulk-read worker
  probe proved an answer, not a served role. This file ships the method
  for keeping those questions apart, not a verdict on any model.

## 11. Measured cost

The cost of factory work decomposes as:

`users × sessions/user × runs/session × requests/run × tokens/request × price/token`

The operator's three middle levers are sessions per user, runs per session,
and requests per run. They are changed by tighter task boundaries, fewer
restarts, and shorter worker chains; they must be read from cost receipts,
not inferred from log size. Tokens per request and price per token still
matter, but are consequences of context and model policy rather than proof
that a workflow is efficient.

The default model assigned to subagents is usually the single biggest cost
choice because it multiplies across every delegated request. A decision under
§7 therefore cites a cost report with the eight fields from
`harness/report-schema.md`, a period, and the approved-task denominator. "It felt
faster" or a model name is not evidence. Unknown consumption is written as
`unknown`; it is never reported as zero.

Provenance and what is still provisional: this decomposition and the focus on
operator-controlled middle factors come from the 2026 Uber software-factory
efficiency account named in issue 23. The relative size of the subagent model
lever is a hypothesis until this factory has comparable per-approved-task
cost reports across model policies.
