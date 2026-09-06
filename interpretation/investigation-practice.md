# Investigation practice

- **Instrument first.** Reproduce with attribution before hypothesizing.
  Enumerate the reachable set instead of concluding from one observed bucket.
- **Measure before dispatch, hand over the whole observed run.** A lane that
  cannot run the acceptance apparatus (a browser-blind sandbox fixing a
  recorder) sees only what it is given. Given one failure it fixes one
  locator per round; given the whole run — log, DOM snapshot, screenshot,
  timings — it addresses every visible failure in one pass and names who
  reruns the apparatus. That is why the execution contract
  (../planning/execution-contract.md §2) makes attachments and the proof
  owner part of the brief, not of the handback. The source factory adopted
  it after a seven-round recorder fix; it has not measured the effect.
- **Root-cause before fix.** A bug lane documents the root cause before any
  fix is proposed. Three failed DIFFERENT hypotheses mean the model of the
  defect is wrong — stop and escalate an architecture question, never
  attempt a fourth. This rule is about the model of the defect; it is not
  the round counter. The two-round limit
  (../planning/execution-contract.md §3) counts complete rounds on the same
  approach; a task can hit either first, and they resolve differently: a
  wrong model is a STOP (design question), an exhausted count is a PARK
  (resumable, split).
- **Second opinions are cheap.** Read-only investigation agents (different
  model family than the implementer) fed with precise questions and file
  scopes return root causes in minutes; falsify THEIR claims with a direct
  check before acting (an investigator once reported a workflow "active on
  every push" — the file's trigger block said otherwise).
- **Probes carry the caller's arguments** — copy the call site verbatim.
  A probe with its own defaults tests a different program.
- **Never signal-probe a live process** without a handler — attach by
  file-mtime and sampling profilers instead.
