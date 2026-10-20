"""Meta-OS v1.2.0 Policy Decision Point (PDP) & Admission Controller (Phase A5).

Implements deterministic, fail-closed policy evaluation for:
- Risk Classification & Dynamic Gate Scheduling (I-06)
- Ephemeral Capability Token Verification (I-02)
- ChangeProposal Admission Control (I-01, I-02, I-04, I-05, I-06, I-08, I-09, I-10, I-12, V12-05)
"""
import os

from . import canonical, secrets, statemachine

ADMISSION_POLICY_PATH = ".antigravity/policies/admission_policy.v1.2.0.json"
POLICY_BUNDLE_LOCK_PATH = ".antigravity/policies/policy_bundle.lock.json"

PROTECTED_LAYER_A_PREFIXES = (
    ".antigravity/",
    ".agents/",
    "scripts/",
    ".git/",
    "SPEC_META_OS",
)

RISK_ORDER = {
    "R0": 0,
    "R1": 1,
    "R2": 2,
    "R3": 3,
    "R4": 4,
}


def build_admission_policy():
    """Return the canonical declarative v1.2.0 Admission & PDP policy document."""
    return {
        "policy_type": "AdmissionAndPdpPolicy",
        "schema_version": "1.2.0",
        "policy_id": "urn:metaos:policy:admission:1.2.0",
        "base_authority_version": "1.1.0",
        "default_decision": "DENY",
        "fail_closed_invariant": "I-08",
        "protected_layer_a_prefixes": list(PROTECTED_LAYER_A_PREFIXES),
        "risk_classification_matrix": {
            "R0": {
                "description": "Documentation, comments, or non-executable metadata only",
                "max_loc_delta": 50,
                "max_blast_radius": "ISOLATED_FILE",
                "counterfactual_handshake_required": False,
                "human_audit_required": False,
                "mutation_tier": "SKIP",
                "mutation_min_score_pct": 0,
                "rollback_proof_required": False,
                "ssh_signature_required": False,
                "required_gates": [
                    "G0_SCHEMA_AND_SECRET_SCAN",
                    "G1_TRIPLE_RED_ORACLE",
                    "G2_WORKTREE_BUILD_GREEN",
                    "G3_ARCHETYPE_SECURITY_SCAN",
                    "G5_ARCHETYPE_PERFORMANCE_SCAN",
                    "G6_PROOF_ASSEMBLY",
                ],
            },
            "R1": {
                "description": "Isolated module logic change without public API, schema, or auth impact",
                "max_loc_delta": 200,
                "max_blast_radius": "MODULE",
                "counterfactual_handshake_required": False,
                "human_audit_required": False,
                "mutation_tier": "FAST_DIFF",
                "mutation_min_score_pct": 70,
                "rollback_proof_required": True,
                "ssh_signature_required": False,
                "required_gates": [
                    "G0_SCHEMA_AND_SECRET_SCAN",
                    "G1_TRIPLE_RED_ORACLE",
                    "G2_WORKTREE_BUILD_GREEN",
                    "G3_ARCHETYPE_SECURITY_SCAN",
                    "G4_MUTATION_FAST_DIFF",
                    "G5_ARCHETYPE_PERFORMANCE_SCAN",
                    "G6_PROOF_ASSEMBLY",
                ],
            },
            "R2": {
                "description": "Service-level change, public API change, or build/dependency update",
                "max_loc_delta": 600,
                "max_blast_radius": "SERVICE",
                "counterfactual_handshake_required": True,
                "human_audit_required": True,
                "mutation_tier": "TARGETED_MODULE",
                "mutation_min_score_pct": 80,
                "rollback_proof_required": True,
                "ssh_signature_required": False,
                "required_gates": [
                    "G0_SCHEMA_AND_SECRET_SCAN",
                    "G0_COUNTERFACTUAL_HANDSHAKE",
                    "G1_TRIPLE_RED_ORACLE",
                    "G2_WORKTREE_BUILD_GREEN",
                    "G3_ARCHETYPE_SECURITY_SCAN",
                    "G4_MUTATION_TARGETED_MODULE",
                    "G5_ARCHETYPE_PERFORMANCE_SCAN",
                    "G6_PROOF_ASSEMBLY",
                    "G7_HUMAN_AUDIT",
                ],
            },
            "R3": {
                "description": "Cross-service, data schema/migration, or authentication/cryptography change",
                "max_loc_delta": 1500,
                "max_blast_radius": "CROSS_SERVICE",
                "counterfactual_handshake_required": True,
                "human_audit_required": True,
                "mutation_tier": "FULL_CRITICAL",
                "mutation_min_score_pct": 90,
                "rollback_proof_required": True,
                "ssh_signature_required": True,
                "required_gates": [
                    "G0_SCHEMA_AND_SECRET_SCAN",
                    "G0_COUNTERFACTUAL_HANDSHAKE",
                    "G1_TRIPLE_RED_ORACLE",
                    "G2_WORKTREE_BUILD_GREEN",
                    "G3_ARCHETYPE_SECURITY_SCAN",
                    "G4_MUTATION_FULL_CRITICAL",
                    "G5_ARCHETYPE_PERFORMANCE_SCAN",
                    "G6_PROOF_ASSEMBLY",
                    "G7_HUMAN_AUDIT_SSH_SIGNED",
                ],
            },
            "R4": {
                "description": "System-wide architectural change or Layer A / Layer B self-modification (I-05)",
                "max_loc_delta": 5000,
                "max_blast_radius": "SYSTEM_WIDE",
                "counterfactual_handshake_required": True,
                "human_audit_required": True,
                "mutation_tier": "FULL_CRITICAL",
                "mutation_min_score_pct": 95,
                "rollback_proof_required": True,
                "ssh_signature_required": True,
                "required_gates": [
                    "G0_SCHEMA_AND_SECRET_SCAN",
                    "G0_COUNTERFACTUAL_HANDSHAKE",
                    "G1_TRIPLE_RED_ORACLE",
                    "G2_WORKTREE_BUILD_GREEN",
                    "G3_ARCHETYPE_SECURITY_SCAN",
                    "G4_MUTATION_FULL_CRITICAL",
                    "G5_ARCHETYPE_PERFORMANCE_SCAN",
                    "G6_PROOF_ASSEMBLY",
                    "G7_HUMAN_AUDIT_SSH_SIGNED",
                    "G8_SELF_MODIFICATION_LOCK",
                ],
            },
        },
        "invariants_enforced": [
            {
                "invariant_id": "I-01",
                "rule": "Agents emit only pure data ChangeProposals; direct git commit/merge or state mutation by agent roles is forbidden.",
            },
            {
                "invariant_id": "I-02",
                "rule": "Task capability tokens are ephemeral, time-bounded, path-scoped, and strictly forbidden from granting write access to Layer A.",
            },
            {
                "invariant_id": "I-04",
                "rule": "ChangeProposal base_commit_hash and base_tree_hash must match the current repository HEAD commit and tree.",
            },
            {
                "invariant_id": "I-05",
                "rule": "Any modification touching Layer A/B paths requires self_modification=true, risk_class=R4, and SSH-signed HUMAN approval.",
            },
            {
                "invariant_id": "I-06",
                "rule": "Risk classification is deterministically computed from risk hints and blast radius; declared risk_class cannot downgrade computed risk.",
            },
            {
                "invariant_id": "I-08",
                "rule": "Fail-closed default DENY on any missing field, schema violation, unverified evidence, or ambiguous state.",
            },
            {
                "invariant_id": "I-09",
                "rule": "Every admitted ChangeProposal must include an executable rollback_plan with strategy and non-empty steps.",
            },
            {
                "invariant_id": "I-10",
                "rule": "Proposal admission requires TESTS_ARMED_RED state and the V12-05 triple RED test oracle (CompilationSuccess == true && RuntimeExecution == EXECUTED && TestExitCode != 0).",
            },
            {
                "invariant_id": "I-12",
                "rule": "Zero-secret policy: any secret token or private key pattern in proposal payloads triggers immediate DENY and QUARANTINED escalation.",
            },
        ],
    }


def touches_layer_a(paths):
    """Return list of paths that touch protected Layer A kernel directories/files."""
    violating = []
    for p in paths or []:
        if not isinstance(p, str):
            continue
        norm = p.lstrip("./")
        for prefix in PROTECTED_LAYER_A_PREFIXES:
            if norm.startswith(prefix) or p.startswith(prefix):
                violating.append(p)
                break
    return violating


def classify_risk_and_schedule(risk_hints, self_modification=False, layer_a_touched=False):
    """Deterministically compute risk_class (R0..R4) and gate schedule (I-06)."""
    if not isinstance(risk_hints, dict):
        risk_hints = {}

    blast = risk_hints.get("blast_radius", "MODULE")
    loc = risk_hints.get("estimated_loc_delta", 100)
    if not isinstance(loc, int) or isinstance(loc, bool):
        loc = 100

    auth_crypto = bool(risk_hints.get("touches_auth_or_crypto", False))
    schema_mig = bool(risk_hints.get("touches_data_schema_or_migrations", False))
    pub_api = bool(risk_hints.get("touches_public_api", False))
    build_deps = bool(risk_hints.get("touches_build_ci_or_deps", False))

    if self_modification or layer_a_touched or blast == "SYSTEM_WIDE" or loc > 1500:
        risk_class = "R4"
    elif auth_crypto or schema_mig or blast == "CROSS_SERVICE" or loc > 600:
        risk_class = "R3"
    elif pub_api or build_deps or blast == "SERVICE" or loc > 200:
        risk_class = "R2"
    elif blast == "MODULE" or loc > 50:
        risk_class = "R1"
    elif blast == "ISOLATED_FILE" and not (auth_crypto or schema_mig or pub_api or build_deps):
        risk_class = "R0"
    else:
        risk_class = "R1"

    policy = build_admission_policy()
    spec = policy["risk_classification_matrix"][risk_class]
    return {
        "risk_class": risk_class,
        "risk_rank": RISK_ORDER[risk_class],
        "counterfactual_handshake_required": spec["counterfactual_handshake_required"],
        "human_audit_required": spec["human_audit_required"],
        "mutation_tier": spec["mutation_tier"],
        "mutation_min_score_pct": spec["mutation_min_score_pct"],
        "rollback_proof_required": spec["rollback_proof_required"],
        "ssh_signature_required": spec["ssh_signature_required"],
        "required_gates": list(spec["required_gates"]),
    }


def _match_glob_prefix(target_path, pattern):
    """Deterministic prefix matcher supporting trailing /** or directory prefix."""
    if pattern.endswith("/**"):
        prefix = pattern[:-3].rstrip("/")
        return target_path == prefix or target_path.startswith(prefix + "/")
    if pattern.endswith("/"):
        return target_path.startswith(pattern)
    return target_path == pattern or target_path.startswith(pattern + "/")


def evaluate_capability_token(token, requested_action, requested_tool, target_paths, now_utc):
    """Verify an ephemeral TaskEnvelope capability token under Invariant I-02."""
    if not isinstance(token, dict):
        return {
            "decision": "DENY",
            "invariant_id": "I-02",
            "reason": "I-02: missing or invalid capability_token object",
        }
    for req_key in ("token_id", "issued_at", "expires_at"):
        if req_key not in token:
            return {
                "decision": "DENY",
                "invariant_id": "I-02",
                "reason": "I-02: capability_token missing required field %s" % req_key,
            }

    scopes = token.get("scopes", {})
    allowed_actions = token.get("allowed_actions") if "allowed_actions" in token else scopes.get("actions")
    allowed_tools = token.get("allowed_tools") if "allowed_tools" in token else scopes.get("tools")
    writable_paths = token.get("writable_paths") if "writable_paths" in token else scopes.get("file_write")

    if not isinstance(allowed_actions, list) or not isinstance(allowed_tools, list) or not isinstance(writable_paths, list):
        return {
            "decision": "DENY",
            "invariant_id": "I-02",
            "reason": "I-02: capability_token missing scopes (actions, tools, file_write)",
        }

    issued_at = token["issued_at"]
    expires_at = token["expires_at"]
    if not isinstance(now_utc, str) or not now_utc:
        return {
            "decision": "DENY",
            "invariant_id": "I-02",
            "reason": "I-02: missing evaluation timestamp now_utc",
        }
    if now_utc < issued_at:
        return {
            "decision": "DENY",
            "invariant_id": "I-02",
            "reason": "I-02: capability_token not yet valid (now_utc < issued_at)",
        }
    if now_utc > expires_at:
        return {
            "decision": "DENY",
            "invariant_id": "I-02",
            "reason": "I-02: capability_token expired (%s > %s)" % (now_utc, expires_at),
        }

    if requested_action not in allowed_actions:
        return {
            "decision": "DENY",
            "invariant_id": "I-02",
            "reason": "I-02: requested_action %r not in allowed_actions %r" % (requested_action, allowed_actions),
        }

    if requested_tool not in allowed_tools:
        return {
            "decision": "DENY",
            "invariant_id": "I-02",
            "reason": "I-02: requested_tool %r not in allowed_tools %r" % (requested_tool, allowed_tools),
        }

    for wp in writable_paths:
        if wp.startswith("*") or ".." in wp or wp.startswith("/"):
            return {
                "decision": "DENY",
                "invariant_id": "I-02",
                "reason": "I-02: illegal leading wildcard, traversal, or absolute path in writable_paths: %r" % (wp,),
            }
    layer_a_in_grant = touches_layer_a(writable_paths)
    if layer_a_in_grant:
        return {
            "decision": "DENY",
            "invariant_id": "I-02",
            "reason": "I-02: capability_token writable_paths illegally grant Layer A access: %r" % (layer_a_in_grant,),
        }

    if requested_action in ("WRITE", "PROPOSE", "EXECUTE"):
        if not isinstance(target_paths, list) or not target_paths:
            return {
                "decision": "DENY",
                "invariant_id": "I-02",
                "reason": "I-02: WRITE/PROPOSE/EXECUTE action requires explicit non-empty target_paths",
            }
        layer_a_targets = touches_layer_a(target_paths)
        if layer_a_targets:
            return {
                "decision": "DENY",
                "invariant_id": "I-02",
                "reason": "I-02: target_paths touch immutable Layer A paths: %r" % (layer_a_targets,),
            }
        for tp in target_paths:
            if "*" in tp or ".." in tp or tp.startswith("/"):
                return {
                    "decision": "DENY",
                    "invariant_id": "I-02",
                    "reason": "I-02: invalid target_path %r" % (tp,),
                }
            if requested_action in ("WRITE", "PROPOSE"):
                matched = any(_match_glob_prefix(tp, wp) for wp in writable_paths)
                if not matched:
                    return {
                        "decision": "DENY",
                        "invariant_id": "I-02",
                        "reason": "I-02: target_path %r is outside token writable_paths %r" % (tp, writable_paths),
                    }

    return {
        "decision": "ALLOW",
        "invariant_id": "I-02",
        "token_id": token["token_id"],
        "reason": "Capability token verified",
    }


def evaluate_proposal_admission(
    proposal,
    state_ctx,
    base_commit,
    base_tree,
    now_utc,
    red_oracle=None,
    capability_token=None,
    human_approval=None,
    proposal_validator=None,
    risk_hints=None,
):
    """Evaluate a ChangeProposal at the TESTS_ARMED_RED -> CHANGE_ADMITTED boundary."""
    if not isinstance(proposal, dict):
        return {
            "decision": "DENY",
            "invariant_id": "I-08",
            "patch_ref": None,
            "reason": "I-08: proposal must be a JSON object",
        }

    # 1. Secret scan (I-12) across proposal before any other processing
    try:
        canonical.jcs_bytes(proposal)
    except Exception as exc:
        return {
            "decision": "DENY",
            "invariant_id": "I-08",
            "patch_ref": None,
            "reason": "I-08: proposal failed canonical JCS serialization: %s" % exc,
        }

    secret_hits = secrets.scan_obj(proposal)
    if secret_hits:
        return {
            "decision": "DENY",
            "invariant_id": "I-12",
            "patch_ref": "C-4",
            "quarantine_required": True,
            "reason": "I-12: secret pattern detected in ChangeProposal (%s)" % ",".join(secret_hits),
        }

    # 2. Invariant I-01: Producer agent cannot impersonate Privileged Executor or pre-admit
    proposer = proposal.get("proposer") or proposal.get("producer_agent")
    if not isinstance(proposer, dict):
        return {
            "decision": "DENY",
            "invariant_id": "I-01",
            "patch_ref": None,
            "reason": "I-01: missing proposer metadata",
        }
    role = proposer.get("agent_role") or proposer.get("role", "")
    principal_kind = proposer.get("principal", {}).get("kind", "AGENT")
    if role in ("EXECUTOR", "PRIVILEGED_EXECUTOR", "KERNEL") or principal_kind in ("EXECUTOR", "KERNEL"):
        return {
            "decision": "DENY",
            "invariant_id": "I-01",
            "patch_ref": None,
            "reason": "I-01: proposer cannot claim privileged executor/kernel role (%r)" % (role or principal_kind,),
        }
    if proposal.get("direct_commit_attempt") is True or "status" in proposal:
        return {
            "decision": "DENY",
            "invariant_id": "I-01",
            "patch_ref": None,
            "reason": "I-01: ChangeProposal cannot embed admission status or direct commit flags",
        }

    # 3. Invariant I-04: Base commit & tree hash alignment
    base_obj = proposal.get("base") or {}
    prop_commit = base_obj.get("commit_sha") or proposal.get("base_commit_hash")
    prop_tree = base_obj.get("tree_sha") or proposal.get("base_tree_hash")
    if prop_commit != base_commit:
        return {
            "decision": "DENY",
            "invariant_id": "I-04",
            "patch_ref": None,
            "reason": "I-04: base commit mismatch (%r != %r)" % (prop_commit, base_commit),
        }
    if prop_tree != base_tree:
        return {
            "decision": "DENY",
            "invariant_id": "I-04",
            "patch_ref": None,
            "reason": "I-04: base tree mismatch (%r != %r)" % (prop_tree, base_tree),
        }

    # 4. Invariant I-09: Executable rollback plan verification
    rollback = proposal.get("rollback_plan")
    if not isinstance(rollback, dict):
        return {
            "decision": "DENY",
            "invariant_id": "I-09",
            "patch_ref": "C-8",
            "reason": "I-09: missing rollback_plan object",
        }
    strategy = rollback.get("strategy")
    steps = rollback.get("steps")
    if strategy not in ("WORKTREE_DISCARD", "GIT_REVERT", "COMPENSATING_ACTION"):
        return {
            "decision": "DENY",
            "invariant_id": "I-09",
            "patch_ref": "C-8",
            "reason": "I-09: invalid rollback_plan.strategy %r" % (strategy,),
        }
    if not isinstance(steps, list) or not steps or not all(isinstance(s, str) and s.strip() for s in steps):
        return {
            "decision": "DENY",
            "invariant_id": "I-09",
            "patch_ref": "C-8",
            "reason": "I-09: rollback_plan.steps must be a non-empty list of non-empty commands",
        }

    # 5. Affected files & Invariant I-05 (Self-Modification Governance)
    changes = proposal.get("changes") or proposal.get("affected_files")
    if not isinstance(changes, list) or not changes:
        return {
            "decision": "DENY",
            "invariant_id": "I-08",
            "patch_ref": None,
            "reason": "I-08: changes must be a non-empty list",
        }
    target_paths = [item.get("path", "") for item in changes if isinstance(item, dict)]
    layers_declared = [item.get("layer", "B") for item in changes if isinstance(item, dict)]
    layer_a_paths = touches_layer_a(target_paths)
    declared_self_mod = bool(proposal.get("self_modification", False))
    prop_kind = proposal.get("kind", "CODE")

    if (layer_a_paths or "A" in layers_declared or prop_kind in ("POLICY", "SCHEMA", "ARCHETYPE")) and not declared_self_mod:
        return {
            "decision": "DENY",
            "invariant_id": "I-05",
            "patch_ref": None,
            "reason": "I-05: proposal touches Layer A/policy/schema without self_modification=true",
        }

    declared_rc = proposal.get("risk_class_requested") or proposal.get("risk_class")
    if declared_self_mod or layer_a_paths or "A" in layers_declared:
        if declared_rc != "R4":
            return {
                "decision": "DENY",
                "invariant_id": "I-05",
                "patch_ref": None,
                "reason": "I-05: self-modification proposal must request risk_class_requested='R4'",
            }
        if not isinstance(human_approval, dict) or human_approval.get("actor_kind") != "HUMAN" or not human_approval.get("ssh_signed"):
            return {
                "decision": "DENY",
                "invariant_id": "I-05",
                "patch_ref": None,
                "reason": "I-05: self-modification requires explicit SSH-signed HUMAN approval token",
            }

    # 6. Optional JSON Schema validation (I-08)
    if proposal_validator is not None:
        errs = proposal_validator.errors(proposal)
        if errs:
            return {
                "decision": "DENY",
                "invariant_id": "I-08",
                "patch_ref": None,
                "reason": "I-08: ChangeProposal schema validation failed: %s" % "; ".join("%s: %s" % e for e in errs),
            }

    # 7. Invariant I-06: Risk classification alignment
    effective_hints = risk_hints or proposal.get("risk_hints") or {
        "blast_radius": "MODULE",
        "estimated_loc_delta": 80,
    }
    computed = classify_risk_and_schedule(
        effective_hints,
        self_modification=declared_self_mod,
        layer_a_touched=bool(layer_a_paths or "A" in layers_declared),
    )
    if declared_rc not in RISK_ORDER:
        return {
            "decision": "DENY",
            "invariant_id": "I-06",
            "patch_ref": None,
            "reason": "I-06: invalid declared risk_class_requested %r" % (declared_rc,),
        }
    if RISK_ORDER[declared_rc] < computed["risk_rank"]:
        return {
            "decision": "DENY",
            "invariant_id": "I-06",
            "patch_ref": None,
            "reason": "I-06: declared risk_class_requested %s is lower than computed minimum risk_class %s"
            % (declared_rc, computed["risk_class"]),
        }

    # 8. Invariant I-02: Capability Token check (if token supplied)
    if capability_token is not None:
        tok_res = evaluate_capability_token(
            token=capability_token,
            requested_action="PROPOSE",
            requested_tool="run_tests",
            target_paths=target_paths,
            now_utc=now_utc,
        )
        if tok_res["decision"] != "ALLOW":
            return {
                "decision": "DENY",
                "invariant_id": "I-02",
                "patch_ref": None,
                "reason": tok_res["reason"],
            }

    # 9. State Machine & Triple RED Test Oracle (V12-05 / I-10)
    if not isinstance(state_ctx, dict) or state_ctx.get("current_state") != "TESTS_ARMED_RED":
        return {
            "decision": "DENY",
            "invariant_id": "I-10",
            "patch_ref": "V12-05",
            "reason": "I-10/V12-05: ChangeProposal can only be admitted when state is TESTS_ARMED_RED (current=%r)"
            % (state_ctx.get("current_state") if isinstance(state_ctx, dict) else None,),
        }

    sm_res = statemachine.evaluate_transition(
        state_ctx=state_ctx,
        from_state="TESTS_ARMED_RED",
        to_state="CHANGE_ADMITTED",
        evidence=["AdmissionPolicyPassReceipt"],
        actor_kind="KERNEL",
        red_oracle=red_oracle,
    )
    if sm_res["decision"] != "ALLOW":
        return {
            "decision": "DENY",
            "invariant_id": sm_res.get("invariant_id") or "I-10",
            "patch_ref": sm_res.get("patch_ref") or "V12-05",
            "reason": sm_res["reason"],
        }

    return {
        "decision": "ALLOW",
        "invariant_id": "I-10",
        "patch_ref": "V12-05",
        "reason": "ChangeProposal admitted under v1.2.0 policy and triple RED oracle",
        "proposal_id": proposal.get("proposal_id"),
        "declared_risk_class": declared_rc,
        "computed_risk_class": computed["risk_class"],
        "gate_schedule": computed,
        "receipt_type": "AdmissionPolicyPassReceipt",
        "next_state_ctx": sm_res["next_state_ctx"],
    }


def load_policy(root):
    return canonical.strict_load_file(os.path.join(root, ADMISSION_POLICY_PATH))
