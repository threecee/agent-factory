# Model policy — operator file (EXAMPLE; copy to `~/.claude/model-policy.md`)

This is the operator's dated binding of the factory's roles
(`../harness/model-policy.md` §2) to models on THIS machine and THESE
accounts. It is a grant with a review date, like the landing policy: the
package ships no names, and a copy of this file with the placeholders still
in it binds nothing. Every field below is required unless marked optional;
the reading rules are in `../harness/model-policy.md` §3, §5 and §6.

```yaml
valid_from: <YYYY-MM-DD>          # the day you signed it; never a future date
review_by: <YYYY-MM-DD>           # names are revisited on this date; past it the policy is stale (§3 rule 3)
signed: <owner name>
roles:
  - role: orchestration
    model: <model id, exact string from the provider>
    provider: <account/subscription the bill goes to>
    invocation: "<the harness or CLI form, with {worktree} {brief} {effort} placeholders>"
    effort: <the CLI's effort token for irreversible work>
    state: active                   # active | retired
    last_probed: <YYYY-MM-DD>       # the one-token probe (§5 rule 2)
    probe_result: <ok | rate_limited | auth_failed | unreachable>
  - role: implementation lane
    model: <…>
    provider: <…>
    invocation: "<cli> exec --cd {worktree} -m <model> -c effort={effort} {brief}"
    effort: <high-equivalent>
    effort_mechanical: <lower setting for bounded mechanical bulk>   # optional
    state: active
    last_probed: <…>
    probe_result: <…>
  - role: cheap judging and reduction
    model: <…>
    provider: <…>
    invocation: "<…>"
    effort: <medium-equivalent>
    state: active
    last_probed: <…>
    probe_result: <…>
  - role: investigation and second-family review
    model: <…>                      # a different model FAMILY from the lane row where a panel needs diversity
    provider: <…>
    invocation: "<…>"
    effort: <provider default or explicit>
    state: active
    last_probed: <…>
    probe_result: <…>
  - role: demanding analysis and verification
    model: <…>
    provider: <…>
    invocation: "<…>"
    effort: <high-equivalent>
    state: active
    admission: owner                # each piece of work is admitted by the owner (§2 table)
    last_probed: <…>
    probe_result: <…>
  - role: product and evaluation identities     # written down for the boundary (§8), never dispatched into
    model: <…>
    provider: <the product's/eval's own key, never a factory key>
    state: active
    owned_by: <the product/eval decision record>
authorizations: []                 # temporary or local grants; each MUST carry `until` (§6 rule 1)
#  - granted: <YYYY-MM-DDTHH:MM>
#    by: <owner>
#    scope: "<which standing rule it lifts, for which roles>"
#    until: <date-time or event>
#    revoked_at: <set when lifted early>
#    reason: <why granted / why lifted>
#    lanes_ran_under: [<lane>, …]
history: []                        # retired rows and lifted grants with the reason; provenance only
#  - role: <…>
#    model: <…>
#    retired: <YYYY-MM-DD>
#    reason: "<provider 404 | quota wall | paid successor not admitted | superseded by …>"
```

## Filling it in

1. Get the exact model id from the provider's live list, not from memory or
   a bundled catalog (`../harness/model-policy.md` §5 rule 1).
2. Run the one-token probe per row and record the date and result. A row
   without a probe date is not dispatchable.
3. Set `review_by` to a date you will actually revisit; two weeks is a
   reasonable horizon, two days when a row changed state today.
4. Point the repo's operations doc at this file by path; do not copy the
   table into the repo (one live policy, §3 rule 1).
5. When a lane must deviate (a quota wall, a retired provider), write the
   authorization row FIRST, then dispatch; cite the row in the lane brief
   header (§4).
