"""Phase A4 - Append-Only Event Journal (run-0000.jsonl) & State Projector (state_board.json)."""
import copy
import os

from . import authority, canonical, contracts, env, journal, projector, receipt, scaffold, secrets
from .receipt import Receipt

RUN_ID = "run-0000"
CONVERSATION_ID = "9372bdb3-ed43-4d40-be8a-ed888cfe77ce"
APPROVAL_STEP_INDEX = 26
APPROVAL_OCCURRED_AT = "2026-10-20T10:12:47Z"
CAPABILITY_OCCURRED_AT = "2026-10-20T03:34:48Z"
BLUEPRINT_OCCURRED_AT = "2026-10-20T03:38:43Z"

BLUEPRINT_REL = ".antigravity/genesis/blueprint/system_blueprint_v1.md"
APPROVAL_REL = ".antigravity/genesis/user_approval_step26.md"
PROPOSAL_REL = ".antigravity/genesis/genesis_bootstrap_proposal.json"
RADAR_REL = ".antigravity/genesis/tech_radar_delta.json"
JOURNAL_REL = ".antigravity/events/run-0000.jsonl"
VIEW_REL = ".antigravity/views/state_board.json"
RECEIPT_A4_REL = ".antigravity/genesis/receipts/A4_event_journal.receipt.json"
JOURNAL_RECEIPT_REL = ".antigravity/genesis/receipts/journal_receipt.json"

ACCEPTED_PATCH_IDS = [
    "C-1", "C-2", "C-3", "C-4", "C-5", "C-6", "C-7", "C-8",
    "V12-01", "V12-02", "V12-03", "V12-04", "V12-05", "V12-06",
]


def _build_tech_radar_delta(root):
    cap_path = os.path.join(root, scaffold.MANIFEST_PATH)
    cap_ref = canonical.file_sha256(cap_path)
    doc = {
        "document_type": "TechRadarDelta",
        "schema_version": "1.0.0",
        "run_id": RUN_ID,
        "capability_manifest_ref": cap_ref,
        "live_web_horizon_scan": {
            "status": "DEFERRED_TO_ARCHETYPE_LOCK",
            "evidence_status": "UNVERIFIED",
            "reason": "Command sandbox has default-deny network egress; Day-0 kernel uses zero external dependencies (stdlib only).",
        },
        "findings": [
            {
                "id": "TR-0001",
                "component": "git_vcs_substrate",
                "source_tier": "OFFICIAL",
                "evidence_status": "VERIFIED",
                "current_version": "2.50.1 (Apple Git-155)",
                "checked_at": "2026-10-20T10:14:35Z",
                "applicability": "REQUIRED",
                "migration_cost": "NONE",
                "security_impact": "POSITIVE_COMMIT_ATTESTATION",
                "expected_benefit": "Enables I-04 commit/tree provenance and I-09 isolated worktrees on local APFS.",
                "confidence": "HIGH",
            },
            {
                "id": "TR-0002",
                "component": "python3_stdlib_kernel_runtime",
                "source_tier": "OFFICIAL",
                "evidence_status": "VERIFIED",
                "current_version": "3.9.6",
                "checked_at": "2026-10-20T10:12:53Z",
                "applicability": "REQUIRED",
                "migration_cost": "LOW",
                "security_impact": "ZERO_SUPPLY_CHAIN_SURFACE",
                "expected_benefit": "Deterministic RFC 8785 JCS, SHA-256 hash chaining, and fail-closed schema validation without third-party packages.",
                "confidence": "HIGH",
            },
            {
                "id": "TR-0003",
                "component": "sshsig_ed25519_signing",
                "source_tier": "OFFICIAL",
                "evidence_status": "VERIFIED",
                "current_version": "OpenSSH_10.2p1",
                "checked_at": "2026-10-20T03:34:47Z",
                "applicability": "REQUIRED",
                "migration_cost": "LOW",
                "security_impact": "CRYPTOGRAPHIC_HUMAN_AND_KERNEL_SIGNATURES",
                "expected_benefit": "Replaces missing LibreSSL Ed25519 CLI support with native ssh-keygen -Y sign/verify.",
                "confidence": "HIGH",
            },
            {
                "id": "TR-0004",
                "component": "ephemeral_container_runtime",
                "source_tier": "OFFICIAL",
                "evidence_status": "VERIFIED",
                "current_version": "NONE",
                "checked_at": "2026-10-20T03:34:27Z",
                "applicability": "UNSUPPORTED",
                "migration_cost": "MEDIUM",
                "security_impact": "DEGRADED_SANDBOX_ISOLATION",
                "expected_benefit": "Degrades gracefully to ephemeral git worktrees under /tmp + human-approved executor until container engine is installed.",
                "confidence": "HIGH",
            },
        ],
    }
    doc["content_hash"] = canonical.jcs_hash(doc)
    return doc


def _build_genesis_proposal(root, blueprint_ref, approval_ref, authority_lock_ref, capability_ref, radar_ref):
    proposal = {
        "document_type": "GenesisBootstrapProposal",
        "schema_version": "1.0.0",
        "proposal_id": "GBP-0000",
        "invariant_basis": "I-01 Day-0 bootstrap exception (user-approved GenesisBootstrapProposal)",
        "run_id": RUN_ID,
        "proposer": {
            "principal_id": "human:oeckoculu",
            "kind": "HUMAN",
            "os_identity": "oeckoculu",
        },
        "approved_at": APPROVAL_OCCURRED_AT,
        "substrate": "LOCAL_APFS_GIT",
        "evidence": {
            "blueprint_path": BLUEPRINT_REL,
            "blueprint_sha256": blueprint_ref,
            "approval_record_path": APPROVAL_REL,
            "approval_record_sha256": approval_ref,
            "authority_lock_path": authority.LOCK_PATH,
            "authority_lock_sha256": authority_lock_ref,
            "capability_manifest_path": scaffold.MANIFEST_PATH,
            "capability_manifest_sha256": capability_ref,
            "tech_radar_delta_path": RADAR_REL,
            "tech_radar_delta_sha256": radar_ref,
        },
        "accepted_patches": [
            {"id": "C-1", "summary": "Bind HUMAN_AUDIT_REQUIRED to suspended_from origin; allow READY_TO_MERGE only when origin == PROOF_ASSEMBLED with CompleteProofReceiptPackage."},
            {"id": "C-2", "summary": "Allow EVIDENCE_INCOMPLETE -> SANDBOX_EXECUTING only when origin is in {CHANGE_ADMITTED..PROOF_ASSEMBLED}; otherwise return to origin."},
            {"id": "C-3", "summary": "Allow recovery from BREAK_GLASS_ACTIVE via RealignmentProjectionReceipt to GENESIS_LOCKED or new child run."},
            {"id": "C-4", "summary": "Define ANY_ACTIVE_STATE explicitly and enforce deterministic exception precedence."},
            {"id": "C-5", "summary": "Route ROLLED_BACK from genesis states to GENESIS_MORPHING instead of INTENT_CAPTURED."},
            {"id": "C-6", "summary": "Enforce both InitializedWorkspace and ValidatedIntentContract on GENESIS_LOCKED -> INTENT_CAPTURED."},
            {"id": "C-7", "summary": "Record pre-journal genesis transitions as retroactive entries (seq 0..k) backed by blueprint and user approval hashes."},
            {"id": "C-8", "summary": "Require CompensatingActionReceipt for post-merge rollback instead of WorktreeCleanupReceipt."},
            {"id": "V12-01", "summary": "Add HANDSHAKE_PENDING rejection (-> CONTRACT_DRAFTING) and timeout (-> INTENT_CAPTURED) transitions."},
            {"id": "V12-02", "summary": "Add BREAK_GLASS_ACTIVE -> GENESIS_LOCKED transition guarded by RealignmentProjectionReceipt."},
            {"id": "V12-03", "summary": "Use polymorphic abstract proof labels ArchetypeSecurityScanProof and ArchetypePerformanceScanProof."},
            {"id": "V12-04", "summary": "Route POST_DEPLOY_OBSERVING drift detection via AutomatedPatchProposal to INTENT_CAPTURED without direct live mutation."},
            {"id": "V12-05", "summary": "Enforce triple RED acceptance oracle on TESTS_ARMED_RED: CompilationSuccess == TRUE, RuntimeExecution == EXECUTED, TestExitCode != 0."},
            {"id": "V12-06", "summary": "Forbid direct merge after QUARANTINED; require return to INTENT_CAPTURED after human security audit."},
        ],
    }
    proposal["content_hash"] = canonical.jcs_hash(proposal)
    return proposal


def _tamper_tests(root, entries, authority_doc, validator):
    outcomes = {}

    # 1. Payload tampering without updating entry_hash
    tampered = [ canonical.jcs_bytes(e) for e in entries ]
    bad0 = copy.deepcopy(entries[0])
    bad0["payload"]["substrate"] = "TAMPERED"
    tampered[0] = canonical.jcs_bytes(bad0)
    _, rep1 = journal.verify_lines(tampered, validator)
    outcomes["payload_byte_tamper_rejected"] = (not rep1["valid"]) and any("entry_hash mismatch" in err for err in rep1["errors"])

    # 2. Broken prev_hash link
    tampered2 = [ canonical.jcs_bytes(e) for e in entries ]
    bad2 = copy.deepcopy(entries[2])
    bad2["prev_hash"] = "sha256:" + ("1" * 64)
    bad2["entry_hash"] = journal.entry_hash(bad2)
    tampered2[2] = canonical.jcs_bytes(bad2)
    _, rep2 = journal.verify_lines(tampered2, validator)
    outcomes["broken_prev_hash_rejected"] = (not rep2["valid"]) and any("prev_hash does not chain" in err for err in rep2["errors"])

    # 3. Sequence gap (delete seq 1)
    tampered3 = [ canonical.jcs_bytes(e) for idx, e in enumerate(entries) if idx != 1 ]
    _, rep3 = journal.verify_lines(tampered3, validator)
    outcomes["sequence_gap_rejected"] = (not rep3["valid"]) and any("seq" in err for err in rep3["errors"])

    # 4. Secret injection rejected before disk write (I-12)
    try:
        journal.build_entry(
            validator=validator,
            seq=len(entries),
            run_id=RUN_ID,
            prev_hash=entries[-1]["entry_hash"],
            event_type="EVIDENCE_RECORDED",
            actor={"principal_id": "kernel:genesis", "kind": "KERNEL", "os_identity": "oeckoculu"},
            payload={
                "phase": "A4",
                "receipt_path": "ghp_" + ("x" * 36),
                "receipt_hash": canonical.ZERO_HASH,
                "status": "PASS",
            },
            reproducibility=env.reproducibility(root),
            retroactive=False,
        )
        outcomes["secret_injection_rejected"] = False
    except secrets.SecretDetected:
        outcomes["secret_injection_rejected"] = True

    # 5. Illegal state transition rejected by projector (I-08)
    bad_entries = copy.deepcopy(entries)
    bad_entries[-1]["transition"]["to_state"] = "READY_TO_MERGE"
    try:
        projector.replay(bad_entries, authority_doc, JOURNAL_REL, root=None)
        outcomes["illegal_transition_rejected"] = False
    except projector.ProjectionError:
        outcomes["illegal_transition_rejected"] = True

    return outcomes


def run(root):
    r = Receipt(root, "A4", "event_journal_and_state_projector")

    blueprint_abs = os.path.join(root, BLUEPRINT_REL)
    approval_abs = os.path.join(root, APPROVAL_REL)
    lock_abs = os.path.join(root, authority.LOCK_PATH)
    cap_abs = os.path.join(root, scaffold.MANIFEST_PATH)
    a1_abs = os.path.join(root, authority.RECEIPT_PATH)
    a2_abs = os.path.join(root, scaffold.RECEIPT_PATH)
    a3_abs = os.path.join(root, contracts.RECEIPT_PATH)

    prereqs = [blueprint_abs, approval_abs, lock_abs, cap_abs, a1_abs, a2_abs, a3_abs]
    prereq_ok = all(os.path.isfile(p) for p in prereqs)
    prior_receipts = {}
    if prereq_ok:
        for ph, rp in (("A1", a1_abs), ("A2", a2_abs), ("A3", a3_abs)):
            ok_sig, claimed = receipt.verify_receipt_file(rp)
            doc = canonical.strict_load_file(rp)
            prior_receipts[ph] = {"hash_ok": ok_sig, "status": doc.get("status"), "receipt_hash": claimed}
            if (not ok_sig) or doc.get("status") != "PASS":
                prereq_ok = False
    if not r.check("A4-C01", "Prerequisite genesis artifacts exist and A1..A3 receipts are PASS and hash-verified",
                   prereq_ok,
                   {"checked": [os.path.relpath(p, root) for p in prereqs], "prior_receipts": prior_receipts}):
        return r

    # Normalize blueprint & approval text in-place to canonical UTF-8/LF/NFC
    for p in (blueprint_abs, approval_abs):
        txt = open(p, "rb").read().decode("utf-8")
        with open(p, "wb") as fh:
            fh.write(canonical.canonical_text(txt).encode("utf-8"))

    radar_doc = _build_tech_radar_delta(root)
    radar_abs = os.path.join(root, RADAR_REL)
    os.makedirs(os.path.dirname(radar_abs), exist_ok=True)
    with open(radar_abs, "wb") as fh:
        fh.write(canonical.pretty_bytes(radar_doc))

    blueprint_ref = canonical.file_sha256(blueprint_abs)
    approval_ref = canonical.file_sha256(approval_abs)
    lock_ref = canonical.file_sha256(lock_abs)
    cap_ref = canonical.file_sha256(cap_abs)
    radar_ref = canonical.file_sha256(radar_abs)

    proposal_doc = _build_genesis_proposal(root, blueprint_ref, approval_ref, lock_ref, cap_ref, radar_ref)
    proposal_abs = os.path.join(root, PROPOSAL_REL)
    with open(proposal_abs, "wb") as fh:
        fh.write(canonical.pretty_bytes(proposal_doc))
    proposal_ref = canonical.file_sha256(proposal_abs)

    validator = journal.load_validator(root)
    journal_abs = os.path.join(root, JOURNAL_REL)
    if os.path.exists(journal_abs):
        os.remove(journal_abs)

    repro = env.reproducibility(root)
    human_actor = {"principal_id": "human:oeckoculu", "kind": "HUMAN", "os_identity": "oeckoculu"}
    kernel_actor = {"principal_id": "kernel:genesis", "kind": "KERNEL", "os_identity": "oeckoculu"}

    # seq 0: GENESIS_BOOTSTRAP (user GENESIS_LOCKED approval)
    prev = canonical.ZERO_HASH
    e0 = journal.build_entry(
        validator=validator,
        seq=0,
        run_id=RUN_ID,
        prev_hash=prev,
        event_type="GENESIS_BOOTSTRAP",
        actor=human_actor,
        payload={
            "proposal_id": "GBP-0000",
            "proposal_path": PROPOSAL_REL,
            "proposal_ref": proposal_ref,
            "decision": "APPROVED",
            "approval_record": {
                "path": APPROVAL_REL,
                "sha256": approval_ref,
                "channel": "ANTIGRAVITY_CONVERSATION",
                "conversation_id": CONVERSATION_ID,
                "step_index": APPROVAL_STEP_INDEX,
            },
            "blueprint": {
                "path": BLUEPRINT_REL,
                "sha256": blueprint_ref,
            },
            "accepted_patch_ids": ACCEPTED_PATCH_IDS,
            "substrate": "LOCAL_APFS_GIT",
        },
        reproducibility=repro,
        transition=None,
        retroactive=True,
        occurred_at=APPROVAL_OCCURRED_AT,
    )
    prev = journal.append(journal_abs, e0, validator)

    # seq 1..3: EVIDENCE_RECORDED for A1, A2, A3
    for seq_idx, (phase_id, rec_rel) in enumerate([
        ("A1", authority.RECEIPT_PATH),
        ("A2", scaffold.RECEIPT_PATH),
        ("A3", contracts.RECEIPT_PATH),
    ], start=1):
        rec_doc = canonical.strict_load_file(os.path.join(root, rec_rel))
        ev_entry = journal.build_entry(
            validator=validator,
            seq=seq_idx,
            run_id=RUN_ID,
            prev_hash=prev,
            event_type="EVIDENCE_RECORDED",
            actor=kernel_actor,
            payload={
                "phase": phase_id,
                "receipt_path": rec_rel,
                "receipt_hash": rec_doc["receipt_hash"],
                "status": "PASS",
            },
            reproducibility=repro,
            transition=None,
            retroactive=False,
        )
        prev = journal.append(journal_abs, ev_entry, validator)

    # seq 4: TECH_RADAR_SYNC -> CAPABILITY_BASELINED (LC-01)
    e4 = journal.build_entry(
        validator=validator,
        seq=4,
        run_id=RUN_ID,
        prev_hash=prev,
        event_type="STATE_TRANSITION",
        actor=kernel_actor,
        payload={},
        reproducibility=repro,
        transition={
            "from_state": "TECH_RADAR_SYNC",
            "to_state": "CAPABILITY_BASELINED",
            "guard_id": "LC-01",
            "suspended_from": None,
            "evidence_refs": [
                {"kind": "CapabilityManifest", "ref": cap_ref, "path": scaffold.MANIFEST_PATH},
                {"kind": "TechRadarDelta", "ref": radar_ref, "path": RADAR_REL},
            ],
            "waivers": [],
        },
        retroactive=True,
        occurred_at=CAPABILITY_OCCURRED_AT,
    )
    prev = journal.append(journal_abs, e4, validator)

    # seq 5: CAPABILITY_BASELINED -> GENESIS_MORPHING (LC-02)
    e5 = journal.build_entry(
        validator=validator,
        seq=5,
        run_id=RUN_ID,
        prev_hash=prev,
        event_type="STATE_TRANSITION",
        actor=kernel_actor,
        payload={},
        reproducibility=repro,
        transition={
            "from_state": "CAPABILITY_BASELINED",
            "to_state": "GENESIS_MORPHING",
            "guard_id": "LC-02",
            "suspended_from": None,
            "evidence_refs": [
                {"kind": "ValidatedEnvironmentProfile", "ref": cap_ref, "path": scaffold.MANIFEST_PATH},
                {"kind": "AuthorityLock", "ref": lock_ref, "path": authority.LOCK_PATH},
            ],
            "waivers": [],
        },
        retroactive=True,
        occurred_at=BLUEPRINT_OCCURRED_AT,
    )
    prev = journal.append(journal_abs, e5, validator)

    # seq 6: GENESIS_MORPHING -> GENESIS_LOCKED (LC-03)
    e6 = journal.build_entry(
        validator=validator,
        seq=6,
        run_id=RUN_ID,
        prev_hash=prev,
        event_type="STATE_TRANSITION",
        actor=human_actor,
        payload={},
        reproducibility=repro,
        transition={
            "from_state": "GENESIS_MORPHING",
            "to_state": "GENESIS_LOCKED",
            "guard_id": "LC-03",
            "suspended_from": None,
            "evidence_refs": [
                {"kind": "UserApprovedProfile", "ref": proposal_ref, "path": PROPOSAL_REL},
                {"kind": "HumanApprovalRecord", "ref": approval_ref, "path": APPROVAL_REL},
            ],
            "waivers": [],
        },
        retroactive=True,
        occurred_at=APPROVAL_OCCURRED_AT,
    )
    prev = journal.append(journal_abs, e6, validator)

    entries, report = journal.verify_file(journal_abs, validator)
    r.check("A4-C02", "Journal run-0000.jsonl has seq 0=GENESIS_BOOTSTRAP and contiguous hash-chained entries",
            report["valid"] and len(entries) == 7 and entries[0]["event_type"] == "GENESIS_BOOTSTRAP",
            report)

    authority_doc = canonical.strict_load_file(os.path.join(root, projector.AUTHORITY_PATH))
    view1, bytes1 = projector.project_file(root, JOURNAL_REL, VIEW_REL)
    view2, bytes2 = projector.project_file(root, JOURNAL_REL, out_rel_path=None)
    r.check("A4-C03", "Two independent replays produce byte-identical state_board.json at state GENESIS_LOCKED",
            bytes1 == bytes2 and view1["current_state"] == "GENESIS_LOCKED",
            {"current_state": view1["current_state"], "view_jcs_sha256": canonical.jcs_hash(view1),
             "byte_identical": bytes1 == bytes2})

    tamper = _tamper_tests(root, entries, authority_doc, validator)
    r.check("A4-C04", "Tamper & security negative tests all fail-closed (payload tamper, prev_hash break, seq gap, secret injection, illegal transition)",
            all(tamper.values()), tamper)

    for rel in (BLUEPRINT_REL, APPROVAL_REL, RADAR_REL, PROPOSAL_REL, JOURNAL_REL, VIEW_REL):
        r.output(rel)
    return r
