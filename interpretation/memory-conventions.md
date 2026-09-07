# Memory conventions — lessons that survive sessions

One file per fact under the agent's persistent memory directory, with
frontmatter (`name`, one-line `description`, `type`: user/feedback/project/
reference), indexed by a MEMORY.md with one line per memory. Write the WHY
and HOW-TO-APPLY, not just the what; link related memories.

What earns a memory: operational traps (a tool that lies, a path that decays,
a flag that must be set), corrected assumptions (with the correction dated),
process lessons (e.g. "a non-ff push rejection during a P0 means check for a
parallel fixer before rebasing"). What doesn't: anything the repo already
records (code structure, git history, docs).

Verify memories before acting on them — they reflect what was true when
written. Delete or amend wrong ones on contact. Memory is a trail to
investigate, never a newer authority than the repository, the bank or the
board: when a memory and the repo disagree, the repo is read first and the
memory is corrected.

**Durable facts versus durable data.** A memory holds the lesson (why, how to
apply); the bytes the lesson was learned on — datasets, receipts, run output,
evidence bundles — go to the artifact bank (`harness/artifact-bank.md`), and
the memory points at the artifact **by its bank name**, never at a
scratchpad, worktree or session path. Such a path is a decayed pointer the
moment the session ends; a memory that says "results in
`<scratch>/wave-3/summary.json`" records that a result once existed, not
where to find it. When a memory cites a measurement, it cites the artifact's
README (build SHA, seed, role configuration) so a later reader can judge
whether the number still applies — a number without its provenance is a
rumour with a date.

**A nudge, never a block.** A harness may nudge at the end of a turn or right
after a compaction when the session's guard events log shows one or more
refusals or two red assembly rounds on one train, or when the operations doc
changed in the working tree (its portability claim must be re-tested): the
question is whether the lesson was written here. What counts as a lesson
stays the writer's judgement (`../harness/guards.md` §6, M-14).
