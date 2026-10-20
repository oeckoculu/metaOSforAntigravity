"""Meta-OS v1.2.0 Deterministic State Machine & Guard Engine (Phase A5).

Compiles and enforces the v1.1.0 baseline state machine patched with the 14
user-approved Genesis patches (GBP-0000: C-1..C-8 and V12-01..V12-06).
All guard evaluations are pure, deterministic, and fail-closed (I-08).
"""
import os

from . import canonical

TRANSITIONS_POLICY_PATH = ".antigravity/policies/transitions.v1.2.0.json"

GENESIS_STATES = [
    "TECH_RADAR_SYNC",
    "CAPABILITY_BASELINED",
    "GENESIS_MORPHING",
    "GENESIS_LOCKED",
]

PRE_ADMISSION_STATES = [
    "INTENT_CAPTURED",
    "RISK_CLASSIFIED",
    "HANDSHAKE_PENDING",
    "CONTRACT_DRAFTING",
    "CONTRACT_REVIEWED",
    "CONTRACT_LOCKED",
    "TESTS_ARMED_RED",
]

POST_ADMISSION_PRE_MERGE_STATES = [
    "CHANGE_ADMITTED",
    "SANDBOX_EXECUTING",
    "WORKTREE_GREEN",
    "SECURITY_VERIFIED",
    "MUTATION_VERIFIED",
    "PERFORMANCE_VERIFIED",
    "PROOF_ASSEMBLED",
    "HUMAN_AUDIT_REQUIRED",
    "READY_TO_MERGE",
]

POST_MERGE_ACTIVE_STATES = [
    "MERGED",
    "POST_DEPLOY_OBSERVING",
]

EXCEPTION_STATES = [
    "BLOCKED_POLICY",
    "BUDGET_EXHAUSTED",
    "EVIDENCE_INCOMPLETE",
    "ROLLED_BACK",
    "QUARANTINED",
    "BREAK_GLASS_ACTIVE",
]

TERMINAL_STATES = [
    "CLOSED",
]

ACTIVE_STATES = (
    GENESIS_STATES
    + PRE_ADMISSION_STATES
    + POST_ADMISSION_PRE_MERGE_STATES
    + POST_MERGE_ACTIVE_STATES
)

ALL_STATES = sorted(set(ACTIVE_STATES + EXCEPTION_STATES + TERMINAL_STATES))

# C-4 deterministic exception precedence (1 = highest priority)
EXCEPTION_PRIORITY = {
    "BREAK_GLASS_ACTIVE": 1,
    "QUARANTINED": 2,
    "BLOCKED_POLICY": 3,
    "BUDGET_EXHAUSTED": 4,
    "EVIDENCE_INCOMPLETE": 5,
    "ROLLED_BACK": 6,
}


def build_transitions_policy():
    """Return the canonical declarative v1.2.0 transitions policy document."""
    doc = {
        "policy_type": "StateMachineTransitionsPolicy",
        "schema_version": "1.2.0",
        "policy_id": "urn:metaos:policy:transitions:1.2.0",
        "base_authority_version": "1.1.0",
        "applied_patches": [
            "C-1", "C-2", "C-3", "C-4", "C-5", "C-6", "C-7", "C-8",
            "V12-01", "V12-02", "V12-03", "V12-04", "V12-05", "V12-06",
        ],
        "initial_state": "TECH_RADAR_SYNC",
        "terminal_states": TERMINAL_STATES,
        "state_sets": {
            "GENESIS_STATES": GENESIS_STATES,
            "PRE_ADMISSION_STATES": PRE_ADMISSION_STATES,
            "POST_ADMISSION_PRE_MERGE_STATES": POST_ADMISSION_PRE_MERGE_STATES,
            "POST_MERGE_ACTIVE_STATES": POST_MERGE_ACTIVE_STATES,
            "ACTIVE_STATES": ACTIVE_STATES,
            "EXCEPTION_STATES": EXCEPTION_STATES,
            "TERMINAL_STATES": TERMINAL_STATES,
        },
        "exception_priority": EXCEPTION_PRIORITY,
        "lifecycle_guards": [
            {
                "guard_id": "LC-01",
                "from_state": "TECH_RADAR_SYNC",
                "to_state": "CAPABILITY_BASELINED",
                "all_of_evidence": ["TechRadarDelta", "CapabilityManifest"],
                "allow_retroactive": True,
            },
            {
                "guard_id": "LC-02",
                "from_state": "CAPABILITY_BASELINED",
                "to_state": "GENESIS_MORPHING",
                "all_of_evidence": ["ValidatedEnvironmentProfile"],
                "allow_retroactive": True,
            },
            {
                "guard_id": "LC-03",
                "from_state": "GENESIS_MORPHING",
                "to_state": "GENESIS_LOCKED",
                "all_of_evidence": ["UserApprovedProfile"],
                "required_actor_kinds": ["HUMAN"],
                "requires_genesis_bootstrap": True,
                "allow_retroactive": True,
            },
            {
                "guard_id": "LC-04",
                "patch_ref": "C-6",
                "from_state": "GENESIS_LOCKED",
                "to_state": "INTENT_CAPTURED",
                "all_of_evidence": ["InitializedWorkspace", "ValidatedIntentContract"],
                "allow_retroactive": False,
            },
            {
                "guard_id": "LC-05",
                "from_state": "INTENT_CAPTURED",
                "to_state": "RISK_CLASSIFIED",
                "all_of_evidence": ["RiskClassAssignment", "GateSchedule"],
                "allow_retroactive": False,
            },
            {
                "guard_id": "LC-06A",
                "from_state": "RISK_CLASSIFIED",
                "to_state": "HANDSHAKE_PENDING",
                "any_of_evidence_sets": [
                    ["CounterfactualHandshakeRequest"],
                    ["CounterfactualHandshakeResult"],
                ],
                "allow_retroactive": False,
            },
            {
                "guard_id": "LC-06B",
                "from_state": "RISK_CLASSIFIED",
                "to_state": "CONTRACT_DRAFTING",
                "all_of_evidence": ["ContractDraft"],
                "allowed_risk_classes": ["R0", "R1"],
                "allow_retroactive": False,
            },
            {
                "guard_id": "LC-07A",
                "patch_ref": "V12-01",
                "from_state": "HANDSHAKE_PENDING",
                "to_state": "CONTRACT_DRAFTING",
                "all_of_evidence": ["HumanApprovalReceipt"],
                "required_actor_kinds": ["HUMAN"],
                "allow_retroactive": False,
            },
            {
                "guard_id": "LC-07B",
                "patch_ref": "V12-01",
                "from_state": "HANDSHAKE_PENDING",
                "to_state": "CONTRACT_DRAFTING",
                "all_of_evidence": ["HandshakeRejectionReceipt"],
                "allow_retroactive": False,
            },
            {
                "guard_id": "LC-07C",
                "patch_ref": "V12-01",
                "from_state": "HANDSHAKE_PENDING",
                "to_state": "INTENT_CAPTURED",
                "all_of_evidence": ["HandshakeTimeoutReceipt"],
                "allow_retroactive": False,
            },
            {
                "guard_id": "LC-08",
                "from_state": "CONTRACT_DRAFTING",
                "to_state": "CONTRACT_REVIEWED",
                "all_of_evidence": ["ThreatModelReport", "ContractDiff"],
                "allow_retroactive": False,
            },
            {
                "guard_id": "LC-09",
                "from_state": "CONTRACT_REVIEWED",
                "to_state": "CONTRACT_LOCKED",
                "all_of_evidence": ["CanonicalSpecLockFile"],
                "allow_retroactive": False,
            },
            {
                "guard_id": "LC-10",
                "from_state": "CONTRACT_LOCKED",
                "to_state": "TESTS_ARMED_RED",
                "all_of_evidence": ["PropertyBasedTestSet", "GoldenCases"],
                "allow_retroactive": False,
            },
            {
                "guard_id": "LC-11",
                "patch_ref": "V12-05",
                "from_state": "TESTS_ARMED_RED",
                "to_state": "CHANGE_ADMITTED",
                "all_of_evidence": ["AdmissionPolicyPassReceipt"],
                "requires_triple_red_oracle": {
                    "CompilationSuccess": True,
                    "RuntimeExecution": "EXECUTED",
                    "TestExitCode_non_zero": True,
                    "zero_build_collection_infra_errors": True,
                    "min_failures": 1,
                },
                "allow_retroactive": False,
            },
            {
                "guard_id": "LC-12",
                "from_state": "CHANGE_ADMITTED",
                "to_state": "SANDBOX_EXECUTING",
                "all_of_evidence": ["EphemeralSandboxAllocation"],
                "required_actor_kinds": ["EXECUTOR", "KERNEL"],
                "allow_retroactive": False,
            },
            {
                "guard_id": "LC-13",
                "from_state": "SANDBOX_EXECUTING",
                "to_state": "WORKTREE_GREEN",
                "all_of_evidence": ["IsolatedWorktreeBuildSuccess"],
                "allow_retroactive": False,
            },
            {
                "guard_id": "LC-14",
                "patch_ref": "V12-03",
                "from_state": "WORKTREE_GREEN",
                "to_state": "SECURITY_VERIFIED",
                "all_of_evidence": ["ArchetypeSecurityScanProof"],
                "allow_retroactive": False,
            },
            {
                "guard_id": "LC-15",
                "from_state": "SECURITY_VERIFIED",
                "to_state": "MUTATION_VERIFIED",
                "all_of_evidence": ["MutationScorePass", "Non-SurvivingInvariants"],
                "allow_retroactive": False,
            },
            {
                "guard_id": "LC-16",
                "patch_ref": "V12-03",
                "from_state": "MUTATION_VERIFIED",
                "to_state": "PERFORMANCE_VERIFIED",
                "all_of_evidence": ["ArchetypePerformanceScanProof"],
                "allow_retroactive": False,
            },
            {
                "guard_id": "LC-17",
                "from_state": "PERFORMANCE_VERIFIED",
                "to_state": "PROOF_ASSEMBLED",
                "all_of_evidence": ["CompleteProofReceiptPackage"],
                "allow_retroactive": False,
            },
            {
                "guard_id": "LC-18A",
                "from_state": "PROOF_ASSEMBLED",
                "to_state": "HUMAN_AUDIT_REQUIRED",
                "all_of_evidence": ["CompleteProofReceiptPackage"],
                "sets_suspended_from": "PROOF_ASSEMBLED",
                "allow_retroactive": False,
            },
            {
                "guard_id": "LC-18B",
                "from_state": "PROOF_ASSEMBLED",
                "to_state": "READY_TO_MERGE",
                "all_of_evidence": ["AutomatedGatePass", "CompleteProofReceiptPackage"],
                "allowed_risk_classes": ["R0", "R1"],
                "forbid_self_modification": True,
                "allow_retroactive": False,
            },
            {
                "guard_id": "LC-19A",
                "patch_ref": "C-1",
                "from_state": "HUMAN_AUDIT_REQUIRED",
                "to_state": "READY_TO_MERGE",
                "required_suspended_from": ["PROOF_ASSEMBLED"],
                "forbid_quarantine_taint": True,
                "all_of_evidence": ["HumanApprovalToken", "CompleteProofReceiptPackage"],
                "required_actor_kinds": ["HUMAN"],
                "allow_retroactive": False,
            },
            {
                "guard_id": "LC-19B",
                "patch_ref": "C-1",
                "from_state": "HUMAN_AUDIT_REQUIRED",
                "to_state": "RESUME_TO_ORIGIN",
                "forbid_quarantine_taint": True,
                "all_of_evidence": ["HumanApprovalToken"],
                "required_actor_kinds": ["HUMAN"],
                "allow_retroactive": False,
            },
            {
                "guard_id": "LC-19C",
                "patch_ref": "V12-06",
                "from_state": "HUMAN_AUDIT_REQUIRED",
                "to_state": "INTENT_CAPTURED",
                "any_of_evidence_sets": [
                    ["HumanApprovalToken", "SanitizedAuditAttestation"],
                    ["RejectionRationale"],
                ],
                "required_actor_kinds": ["HUMAN"],
                "allow_retroactive": False,
            },
            {
                "guard_id": "LC-20",
                "from_state": "READY_TO_MERGE",
                "to_state": "MERGED",
                "all_of_evidence": ["GitMergeSuccess", "AppendOnlyEventRecord"],
                "required_actor_kinds": ["EXECUTOR"],
                "allow_retroactive": False,
            },
            {
                "guard_id": "LC-21",
                "from_state": "MERGED",
                "to_state": "POST_DEPLOY_OBSERVING",
                "all_of_evidence": ["CanaryDeploymentTelemetry"],
                "allow_retroactive": False,
            },
            {
                "guard_id": "LC-22A",
                "from_state": "POST_DEPLOY_OBSERVING",
                "to_state": "CLOSED",
                "all_of_evidence": ["StabilityReceipt", "FinalStateLock"],
                "allow_retroactive": False,
            },
            {
                "guard_id": "LC-22B",
                "patch_ref": "V12-04",
                "from_state": "POST_DEPLOY_OBSERVING",
                "to_state": "INTENT_CAPTURED",
                "all_of_evidence": ["DriftDetectionReport", "AutomatedPatchProposal"],
                "allow_retroactive": False,
            },
        ],
        "exception_guards": [
            {
                "guard_id": "EX-01",
                "patch_ref": "C-4",
                "from_state": "ANY_ACTIVE_OR_LOWER_EXCEPTION",
                "to_state": "BLOCKED_POLICY",
                "all_of_evidence": ["PolicyViolationRecord"],
                "preserves_suspended_from": True,
            },
            {
                "guard_id": "EX-02",
                "patch_ref": "C-1",
                "from_state": "BLOCKED_POLICY",
                "to_state": "HUMAN_AUDIT_REQUIRED",
                "all_of_evidence": ["PolicyExemptionReviewPacket"],
                "preserves_suspended_from": True,
            },
            {
                "guard_id": "EX-03",
                "patch_ref": "C-4",
                "from_state": "ANY_ACTIVE_OR_LOWER_EXCEPTION",
                "to_state": "BUDGET_EXHAUSTED",
                "all_of_evidence": ["BudgetBreachRecord"],
                "preserves_suspended_from": True,
            },
            {
                "guard_id": "EX-04",
                "patch_ref": "C-1",
                "from_state": "BUDGET_EXHAUSTED",
                "to_state": "HUMAN_AUDIT_REQUIRED",
                "all_of_evidence": ["BudgetIncrementAuthorization"],
                "preserves_suspended_from": True,
            },
            {
                "guard_id": "EX-05",
                "patch_ref": "C-2",
                "from_state": "ANY_ACTIVE_STATE",
                "to_state": "EVIDENCE_INCOMPLETE",
                "all_of_evidence": ["MissingEvidenceAuditReport"],
                "preserves_suspended_from": True,
            },
            {
                "guard_id": "EX-06A",
                "patch_ref": "C-2",
                "from_state": "EVIDENCE_INCOMPLETE",
                "to_state": "SANDBOX_EXECUTING",
                "required_suspended_from": POST_ADMISSION_PRE_MERGE_STATES,
                "all_of_evidence": ["RemediationTaskEnvelope"],
            },
            {
                "guard_id": "EX-06B",
                "patch_ref": "C-2",
                "from_state": "EVIDENCE_INCOMPLETE",
                "to_state": "RESUME_TO_PRE_ADMISSION_ORIGIN",
                "required_suspended_from": GENESIS_STATES + PRE_ADMISSION_STATES,
                "all_of_evidence": ["RemediationTaskEnvelope"],
            },
            {
                "guard_id": "EX-07A",
                "patch_ref": "C-8",
                "from_state": "PRE_MERGE_ACTIVE_STATES",
                "to_state": "ROLLED_BACK",
                "all_of_evidence": ["FailureRecord", "WorktreeCleanupReceipt"],
                "preserves_suspended_from": True,
            },
            {
                "guard_id": "EX-07B",
                "patch_ref": "C-8",
                "from_state": "POST_MERGE_ACTIVE_STATES",
                "to_state": "ROLLED_BACK",
                "all_of_evidence": ["FailureRecord", "CompensatingActionReceipt"],
                "preserves_suspended_from": True,
            },
            {
                "guard_id": "EX-08A",
                "patch_ref": "C-5",
                "from_state": "ROLLED_BACK",
                "to_state": "GENESIS_MORPHING",
                "required_suspended_from": GENESIS_STATES,
                "all_of_evidence": ["RevisedGenesisProfileRecord"],
            },
            {
                "guard_id": "EX-08B",
                "patch_ref": "C-5",
                "from_state": "ROLLED_BACK",
                "to_state": "INTENT_CAPTURED",
                "required_suspended_from": PRE_ADMISSION_STATES + POST_ADMISSION_PRE_MERGE_STATES + POST_MERGE_ACTIVE_STATES,
                "all_of_evidence": ["RevisedHypothesisRecord"],
            },
            {
                "guard_id": "EX-09",
                "patch_ref": "C-4",
                "from_state": "ANY_ACTIVE_OR_LOWER_EXCEPTION",
                "to_state": "QUARANTINED",
                "all_of_evidence": ["SecurityAnomalyReport"],
                "sets_quarantine_taint": True,
            },
            {
                "guard_id": "EX-10",
                "patch_ref": "V12-06",
                "from_state": "QUARANTINED",
                "to_state": "HUMAN_AUDIT_REQUIRED",
                "all_of_evidence": ["SanitizedAuditAttestation"],
                "keeps_quarantine_taint": True,
            },
            {
                "guard_id": "EX-11",
                "patch_ref": "I-15",
                "from_state": "ANY_NON_TERMINAL_STATE",
                "to_state": "BREAK_GLASS_ACTIVE",
                "all_of_evidence": ["CryptographicallySignedBreakGlassOverrideEvent"],
                "required_actor_kinds": ["HUMAN"],
                "requires_ssh_signature": True,
            },
            {
                "guard_id": "EX-12",
                "patch_ref": "C-3/V12-02",
                "from_state": "BREAK_GLASS_ACTIVE",
                "to_state": "GENESIS_LOCKED",
                "all_of_evidence": ["RealignmentProjectionReceipt", "CryptographicallySignedBreakGlassReviewRecord"],
                "required_actor_kinds": ["HUMAN"],
                "requires_ssh_signature": True,
            },
        ],
    }
    doc["content_hash"] = canonical.jcs_hash(doc)
    return doc


def initial_context(state="TECH_RADAR_SYNC", genesis_approved=True, risk_class="R1",
                    self_modification=False, suspended_from=None, quarantine_tainted=False):
    return {
        "current_state": state,
        "suspended_from": suspended_from,
        "quarantine_tainted": bool(quarantine_tainted),
        "genesis_approved": bool(genesis_approved),
        "risk_class": risk_class,
        "self_modification": bool(self_modification),
    }


def _deny(reason, patch_ref=None, invariant_id="I-08"):
    return {
        "allowed": False,
        "decision": "DENY",
        "guard_id": None,
        "patch_ref": patch_ref,
        "invariant_id": invariant_id,
        "reason": reason,
        "next_context": None,
        "next_state_ctx": None,
    }


def _allow(guard_id, next_ctx, patch_ref=None):
    return {
        "allowed": True,
        "decision": "ALLOW",
        "guard_id": guard_id,
        "patch_ref": patch_ref,
        "invariant_id": None,
        "reason": "GUARD_SATISFIED",
        "next_context": next_ctx,
        "next_state_ctx": next_ctx,
    }


def _has_all(provided, required):
    return all(r in provided for r in required)


def _check_triple_red_oracle(red_oracle):
    """V12-05: CompilationSuccess == True, RuntimeExecution == EXECUTED, TestExitCode != 0."""
    if not isinstance(red_oracle, dict):
        return False, "V12-05: missing red_oracle verification object"
    comp = red_oracle.get("CompilationSuccess") if "CompilationSuccess" in red_oracle else red_oracle.get("compilation_success")
    if comp is not True:
        return False, "V12-05: CompilationSuccess must be True (compile/syntax failure is not a valid RED test)"
    run_exec = red_oracle.get("RuntimeExecution") if "RuntimeExecution" in red_oracle else red_oracle.get("runtime_execution")
    if run_exec != "EXECUTED":
        return False, "V12-05: RuntimeExecution must equal 'EXECUTED'"
    exit_code = red_oracle.get("TestExitCode") if "TestExitCode" in red_oracle else red_oracle.get("test_exit_code")
    if isinstance(exit_code, bool) or not isinstance(exit_code, int) or exit_code == 0:
        return False, "V12-05: TestExitCode must be a non-zero integer"
    for err_field in ("collection_errors", "build_errors", "infrastructure_errors"):
        if red_oracle.get(err_field, 0) != 0:
            return False, "V12-05: %s must be 0" % err_field
    if red_oracle.get("failures", 1) < 1:
        return False, "V12-05: failures must be >= 1"
    return True, "OK"


def evaluate_transition(state_ctx=None, from_state=None, to_state=None, evidence=None,
                        actor_kind="KERNEL", retroactive=False, red_oracle=None,
                        ssh_signed=False, ctx=None, evidence_kinds=None):
    """Deterministically evaluate a requested state transition against v1.2.0 guards."""
    if ctx is not None and state_ctx is None:
        state_ctx = ctx
    if evidence_kinds is not None and evidence is None:
        evidence = evidence_kinds
    # Support 3-arg call (ctx, to_state, evidence_list)
    if isinstance(to_state, (list, tuple, set)) and evidence is None:
        evidence = to_state
        to_state = from_state
        from_state = None

    if not isinstance(state_ctx, dict):
        state_ctx = initial_context(state=from_state or "TECH_RADAR_SYNC")
    ctx = state_ctx

    ctx_from = ctx.get("current_state")
    if from_state is not None and ctx_from is not None and from_state != ctx_from:
        return _deny("State context mismatch: requested from_state=%r != current_state=%r" % (from_state, ctx_from))
    from_state = from_state or ctx_from
    suspended_from = ctx.get("suspended_from")
    quarantine_tainted = bool(ctx.get("quarantine_tainted", False))
    genesis_approved = bool(ctx.get("genesis_approved", False))
    risk_class = ctx.get("risk_class", "R1")
    self_mod = bool(ctx.get("self_modification", False))
    provided = set(evidence or [])

    if from_state not in ALL_STATES or to_state not in ALL_STATES:
        return _deny("Unknown state in transition %r -> %r" % (from_state, to_state))
    if from_state in TERMINAL_STATES:
        return _deny("Cannot transition out of terminal state %s" % from_state)

    # C-7: Retroactive transitions are only permitted during genesis (LC-01..LC-03)
    if retroactive and not (from_state in ("TECH_RADAR_SYNC", "CAPABILITY_BASELINED", "GENESIS_MORPHING")
                            and to_state in ("CAPABILITY_BASELINED", "GENESIS_MORPHING", "GENESIS_LOCKED")):
        return _deny("C-7: retroactive flag is forbidden outside genesis transitions LC-01..LC-03", patch_ref="C-7")

    next_ctx = dict(ctx)
    next_ctx["current_state"] = to_state

    # 1. Check incoming exception transitions (EX-01, EX-03, EX-05, EX-07A/B, EX-09, EX-11)
    if to_state == "BREAK_GLASS_ACTIVE":
        if actor_kind != "HUMAN":
            return _deny("I-15: BREAK_GLASS_ACTIVE requires HUMAN actor", patch_ref="I-15", invariant_id="I-15")
        if not ssh_signed:
            return _deny("I-15: BREAK_GLASS_ACTIVE requires cryptographic SSH signature", patch_ref="I-15", invariant_id="I-15")
        if not _has_all(provided, ["CryptographicallySignedBreakGlassOverrideEvent"]):
            return _deny("I-15: missing CryptographicallySignedBreakGlassOverrideEvent", patch_ref="I-15", invariant_id="I-15")
        if from_state in ACTIVE_STATES:
            next_ctx["suspended_from"] = from_state
        return _allow("EX-11", next_ctx, patch_ref="I-15")

    if to_state in ("QUARANTINED", "BLOCKED_POLICY", "BUDGET_EXHAUSTED", "EVIDENCE_INCOMPLETE", "ROLLED_BACK"):
        # C-4 exception preemption check when already in an exception state
        if from_state in EXCEPTION_STATES:
            curr_prio = EXCEPTION_PRIORITY[from_state]
            next_prio = EXCEPTION_PRIORITY[to_state]
            if next_prio >= curr_prio:
                return _deny(
                    "C-4: exception %s (priority %d) cannot preempt %s (priority %d)"
                    % (to_state, next_prio, from_state, curr_prio),
                    patch_ref="C-4",
                )
        origin = from_state if from_state in ACTIVE_STATES else suspended_from

        if to_state == "QUARANTINED":
            if not _has_all(provided, ["SecurityAnomalyReport"]):
                return _deny("EX-09: missing SecurityAnomalyReport", patch_ref="C-4")
            next_ctx["suspended_from"] = "QUARANTINED"
            next_ctx["quarantine_tainted"] = True
            return _allow("EX-09", next_ctx, patch_ref="C-4")

        if to_state == "BLOCKED_POLICY":
            if not _has_all(provided, ["PolicyViolationRecord"]):
                return _deny("EX-01: missing PolicyViolationRecord", patch_ref="C-4")
            next_ctx["suspended_from"] = origin
            return _allow("EX-01", next_ctx, patch_ref="C-4")

        if to_state == "BUDGET_EXHAUSTED":
            if not _has_all(provided, ["BudgetBreachRecord"]):
                return _deny("EX-03: missing BudgetBreachRecord", patch_ref="C-4")
            next_ctx["suspended_from"] = origin
            return _allow("EX-03", next_ctx, patch_ref="C-4")

        if to_state == "EVIDENCE_INCOMPLETE":
            if from_state not in ACTIVE_STATES:
                return _deny("C-2: EVIDENCE_INCOMPLETE can only be entered from an active state", patch_ref="C-2")
            if not _has_all(provided, ["MissingEvidenceAuditReport"]):
                return _deny("EX-05: missing MissingEvidenceAuditReport", patch_ref="C-2")
            next_ctx["suspended_from"] = from_state
            return _allow("EX-05", next_ctx, patch_ref="C-2")

        if to_state == "ROLLED_BACK":
            if from_state not in ACTIVE_STATES:
                return _deny("C-8: ROLLED_BACK can only be entered from an active state", patch_ref="C-8")
            if from_state in POST_MERGE_ACTIVE_STATES:
                if not _has_all(provided, ["FailureRecord", "CompensatingActionReceipt"]):
                    return _deny(
                        "C-8: post-merge rollback from %s requires FailureRecord & CompensatingActionReceipt (WorktreeCleanupReceipt is invalid post-merge)"
                        % from_state,
                        patch_ref="C-8",
                        invariant_id="I-09",
                    )
                next_ctx["suspended_from"] = from_state
                return _allow("EX-07B", next_ctx, patch_ref="C-8")
            if not _has_all(provided, ["FailureRecord", "WorktreeCleanupReceipt"]):
                return _deny("EX-07A: pre-merge rollback requires FailureRecord & WorktreeCleanupReceipt", patch_ref="C-8")
            next_ctx["suspended_from"] = from_state
            return _allow("EX-07A", next_ctx, patch_ref="C-8")

    # 2. Check recovery transitions out of EXCEPTION_STATES
    if from_state == "BREAK_GLASS_ACTIVE":
        if to_state != "GENESIS_LOCKED":
            return _deny("C-3/V12-02: BREAK_GLASS_ACTIVE can only recover to GENESIS_LOCKED", patch_ref="C-3/V12-02")
        if actor_kind != "HUMAN" or not ssh_signed:
            return _deny("C-3/V12-02: BREAK_GLASS_ACTIVE realignment requires signed HUMAN authorization", patch_ref="C-3/V12-02")
        if not _has_all(provided, ["RealignmentProjectionReceipt", "CryptographicallySignedBreakGlassReviewRecord"]):
            return _deny("C-3/V12-02: missing RealignmentProjectionReceipt & CryptographicallySignedBreakGlassReviewRecord", patch_ref="C-3/V12-02")
        next_ctx["suspended_from"] = None
        return _allow("EX-12", next_ctx, patch_ref="C-3/V12-02")

    if from_state == "QUARANTINED":
        if to_state != "HUMAN_AUDIT_REQUIRED":
            return _deny("V12-06: QUARANTINED must transition to HUMAN_AUDIT_REQUIRED first", patch_ref="V12-06")
        if not _has_all(provided, ["SanitizedAuditAttestation"]):
            return _deny("EX-10: missing SanitizedAuditAttestation", patch_ref="V12-06")
        next_ctx["suspended_from"] = "QUARANTINED"
        next_ctx["quarantine_tainted"] = True
        return _allow("EX-10", next_ctx, patch_ref="V12-06")

    if from_state == "BLOCKED_POLICY":
        if to_state != "HUMAN_AUDIT_REQUIRED":
            return _deny("C-1: BLOCKED_POLICY can only transition to HUMAN_AUDIT_REQUIRED", patch_ref="C-1")
        if not _has_all(provided, ["PolicyExemptionReviewPacket"]):
            return _deny("EX-02: missing PolicyExemptionReviewPacket", patch_ref="C-1")
        return _allow("EX-02", next_ctx, patch_ref="C-1")

    if from_state == "BUDGET_EXHAUSTED":
        if to_state != "HUMAN_AUDIT_REQUIRED":
            return _deny("C-1: BUDGET_EXHAUSTED can only transition to HUMAN_AUDIT_REQUIRED", patch_ref="C-1")
        if not _has_all(provided, ["BudgetIncrementAuthorization"]):
            return _deny("EX-04: missing BudgetIncrementAuthorization", patch_ref="C-1")
        return _allow("EX-04", next_ctx, patch_ref="C-1")

    if from_state == "EVIDENCE_INCOMPLETE":
        if not _has_all(provided, ["RemediationTaskEnvelope"]):
            return _deny("C-2: missing RemediationTaskEnvelope", patch_ref="C-2")
        if suspended_from in POST_ADMISSION_PRE_MERGE_STATES:
            if to_state != "SANDBOX_EXECUTING":
                return _deny("C-2: post-admission EVIDENCE_INCOMPLETE must remediate via SANDBOX_EXECUTING", patch_ref="C-2")
            next_ctx["suspended_from"] = None
            return _allow("EX-06A", next_ctx, patch_ref="C-2")
        if suspended_from in (GENESIS_STATES + PRE_ADMISSION_STATES):
            if to_state == "SANDBOX_EXECUTING":
                return _deny(
                    "C-2: pre-admission EVIDENCE_INCOMPLETE (from %s) cannot jump to SANDBOX_EXECUTING (would bypass RED test oracle & admission)"
                    % suspended_from,
                    patch_ref="C-2",
                )
            if to_state != suspended_from:
                return _deny("C-2: pre-admission EVIDENCE_INCOMPLETE must return to origin %s" % suspended_from, patch_ref="C-2")
            next_ctx["suspended_from"] = None
            return _allow("EX-06B", next_ctx, patch_ref="C-2")
        return _deny("C-2: EVIDENCE_INCOMPLETE has invalid or missing suspended_from %r" % (suspended_from,), patch_ref="C-2")

    if from_state == "ROLLED_BACK":
        if suspended_from in GENESIS_STATES:
            if to_state != "GENESIS_MORPHING":
                return _deny(
                    "C-5: rollback from genesis state %s must return to GENESIS_MORPHING, not %s"
                    % (suspended_from, to_state),
                    patch_ref="C-5",
                )
            if not _has_all(provided, ["RevisedGenesisProfileRecord"]):
                return _deny("EX-08A: missing RevisedGenesisProfileRecord", patch_ref="C-5")
            next_ctx["suspended_from"] = None
            return _allow("EX-08A", next_ctx, patch_ref="C-5")
        if to_state != "INTENT_CAPTURED":
            return _deny("EX-08B: post-genesis ROLLED_BACK must transition to INTENT_CAPTURED", patch_ref="C-5")
        if not _has_all(provided, ["RevisedHypothesisRecord"]):
            return _deny("EX-08B: missing RevisedHypothesisRecord", patch_ref="C-5")
        next_ctx["suspended_from"] = None
        return _allow("EX-08B", next_ctx, patch_ref="C-5")

    # 3. Check HUMAN_AUDIT_REQUIRED exits (C-1 & V12-06)
    if from_state == "HUMAN_AUDIT_REQUIRED":
        if actor_kind != "HUMAN":
            return _deny("HUMAN_AUDIT_REQUIRED exit requires HUMAN actor", patch_ref="C-1", invariant_id="I-06")
        if quarantine_tainted or suspended_from == "QUARANTINED":
            if to_state != "INTENT_CAPTURED":
                return _deny(
                    "V12-06: after QUARANTINED, direct merge or execution resume (%s) is forbidden; must return to INTENT_CAPTURED"
                    % to_state,
                    patch_ref="V12-06",
                    invariant_id="I-14",
                )
            if not _has_all(provided, ["HumanApprovalToken", "SanitizedAuditAttestation"]):
                return _deny("V12-06: post-quarantine return to INTENT_CAPTURED requires HumanApprovalToken & SanitizedAuditAttestation", patch_ref="V12-06")
            next_ctx["suspended_from"] = None
            next_ctx["quarantine_tainted"] = False
            return _allow("LC-19C", next_ctx, patch_ref="V12-06")

        if to_state == "READY_TO_MERGE":
            if suspended_from != "PROOF_ASSEMBLED":
                return _deny(
                    "C-1: HUMAN_AUDIT_REQUIRED -> READY_TO_MERGE denied because suspended_from=%r != 'PROOF_ASSEMBLED' (gate bypass blocked)"
                    % (suspended_from,),
                    patch_ref="C-1",
                    invariant_id="I-10",
                )
            if not _has_all(provided, ["HumanApprovalToken", "CompleteProofReceiptPackage"]):
                return _deny("C-1: READY_TO_MERGE requires both HumanApprovalToken & CompleteProofReceiptPackage", patch_ref="C-1", invariant_id="I-10")
            next_ctx["suspended_from"] = None
            return _allow("LC-19A", next_ctx, patch_ref="C-1")

        if to_state == "INTENT_CAPTURED":
            if not ("RejectionRationale" in provided or "HumanApprovalToken" in provided):
                return _deny("LC-19C: returning to INTENT_CAPTURED requires RejectionRationale or HumanApprovalToken", patch_ref="C-1")
            next_ctx["suspended_from"] = None
            return _allow("LC-19C", next_ctx, patch_ref="C-1")

        if suspended_from and to_state == suspended_from:
            if not _has_all(provided, ["HumanApprovalToken"]):
                return _deny("LC-19B: resuming to origin %s requires HumanApprovalToken" % suspended_from, patch_ref="C-1")
            next_ctx["suspended_from"] = None
            return _allow("LC-19B", next_ctx, patch_ref="C-1")

        return _deny(
            "C-1: illegal exit %s from HUMAN_AUDIT_REQUIRED (suspended_from=%r)"
            % (to_state, suspended_from),
            patch_ref="C-1",
        )

    # 4. Sequential Lifecycle Guards (LC-01..LC-22)
    if from_state == "TECH_RADAR_SYNC" and to_state == "CAPABILITY_BASELINED":
        if not _has_all(provided, ["TechRadarDelta", "CapabilityManifest"]):
            return _deny("LC-01: requires TechRadarDelta & CapabilityManifest")
        return _allow("LC-01", next_ctx)

    if from_state == "CAPABILITY_BASELINED" and to_state == "GENESIS_MORPHING":
        if not _has_all(provided, ["ValidatedEnvironmentProfile"]):
            return _deny("LC-02: requires ValidatedEnvironmentProfile")
        return _allow("LC-02", next_ctx)

    if from_state == "GENESIS_MORPHING" and to_state == "GENESIS_LOCKED":
        if not genesis_approved:
            return _deny("LC-03: requires approved GENESIS_BOOTSTRAP event")
        if actor_kind != "HUMAN":
            return _deny("LC-03: GENESIS_LOCKED requires HUMAN actor")
        if not _has_all(provided, ["UserApprovedProfile"]):
            return _deny("LC-03: requires UserApprovedProfile")
        return _allow("LC-03", next_ctx)

    if from_state == "GENESIS_LOCKED" and to_state == "INTENT_CAPTURED":
        if not _has_all(provided, ["InitializedWorkspace", "ValidatedIntentContract"]):
            return _deny("C-6/LC-04: requires BOTH InitializedWorkspace & ValidatedIntentContract", patch_ref="C-6")
        return _allow("LC-04", next_ctx, patch_ref="C-6")

    if from_state == "INTENT_CAPTURED" and to_state == "RISK_CLASSIFIED":
        if not _has_all(provided, ["RiskClassAssignment", "GateSchedule"]):
            return _deny("LC-05: requires RiskClassAssignment & GateSchedule")
        return _allow("LC-05", next_ctx)

    if from_state == "RISK_CLASSIFIED":
        if to_state == "HANDSHAKE_PENDING":
            if not ("CounterfactualHandshakeRequest" in provided or "CounterfactualHandshakeResult" in provided):
                return _deny("LC-06A: requires CounterfactualHandshakeRequest or CounterfactualHandshakeResult")
            return _allow("LC-06A", next_ctx)
        if to_state == "CONTRACT_DRAFTING":
            if risk_class not in ("R0", "R1") or self_mod:
                return _deny("I-06/LC-06B: risk_class %s or self-modification requires HANDSHAKE_PENDING" % risk_class, invariant_id="I-06")
            if not _has_all(provided, ["ContractDraft"]):
                return _deny("LC-06B: requires ContractDraft")
            return _allow("LC-06B", next_ctx)

    if from_state == "HANDSHAKE_PENDING":
        if to_state == "CONTRACT_DRAFTING":
            if "HumanApprovalReceipt" in provided:
                if actor_kind != "HUMAN":
                    return _deny("V12-01/LC-07A: HumanApprovalReceipt requires HUMAN actor", patch_ref="V12-01")
                return _allow("LC-07A", next_ctx, patch_ref="V12-01")
            if "HandshakeRejectionReceipt" in provided:
                return _allow("LC-07B", next_ctx, patch_ref="V12-01")
            return _deny("V12-01: HANDSHAKE_PENDING -> CONTRACT_DRAFTING requires HumanApprovalReceipt or HandshakeRejectionReceipt", patch_ref="V12-01")
        if to_state == "INTENT_CAPTURED":
            if not _has_all(provided, ["HandshakeTimeoutReceipt"]):
                return _deny("V12-01/LC-07C: HANDSHAKE_PENDING -> INTENT_CAPTURED requires HandshakeTimeoutReceipt", patch_ref="V12-01")
            return _allow("LC-07C", next_ctx, patch_ref="V12-01")

    if from_state == "CONTRACT_DRAFTING" and to_state == "CONTRACT_REVIEWED":
        if not _has_all(provided, ["ThreatModelReport", "ContractDiff"]):
            return _deny("LC-08: requires ThreatModelReport & ContractDiff")
        return _allow("LC-08", next_ctx)

    if from_state == "CONTRACT_REVIEWED" and to_state == "CONTRACT_LOCKED":
        if not _has_all(provided, ["CanonicalSpecLockFile"]):
            return _deny("LC-09: requires CanonicalSpecLockFile")
        return _allow("LC-09", next_ctx)

    if from_state == "CONTRACT_LOCKED" and to_state == "TESTS_ARMED_RED":
        if not _has_all(provided, ["PropertyBasedTestSet", "GoldenCases"]):
            return _deny("LC-10: requires PropertyBasedTestSet & GoldenCases")
        return _allow("LC-10", next_ctx)

    if from_state == "TESTS_ARMED_RED" and to_state == "CHANGE_ADMITTED":
        if not _has_all(provided, ["AdmissionPolicyPassReceipt"]):
            return _deny("V12-05/LC-11: requires AdmissionPolicyPassReceipt", patch_ref="V12-05")
        ok_red, reason_red = _check_triple_red_oracle(red_oracle)
        if not ok_red:
            return _deny(reason_red, patch_ref="V12-05", invariant_id="I-10")
        return _allow("LC-11", next_ctx, patch_ref="V12-05")

    if from_state == "CHANGE_ADMITTED" and to_state == "SANDBOX_EXECUTING":
        if actor_kind not in ("EXECUTOR", "KERNEL"):
            return _deny("I-01/LC-12: SANDBOX_EXECUTING allocation requires EXECUTOR or KERNEL actor", invariant_id="I-01")
        if not _has_all(provided, ["EphemeralSandboxAllocation"]):
            return _deny("LC-12: requires EphemeralSandboxAllocation")
        return _allow("LC-12", next_ctx)

    if from_state == "SANDBOX_EXECUTING" and to_state == "WORKTREE_GREEN":
        if not _has_all(provided, ["IsolatedWorktreeBuildSuccess"]):
            return _deny("LC-13: requires IsolatedWorktreeBuildSuccess")
        return _allow("LC-13", next_ctx)

    if from_state == "WORKTREE_GREEN" and to_state == "SECURITY_VERIFIED":
        if not _has_all(provided, ["ArchetypeSecurityScanProof"]):
            return _deny("V12-03/LC-14: requires polymorphic proof label ArchetypeSecurityScanProof", patch_ref="V12-03", invariant_id="I-13")
        return _allow("LC-14", next_ctx, patch_ref="V12-03")

    if from_state == "SECURITY_VERIFIED" and to_state == "MUTATION_VERIFIED":
        if not _has_all(provided, ["MutationScorePass", "Non-SurvivingInvariants"]):
            return _deny("LC-15: requires MutationScorePass & Non-SurvivingInvariants")
        return _allow("LC-15", next_ctx)

    if from_state == "MUTATION_VERIFIED" and to_state == "PERFORMANCE_VERIFIED":
        if not _has_all(provided, ["ArchetypePerformanceScanProof"]):
            return _deny("V12-03/LC-16: requires polymorphic proof label ArchetypePerformanceScanProof", patch_ref="V12-03", invariant_id="I-13")
        return _allow("LC-16", next_ctx, patch_ref="V12-03")

    if from_state == "PERFORMANCE_VERIFIED" and to_state == "PROOF_ASSEMBLED":
        if not _has_all(provided, ["CompleteProofReceiptPackage"]):
            return _deny("LC-17: requires CompleteProofReceiptPackage")
        return _allow("LC-17", next_ctx)

    if from_state == "PROOF_ASSEMBLED":
        if to_state == "HUMAN_AUDIT_REQUIRED":
            if not _has_all(provided, ["CompleteProofReceiptPackage"]):
                return _deny("LC-18A: requires CompleteProofReceiptPackage")
            next_ctx["suspended_from"] = "PROOF_ASSEMBLED"
            return _allow("LC-18A", next_ctx)
        if to_state == "READY_TO_MERGE":
            if self_mod or risk_class not in ("R0", "R1"):
                return _deny("I-05/I-06/LC-18B: risk_class %s or self-modification requires HUMAN_AUDIT_REQUIRED" % risk_class, invariant_id="I-06")
            if not _has_all(provided, ["AutomatedGatePass", "CompleteProofReceiptPackage"]):
                return _deny("LC-18B: requires AutomatedGatePass & CompleteProofReceiptPackage")
            return _allow("LC-18B", next_ctx)

    if from_state == "READY_TO_MERGE" and to_state == "MERGED":
        if actor_kind != "EXECUTOR":
            return _deny("I-01/LC-20: MERGED commit requires Privileged EXECUTOR actor", invariant_id="I-01")
        if not _has_all(provided, ["GitMergeSuccess", "AppendOnlyEventRecord"]):
            return _deny("LC-20: requires GitMergeSuccess & AppendOnlyEventRecord")
        return _allow("LC-20", next_ctx)

    if from_state == "MERGED" and to_state == "POST_DEPLOY_OBSERVING":
        if not _has_all(provided, ["CanaryDeploymentTelemetry"]):
            return _deny("LC-21: requires CanaryDeploymentTelemetry")
        return _allow("LC-21", next_ctx)

    if from_state == "POST_DEPLOY_OBSERVING":
        if to_state == "CLOSED":
            if not _has_all(provided, ["StabilityReceipt", "FinalStateLock"]):
                return _deny("LC-22A: requires StabilityReceipt & FinalStateLock")
            return _allow("LC-22A", next_ctx)
        if to_state == "INTENT_CAPTURED":
            if not _has_all(provided, ["DriftDetectionReport", "AutomatedPatchProposal"]):
                return _deny("V12-04/LC-22B: drift loopback requires DriftDetectionReport & AutomatedPatchProposal", patch_ref="V12-04", invariant_id="I-01")
            return _allow("LC-22B", next_ctx, patch_ref="V12-04")

    return _deny("Illegal state transition %s -> %s (no matching guard)" % (from_state, to_state))


def load_policy(root):
    return canonical.strict_load_file(os.path.join(root, TRANSITIONS_POLICY_PATH))
