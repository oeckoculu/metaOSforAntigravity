"""Phase A5: State Machine Guard Compilation (v1.2.0) & Policy Decision Point (PDP).

Materializes:
- .antigravity/policies/transitions.v1.2.0.json
- .antigravity/policies/admission_policy.v1.2.0.json
- .antigravity/policies/policy_bundle.lock.json

Executes the deterministic regression test suite across all 14 accepted patches
(C-1..C-8 and V12-01..V12-06) plus PDP/Admission Controller invariants
(I-01, I-02, I-04, I-05, I-06, I-08, I-09, I-10, I-12) and live journal replay.
"""
import copy
import os

from . import canonical, journal, pdp, receipt, schema, statemachine

RECEIPT_A5_REL = ".antigravity/genesis/receipts/A5_state_machine_and_pdp.receipt.json"
AUTHORITY_LOCK_REL = ".antigravity/genesis/authority_lock.json"
GENESIS_PROPOSAL_REL = ".antigravity/genesis/genesis_bootstrap_proposal.json"
CHANGE_PROPOSAL_SCHEMA_REL = ".antigravity/schemas/core/change_proposal.schema.json"
FIXTURES_REL = ".antigravity/schemas/core/fixtures/core_golden.fixtures.json"


def _write_canonical_json(root, rel_path, obj):
    abs_path = os.path.join(root, rel_path)
    os.makedirs(os.path.dirname(abs_path), exist_ok=True)
    pretty = canonical.pretty_bytes(obj)
    with open(abs_path, "wb") as fh:
        fh.write(pretty)
    return canonical.jcs_hash(obj), len(pretty)


def _run_happy_path_simulation():
    """Simulate a full 22-step lifecycle from TECH_RADAR_SYNC to CLOSED."""
    ctx = statemachine.initial_context(
        state="TECH_RADAR_SYNC",
        risk_class="R2",
        genesis_approved=True,
    )
    steps = [
        ("TECH_RADAR_SYNC", "CAPABILITY_BASELINED", ["TechRadarDelta", "CapabilityManifest"], "KERNEL", True, None),
        ("CAPABILITY_BASELINED", "GENESIS_MORPHING", ["ValidatedEnvironmentProfile"], "KERNEL", True, None),
        ("GENESIS_MORPHING", "GENESIS_LOCKED", ["UserApprovedProfile"], "HUMAN", True, None),
        ("GENESIS_LOCKED", "INTENT_CAPTURED", ["InitializedWorkspace", "ValidatedIntentContract"], "KERNEL", False, None),
        ("INTENT_CAPTURED", "RISK_CLASSIFIED", ["RiskClassAssignment", "GateSchedule"], "KERNEL", False, None),
        ("RISK_CLASSIFIED", "HANDSHAKE_PENDING", ["CounterfactualHandshakeRequest"], "KERNEL", False, None),
        ("HANDSHAKE_PENDING", "CONTRACT_DRAFTING", ["HumanApprovalReceipt"], "HUMAN", False, None),
        ("CONTRACT_DRAFTING", "CONTRACT_REVIEWED", ["ThreatModelReport", "ContractDiff"], "KERNEL", False, None),
        ("CONTRACT_REVIEWED", "CONTRACT_LOCKED", ["CanonicalSpecLockFile"], "KERNEL", False, None),
        ("CONTRACT_LOCKED", "TESTS_ARMED_RED", ["PropertyBasedTestSet", "GoldenCases"], "KERNEL", False, None),
        (
            "TESTS_ARMED_RED",
            "CHANGE_ADMITTED",
            ["AdmissionPolicyPassReceipt"],
            "KERNEL",
            False,
            {"compilation_success": True, "runtime_execution": "EXECUTED", "test_exit_code": 1},
        ),
        ("CHANGE_ADMITTED", "SANDBOX_EXECUTING", ["EphemeralSandboxAllocation"], "EXECUTOR", False, None),
        ("SANDBOX_EXECUTING", "WORKTREE_GREEN", ["IsolatedWorktreeBuildSuccess"], "EXECUTOR", False, None),
        ("WORKTREE_GREEN", "SECURITY_VERIFIED", ["ArchetypeSecurityScanProof"], "KERNEL", False, None),
        ("SECURITY_VERIFIED", "MUTATION_VERIFIED", ["MutationScorePass", "Non-SurvivingInvariants"], "KERNEL", False, None),
        ("MUTATION_VERIFIED", "PERFORMANCE_VERIFIED", ["ArchetypePerformanceScanProof"], "KERNEL", False, None),
        ("PERFORMANCE_VERIFIED", "PROOF_ASSEMBLED", ["CompleteProofReceiptPackage"], "KERNEL", False, None),
        ("PROOF_ASSEMBLED", "HUMAN_AUDIT_REQUIRED", ["CompleteProofReceiptPackage"], "KERNEL", False, None),
        ("HUMAN_AUDIT_REQUIRED", "READY_TO_MERGE", ["HumanApprovalToken", "CompleteProofReceiptPackage"], "HUMAN", False, None),
        ("READY_TO_MERGE", "MERGED", ["GitMergeSuccess", "AppendOnlyEventRecord"], "EXECUTOR", False, None),
        ("MERGED", "POST_DEPLOY_OBSERVING", ["CanaryDeploymentTelemetry"], "KERNEL", False, None),
        ("POST_DEPLOY_OBSERVING", "CLOSED", ["StabilityReceipt", "FinalStateLock"], "KERNEL", False, None),
    ]
    guards_fired = []
    for from_s, to_s, ev, actor, retro, red in steps:
        res = statemachine.evaluate_transition(
            state_ctx=ctx,
            from_state=from_s,
            to_state=to_s,
            evidence=ev,
            actor_kind=actor,
            retroactive=retro,
            red_oracle=red,
        )
        if res["decision"] != "ALLOW":
            return False, "Failed at %s -> %s: %s" % (from_s, to_s, res["reason"]), guards_fired
        ctx = res["next_state_ctx"]
        guards_fired.append(res["guard_id"])
    return ctx["current_state"] == "CLOSED", "Completed 22 transitions to CLOSED", guards_fired


def _test_c1_and_v12_06():
    """Verify C-1 (HUMAN_AUDIT_REQUIRED origin-scoped routing) & V12-06 (Post-quarantine merge ban)."""
    results = []

    # 1. BUDGET_EXHAUSTED from SANDBOX_EXECUTING -> HUMAN_AUDIT_REQUIRED -> READY_TO_MERGE must be DENIED (C-1)
    ctx = statemachine.initial_context(state="SANDBOX_EXECUTING", risk_class="R2")
    r1 = statemachine.evaluate_transition(ctx, "SANDBOX_EXECUTING", "BUDGET_EXHAUSTED", ["BudgetBreachRecord"])
    r2 = statemachine.evaluate_transition(r1["next_state_ctx"], "BUDGET_EXHAUSTED", "HUMAN_AUDIT_REQUIRED", ["BudgetIncrementAuthorization"])
    r3_bypass = statemachine.evaluate_transition(
        r2["next_state_ctx"],
        "HUMAN_AUDIT_REQUIRED",
        "READY_TO_MERGE",
        ["HumanApprovalToken", "CompleteProofReceiptPackage"],
        actor_kind="HUMAN",
    )
    r3_resume = statemachine.evaluate_transition(
        r2["next_state_ctx"],
        "HUMAN_AUDIT_REQUIRED",
        "SANDBOX_EXECUTING",
        ["HumanApprovalToken"],
        actor_kind="HUMAN",
    )
    results.append(("C-1_budget_to_merge_denied", r3_bypass["decision"] == "DENY"))
    results.append(("C-1_budget_resume_to_origin_allowed", r3_resume["decision"] == "ALLOW"))

    # 2. BLOCKED_POLICY from CONTRACT_REVIEWED -> HUMAN_AUDIT_REQUIRED -> READY_TO_MERGE must be DENIED (C-1)
    ctx_bp = statemachine.initial_context(state="CONTRACT_REVIEWED", risk_class="R2")
    b1 = statemachine.evaluate_transition(ctx_bp, "CONTRACT_REVIEWED", "BLOCKED_POLICY", ["PolicyViolationRecord"])
    b2 = statemachine.evaluate_transition(b1["next_state_ctx"], "BLOCKED_POLICY", "HUMAN_AUDIT_REQUIRED", ["PolicyExemptionReviewPacket"])
    b3_bypass = statemachine.evaluate_transition(
        b2["next_state_ctx"],
        "HUMAN_AUDIT_REQUIRED",
        "READY_TO_MERGE",
        ["HumanApprovalToken", "CompleteProofReceiptPackage"],
        actor_kind="HUMAN",
    )
    results.append(("C-1_blocked_policy_to_merge_denied", b3_bypass["decision"] == "DENY"))

    # 3. V12-06: QUARANTINED -> HUMAN_AUDIT_REQUIRED -> READY_TO_MERGE or SANDBOX_EXECUTING must be DENIED;
    #    only INTENT_CAPTURED with HumanApprovalToken & SanitizedAuditAttestation is ALLOWED.
    ctx_q = statemachine.initial_context(state="SANDBOX_EXECUTING", risk_class="R2")
    q1 = statemachine.evaluate_transition(ctx_q, "SANDBOX_EXECUTING", "QUARANTINED", ["SecurityAnomalyReport"])
    q2 = statemachine.evaluate_transition(q1["next_state_ctx"], "QUARANTINED", "HUMAN_AUDIT_REQUIRED", ["SanitizedAuditAttestation"])
    q3_merge = statemachine.evaluate_transition(
        q2["next_state_ctx"],
        "HUMAN_AUDIT_REQUIRED",
        "READY_TO_MERGE",
        ["HumanApprovalToken", "CompleteProofReceiptPackage"],
        actor_kind="HUMAN",
    )
    q3_resume = statemachine.evaluate_transition(
        q2["next_state_ctx"],
        "HUMAN_AUDIT_REQUIRED",
        "SANDBOX_EXECUTING",
        ["HumanApprovalToken", "SanitizedAuditAttestation"],
        actor_kind="HUMAN",
    )
    q3_reintent = statemachine.evaluate_transition(
        q2["next_state_ctx"],
        "HUMAN_AUDIT_REQUIRED",
        "INTENT_CAPTURED",
        ["HumanApprovalToken", "SanitizedAuditAttestation"],
        actor_kind="HUMAN",
    )
    results.append(("V12-06_quarantine_to_merge_denied", q3_merge["decision"] == "DENY"))
    results.append(("V12-06_quarantine_to_sandbox_denied", q3_resume["decision"] == "DENY"))
    results.append(("V12-06_quarantine_to_intent_captured_allowed", q3_reintent["decision"] == "ALLOW"))

    # 4. C-1 positive: PROOF_ASSEMBLED -> HUMAN_AUDIT_REQUIRED -> READY_TO_MERGE allowed with proof package
    ctx_pa = statemachine.initial_context(state="PROOF_ASSEMBLED", risk_class="R3")
    p1 = statemachine.evaluate_transition(ctx_pa, "PROOF_ASSEMBLED", "HUMAN_AUDIT_REQUIRED", ["CompleteProofReceiptPackage"])
    p2 = statemachine.evaluate_transition(
        p1["next_state_ctx"],
        "HUMAN_AUDIT_REQUIRED",
        "READY_TO_MERGE",
        ["HumanApprovalToken", "CompleteProofReceiptPackage"],
        actor_kind="HUMAN",
    )
    results.append(("C-1_proof_assembled_to_merge_allowed", p2["decision"] == "ALLOW"))

    all_ok = all(ok for _, ok in results)
    return all_ok, dict(results)


def _test_c2_evidence_incomplete():
    """Verify C-2 (EVIDENCE_INCOMPLETE pre-admission vs post-admission routing)."""
    results = []

    # Pre-admission: CONTRACT_REVIEWED -> EVIDENCE_INCOMPLETE -> SANDBOX_EXECUTING must be DENIED
    ctx_pre = statemachine.initial_context(state="CONTRACT_REVIEWED", risk_class="R2")
    e1 = statemachine.evaluate_transition(ctx_pre, "CONTRACT_REVIEWED", "EVIDENCE_INCOMPLETE", ["MissingEvidenceAuditReport"])
    e2_jump = statemachine.evaluate_transition(
        e1["next_state_ctx"],
        "EVIDENCE_INCOMPLETE",
        "SANDBOX_EXECUTING",
        ["RemediationTaskEnvelope"],
    )
    e2_origin = statemachine.evaluate_transition(
        e1["next_state_ctx"],
        "EVIDENCE_INCOMPLETE",
        "CONTRACT_REVIEWED",
        ["RemediationTaskEnvelope"],
    )
    results.append(("C-2_pre_admission_jump_to_sandbox_denied", e2_jump["decision"] == "DENY"))
    results.append(("C-2_pre_admission_return_to_origin_allowed", e2_origin["decision"] == "ALLOW"))

    # Post-admission: SECURITY_VERIFIED -> EVIDENCE_INCOMPLETE -> SANDBOX_EXECUTING must be ALLOWED
    ctx_post = statemachine.initial_context(state="SECURITY_VERIFIED", risk_class="R2")
    p1 = statemachine.evaluate_transition(ctx_post, "SECURITY_VERIFIED", "EVIDENCE_INCOMPLETE", ["MissingEvidenceAuditReport"])
    p2_sandbox = statemachine.evaluate_transition(
        p1["next_state_ctx"],
        "EVIDENCE_INCOMPLETE",
        "SANDBOX_EXECUTING",
        ["RemediationTaskEnvelope"],
    )
    results.append(("C-2_post_admission_remediate_via_sandbox_allowed", p2_sandbox["decision"] == "ALLOW"))

    return all(ok for _, ok in results), dict(results)


def _test_c3_to_c8_and_v12_02():
    """Verify patches C-3/V12-02, C-4, C-5, C-6, C-7, and C-8."""
    results = []

    # C-3 / V12-02: BREAK_GLASS_ACTIVE -> GENESIS_LOCKED
    ctx_bg = statemachine.initial_context(state="POST_DEPLOY_OBSERVING", risk_class="R3")
    bg_enter = statemachine.evaluate_transition(
        ctx_bg,
        "POST_DEPLOY_OBSERVING",
        "BREAK_GLASS_ACTIVE",
        ["CryptographicallySignedBreakGlassOverrideEvent"],
        actor_kind="HUMAN",
        ssh_signed=True,
    )
    bg_exit_unsigned = statemachine.evaluate_transition(
        bg_enter["next_state_ctx"],
        "BREAK_GLASS_ACTIVE",
        "GENESIS_LOCKED",
        ["RealignmentProjectionReceipt", "CryptographicallySignedBreakGlassReviewRecord"],
        actor_kind="HUMAN",
        ssh_signed=False,
    )
    bg_exit_valid = statemachine.evaluate_transition(
        bg_enter["next_state_ctx"],
        "BREAK_GLASS_ACTIVE",
        "GENESIS_LOCKED",
        ["RealignmentProjectionReceipt", "CryptographicallySignedBreakGlassReviewRecord"],
        actor_kind="HUMAN",
        ssh_signed=True,
    )
    results.append(("C-3_V12-02_break_glass_enter_allowed", bg_enter["decision"] == "ALLOW"))
    results.append(("C-3_V12-02_break_glass_exit_unsigned_denied", bg_exit_unsigned["decision"] == "DENY"))
    results.append(("C-3_V12-02_break_glass_exit_to_genesis_locked_allowed", bg_exit_valid["decision"] == "ALLOW"))

    # C-4: Exception Priority Preemption (BUDGET_EXHAUSTED=4 -> BLOCKED_POLICY=3 allowed and preserves origin;
    #      BLOCKED_POLICY=3 -> QUARANTINED=2 allowed; QUARANTINED=2 -> BUDGET_EXHAUSTED=4 denied)
    ctx_p = statemachine.initial_context(state="SANDBOX_EXECUTING", risk_class="R2")
    ex_b = statemachine.evaluate_transition(ctx_p, "SANDBOX_EXECUTING", "BUDGET_EXHAUSTED", ["BudgetBreachRecord"])
    ex_preempt_policy = statemachine.evaluate_transition(
        ex_b["next_state_ctx"],
        "BUDGET_EXHAUSTED",
        "BLOCKED_POLICY",
        ["PolicyViolationRecord"],
    )
    ex_preempt_up = statemachine.evaluate_transition(
        ex_preempt_policy["next_state_ctx"],
        "BLOCKED_POLICY",
        "QUARANTINED",
        ["SecurityAnomalyReport"],
    )
    ex_preempt_down = statemachine.evaluate_transition(
        ex_preempt_up["next_state_ctx"],
        "QUARANTINED",
        "BUDGET_EXHAUSTED",
        ["BudgetBreachRecord"],
    )
    results.append(("C-4_higher_priority_exception_preempts", ex_preempt_up["decision"] == "ALLOW"))
    results.append(("C-4_origin_preserved_on_preemption", ex_preempt_policy["next_state_ctx"]["suspended_from"] == "SANDBOX_EXECUTING"))
    results.append(("C-4_lower_priority_exception_denied", ex_preempt_down["decision"] == "DENY"))

    # C-5: Genesis vs Post-Genesis ROLLED_BACK recovery
    ctx_gen = statemachine.initial_context(state="GENESIS_MORPHING", risk_class="R0")
    rb_gen = statemachine.evaluate_transition(ctx_gen, "GENESIS_MORPHING", "ROLLED_BACK", ["FailureRecord", "WorktreeCleanupReceipt"])
    rb_gen_wrong = statemachine.evaluate_transition(rb_gen["next_state_ctx"], "ROLLED_BACK", "INTENT_CAPTURED", ["RevisedHypothesisRecord"])
    rb_gen_right = statemachine.evaluate_transition(rb_gen["next_state_ctx"], "ROLLED_BACK", "GENESIS_MORPHING", ["RevisedGenesisProfileRecord"])
    results.append(("C-5_genesis_rollback_to_intent_denied", rb_gen_wrong["decision"] == "DENY"))
    results.append(("C-5_genesis_rollback_to_morphing_allowed", rb_gen_right["decision"] == "ALLOW"))

    # C-6: LC-04 requires BOTH InitializedWorkspace & ValidatedIntentContract
    ctx_gl = statemachine.initial_context(state="GENESIS_LOCKED", risk_class="R1")
    lc04_partial = statemachine.evaluate_transition(ctx_gl, "GENESIS_LOCKED", "INTENT_CAPTURED", ["InitializedWorkspace"])
    lc04_full = statemachine.evaluate_transition(
        ctx_gl,
        "GENESIS_LOCKED",
        "INTENT_CAPTURED",
        ["InitializedWorkspace", "ValidatedIntentContract"],
    )
    results.append(("C-6_lc04_single_evidence_denied", lc04_partial["decision"] == "DENY"))
    results.append(("C-6_lc04_dual_evidence_allowed", lc04_full["decision"] == "ALLOW"))

    # C-7: Retroactive flag forbidden post-genesis
    lc04_retro = statemachine.evaluate_transition(
        ctx_gl,
        "GENESIS_LOCKED",
        "INTENT_CAPTURED",
        ["InitializedWorkspace", "ValidatedIntentContract"],
        retroactive=True,
    )
    results.append(("C-7_post_genesis_retroactive_denied", lc04_retro["decision"] == "DENY"))

    # C-8: Post-merge rollback requires CompensatingActionReceipt (WorktreeCleanupReceipt rejected)
    ctx_pm = statemachine.initial_context(state="POST_DEPLOY_OBSERVING", risk_class="R2")
    pm_rb_bad = statemachine.evaluate_transition(
        ctx_pm,
        "POST_DEPLOY_OBSERVING",
        "ROLLED_BACK",
        ["FailureRecord", "WorktreeCleanupReceipt"],
    )
    pm_rb_good = statemachine.evaluate_transition(
        ctx_pm,
        "POST_DEPLOY_OBSERVING",
        "ROLLED_BACK",
        ["FailureRecord", "CompensatingActionReceipt"],
    )
    results.append(("C-8_post_merge_worktree_cleanup_denied", pm_rb_bad["decision"] == "DENY"))
    results.append(("C-8_post_merge_compensating_action_allowed", pm_rb_good["decision"] == "ALLOW"))

    return all(ok for _, ok in results), dict(results)


def _test_v12_01_03_04_05():
    """Verify V12-01 (Handshake branches), V12-03 (Polymorphic proofs), V12-04 (Drift loop), V12-05 (Triple RED oracle)."""
    results = []

    # V12-01: HANDSHAKE_PENDING approve, reject, timeout
    ctx_hs = statemachine.initial_context(state="HANDSHAKE_PENDING", risk_class="R2")
    hs_approve = statemachine.evaluate_transition(ctx_hs, "HANDSHAKE_PENDING", "CONTRACT_DRAFTING", ["HumanApprovalReceipt"], actor_kind="HUMAN")
    hs_reject = statemachine.evaluate_transition(ctx_hs, "HANDSHAKE_PENDING", "CONTRACT_DRAFTING", ["HandshakeRejectionReceipt"], actor_kind="HUMAN")
    hs_timeout = statemachine.evaluate_transition(ctx_hs, "HANDSHAKE_PENDING", "INTENT_CAPTURED", ["HandshakeTimeoutReceipt"], actor_kind="KERNEL")
    results.append(("V12-01_handshake_approve_allowed", hs_approve["decision"] == "ALLOW" and hs_approve["guard_id"] == "LC-07A"))
    results.append(("V12-01_handshake_reject_allowed", hs_reject["decision"] == "ALLOW" and hs_reject["guard_id"] == "LC-07B"))
    results.append(("V12-01_handshake_timeout_allowed", hs_timeout["decision"] == "ALLOW" and hs_timeout["guard_id"] == "LC-07C"))

    # V12-03: Polymorphic proof labels ArchetypeSecurityScanProof & ArchetypePerformanceScanProof
    ctx_wg = statemachine.initial_context(state="WORKTREE_GREEN", risk_class="R1")
    sec_bad = statemachine.evaluate_transition(ctx_wg, "WORKTREE_GREEN", "SECURITY_VERIFIED", ["SASTPass"])
    sec_good = statemachine.evaluate_transition(ctx_wg, "WORKTREE_GREEN", "SECURITY_VERIFIED", ["ArchetypeSecurityScanProof"])
    ctx_mv = statemachine.initial_context(state="MUTATION_VERIFIED", risk_class="R1")
    perf_bad = statemachine.evaluate_transition(ctx_mv, "MUTATION_VERIFIED", "PERFORMANCE_VERIFIED", ["BenchmarkDeltaPass"])
    perf_good = statemachine.evaluate_transition(ctx_mv, "MUTATION_VERIFIED", "PERFORMANCE_VERIFIED", ["ArchetypePerformanceScanProof"])
    results.append(("V12-03_legacy_security_label_denied", sec_bad["decision"] == "DENY"))
    results.append(("V12-03_polymorphic_security_label_allowed", sec_good["decision"] == "ALLOW"))
    results.append(("V12-03_legacy_perf_label_denied", perf_bad["decision"] == "DENY"))
    results.append(("V12-03_polymorphic_perf_label_allowed", perf_good["decision"] == "ALLOW"))

    # V12-04: POST_DEPLOY_OBSERVING drift loopback
    ctx_pdo = statemachine.initial_context(state="POST_DEPLOY_OBSERVING", risk_class="R2")
    drift_bad = statemachine.evaluate_transition(ctx_pdo, "POST_DEPLOY_OBSERVING", "INTENT_CAPTURED", ["DriftDetectionReport"])
    drift_good = statemachine.evaluate_transition(
        ctx_pdo,
        "POST_DEPLOY_OBSERVING",
        "INTENT_CAPTURED",
        ["DriftDetectionReport", "AutomatedPatchProposal"],
    )
    results.append(("V12-04_drift_without_proposal_denied", drift_bad["decision"] == "DENY"))
    results.append(("V12-04_drift_with_automated_patch_proposal_allowed", drift_good["decision"] == "ALLOW"))

    # V12-05: Triple RED test oracle
    ctx_red = statemachine.initial_context(state="TESTS_ARMED_RED", risk_class="R1")
    red_compile_err = statemachine.evaluate_transition(
        ctx_red,
        "TESTS_ARMED_RED",
        "CHANGE_ADMITTED",
        ["AdmissionPolicyPassReceipt"],
        red_oracle={"compilation_success": False, "runtime_execution": "EXECUTED", "test_exit_code": 1},
    )
    red_not_exec = statemachine.evaluate_transition(
        ctx_red,
        "TESTS_ARMED_RED",
        "CHANGE_ADMITTED",
        ["AdmissionPolicyPassReceipt"],
        red_oracle={"compilation_success": True, "runtime_execution": "NOT_EXECUTED", "test_exit_code": 1},
    )
    red_premature_green = statemachine.evaluate_transition(
        ctx_red,
        "TESTS_ARMED_RED",
        "CHANGE_ADMITTED",
        ["AdmissionPolicyPassReceipt"],
        red_oracle={"compilation_success": True, "runtime_execution": "EXECUTED", "test_exit_code": 0},
    )
    red_valid = statemachine.evaluate_transition(
        ctx_red,
        "TESTS_ARMED_RED",
        "CHANGE_ADMITTED",
        ["AdmissionPolicyPassReceipt"],
        red_oracle={"compilation_success": True, "runtime_execution": "EXECUTED", "test_exit_code": 1},
    )
    results.append(("V12-05_compile_error_denied", red_compile_err["decision"] == "DENY"))
    results.append(("V12-05_not_executed_denied", red_not_exec["decision"] == "DENY"))
    results.append(("V12-05_premature_green_exit_0_denied", red_premature_green["decision"] == "DENY"))
    results.append(("V12-05_valid_triple_red_allowed", red_valid["decision"] == "ALLOW"))

    return all(ok for _, ok in results), dict(results)


def _test_pdp_and_admission(root):
    """Verify PDP & Admission Controller invariants (I-01, I-02, I-04, I-05, I-06, I-09, I-12)."""
    fixtures = canonical.strict_load_file(os.path.join(root, FIXTURES_REL))
    cases_by_schema = dict((c["schema"], c["valid"]) for c in fixtures["cases"])
    base_prop = copy.deepcopy(cases_by_schema["change_proposal.schema.json"])
    base_task = copy.deepcopy(cases_by_schema["task_envelope.schema.json"])
    valid_tok = copy.deepcopy(base_task["capability_token"])

    base_commit = base_prop["base"]["commit_sha"]
    base_tree = base_prop["base"]["tree_sha"]
    now_utc = "2026-10-20T10:15:00Z"

    valid_red = {
        "compilation_success": True,
        "runtime_execution": "EXECUTED",
        "test_exit_code": 1,
    }
    default_hints = {
        "blast_radius": "MODULE",
        "estimated_loc_delta": 80,
        "touches_auth_or_crypto": False,
        "touches_data_schema_or_migrations": False,
        "touches_public_api": False,
        "touches_build_ci_or_deps": False,
    }
    state_ctx = statemachine.initial_context(state="TESTS_ARMED_RED", risk_class="R1")
    prop_schema = canonical.strict_load_file(os.path.join(root, CHANGE_PROPOSAL_SCHEMA_REL))
    prop_validator = schema.Validator(prop_schema)

    results = []

    # 1. Valid baseline proposal admitted
    res_ok = pdp.evaluate_proposal_admission(
        proposal=base_prop,
        state_ctx=state_ctx,
        base_commit=base_commit,
        base_tree=base_tree,
        now_utc=now_utc,
        red_oracle=valid_red,
        capability_token=valid_tok,
        proposal_validator=prop_validator,
        risk_hints=default_hints,
    )
    results.append(("PDP_valid_proposal_allowed", res_ok["decision"] == "ALLOW"))

    # 2. I-01: Proposer claiming EXECUTOR role or embedding status denied
    p_i01 = copy.deepcopy(base_prop)
    p_i01["proposer"]["agent_role"] = "EXECUTOR"
    res_i01 = pdp.evaluate_proposal_admission(
        proposal=p_i01,
        state_ctx=state_ctx,
        base_commit=base_commit,
        base_tree=base_tree,
        now_utc=now_utc,
        red_oracle=valid_red,
        capability_token=valid_tok,
    )
    results.append(("I-01_privileged_role_impersonation_denied", res_i01["decision"] == "DENY" and res_i01["invariant_id"] == "I-01"))

    # 3. I-02: Expired capability token denied & Layer A writable grant denied
    tok_expired = copy.deepcopy(valid_tok)
    tok_expired["expires_at"] = "2026-10-20T10:05:00Z"
    res_i02_exp = pdp.evaluate_capability_token(tok_expired, "PROPOSE", "run_tests", ["src/app.py"], now_utc)
    tok_layer_a = copy.deepcopy(valid_tok)
    tok_layer_a["scopes"]["file_write"] = [".antigravity/policies/x.json"]
    res_i02_la = pdp.evaluate_capability_token(tok_layer_a, "PROPOSE", "run_tests", [".antigravity/policies/x.json"], now_utc)
    results.append(("I-02_expired_token_denied", res_i02_exp["decision"] == "DENY"))
    results.append(("I-02_layer_a_token_grant_denied", res_i02_la["decision"] == "DENY"))

    # 4. I-04: Base commit mismatch denied
    p_i04 = copy.deepcopy(base_prop)
    p_i04["base"]["commit_sha"] = "0" * 40
    res_i04 = pdp.evaluate_proposal_admission(
        proposal=p_i04,
        state_ctx=state_ctx,
        base_commit=base_commit,
        base_tree=base_tree,
        now_utc=now_utc,
        red_oracle=valid_red,
        capability_token=valid_tok,
    )
    results.append(("I-04_base_commit_mismatch_denied", res_i04["decision"] == "DENY" and res_i04["invariant_id"] == "I-04"))

    # 5. I-05: Undeclared Layer A modification denied; declared R4 with SSH-signed HUMAN allowed
    p_i05 = copy.deepcopy(base_prop)
    p_i05["changes"][0]["path"] = ".antigravity/policies/custom.json"
    p_i05["changes"][0]["layer"] = "A"
    p_i05["self_modification"] = False
    res_i05_undeclared = pdp.evaluate_proposal_admission(
        proposal=p_i05,
        state_ctx=state_ctx,
        base_commit=base_commit,
        base_tree=base_tree,
        now_utc=now_utc,
        red_oracle=valid_red,
    )
    p_i05_declared = copy.deepcopy(p_i05)
    p_i05_declared["self_modification"] = True
    p_i05_declared["risk_class_requested"] = "R4"
    res_i05_unsigned = pdp.evaluate_proposal_admission(
        proposal=p_i05_declared,
        state_ctx=state_ctx,
        base_commit=base_commit,
        base_tree=base_tree,
        now_utc=now_utc,
        red_oracle=valid_red,
        human_approval={"actor_kind": "HUMAN", "ssh_signed": False},
    )
    res_i05_signed = pdp.evaluate_proposal_admission(
        proposal=p_i05_declared,
        state_ctx=state_ctx,
        base_commit=base_commit,
        base_tree=base_tree,
        now_utc=now_utc,
        red_oracle=valid_red,
        human_approval={"actor_kind": "HUMAN", "ssh_signed": True},
    )
    results.append(("I-05_undeclared_layer_a_denied", res_i05_undeclared["decision"] == "DENY" and res_i05_undeclared["invariant_id"] == "I-05"))
    results.append(("I-05_unsigned_self_mod_denied", res_i05_unsigned["decision"] == "DENY" and res_i05_unsigned["invariant_id"] == "I-05"))
    results.append(("I-05_ssh_signed_self_mod_allowed", res_i05_signed["decision"] == "ALLOW"))

    # 6. I-06: Risk downgrade denied
    high_risk_hints = copy.deepcopy(default_hints)
    high_risk_hints["touches_auth_or_crypto"] = True
    res_i06 = pdp.evaluate_proposal_admission(
        proposal=base_prop,
        state_ctx=state_ctx,
        base_commit=base_commit,
        base_tree=base_tree,
        now_utc=now_utc,
        red_oracle=valid_red,
        capability_token=valid_tok,
        risk_hints=high_risk_hints,
    )
    results.append(("I-06_risk_downgrade_denied", res_i06["decision"] == "DENY" and res_i06["invariant_id"] == "I-06"))

    # 7. I-09: Empty rollback steps denied
    p_i09 = copy.deepcopy(base_prop)
    p_i09["rollback_plan"]["steps"] = []
    res_i09 = pdp.evaluate_proposal_admission(
        proposal=p_i09,
        state_ctx=state_ctx,
        base_commit=base_commit,
        base_tree=base_tree,
        now_utc=now_utc,
        red_oracle=valid_red,
    )
    results.append(("I-09_empty_rollback_steps_denied", res_i09["decision"] == "DENY" and res_i09["invariant_id"] == "I-09"))

    # 8. I-12: Secret leak in proposal rationale denied and flagged for quarantine
    # Constructed dynamically at runtime so source tree remains 100% secret-clean
    synthetic_token = "ghp_" + ("x" * 36)
    p_i12 = copy.deepcopy(base_prop)
    p_i12["rationale"] = "Injected token " + synthetic_token
    res_i12 = pdp.evaluate_proposal_admission(
        proposal=p_i12,
        state_ctx=state_ctx,
        base_commit=base_commit,
        base_tree=base_tree,
        now_utc=now_utc,
        red_oracle=valid_red,
    )
    results.append(("I-12_secret_in_proposal_denied_and_quarantined", res_i12["decision"] == "DENY" and res_i12["invariant_id"] == "I-12" and res_i12.get("quarantine_required") is True))

    return all(ok for _, ok in results), dict(results)


def _replay_live_journal(root):
    """Replay .antigravity/events/run-0000.jsonl through the compiled v1.2.0 guard engine."""
    validator = journal.load_validator(root)
    jpath = os.path.join(root, ".antigravity/events/run-0000.jsonl")
    entries, report = journal.verify_file(jpath, validator)
    if not report["valid"]:
        return False, {"error": "Journal verification failed", "details": report}

    ctx = statemachine.initial_context(
        state="TECH_RADAR_SYNC",
        risk_class="R0",
        genesis_approved=False,
    )
    replayed_transitions = []
    for entry in entries:
        etype = entry["event_type"]
        if etype == "GENESIS_BOOTSTRAP":
            if entry.get("payload", {}).get("decision") == "APPROVED":
                ctx["genesis_approved"] = True
        elif etype == "STATE_TRANSITION":
            tr = entry["transition"]
            ev_labels = []
            for item in tr.get("evidence_refs", []):
                if isinstance(item, dict) and "kind" in item:
                    ev_labels.append(item["kind"])
                elif isinstance(item, str):
                    ev_labels.append(item)
            is_ssh_signed = entry.get("signature", {}).get("alg") == "sshsig-ed25519"
            res = statemachine.evaluate_transition(
                state_ctx=ctx,
                from_state=tr["from_state"],
                to_state=tr["to_state"],
                evidence=ev_labels,
                actor_kind=entry["actor"]["kind"],
                retroactive=entry.get("retroactive", False),
                ssh_signed=is_ssh_signed,
            )
            if res["decision"] != "ALLOW":
                return False, {
                    "failed_seq": entry["seq"],
                    "transition": tr,
                    "reason": res["reason"],
                }
            ctx = res["next_state_ctx"]
            replayed_transitions.append(
                {
                    "seq": entry["seq"],
                    "guard_id": res["guard_id"],
                    "from_state": tr["from_state"],
                    "to_state": tr["to_state"],
                }
            )
    ok = ctx["current_state"] == "GENESIS_LOCKED" and len(replayed_transitions) >= 3
    return ok, {
        "final_state": ctx["current_state"],
        "transitions_verified": len(replayed_transitions),
        "replayed_transitions": replayed_transitions,
    }


def run(root):
    r = receipt.Receipt(root, "A5", "state_machine_and_pdp")

    # 1. Materialize declarative policy files & bundle lock
    transitions_doc = statemachine.build_transitions_policy()
    admission_doc = pdp.build_admission_policy()

    tr_hash, tr_bytes = _write_canonical_json(root, statemachine.TRANSITIONS_POLICY_PATH, transitions_doc)
    adm_hash, adm_bytes = _write_canonical_json(root, pdp.ADMISSION_POLICY_PATH, admission_doc)

    auth_lock = canonical.strict_load_file(os.path.join(root, AUTHORITY_LOCK_REL))
    gen_prop = canonical.strict_load_file(os.path.join(root, GENESIS_PROPOSAL_REL))

    bundle_lock = {
        "bundle_id": "urn:metaos:policy-bundle:1.2.0",
        "schema_version": "1.2.0",
        "base_authority_lock_sha256": canonical.jcs_hash(auth_lock),
        "genesis_bootstrap_proposal_id": gen_prop["proposal_id"],
        "genesis_bootstrap_proposal_sha256": canonical.jcs_hash(gen_prop),
        "applied_patches": transitions_doc["applied_patches"],
        "policies": {
            "transitions": {
                "policy_id": transitions_doc["policy_id"],
                "path": statemachine.TRANSITIONS_POLICY_PATH,
                "canonical_sha256": tr_hash,
                "bytes": tr_bytes,
                "state_count": len(transitions_doc["state_sets"]["ACTIVE_STATES"])
                + len(transitions_doc["state_sets"]["EXCEPTION_STATES"])
                + len(transitions_doc["state_sets"]["TERMINAL_STATES"]),
                "lifecycle_guard_count": len(transitions_doc["lifecycle_guards"]),
                "exception_guard_count": len(transitions_doc["exception_guards"]),
            },
            "admission_and_pdp": {
                "policy_id": admission_doc["policy_id"],
                "path": pdp.ADMISSION_POLICY_PATH,
                "canonical_sha256": adm_hash,
                "bytes": adm_bytes,
                "risk_classes": sorted(admission_doc["risk_classification_matrix"].keys()),
                "invariants_enforced_count": len(admission_doc["invariants_enforced"]),
            },
        },
    }
    bundle_hash, _ = _write_canonical_json(root, pdp.POLICY_BUNDLE_LOCK_PATH, bundle_lock)

    for rel in (
        statemachine.TRANSITIONS_POLICY_PATH,
        pdp.ADMISSION_POLICY_PATH,
        pdp.POLICY_BUNDLE_LOCK_PATH,
        ".antigravity/kernel/metaos/statemachine.py",
        ".antigravity/kernel/metaos/pdp.py",
        ".antigravity/kernel/metaos/phase_a5.py",
        "scripts/sm_transition",
        "scripts/pdp_eval",
    ):
        r.output(rel)

    expected_patches = [
        "C-1", "C-2", "C-3", "C-4", "C-5", "C-6", "C-7", "C-8",
        "V12-01", "V12-02", "V12-03", "V12-04", "V12-05", "V12-06",
    ]
    c01_ok = (
        transitions_doc["applied_patches"] == expected_patches
        and bundle_lock["policies"]["transitions"]["state_count"] == 29
    )
    r.check(
        "A5-C01",
        "v1.2.0 transitions policy, admission policy, and policy_bundle.lock.json materialized and bound to GBP-0000 (29 states, 14 patches)",
        c01_ok,
        {
            "invariant_id": "I-08",
            "transitions_sha256": tr_hash,
            "admission_sha256": adm_hash,
            "bundle_lock_sha256": bundle_hash,
            "applied_patches": transitions_doc["applied_patches"],
        },
    )

    # A5-C02: Happy path lifecycle simulation
    hp_ok, hp_msg, hp_guards = _run_happy_path_simulation()
    r.check(
        "A5-C02",
        "Full 22-step lifecycle happy-path simulation (TECH_RADAR_SYNC -> CLOSED) executes deterministically",
        hp_ok,
        {"invariant_id": "I-03", "summary": hp_msg, "guards_fired": hp_guards},
    )

    # A5-C03: C-1 & V12-06 regression tests
    c03_ok, c03_details = _test_c1_and_v12_06()
    r.check(
        "A5-C03",
        "C-1 & V12-06 regression suite: HUMAN_AUDIT_REQUIRED origin-scoped routing blocks gate bypass and post-quarantine merge",
        c03_ok,
        {"invariant_id": "I-10", "cases": c03_details},
    )

    # A5-C04: C-2 regression tests
    c04_ok, c04_details = _test_c2_evidence_incomplete()
    r.check(
        "A5-C04",
        "C-2 regression suite: pre-admission EVIDENCE_INCOMPLETE blocked from jumping to SANDBOX_EXECUTING; post-admission allowed",
        c04_ok,
        {"invariant_id": "I-08", "cases": c04_details},
    )

    # A5-C05: C-3..C-8 & V12-02 regression tests
    c05_ok, c05_details = _test_c3_to_c8_and_v12_02()
    r.check(
        "A5-C05",
        "C-3/V12-02, C-4, C-5, C-6, C-7, C-8 regression suite (Break-Glass realignment, exception preemption, rollback scoping, LC-04 dual evidence, retroactive lock, post-merge compensating action)",
        c05_ok,
        {"invariant_id": "I-09", "cases": c05_details},
    )

    # A5-C06: V12-01, V12-03, V12-04, V12-05 regression tests
    c06_ok, c06_details = _test_v12_01_03_04_05()
    r.check(
        "A5-C06",
        "V12-01, V12-03, V12-04, V12-05 regression suite (Handshake branches, polymorphic security/perf proof labels, drift loopback, and triple RED test oracle)",
        c06_ok,
        {"invariant_id": "I-13", "cases": c06_details},
    )

    # A5-C07: PDP & Admission Controller invariant tests
    c07_ok, c07_details = _test_pdp_and_admission(root)
    r.check(
        "A5-C07",
        "Policy Decision Point & Admission Controller enforces I-01, I-02, I-04, I-05, I-06, I-09, and I-12 fail-closed rules",
        c07_ok,
        {"invariant_id": "I-01", "cases": c07_details},
    )

    # A5-C08: Live journal replay through compiled v1.2.0 guard engine
    c08_ok, c08_details = _replay_live_journal(root)
    r.check(
        "A5-C08",
        "Live event journal (.antigravity/events/run-0000.jsonl, seq 0..6) replays cleanly through compiled v1.2.0 guard engine to GENESIS_LOCKED",
        c08_ok,
        {"invariant_id": "I-03", "replay": c08_details},
    )

    return r
