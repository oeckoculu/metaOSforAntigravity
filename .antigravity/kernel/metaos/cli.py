"""Command-line entrypoint for Meta-OS kernel phases and journal/projection/policy/PEP/outbox/crypto utilities."""
import argparse
import os
import sys

from . import authority, canonical, contracts, crypto, env, genesis, journal, pdp, pep, phase_a5, phase_a6, phase_a7, ports, projector, scaffold, statemachine


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


def cmd_phase_a6(args):
    r = phase_a6.run(args.root)
    body = r.write(phase_a6.RECEIPT_A6_REL)
    pep_abs = os.path.join(args.root, phase_a6.PEP_RECEIPT_REL)
    with open(pep_abs, "wb") as fh:
        fh.write(canonical.pretty_bytes(body))
    sys.stdout.write(canonical.pretty_bytes(body).decode("utf-8"))
    return 0 if r.passed else 1


def cmd_phase_a7(args):
    r = phase_a7.run(args.root, keystore_dir=args.keystore_dir)
    body = r.write(phase_a7.RECEIPT_A7_REL)
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
    _, report = journal.verify_file(jpath, validator, root=args.root)
    sys.stdout.write(canonical.pretty_bytes(report).decode("utf-8"))
    return 0 if report["valid"] else 1


def cmd_project_state(args):
    view, out_bytes = projector.project_file(args.root, args.journal, args.output)
    sys.stdout.write(out_bytes.decode("utf-8"))
    return 0


def cmd_journal_append(args):
    validator = journal.load_validator(args.root)
    jpath = os.path.join(args.root, args.journal)
    entries, report = journal.verify_file(jpath, validator, root=args.root)
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
        root=args.root,
        sign_principal=spec.get("sign_principal"),
        sign_namespace=spec.get("sign_namespace"),
    )
    h = journal.append(jpath, entry, validator, root=args.root)
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


def _load_req_or_stdin(request_json):
    if request_json:
        return canonical.strict_load_file(request_json)
    raw = sys.stdin.read()
    if not raw.strip():
        return {}
    return canonical.strict_loads(raw)


def cmd_outbox_emit(args):
    if args.request_json:
        req = canonical.strict_load_file(args.request_json)
    else:
        req = {
            "kind": args.kind,
            "title": args.title,
            "summary": args.summary,
            "payload": canonical.strict_loads(args.payload_json) if args.payload_json else {},
            "run_id": args.run_id,
            "idempotency_key": args.idempotency_key,
        }
    res = ports.emit_outbox_item(
        root=args.root,
        kind=req["kind"],
        title=req["title"],
        summary=req["summary"],
        payload=req.get("payload", {}),
        run_id=req.get("run_id", "run-0000"),
        idempotency_key=req.get("idempotency_key"),
    )
    sys.stdout.write(canonical.pretty_bytes(res).decode("utf-8"))
    return 0


def cmd_outbox_ack(args):
    res = ports.acknowledge_outbox_item(
        root=args.root,
        outbox_id=args.outbox_id,
        actor_principal={"principal_id": args.principal, "kind": args.actor_kind},
        decision=args.decision,
        rationale=args.rationale,
    )
    sys.stdout.write(canonical.pretty_bytes(res).decode("utf-8"))
    return 0 if res["decision"] == "ALLOW" else 1


def cmd_pep_session_start(args):
    res = pep.evaluate_session_start(args.root)
    sys.stdout.write(canonical.pretty_bytes(res).decode("utf-8"))
    return 0 if res["decision"] == "ALLOW" else 1


def cmd_pep_pre_tool_use(args):
    req = _load_req_or_stdin(args.request_json)
    res = pep.evaluate_pre_tool_use(args.root, req)
    sys.stdout.write(canonical.pretty_bytes(res).decode("utf-8"))
    return 0 if res["decision"] == "ALLOW" else 2


def cmd_pep_post_tool_use(args):
    req = _load_req_or_stdin(args.request_json)
    res = pep.evaluate_post_tool_use(args.root, req)
    sys.stdout.write(canonical.pretty_bytes(res).decode("utf-8"))
    return 0 if res["decision"] == "ALLOW" else 2


def cmd_keys_init(args):
    manifest = crypto.init_keys(args.root, keystore_dir=args.keystore_dir, force=args.force)
    sys.stdout.write(canonical.pretty_bytes(manifest).decode("utf-8"))
    return 0


def cmd_token_issue(args):
    req = _load_req_or_stdin(args.request_json)
    tok = crypto.issue_capability_token(
        root=args.root,
        file_read=req.get("file_read", ["src/**"]),
        file_write=req.get("file_write", ["src/**"]),
        tools=req.get("tools", ["write_file", "run_tests"]),
        actions=req.get("actions", ["READ", "PROPOSE", "EXECUTE_TEST"]),
        ttl_seconds=req.get("ttl_seconds", 1800),
        issued_at=req.get("issued_at"),
        token_id=req.get("token_id"),
        agent_role=req.get("agent_role", "BuilderAgent"),
        keystore_dir=args.keystore_dir,
    )
    sys.stdout.write(canonical.pretty_bytes(tok).decode("utf-8"))
    return 0


def cmd_break_glass(args):
    req = _load_req_or_stdin(args.request_json)
    msg_bytes = canonical.jcs_bytes(req)
    sig = crypto.sign_bytes(
        data_bytes=msg_bytes,
        principal_id=req.get("principal_id", "human:oeckoculu"),
        namespace="metaos.breakglass",
        root=args.root,
        keystore_dir=args.keystore_dir,
    )
    out = dict(req)
    out["signature"] = sig
    sys.stdout.write(canonical.pretty_bytes(out).decode("utf-8"))
    return 0


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

    p_a6 = sub.add_parser("phase-a6")
    p_a6.set_defaults(func=cmd_phase_a6)

    p_a7 = sub.add_parser("phase-a7")
    p_a7.add_argument("--keystore-dir", default=None)
    p_a7.set_defaults(func=cmd_phase_a7)

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

    p_oe = sub.add_parser("outbox-emit")
    p_oe.add_argument("--request-json", default=None)
    p_oe.add_argument("--kind", default="HUMAN_AUDIT_REVIEW")
    p_oe.add_argument("--title", default="")
    p_oe.add_argument("--summary", default="")
    p_oe.add_argument("--payload-json", default=None)
    p_oe.add_argument("--run-id", default="run-0000")
    p_oe.add_argument("--idempotency-key", default=None)
    p_oe.set_defaults(func=cmd_outbox_emit)

    p_oa = sub.add_parser("outbox-ack")
    p_oa.add_argument("--outbox-id", required=True)
    p_oa.add_argument("--decision", required=True)
    p_oa.add_argument("--principal", default="human:oeckoculu")
    p_oa.add_argument("--actor-kind", default="HUMAN")
    p_oa.add_argument("--rationale", default="")
    p_oa.set_defaults(func=cmd_outbox_ack)

    p_pss = sub.add_parser("pep-session-start")
    p_pss.set_defaults(func=cmd_pep_session_start)

    p_ppt = sub.add_parser("pep-pre-tool-use")
    p_ppt.add_argument("--request-json", default=None)
    p_ppt.set_defaults(func=cmd_pep_pre_tool_use)

    p_po = sub.add_parser("pep-post-tool-use")
    p_po.add_argument("--request-json", default=None)
    p_po.set_defaults(func=cmd_pep_post_tool_use)

    p_ki = sub.add_parser("keys-init")
    p_ki.add_argument("--keystore-dir", default=None)
    p_ki.add_argument("--force", action="store_true")
    p_ki.set_defaults(func=cmd_keys_init)

    p_ti = sub.add_parser("token-issue")
    p_ti.add_argument("--request-json", default=None)
    p_ti.add_argument("--keystore-dir", default=None)
    p_ti.set_defaults(func=cmd_token_issue)

    p_bg = sub.add_parser("break-glass")
    p_bg.add_argument("--request-json", default=None)
    p_bg.add_argument("--keystore-dir", default=None)
    p_bg.set_defaults(func=cmd_break_glass)

    args = p.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
