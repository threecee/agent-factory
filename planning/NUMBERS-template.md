# Number registry

One row per allocated number. Claim first (push to main immediately), flip
`claimed → landed` at landing, re-claim released numbers by rewriting the row
in place. Numbers are allocated only by the orchestrator.

| kind | number | branch/lane | date | state | description |
| --- | --- | --- | --- | --- | --- |
