# Evaluation practice — understand how it really works

The admission gate (may this evaluation start, what may it claim) lives in
`verification/evaluation-readiness.md`. This file owns how a result is READ.

## Three results, three readings
- **A pre-flight smoke** says the served instance is the product we meant to
  measure and is alive. It says nothing about quality. A rejected smoke is a
  finding about the apparatus; fix it before any wave, never "run the wave
  anyway and annotate".
- **A functional trial** (scripted journey, fakes allowed) says the journey's
  plumbing works on this build. Its numbers are plumbing-only, never model
  quality. A partial trial proves exactly the actions its receipt lists as
  performed; the omitted actions are unproven, not failed.
- **An AI evaluation** says how good the product is in its INTENDED mode —
  and only if the receipt shows every product AI role configured real and
  observed alive for the whole run. A judge that scores while the product's
  own AI role is dead answers the wrong question; the score is discarded,
  not footnoted. "Never without AI" binds this type only.

## Measure the intended product mode
- Read the receipt's role table before any number: driver, judge and
  product roles are three different things. A live judge is not a live
  product; a live driver is not a live product.
- Distinguish a deliberate stand-in (fake configured, fake observed) from a
  broken promise (real configured, unavailable observed). Both leave outputs
  marked unavailable. The first is a different evaluation type; the second
  invalidates the run. Report both states, never collapse them into "AI
  off". The verdict is read off persisted configuration, never inferred
  from an output's model id, and it is taken on what the consumer's read
  path shows now, not on superseded history — `harness/artifact-bank.md`
  §4–§5; the gate example in `verification/examples/identity-and-history.md`
  §1 governs the live/history split.
- Background work must be finished before the measured phase (the project's
  readiness contract — all warmers terminal, the user-facing ready signal
  emitted). An evaluation against a half-warm instance measures the
  apparatus, not the product; its "what is not found" findings are
  attributable to the missing work.
- Full evaluations never share the machine with build lanes, a verify run or
  an instance standup — re-run at idle before adjudicating. Timing findings
  from a loaded machine are not findings.

## Small beds and what they cannot show
- A small start state proves flows, not scale: nothing about throughput,
  cold-path latency or convergence of long background chains. Those need
  the large bed, measured separately and never inferred from the small one.
- A small bed can only prove the situations it contains. When a journey step
  has no data to act on, the trial is rejected (readiness §3) — a green
  suite whose journey leg skipped for data is not a green journey, and a
  green fake-role prefix is not a passed AI journey.
- **The seed is extended, never swapped.** A small seed is the default bed
  for functional and persona runs because it starts fast and can be renewed
  from scratch; when a journey needs a situation the seed lacks, the seed is
  extended and the start state rebuilt — never replaced by the large set. A
  chain of pristines derived from each other inherits stale leases and
  model-off placeholders — comparisons across such a chain are comparisons
  of debris (`harness/artifact-bank.md` §7).
- The offline fake trial keeps its own value: it is the cheapest true proof
  that the product's plumbing survived the train. Keep it in verify; keep
  the AI-on trial out of verify.

## Persona/pixel waves
- Scripted user journeys against a served instance, screenshot per beat,
  every beat gated on the page actually FINISHING loading (a loading-marker
  wait with an honest "never finished within Ns" marking — screenshots taken
  before load are evaluation lies). Judgments must cite the RUN'S OWN
  screenshots, never a previous run's.
- "Done" without visible end-evidence (a saved-state receipt, a provenance
  link the persona can reach) is a finding against the product, not a
  success — record what the judges could not see.

## State parity and comparability
- Full evaluations run against a freshly built instance from a pristine bank
  copy; cross-run comparisons require a parity receipt — the rows the
  readiness receipt already carries (`verification/evaluation-readiness.md`
  §4): build SHA, start-state identity, per-role `configured` / `observed` /
  `identity`, background-work state. One differing row ⇒ the runs are not
  comparable; report that, not a delta. Wins measured on leftover state are
  not wins.
- **Parity is not isolation.** Two copies with identical manifest hashes
  that record the same external file reference (a corpus directory, a model
  cache) are ONE evaluation state: the first run's ordinary writes become
  the second run's starting point, and neither result can be rebuilt. Before
  a copy is exercised, every recorded path must resolve inside the copy, no
  job lease may be expired, and every configured role must have delivered —
  `harness/artifact-bank.md` §3 (worked example with two copies) and §6.
  The source is never served or written to; after the run its hash must be
  unchanged, or the run is invalid and the source is renewed (§7).
- Identity means the identity the product's reader uses (a digest), never a
  file mtime (`verification/examples/identity-and-history.md` §2). The bank
  and isolation rules are owned by `harness/artifact-bank.md` §3, §6–§7.

## Honest metrics
- A structurally-red metric (e.g. a corpus limitation) is reported as
  apparatus, not product.
- The receipt's `proves:` line is the evaluation's whole claim. A report
  that says more than that line is over-claiming.

## Findings loop
- Every eval finding becomes a board item (or an explicit won't-fix with
  reasons). The eval report is an artifact the owner can read end to end,
  with per-finding evidence, banked as it is produced.
- Findings that stand independent of the AI state (a missing receipt, an
  action with no feedback) are filed even when the run itself is invalid as
  an AI measurement — say which findings depend on the AI state and which
  do not.

## Stop-and-fix loops
- When validating fixes, run ONE failing persona; only if clean, run the
  next. Critical finding → fix lane → re-run. Each re-run gets a fresh
  pre-flight smoke; an admission receipt from an earlier run admits nothing.
