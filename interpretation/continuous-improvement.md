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
