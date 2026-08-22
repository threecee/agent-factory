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
