# The continuous-improvement loop

evaluation/incident → finding with evidence → board item → owner triage
(periodically re-verified against CURRENT code, at depth: primary sources,
today's locks/alerts, not yesterday's assumptions) → spec → lane → choices
ledger → train → landed → re-proven by the NEXT evaluation.

Two disciplines make the loop honest:
1. **Deep re-verification before executing owner verdicts.** Board bodies rot;
   a verdict taken on a stale card must come back to the owner, not be
   silently executed (a card was once approved whose problem no longer
   existed — the audit caught it, the owner annulled).
2. **Process findings feed the factory itself.** Orchestrator mistakes the
   machinery catches (date errors, stale instructions, mid-verify mutations)
   get memories and, when procedural, reviewed diffs to the operations doc.

A change to the factory's own machinery enters the same loop as a product
change: a pilot with a measurement, a finding with the numbers, a board item
for adoption. `harness/bulk-read-contract.md` is the worked case — routing
large reads through a cheaper worker is adopted only after an off/on train
pair records total cost (orchestrator and worker), latency and fact
preservation (§7 there); until then it stays a voluntary tool. A machinery
change that skips the measurement is a choice for the ledger, not a
saving.

## 1. Path-scoped open improvement items

This marked table is the one registry of improvement items that are still
open and need to reach a lane before it starts. Each item occupies one row:
`Status` is exactly `open` or `closed`, `Path glob` is one repository-relative
shell glob with no `|` character, and `Improvement item` is the text or
resolving pointer the lane must read. Closing an item changes its status in
place; it does not delete the evidence trail.

<!-- open-improvements:start -->
| Status | Path glob | Improvement item |
|---|---|---|
<!-- open-improvements:end -->

At brief preparation, run
`bash harness/lookup_open_improvements.sh interpretation/continuous-improvement.md
<planned-path>...` separately for the planned paths covered by each selected
diff-triggered leg. Add every returned line to that leg's `reads first` cell,
and leave the cell's existing pointers unchanged when the lookup prints
nothing. An open item appears only where its glob matches, a closed item never
appears, and duplicate matches emit the item once. The shell test and its
`harness/**` falsification are
`harness/tests/test_lookup_open_improvements.sh`.
