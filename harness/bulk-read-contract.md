# Bulk-read contract — bounded reading through a worker (pilot)

**Status: pilot, measurement-gated.** Nothing in this file activates by
itself. Installing the three skills below changes no behaviour until the
operator (a) wires the commands in §4, (b) passes the worker-down trial in
§5, and (c) decides — after the on/off pilot in §7 has numbers — whether the
optional adapter in §8 is registered. This contract is the one home for every
rule about routing large reads through a cheaper worker; the skills
(`skills/bulk-reader`, `skills/log-triage`, `skills/handback-digest`) point
here and carry only invocation and scope.

Depends on `planning/execution-contract.md` (§2 measurement baseline, §3
complete rounds — the counts §7 below reads) and the handback fields in
`harness/report-schema.md` (`choices:` and its `<lane>-choices.md` sidecar)
for what a handback contains, and on the stable choice ID in
`interpretation/choices-ledger-README.md` §2 for how a digest entry is tied to
the audited ledger entry.

## 1. The problem and the boundary

An orchestrator needs three failure lines from a 4 000-line verify log, or the
slice list from a 540-line spec. Reading the whole file spends the
orchestrator's context on text it will use once. A cheap worker can return
the three lines with exact identifiers; the orchestrator then reads those
lines in the source before it decides cause and action.

Two boundaries make this safe and keep it honest:

- **The worker reduces reading; it never takes over judgment.** Root cause,
  architecture, boundary-sensitive code, security review, and the final
  choice verdict stay with the responsible agent (§9).
- **If every worker is down, ordinary reading must still work.** An
  optimisation that can stop the factory is not an optimisation (§5).

## 2. The three read-only shunts

| Shunt | Input | Output | Owner of the judgment that follows |
|---|---|---|---|
| bulk-read | one or more files + one narrow question | structured bullets, each led by an exact name, type, or line number | the caller, reading the cited lines (§3 rule 4) |
| log-triage | one large run/verify log | failing tests, assertion text, tracebacks, red gates, each with a source line number | the caller, root-causing with `skills/systematic-debugging` |
| handback-digest | one lane handback (+ optional diff stat) | one DRAFT ledger entry per choice: headline, provisional verdict, confidence, walked scenario | `skills/audit-choices` — the digest is never the verdict (§3 rule 7) |

All three are read-only: they write nothing into the tree. A writing
counterpart (a "code-writer" that drafts implementation from an approved
spec) is a separate, voluntary contract with its own review path and is
**not part of this pilot** (§10).

## 3. Rules

1. **Activation follows a working worker path, never precedes it.** Before
   any automatic routing (§8) is registered, the operator runs one live probe
   against the configured worker on a real repository file and records the
   result (worker id, lines, input/output tokens, seconds, facts checked). A
   factory that registered its hooks first — with no reachable worker — locked
   its own orchestrator out of every bulk read; that is the failure mode this
   rule exists for. The probe proves the worker answers; it does not prove a
   net saving (§7).
2. **Narrow question in, exact identifiers out.** A shunt question must be
   answerable from the file's text: names, counts, line numbers, "does X
   exist", "list every Y". "Summarise this" and "what is wrong here" are not
   shunt questions. The answer leads every bullet with the exact identifier and
   claims no line precision it cannot support.
3. **Explicit input boundary.** By default a shunt accepts only files inside
   the repository and the lane's run directory (the launcher's
   `LANE_RUN_DIR`; `harness/run-lifecycle.md` §2–§3). Any other
   path is refused with the offending path named and a distinct exit code,
   before any worker is invoked. An explicit opt-in flag exists for reviewed
   material only; the reviewer confirms the material is approved for the
   worker's provider under the project's own data rules. A file path never
   implies approval — the project's confidentiality, egress and licensing
   rules are local and are not encoded in this contract.
4. **Source return before decision.** The caller reads the cited lines in the
   source (a bounded read, rule 5) before it states a cause, orders a fix, or
   writes a ledger entry. A shunt answer is a pointer, not evidence.
5. **Three escape hatches, all named in the block message.** (a) A bounded
   read — `offset`/`limit`, a narrow `sed -n` span, `grep`, `wc`,
   `git diff --stat` — always passes unconditionally; it is the built-in
   path, not a workaround. (b) A per-path exemption list (globs) for files the
   operator has decided to read whole. (c) A session-wide disable variable for
   when every worker is down. A hook whose block message does not print all
   three is not compliant.
6. **Fail closed on the worker side, open on the reader side.** When every
   configured worker fails, the shunt exits with a distinct code, names each
   worker's failure, and echoes **none** of the input — the corpus never
   reaches stdout/stderr through the error path. The reader then falls back
   to rule 5. An unknown worker alias fails the same way, before any call.
7. **The final verdict lies with the audit.** A handback digest is a draft in
   the ledger's own entry format. `skills/audit-choices` traces the handback
   and the diff itself, decides sound/unsound/needs-user, and writes the
   ledger entry; the digest may be quoted, never pasted in as the verdict. The
   orchestrator still hunts for choices the digest omitted.
8. **Measure before adopting.** Adoption is decided by the on/off pilot in
   §7: total cost across orchestrator **and** worker, wall-clock latency, and
   quality deviation on a fixed fact list. A smaller orchestrator context can
   cost more in total. Without those numbers the shunts stay voluntary tools;
   they do not become standard practice.
9. **The adapter is a harness option, never a default.** The PreToolUse hook
   in §8 is one harness's way to make the routing automatic. It is registered
   by a deliberate operator step after rules 1 and 8 are met, is listed in the
   operator's local policy, and is removable by deleting one registration.
   Harnesses without such a hook use the skills by explicit invocation only.
10. **Every parameter has a local owner.** The threshold, worker chain,
    provider, request format, timeout and log location in §4 are operator
    choices with a stated reason; none is a universal constant. Model names
    are never written into a skill.

## 4. Parameters

The contract names roles; the operator binds each to a value in the
repository's operations doc (`{{PARAM}}` in the skills refers to this table).

| Role | Placeholder in the skills | Suggested default name | Owner |
|---|---|---|---|
| Bulk-read command | `{{BULK_READ_CMD}}` | `python scripts/factory/bulk_read.py` (Python repos) or any CLI honouring §3 rules 2–6 | repo operations doc |
| Log-triage command | `{{LOG_TRIAGE_CMD}}` | `python scripts/factory/log_triage.py` | repo operations doc |
| Handback-digest command | `{{HANDBACK_DIGEST_CMD}}` | `python scripts/factory/handback_digest.py` | repo operations doc |
| Line threshold | `{{SHUNT_MIN_LINES}}` | env `SHUNT_MIN_LINES`; one factory started at 350 as an untried default — the value is tried against round-trip cost in §7, never inherited; unbound, the adapter in §8 is inert | operator (`user-level/`) |
| Worker chain | `{{SHUNT_WORKERS}}` | env `SHUNT_WORKERS`, comma-separated aliases; each alias maps to a provider/model in code; unknown alias fails closed | operator (`user-level/`) |
| Session disable | `{{SHUNT_DISABLE}}` | env `SHUNT_DISABLED=1` | operator; set only while workers are down |
| Path exemptions | `{{SHUNT_ALLOW}}` | env `SHUNT_ALLOW`, comma-separated globs (absolute or repo-relative) | operator |
| External opt-in | `{{ALLOW_EXTERNAL_FLAG}}` | `--allow-external` | the reviewer of that one input |
| Input roots | — | repository root + the launcher's `LANE_RUN_DIR` | `harness/run-lifecycle.md` §3 |
| Measurement log | `{{SHUNT_LOG}}` | env `SHUNT_LOG`; default a gitignored JSONL under the repo; named per train during the pilot | operator; banked as produced per `harness/artifact-bank.md` §2 during the pilot |
| Log-file pattern | `{{LOG_GLOBS}}` | globs that identify run/verify logs (routes to log-triage instead of bulk-read) | repo operations doc |
| Worker timeout | — | per-call ceiling in the worker adapter (one factory used 180 s) | repo operations doc |

Exit codes the skills rely on, whatever the command: `0` answer on stdout and
one metrics line on stderr; `2` input refused (boundary, not a file); `3`
every worker failed. The metrics line carries at least
`worker`, `input_tokens`, `output_tokens`, `seconds`, `lines`.

## 5. Worker-down trial (do this before registering anything)

The trial shows the escape hatch working while no worker can answer. Run it
in a throwaway directory with a fake worker on `PATH` that always fails, or
with the worker chain pointed at an unreachable alias.

```sh
# 1. A large file whose content must never leak through an error path.
printf 'line %d\n' $(seq 1 400) > big.txt
echo 'CANARY-DO-NOT-ECHO' >> big.txt

# 2. Every worker fails (fake binary that exits 1, or an unreachable chain).
#    Bind the threshold too: an unbound threshold leaves the adapter inert (§8).
export SHUNT_WORKERS=unreachable-alias        # or: PATH="$PWD/fake-bin:$PATH"
export SHUNT_MIN_LINES=350                    # the value under trial, not a constant

# 3. The shunt itself: must exit 3 and echo nothing from the file.
{{BULK_READ_CMD}} big.txt --question 'which line holds the canary?' ; echo "exit=$?"
```

Check, in order:

| Step | Expected | What a failure means |
|---|---|---|
| 3 | `exit=3`; stderr names each worker and its failure; the string `CANARY-DO-NOT-ECHO` appears nowhere in stdout or stderr | rule 6 broken — the error path leaks the corpus, or the exit code is not distinct from a refused input (`2`) |
| 4. bounded read of `big.txt` lines 395–401 through the harness (or `sed -n '395,401p' big.txt`) with the hook registered | passes without invoking the shunt; the canary line is visible | rule 5(a) broken — bounded reads must never route |
| 5. unbounded read of `big.txt` with the hook registered | blocked; the block message prints the exact shunt command **and** all three escape hatches | rule 5 broken — a message naming fewer than three hatches leaves the operator guessing |
| 6. `SHUNT_DISABLED=1` (or the bound name) then the same unbounded read | passes | rule 5(c) broken — the factory would stop when workers are down |
| 7. `SHUNT_ALLOW='big.txt'`, disable unset, same unbounded read | passes | rule 5(b) broken |
| 8. unset both, same read | blocked again | the hatch is a switch, not a latch |

Record the trial (date, command, exit codes, the eight verdicts) in the
operations doc next to the parameter table. The trial is repeated whenever
the adapter or the worker chain changes. The source factory pinned steps 3,
4, 6 and 7 as tests against a fake worker binary and tested the block message
of step 5 — but that message named two hatches (the bounded read and the
disable variable), not three, so the source would not pass step 5 as written
here; step 8 has no pinned test there. Repeat all eight in your own harness
rather than inheriting any of that.

## 6. Fact preservation (critical facts and IDs)

A shunt answer is only usable if the identifiers survive verbatim. Before
the pilot, fix the check:

1. Pick one file per shunt mode that the factory actually reads (a spec, a
   verify log, a handback).
2. Write the fact list **before** asking the worker: every identifier a
   reader would act on — slice names, test names, gate names, issue numbers,
   SHAs, exact assertion strings, line numbers where the file has them. Ten
   to twenty items; store the list beside the file.
3. Run the shunt with the narrowest question that should surface those facts.
4. Score each fact: **preserved** (verbatim), **missed** (absent),
   **misstated** (present but wrong — a shifted line number, a truncated
   name, a merged pair). Misstated counts worse than missed: it is acted on.
5. Confirm every preserved fact by a bounded read of the cited line (rule 4).

The form of the record, illustrated on a 540-line design spec with eight
slices and the question "list every slice with its name and scope files":

```
fact list (written first)         | worker answer            | score
S1 <name> — files a, b            | S1 <name> — a, b         | preserved
S2 <name> — file c                | S2 <name> — c            | preserved
...                                | ...                      |
S8 <name> — files h, i            | S8 <name> — h, i         | preserved
                                   | 8/8 preserved, 0 missed, 0 misstated
```

That table shows the method; it is not a sourced measurement. The one sourced
probe behind this contract — eight points judged correct after the fact, 31 s
wall-clock, 93 160 input / 894 output worker tokens over 542 lines, one
worker, one file, one question — was run **without** a pre-written fact list
and without preserved/missed/misstated scoring, so it is evidence that the
worker answered, not a §6 result. It is **not** a representative token
accounting and it says nothing about a train-level saving. Two more
properties the pilot has to show, which that probe did not: exact-ID
preservation on a log (line numbers under duplication) and on a handback
(SHAs, gate names, negations such as "not run" surviving into the digest).

## 7. The pilot: hook off versus hook on

Decide adoption on one otherwise comparable pair of trains — same lane count
and task shape as far as the board allows — one landed with the adapter
unregistered and the skills used only by explicit choice, one with the
adapter registered. Record, per train:

| Measure | Off | On | Source |
|---|---|---|---|
| Orchestrator cost (harness cost report, e.g. `/cost` in Claude Code) | | | the harness |
| Worker cost: calls, lines shunted, input/output tokens | n/a | | `{{SHUNT_LOG}}` summary |
| **Total** cost (orchestrator + worker, in one unit — tokens by price, or currency) | | | computed; never the orchestrator line alone |
| Tool results: count and byte size of read results entering context | | | harness transcript |
| Wall-clock: dispatch to landed, and per shunted read (round-trip) | | | run receipts (`harness/run-lifecycle.md`) |
| Quality deviation: facts missed + misstated on the §6 fact lists | 0 by construction | | §6 scoring |
| Downstream: complete rounds per accepted task, first-round-red trains | | | `planning/execution-contract.md` counts |

Report the on/off difference as a percentage **with the denominator, the
period, and the task-shape difference stated**. Log size is not token usage;
a shunt that halves the orchestrator's read bytes but doubles total spend is
a loss. One night's trains are examples, not a control group; repeat the pair
before calling a number an effect.

Decision rule: adopt (register the adapter as local policy) only if total
cost or latency improves **and** quality deviation is zero on exact
identifiers. Any misstated ID in the pilot is a finding against the worker
prompt or the worker, and the pilot repeats after the fix. Otherwise the
skills remain voluntary and the adapter stays unregistered.

**State of evidence at the source factory (as of the pin this contract was
distilled from):** hooks, wrappers, the three skills and the escape hatch
are landed and the activation probe is recorded; **no hook-off/hook-on train
comparison has been documented**. The saving is therefore a hypothesis
under test, not a documented result. Write the same sentence in your
operations doc until your own pilot replaces it.

## 8. The PreToolUse adapter (harness option)

Claude Code can run a command before a tool call and block it with exit 2.
That is one harness's mechanism; the contract does not require it. Where it
exists, the adapter does exactly this and nothing more:

- **Read tool:** if the disable variable is set → allow. If the call carries
  `offset` or `limit` → allow. If the path matches an exemption glob → allow.
  If the file has fewer than the threshold lines → allow. Otherwise block
  with a message that names the skill, prints the exact shunt command, and
  lists all three escape hatches.
- **Shell tool:** parse the command into segments; for `cat`/`head`/`tail`/
  `less`/`more`, or a `sed -n` span at least the threshold long, resolve the
  file operands (globs, `cd`, `env` prefixes) and apply the same decision. A
  file matching `{{LOG_GLOBS}}` routes to log-triage instead of bulk-read.
  `grep`, `wc`, `git diff --stat` and narrow `sed` spans are never blocked.

Minimal Read-side adapter (stdlib only; the line count and the message are
the whole policy; the threshold is read from the operator's environment and
the adapter is inert while it is unbound — rule 10, no constant in code):

```python
#!/usr/bin/env python3
import json, os, sys, fnmatch
DISABLE, MIN, ALLOW = "SHUNT_DISABLED", "SHUNT_MIN_LINES", "SHUNT_ALLOW"
CMD = "{{BULK_READ_CMD}}"  # bind to the command from contract §4
if os.environ.get(DISABLE) == "1": sys.exit(0)
if not os.environ.get(MIN, "").isdigit(): sys.exit(0)  # unbound threshold: inert (§4)
tool_input = json.load(sys.stdin).get("tool_input", {})
path = tool_input.get("file_path")
if not path or tool_input.get("offset") is not None or tool_input.get("limit") is not None: sys.exit(0)
if any(p and fnmatch.fnmatch(path, p) for p in os.environ.get(ALLOW, "").split(",")): sys.exit(0)
limit = int(os.environ[MIN])
try:
    with open(path, "rb") as fh:
        if sum(1 for _ in fh) <= limit: sys.exit(0)
except OSError: sys.exit(0)
print(f"Bounded-read contract: unbounded read of {path} is blocked (> {limit} lines). "
      f"See skill 'bulk-reader'. Escape hatches: a Read with offset/limit always passes; "
      f"{ALLOW}=<glob> exempts this path; {DISABLE}=1 disables this hook for the session. "
      f"Run exactly:\n{CMD} {path} --question '<question>'", file=sys.stderr)
sys.exit(2)
```

Registration is a separate, deliberate step in the harness settings file
(`PreToolUse`, matcher `Read`, and a second entry for the shell tool), taken
only after §5 passes and §7 has numbers. This package ships no registration.
The adapter never intercepts a lane running in another CLI; lanes that read
large files in their own harness follow that harness's own policy.

Portability of the adapter itself is empirical: the shell-side parsing
(compound commands, `cd` tracking, `env -S`, quoted paths) was the bulk of
the source factory's implementation and test surface, and it is exactly the
part a different shell or harness will break. Port the tests with the
adapter or do not port the shell side.

## 9. What stays with the responsible agent

- Debugging, root cause and hypothesis ranking (`interpretation/investigation-practice.md`).
- Architecture, seams, and any code inside a project-declared boundary.
- Security review and anything the project's own data rules classify.
- The `audit-choices` verdict and the ledger entry.
- Reading the cited source lines before acting (rule 4).

A worker output that argues a cause, proposes an edit, or grades a choice is
out of contract; treat it as noise and narrow the question.

## 10. Not in this contract

- **No automatic activation.** Installing skills or copying an adapter
  registers nothing; §3 rule 9.
- **No code-writer port.** A spec-to-code drafting shunt is a writing
  contract with its own review path; it is evaluated on its own, never
  bundled with three reading helpers.
- **No compressed handback grammar.** The source factory benchmarked a
  micro-DSL for handbacks (37 % byte saving on paper) and rejected it because
  the cheaper writer broke the grammar in twelve of twelve cases; the whole
  writer→reader chain is what is measured, not bytes. Short structured prose
  stays (`harness/report-schema.md`).
- **No inherited data rules.** The source factory's synthetic-only and
  air-gap boundaries are that project's; this contract carries only the
  requirement that a boundary exists, is checked before the worker is called,
  and fails closed (§3 rules 3 and 6).
- **No model names, thresholds or providers as constants.** §3 rule 10.
