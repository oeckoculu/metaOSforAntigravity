"""Meta-OS v1.2.0 Redaction Filter & UntrustedContentEnvelope Parser/Sanitizer (Phase A8).

Implements:
- Deterministic secret redaction across strings and nested JSON structures (I-12)
- UntrustedContentEnvelope parser, prompt-injection stripper, and cryptographic sealer (I-14)
"""
import copy
import os
import re
import unicodedata

from . import canonical, crypto, env, schema, secrets

ENVELOPE_SCHEMA_REL = ".antigravity/schemas/core/untrusted_content_envelope.schema.json"
SAMPLE_ENVELOPE_REL = ".antigravity/genesis/sample_untrusted_envelope.json"

INJECTION_PATTERNS = [
    ("IGNORE_PREVIOUS_INSTRUCTIONS", re.compile(r"ignore\s+(?:all\s+)?previous\s+instructions", re.IGNORECASE)),
    ("SYSTEM_OVERRIDE_DIRECTIVE", re.compile(r"system\s+override\s+bypass\s+invariants", re.IGNORECASE)),
    ("DISABLE_FAIL_CLOSED_KERNEL", re.compile(r"disable\s+fail-closed\s+kernel", re.IGNORECASE)),
    ("EXECUTE_SHELL_DIRECTIVE", re.compile(r"<\s*tool_call\s*>|run_command\s*\(", re.IGNORECASE)),
    ("ROLE_HIJACK_MARKER", re.compile(r"(?:^|\n)\s*(?:SYSTEM|DEVELOPER|KERNEL_OVERRIDE)\s*:", re.IGNORECASE)),
]


class EnvelopeError(Exception):
    pass


def load_validator(root):
    s = canonical.strict_load_file(os.path.join(root, ENVELOPE_SCHEMA_REL))
    return schema.Validator(s)


def redact_text(text):
    """Deterministically redact all secret patterns and prompt-injection directives from text."""
    if not isinstance(text, str):
        text = str(text)
    norm = unicodedata.normalize("NFC", text).replace("\r\n", "\n").replace("\r", "\n")

    matched_secrets = []
    secret_count = 0
    out = norm

    for name, rx in secrets.PATTERNS:
        matches = list(rx.finditer(out))
        if matches:
            secret_count += len(matches)
            if name not in matched_secrets:
                matched_secrets.append(name)
            out = rx.sub("[REDACTED:%s]" % name, out)

    matched_injections = []
    injection_count = 0
    for name, rx in INJECTION_PATTERNS:
        matches = list(rx.finditer(out))
        if matches:
            injection_count += len(matches)
            if name not in matched_injections:
                matched_injections.append(name)
            out = rx.sub("[STRIPPED_INJECTION:%s]" % name, out)

    return {
        "sanitized_text": out,
        "secrets_redacted_count": secret_count,
        "matched_secret_classes": sorted(matched_secrets),
        "prompt_injection_stripped_count": injection_count,
        "matched_injection_patterns": sorted(matched_injections),
        "quarantine_recommended": bool(secret_count > 0 or injection_count > 0),
        "redaction_profile": secrets.PROFILE,
    }


def redact_obj(obj):
    """Recursively redact secrets and prompt-injection directives in a JSON-compatible object."""
    matched_secrets = set()
    matched_injections = set()
    counts = {"secrets": 0, "injections": 0}

    def walk(v):
        if isinstance(v, str):
            res = redact_text(v)
            matched_secrets.update(res["matched_secret_classes"])
            matched_injections.update(res["matched_injection_patterns"])
            counts["secrets"] += res["secrets_redacted_count"]
            counts["injections"] += res["prompt_injection_stripped_count"]
            return res["sanitized_text"]
        if isinstance(v, list):
            return [walk(item) for item in v]
        if isinstance(v, dict):
            return dict((k, walk(val)) for k, val in v.items())
        return copy.deepcopy(v)

    sanitized = walk(obj)
    # Guarantee post-redaction object is 100% secret-free (I-12)
    secrets.assert_clean(sanitized)
    return {
        "sanitized": sanitized,
        "secrets_redacted_count": counts["secrets"],
        "matched_secret_classes": sorted(matched_secrets),
        "prompt_injection_stripped_count": counts["injections"],
        "matched_injection_patterns": sorted(matched_injections),
        "quarantine_recommended": bool(counts["secrets"] > 0 or counts["injections"] > 0),
        "redaction_profile": secrets.PROFILE,
    }


def wrap_untrusted_content(
    root,
    raw_text,
    source_kind,
    source_uri,
    retrieved_at=None,
    run_id="run-0000",
    envelope_id=None,
    extracted_claims=None,
    keystore_dir=None,
):
    """Parse, sanitize, and seal untrusted external content into an UntrustedContentEnvelope (I-12, I-14)."""
    if not isinstance(raw_text, str):
        raise EnvelopeError("I-14: raw_text must be a string")

    raw_bytes = raw_text.encode("utf-8")
    raw_hash = canonical.sha256_ref(raw_bytes)
    red = redact_text(raw_text)

    # Also sanitize any extracted claim statements
    clean_claims = []
    for idx, clm in enumerate(extracted_claims or [], start=1):
        stmt = clm.get("statement", "") if isinstance(clm, dict) else str(clm)
        stmt_red = redact_text(stmt)["sanitized_text"]
        clean_claims.append(
            {
                "claim_id": clm.get("claim_id", "CLM-%04d" % idx) if isinstance(clm, dict) else ("CLM-%04d" % idx),
                "statement": stmt_red,
                "evidence_status": "UNVERIFIED",
            }
        )

    doc = {
        "schema_version": "1.0.0",
        "envelope_id": envelope_id or env.uuid7(),
        "run_id": run_id,
        "source": {
            "kind": source_kind,
            "uri": source_uri,
            "retrieved_at": retrieved_at or env.utc_now(),
        },
        "trust_level": "UNTRUSTED_ENVELOPED",
        "executable_authority": "NONE_DATA_ONLY",
        "sanitization": {
            "redaction_profile": red["redaction_profile"],
            "secrets_redacted_count": red["secrets_redacted_count"],
            "matched_secret_classes": red["matched_secret_classes"],
            "prompt_injection_stripped_count": red["prompt_injection_stripped_count"],
            "matched_injection_patterns": red["matched_injection_patterns"],
            "quarantine_recommended": red["quarantine_recommended"],
        },
        "raw_sha256": raw_hash,
        "sanitized_text": red["sanitized_text"],
        "extracted_claims": clean_claims,
    }

    # Fail-closed check: sanitized envelope must contain zero residual secrets (I-12)
    secrets.assert_clean(doc)
    body_hash = canonical.jcs_hash(doc)
    doc["content_hash"] = body_hash

    if os.path.isfile(os.path.join(root, crypto.ALLOWED_SIGNERS_REL)):
        doc["signature"] = crypto.sign_bytes(
            data_bytes=body_hash.encode("utf-8"),
            principal_id="kernel:authority",
            namespace="metaos.kernel",
            root=root,
            keystore_dir=keystore_dir,
        )
    else:
        doc["signature"] = {"status": "UNSIGNED", "reason": "KEYS_NOT_PROVISIONED_UNTIL_A7"}

    validator = load_validator(root)
    errs = validator.errors(doc)
    if errs:
        raise EnvelopeError("UntrustedContentEnvelope failed schema validation: " + "; ".join("%s: %s" % e for e in errs))

    return doc


def verify_untrusted_envelope(root, envelope_doc):
    """Verify schema, content_hash, zero-secret guarantee, data-only authority, and kernel signature."""
    if not isinstance(envelope_doc, dict):
        return {"valid": False, "invariant_id": "I-14", "reason": "Envelope must be a JSON object"}

    validator = load_validator(root)
    errs = validator.errors(envelope_doc)
    if errs:
        return {
            "valid": False,
            "invariant_id": "I-14",
            "reason": "Schema validation failed: " + "; ".join("%s: %s" % e for e in errs),
        }

    if envelope_doc.get("trust_level") != "UNTRUSTED_ENVELOPED" or envelope_doc.get("executable_authority") != "NONE_DATA_ONLY":
        return {
            "valid": False,
            "invariant_id": "I-14",
            "reason": "I-14 violation: untrusted content cannot claim executable authority",
        }

    if secrets.scan_obj(envelope_doc):
        return {
            "valid": False,
            "invariant_id": "I-12",
            "reason": "I-12 violation: residual secret pattern present inside envelope",
        }

    for _, rx in INJECTION_PATTERNS:
        if rx.search(envelope_doc.get("sanitized_text", "")):
            return {
                "valid": False,
                "invariant_id": "I-14",
                "reason": "I-14 violation: unstripped prompt injection directive present in sanitized_text",
            }

    body = dict((k, v) for k, v in envelope_doc.items() if k not in ("content_hash", "signature"))
    expected_hash = canonical.jcs_hash(body)
    if envelope_doc.get("content_hash") != expected_hash:
        return {
            "valid": False,
            "invariant_id": "I-08",
            "reason": "content_hash mismatch (%r != %r)" % (envelope_doc.get("content_hash"), expected_hash),
        }

    sig = envelope_doc.get("signature", {})
    if sig.get("alg") == "sshsig-ed25519":
        ver = crypto.verify_signature(
            data_bytes=expected_hash.encode("utf-8"),
            sig_obj=sig,
            principal_id="kernel:authority",
            expected_namespace="metaos.kernel",
            root=root,
        )
        if not ver["valid"]:
            return {
                "valid": False,
                "invariant_id": "I-15",
                "reason": "Kernel signature verification failed: %s" % ver["reason"],
            }

    return {
        "valid": True,
        "invariant_id": "I-14",
        "envelope_id": envelope_doc["envelope_id"],
        "content_hash": expected_hash,
        "quarantine_recommended": envelope_doc["sanitization"]["quarantine_recommended"],
    }
