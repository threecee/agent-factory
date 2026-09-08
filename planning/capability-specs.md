# Capability specs — durable behaviour, lane deltas, and archival

## 1. Three durable artifacts

Three durable artifacts answer different questions:

| Artifact | Question it answers |
|---|---|
| Capability spec | What does the system do today? There is one capability spec for each capability in the project's feature registry. |
| Architecture decision record (ADR) | Why was this architecture chosen, and how does it work? Its existing role is unchanged. |
| Choices ledger | What did an agent decide on the owner's behalf while carrying out approved work? |

Build specs are transient. They describe the intended journey from an approved
change to proof, as the “What” rung of `core-model.md` “The ladder” defines.
After delivery, `../skills/close-spec/SKILL.md` closes that build record; the
capability spec remains as the current behavioural truth.

## 2. Capability spec and delta format

A capability spec uses the OpenSpec shape:

```markdown
## Purpose

<At least 50 characters describing the capability's user-facing purpose.>

## Requirements

### Requirement: <name>

The system SHALL <observable behaviour>.

#### Scenario: <name>

- **WHEN** <condition or action>
- **THEN** <observable result>
- **AND** <additional observable result, when needed>
```

A lane delta uses whichever of these level-two headers describe its change:
`## ADDED Requirements`, `## MODIFIED Requirements`,
`## REMOVED Requirements`, and `## RENAMED Requirements`. A MODIFIED block is
a whole-block replacement, not a patch fragment.

A capability spec says what an observer can rely on. It never contains module,
function, table, environment-variable, or migration names, and it never carries
rationale. Those implementation details and explanations belong in code,
build notes, or ADRs.

## 3. The lane delta rule

A lane that changes behaviour writes
`openspec/changes/<lane>/specs/<capability>/spec.md`. The capability name is
the matching entry in the project's feature registry; one delta cannot stand
in for another capability's delta.

A lane that does not change behaviour carries one of these commit trailers:

```text
Spec-delta: none - <reason>
Spec-delta: none - <capability>: <reason>
```

The first form covers the full commit range. The second scopes the claim to one
capability. A pairing waiver is a different claim about paired artifacts and
never substitutes for a spec delta or a `Spec-delta:` trailer.

## 4. Archive is a lander step

After all lane merges and before assembly cross-checks, the lander lists the
live change directories in stable lexical order and runs
`openspec archive <change> --yes` for each one. All resulting spec updates and
archive moves are recorded in one lander commit. Every later cross-check and
the full verification run read that post-archive HEAD.

The invariant is: **the default branch never holds a live change directory**.
An archive retry determines completion by finding exactly one directory that
matches `openspec/changes/archive/*-<id>`, not from the previous CLI exit or
from reconstructing the date. One match means the change is already archived,
no match means the lander runs the command, and multiple matches are a
conflicting archive state. The measured directory shape remains
`YYYY-MM-DD-<id>` (§8).


**New capability from an ADDED-only delta.** `openspec archive` creates the canonical file with a placeholder Purpose (`TBD - created by archiving change <id>`), and strict validation treats that placeholder as a fatal warning. The lander writes the real Purpose (at least 50 characters, linking the governing document) in the same landing commit, before the post-archive validation; a lane may pre-write it in its report so the lander only pastes it. Measured 2026-09-08.

## 5. Validation and pairing gates

The strict validation leg runs with all four non-interactive controls set:

```sh
CI=1 OPENSPEC_TELEMETRY=0 DO_NOT_TRACK=1 OPENSPEC_NO_UPDATE_CHECK=1 \
  openspec validate --all --strict
```

The pairing leg treats `spec:` as a paired artifact pattern. A delta under
capability A satisfies only capability A; it never satisfies a behavioural
change to capability B. The scoped and range-wide `Spec-delta: none` forms in
§3 are the only no-delta claims.

Both legs are advisory while any capability's `sources.md` sidecar has a
`review:` state other than `accepted`. They become HARD only after every
capability sidecar reads `review: accepted`. Strict validation still reports
its real exit code during the advisory period; advisory changes who may rely
on the result, not what the command found.

The project's validation adapter and pairing gate own that transition. Each
always runs and prints its real result. During the advisory period it labels a
finding `ADVISORY` and exits zero; after promotion it propagates a nonzero
result. The legs table and verification entry invoke the adapter, never the
raw CLI, so advisory findings cannot accidentally become a hard gate early.

## 6. Sources and the review rubric

Author an initial capability spec from evidence in this order: code and tests,
then ADRs, journeys, design notes, and paired artifacts. Later sources may
clarify intent but do not erase a divergence from observed behaviour.

Each capability has a sibling `sources.md` sidecar. It records `review:` as
`pending`, `accepted`, or `rejected`; maps every requirement to its source
paths or the literal `inferred`; lists divergences between sources; and lists
registry globs that no requirement covers. `inferred` means the requirement
needs an owner ruling, not that the inference became fact.

Review each capability against the complete rubric:

- **R1 — Purpose:** `Purpose` is at least 50 characters and at most five
  sentences; it names the audience, relevant journey identifiers, and
  relative links to governing ADRs. OpenSpec reports a shorter purpose as a
  warning, and strict validation makes warnings fatal.
- **R2 — Observable unit:** each requirement contains exactly one SHALL and
  one observable behaviour that can be checked at a UI, API, CLI, export, or
  log boundary without reading source. A negative SHALL is valid.
- **R3 — Scenario boundary:** every requirement has at least one scenario
  with WHEN and THEN; requirements and scenarios contain none of the
  implementation names excluded by §2.
- **R4 — Honest degradation:** provider-dependent capabilities cover the
  unavailable state and, where the sourced implementation has one, the
  degraded state.
- **R5 — Protected boundaries:** user-welfare and evidence-chain boundaries
  are requirements, not notes.
- **R6 — Provenance:** every requirement has sidecar sources or `inferred`
  with a reason; an unmarked inference is rejected.
- **R7 — Coverage:** every registry code glob is cited by at least one source
  or appears under uncovered globs with a reason.
- **R8 — One home:** each behaviour exists in exactly one capability spec;
  other specs refer to it by capability name.
- **R9 — Language:** prose is English, while SHALL, WHEN, THEN, and AND keep
  those exact uppercase tokens.
- **R10 — Size signal:** more than about 25 requirements or two distinct
  purposes signals that the registry entry may contain two capabilities. The
  lane reports the split question and never changes registry semantics.

## 7. Review protocol

Review proceeds through one docket per capability cluster. Each docket names
its included capabilities and gives every capability one state: `pending`,
`accepted`, or `rejected`. Acceptance updates that capability's sidecar;
landing a spec or delta does not imply acceptance. The sidecar is the
authoritative state; the docket only displays it and records the ruling that
the sidecar receives.

A rejection records one or more stable codes:

| Code | Meaning |
|---|---|
| `wrong-what` | The requirement states the wrong observable behaviour. |
| `how-leak` | The spec exposes implementation detail or rationale. |
| `missing-behaviour` | A sourced behaviour is absent. |
| `wrong-split` | The behaviour belongs to a different capability boundary. |
| `divergence-ruling` | Conflicting evidence needs an owner ruling. |

Rejected capabilities return to `pending` after correction and must be
reviewed again. Only an explicit `accepted` verdict counts toward the HARD
transition in §5.

## 8. Measured CLI facts and provisional policy

The following facts were measured against `@fission-ai/openspec` 1.12.0:

- No `project.md` or `config.yaml` is needed for strict validation.
- A `sources.md` sidecar is tolerated.
- A change directory containing only `specs/` archives successfully.
- MODIFIED must copy every surviving scenario as a whole-block replacement,
  or validation fails.
- The archive directory is named `YYYY-MM-DD-<id>`.
- Re-archive fails with `archive_change_not_found`.
- With two live deltas on one requirement, the second fails after the first
  archives.
- Telemetry and update checks are disabled with `CI=1`,
  `OPENSPEC_TELEMETRY=0`, `DO_NOT_TRACK=1`, and
  `OPENSPEC_NO_UPDATE_CHECK=1`.

The source order, sidecar review protocol, rubric, advisory period, and HARD
promotion are project policy layered around those measured CLI behaviours.
They remain provisional until every registered capability has an accepted
sidecar and the project promotes both gates by reviewed change. The CLI facts
are version-specific and must be remeasured before upgrading; the kit defines
no custom merge fallback when the pinned CLI refuses an archive.

The package-level human proof is
`../harness/tests/test_capability_spec_flow.sh`. It exercises the pinned CLI
when present and reports absence as a loud skip, never a pass.
