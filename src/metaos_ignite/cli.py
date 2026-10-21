"""Unified CLI Entrypoint for Meta-OS Layer B (python3 -m src.metaos_ignite.cli).

Subcommands:
- compile
- verify-red
- verify-green
- assemble-proof
- project-cockpit
- render-guide
- init-new-project
"""
import argparse
import json
import os
import sys

from . import archetypes, cockpit, compiler, executor, guide, proof

ROOT_DEFAULT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))


def _print_json(obj):
    sys.stdout.write(json.dumps(obj, indent=2, sort_keys=True) + "\n")


def main(argv=None):
    parser = argparse.ArgumentParser(prog="metaos_ignite.cli")
    parser.add_argument("--root", default=ROOT_DEFAULT)
    sub = parser.add_subparsers(dest="subcommand", required=True)

    p_comp = sub.add_parser("compile")
    p_comp.add_argument("--manifest", default=".antigravity/genesis/project_manifest.json")
    p_comp.add_argument("--briefing", default=".antigravity/genesis/research_briefing.md")

    p_red = sub.add_parser("verify-red")
    p_red.add_argument("--run1", default="receipts/b1_red_oracle_run1.json")
    p_red.add_argument("--run2", default="receipts/b1_red_oracle_run2.json")

    p_green = sub.add_parser("verify-green")
    p_green.add_argument("--seed", type=int, default=42)

    p_proof = sub.add_parser("assemble-proof")
    p_proof.add_argument("--run-id", default="run-0000")
    p_proof.add_argument("--keystore-dir", default=None)

    p_cockpit = sub.add_parser("project-cockpit")
    p_cockpit.add_argument("--output-dir", default="docs/cockpit")

    p_guide = sub.add_parser("render-guide")
    p_guide.add_argument("--output-path", default="docs/IGNITE_GUIDE.md")

    p_init = sub.add_parser("init-new-project")
    p_init.add_argument("--target-root", default=None)
    p_init.add_argument("--run-id", default="run-0001")
    p_init.add_argument("--project-name", default="MetaOS_Canary_Project")
    p_init.add_argument("--archetype", default="Backend_API", choices=archetypes.list_archetypes())
    p_init.add_argument("--language", default="python", choices=archetypes.list_languages())
    p_init.add_argument("--risk-class", default="R2")
    p_init.add_argument("--dry-run", action="store_true")
    p_init.add_argument("--keystore-dir", default=None)

    args = parser.parse_args(argv)
    root = os.path.abspath(args.root)

    if args.subcommand == "compile":
        res = compiler.compile_ignition_pack(root, manifest_path=args.manifest, briefing_path=args.briefing)
        _print_json(res)
        return 0

    if args.subcommand == "verify-red":
        r1 = json.loads(open(os.path.join(root, args.run1), "rb").read().decode("utf-8"))
        r2 = json.loads(open(os.path.join(root, args.run2), "rb").read().decode("utf-8"))
        res = executor.evaluate_triple_red_oracle(r1, r2, ["ORC-001", "ORC-002", "ORC-003", "ORC-004", "ORC-005"])
        _print_json(res)
        return 0 if res["valid"] else 1

    if args.subcommand == "verify-green":
        if os.path.join(root, "tests") not in sys.path:
            sys.path.insert(0, os.path.join(root, "tests"))
        import run_suite
        rep1 = run_suite.run_suite(root=root, seed=args.seed, mode="GREEN_VERIFY")
        rep2 = run_suite.run_suite(root=root, seed=args.seed, mode="GREEN_VERIFY")
        wt_rep = executor.execute_in_worktree(root, seed=args.seed, mode="GREEN_VERIFY")
        deterministic = rep1["oracle_results"] == rep2["oracle_results"]
        ok = (
            rep1["CompilationSuccess"] is True
            and rep1["TestExitCode"] == 0
            and rep1["failures"] == 0
            and deterministic
            and wt_rep["worktree_clean_restored"] is True
        )
        out = {
            "valid": ok,
            "deterministic_replay_match": deterministic,
            "suite_run1": rep1,
            "worktree_verification": wt_rep,
        }
        _print_json(out)
        return 0 if ok else 1

    if args.subcommand == "assemble-proof":
        res = proof.assemble_proof_package(root, run_id=args.run_id, keystore_dir=args.keystore_dir)
        _print_json(res)
        return 0

    if args.subcommand == "project-cockpit":
        res = cockpit.project_cockpit(root, output_dir=args.output_dir)
        _print_json(res)
        return 0

    if args.subcommand == "render-guide":
        res = guide.render_ignite_guide(root, output_path=args.output_path)
        _print_json(res)
        return 0

    if args.subcommand == "init-new-project":
        t_root = os.path.abspath(args.target_root) if args.target_root else root
        res = compiler.ignite_new_project(
            target_root=t_root,
            run_id=args.run_id,
            project_name=args.project_name,
            primary_archetype=args.archetype,
            language=args.language,
            risk_class=args.risk_class,
            dry_run=args.dry_run,
            keystore_dir=args.keystore_dir,
        )
        _print_json(res)
        return 0

    return 1


if __name__ == "__main__":
    sys.exit(main())
