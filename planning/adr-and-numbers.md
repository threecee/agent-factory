# ADRs and the number registry

## ADR discipline
- `docs/decisions/NNNN-slug.md` with frontmatter: `id: ADR-NNNN` (the
  traceability gate checks it against the filename), `status:` (Proposed /
  Accepted / Superseded / Rejected) and `code:` — a list of
  `path[::Symbol]` anchors binding the decision to the code that implements
  it (symbol resolution is Python-shaped; other stacks anchor to the file —
  `../verification/gates/README.md`, "ADR front matter").
  Only Accepted ADRs "gate" a module (see module-coverage in verification).
- A generated index (`build_adr_index.py`) is checked in verify; regenerate,
  never hand-edit.

## The number registry (NUMBERS.md)
Numbers (ADRs, schema migrations) are globally scarce and collide silently.
Rules, learned the hard way:
1. Numbers are allocated ONLY by the orchestrator. A lane that discovers it
   needs one STOPS and reports — always. (A lane that self-allocates creates
   collisions the moment two lanes do it; this happened and was caught.)
2. Claim the number FIRST: append a `claimed` row to NUMBERS.md and push it
   to main immediately, before the work exists.
3. Flip `claimed → landed` in place as part of landing the train.
4. A released number is re-claimed by rewriting its row in place — never by
   appending a duplicate row.
