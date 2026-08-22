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
written. Delete or amend wrong ones on contact.
