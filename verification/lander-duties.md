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
   block. (The smoke test shipped a red train exactly that way once.) — AND
   gated on landing authority (§ Landing authority below): a live ruling
   from the owner for THIS train, or an active standing policy that covers
   it with no hold category firing. Neither → hold, do not push.
10. Flip NUMBERS `claimed → landed`. Board sweep (Done + archive). ONE `landed`
    notification per boarded item (`../planning/board-protocol.md`
    § Notifications). Fast-forward the primary checkout. Reap lane worktrees
    and branches. Then the derived-view check (§ Derived views below).

## Landing authority

Steps 1–8 produce a verified train. Step 9 asks a different question: who
said this train may land NOW? The answer lives in one place — the operator's
landing policy, `../user-level/landing-policy.example.md`, which is
INACTIVE as shipped. Read it as the owner's grant, never as a template.

1. Run the policy check from the landing policy §1. `NO AUTHORITY` is the
   default and is not an error.
2. **No authority → hold.** Keep the train worktree and its verify log
   intact; do NOT reap. File a decision brief on the blocked item from
   `../planning/decision-brief-template.md` (options with consequences, one
   recommendation, what continues meanwhile). Status → Decision needed.
   Write the key `<item> <train sha> held` on the item, then send ONE
   notification. Wait. Do nothing irreversible.
3. **On the ruling:** the ruling is on the item (copy it there verbatim if it
   came by chat). Re-run step 8 — origin/main may have moved during the hold;
   if it did, re-confirm boarding SHAs and re-verify the re-assembled tree —
   then step 9. A hold of two hours is normal; a hold that outlives the
   train's base is a re-assembly, not a force-push.
4. **Authority → land**, only if ALL hold: the policy covers this train's
   kind (e.g. a single P1 fix lane against an In-flight, owner-approved
   item — the owner's definition, not the package's); every `requires:` line
   of the policy is met by steps 1–8; NO `holds:` category fires. The
   non-removable floor of that list is enumerated ONCE, in the landing
   policy §2 `holds:` — read it there; this file does not repeat it. Any
   floor entry firing → step 2, even under authority.
5. **After an autonomous landing:** the train's choices ledger names the
   policy (file, `valid_until`, `signed`) and the item it landed for; the
   `landed` notification is the owner's first contact with it. The owner
   may revoke the policy; the landing stands (it was verified) and the next
   train holds.

Worked reading: a train carrying one lane (a warmer-convergence fix that
blocked an owner-approved evaluation rerun), verify green on the assembled
tree, five sound choices, no migration. Policy absent → held with an A/B
brief; the owner ruled A after about two hours; the train landed (source
factory, one occurrence). Policy ACTIVE with `covers: P1 fix` → the same
train lands at step 9 and the owner reads `<item> <sha> landed`. Same train
with one unsound entry, or with a migration → held in BOTH cases.

## Derived views

Applies only when the repo has a page that displays board state (a status
page, dashboard, generated README table). The board is authority
(`../planning/board-protocol.md` § Derived views); this is the checkpoint.

1. After the board sweep in step 10, list the FULL board item set with
   pagination (`gh project item-list … --limit 100`, paging until empty —
   the default is 30 rows) and the page's rendering of the same items.
2. Compare, per boarded item: item id present on the page; status on the
   page equals the board status after the sweep; the landing SHA the page
   shows equals the SHA just pushed.
3. Record any difference on the board as a bug on the page or its
   generator, with the three values. Never edit the board to match the
   page; never hand-edit the page to match the board — regenerate it.
4. If the page cannot be regenerated before the session ends, say so in
   the landing summary. An unchecked page is the second-order failure the
   check exists to prevent: an item landed and closed on the board still
   reading "in progress" on the page, and the owner ordering the same work
   again.

Confidence: a recommended refinement (the source factory's retrospective
named it; its landing scripts flip and archive but were not observed to
compare against a page). Not a routine with a track record.
