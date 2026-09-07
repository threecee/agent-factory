# Gates — deterministic verification scripts

Copied from the source factory with ONE deliberate deviation (below). Each
script's docstring is its contract; a few carry localized (Norwegian) output
strings — translate strings during installation, never logic. Highlights:

- `check_ruff_ratchet.py` / `check_mypy.py` / `check_bandit.py` — one-way
  baselines with `--update` as the only path to a new baseline.
- `check_gitleaks.py` — secret scan with BOTH committed-history and
  working-tree legs. A NEW secret literal is never baselined; moved baselined
  fixtures re-baseline via `--update`.
- `check_backlog.py` — planning-doc teeth: cited-or-stamped specs, closing
  evidence on DONE rows, dangling-link detection.
- `check_module_coverage.py` — ADR/feature-map ↔ code pairing under a one-way
  cap; pair modules in waves and LOWER the cap each wave.
- `check_traceability.py`, `build_adr_index.py`, `check_number_provenance.py`,
  `check_migration_heads.py` — decision-record integrity.
- `lane_sentinel.py` — the lane heartbeat CLI.
- `check_dist_fresh.py` — frontend bundle freshness stamp (serve refuses a
  stale bundle; bundle identity is verified before visual review).

## Which gates port, which are stack-specific, which are domain choices

Measured on 2026-09-06 by copying all 24 scripts into a Node repository with
no Python project and running each the way its docstring documents
(`../examples/install-trial-node.md`). Do not copy the set uncritically:
only the first group runs outside a Python repo, and one script cannot run
anywhere as shipped.

| Group | Scripts | What a non-Python repo does |
|---|---|---|
| **Repo-agnostic decision gates** (port as-is) | `build_adr_index.py`, `check_traceability.py`, `check_backlog.py`, `check_migration_heads.py` (registry leg only), `check_gitleaks.py`, `check_number_provenance.py`, `lane_sentinel.py` | Run them with a `python3` interpreter that has **PyYAML** (the only third-party import of this group; `alembic` is imported lazily, see the deviation below) and the `gitleaks` binary. Invoke as `python3 -m scripts.<gate>` from the repo root — the docstrings' form — because they import each other as `scripts.<module>`; `python3 scripts/<gate>.py` raises `ModuleNotFoundError: No module named 'scripts'`. Pin the interpreter in the verify entry (`PY ?= python3`). Or reimplement the contract in the repo's language; the contract is the docstring. |
| **Stack-specific (Python tooling)** | `check_ruff_ratchet.py`, `check_mypy.py`, `check_bandit.py`, `check_semgrep.py` (semgrep is multi-language; the rules and the `src/` layout are the source factory's), `check_sca.py` (`uv.lock`), `check_reachability.py` (Python `ast` over `src/kripos`), `check_test_health.py` | WRITE the equivalent with the same contract: a committed per-rule baseline, exit 1 on any increase or new rule, `--update` as the only path to a new baseline, `--report` exits 0, a **missing baseline is a hard failure**. `../examples/node/check_lint_ratchet.mjs` is that contract in about fifty lines of JavaScript; substitute `eslint`/`tsc`/`npm audit` (or `golangci-lint`, `cargo clippy`, `osv-scanner` over the lockfile) as the finding source. |
| **Stack-specific (frontend / migrations / vendoring)** | `check_dist_fresh.py` (Vite inputs), `check_migration_heads.py` heads leg (Alembic), `check_vendored_plugin.py` (one vendored CLI plugin under `third_party/`) | Only if the repo has the thing: a built bundle, a migration graph, a vendored plugin. Otherwise do not copy. |
| **Domain choices of the source factory** | `check_ki_tolket_marking.py` (visible marking of model-derived UI content), `check_vocabulary.py` (rules in a project constitution), `check_consistency.py` (feature map pairing demo/help/seed), `check_entrypoint_docs.py` (model-role table, `src/kripos` packages, README targets), `check_story_coverage.py` (CUJ documents), `check_scoreboard.py` (corpus scoreboard schema) | Read the docstring as a design idea; port the METHOD only if the repo has the same need (a paired-artifact rule, a forbidden-vocabulary lint). Never as a requirement of the factory. |
| **Cannot run as shipped** | `check_contract_touch.py` | Imports `scripts.check_egress`, which this package does not ship (a domain gate over the source factory's egress seam). Listed for honesty; supply your own contract classifier or drop it. |

`check_number_provenance.py` is repo-agnostic in shape (a positive annotation
on a narrow claim surface) but its default surface list names the source
factory's files; set the surface for your repo.

## Dependency clusters (ship together)
`check_backlog.py` imports `check_traceability.py` AND `check_migration_heads.py`;
`build_adr_index.py`, `check_module_coverage.py`, `check_contract_touch.py`
and `check_test_health.py` import `check_traceability.py` (and more). All of
these need `PyYAML`.

**The one deviation from verbatim.** `check_migration_heads.py` imported
`alembic` at module top, so `check_backlog.py` — which only uses its
NUMBERS-registry helpers — could not run in a repository without migrations
unless `alembic` was installed for nothing. The import now happens inside
`get_heads()` (the single-head leg); the registry leg and everything
`check_backlog.py` imports are unchanged. Recorded here so a re-copy from
the source factory does not silently reintroduce the dependency.

## ADR front matter the traceability gate actually requires
`id: ADR-NNNN` (checked against the filename; `id_mismatch` otherwise),
`status:` in {Proposed, Accepted, Superseded, Rejected}, `code:` and
optionally `tests:` as `path[::Symbol]` anchors. The symbol grammar is
Python-shaped — `def`/`class`/`async def` or `NAME =`/`NAME:` at line
start — so `src/hello.js::greet` on `function greet()` reads as "symbol
gone"; anchor other stacks to the file (or to a `class`). The reverse leg
(`ADR-NNNN` back-references) reads only `*.py` under `src/` and `tests/`;
extending the suffix set is a logic change — record it when you make it.

## Gitleaks specifics (falsification guidance)
- Copy `gitleaks.toml.example` → repo root as `.gitleaks.toml` (the gate fails
  closed without it). It extends the DEFAULT ruleset. Generate both baselines
  once with `--update`; the gate is HARD on a missing baseline.
- The WORKING-TREE leg is advisory by design (a hit there is fixable before
  commit — it prints, exit stays 0); the COMMITTED-HISTORY leg is the HARD
  gate (exit 1 — rewrite the commit).
- When falsifying: plant a RANDOM-shaped secret. Known documentation keys
  (e.g. AWS's AKIAIOSFODNN7EXAMPLE) are allowlisted inside gitleaks itself and
  will NOT fire — a falsification that plants one falsifies nothing.
- `gitleaks git` scans ALL refs: a secret on a throwaway branch reds the gate
  everywhere until the branch is deleted. Deleting the branch is enough
  (checked 2026-09-06: exit 1 with the branch, exit 0 right after
  `git branch -D`, no prune needed).
