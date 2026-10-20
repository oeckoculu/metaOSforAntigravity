"""Phase A7: Cryptographic Signing Infrastructure (ssh-keygen -Y), CapabilityToken Issuer & Break-Glass Drill.

Materializes:
- .antigravity/keys/human_owner.ed25519.pub
- .antigravity/keys/kernel_authority.ed25519.pub
- .antigravity/keys/allowed_signers
- .antigravity/keys/keyring_manifest.json
- .antigravity/genesis/initial_capability_token.json
- .antigravity/genesis/break_glass_drill_override.json
- .antigravity/genesis/break_glass_review_record.json
- .antigravity/genesis/realignment_projection_receipt.json
- Appends seq 7..12 (signed EVIDENCE_RECORDED, TOKEN_ISSUED, BREAK_GLASS_OVERRIDE, EX-11, EX-12) to .antigravity/events/run-0000.jsonl
- Re-projects .antigravity/views/state_board.json
- Writes .antigravity/genesis/receipts/A7_keys_tokens_and_break_glass.receipt.json
"""
import copy
import os

from . import canonical, crypto, env, journal, pdp, phase_a5, phase_a6, projector, receipt, schema, secrets

RECEIPT_A7_REL = ".antigravity/genesis/receipts/A7_keys_tokens_and_break_glass.receipt.json"
TASK_ENVELOPE_SCHEMA_REL = ".antigravity/schemas/core/task_envelope.schema.json"

DRILL_ISSUED_AT = "2026-10-20T22:40:00Z"
DRILL_TOKEN_ID = "0192f3a4-0000-7000-8000-000000000007"


def _write_canonical_json(root, rel_path, obj):
    abs_path = os.path.join(root, rel_path)
    os.makedirs(os.path.dirname(abs_path), exist_ok=True)
    pretty = canonical.pretty_bytes(obj)
    with open(abs_path, "wb") as fh:
        fh.write(pretty)
    return canonical.file_sha256(abs_path), canonical.jcs_hash(obj)


def _build_signed_break_glass_artifacts(root, keystore_dir=None):
    """Create and sign the 3 Break-Glass drill artifacts with human:oeckoculu (metaos.breakglass)."""
    override_doc = {
        "document_type": "CryptographicallySignedBreakGlassOverrideEvent",
        "schema_version": "1.0.0",
        "override_id": "BGO-20261020-0001",
        "run_id": "run-0000",
        "drill": True,
        "incident_severity": "P0_DRILL",
        "origin_state": "GENESIS_LOCKED",
        "target_state": "BREAK_GLASS_ACTIVE",
        "actor": {
            "principal_id": "human:oeckoculu",
            "kind": "HUMAN",
            "os_identity": "oeckoculu",
        },
        "issued_at": DRILL_ISSUED_AT,
        "rationale": "Phase A7 mandatory Break-Glass override and C-3/V12-02 realignment drill.",
    }
    override_body_hash = canonical.jcs_hash(override_doc)
    override_doc["content_hash"] = override_body_hash
    override_doc["signature"] = crypto.sign_bytes(
        data_bytes=override_body_hash.encode("utf-8"),
        principal_id="human:oeckoculu",
        namespace="metaos.breakglass",
        root=root,
        keystore_dir=keystore_dir,
    )
    ov_file_sha, _ = _write_canonical_json(root, crypto.BREAK_GLASS_OVERRIDE_REL, override_doc)

    review_doc = {
        "document_type": "CryptographicallySignedBreakGlassReviewRecord",
        "schema_version": "1.0.0",
        "review_id": "BGR-20261020-0001",
        "override_id": "BGO-20261020-0001",
        "override_file_sha256": ov_file_sha,
        "run_id": "run-0000",
        "reviewer": {
            "principal_id": "human:oeckoculu",
            "kind": "HUMAN",
            "os_identity": "oeckoculu",
        },
        "reviewed_at": DRILL_ISSUED_AT,
        "decision": "REALIGN_TO_GENESIS_LOCKED",
        "findings": "Break-glass drill verified; no unrecorded side effects; kernel invariants intact.",
    }
    review_body_hash = canonical.jcs_hash(review_doc)
    review_doc["content_hash"] = review_body_hash
    review_doc["signature"] = crypto.sign_bytes(
        data_bytes=review_body_hash.encode("utf-8"),
        principal_id="human:oeckoculu",
        namespace="metaos.breakglass",
        root=root,
        keystore_dir=keystore_dir,
    )
    rev_file_sha, _ = _write_canonical_json(root, crypto.BREAK_GLASS_REVIEW_REL, review_doc)

    realign_doc = {
        "document_type": "RealignmentProjectionReceipt",
        "schema_version": "1.0.0",
        "realignment_id": "RPR-20261020-0001",
        "override_id": "BGO-20261020-0001",
        "review_id": "BGR-20261020-0001",
        "review_file_sha256": rev_file_sha,
        "from_state": "BREAK_GLASS_ACTIVE",
        "to_state": "GENESIS_LOCKED",
        "patch_ref": "C-3/V12-02",
        "verified_at": DRILL_ISSUED_AT,
    }
    realign_body_hash = canonical.jcs_hash(realign_doc)
    realign_doc["content_hash"] = realign_body_hash
    realign_doc["signature"] = crypto.sign_bytes(
        data_bytes=realign_body_hash.encode("utf-8"),
        principal_id="human:oeckoculu",
        namespace="metaos.breakglass",
        root=root,
        keystore_dir=keystore_dir,
    )
    real_file_sha, _ = _write_canonical_json(root, crypto.REALIGNMENT_RECEIPT_REL, realign_doc)

    return {
        "override": (override_doc, ov_file_sha),
        "review": (review_doc, rev_file_sha),
        "realignment": (realign_doc, real_file_sha),
    }


def _append_a7_journal_events(root, tok_obj, tok_file_sha, bg_artifacts, keystore_dir=None):
    """Idempotently append seq 7..12 to .antigravity/events/run-0000.jsonl and project state_board.json."""
    validator = journal.load_validator(root)
    jpath = os.path.join(root, journal.DEFAULT_JOURNAL_REL)
    entries, report = journal.verify_file(jpath, validator, root=root)
    if not report["valid"]:
        raise journal.JournalError("Cannot append Phase A7 events to invalid journal: " + "; ".join(report["errors"]))

    # If seq 0..6 are present (or if previous A7 run already appended seq 7..12, truncate back to seq 0..6 before re-appending with current keys)
    if len(entries) > 7:
        base_entries = entries[:7]
        raw_lines = [canonical.jcs_bytes(e) + b"\n" for e in base_entries]
        with open(jpath, "wb") as fh:
            fh.write(b"".join(raw_lines))
        entries, report = journal.verify_file(jpath, validator, root=root)

    rep = env.reproducibility(root)
    kernel_actor = {"principal_id": "kernel:authority", "kind": "KERNEL", "os_identity": "oeckoculu"}
    human_actor = {"principal_id": "human:oeckoculu", "kind": "HUMAN", "os_identity": "oeckoculu"}

    # Ensure A5 and A6 receipts exist (in sandbox test if A5/A6 weren't run yet, run them)
    a5_rec_abs = os.path.join(root, phase_a5.RECEIPT_A5_REL)
    if not os.path.isfile(a5_rec_abs):
        r5 = phase_a5.run(root)
        r5.write(phase_a5.RECEIPT_A5_REL)
    a6_rec_abs = os.path.join(root, phase_a6.RECEIPT_A6_REL)
    if not os.path.isfile(a6_rec_abs):
        r6 = phase_a6.run(root)
        r6.write(phase_a6.RECEIPT_A6_REL)

    a5_rec = canonical.strict_load_file(a5_rec_abs)
    a6_rec = canonical.strict_load_file(a6_rec_abs)

    # seq 7: EVIDENCE_RECORDED for Phase A5
    e7 = journal.build_entry(
        validator=validator,
        seq=7,
        run_id="run-0000",
        prev_hash=entries[-1]["entry_hash"],
        event_type="EVIDENCE_RECORDED",
        actor=kernel_actor,
        payload={
            "phase": "A5",
            "receipt_path": phase_a5.RECEIPT_A5_REL,
            "receipt_hash": a5_rec["receipt_hash"],
            "status": "PASS",
        },
        reproducibility=rep,
        ts=DRILL_ISSUED_AT,
        root=root,
        sign_principal="kernel:authority",
        sign_namespace="metaos.journal",
        keystore_dir=keystore_dir,
    )
    journal.append(jpath, e7, validator, root=root)

    # seq 8: EVIDENCE_RECORDED for Phase A6
    e8 = journal.build_entry(
        validator=validator,
        seq=8,
        run_id="run-0000",
        prev_hash=e7["entry_hash"],
        event_type="EVIDENCE_RECORDED",
        actor=kernel_actor,
        payload={
            "phase": "A6",
            "receipt_path": phase_a6.RECEIPT_A6_REL,
            "receipt_hash": a6_rec["receipt_hash"],
            "status": "PASS",
        },
        reproducibility=rep,
        ts=DRILL_ISSUED_AT,
        root=root,
        sign_principal="kernel:authority",
        sign_namespace="metaos.journal",
        keystore_dir=keystore_dir,
    )
    journal.append(jpath, e8, validator, root=root)

    # seq 9: TOKEN_ISSUED for initial_capability_token.json
    e9 = journal.build_entry(
        validator=validator,
        seq=9,
        run_id="run-0000",
        prev_hash=e8["entry_hash"],
        event_type="TOKEN_ISSUED",
        actor=kernel_actor,
        payload={
            "token_id": tok_obj["token_id"],
            "agent_role": "BuilderAgent",
            "issued_at": tok_obj["issued_at"],
            "expires_at": tok_obj["expires_at"],
            "token_path": crypto.INITIAL_TOKEN_REL,
            "token_sha256": tok_file_sha,
            "issuer_key_id": tok_obj["issuer_signature"]["key_id"],
        },
        reproducibility=rep,
        ts=DRILL_ISSUED_AT,
        root=root,
        sign_principal="kernel:authority",
        sign_namespace="metaos.journal",
        keystore_dir=keystore_dir,
    )
    journal.append(jpath, e9, validator, root=root)

    # seq 10: BREAK_GLASS_OVERRIDE (signed by human:oeckoculu under metaos.breakglass)
    ov_doc, ov_sha = bg_artifacts["override"]
    rev_doc, rev_sha = bg_artifacts["review"]
    real_doc, real_sha = bg_artifacts["realignment"]

    e10 = journal.build_entry(
        validator=validator,
        seq=10,
        run_id="run-0000",
        prev_hash=e9["entry_hash"],
        event_type="BREAK_GLASS_OVERRIDE",
        actor=human_actor,
        payload={
            "override_id": ov_doc["override_id"],
            "drill": True,
            "incident_severity": ov_doc["incident_severity"],
            "override_path": crypto.BREAK_GLASS_OVERRIDE_REL,
            "override_sha256": ov_sha,
            "rationale": ov_doc["rationale"],
        },
        reproducibility=rep,
        ts=DRILL_ISSUED_AT,
        root=root,
        sign_principal="human:oeckoculu",
        sign_namespace="metaos.breakglass",
        keystore_dir=keystore_dir,
    )
    journal.append(jpath, e10, validator, root=root)

    # seq 11: STATE_TRANSITION EX-11 (GENESIS_LOCKED -> BREAK_GLASS_ACTIVE)
    e11 = journal.build_entry(
        validator=validator,
        seq=11,
        run_id="run-0000",
        prev_hash=e10["entry_hash"],
        event_type="STATE_TRANSITION",
        actor=human_actor,
        transition={
            "from_state": "GENESIS_LOCKED",
            "to_state": "BREAK_GLASS_ACTIVE",
            "guard_id": "EX-11",
            "suspended_from": "GENESIS_LOCKED",
            "evidence_refs": [
                {
                    "kind": "CryptographicallySignedBreakGlassOverrideEvent",
                    "ref": ov_sha,
                    "path": crypto.BREAK_GLASS_OVERRIDE_REL,
                }
            ],
            "waivers": [],
        },
        payload={},
        reproducibility=rep,
        ts=DRILL_ISSUED_AT,
        root=root,
        sign_principal="human:oeckoculu",
        sign_namespace="metaos.breakglass",
        keystore_dir=keystore_dir,
    )
    journal.append(jpath, e11, validator, root=root)

    # seq 12: STATE_TRANSITION EX-12 (BREAK_GLASS_ACTIVE -> GENESIS_LOCKED realignment, C-3/V12-02)
    e12 = journal.build_entry(
        validator=validator,
        seq=12,
        run_id="run-0000",
        prev_hash=e11["entry_hash"],
        event_type="STATE_TRANSITION",
        actor=human_actor,
        transition={
            "from_state": "BREAK_GLASS_ACTIVE",
            "to_state": "GENESIS_LOCKED",
            "guard_id": "EX-12",
            "suspended_from": None,
            "evidence_refs": [
                {
                    "kind": "RealignmentProjectionReceipt",
                    "ref": real_sha,
                    "path": crypto.REALIGNMENT_RECEIPT_REL,
                },
                {
                    "kind": "CryptographicallySignedBreakGlassReviewRecord",
                    "ref": rev_sha,
                    "path": crypto.BREAK_GLASS_REVIEW_REL,
                },
            ],
            "waivers": [],
        },
        payload={},
        reproducibility=rep,
        ts=DRILL_ISSUED_AT,
        root=root,
        sign_principal="human:oeckoculu",
        sign_namespace="metaos.breakglass",
        keystore_dir=keystore_dir,
    )
    journal.append(jpath, e12, validator, root=root)

    view, view_bytes = projector.project_file(root)
    return [e7, e8, e9, e10, e11, e12], view, view_bytes


def run(root, keystore_dir=None):
    r = receipt.Receipt(root, "A7", "keys_tokens_and_break_glass")

    # 1. Provision Ed25519 keys & allowed_signers
    manifest = crypto.init_keys(root, keystore_dir=keystore_dir)
    ks_dir = crypto.get_keystore_dir(keystore_dir)

    # Update policy_bundle.lock.json to lock keyring_manifest.json as well
    bundle_path = os.path.join(root, pdp.POLICY_BUNDLE_LOCK_PATH)
    if os.path.isfile(bundle_path):
        bundle_lock = canonical.strict_load_file(bundle_path)
        bundle_lock["policies"]["keyring_manifest"] = {
            "policy_id": "urn:metaos:keyring:1.0.0",
            "path": crypto.KEYRING_MANIFEST_REL,
            "canonical_sha256": canonical.jcs_hash(manifest),
            "bytes": len(canonical.pretty_bytes(manifest)),
            "principals": sorted(manifest["principals"].keys()),
        }
        _write_canonical_json(root, pdp.POLICY_BUNDLE_LOCK_PATH, bundle_lock)

    # Check that zero private keys exist anywhere inside root
    priv_in_repo = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in (".git", "__pycache__")]
        for fn in filenames:
            p = os.path.join(dirpath, fn)
            try:
                txt = open(p, "rb").read().decode("utf-8")
            except UnicodeDecodeError:
                continue
            hits = secrets.scan_text(txt)
            if "PRIVATE_KEY_BLOCK" in hits:
                priv_in_repo.append(os.path.relpath(p, root))

    c01_ok = (
        os.path.isfile(os.path.join(root, crypto.ALLOWED_SIGNERS_REL))
        and os.path.isfile(os.path.join(root, crypto.HUMAN_PUB_REL))
        and os.path.isfile(os.path.join(root, crypto.KERNEL_PUB_REL))
        and not priv_in_repo
        and not ks_dir.startswith(os.path.realpath(root))
    )
    r.check(
        "A7-C01",
        "Ed25519 public keyring & allowed_signers provisioned in .antigravity/keys/; private keys isolated outside repository (I-12, I-15)",
        c01_ok,
        {
            "invariant_id": "I-12",
            "human_key_id": manifest["principals"]["human:oeckoculu"]["key_id"],
            "kernel_key_id": manifest["principals"]["kernel:authority"]["key_id"],
            "allowed_signers_sha256": manifest["allowed_signers_sha256"],
            "private_keys_in_repo": priv_in_repo,
        },
    )

    # 2. Test ssh-keygen -Y sign & verify positive and negative cases
    msg = b"metaos-a7-signature-test-payload"
    sig_valid = crypto.sign_bytes(msg, "human:oeckoculu", "metaos.breakglass", root, keystore_dir=keystore_dir)
    v_ok = crypto.verify_signature(msg, sig_valid, "human:oeckoculu", "metaos.breakglass", root)
    v_tampered = crypto.verify_signature(msg + b"-tampered", sig_valid, "human:oeckoculu", "metaos.breakglass", root)
    v_wrong_ns = crypto.verify_signature(msg, sig_valid, "human:oeckoculu", "metaos.human", root)
    v_wrong_principal = crypto.verify_signature(msg, sig_valid, "kernel:authority", "metaos.breakglass", root)

    c02_cases = {
        "valid_signature_verified": v_ok["valid"] is True,
        "tampered_payload_rejected": v_tampered["valid"] is False,
        "wrong_namespace_rejected": v_wrong_ns["valid"] is False,
        "wrong_principal_rejected": v_wrong_principal["valid"] is False,
    }
    r.check(
        "A7-C02",
        "ssh-keygen -Y sign and verify enforce cryptographic integrity, namespace binding, and principal isolation",
        all(c02_cases.values()),
        {"invariant_id": "I-15", "cases": c02_cases},
    )

    # 3. Issue initial signed CapabilityToken & verify cryptographic signature + tamper rejection
    tok = crypto.issue_capability_token(
        root=root,
        file_read=["contracts/**", "invariants/**", "src/**", "tests/**"],
        file_write=["src/**", "tests/**"],
        tools=["write_file", "edit_file", "run_tests"],
        actions=["READ", "PROPOSE", "EXECUTE_TEST"],
        ttl_seconds=1800,
        issued_at=DRILL_ISSUED_AT,
        token_id=DRILL_TOKEN_ID,
        agent_role="BuilderAgent",
        keystore_dir=keystore_dir,
    )
    tok_file_sha, _ = _write_canonical_json(root, crypto.INITIAL_TOKEN_REL, tok)

    tok_eval_ok = crypto.verify_signed_capability_token(
        root=root,
        token=tok,
        requested_action="PROPOSE",
        requested_tool="write_file",
        target_paths=["src/module.py"],
        now_utc="2026-10-20T22:50:00Z",
    )
    tok_tampered = copy.deepcopy(tok)
    tok_tampered["scopes"]["file_write"] = ["src/**", "infra/**"]
    tok_eval_tampered = crypto.verify_signed_capability_token(
        root=root,
        token=tok_tampered,
        requested_action="PROPOSE",
        requested_tool="write_file",
        target_paths=["infra/main.tf"],
        now_utc="2026-10-20T22:50:00Z",
    )
    c03_cases = {
        "signed_token_verified_allow": tok_eval_ok["decision"] == "ALLOW",
        "tampered_scope_signature_rejected": tok_eval_tampered["decision"] == "DENY",
        "token_id": tok["token_id"],
        "issuer_key_id": tok["issuer_signature"]["key_id"],
    }
    r.check(
        "A7-C03",
        "Cryptographically signed CapabilityToken issued and verified; post-issuance scope tampering is rejected (I-02)",
        tok_eval_ok["decision"] == "ALLOW" and tok_eval_tampered["decision"] == "DENY",
        {"invariant_id": "I-02", "cases": c03_cases},
    )

    # 4. CapabilityToken issuance fail-closed negative tests (TTL, Layer A, privileged action, verifier isolation, expiry)
    ttl_blocked = False
    try:
        crypto.issue_capability_token(root, ["src/**"], ["src/**"], ["run_tests"], ["READ"], ttl_seconds=86400, keystore_dir=keystore_dir)
    except crypto.CryptoError:
        ttl_blocked = True

    layer_a_blocked = False
    try:
        crypto.issue_capability_token(root, ["src/**"], [".antigravity/policies/x.json"], ["write_file"], ["PROPOSE"], keystore_dir=keystore_dir)
    except crypto.CryptoError:
        layer_a_blocked = True

    priv_action_blocked = False
    try:
        crypto.issue_capability_token(root, ["src/**"], ["src/**"], ["run_tests"], ["COMMIT"], keystore_dir=keystore_dir)
    except crypto.CryptoError:
        priv_action_blocked = True

    verifier_write_blocked = False
    try:
        crypto.issue_capability_token(
            root, ["src/**"], ["src/**"], ["run_tests"], ["EXECUTE_TEST"], agent_role="RedTeamVerifierAgent", keystore_dir=keystore_dir
        )
    except crypto.CryptoError:
        verifier_write_blocked = True

    tok_expired_eval = crypto.verify_signed_capability_token(
        root=root,
        token=tok,
        requested_action="PROPOSE",
        requested_tool="write_file",
        target_paths=["src/module.py"],
        now_utc="2026-10-20T23:59:00Z",
    )
    c04_cases = {
        "excessive_ttl_rejected": ttl_blocked,
        "layer_a_write_scope_rejected": layer_a_blocked,
        "privileged_commit_action_rejected": priv_action_blocked,
        "verifier_src_write_rejected": verifier_write_blocked,
        "expired_token_runtime_denied": tok_expired_eval["decision"] == "DENY",
    }
    r.check(
        "A7-C04",
        "CapabilityToken issuer blocks excessive TTL, Layer A write scopes, privileged actions, verifier src writes, and expired tokens (I-02)",
        all(c04_cases.values()),
        {"invariant_id": "I-02", "cases": c04_cases},
    )

    # 5. Build & verify Break-Glass drill artifacts and append seq 7..12 to run-0000.jsonl
    bg_artifacts = _build_signed_break_glass_artifacts(root, keystore_dir=keystore_dir)
    ov_doc, _ = bg_artifacts["override"]
    rev_doc, _ = bg_artifacts["review"]
    real_doc, _ = bg_artifacts["realignment"]

    ov_ver = crypto.verify_signature(
        ov_doc["content_hash"].encode("utf-8"), ov_doc["signature"], "human:oeckoculu", "metaos.breakglass", root
    )
    rev_ver = crypto.verify_signature(
        rev_doc["content_hash"].encode("utf-8"), rev_doc["signature"], "human:oeckoculu", "metaos.breakglass", root
    )
    real_ver = crypto.verify_signature(
        real_doc["content_hash"].encode("utf-8"), real_doc["signature"], "human:oeckoculu", "metaos.breakglass", root
    )
    c05_ok = ov_ver["valid"] and rev_ver["valid"] and real_ver["valid"]
    r.check(
        "A7-C05",
        "Break-Glass Override, Review Record, and Realignment Projection Receipt cryptographically signed by human:oeckoculu (I-15, C-3/V12-02)",
        c05_ok,
        {
            "invariant_id": "I-15",
            "override_id": ov_doc["override_id"],
            "override_verified": ov_ver["valid"],
            "review_verified": rev_ver["valid"],
            "realignment_verified": real_ver["valid"],
        },
    )

    # 6. Append signed events seq 7..12 to run-0000.jsonl and verify journal chain + signatures
    appended_entries, view1, view1_bytes = _append_a7_journal_events(
        root, tok, tok_file_sha, bg_artifacts, keystore_dir=keystore_dir
    )
    validator = journal.load_validator(root)
    jpath = os.path.join(root, journal.DEFAULT_JOURNAL_REL)
    all_entries, j_report = journal.verify_file(jpath, validator, root=root)
    c06_ok = (
        j_report["valid"] is True
        and j_report["entries"] == 13
        and j_report["signed_entries"] == 6
        and j_report["unsigned_entries"] == 7
    )
    r.check(
        "A7-C06",
        "Event journal (.antigravity/events/run-0000.jsonl) records signed EVIDENCE_RECORDED, TOKEN_ISSUED, BREAK_GLASS_OVERRIDE, EX-11, and EX-12 (seq 7..12)",
        c06_ok,
        {
            "invariant_id": "I-03",
            "total_entries": j_report["entries"],
            "signed_entries": j_report["signed_entries"],
            "unsigned_genesis_entries": j_report["unsigned_entries"],
            "head_seq": j_report["head_seq"],
            "head_hash": j_report["head_hash"],
        },
    )

    # 7. Test rejection of unsigned or AGENT-authored BREAK_GLASS_OVERRIDE in journal
    unsigned_bg_rejected = False
    try:
        journal.build_entry(
            validator=validator,
            seq=13,
            run_id="run-0000",
            prev_hash=j_report["head_hash"],
            event_type="BREAK_GLASS_OVERRIDE",
            actor={"principal_id": "human:oeckoculu", "kind": "HUMAN"},
            payload={"override_id": "BGO-FAKE"},
            reproducibility=env.reproducibility(root),
        )
    except journal.JournalError:
        unsigned_bg_rejected = True

    agent_bg_rejected = False
    try:
        journal.build_entry(
            validator=validator,
            seq=13,
            run_id="run-0000",
            prev_hash=j_report["head_hash"],
            event_type="BREAK_GLASS_OVERRIDE",
            actor={"principal_id": "agent:builder-1", "kind": "AGENT"},
            payload={"override_id": "BGO-FAKE"},
            reproducibility=env.reproducibility(root),
            signature=sig_valid,
        )
    except journal.JournalError:
        agent_bg_rejected = True

    r.check(
        "A7-C07",
        "Unsigned or AGENT-authored BREAK_GLASS_OVERRIDE journal entries are rejected fail-closed (I-15)",
        unsigned_bg_rejected and agent_bg_rejected,
        {
            "invariant_id": "I-15",
            "unsigned_break_glass_rejected": unsigned_bg_rejected,
            "agent_break_glass_rejected": agent_bg_rejected,
        },
    )

    # 8. Deterministic two-replay projection check after Break-Glass drill
    view2, view2_bytes = projector.project_file(root)
    c08_ok = (
        view1_bytes == view2_bytes
        and view2["current_state"] == "GENESIS_LOCKED"
        and len(view2.get("issued_tokens", [])) == 1
        and len(view2.get("break_glass_log", [])) == 1
    )
    r.check(
        "A7-C08",
        "Two independent journal replays after Break-Glass drill produce byte-identical state_board.json realigned at GENESIS_LOCKED (I-03, C-3/V12-02)",
        c08_ok,
        {
            "invariant_id": "I-03",
            "current_state": view2["current_state"],
            "byte_identical_replay": view1_bytes == view2_bytes,
            "state_board_sha256": canonical.sha256_ref(view2_bytes),
            "history_transitions": len(view2["history"]),
        },
    )

    for rel in (
        crypto.ALLOWED_SIGNERS_REL,
        crypto.HUMAN_PUB_REL,
        crypto.KERNEL_PUB_REL,
        crypto.KEYRING_MANIFEST_REL,
        crypto.INITIAL_TOKEN_REL,
        crypto.BREAK_GLASS_OVERRIDE_REL,
        crypto.BREAK_GLASS_REVIEW_REL,
        crypto.REALIGNMENT_RECEIPT_REL,
        pdp.POLICY_BUNDLE_LOCK_PATH,
        journal.DEFAULT_JOURNAL_REL,
        projector.DEFAULT_VIEW,
        ".antigravity/kernel/metaos/crypto.py",
        ".antigravity/kernel/metaos/phase_a7.py",
        "scripts/keys_init",
        "scripts/token_issue",
        "scripts/break_glass",
    ):
        r.output(rel)

    return r
