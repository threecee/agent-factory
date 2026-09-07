# Evaluation readiness — the admission gate before anything expensive runs

This file owns the rules that decide whether an evaluation may START and what
its result is allowed to CLAIM. `interpretation/evaluation-practice.md` owns
how to read the result; `verification/verify-portfolio.md` owns which of the
legs below run inside `make verify`; `verification/falsification.md` owns the
proof that the gate itself has teeth.

Why this exists: in the source factory, one night lost twelve hours to faults
that were observable in minutes without any AI driver — a served instance
whose startup banner said "AI on" while its HTTP client was already closed
(hundreds of log errors from boot), a stale background job that held the
readiness signal, a warmer that reported progress it was not making. A
multi-hour persona wave then measured the wrong product. Cheap, named checks
before the expensive run would have stopped every one of them.

## 1. Three evaluation types — never conflated

| Type | Question it answers | Drivers | Product AI roles | Proves |
|---|---|---|---|---|
| **Pre-flight smoke** | Is the served instance the product we intend to measure, and is it alive? | none (scripted probes) | as the later evaluation will run them | admission of the instance, nothing about the product's quality |
| **Functional trial** | Does the user journey work end to end on this build? | scripted journey (recorder, route walk) | fakes allowed and preferred | the journey's plumbing; nothing about model quality |
| **AI evaluation** | How good is the product with its AI roles live? | scripted or agentic personas, judges | real, configured, observed alive | product quality in the intended mode |

Rules:

1. Every evaluation run declares its type in its receipt (§4). The type fixes
   the REQUIRED check set (§2.2) and the strongest claim the result may make.
2. A result never migrates upward. A functional trial with fakes is a
   functional trial however green it is; it is never reported as a passed AI
   evaluation, not even "in effect".
3. A functional trial with offline fakes is explicitly a valid functional
   proof. It is the preferred verify-time leg (§3) because it needs no
   provider, no quota and no network, and it fails only on the product's own
   plumbing.
4. "Never evaluate without AI" binds AI evaluations only — evaluations of an
   AI feature must have the product's AI roles actually alive. It does not
   bind deterministic tests, functional trials, or products without AI roles.

## 2. The pre-flight smoke (admission criterion)

### 2.1 Shape
A fixed list of named checks with stable ids, run in a fixed order against
the served instance, inside a project-chosen time budget, writing one receipt
(§4) in machine and human form. "Deterministic" means the SCHEDULE and the
CRITERIA are fixed; a check that makes a real model call is still an external
call and may fail for external reasons — that is a finding, not flakiness to
retry silently.

The check families every served product has an equivalent of (the project
names its own ids and thresholds):

| Family | What one check does | Typical failure it catches |
|---|---|---|
| **Role liveness** | One real, minimal call through the product's OWN client for each configured AI role (a single reasoning turn that must return valid structured output; an embedding whose identity must equal the pinned identity) | the closed-client class: a banner or config says "on", the product's client is dead |
| **Log cleanliness** | Count the role's known fatal log lines since THIS server process started (pin the pid and its start time; an older log is not evidence) | "client has been closed" repeated from boot |
| **Background work** | The project's readiness contract for derived data (all warmers terminal, no non-terminal job rows older than server start, the user-facing "ready" signal actually emitted) | stale job leases inherited from a copied instance; a warmer with no progress |
| **Progress under load** | Trigger the heaviest background job and require its progress counter to RISE within a bound while an interactive route's p95 stays under the project's ceiling | a warmer that spins without publishing; interactive starvation |
| **Route walk** | Visit every route of the evaluated surface as the evaluated role: page label visible, content signature visible, no page-level loading marker after N seconds, no unexpected console errors, no 5xx; screenshot per route | a route that never finishes loading; a dead build |
| **Critical action** | One scripted decision through the UI with its feedback bound (a toast within N seconds; a queue rebuild within M seconds; the dependent view still loads during the rebuild) | the action "works" but the receipt never renders |
| **Selector contract** | Every locator the later scripted driver will use resolves in the REAL served DOM, or is explicitly marked post-interaction | a recorder that fails at beat 6 after five minutes of setup |

### 2.2 Verdict rules
5. The evaluation about to run declares which check ids it DEPENDS on: the
   required set. A pre-flight verdict is `admitted` only when every required
   check is `ok`. `fail` rejects. **`skip` on a required check rejects** —
   an omitted probe is not a passed probe. The process exit code is derived
   from the verdict, never from "no check failed".
6. Skips are legal only for checks outside the required set, and every skip
   row carries its cause. A run with any skipped check is a PARTIAL run and
   its receipt says so in the verdict line.
7. A closed or dead product role fails admission even when the judge, the
   driver and every other check are green. A working judge scoring a dead
   product answers the wrong question. (Worked verdict §5.1.)
8. The receipt distinguishes three states per AI role: `configured` (what
   the run promised), `observed` (what the liveness check saw), and whether
   the pair is a deliberate stand-in (`fake` configured and observed) or a
   broken promise (real configured, `unavailable` observed). A deliberate
   fake is admitted for functional trials and rejected for AI evaluations; a
   broken promise is rejected for both.
9. Admission is bound to one run: the receipt carries the run id and the
   served process identity, and a wrapper refuses to start the expensive
   phase on a receipt from an earlier run or an earlier server process.
   (`harness/run-lifecycle.md` §2 owns run identity and §5 binds a verdict
   to it; the served process is identified as §6 identifies any process —
   executable name plus exact argv token, never a log line.)
10. The receipt is banked as it is produced, next to the evaluation's own
    output (`harness/artifact-bank.md` §2; the run's own receipts go to the
    bank per `harness/run-lifecycle.md` §9); a smoke that lives only in a
    scratchpad cannot admit a later reader.

### 2.3 Coverage, not exit code
The source factory's first live smoke ran "13 of 14 checks green" and the
fourteenth check imported a helper that had never existed on main: its unit
tests had exercised the classifier with fabricated probes, never the real
inventory. Later, a pixel pass "14/14" was produced with several AI and
load checks switched off against fake providers. Neither number is evidence
of a full AI smoke. Read the check LIST of a receipt, not its total; a
wrapper that admits on exit code alone is vacuous (falsify it per
`falsification.md` rule 13).

## 3. The functional trial on a small bed

11. Keep a small, complete, banked start state (a synthetic case that starts
    in seconds) for functional trials, and a separate large start state for
    scale and performance. The small bed is the default; the large bed is
    reserved for what only scale can show. Each trial run STARTS its own
    instance from a fresh copy of that state: an instance that was already
    serving cannot show a startup-only fault (the closed-client class of
    §2.1 lives in the startup path, as does a stale lease inherited from a
    copy), so re-using a running instance for "one more trial" is not the
    trial. The copy is isolated per `harness/artifact-bank.md` §3 before
    the instance starts.
12. **"Small" must still contain every situation the journey needs.** For
    each critical action of the scripted journey the project writes down its
    data preconditions (e.g. "the merge step needs at least two accounts with
    the same display name from different sources") and the trial checks them
    BEFORE the driver starts. The source factory's first live run of its
    recorder stopped at the fourth beat — every page loaded, but the seed had
    three accounts with distinct names and the "merge duplicates" beat had
    nothing to merge. A green suite whose journey leg skipped for data is
    not a green journey.
13. A missing required data situation is a rejection of the trial, not a
    pass with a note (worked verdict §5.2). Locally, when the banked bed is
    absent on a machine, the verify leg may SKIP with a loud reason; the
    landing duty then requires an actual PASSED line for that leg whenever
    the bed exists, and a mandatory acceptance (a train that touches the
    journey, an install smoke) needs a real pass, never the skip.
14. Fakes are preferred on the small bed. The trial's driver reads the
    instance's manifest and REFUSES the steps that need a real AI role when
    that role is a fake or absent — before the browser starts, so the
    refusal costs seconds, not a timeout per step.
15. A partial journey writes a partial receipt: the exact ids of the actions
    performed, the exact ids omitted, and the cause of omission (§4 example).
    "Beats 1–5 recorded, 6–8 skipped: require the reasoning role,
    configured=fake" is a complete, honest functional proof of beats 1–5. It
    is never rendered as "journey passed".
16. The full AI journey (all beats, real roles) is a separate run against a
    separately built AI-on copy of the same small seed, in a provider window,
    never inside `make verify`. The two beds are never one symlink that gets
    flipped: a verify leg must not be able to consume model capacity or
    silently change what it exercises.
17. Start-state identity is what the product's own reader uses (a content
    digest, a manifest hash), never a file mtime: copying a bed reorders
    mtimes, and a gate that picks "the newest snapshot" then admits a stale
    index over the finished one. The gate and the reader must compute the
    same identity. The worked example — a decoy snapshot with a newer mtime
    and the wrong key, which a mtime-picking gate selects and a key-resolving
    gate rejects — is `verification/examples/identity-and-history.md` §2
    (falsification rule 11).

## 4. The receipt

One schema serves all three types; the `evaluation` field and the
`required:` flags change. Machine form (JSON/YAML) and human form (a table)
are rendered from the same rows.

```yaml
evaluation: functional-trial          # pre-flight-smoke | functional-trial | ai-evaluation
run_id: 20260906T0412Z-3f9c1e2        # one run, one receipt (PR2 run lifecycle)
build_sha: 3f9c1e2
instance:
  start_state: small-synthetic-r12-pristine      # a banked, named start state
  start_state_identity: sha256:9b1d…                  # the reader's identity, not mtime
  served: http://127.0.0.1:<port>  pid=4711  started=2026-09-06T04:10:02Z
roles:                                # per role: configured / observed / stand_in / identity (no key material)
  driver:  { configured: scripted-recorder, observed: alive, identity: recorder@3f9c1e2 }
  judge:   { configured: none }
  product:
    reasoning: { configured: fake, observed: fake, stand_in: deliberate, identity: fake-v1 }
    embedding: { configured: fake, observed: fake, stand_in: deliberate, identity: fake-v1 }
background_work:
  required: all-terminal-and-notified
  observed: all-terminal-and-notified
  evidence: "readiness endpoint: 3/3 cases terminal, ready signal emitted; 0 non-terminal jobs older than pid start"
checks:
  - { id: log-clean,            required: true,  status: ok,   seconds: 0.4,  evidence: "0 closed-client lines since pid 4711 start" }
  - { id: reasoning-call,       required: false, status: skip, seconds: 0.0,  evidence: "reasoning=fake (deliberate); not required for functional-trial" }
  - { id: embedding-identity,   required: true,  status: ok,   seconds: 0.2,  evidence: "stamped identity == pinned identity (fake-v1)" }
  - { id: jobs-no-stale,        required: true,  status: ok,   seconds: 0.1,  evidence: "0 non-terminal rows older than server start" }
  - { id: routes-ready,         required: true,  status: ok,   seconds: 41.0, evidence: "14/14 routes label+signature visible, no loading marker at 60 s" }
  - { id: decision-feedback,    required: true,  status: ok,   seconds: 6.3,  evidence: "toast within 30 s; queue rebuilt in 48 s; dependent view loaded during rebuild" }
  - { id: selector-contract,    required: true,  status: ok,   seconds: 3.9,  evidence: "31/31 locators resolve in served DOM (2 marked post-interaction)" }
  - { id: precondition-merge-candidates, required: true, status: ok, seconds: 0.1, evidence: "2 accounts share display name across sources" }
actions:
  performed: [b1-open-case, b2-search, b3-open-review, b4-merge-duplicates, b5-attach-note]
  omitted:   [b6-ask-assistant, b7-accept-suggestion, b8-export]
  omitted_cause: "b6–b8 require the reasoning role; configured=fake (deliberate); refused before browser start"
verdict: admitted (partial: 1 skip outside required set; 3 actions omitted)
proves: "beats b1–b5 work end to end offline on 3f9c1e2 against the named start state. Nothing about model quality. b6–b8 unproven."
```

Human form, same rows:

| check | required | status | seconds | evidence |
|---|---|---|---:|---|
| log-clean | yes | ok | 0.4 | 0 closed-client lines since pid 4711 start |
| reasoning-call | no | skip | 0.0 | reasoning=fake (deliberate); not required for functional-trial |
| … | | | | |

The `proves:` line is mandatory and is the only sentence a downstream report
may quote as the evaluation's claim.

Every role row carries an `identity` — the provider/model pin or the pinned
embedding identity the product's own configuration names, for a fake the
fake's version — and never a key, token or endpoint secret. `build_sha`,
`start_state_identity`, the role rows and `background_work` are the parity
rows: two runs are comparable only when all of them agree
(`interpretation/evaluation-practice.md`, "State parity and comparability").

## 5. Worked verdicts

Each example is a diff against the §4 receipt. The reader should be able to
produce the same verdict from the rules in §2.2 alone.

### 5.1 Closed product client, judge working → rejected
```yaml
evaluation: ai-evaluation
roles:
  judge:   { configured: model-judge, observed: alive }         # judge is fine
  product:
    reasoning: { configured: real, observed: unavailable, stand_in: none, identity: <provider/model> }   # broken promise
checks:
  - { id: log-clean,      required: true, status: fail, evidence: "412 'client has been closed' lines since pid start" }
  - { id: reasoning-call, required: true, status: fail, evidence: "RuntimeError: cannot send a request, client has been closed" }
verdict: rejected
proves: "nothing — the product's reasoning role is configured real and observed dead; a judge score here would grade a product with AI off. Fix the lifecycle, restart, re-run pre-flight."
```
Rule 7 applies. Do not "run the wave anyway and mark it apparatus": the
source factory did exactly that once, and the resulting numbers had to be
retro-annotated as AI-off in every bank README and re-run.

### 5.2 Missing required data situation → rejected
```yaml
evaluation: functional-trial
checks:
  - { id: precondition-merge-candidates, required: true, status: fail, evidence: "0 pairs of accounts share a display name; b4-merge-duplicates needs >= 2" }
actions:
  performed: [b1-open-case, b2-search, b3-open-review]
  omitted:   [b4-merge-duplicates, b5-attach-note, b6-ask-assistant, b7-accept-suggestion, b8-export]
  omitted_cause: "b4 precondition unmet; b5–b8 not attempted (sequential journey)"
verdict: rejected
proves: "the bed cannot exercise the journey; extend the seed, rebuild the start state, re-run. Pages loading is not the journey working."
```
Rule 12–13 apply. The only legal weaker outcome is a LOCAL `skip` of the
verify leg when the bed is absent on this machine — and that skip cannot
satisfy a mandatory acceptance.

### 5.3 Skipped required probe → rejected
```yaml
evaluation: ai-evaluation
checks:
  - { id: reasoning-call,      required: true, status: skip, evidence: "skipped by --skip" }
  - { id: progress-under-load, required: true, status: skip, evidence: "skipped by --skip" }
  # every other row ok
verdict: rejected
proves: "nothing about AI readiness — two checks the AI evaluation depends on were not run. 12/14 ok is not admission."
```
Rule 5 applies. A wrapper that reads "no failures ⇒ go" is the vacuity this
rule exists for; the falsification in `falsification.md` rule 13 plants
exactly this receipt.

### 5.4 Offline fake prefix → admitted, as what it is
The §4 receipt itself. It is a complete functional proof of beats 1–5 and
belongs in `make verify`. It may not be quoted as "the journey passed" or as
any AI result; the full eight-beat run happens under §3 rule 16 with real
roles and its own receipt.

### 5.5 Import-only installation check → not admission
```yaml
evaluation: pre-flight-smoke        # installation readiness
checks:
  - { id: gate-import,        required: false, status: ok,   evidence: "python -c 'import check_x' exit 0" }
  - { id: gate-documented-cli, required: true, status: fail, evidence: "python scripts/check_x.py --check: ModuleNotFoundError (sys.path lacks repo root when run as a script)" }
verdict: rejected
```
See §6. Green import, red invocation — the documented command is the one the
runbook, the CI job and the lander actually run.

## 6. Installation readiness: run the documented entry point

18. An installed factory proves itself by running each gate and script THE
    WAY ITS RUNBOOK DOCUMENTS IT — `python scripts/<gate>.py --check`,
    `make verify`, the container `CMD` — from a shell with the runbook's
    environment, and by reading the gate's own verdict line. An import test
    (`python -c "import gate"`, a pytest that imports the module) proves the
    module parses; it does not prove the invocation, its `sys.path`, its
    working-directory assumptions or its exit code. An installation whose
    only evidence is imports is copied, not installed.
19. For a product with a served surface, installation readiness includes one
    offline functional trial (§3) against a small start state; the receipt
    (§4) is banked as the installation's first evaluation artifact.
20. Which tree the invocation actually imported is a separate proof (a
    worktree can share an environment with the primary checkout and silently
    import the wrong revision); that provenance rule is owned by
    `harness/worktree-ritual.md` ("Prove which code the test imported",
    with the per-stack probes) and `verify-portfolio.md` ("Prove the import
    root before the expensive run").

## 7. Provenance and what is still provisional

The rules above are distilled from the source factory's pre-eval smoke, its
small-bed recorder leg and its AI-on evaluation protocol. What that factory
had actually shown at the time of writing:

- The offline fake prefix of its eight-beat journey (beats 1–5) ran green in
  a real browser inside its verify portfolio, ~150 s, with a partial receipt
  of exactly the §4 shape (`beats_recorded`, `beats_skipped`,
  `beats_skipped_reason`). This is the anonymized §4/§5.4 example.
- Its first live pre-flight smoke found a fabricated-probe gap (§2.3) and was
  fixed; the smoke has since gated its AI-on evaluations. The AI-on smoke
  that established that gate was itself a PARTIAL run by §2.2 rule 6 — nine
  of ten checks green, the embedding-identity check red as an apparatus
  fault — so it is evidence that the gate runs, not a full AI-on admission.
- **Still awaited:** the first sharp AI-on smoke plus full persona wave on a
  freshly built large start state under current code (the source factory's
  "T1"); its result was pending in a parallel run when this doctrine was
  written and is NOT claimed here. Likewise pending there: the replay matrix
  for warmer throughput (its #641), the precision fix for the pristine gate's
  history-vs-live unavailable counting (its #669 — the gate SHAPE is
  `verification/examples/identity-and-history.md` §1; the source factory's
  measurement with it is not in this package), and the post-fix convergence
  measurement of the large case (its #590/#670). None of these is a proven
  result in this package; they are the reason §1 rule 2 and §2.2 rule 8 are
  phrased as they are.
