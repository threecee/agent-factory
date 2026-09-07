# Evaluation practice — understand how it really works

- **Persona/pixel waves:** scripted user journeys against a served instance,
  screenshot per beat, every beat gated on the page actually FINISHING loading
  (a loading-marker wait with an honest "never finished within Ns" marking —
  screenshots taken before load are evaluation lies). Judgments must cite the
  RUN'S OWN screenshots, never a previous run's.
- **State parity:** full evaluations run against a freshly built instance
  from a pristine bank copy; cross-run comparisons require a parity receipt
  (manifest hash). Wins measured on leftover state are not wins.
- **Parity is not isolation.** Two copies with identical manifest hashes
  that record the same external file reference (a corpus directory, a model
  cache) are ONE evaluation state: the first run's ordinary writes become
  the second run's starting point, and neither result can be rebuilt. Before
  a copy is exercised, every recorded path must resolve inside the copy, no
  job lease may be expired, and every configured role must have delivered —
  `harness/artifact-bank.md` §3 (worked example with two copies) and §6.
  The source is never served or written to; after the run its hash must be
  unchanged, or the run is invalid and the source is renewed (§7).
- **Honest metrics:** a fake provider's numbers are plumbing-only, never
  model quality. A structurally-red metric (e.g. a corpus limitation) is
  reported as apparatus, not product. Evals never share the machine with
  build lanes — re-run at idle before adjudicating.
- **Intended fake ≠ promised-but-failed.** Both leave outputs marked
  unavailable. A run receipt names, per configured role, whether the role
  was a deliberate stand-in (accepted, disclosed with counts), delivered, or
  configured and failed (refused — the run measured the apparatus, not the
  product). The verdict is read off persisted configuration, never inferred
  from an output's model id, and it is taken on what the consumer's read
  path shows now, not on superseded history — `harness/artifact-bank.md`
  §4–§5; the gate example in `verification/examples/identity-and-history.md`
  (introduced by PR10) governs the live/history split.
- **Small bed, complete situations.** A small seed is the default bed for
  functional and persona runs because it starts fast and can be renewed
  from scratch; it must contain every situation the run needs (the seed is
  extended, never swapped for the large set). The large set is for scale
  and performance measurements only. A chain of pristines derived from each
  other inherits stale leases and model-off placeholders — comparisons
  across such a chain are comparisons of debris (`harness/artifact-bank.md`
  §7).
- **Findings loop:** every eval finding becomes a board item (or an explicit
  won't-fix with reasons). The eval report is an artifact the owner can read
  end to end, with per-finding evidence.
- **Stop-and-fix loops:** when validating fixes, run ONE failing persona;
  only if clean, run the next. Critical finding → fix lane → re-run.
