# Meta-OS v1.2 Developer Ergonomics & Operational Automation Makefile
.SHELLFLAGS := -eu -c
.ONESHELL:

.PHONY: all help test verify cockpit fast-track guide selftest lock journal-verify clean

all: verify test guide cockpit ## Run full verification, test suite, and re-project guides and cockpit

help: ## Show this help message
	@echo "================================================================="
	@echo "Meta-OS v1.2 Polymorphic Operating System — Operational Makefile"
	@echo "================================================================="
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-18s\033[0m %s\n", $$1, $$2}'

test: ## Run 5-Oracle deterministic test runner in green verification mode
	python3 tests/run_suite.py --seed 42 --mode GREEN_VERIFY

verify: lock selftest journal-verify pep ## Run all Layer A and kernel constitutional verification checks

lock: ## Verify Layer A Merkle lock integrity (97 files)
	./scripts/kernel_lock

selftest: ## Run kernel self-test and state board verification
	./scripts/kernel_selftest

journal-verify: ## Verify append-only cryptographic event journal
	./scripts/journal_verify

pep: ## Verify Policy Enforcement Point session start allow decision
	./scripts/pep_session_start

cockpit: ## Re-project Obsidian Cockpit views with zero LLM tokens (I-07)
	python3 -m src.metaos_ignite.cli project-cockpit

fast-track: ## Run automated R1 fast-track pipeline (sandbox tests, proof assembly, cockpit)
	python3 -m src.metaos_ignite.cli fast-track --risk R1

guide: ## Re-render Turkish Operator Handbook (docs/IGNITE_GUIDE.md) and External Context
	python3 -m src.metaos_ignite.cli render-guide

clean: ## Clean local python cache files
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
