"""Command-line entrypoint for Meta-OS kernel phases and journal/projection/policy utilities."""
import argparse
import os
import sys

from . import authority, canonical, contracts, env, genesis, journal, pdp, phase_a5, projector, scaffold, statemachine


def cmd_phase_a1(args):
    r, _ = authority.run(
        args.root,
        lineage_json=args.lineage_json,
        lineage_spec=args.lineage_spec,
        upstream=args.upstream,
    )
    body = r.write(authority.RECEIPT_PATH)
    sys.stdout.write(canonical.pretty_bytes(body).decode("utf-8"))
    return 0 if r.passed else 1


def cmd_phase_a2(args):
    r = scaffold.run(args.root)
    body = r.write(scaffold.RECEIPT_PATH)
    sys.stdout.write(canonical.pretty_bytes(body).decode("utf-8"))
    return 0 if r.passed else 1


def cmd_phase_a3(args):
    r = contracts.run(args.root)
    body = r.write(contracts.RECEIPT_PATH)
    sys.stdout.write(canonical.pretty_bytes(body).decode("utf-8"))
    return 0 if r.passed else 1


def cmd_phase_a4(args):
    r = genesis.run(args.root)
    body = r.write(genesis.RECEIPT_A4_REL)
    jr_abs = os.path.join(args.root, genesis.JOURNAL_RECEIPT_REL)
    with open(jr_abs, "wb") as fh:
        fh.write(canonical.pretty_bytes(body))
    sys.stdout.write(canonical.pretty_bytes(body).decode("utf-8"))
    return 0 if r.passed else 1


def cmd_phase_a5(args):
    r = phase_a5.run(args.root)
    body = r.write(phase_a5.RECEIPT_A5_REL)
    sys.stdout.write(canonical.pretty_bytes(body).decode("utf-8"))
    return 0 if r.passed else 1


def cmd_bootstrap_a1_a4(args):
    r1, _ = authority.run(
        args.root,
        lineage_json=args.lineage_json,
        lineage_spec=args.lineage_spec,
        upstream=args.upstream,
    )
    r1.write(authority.RECEIPT_PATH)
    if not r1.passed:
        sys.stderr.write("Phase A1 failed\n")
        return 1
    r2 = scaffold.run(args.root)
    r2.write(scaffold.RECEIPT_PATH)
    if not r2.passed:
        sys.stderr.write("Phase A2 failed\n")
        return 1
    r3 = contracts.run(args.root)
    r3.write(contracts.RECEIPT_PATH)
    if not r3.passed:
        sys.stderr.write("Phase A3 failed\n")
        return 1
    return cmd_phase_a4(args)


def cmd_journal_verify(args):
    validator = journal.load_validator(args.root)
    jpath = os.path.join(args.root, args.journal)
    _, report = journal.verify_file(jpath, validator)
    sys.stdout.write(canonical.pretty_bytes(report).decode("utf-8"))
    return 0 if report["valid"] else 1


def cmd_project_state(args):
    view, out_bytes = projector.project_file(args.root, args.journal, args.output)
    sys.stdout.write(out_bytes.decode("utf-8"))
    return 0


def cmd_journal_append(args):
    validator = journal.load_validator(args.root)
    jpath = os.path.join(args.root, args.journal)
    entries, report = journal.verify_file(jpath, validator)
    if not report["valid"]:
        sys.stderr.write("journal invalid: %s\n" % "; ".join(report["errors"]))
        return 1
    spec = canonical.strict_load_file(args.entry_json)
    seq = len(entries)
    prev = entries[-1]["entry_hash"] if entries else canonical.ZERO_HASH
    entry = journal.build_entry(
        validator=validator,
        seq=seq,
        run_id=spec["run_id"],
        prev_hash=prev,
        event_type=spec["event_type"],
        actor=spec["actor"],
        payload=spec.get("payload", {}),
        reproducibility=spec.get("reproducibility") or env.reproducibility(args.root),
        transition=spec.get("transition"),
        retroactive=spec.get("retroactive", False),
        occurred_at=spec.get("occurred_at"),
        parent_run_id=spec.get("parent_run_id"),
    )
    h = journal.append(jpath, entry, validator)
    sys.stdout.write(canonical.pretty_bytes({"seq": seq, "entry_hash": h}).decode("utf-8"))
    return 0


def cmd_sm_transition(args):
    req = canonical.strict_load_file(args.request_json)
    res = statemachine.evaluate_transition(
        state_ctx=req.get("state_ctx") or statemachine.initial_context(req["from_state"]),
        from_state=req["from_state"],
        to_state=req["to_state"],
        evidence=req.get("evidence", []),
        actor_kind=req.get("actor_kind", "KERNEL"),
        retroactive=req.get("retroactive", False),
        red_oracle=req.get("red_oracle"),
        ssh_signed=req.get("ssh_signed", False),
    )
    sys.stdout.write(canonical.pretty_bytes(res).decode("utf-8"))
    return 0 if res["decision"] == "ALLOW" else 1


def cmd_pdp_eval(args):
    req = canonical.strict_load_file(args.request_json)
    mode = req.get("mode", "ADMISSION")
    if mode == "RISK_CLASSIFY":
        res = pdp.classify_risk_and_schedule(
            req.get("risk_hints", {}),
            self_modification=req.get("self_modification", False),
            layer_a_touched=req.get("layer_a_touched", False),
        )
        sys.stdout.write(canonical.pretty_bytes(res).decode("utf-8"))
        return 0
    if mode == "CAPABILITY_TOKEN":
        res = pdp.evaluate_capability_token(
            token=req.get("capability_token"),
            requested_action=req.get("requested_action"),
            requested_tool=req.get("requested_tool"),
            target_paths=req.get("target_paths", []),
            now_utc=req.get("now_utc"),
        )
        sys.stdout.write(canonical.pretty_bytes(res).decode("utf-8"))
        return 0 if res["decision"] == "ALLOW" else 1

    res = pdp.evaluate_proposal_admission(
        proposal=req.get("proposal"),
        state_ctx=req.get("state_ctx"),
        base_commit=req.get("base_commit"),
        base_tree=req.get("base_tree"),
        now_utc=req.get("now_utc"),
        red_oracle=req.get("red_oracle"),
        capability_token=req.get("capability_token"),
        human_approval=req.get("human_approval"),
    )
    sys.stdout.write(canonical.pretty_bytes(res).decode("utf-8"))
    return 0 if res["decision"] == "ALLOW" else 1


def main(argv=None):
    p = argparse.ArgumentParser(prog="metaos")
    p.add_argument("--root", default=os.getcwd(), help="Repository root directory")
    sub = p.add_subparsers(dest="cmd", required=True)

    p_a1 = sub.add_parser("phase-a1")
    p_a1.add_argument("--lineage-json", default=None)
    p_a1.add_argument("--lineage-spec", default=None)
    p_a1.add_argument("--upstream", action="append", default=[])
    p_a1.set_defaults(func=cmd_phase_a1)

    p_a2 = sub.add_parser("phase-a2")
    p_a2.set_defaults(func=cmd_phase_a2)

    p_a3 = sub.add_parser("phase-a3")
    p_a3.set_defaults(func=cmd_phase_a3)

    p_a4 = sub.add_parser("phase-a4")
    p_a4.set_defaults(func=cmd_phase_a4)

    p_a5 = sub.add_parser("phase-a5")
    p_a5.set_defaults(func=cmd_phase_a5)

    p_boot = sub.add_parser("bootstrap-a1-a4")
    p_boot.add_argument("--lineage-json", default=None)
    p_boot.add_argument("--lineage-spec", default=None)
    p_boot.add_argument("--upstream", action="append", default=[])
    p_boot.set_defaults(func=cmd_bootstrap_a1_a4)

    p_jv = sub.add_parser("journal-verify")
    p_jv.add_argument("--journal", default=projector.DEFAULT_JOURNAL)
    p_jv.set_defaults(func=cmd_journal_verify)

    p_ps = sub.add_parser("project-state")
    p_ps.add_argument("--journal", default=projector.DEFAULT_JOURNAL)
    p_ps.add_argument("--output", default=projector.DEFAULT_VIEW)
    p_ps.set_defaults(func=cmd_project_state)

    p_ja = sub.add_parser("journal-append")
    p_ja.add_argument("--journal", default=projector.DEFAULT_JOURNAL)
    p_ja.add_argument("--entry-json", required=True)
    p_ja.set_defaults(func=cmd_journal_append)

    p_sm = sub.add_parser("sm-transition")
    p_sm.add_argument("--request-json", required=True)
    p_sm.set_defaults(func=cmd_sm_transition)

    p_pdp = sub.add_parser("pdp-eval")
    p_pdp.add_argument("--request-json", required=True)
    p_pdp.set_defaults(func=cmd_pdp_eval)

    args = p.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
