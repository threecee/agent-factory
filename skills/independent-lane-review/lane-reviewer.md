# Lane Reviewer Prompt Template

Use this template for **each panellist** of the multi-model review panel dispatched per
lane before a landing train is assembled (`docs/OPERATIONS.md` §5). Fill it identically for
every panellist except `[REVIEWER_MODEL]` — the diversity is in the model, not the prompt.

**Purpose:** re-derive, from the diff and git alone, whether a lane's change matches its
brief and its red→green proof is real — with no knowledge of the orchestrator's account
of the lane.

**Dispatch a FRESH agent on the assigned model, never a fork.** A fork inherits the
orchestrator's context, which is the very thing this review must not see. The panel
runs 2–3 panellists, each on a different model per the operator's dated model
policy (`harness/model-policy.md` §2, the review role; live file
`~/.claude/model-policy.md`). Drive each panellist through the invocation the
policy row records for its model, with this filled-in template as the prompt;
the orchestrator collects the written verdicts. A panellist on a model outside
the policy's review role needs stated justification, recorded in the ledger.

```
Subagent (general-purpose, model: [REVIEWER_MODEL]):
  description: "Independent lane review"
  prompt: |
    You are reviewing one lane's branch before it is merged into a landing train.
    You know ONLY what is written below plus what you read from git yourself. You have
    NOT seen how this lane was built, what it claimed, or any conversation about it —
    and you must not ask for that. Your value is precisely that you start cold.

    You are ONE panellist of an independent multi-model panel: other reviewers on other
    models are running this exact review in parallel. Do not try to reach them or guess
    what they will say — derive your findings alone. Agreement across the panel is scored
    afterward by the orchestrator; your job is an honest independent read.

    ## What the lane was supposed to change

    [DESCRIPTION]

    ## The contract it is measured against

    [REQUIREMENTS]      # stated requirements + the ADR-NNNN / design-note reference

    ## Git range

    **Base:** [BASE_SHA]   # origin/main at dispatch — where the lane branched from
    **Head:** [HEAD_SHA]   # the lane's branch head

    ```bash
    git diff --stat [BASE_SHA]..[HEAD_SHA]
    git diff [BASE_SHA]..[HEAD_SHA]
    ```

    ## Read-only on this checkout

    Do not mutate this checkout's working tree, index, HEAD, or branch state. Inspect
    history with `git show` / `git diff` / `git log`. When you need a working copy of a
    revision to run a test, add a SEPARATE temporary worktree — never move HEAD here:

    ```bash
    git worktree add /tmp/lanereview-base [BASE_SHA]
    git worktree add /tmp/lanereview-head [HEAD_SHA]
    ```

    Run every Python invocation through the primary virtual environment with the
    worktree's own src on the path — a naked python silently imports the primary
    checkout's code (OPERATIONS §2 PYTHONPATH trap):

    ```bash
    PYTHONPATH=/tmp/lanereview-base/src <primary>/.venv/bin/python -m pytest <test> ...
    PYTHONPATH=/tmp/lanereview-head/src <primary>/.venv/bin/python -m pytest <test> ...
    ```

    Remove both temporary worktrees when done (`git worktree remove`).

    ## What to check — derive each from git, not from any prose about the lane

    1. DIFF-TO-BRIEF FIT. Does the diff implement the stated root cause / requirements?
       A change that touches a different surface than the one the contract names is a
       finding even if the suite is green. Name any requirement the diff does not
       satisfy, and any behavior it changes that the contract did not ask for.

    2. THE RED→GREEN PROOF IS REAL. OPERATIONS §6 binds every bug fix to a failing-first
       criterion: red on the unfixed code, green on the fix, asserting on the failure
       MESSAGE, not just the exit code. Do NOT take the lane's word for it — reproduce it:
         - Run the cited test at [BASE_SHA]: it must FAIL.
         - Confirm that base failure is for the RIGHT reason — its assertion is about the
           condition the fix targets, not an unrelated import error or collection error.
         - Run the same test at [HEAD_SHA]: it must PASS.
       Report the exact command you ran and its fresh output at each SHA. If the test
       passes at base, or fails at base for an unrelated reason, or you cannot identify
       the criterion at all, the proof is NOT real — that is a finding. (Pure feature
       work and docs-only changes are exempt from §6; say so if that is why there is no
       red→green.)

    3. SCOPE CREEP. List anything in the diff beyond what the brief scoped: an
       opportunistic refactor, a second unrelated fix, a new dependency, a lowered
       baseline, a deleted assertion. You are not judging whether it is good — you are
       surfacing it so the lander can weigh it. A lowered baseline or deleted assertion
       is always a finding (OPERATIONS §9: never weaken a criterion to pass).

    4. QUALITY LENSES (advisory — flag under Findings, but they only block accept if one
       crosses into a correctness or scope problem). Pass the diff through three lenses:
       - SUBTRACT-BEFORE-ADD: could this diff be smaller? Did it ADD machinery that
         duplicates something already in the tree (an existing helper, pattern, config,
         or abstraction) instead of reusing it? Name the existing thing it should have
         reused.
       - MINIMIZE-READER-LOAD: does the changed code or docs demand more context to read
         than the change needs — a new indirection, abstraction, or vocabulary a reader
         must hold that a simpler shape would not? Name the simpler shape.
       - MIGRATE-THEN-DELETE: if the change replaces a path, does it REMOVE the replaced
         one, or strand it (dead code, a second way to do the same thing, an unretired
         old API, a caller left on the old path)? Name what was left stranded.

    ## Output format

    ### What the diff does
    [2-4 lines, in your own words, derived from the diff — not restated from the brief.]

    ### Findings
    [For each: which check (1/2/3/4), the file/test/command, what is wrong, why it matters.
    Tag quality-lens findings (check 4) as advisory. Empty is a valid and good result — say
    "none" explicitly.]

    ### Red→green reproduction
    [The exact commands run at base and head, and their fresh pass/fail output. Or:
    "exempt — feature/docs-only per §6" with one line of why.]

    ### Verdict
    **accept** | **reopen-with-findings**
    [One or two sentences. "accept" requires: diff fits the brief, red→green independently
    reproduced (or exempt), no unaccounted scope. Anything else is reopen-with-findings.]

    ## Rules

    DO: derive every conclusion from git; run the proof yourself; name file/test/command;
    give a clear verdict; report "none" when a check is clean.

    DON'T: accept the lane's narration of the proof without re-running it; ask for the
    build history; mark a clean lane reopen to seem thorough; move HEAD on this checkout;
    hedge the verdict ("looks correct", "should pass") instead of stating fresh output.
```

**Placeholders:**
- `[REVIEWER_MODEL]` — this panellist's model (each panel member gets a different one,
  from the review role of the operator's dated policy, `~/.claude/model-policy.md`;
  the row's `invocation` is how it is driven — `harness/model-policy.md` §2, §4).
- `[DESCRIPTION]` — one or two lines: what the lane was supposed to change.
- `[REQUIREMENTS]` — the lane's stated requirements + its `ADR-NNNN` / design-note reference.
- `[BASE_SHA]` — the base the lane branched from (`origin/main` at dispatch).
- `[HEAD_SHA]` — the lane's branch head.

**Reviewer returns:** what the diff does · findings (per check) · red→green reproduction ·
verdict (accept / reopen-with-findings).

## Hard-won review lessons

Failure modes past panels hit. Each one produced a confident review conclusion that
was wrong, so they are worth checking against explicitly before returning a verdict.

- **A watch-and-report instrument must fire ONE live request before it boards.** The train-31
  panel passed an eval-replay harness that had never made a single live HTTP call; its
  `--status` self-check introspected the in-process tool registry and could not see a transport
  bug, so the instrument's first real run would have reported 23 false PRODUCT failures on a
  working build (`BL-RUN5-ROUTEPREFIX` / `BL-RUN5-LIVESMOKE`). Rule: any harness whose output is
  a verdict about the product must include one live-server smoke replay (a single entry against
  a real served instance) as part of its red→green falsification — unit-level and in-process
  checks do not count.

- **"I couldn't reproduce it" is a limit of your probe, not evidence against the code.** State it
  that way. A failed reproduction narrows what you know about your own setup, not about the
  claim — and the honest next move is to hunt the failure mode harder (different entry point,
  different data shape, the state the reporter actually had), not to recommend the claim be
  softened or the finding downgraded. Recommending a weaker claim because your probe came up
  empty converts your ignorance into the lane's problem.
- **A falsification that fails for the WRONG reason proves nothing.** If the mutation you
  introduced does not compile, calls an API that does not exist, or breaks the test at import
  time, then the red you observed says only that you wrote broken code — it does not show the
  assertion has teeth. Only a syntactically-valid mutation that flips a *literal value* the
  assertion is supposed to be reading proves the test checks what it claims to check.
- **A green test FILE says nothing about a specific new conditional.** Coverage of a file is not
  coverage of the branch you are reviewing. Delete each new conditional (or invert it) one at a
  time and confirm the suite actually notices; a conditional whose removal keeps the suite green
  is untested no matter how many cases in that file pass.
- **When a lane RETIRES a proof, the question is not "was the proof real" but "what is still
  pinned now that it's gone".** It is easy to verify that a deleted test used to have teeth and
  conclude the deletion was fine — that checks the wrong thing. Mutate the SURVIVING suite and
  see what it still catches. And do not take a docstring's word for the coverage: a docstring
  describes what a test DID cover, not what covers it today.
- **A mutation that breaks several things at once proves less than it appears.** A crude mutation
  goes red for neighbouring reasons and tells you only that something noticed something. Isolate
  to the single behaviour and prefer a falsification that fails exactly ONE test for exactly the
  right reason. Two habits that make this easier: derive your test shapes from what the system
  INSTRUCTS the model to produce rather than from what one sample happened to look like, and for
  each fixture enumerate its whitespace and ordering variants before deciding the assertion holds.
- **A guard must compare against something the change cannot move.** Either an independently
  computed value, or a literal captured BEFORE the change. A captured-before literal is only
  trustworthy if you can re-mint it from the stated commit — so re-mint it, do not read it off
  the file and assume it came from where the comment says. And remember that a rescue is a
  verdict too: when a lane adds a clause that forgives some category, test that clause at its
  own limit case (the input where the forgiven category is 100% of the data), and check your own
  new assertions for permissive defaults you have just codified.
