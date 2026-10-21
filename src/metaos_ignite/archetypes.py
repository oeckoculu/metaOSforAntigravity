"""Polymorphic Project Archetype Registry & Synthesizer (DO-1 / OUT-001).

Defines the 6 universal project archetypes from SPEC_META_OS_v1.1.md Section 4.1
and the 5 language toolchain port templates (python, typescript, go, rust, generic).
Enforces V12-03 polymorphic gate proof labels:
- ArchetypeSecurityScanProof
- ArchetypePerformanceScanProof
"""

ARCHETYPE_SPECS = {
    "Backend_API": {
        "default_directories": [
            "contracts/openapi",
            "contracts/asyncapi",
            "invariants",
            "src/api",
            "src/domain",
            "src/adapters",
            "tests/contract",
            "tests/property",
            "tests/integration",
            "receipts",
            "provenance",
            "infra/migrations",
            "docs/cockpit",
        ],
        "perf_budgets": {
            "p99_latency_ms": 150,
            "max_queries_per_request": 4,
            "max_memory_mb": 256,
        },
        "security_scanners": ["sast_ast_audit", "secret_redaction_scan", "openapi_authz_matrix", "sbom_lock_verify"],
        "performance_probes": ["otel_p99_latency_gate", "n_plus_one_query_counter"],
        "agent_schedule": ["SpecArchitect", "TestOracleEngineer", "ImplementationBuilder", "SecurityVerifier", "PerformanceVerifier"],
    },
    "FullStack_Web": {
        "default_directories": [
            "contracts/ui_states",
            "contracts/api_schema",
            "invariants",
            "src/frontend",
            "src/backend",
            "src/shared",
            "tests/e2e",
            "tests/accessibility",
            "tests/visual_regression",
            "receipts",
            "provenance",
            "infra",
            "docs/cockpit",
        ],
        "perf_budgets": {
            "lcp_ms": 2000,
            "cls_max_milli": 100,
            "bundle_size_kb_max": 350,
        },
        "security_scanners": ["csp_dom_xss_audit", "csrf_session_audit", "secret_redaction_scan", "sbom_lock_verify"],
        "performance_probes": ["core_web_vitals_probe", "bundle_budget_verifier"],
        "agent_schedule": ["UXContractArchitect", "TestOracleEngineer", "FullStackBuilder", "A11yAndSecurityVerifier", "WebPerfVerifier"],
    },
    "Data_ML_Pipeline": {
        "default_directories": [
            "contracts/datasets",
            "contracts/feature_store",
            "invariants/data_drift",
            "src/pipelines",
            "src/transforms",
            "src/evaluation",
            "tests/data_quality",
            "tests/reproducibility",
            "receipts",
            "provenance/lineage",
            "infra/warehouse",
            "docs/cockpit",
        ],
        "perf_budgets": {
            "throughput_rows_per_sec_min": 10000,
            "max_memory_mb": 1024,
            "drift_kl_divergence_max_bps": 500,
        },
        "security_scanners": ["pii_leakage_scanner", "dataset_poisoning_guard", "secret_redaction_scan", "sbom_lock_verify"],
        "performance_probes": ["batch_throughput_profiler", "memory_watermark_probe"],
        "agent_schedule": ["DataContractArchitect", "LineageOracleEngineer", "PipelineBuilder", "PrivacyAndDriftVerifier", "ThroughputVerifier"],
    },
    "CLI_SDK": {
        "default_directories": [
            "contracts/src/schemas",
            "contracts/generated",
            "contracts/locks",
            "invariants",
            "src/metaos_ignite",
            "tests/golden",
            "receipts/by-run",
            "receipts/pointers",
            "provenance/sbom",
            "infra",
            "docs/cockpit",
            "docs/templates",
        ],
        "perf_budgets": {
            "cold_start_ms_max": 250,
            "full_suite_ms_max": 1000,
            "max_memory_mb": 128,
            "external_dependencies_max": 0,
        },
        "security_scanners": ["ast_dangerous_call_audit", "secret_redaction_scan", "untrusted_envelope_guard", "hermetic_sbom_verify"],
        "performance_probes": ["cold_start_latency_probe", "zero_io_leak_verifier"],
        "agent_schedule": ["SDKContractArchitect", "PropertyAndGoldenOracle", "HermeticSDKBuilder", "SupplyChainVerifier", "ColdStartVerifier"],
    },
    "Autonomous_Agent": {
        "default_directories": [
            "contracts/tool_schemas",
            "contracts/capability_scopes",
            "invariants/safety_bounds",
            "src/planner",
            "src/executor",
            "src/memory",
            "tests/adversarial",
            "tests/trajectory_golden",
            "receipts",
            "provenance/envelopes",
            "infra/sandbox",
            "docs/cockpit",
        ],
        "perf_budgets": {
            "step_decision_ms_max": 500,
            "token_budget_per_task_max": 32000,
            "max_circuit_breaker_trips": 0,
        },
        "security_scanners": ["prompt_injection_envelope_audit", "capability_token_scope_audit", "secret_redaction_scan", "sbom_lock_verify"],
        "performance_probes": ["token_efficiency_meter", "step_latency_profiler"],
        "agent_schedule": ["SafetyArchitect", "AdversarialOracleEngineer", "AgentRuntimeBuilder", "ContainmentVerifier", "TokenBudgetVerifier"],
    },
    "Embedded_IoT": {
        "default_directories": [
            "contracts/hal_interfaces",
            "contracts/telemetry_frames",
            "invariants/timing_wcet",
            "src/firmware",
            "src/drivers",
            "src/rtos_tasks",
            "tests/hil_simulation",
            "tests/fault_injection",
            "receipts",
            "provenance/firmware_signing",
            "infra/board_profiles",
            "docs/cockpit",
        ],
        "perf_budgets": {
            "wcet_microseconds_max": 500,
            "static_ram_bytes_max": 65536,
            "flash_binary_bytes_max": 262144,
        },
        "security_scanners": ["stack_bounds_static_audit", "signed_boot_manifest_verify", "secret_redaction_scan", "sbom_lock_verify"],
        "performance_probes": ["wcet_cycle_estimator", "static_ram_flash_profiler"],
        "agent_schedule": ["EmbeddedArchitect", "SILOracleEngineer", "FirmwareBuilder", "MemorySafetyVerifier", "WCETVerifier"],
    },
}

LANGUAGE_TOOLCHAINS = {
    "python": {
        "language": "python",
        "runtime": "python3 (>=3.9, stdlib-first hermetic)",
        "compiler_cmd": "python3 -m py_compile",
        "test_cmd": "python3 tests/run_suite.py --seed 42",
        "linter_cmd": "python3 -m ast",
        "mutation_engine": "metaos_ignite.ast_mutator",
        "package_lock": "stdlib-only (zero-dependency lock)",
    },
    "typescript": {
        "language": "typescript",
        "runtime": "node (>=20 LTS)",
        "compiler_cmd": "tsc --noEmit --pretty false",
        "test_cmd": "node --test",
        "linter_cmd": "eslint --max-warnings=0",
        "mutation_engine": "stryker-deterministic",
        "package_lock": "pnpm-lock.yaml",
    },
    "go": {
        "language": "go",
        "runtime": "go (>=1.22)",
        "compiler_cmd": "go build ./...",
        "test_cmd": "go test -count=1 -race ./...",
        "linter_cmd": "go vet ./...",
        "mutation_engine": "go-mutesting-deterministic",
        "package_lock": "go.sum",
    },
    "rust": {
        "language": "rust",
        "runtime": "rustc (>=1.78, edition 2021)",
        "compiler_cmd": "cargo check --locked --offline",
        "test_cmd": "cargo test --locked --offline",
        "linter_cmd": "cargo clippy -- -D warnings",
        "mutation_engine": "cargo-mutants-deterministic",
        "package_lock": "Cargo.lock",
    },
    "generic": {
        "language": "generic",
        "runtime": "posix-sh + python3-verifier",
        "compiler_cmd": "python3 tests/run_suite.py --mode COMPILE_ONLY",
        "test_cmd": "python3 tests/run_suite.py --seed 42",
        "linter_cmd": "python3 -m py_compile",
        "mutation_engine": "metaos_ignite.ast_mutator",
        "package_lock": "provenance/sbom/layer_b_sbom.json",
    },
}

REQUIRED_ORACLES = ["CONTRACT", "PROPERTY", "GOLDEN", "PERF", "SECURITY"]


def list_archetypes():
    """Return sorted list of the 6 supported universal project archetypes."""
    return sorted(ARCHETYPE_SPECS.keys())


def list_languages():
    """Return sorted list of the 5 supported language toolchain adapters."""
    return sorted(LANGUAGE_TOOLCHAINS.keys())


def synthesize_archetype_profile(archetype_id, language="python"):
    """Synthesize a deterministic, schema-validated archetype profile (V12-03)."""
    if archetype_id not in ARCHETYPE_SPECS:
        raise ValueError("Unsupported archetype_id: %r" % (archetype_id,))
    if language not in LANGUAGE_TOOLCHAINS:
        raise ValueError("Unsupported language: %r" % (language,))

    spec = ARCHETYPE_SPECS[archetype_id]
    tc = dict(LANGUAGE_TOOLCHAINS[language])
    tc["security_scanners"] = list(spec["security_scanners"])
    tc["performance_probes"] = list(spec["performance_probes"])
    tc["agent_schedule"] = list(spec["agent_schedule"])

    return {
        "schema_version": "1.0.0",
        "archetype_id": archetype_id,
        "language": language,
        "default_directories": list(spec["default_directories"]),
        "toolchain": tc,
        "security_scan_proof_kind": "ArchetypeSecurityScanProof",
        "performance_scan_proof_kind": "ArchetypePerformanceScanProof",
        "perf_budgets": dict(spec["perf_budgets"]),
        "required_oracles": list(REQUIRED_ORACLES),
    }
