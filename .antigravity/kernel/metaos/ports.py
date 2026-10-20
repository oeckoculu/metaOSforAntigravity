"""Meta-OS v1.2.0 Abstract Provider Ports & Local Outbox Adapter (Phase A6).

Implements Invariant I-11 (Graceful Adapter Degradation & Transactional Outbox)
and Invariant I-12 (Zero-Secret Redaction Gate before Outbox/Journal emission).
"""
import os

from . import canonical, env, secrets

PROVIDER_PORTS_POLICY_PATH = ".antigravity/policies/provider_ports.v1.2.0.json"
OUTBOX_DIR_REL = ".antigravity/outbox"
OUTBOX_INDEX_REL = ".antigravity/outbox/index.json"

ALLOWED_OUTBOX_KINDS = (
    "HANDSHAKE_REVIEW",
    "HUMAN_AUDIT_REVIEW",
    "BREAK_GLASS_ALERT",
    "QUARANTINE_REVIEW",
    "DRIFT_ALERT",
    "POLICY_EXEMPTION_REVIEW",
    "BUDGET_INCREMENT_REVIEW",
    "GENESIS_NOTICE",
)

ALLOWED_DECISIONS = (
    "APPROVED",
    "REJECTED",
    "DEFERRED",
)


class OutboxError(Exception):
    pass


def build_provider_ports_policy():
    """Return the canonical declarative v1.2.0 abstract provider ports policy."""
    return {
        "policy_type": "ProviderPortsPolicy",
        "schema_version": "1.2.0",
        "policy_id": "urn:metaos:policy:provider_ports:1.2.0",
        "base_authority_version": "1.1.0",
        "invariants_enforced": ["I-02", "I-06", "I-08", "I-11", "I-12", "I-14"],
        "ports": {
            "HumanInteractionPort": {
                "port_id": "port.human.interaction",
                "requirement_level": "REQUIRED",
                "primary_adapter": "LocalOutboxHumanInteractionAdapter",
                "remote_adapters": ["github.issues", "atlassian.jira", "slack.webhook"],
                "fallback_mode": "TRANSACTIONAL_LOCAL_OUTBOX",
                "outbox_directory": OUTBOX_DIR_REL,
                "outbox_index": OUTBOX_INDEX_REL,
                "idempotency_hash_alg": "sha256-jcs",
                "allowed_kinds": list(ALLOWED_OUTBOX_KINDS),
                "allowed_decisions": list(ALLOWED_DECISIONS),
                "human_only_acknowledgement": True,
            },
            "ModelProviderPort": {
                "port_id": "port.model.provider",
                "requirement_level": "REQUIRED",
                "primary_adapter": "HostAgentModelAdapter",
                "pinning_requirement": "Immutable model_snapshot_ref in TaskEnvelope",
                "fallback_mode": "FAIL_CLOSED_ON_UNPINNED_SNAPSHOT",
            },
            "SandboxProviderPort": {
                "port_id": "port.sandbox.provider",
                "requirement_level": "REQUIRED",
                "primary_adapter": "LocalWorktreeSandboxAdapter",
                "container_status": "UNSUPPORTED_DEGRADED_TO_GIT_WORKTREE",
                "isolation_root": "/tmp/metaos-worktrees",
                "network_policy": "DEFAULT_DENY",
            },
            "SearchHorizonPort": {
                "port_id": "port.search.horizon",
                "requirement_level": "OPTIONAL",
                "primary_adapter": "HostWebSearchAdapter",
                "output_wrapping": "UntrustedContentEnvelope (I-14)",
                "fallback_mode": "OFFLINE_TECH_RADAR_CACHE",
            },
            "TelemetryPort": {
                "port_id": "port.telemetry.sink",
                "requirement_level": "REQUIRED",
                "primary_adapter": "LocalJournalTelemetryAdapter",
                "sink_path": ".antigravity/events/run-0000.jsonl",
                "fallback_mode": "LOCAL_APPEND_ONLY_JSONL",
            },
            "SecretBrokerPort": {
                "port_id": "port.secret.broker",
                "requirement_level": "REQUIRED",
                "primary_adapter": "FailClosedSecretBrokerAdapter",
                "secret_persistence": "FORBIDDEN_IN_REPO_OR_JOURNAL (I-12)",
                "redaction_profile": secrets.PROFILE,
            },
        },
    }


def _load_index(root):
    idx_path = os.path.join(root, OUTBOX_INDEX_REL)
    if not os.path.exists(idx_path):
        return {
            "document_type": "OutboxIndex",
            "schema_version": "1.0.0",
            "items": {},
        }
    return canonical.strict_load_file(idx_path)


def _save_index(root, idx_doc):
    idx_path = os.path.join(root, OUTBOX_INDEX_REL)
    os.makedirs(os.path.dirname(idx_path), exist_ok=True)
    idx_doc["content_hash"] = canonical.jcs_hash(
        {
            "document_type": idx_doc["document_type"],
            "schema_version": idx_doc["schema_version"],
            "items": idx_doc["items"],
        }
    )
    with open(idx_path, "wb") as fh:
        fh.write(canonical.pretty_bytes(idx_doc))


def _render_markdown(envelope):
    lines = [
        "# [%s] %s" % (envelope["kind"], envelope["title"]),
        "",
        "- **Outbox ID:** `%s`" % envelope["outbox_id"],
        "- **Run ID:** `%s`" % envelope["run_id"],
        "- **Status:** `%s`" % envelope["status"],
        "- **Idempotency Key:** `%s`" % envelope["idempotency_key"],
        "- **Created At:** `%s`" % envelope["created_at"],
        "- **Content Hash:** `%s`" % envelope["content_hash"],
        "",
        "## Summary",
        "",
        envelope["summary"],
        "",
        "## Action Instructions",
        "",
        "Acknowledge this outbox item via the deterministic CLI:",
        "",
        "```bash",
        "./scripts/outbox_ack --outbox-id %s --decision APPROVED --principal human:oeckoculu --rationale \"Reviewed and approved\""
        % envelope["outbox_id"],
        "```",
    ]
    return canonical.canonical_text("\n".join(lines))


def emit_outbox_item(
    root,
    kind,
    title,
    summary,
    payload=None,
    run_id="run-0000",
    idempotency_key=None,
    created_at=None,
):
    """Emit a deterministic, idempotent human interaction item to .antigravity/outbox/ (I-11, I-12)."""
    if kind not in ALLOWED_OUTBOX_KINDS:
        raise OutboxError("I-08/I-11: unsupported outbox kind %r" % (kind,))
    if not isinstance(title, str) or not title.strip():
        raise OutboxError("I-08/I-11: title must be a non-empty string")
    if not isinstance(summary, str) or not summary.strip():
        raise OutboxError("I-08/I-11: summary must be a non-empty string")
    if payload is None:
        payload = {}
    if not isinstance(payload, dict):
        raise OutboxError("I-08/I-11: payload must be a JSON object")

    # I-12: Fail-closed secret scan BEFORE any disk write
    secrets.assert_clean({"title": title, "summary": summary, "payload": payload})

    idem_seed = {
        "run_id": run_id,
        "kind": kind,
        "title": title,
        "payload": payload,
    }
    computed_idem = canonical.jcs_hash(idem_seed)
    effective_idem = idempotency_key or computed_idem
    if not isinstance(effective_idem, str) or not effective_idem.startswith("sha256:"):
        effective_idem = canonical.sha256_ref(str(effective_idem).encode("utf-8"))

    outbox_id = "OBX-" + effective_idem.split(":", 1)[1][:16]
    outbox_dir = os.path.join(root, OUTBOX_DIR_REL)
    os.makedirs(outbox_dir, exist_ok=True)

    json_rel = "%s/%s.json" % (OUTBOX_DIR_REL, outbox_id)
    md_rel = "%s/%s.md" % (OUTBOX_DIR_REL, outbox_id)
    json_abs = os.path.join(root, json_rel)
    md_abs = os.path.join(root, md_rel)

    if os.path.exists(json_abs):
        existing = canonical.strict_load_file(json_abs)
        if existing.get("idempotency_key") == effective_idem:
            return {
                "outbox_id": outbox_id,
                "idempotency_key": effective_idem,
                "deduplicated": True,
                "status": existing["status"],
                "json_path": json_rel,
                "markdown_path": md_rel,
                "content_hash": existing["content_hash"],
            }
        raise OutboxError("I-11: outbox_id collision with mismatched idempotency_key for %s" % outbox_id)

    ts = created_at or env.utc_now()
    envelope = {
        "document_type": "HumanOutboxItem",
        "schema_version": "1.0.0",
        "outbox_id": outbox_id,
        "run_id": run_id,
        "kind": kind,
        "status": "PENDING",
        "idempotency_key": effective_idem,
        "created_at": ts,
        "title": title,
        "summary": summary,
        "payload": payload,
        "acknowledgement": None,
        "redaction": {
            "profile": secrets.PROFILE,
            "result": "CLEAN",
        },
    }
    envelope["content_hash"] = canonical.jcs_hash(envelope)

    with open(json_abs, "wb") as fh:
        fh.write(canonical.pretty_bytes(envelope))
    with open(md_abs, "wb") as fh:
        fh.write(_render_markdown(envelope).encode("utf-8"))

    idx_doc = _load_index(root)
    idx_doc["items"][outbox_id] = {
        "outbox_id": outbox_id,
        "kind": kind,
        "status": "PENDING",
        "idempotency_key": effective_idem,
        "json_path": json_rel,
        "markdown_path": md_rel,
        "content_hash": envelope["content_hash"],
        "created_at": ts,
        "acknowledged_at": None,
        "decision": None,
    }
    _save_index(root, idx_doc)

    return {
        "outbox_id": outbox_id,
        "idempotency_key": effective_idem,
        "deduplicated": False,
        "status": "PENDING",
        "json_path": json_rel,
        "markdown_path": md_rel,
        "content_hash": envelope["content_hash"],
    }


def acknowledge_outbox_item(
    root,
    outbox_id,
    actor_principal,
    decision,
    rationale="",
    signature=None,
    acknowledged_at=None,
):
    """Record a HUMAN decision on a pending outbox item (I-06, I-11)."""
    if not isinstance(actor_principal, dict) or actor_principal.get("kind") != "HUMAN":
        return {
            "decision": "DENY",
            "invariant_id": "I-06",
            "reason": "I-06/I-11: only a HUMAN principal can acknowledge HumanInteractionPort outbox items (got %r)"
            % (actor_principal.get("kind") if isinstance(actor_principal, dict) else actor_principal,),
        }
    if decision not in ALLOWED_DECISIONS:
        return {
            "decision": "DENY",
            "invariant_id": "I-08",
            "reason": "I-08/I-11: invalid outbox decision %r (must be one of %r)" % (decision, ALLOWED_DECISIONS),
        }

    # I-12: scan rationale before persisting
    secrets.assert_clean({"rationale": rationale, "actor": actor_principal})

    json_rel = "%s/%s.json" % (OUTBOX_DIR_REL, outbox_id)
    json_abs = os.path.join(root, json_rel)
    if not os.path.exists(json_abs):
        return {
            "decision": "DENY",
            "invariant_id": "I-08",
            "reason": "I-08/I-11: outbox item %s does not exist" % outbox_id,
        }

    envelope = canonical.strict_load_file(json_abs)
    envelope.pop("content_hash", None)
    ack_ts = acknowledged_at or env.utc_now()
    envelope["status"] = "ACKNOWLEDGED"
    envelope["acknowledgement"] = {
        "actor": {
            "principal_id": actor_principal.get("principal_id", "human:unknown"),
            "kind": "HUMAN",
        },
        "decision": decision,
        "rationale": rationale,
        "acknowledged_at": ack_ts,
        "signature": signature or {
            "status": "UNSIGNED",
            "reason": "KEYS_NOT_PROVISIONED_UNTIL_A7",
        },
    }
    envelope["content_hash"] = canonical.jcs_hash(envelope)

    with open(json_abs, "wb") as fh:
        fh.write(canonical.pretty_bytes(envelope))

    idx_doc = _load_index(root)
    if outbox_id in idx_doc["items"]:
        idx_doc["items"][outbox_id]["status"] = "ACKNOWLEDGED"
        idx_doc["items"][outbox_id]["acknowledged_at"] = ack_ts
        idx_doc["items"][outbox_id]["decision"] = decision
        idx_doc["items"][outbox_id]["content_hash"] = envelope["content_hash"]
    _save_index(root, idx_doc)

    return {
        "decision": "ALLOW",
        "invariant_id": "I-11",
        "outbox_id": outbox_id,
        "status": "ACKNOWLEDGED",
        "human_decision": decision,
        "content_hash": envelope["content_hash"],
    }
