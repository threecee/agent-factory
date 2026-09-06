---
name: bulk-reader
description: Answer a narrow question over one or more large repository files without reading their raw content into context. Use when a bounded-read hook blocks an unbounded read of a file over the configured line threshold, or when the orchestrator needs facts (names, line numbers, counts, "does X exist") from a long spec, log, or generated document without spending context on its full text. Never for judgment calls.
---

# Bulk Reader

Route a large-file read through the factory's bulk-read command instead of
loading the file into this session's context. The command sends the file(s)
plus one narrow question to the configured worker chain and returns
structured bullets only — never the raw corpus. The rules live in
`harness/bulk-read-contract.md`; this skill is the invocation.

## Invocation

```sh
{{BULK_READ_CMD}} <path> [<path> ...] --question "<question>"
```

- `<question>` must be answerable from the file's text: names, line numbers,
  counts, "does X exist", "list every Y" — not "summarise this" or an
  open-ended judgment (contract §3 rule 2).
- Repeat the path argument for more than one input; every file is streamed
  to the worker in one request, not read into this session.
- Paths must be inside the repository or the lane scratchpad. A path outside
  that boundary is refused with exit 2 before any worker is called; pass
  `{{ALLOW_EXTERNAL_FLAG}}` only after confirming the material is approved
  for the worker's provider under the project's data rules (contract §3
  rule 3). A file path never implies approval.
- Exit 3 means every configured worker failed; nothing from the file reaches
  stdout or stderr (contract §3 rule 6). Fall back to a bounded read.
- Every bullet leads with the exact identifier. Before you act on one, read
  the cited line in the source with a bounded read (contract §3 rule 4).

## When NOT to use this

Never for debugging, root cause, architecture judgment, boundary-sensitive
code, or security review — the worker answers the literal question against
the literal text with no memory of this session's goals. Read the file
directly when the judgment itself needs the full text, not facts extracted
from it (contract §9).

## Escape hatch

A targeted read with `offset`/`limit` (or a narrow `sed -n` span, `grep`,
`wc`) always passes the hook unchanged — use that instead of this skill when
only a known slice of the file is needed. `{{SHUNT_ALLOW}}` exempts named
paths. `{{SHUNT_DISABLE}}` turns the bounded-read hooks off for the session
(for example when every configured worker is down); it is a session-wide
bypass, not a per-call override — unset it once the workers recover
(contract §3 rule 5, §5).

## Parameters

`{{BULK_READ_CMD}}`, `{{ALLOW_EXTERNAL_FLAG}}`, `{{SHUNT_ALLOW}}`,
`{{SHUNT_DISABLE}}` and the line threshold are bound in the repository's
operations doc from the table in `harness/bulk-read-contract.md` §4. The
source factory bound them to `python scripts/factory/bulk_read.py`,
`--allow-external`, `SHUNT_ALLOW`, `SHUNT_DISABLED=1` and 350 lines; those
are one operator's choices, not defaults of this skill.
