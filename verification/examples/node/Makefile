PY ?= python3
.PHONY: verify probe-import-root
probe-import-root:
	@node src/hello.js --where | tee /dev/stderr | grep -q "^$(CURDIR)/src/hello.js$$" || { echo "[import-root] HARD: entry resolved outside $(CURDIR)"; exit 1; }
verify: probe-import-root
	$(PY) -m scripts.build_adr_index --check
	$(PY) -m scripts.check_traceability
	$(PY) -m scripts.check_backlog
	$(PY) -m scripts.check_gitleaks
	node scripts/check_lint_ratchet.mjs
	node --test
