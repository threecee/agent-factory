# Lander duties — the landing train

The orchestrator (lander) assembles and lands; lanes never push main.

1. Create the train worktree from the CURRENT origin/main SHA.
2. `--no-ff` merge each lane's PINNED handback SHA (never branch names).
3. Assembly cross-checks: one migration head; number registry consistent
   (regenerated indexes from multiple lanes merge-conflict here — resolve by
   regenerating once on the assembled tree); counter-like edits from parallel
   lanes merged "clean" can still be wrong — set base+N at assembly.
4. The choices ledger for the train is committed WITH the train.
5. Cheap gates by direct exit code on the assembled tree.
6. Frontend-touching trains: build the release bundle on the assembled tree
   and run the full frontend suite (worktree node-module symlinks can break
   bundlers — a real install in the train worktree, then re-install in the
   primary afterwards, is the known workaround).
7. FULL verify green on the assembled tree. If a mid-verify edit becomes
   necessary, STOP the verify first; never mutate a tree under a running
   verify (each such mutation costs a full re-run).
8. Re-confirm currency: fetch; if origin/main moved, READ what landed before
   rebasing — a non-ff rejection during an incident usually means a parallel
   session fixed the same thing (stand down if their fix is complete).
9. Push HEAD:main GATED ON the verify verdict — mechanically
   (`make verify && git push …`), never as two statements in one unconditional
   block. (The smoke test shipped a red train exactly that way once.)
10. Flip NUMBERS `claimed → landed`. Board sweep (Done + archive). Fast-forward
    the primary checkout. Reap lane worktrees and branches.
