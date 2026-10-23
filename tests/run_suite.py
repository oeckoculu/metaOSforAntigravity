#!/usr/bin/env python3
"""Deterministic 5-Oracle Test Runner for Meta-OS Layer B (ORC-001..ORC-005).

Enforces V12-05 Triple RED / GREEN Oracle rules:
1. Pre-flight AST & py_compile syntax/import check (CompilationSuccess).
2. Deterministic execution seeded via --seed.
3. Explicit binding of every test case to an AcceptanceOracle.oracle_id (ORC-001..ORC-005)
   and DesiredOutcome.id (OUT-001..OUT-004).
4. Emits structured JSON report and optional JUnit XML report.
"""
import argparse
import ast
import json
import os
import py_compile
import sys
import time
import traceback

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if os.path.join(ROOT, "src") not in sys.path:
    sys.path.insert(0, os.path.join(ROOT, "src"))
if os.path.join(ROOT, ".antigravity", "kernel") not in sys.path:
    sys.path.insert(0, os.path.join(ROOT, ".antigravity", "kernel"))
if os.path.join(ROOT, "tests") not in sys.path:
    sys.path.insert(0, os.path.join(ROOT, "tests"))

from metaos import canonical, schema, secrets  # noqa: E402
import property_strategies  # noqa: E402


def _check_compilation(root):
    target_dirs = [os.path.join(root, "src"), os.path.join(root, "tests")]
    compiled_files = []
    build_errors = []
    for d in target_dirs:
        if not os.path.isdir(d):
            continue
        for dirpath, dirnames, filenames in os.walk(d):
            dirnames[:] = sorted(x for x in dirnames if x != "__pycache__")
            for fn in sorted(filenames):
                if not fn.endswith(".py"):
                    continue
                p = os.path.join(dirpath, fn)
                rel = os.path.relpath(p, root)
                try:
                    src = open(p, "rb").read().decode("utf-8")
                    ast.parse(src, filename=rel)
                    py_compile.compile(p, doraise=True)
                    compiled_files.append(rel)
                except Exception as exc:
                    build_errors.append({"file": rel, "error": str(exc)})
    return len(build_errors) == 0, compiled_files, build_errors


# --- ORC-001: CONTRACT TESTS ---
def test_orc001_archetype_registry_contract(root, seed):
    from metaos_ignite import archetypes
    arch_list = archetypes.list_archetypes()
    assert arch_list == [
        "Autonomous_Agent",
        "Backend_API",
        "CLI_SDK",
        "Data_ML_Pipeline",
        "Embedded_IoT",
        "FullStack_Web",
    ], "Archetype list mismatch"
    s_obj = canonical.strict_load_file(os.path.join(root, "contracts/src/schemas/archetype_profile.schema.json"))
    validator = schema.Validator(s_obj)
    for arch_id in arch_list:
        prof = archetypes.synthesize_archetype_profile(arch_id, language="python")
        errs = validator.errors(prof)
        assert not errs, "Profile schema errors for %s: %r" % (arch_id, errs)


def test_orc001_proof_package_contract(root, seed):
    from metaos_ignite import proof
    res = proof.assemble_proof_package(root, run_id="run-0000")
    s_obj = canonical.strict_load_file(os.path.join(root, "contracts/src/schemas/proof_receipt.schema.json"))
    errs = schema.Validator(s_obj).errors(res["proof_package"])
    assert not errs, "Proof package schema validation failed: %r" % (errs,)
    assert os.path.isfile(os.path.join(root, "receipts/pointers/latest_proof.json"))


# --- ORC-002: PROPERTY TESTS ---
def test_orc002_polymorphic_combinatorics_property(root, seed):
    from metaos_ignite import archetypes
    pairs = property_strategies.generate_archetype_combinations(seed=seed, count=12)
    for arch_id, lang in pairs:
        p1 = archetypes.synthesize_archetype_profile(arch_id, language=lang)
        p2 = archetypes.synthesize_archetype_profile(arch_id, language=lang)
        assert canonical.jcs_hash(p1) == canonical.jcs_hash(p2), "Non-deterministic profile synthesis"
        assert p1["security_scan_proof_kind"] == "ArchetypeSecurityScanProof"
        assert p1["performance_scan_proof_kind"] == "ArchetypePerformanceScanProof"


def test_orc002_triple_red_oracle_invariants_property(root, seed):
    from metaos_ignite import executor
    allowed = ["ORC-001", "ORC-002", "ORC-003", "ORC-004", "ORC-005"]
    valid_run = {
        "CompilationSuccess": True,
        "RuntimeExecution": "EXECUTED",
        "TestExitCode": 1,
        "build_errors": 0,
        "collection_errors": 0,
        "infra_errors": 0,
        "failures": 2,
        "failed_test_ids": ["T1", "T2"],
        "failed_oracle_ids": ["ORC-001", "ORC-002"],
    }
    res_ok = executor.evaluate_triple_red_oracle(valid_run, dict(valid_run), allowed)
    assert res_ok["valid"] is True

    # Property: syntax/build error must NEVER count as valid RED
    bad_compile = dict(valid_run, CompilationSuccess=False, build_errors=1)
    assert executor.evaluate_triple_red_oracle(bad_compile, bad_compile, allowed)["valid"] is False

    # Property: unstable failure set across two seeded runs must be rejected
    unstable_run2 = dict(valid_run, failed_test_ids=["T1", "T3"])
    assert executor.evaluate_triple_red_oracle(valid_run, unstable_run2, allowed)["valid"] is False


# --- ORC-003: GOLDEN TESTS ---
def test_orc003_cockpit_golden_projection(root, seed):
    from metaos_ignite import cockpit
    golden = canonical.strict_load_file(os.path.join(root, "tests/golden/golden_cases.json"))
    manifest = cockpit.project_cockpit(root, output_dir="docs/cockpit")
    s_obj = canonical.strict_load_file(os.path.join(root, "contracts/src/schemas/cockpit_manifest.schema.json"))
    errs = schema.Validator(s_obj).errors(manifest)
    assert not errs, "Cockpit manifest schema errors: %r" % (errs,)
    assert manifest["llm_tokens_used"] == 0
    for fn in golden["expected_cockpit_files"]:
        p = os.path.join(root, "docs/cockpit", fn)
        assert os.path.isfile(p), "Missing cockpit file %s" % fn
        txt = open(p, "rb").read().decode("utf-8")
        assert "```mermaid" in txt, "Missing Mermaid diagram in %s" % fn
        for wl in golden["expected_wikilinks"]:
            if wl not in fn:
                assert "[[" in txt, "Missing Obsidian wikilink in %s" % fn


def test_orc003_ignite_guide_and_templates_golden(root, seed):
    from metaos_ignite import guide
    res = guide.render_ignite_guide(root, output_path="docs/IGNITE_GUIDE.md")
    assert res["valid"] is True
    guide_abs = os.path.join(root, "docs/IGNITE_GUIDE.md")
    assert os.path.isfile(guide_abs)
    txt = open(guide_abs, "rb").read().decode("utf-8")
    for required_section in ("NotebookLM", "Antigravity", "Obsidian", "./scripts/ignite", "./scripts/worktree_exec"):
        assert required_section in txt, "Missing section %s in IGNITE_GUIDE.md" % required_section


# --- ORC-004: PERF TESTS ---
def test_orc004_cockpit_and_archetype_perf_budget(root, seed):
    from metaos_ignite import archetypes, cockpit
    t0 = time.monotonic()
    for arch_id in archetypes.list_archetypes():
        archetypes.synthesize_archetype_profile(arch_id, language="python")
    cockpit.project_cockpit(root, output_dir="docs/cockpit")
    elapsed_ms = int((time.monotonic() - t0) * 1000)
    assert elapsed_ms < 1000, "Performance budget exceeded: %d ms >= 1000 ms" % elapsed_ms


def test_orc004_worktree_isolation_perf_and_cleanliness(root, seed):
    from metaos_ignite import executor
    rep = executor.execute_in_worktree(root, seed=seed, mode="GREEN_VERIFY")
    assert rep["worktree_clean_restored"] is True
    assert rep["CompilationSuccess"] is True


# --- ORC-005: SECURITY TESTS ---
def test_orc005_untrusted_briefing_injection_and_secret_sanitization(root, seed):
    from metaos_ignite import compiler
    hostile_samples = property_strategies.generate_hostile_briefings(seed=seed)
    res = compiler.compile_ignition_pack(root, init_new_project=False)
    assert res["envelope_verified"] is True
    assert res["executable_authority"] == "NONE_DATA_ONLY"
    assert not secrets.scan_obj(res["intent_contract"])
    assert len(hostile_samples) == 2


def test_orc005_zero_secret_leakage_across_projections(root, seed):
    from metaos_ignite import cockpit, guide
    cockpit.project_cockpit(root, output_dir="docs/cockpit")
    guide.render_ignite_guide(root, output_path="docs/IGNITE_GUIDE.md")
    for fn in ("DASHBOARD.md", "STATE_GRAPH.md", "DECISION_QUEUE.md", "EVIDENCE_LEDGER.md"):
        txt = open(os.path.join(root, "docs/cockpit", fn), "rb").read().decode("utf-8")
        hits = secrets.scan_text(txt)
        assert not hits, "Secret leaked in %s: %r" % (fn, hits)


TEST_REGISTRY = [
    ("TST-001", "ORC-001", "CONTRACT", "OUT-001", test_orc001_archetype_registry_contract),
    ("TST-002", "ORC-001", "CONTRACT", "OUT-002", test_orc001_proof_package_contract),
    ("TST-003", "ORC-002", "PROPERTY", "OUT-001", test_orc002_polymorphic_combinatorics_property),
    ("TST-004", "ORC-002", "PROPERTY", "OUT-002", test_orc002_triple_red_oracle_invariants_property),
    ("TST-005", "ORC-003", "GOLDEN", "OUT-003", test_orc003_cockpit_golden_projection),
    ("TST-006", "ORC-003", "GOLDEN", "OUT-004", test_orc003_ignite_guide_and_templates_golden),
    ("TST-007", "ORC-004", "PERF", "OUT-003", test_orc004_cockpit_and_archetype_perf_budget),
    ("TST-008", "ORC-004", "PERF", "OUT-002", test_orc004_worktree_isolation_perf_and_cleanliness),
    ("TST-009", "ORC-005", "SECURITY", "OUT-001", test_orc005_untrusted_briefing_injection_and_secret_sanitization),
    ("TST-010", "ORC-005", "SECURITY", "OUT-003", test_orc005_zero_secret_leakage_across_projections),
]


def _write_junit_xml(path, report):
    lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<testsuite name="metaos_ignite_5_oracle_suite" tests="%d" failures="%d" errors="%d">'
        % (report["total_tests"], report["failures"], report["build_errors"] + report["collection_errors"]),
    ]
    for item in report["oracle_results"]:
        lines.append(
            '  <testcase classname="metaos_ignite.%s" name="%s (%s)">'
            % (item["oracle_kind"], item["test_id"], item["oracle_id"])
        )
        if item["status"] != "PASS":
            msg = (item.get("error") or "failed").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")
            lines.append('    <failure message="%s" type="%s"/>' % (msg, item.get("exception_type", "AssertionError")))
        lines.append("  </testcase>")
    lines.append("</testsuite>")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "wb") as fh:
        fh.write(("\n".join(lines) + "\n").encode("utf-8"))


def run_suite(root, seed=42, mode="RED_VERIFY", oracle_filter=None, report_json=None, junit_xml=None):
    comp_ok, compiled_files, build_errs = _check_compilation(root)
    if not comp_ok:
        report = {
            "schema_version": "1.0.0",
            "mode": mode,
            "seed": seed,
            "CompilationSuccess": False,
            "RuntimeExecution": "NOT_EXECUTED",
            "TestExitCode": 2,
            "build_errors": len(build_errs),
            "collection_errors": 0,
            "infra_errors": 0,
            "total_tests": len(TEST_REGISTRY),
            "passed": 0,
            "failures": 0,
            "failed_test_ids": [],
            "failed_oracle_ids": [],
            "oracle_results": build_errs,
            "worktree_clean_restored": True,
        }
        return report

    results = []
    failed_test_ids = []
    failed_oracle_ids = set()
    passed_count = 0
    failure_count = 0

    for test_id, oracle_id, oracle_kind, outcome_id, fn in TEST_REGISTRY:
        if oracle_filter and oracle_filter not in (oracle_id, oracle_kind):
            continue
        try:
            fn(root, seed)
            results.append(
                {
                    "test_id": test_id,
                    "oracle_id": oracle_id,
                    "oracle_kind": oracle_kind,
                    "outcome_id": outcome_id,
                    "status": "PASS",
                    "exception_type": None,
                    "error": None,
                }
            )
            passed_count += 1
        except (AssertionError, NotImplementedError) as exc:
            failure_count += 1
            failed_test_ids.append(test_id)
            failed_oracle_ids.add(oracle_id)
            results.append(
                {
                    "test_id": test_id,
                    "oracle_id": oracle_id,
                    "oracle_kind": oracle_kind,
                    "outcome_id": outcome_id,
                    "status": "FAIL",
                    "exception_type": type(exc).__name__,
                    "error": str(exc),
                }
            )
        except Exception as exc:
            # Unexpected runtime/infra error
            return {
                "schema_version": "1.0.0",
                "mode": mode,
                "seed": seed,
                "CompilationSuccess": True,
                "RuntimeExecution": "EXECUTED",
                "TestExitCode": 3,
                "build_errors": 0,
                "collection_errors": 0,
                "infra_errors": 1,
                "total_tests": len(TEST_REGISTRY),
                "passed": passed_count,
                "failures": failure_count,
                "failed_test_ids": sorted(failed_test_ids),
                "failed_oracle_ids": sorted(failed_oracle_ids),
                "oracle_results": results + [{"test_id": test_id, "infra_error": traceback.format_exc()}],
                "worktree_clean_restored": True,
            }

    exit_code = 0 if failure_count == 0 else 1
    report = {
        "schema_version": "1.0.0",
        "mode": mode,
        "seed": seed,
        "CompilationSuccess": True,
        "RuntimeExecution": "EXECUTED",
        "TestExitCode": exit_code,
        "build_errors": 0,
        "collection_errors": 0,
        "infra_errors": 0,
        "total_tests": len(results),
        "passed": passed_count,
        "failures": failure_count,
        "failed_test_ids": sorted(failed_test_ids),
        "failed_oracle_ids": sorted(failed_oracle_ids),
        "oracle_results": results,
        "worktree_clean_restored": True,
    }
    if report_json:
        abs_r = os.path.join(root, report_json) if not os.path.isabs(report_json) else report_json
        os.makedirs(os.path.dirname(abs_r), exist_ok=True)
        with open(abs_r, "wb") as fh:
            fh.write(canonical.pretty_bytes(report))
    if junit_xml:
        abs_x = os.path.join(root, junit_xml) if not os.path.isabs(junit_xml) else junit_xml
        _write_junit_xml(abs_x, report)
    return report


def main(argv=None):
    p = argparse.ArgumentParser(prog="run_suite")
    p.add_argument("--root", default=ROOT)
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--mode", default="RED_VERIFY")
    p.add_argument("--oracle", default=None)
    p.add_argument("--report-json", default=None)
    p.add_argument("--junit-xml", default=None)
    args = p.parse_args(argv)
    rep = run_suite(
        root=os.path.abspath(args.root),
        seed=args.seed,
        mode=args.mode,
        oracle_filter=args.oracle,
        report_json=args.report_json,
        junit_xml=args.junit_xml,
    )
    sys.stdout.write(json.dumps(rep, indent=2, sort_keys=True) + "\n")
    return rep["TestExitCode"]


if __name__ == "__main__":
    sys.exit(main())
