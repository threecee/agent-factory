# Evaluation practice — understand how it really works

- **Persona/pixel waves:** scripted user journeys against a served instance,
  screenshot per beat, every beat gated on the page actually FINISHING loading
  (a loading-marker wait with an honest "never finished within Ns" marking —
  screenshots taken before load are evaluation lies). Judgments must cite the
  RUN'S OWN screenshots, never a previous run's.
- **State parity:** full evaluations run against a freshly built instance
  from a pristine bank copy; cross-run comparisons require a parity receipt
  (manifest hash). Wins measured on leftover state are not wins.
- **Honest metrics:** a fake provider's numbers are plumbing-only, never
  model quality. A structurally-red metric (e.g. a corpus limitation) is
  reported as apparatus, not product. Evals never share the machine with
  build lanes — re-run at idle before adjudicating.
- **Findings loop:** every eval finding becomes a board item (or an explicit
  won't-fix with reasons). The eval report is an artifact the owner can read
  end to end, with per-finding evidence.
- **Stop-and-fix loops:** when validating fixes, run ONE failing persona;
  only if clean, run the next. Critical finding → fix lane → re-run.
