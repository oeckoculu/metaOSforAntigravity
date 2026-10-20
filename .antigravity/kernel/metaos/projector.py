"""State Projector: deterministic replay of a journal into a materialized view (I-03).

Supports both the baseline v1.1.0 lifecycle table and the compiled v1.2.0
state machine guard engine (including exception/recovery transitions EX-01..EX-12,
TOKEN_ISSUED, and cryptographically signed BREAK_GLASS_OVERRIDE events).
"""
import os
import re

from . import canonical, crypto, journal, receipt, statemachine

VIEW_VERSION = "1.0.0"
DEFAULT_JOURNAL = ".antigravity/events/run-0000.jsonl"
DEFAULT_VIEW = ".antigravity/views/state_board.json"
AUTHORITY_PATH = ".antigravity/schemas/invariants_and_states.json"


class ProjectionError(Exception):
    pass


def lifecycle_table(authority):
    table = {}
    for idx, row in enumerate(authority["state_machine"]["lifecycle_transitions"], start=1):
        table[row["current_state"]] = {
            "guard_id": "LC-%02d" % idx,
            "allowed_next_states": list(row["allowed_next_states"]),
            "required_evidence": row["required_evidence"],
        }
    return table


def evidence_satisfied(requirement, provided):
    """'A & B' -> all; 'A or B' -> any. Labels compared without parameters."""
    alternatives = [alt.strip() for alt in re.split(r"\s+or\s+", requirement)]
    for alt in alternatives:
        labels = [re.sub(r"\(.*\)$", "", part.strip()) for part in alt.split("&")]
        if all(lbl in provided for lbl in labels):
            return True, alt
    return False, None


def _verify_artifact_on_disk(root, rel_path, expected_ref):
    abs_path = os.path.join(root, rel_path)
    if not os.path.isfile(abs_path):
        raise ProjectionError("referenced artifact missing on disk: %s" % rel_path)
    actual = canonical.file_sha256(abs_path)
    if actual != expected_ref:
        raise ProjectionError("artifact hash mismatch for %s: expected %s != %s" % (rel_path, expected_ref, actual))


def replay(entries, authority, journal_path, root=None):
    table = lifecycle_table(authority)
    state = authority["state_machine"]["initial_state"]
    sm_ctx = statemachine.initial_context(state=state, risk_class="R0", genesis_approved=False)
    history = []
    evidence = []
    waivers = []
    issued_tokens = []
    break_glass_events = []
    genesis = None

    for e in entries:
        et = e["event_type"]
        if e["seq"] == 0 and et != "GENESIS_BOOTSTRAP":
            raise ProjectionError("seq 0 must be GENESIS_BOOTSTRAP")
        if et == "GENESIS_BOOTSTRAP":
            p = e["payload"]
            if p["decision"] != "APPROVED":
                raise ProjectionError("genesis bootstrap not approved")
            if root is not None:
                _verify_artifact_on_disk(root, p["proposal_path"], p["proposal_ref"])
                _verify_artifact_on_disk(root, p["approval_record"]["path"], p["approval_record"]["sha256"])
                _verify_artifact_on_disk(root, p["blueprint"]["path"], p["blueprint"]["sha256"])
            genesis = {
                "proposal_id": p["proposal_id"],
                "proposal_ref": p["proposal_ref"],
                "decision": p["decision"],
                "accepted_patch_ids": sorted(p["accepted_patch_ids"]),
                "approval_record_sha256": p["approval_record"]["sha256"],
                "entry_hash": e["entry_hash"],
            }
            sm_ctx["genesis_approved"] = True
        elif et == "STATE_TRANSITION":
            t = e["transition"]
            if t["from_state"] != state:
                raise ProjectionError("seq %d: from_state %s != current %s" % (e["seq"], t["from_state"], state))
            if root is not None:
                for ev_ref in t["evidence_refs"]:
                    if "path" in ev_ref:
                        _verify_artifact_on_disk(root, ev_ref["path"], ev_ref["ref"])
            provided = set(x["kind"] for x in t["evidence_refs"]) | set(w["evidence"] for w in t["waivers"])
            row = table.get(state)
            if row is not None and t["to_state"] in row["allowed_next_states"] and t["guard_id"] == row["guard_id"]:
                if t["to_state"] == "GENESIS_LOCKED" and genesis is None:
                    raise ProjectionError("GENESIS_LOCKED requires an approved GENESIS_BOOTSTRAP event")
                ok, branch = evidence_satisfied(row["required_evidence"], provided)
                if not ok:
                    raise ProjectionError("seq %d: required evidence '%s' not satisfied (fail-closed)" % (e["seq"], row["required_evidence"]))
                for w in t["waivers"]:
                    waivers.append({"seq": e["seq"], "evidence": w["evidence"], "follow_up": w["follow_up"], "status": "OPEN"})
                history.append({
                    "seq": e["seq"],
                    "from": state,
                    "to": t["to_state"],
                    "guard_id": row["guard_id"],
                    "satisfied_by": branch,
                    "retroactive": e["retroactive"],
                })
                state = t["to_state"]
                sm_ctx["current_state"] = state
                sm_ctx["suspended_from"] = t.get("suspended_from")
            else:
                # Evaluate via compiled v1.2.0 state machine guard engine (exception/recovery/branch guards)
                is_ssh_signed = e.get("signature", {}).get("alg") == "sshsig-ed25519"
                sm_res = statemachine.evaluate_transition(
                    state_ctx=sm_ctx,
                    from_state=state,
                    to_state=t["to_state"],
                    evidence=sorted(provided),
                    actor_kind=e["actor"]["kind"],
                    retroactive=e["retroactive"],
                    ssh_signed=is_ssh_signed,
                )
                if sm_res["decision"] != "ALLOW":
                    raise ProjectionError(
                        "seq %d: illegal transition %s -> %s (%s)"
                        % (e["seq"], state, t["to_state"], sm_res["reason"])
                    )
                if t["guard_id"] != sm_res["guard_id"]:
                    raise ProjectionError(
                        "seq %d: guard_id mismatch (%r != %r)" % (e["seq"], t["guard_id"], sm_res["guard_id"])
                    )
                for w in t["waivers"]:
                    waivers.append({"seq": e["seq"], "evidence": w["evidence"], "follow_up": w["follow_up"], "status": "OPEN"})
                history.append({
                    "seq": e["seq"],
                    "from": state,
                    "to": t["to_state"],
                    "guard_id": sm_res["guard_id"],
                    "satisfied_by": " & ".join(sorted(provided)),
                    "retroactive": e["retroactive"],
                })
                sm_ctx = sm_res["next_state_ctx"]
                state = sm_ctx["current_state"]
        elif et == "EVIDENCE_RECORDED":
            p = e["payload"]
            if root is not None:
                rec_abs = os.path.join(root, p["receipt_path"])
                if not os.path.isfile(rec_abs):
                    raise ProjectionError("receipt missing on disk: %s" % p["receipt_path"])
                ok_rec, claimed = receipt.verify_receipt_file(rec_abs)
                if not ok_rec or claimed != p["receipt_hash"]:
                    raise ProjectionError("receipt integrity check failed for %s" % p["receipt_path"])
            evidence.append({
                "seq": e["seq"],
                "phase": p["phase"],
                "receipt_path": p["receipt_path"],
                "receipt_hash": p["receipt_hash"],
                "status": p["status"],
            })
        elif et == "TOKEN_ISSUED":
            p = e["payload"]
            if root is not None and "token_path" in p and "token_sha256" in p:
                _verify_artifact_on_disk(root, p["token_path"], p["token_sha256"])
            issued_tokens.append({
                "seq": e["seq"],
                "token_id": p.get("token_id"),
                "agent_role": p.get("agent_role"),
                "issued_at": p.get("issued_at"),
                "expires_at": p.get("expires_at"),
                "token_sha256": p.get("token_sha256"),
            })
        elif et == "BREAK_GLASS_OVERRIDE":
            p = e["payload"]
            sig = e.get("signature", {})
            if e.get("actor", {}).get("kind") != "HUMAN" or sig.get("alg") != "sshsig-ed25519":
                raise ProjectionError("seq %d: BREAK_GLASS_OVERRIDE requires HUMAN actor and sshsig-ed25519 signature (I-15)" % e["seq"])
            if root is not None:
                if "override_path" in p and "override_sha256" in p:
                    _verify_artifact_on_disk(root, p["override_path"], p["override_sha256"])
                ver = crypto.verify_signature(
                    data_bytes=e["entry_hash"].encode("utf-8"),
                    sig_obj=sig,
                    principal_id=e["actor"]["principal_id"],
                    expected_namespace=sig["namespace"],
                    root=root,
                )
                if not ver["valid"]:
                    raise ProjectionError("seq %d: BREAK_GLASS_OVERRIDE signature invalid: %s" % (e["seq"], ver["reason"]))
            break_glass_events.append({
                "seq": e["seq"],
                "override_id": p.get("override_id"),
                "incident_severity": p.get("incident_severity"),
                "actor": e["actor"]["principal_id"],
                "key_id": sig.get("key_id"),
                "namespace": sig.get("namespace"),
                "entry_hash": e["entry_hash"],
            })
        else:
            raise ProjectionError("seq %d: unsupported event type %s (fail-closed)" % (e["seq"], et))

    nxt = table.get(state)
    unsigned = sum(1 for e in entries if e["signature"].get("status") == "UNSIGNED")
    signed = sum(1 for e in entries if e["signature"].get("alg") == "sshsig-ed25519")
    has_policies = root is not None and os.path.isfile(os.path.join(root, statemachine.TRANSITIONS_POLICY_PATH))

    view = {
        "view": "state_board",
        "view_version": VIEW_VERSION,
        "run_id": entries[0]["run_id"] if entries else None,
        "derived_from": {
            "journal": journal_path,
            "head_seq": entries[-1]["seq"] if entries else None,
            "head_hash": entries[-1]["entry_hash"] if entries else None,
            "authority_version": authority["version"],
            "authority_jcs_sha256": canonical.jcs_hash(authority),
        },
        "current_state": state,
        "next": {
            "allowed_next_states": nxt["allowed_next_states"],
            "required_evidence": nxt["required_evidence"],
            "guard_id": nxt["guard_id"],
        } if nxt else None,
        "history": history,
        "genesis": genesis,
        "evidence": evidence,
        "open_waivers": waivers,
        "signature_status": {
            "signed_entries": signed,
            "unsigned_entries": unsigned,
            "reason": "PRE_A7_GENESIS_ENTRIES_UNSIGNED" if (signed and unsigned) else ("KEYS_NOT_PROVISIONED_UNTIL_A7" if unsigned else None),
        } if signed else {
            "unsigned_entries": unsigned,
            "reason": "KEYS_NOT_PROVISIONED_UNTIL_A7" if unsigned else None,
        },
        "patchset_status": "COMPILED_V1.2.0_ACTIVE" if (signed or has_policies) else "ACCEPTED_NOT_COMPILED (guards compiled at A5)",
    }
    if issued_tokens:
        view["issued_tokens"] = issued_tokens
    if break_glass_events:
        view["break_glass_log"] = break_glass_events
    return view


def render(view):
    return canonical.sorted_pretty_bytes(view)


def project_file(root, journal_rel_path=DEFAULT_JOURNAL, out_rel_path=DEFAULT_VIEW):
    validator = journal.load_validator(root)
    journal_abs = os.path.join(root, journal_rel_path)
    entries, report = journal.verify_file(journal_abs, validator, root=root)
    if not report["valid"]:
        raise ProjectionError("cannot project invalid journal: " + "; ".join(report["errors"][:5]))
    if not entries:
        raise ProjectionError("cannot project empty journal")
    authority = canonical.strict_load_file(os.path.join(root, AUTHORITY_PATH))
    view = replay(entries, authority, journal_rel_path, root=root)
    out_bytes = render(view)
    if out_rel_path is not None:
        out_abs = os.path.join(root, out_rel_path)
        os.makedirs(os.path.dirname(out_abs), exist_ok=True)
        with open(out_abs, "wb") as fh:
            fh.write(out_bytes)
    return view, out_bytes
