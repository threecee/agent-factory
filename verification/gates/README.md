# Gates — deterministic verification scripts

Copied verbatim from the source factory. Each script's docstring is its
contract; a few carry localized (Norwegian) output strings — translate strings
during installation, never logic. Highlights:

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


## Dependency clusters (ship together)
`check_backlog.py` imports `check_traceability.py` AND `check_migration_heads.py`
(which needs `alembic` on the venv even in repos without migrations — install it
or strip the import during adaptation). `build_adr_index.py` imports
`check_traceability.py`. The smoke test found these the hard way.

## Gitleaks specifics (falsification guidance)
- Copy `gitleaks.toml.example` → repo root as `.gitleaks.toml` (the gate fails
  closed without it). It extends the DEFAULT ruleset.
- The WORKING-TREE leg is advisory by design (a hit there is fixable before
  commit — it prints, exit stays 0); the COMMITTED-HISTORY leg is the HARD
  gate (exit 1 — rewrite the commit).
- When falsifying: plant a RANDOM-shaped secret. Known documentation keys
  (e.g. AWS's AKIAIOSFODNN7EXAMPLE) are allowlisted inside gitleaks itself and
  will NOT fire — a falsification that plants one falsifies nothing.
- `gitleaks git` scans ALL refs: a secret on a throwaway branch reds the gate
  everywhere until the branch is deleted.
