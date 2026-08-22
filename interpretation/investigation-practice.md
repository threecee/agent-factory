# Investigation practice

- **Instrument first.** Reproduce with attribution before hypothesizing.
  Enumerate the reachable set instead of concluding from one observed bucket.
- **Root-cause before fix.** A bug lane documents the root cause before any
  fix is proposed; three failed DIFFERENT hypotheses mean the model of the
  defect is wrong — stop and escalate, never attempt a fourth.
- **Second opinions are cheap.** Read-only investigation agents (different
  model family than the implementer) fed with precise questions and file
  scopes return root causes in minutes; falsify THEIR claims with a direct
  check before acting (an investigator once reported a workflow "active on
  every push" — the file's trigger block said otherwise).
- **Probes carry the caller's arguments** — copy the call site verbatim.
  A probe with its own defaults tests a different program.
- **Never signal-probe a live process** without a handler — attach by
  file-mtime and sampling profilers instead.
