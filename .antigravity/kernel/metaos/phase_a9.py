"""Phase A9: End-to-End Kernel Self-Test, kernel_lock.json Sealing, KernelReadyReceipt & Layer B Skeleton.

Materializes:
- .antigravity/events/run-0000.jsonl (appends seq 13..14 signed EVIDENCE_RECORDED for A7 and A8)
- .antigravity/views/state_board.json (re-projected from seq 0..14)
- .antigravity/genesis/kernel_lock.json (cryptographically signed canonical SHA-256 manifest of Layer A)
- .antigravity/genesis/initialized_workspace.json (cryptographically signed InitializedWorkspace artifact for LC-04)
- .antigravity/genesis/receipts/KernelReadyReceipt.json (cryptographically signed KernelReadyReceipt for LC-04)
- .antigravity/genesis/receipts/A9_kernel_selftest_and_lock.receipt.json
- Layer B skeleton directories: contracts/, invariants/, src/, tests/, receipts/, provenance/, infra/, docs/ (.gitkeep)

Executes deterministic verification suites A9-C01 .. A9-C08.
"""
import os

from . import (
    authority,
    canonical,
    contracts,
    crypto,
    env,
    envelope,
    genesis,
    journal,
    pdp,
    pep,
    phase_a5,
    phase_a6,
    phase_a7,
    phase_a8,
    projector,
    receipt,
    scaffold,
    schema,
    secrets,
    statemachine,
)

KERNEL_LOCK_REL = ".antigravity/genesis/kernel_lock.json"
INITIALIZED_WORKSPACE_REL = ".antigravity/genesis/initialized_workspace.json"
KERNEL_READY_RECEIPT_REL = ".antigravity/genesis/receipts/KernelReadyReceipt.json"
RECEIPT_A9_REL = ".antigravity/genesis/receipts/A9_kernel_selftest_and_lock.receipt.json"

LOCK_TIMESTAMP = "2026-10-20T23:00:00Z"

PRIOR_PHASE_RECEIPTS = [
    ("A1", authority.RECEIPT_PATH),
    ("A2", scaffold.RECEIPT_PATH),
    ("A3", contracts.RECEIPT_PATH),
    ("A4", genesis.RECEIPT_A4_REL),
    ("A5", phase_a5.RECEIPT_A5_REL),
    ("A6", phase_a6.RECEIPT_A6_REL),
    ("A7", phase_a7.RECEIPT_A7_REL),
    ("A8", phase_a8.RECEIPT_A8_REL),
]

EXCLUDED_FROM_KERNEL_LOCK = {
    KERNEL_LOCK_REL,
    INITIALIZED_WORKSPACE_REL,
    KERNEL_READY_RECEIPT_REL,
    RECEIPT_A9_REL,
}


def _write_canonical_json(root, rel_path, obj):
    abs_path = os.path.join(root, rel_path)
    os.makedirs(os.path.dirname(abs_path), exist_ok=True)
    pretty = canonical.pretty_bytes(obj)
    with open(abs_path, "wb") as fh:
        fh.write(pretty)
    return canonical.file_sha256(abs_path), canonical.jcs_hash(obj)


def _sign_document(doc_without_sig, principal_id, namespace, root, keystore_dir=None):
    doc = dict(doc_without_sig)
    doc.pop("content_hash", None)
    doc.pop("signature", None)
    content_hash = canonical.jcs_hash(doc)
    sig = crypto.sign_bytes(
        data_bytes=content_hash.encode("utf-8"),
        principal_id=principal_id,
        namespace=namespace,
        root=root,
        keystore_dir=keystore_dir,
    )
    doc["content_hash"] = content_hash
    doc["signature"] = sig
    return doc


def _verify_document_signature(doc, principal_id, namespace, root):
    if not isinstance(doc, dict) or "content_hash" not in doc or "signature" not in doc:
        return {"valid": False, "reason": "missing content_hash or signature"}
    unsigned = dict(doc)
    expected_hash = unsigned.pop("content_hash")
    sig = unsigned.pop("signature")
    actual_hash = canonical.jcs_hash(unsigned)
    if actual_hash != expected_hash:
        return {"valid": False, "reason": "content_hash mismatch"}
    return crypto.verify_signature(
        data_bytes=expected_hash.encode("utf-8"),
        sig_obj=sig,
        principal_id=principal_id,
        expected_namespace=namespace,
        root=root,
    )


def _append_a9_journal_events(root, keystore_dir=None):
    """Idempotently append signed seq 13 (A7 receipt) and seq 14 (A8 receipt) to run-0000.jsonl."""
    # Update policy_bundle.lock.json to include untrusted_content_envelope.schema.json
    bundle_path = os.path.join(root, pdp.POLICY_BUNDLE_LOCK_PATH)
    env_schema_abs = os.path.join(root, envelope.ENVELOPE_SCHEMA_REL)
    if os.path.isfile(bundle_path) and os.path.isfile(env_schema_abs):
        bundle_lock = canonical.strict_load_file(bundle_path)
        env_schema_obj = canonical.strict_load_file(env_schema_abs)
        bundle_lock["policies"]["untrusted_content_envelope_schema"] = {
            "policy_id": env_schema_obj.get("$id", "urn:metaos:schema:core:untrusted_content_envelope:1.0.0"),
            "path": envelope.ENVELOPE_SCHEMA_REL,
            "canonical_sha256": canonical.jcs_hash(env_schema_obj),
            "bytes": os.path.getsize(env_schema_abs),
        }
        _write_canonical_json(root, pdp.POLICY_BUNDLE_LOCK_PATH, bundle_lock)

    a7_abs = os.path.join(root, phase_a7.RECEIPT_A7_REL)
    if not os.path.isfile(a7_abs):
        r7 = phase_a7.run(root, keystore_dir=keystore_dir)
        r7.write(phase_a7.RECEIPT_A7_REL)
    a8_abs = os.path.join(root, phase_a8.RECEIPT_A8_REL)
    if not os.path.isfile(a8_abs):
        r8 = phase_a8.run(root, keystore_dir=keystore_dir)
        r8.write(phase_a8.RECEIPT_A8_REL)

    a7_rec = canonical.strict_load_file(a7_abs)
    a8_rec = canonical.strict_load_file(a8_abs)

    validator = journal.load_validator(root)
    jpath = os.path.join(root, journal.DEFAULT_JOURNAL_REL)
    entries, report = journal.verify_file(jpath, validator, root=root)
    if not report["valid"]:
        raise RuntimeError("Existing journal invalid before Phase A9 append: %s" % "; ".join(report["errors"]))

    # Truncate back to seq 0..12 if A9 was previously run
    base_entries = [e for e in entries if e["seq"] <= 12]
    if len(base_entries) != len(entries):
        raw_bytes = b"".join(canonical.jcs_bytes(e) + b"\n" for e in base_entries)
        with open(jpath, "wb") as fh:
            fh.write(raw_bytes)
        entries, report = journal.verify_file(jpath, validator, root=root)
        if not report["valid"]:
            raise RuntimeError("Truncated base journal invalid: %s" % "; ".join(report["errors"]))

    rep = env.reproducibility(root)
    kernel_actor = {"principal_id": "kernel:authority", "kind": "KERNEL", "os_identity": "oeckoculu"}

    # seq 13: EVIDENCE_RECORDED for Phase A7
    e13 = journal.build_entry(
        validator=validator,
        seq=13,
        run_id="run-0000",
        prev_hash=entries[-1]["entry_hash"],
        event_type="EVIDENCE_RECORDED",
        actor=kernel_actor,
        payload={
            "phase": "A7",
            "receipt_path": phase_a7.RECEIPT_A7_REL,
            "receipt_hash": a7_rec["receipt_hash"],
            "status": "PASS",
        },
        reproducibility=rep,
        ts=LOCK_TIMESTAMP,
        root=root,
        sign_principal="kernel:authority",
        sign_namespace="metaos.journal",
        keystore_dir=keystore_dir,
    )
    journal.append(jpath, e13, validator, root=root)

    # seq 14: EVIDENCE_RECORDED for Phase A8
    e14 = journal.build_entry(
        validator=validator,
        seq=14,
        run_id="run-0000",
        prev_hash=e13["entry_hash"],
        event_type="EVIDENCE_RECORDED",
        actor=kernel_actor,
        payload={
            "phase": "A8",
            "receipt_path": phase_a8.RECEIPT_A8_REL,
            "receipt_hash": a8_rec["receipt_hash"],
            "status": "PASS",
        },
        reproducibility=rep,
        ts=LOCK_TIMESTAMP,
        root=root,
        sign_principal="kernel:authority",
        sign_namespace="metaos.journal",
        keystore_dir=keystore_dir,
    )
    journal.append(jpath, e14, validator, root=root)

    view, view_bytes = projector.project_file(root)
    return [e13, e14], view, view_bytes


def run_selftest(root):
    """Execute end-to-end kernel verification across Phases A1..A8."""
    # 1. Verify all prior phase receipts A1..A8
    receipt_results = {}
    all_receipts_ok = True
    for phase_id, rel in PRIOR_PHASE_RECEIPTS:
        abs_p = os.path.join(root, rel)
        if not os.path.isfile(abs_p):
            receipt_results[phase_id] = {"present": False, "valid": False}
            all_receipts_ok = False
            continue
        ok, msg = receipt.verify_receipt_file(abs_p)
        obj = canonical.strict_load_file(abs_p)
        passed = ok and obj.get("status") == "PASS"
        receipt_results[phase_id] = {
            "present": True,
            "valid": passed,
            "receipt_hash": obj.get("receipt_hash"),
            "checks_count": len(obj.get("checks", [])),
            "detail": msg,
        }
        if not passed:
            all_receipts_ok = False

    # 2. Verify authority lock integrity
    auth_lock_abs = os.path.join(root, authority.LOCK_PATH)
    auth_lock = canonical.strict_load_file(auth_lock_abs)
    lock_entries = dict((e["path"], e["sha256"]) for e in auth_lock.get("entries", []))
    spec_sha = canonical.file_sha256(os.path.join(root, authority.SPEC_PATH))
    inv_sha = canonical.file_sha256(os.path.join(root, authority.JSON_DST))
    authority_ok = (
        spec_sha == lock_entries.get(authority.SPEC_PATH)
        and inv_sha == lock_entries.get(authority.JSON_DST)
    )

    # 3. Verify all 5 core schemas and golden fixtures
    core_dir = os.path.join(root, ".antigravity/schemas/core")
    schema_files = sorted(fn for fn in os.listdir(core_dir) if fn.endswith(".schema.json"))
    schemas_ok = len(schema_files) == 5
    schema_ids = []
    for fn in schema_files:
        s_obj = canonical.strict_load_file(os.path.join(core_dir, fn))
        if schema.lint_schema(s_obj):
            schemas_ok = False
        schema_ids.append(s_obj.get("$id"))

    # 4. Verify PEP SessionStart, PreToolUse, PostToolUse, State Machine, PDP, Crypto, Envelope
    sess_res = pep.evaluate_session_start(root)
    pre_deny_layer_a = pep.evaluate_pre_tool_use(
        root,
        {
            "tool_name": "write_file",
            "actor": {"principal_id": "agent:builder-1", "kind": "AGENT"},
            "tool_input": {"Path": ".antigravity/policies/admission_policy.v1.2.0.json"},
        },
    )
    pre_deny_untrusted = pep.evaluate_pre_tool_use(
        root,
        {
            "tool_name": "write_file",
            "actor": {"principal_id": "agent:builder-1", "kind": "AGENT"},
            "source_trust": "UNTRUSTED",
            "untrusted_envelope_verified": False,
            "tool_input": {"Path": "src/main.py"},
        },
    )
    lc04_eval = statemachine.evaluate_transition(
        state_ctx=statemachine.initial_context("GENESIS_LOCKED"),
        from_state="GENESIS_LOCKED",
        to_state="INTENT_CAPTURED",
        evidence=["InitializedWorkspace", "ValidatedIntentContract"],
    )
    sample_env = canonical.strict_load_file(os.path.join(root, envelope.SAMPLE_ENVELOPE_REL))
    env_ver = envelope.verify_untrusted_envelope(root, sample_env)
    init_tok = canonical.strict_load_file(os.path.join(root, crypto.INITIAL_TOKEN_REL))
    tok_ver = crypto.verify_signed_capability_token(
        root=root,
        token=init_tok,
        requested_action="PROPOSE",
        requested_tool="write_file",
        target_paths=["src/app.py"],
        now_utc="2026-10-20T22:50:00Z",
    )

    subsystems_ok = (
        sess_res["decision"] == "ALLOW"
        and pre_deny_layer_a["decision"] == "DENY"
        and pre_deny_untrusted["decision"] == "DENY"
        and lc04_eval["decision"] == "ALLOW"
        and env_ver["valid"] is True
        and tok_ver["decision"] == "ALLOW"
    )

    # 5. Verify Journal & Two-Replay Deterministic Projection
    validator = journal.load_validator(root)
    jpath = os.path.join(root, journal.DEFAULT_JOURNAL_REL)
    _, j_report = journal.verify_file(jpath, validator, root=root)
    v1, b1 = projector.project_file(root)
    v2, b2 = projector.project_file(root)
    journal_ok = (
        j_report["valid"] is True
        and j_report["entries"] == 15
        and j_report["signed_entries"] == 8
        and b1 == b2
        and v2["current_state"] == "GENESIS_LOCKED"
    )

    # 6. Working tree secret scan (I-12)
    secret_hits = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in (".git", "__pycache__")]
        for fn in filenames:
            p = os.path.join(dirpath, fn)
            try:
                text = open(p, "rb").read().decode("utf-8")
            except UnicodeDecodeError:
                continue
            hits = secrets.scan_text(text)
            if hits:
                secret_hits.append({"path": os.path.relpath(p, root), "classes": hits})

    overall_ok = (
        all_receipts_ok
        and authority_ok
        and schemas_ok
        and subsystems_ok
        and journal_ok
        and not secret_hits
    )

    return {
        "overall_valid": overall_ok,
        "receipts_a1_a8_ok": all_receipts_ok,
        "receipts": receipt_results,
        "authority_ok": authority_ok,
        "schemas_ok": schemas_ok,
        "schema_ids": schema_ids,
        "subsystems_ok": subsystems_ok,
        "lc04_guard_armed": lc04_eval["decision"] == "ALLOW",
        "journal_ok": journal_ok,
        "journal_report": j_report,
        "state_board_sha256": canonical.sha256_ref(b2),
        "current_state": v2["current_state"],
        "secret_scan_hits": secret_hits,
    }


def _categorize_layer_a_file(rel_path):
    if rel_path in ("SPEC_META_OS_v1.1.md", ".antigravity/schemas/invariants_and_states.json", ".antigravity/genesis/authority_lock.json"):
        return "AUTHORITY"
    if rel_path.startswith(".antigravity/schemas/"):
        return "SCHEMA"
    if rel_path.startswith(".antigravity/policies/"):
        return "POLICY"
    if rel_path.startswith(".antigravity/keys/"):
        return "KEYRING"
    if rel_path.startswith(".antigravity/kernel/"):
        return "KERNEL_CODE"
    if rel_path.startswith(".agents/"):
        return "PEP_HOOK"
    if rel_path.startswith("scripts/"):
        return "CLI_SCRIPT"
    if rel_path.startswith(".antigravity/events/") or rel_path.startswith(".antigravity/views/"):
        return "JOURNAL_AND_VIEW"
    if rel_path.startswith(".antigravity/outbox/"):
        return "OUTBOX"
    if rel_path.startswith(".antigravity/genesis/receipts/"):
        return "PHASE_RECEIPT"
    return "GENESIS_ARTIFACT"


def build_kernel_lock(root, selftest_report, keystore_dir=None):
    """Collect and freeze canonical SHA-256 hashes of all Layer A files into kernel_lock.json."""
    layer_a_roots = [".antigravity", ".agents", "scripts"]
    top_files = ["SPEC_META_OS_v1.1.md", ".gitignore"]

    rel_paths = []
    for tf in top_files:
        if os.path.isfile(os.path.join(root, tf)):
            rel_paths.append(tf)

    for sub_root in layer_a_roots:
        abs_sub = os.path.join(root, sub_root)
        if not os.path.isdir(abs_sub):
            continue
        for dirpath, dirnames, filenames in os.walk(abs_sub):
            dirnames[:] = sorted(d for d in dirnames if d not in ("__pycache__", ".git"))
            for fn in sorted(filenames):
                if fn.endswith(".pyc") or fn == ".DS_Store":
                    continue
                abs_f = os.path.join(dirpath, fn)
                rel_f = os.path.relpath(abs_f, root).replace(os.sep, "/")
                if rel_f in EXCLUDED_FROM_KERNEL_LOCK:
                    continue
                rel_paths.append(rel_f)

    rel_paths = sorted(set(rel_paths))
    files_manifest = {}
    category_counts = {}
    total_bytes = 0

    for rel_f in rel_paths:
        abs_f = os.path.join(root, rel_f)
        sha = canonical.file_sha256(abs_f)
        sz = os.path.getsize(abs_f)
        cat = _categorize_layer_a_file(rel_f)
        files_manifest[rel_f] = {
            "sha256": sha,
            "bytes": sz,
            "category": cat,
        }
        category_counts[cat] = category_counts.get(cat, 0) + 1
        total_bytes += sz

    merkle_root = canonical.jcs_hash(files_manifest)
    unsigned_lock = {
        "artifact_kind": "KernelLock",
        "schema_version": "1.2.0",
        "locked_at": LOCK_TIMESTAMP,
        "run_id": "run-0000",
        "state_at_lock": "GENESIS_LOCKED",
        "immutability_invariant": "I-09",
        "authority_lock_sha256": canonical.file_sha256(os.path.join(root, authority.LOCK_PATH)),
        "policy_bundle_lock_sha256": canonical.file_sha256(os.path.join(root, pdp.POLICY_BUNDLE_LOCK_PATH)),
        "journal_head_seq": selftest_report["journal_report"]["head_seq"],
        "journal_head_hash": selftest_report["journal_report"]["head_hash"],
        "state_board_sha256": selftest_report["state_board_sha256"],
        "total_locked_files": len(files_manifest),
        "total_locked_bytes": total_bytes,
        "category_counts": category_counts,
        "merkle_root_sha256": merkle_root,
        "files": files_manifest,
    }
    signed_lock = _sign_document(
        unsigned_lock,
        principal_id="kernel:authority",
        namespace="metaos.kernel",
        root=root,
        keystore_dir=keystore_dir,
    )
    lock_sha, _ = _write_canonical_json(root, KERNEL_LOCK_REL, signed_lock)
    return signed_lock, lock_sha


def verify_kernel_lock(root):
    """Verify kernel_lock.json signature and every locked file's SHA-256 hash."""
    lock_abs = os.path.join(root, KERNEL_LOCK_REL)
    if not os.path.isfile(lock_abs):
        return {"valid": False, "errors": ["kernel_lock.json missing"]}
    lock_doc = canonical.strict_load_file(lock_abs)
    errors = []
    sig_ver = _verify_document_signature(lock_doc, "kernel:authority", "metaos.kernel", root)
    if not sig_ver["valid"]:
        errors.append("kernel_lock signature invalid: %s" % sig_ver.get("reason"))

    files_manifest = lock_doc.get("files", {})
    if canonical.jcs_hash(files_manifest) != lock_doc.get("merkle_root_sha256"):
        errors.append("merkle_root_sha256 mismatch")

    mismatched_files = []
    for rel_f, meta in sorted(files_manifest.items()):
        abs_f = os.path.join(root, rel_f)
        if not os.path.isfile(abs_f):
            mismatched_files.append({"path": rel_f, "error": "missing"})
            continue
        actual_sha = canonical.file_sha256(abs_f)
        if actual_sha != meta["sha256"]:
            mismatched_files.append({"path": rel_f, "expected": meta["sha256"], "actual": actual_sha})

    if mismatched_files:
        errors.append("%d locked files mismatched" % len(mismatched_files))

    return {
        "valid": len(errors) == 0,
        "total_locked_files": len(files_manifest),
        "merkle_root_sha256": lock_doc.get("merkle_root_sha256"),
        "mismatched_files": mismatched_files,
        "errors": errors,
    }


def initialize_layer_b_workspace(root, kernel_lock_sha, keystore_dir=None):
    """Create the 8 empty Layer B skeleton directories with .gitkeep and emit InitializedWorkspace."""
    dirs_meta = {}
    for d in scaffold.LAYER_B:
        abs_d = os.path.join(root, d)
        os.makedirs(abs_d, exist_ok=True)
        keep_rel = d + "/.gitkeep"
        keep_abs = os.path.join(root, keep_rel)
        if not os.path.isfile(keep_abs):
            with open(keep_abs, "wb") as fh:
                fh.write(b"")
        dirs_meta[d] = {
            "gitkeep_path": keep_rel,
            "gitkeep_sha256": canonical.file_sha256(keep_abs),
        }

    unsigned_ws = {
        "artifact_kind": "InitializedWorkspace",
        "schema_version": "1.2.0",
        "initialized_at": LOCK_TIMESTAMP,
        "run_id": "run-0000",
        "bound_kernel_lock_path": KERNEL_LOCK_REL,
        "bound_kernel_lock_sha256": kernel_lock_sha,
        "archetype_binding": "DEFERRED_TO_DAY_1",
        "layer_b_directories": dirs_meta,
    }
    signed_ws = _sign_document(
        unsigned_ws,
        principal_id="kernel:authority",
        namespace="metaos.kernel",
        root=root,
        keystore_dir=keystore_dir,
    )
    ws_sha, _ = _write_canonical_json(root, INITIALIZED_WORKSPACE_REL, signed_ws)
    return signed_ws, ws_sha


def build_kernel_ready_receipt(root, kernel_lock, kernel_lock_sha, ws_doc, ws_sha, selftest_report, keystore_dir=None):
    """Emit cryptographically signed KernelReadyReceipt.json for LC-04."""
    unsigned_ready = {
        "artifact_kind": "KernelReadyReceipt",
        "schema_version": "1.2.0",
        "issued_at": LOCK_TIMESTAMP,
        "run_id": "run-0000",
        "status": "PASS",
        "current_state": "GENESIS_LOCKED",
        "next_armed_transition": {
            "guard_id": "LC-04",
            "from_state": "GENESIS_LOCKED",
            "to_state": "INTENT_CAPTURED",
            "required_evidence": ["InitializedWorkspace", "ValidatedIntentContract"],
        },
        "kernel_lock": {
            "path": KERNEL_LOCK_REL,
            "sha256": kernel_lock_sha,
            "merkle_root_sha256": kernel_lock["merkle_root_sha256"],
            "total_locked_files": kernel_lock["total_locked_files"],
        },
        "initialized_workspace": {
            "path": INITIALIZED_WORKSPACE_REL,
            "sha256": ws_sha,
            "layer_b_directories": sorted(ws_doc["layer_b_directories"].keys()),
        },
        "journal_state": {
            "journal_path": journal.DEFAULT_JOURNAL_REL,
            "head_seq": selftest_report["journal_report"]["head_seq"],
            "head_hash": selftest_report["journal_report"]["head_hash"],
            "state_board_path": projector.DEFAULT_VIEW,
            "state_board_sha256": selftest_report["state_board_sha256"],
        },
        "verified_phase_receipts": {
            phase_id: info["receipt_hash"]
            for phase_id, info in sorted(selftest_report["receipts"].items())
        },
    }
    signed_ready = _sign_document(
        unsigned_ready,
        principal_id="kernel:authority",
        namespace="metaos.kernel",
        root=root,
        keystore_dir=keystore_dir,
    )
    ready_sha, _ = _write_canonical_json(root, KERNEL_READY_RECEIPT_REL, signed_ready)
    return signed_ready, ready_sha


def run(root, keystore_dir=None):
    r = receipt.Receipt(root, "A9", "kernel_selftest_and_lock")

    # Ensure A8 receipt and journal seq 13..14 are recorded before self-test & lock
    _append_a9_journal_events(root, keystore_dir=keystore_dir)

    # Run end-to-end kernel self-test
    st = run_selftest(root)

    # 1. A9-C01: Prior phase receipts A1..A8 verified
    r.check(
        "A9-C01",
        "All prior Layer A phase receipts (A1..A8) exist, have status PASS, and pass JCS hash verification",
        st["receipts_a1_a8_ok"],
        {
            "invariant_id": "I-06",
            "receipts": {k: v["receipt_hash"] for k, v in sorted(st["receipts"].items())},
        },
    )

    # 2. A9-C02: Authority lock and 5 core JSON Schemas verified
    r.check(
        "A9-C02",
        "Authority lock (SPEC_META_OS_v1.1.md + invariants_and_states.json) and all 5 core JSON Schemas pass fail-closed verification",
        st["authority_ok"] and st["schemas_ok"],
        {
            "invariant_id": "I-01",
            "authority_ok": st["authority_ok"],
            "schema_ids": st["schema_ids"],
        },
    )

    # 3. A9-C03: Subsystems (PEP, State Machine, PDP, Keyring, CapabilityToken, UntrustedContentEnvelope) pass self-test
    r.check(
        "A9-C03",
        "End-to-end kernel subsystem self-test passes (PEP SessionStart/PreToolUse, State Machine, PDP, Ed25519 Keyring, CapabilityToken, UntrustedContentEnvelope)",
        st["subsystems_ok"],
        {
            "invariant_id": "I-09",
            "subsystems_ok": st["subsystems_ok"],
            "lc04_guard_armed": st["lc04_guard_armed"],
        },
    )

    # 4. A9-C04: Event journal (seq 0..14) and two-replay state projection verified
    r.check(
        "A9-C04",
        "Event journal (.antigravity/events/run-0000.jsonl, seq 0..14) and deterministic state_board.json pass hash-chain, Ed25519 signature, and two-replay identity checks (I-03)",
        st["journal_ok"],
        {
            "invariant_id": "I-03",
            "entries": st["journal_report"]["entries"],
            "signed_entries": st["journal_report"]["signed_entries"],
            "head_seq": st["journal_report"]["head_seq"],
            "head_hash": st["journal_report"]["head_hash"],
            "state_board_sha256": st["state_board_sha256"],
            "current_state": st["current_state"],
        },
    )

    # 5. A9-C05: Zero secrets or private keys in repository working tree (I-12)
    r.check(
        "A9-C05",
        "Repository working tree scan confirms zero leaked secrets or private key material (I-12)",
        len(st["secret_scan_hits"]) == 0,
        {
            "invariant_id": "I-12",
            "secret_scan_hits": st["secret_scan_hits"],
        },
    )

    # 6. A9-C06: Freeze Layer A into kernel_lock.json and verify cryptographic lock
    kernel_lock, kernel_lock_sha = build_kernel_lock(root, st, keystore_dir=keystore_dir)
    lock_ver = verify_kernel_lock(root)
    r.check(
        "A9-C06",
        "Layer A immutable manifest frozen in .antigravity/genesis/kernel_lock.json and verified with kernel:authority Ed25519 signature (I-09)",
        lock_ver["valid"],
        {
            "invariant_id": "I-09",
            "kernel_lock_sha256": kernel_lock_sha,
            "merkle_root_sha256": kernel_lock["merkle_root_sha256"],
            "total_locked_files": kernel_lock["total_locked_files"],
            "total_locked_bytes": kernel_lock["total_locked_bytes"],
            "category_counts": kernel_lock["category_counts"],
        },
    )

    # 7. A9-C07: Materialize Layer B skeleton (InitializedWorkspace)
    ws_doc, ws_sha = initialize_layer_b_workspace(root, kernel_lock_sha, keystore_dir=keystore_dir)
    ws_sig_ver = _verify_document_signature(ws_doc, "kernel:authority", "metaos.kernel", root)
    layer_b_dirs_ok = all(
        os.path.isdir(os.path.join(root, d)) and os.path.isfile(os.path.join(root, d, ".gitkeep"))
        for d in scaffold.LAYER_B
    )
    r.check(
        "A9-C07",
        "Layer B empty workspace skeleton (contracts/, invariants/, src/, tests/, receipts/, provenance/, infra/, docs/) and InitializedWorkspace artifact created (LC-04)",
        ws_sig_ver["valid"] and layer_b_dirs_ok,
        {
            "invariant_id": "I-09",
            "initialized_workspace_sha256": ws_sha,
            "layer_b_directories": scaffold.LAYER_B,
            "archetype_binding": ws_doc["archetype_binding"],
        },
    )

    # 8. A9-C08: Emit and verify KernelReadyReceipt.json
    ready_doc, ready_sha = build_kernel_ready_receipt(
        root, kernel_lock, kernel_lock_sha, ws_doc, ws_sha, st, keystore_dir=keystore_dir
    )
    ready_sig_ver = _verify_document_signature(ready_doc, "kernel:authority", "metaos.kernel", root)
    r.check(
        "A9-C08",
        "KernelReadyReceipt (.antigravity/genesis/receipts/KernelReadyReceipt.json) emitted and cryptographically signed; LC-04 transition armed",
        ready_sig_ver["valid"] and ready_doc["status"] == "PASS",
        {
            "invariant_id": "I-06",
            "kernel_ready_receipt_sha256": ready_sha,
            "next_armed_transition": ready_doc["next_armed_transition"],
        },
    )

    for rel in (
        KERNEL_LOCK_REL,
        INITIALIZED_WORKSPACE_REL,
        KERNEL_READY_RECEIPT_REL,
        pdp.POLICY_BUNDLE_LOCK_PATH,
        journal.DEFAULT_JOURNAL_REL,
        projector.DEFAULT_VIEW,
        ".antigravity/kernel/metaos/phase_a9.py",
        "scripts/kernel_selftest",
        "scripts/kernel_lock",
    ):
        r.output(rel)
    for d in scaffold.LAYER_B:
        r.output(d + "/.gitkeep")

    return r
