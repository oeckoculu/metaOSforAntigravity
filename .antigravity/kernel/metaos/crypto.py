"""Meta-OS v1.2.0 Cryptographic Signing (ssh-keygen -Y), CapabilityToken Issuer & Break-Glass Engine (Phase A7).

Implements:
- Ed25519 key provisioning with private keys strictly OUTSIDE the repository working tree (I-12)
- OpenSSH allowed_signers management & ssh-keygen -Y sign / verify (I-05, I-15)
- Short-lived, scope-bounded CapabilityToken issuance & cryptographic verification (I-02)
- Cryptographically signed BREAK_GLASS_OVERRIDE & Realignment Projection (I-15, C-3/V12-02)
"""
import copy
import datetime
import hashlib
import os
import subprocess
import tempfile

from . import canonical, env, pdp, secrets

KEYS_DIR_REL = ".antigravity/keys"
ALLOWED_SIGNERS_REL = ".antigravity/keys/allowed_signers"
KEYRING_MANIFEST_REL = ".antigravity/keys/keyring_manifest.json"
HUMAN_PUB_REL = ".antigravity/keys/human_owner.ed25519.pub"
KERNEL_PUB_REL = ".antigravity/keys/kernel_authority.ed25519.pub"
INITIAL_TOKEN_REL = ".antigravity/genesis/initial_capability_token.json"
BREAK_GLASS_OVERRIDE_REL = ".antigravity/genesis/break_glass_drill_override.json"
BREAK_GLASS_REVIEW_REL = ".antigravity/genesis/break_glass_review_record.json"
REALIGNMENT_RECEIPT_REL = ".antigravity/genesis/realignment_projection_receipt.json"

DEFAULT_EXTERNAL_KEYSTORE = "/tmp/metaos-keystore"

PRINCIPALS = {
    "human:oeckoculu": {
        "role": "HUMAN",
        "key_filename": "human_owner_ed25519",
        "pub_rel": HUMAN_PUB_REL,
        "namespaces": [
            "metaos.human",
            "metaos.breakglass",
            "metaos.proposal",
            "metaos.journal",
        ],
    },
    "kernel:authority": {
        "role": "KERNEL",
        "key_filename": "kernel_authority_ed25519",
        "pub_rel": KERNEL_PUB_REL,
        "namespaces": [
            "metaos.kernel",
            "metaos.token",
            "metaos.journal",
            "metaos.receipt",
        ],
    },
}

MAX_TOKEN_TTL_SECONDS = 3600
ALLOWED_TOKEN_ACTIONS = frozenset(["READ", "PROPOSE", "EXECUTE_TEST"])


class CryptoError(Exception):
    pass


def get_keystore_dir(keystore_dir=None):
    return os.path.abspath(keystore_dir or os.environ.get("METAOS_KEYSTORE_DIR", DEFAULT_EXTERNAL_KEYSTORE))


def _assert_outside_repo(root, keystore_dir):
    root_real = os.path.realpath(root)
    ks_real = os.path.realpath(keystore_dir)
    if ks_real == root_real or ks_real.startswith(root_real + os.sep):
        raise CryptoError(
            "I-12 violation: private keystore directory %s cannot reside inside repository root %s"
            % (ks_real, root_real)
        )


def _extract_fingerprint(pub_path):
    out = subprocess.run(
        ["ssh-keygen", "-lf", pub_path],
        check=True,
        capture_output=True,
        text=True,
        timeout=10,
    ).stdout.strip()
    # Format: "256 SHA256:xxxx comment (ED25519)"
    parts = out.split()
    if len(parts) < 2 or not parts[1].startswith("SHA256:"):
        raise CryptoError("Failed to parse ssh-keygen fingerprint from: %r" % (out,))
    return parts[1]


def init_keys(root, keystore_dir=None, force=False):
    """Provision Ed25519 keypairs outside the workspace and write public keys + allowed_signers in .antigravity/keys/."""
    ks_dir = get_keystore_dir(keystore_dir)
    _assert_outside_repo(root, ks_dir)
    os.makedirs(ks_dir, mode=0o700, exist_ok=True)

    keys_dir_abs = os.path.join(root, KEYS_DIR_REL)
    os.makedirs(keys_dir_abs, exist_ok=True)

    manifest_keys = {}
    allowed_lines = []

    for principal_id in sorted(PRINCIPALS.keys()):
        spec = PRINCIPALS[principal_id]
        priv_path = os.path.join(ks_dir, spec["key_filename"])
        pub_ext_path = priv_path + ".pub"
        pub_repo_abs = os.path.join(root, spec["pub_rel"])

        # If public key already exists in repo and private key exists in keystore (and not force), reuse it
        if not (os.path.isfile(priv_path) and os.path.isfile(pub_ext_path)) or force:
            for p in (priv_path, pub_ext_path):
                if os.path.exists(p):
                    os.unlink(p)
            subprocess.run(
                [
                    "ssh-keygen",
                    "-t",
                    "ed25519",
                    "-N",
                    "",
                    "-C",
                    principal_id,
                    "-f",
                    priv_path,
                ],
                check=True,
                capture_output=True,
                timeout=10,
            )
            os.chmod(priv_path, 0o600)

        pub_line = open(pub_ext_path, "r", encoding="utf-8").read().strip()
        with open(pub_repo_abs, "wb") as fh:
            fh.write(canonical.canonical_text(pub_line).encode("utf-8"))

        fp = _extract_fingerprint(pub_repo_abs)
        ns_csv = ",".join(spec["namespaces"])
        allowed_lines.append('%s namespaces="%s" %s' % (principal_id, ns_csv, pub_line))

        manifest_keys[principal_id] = {
            "principal_id": principal_id,
            "role": spec["role"],
            "alg": "sshsig-ed25519",
            "key_id": fp,
            "public_key_path": spec["pub_rel"],
            "public_key_sha256": canonical.file_sha256(pub_repo_abs),
            "allowed_namespaces": list(spec["namespaces"]),
        }

    allowed_abs = os.path.join(root, ALLOWED_SIGNERS_REL)
    with open(allowed_abs, "wb") as fh:
        fh.write(canonical.canonical_text("\n".join(allowed_lines)).encode("utf-8"))

    manifest = {
        "document_type": "KeyringManifest",
        "schema_version": "1.0.0",
        "allowed_signers_path": ALLOWED_SIGNERS_REL,
        "allowed_signers_sha256": canonical.file_sha256(allowed_abs),
        "private_keystore_isolation": "EXTERNAL_OUTSIDE_WORKSPACE_ONLY",
        "principals": manifest_keys,
    }
    manifest["content_hash"] = canonical.jcs_hash(manifest)
    manifest_abs = os.path.join(root, KEYRING_MANIFEST_REL)
    with open(manifest_abs, "wb") as fh:
        fh.write(canonical.pretty_bytes(manifest))

    return manifest


def sign_bytes(data_bytes, principal_id, namespace, root, keystore_dir=None):
    """Sign raw bytes using ssh-keygen -Y sign and return a canonical SshSignature object."""
    if principal_id not in PRINCIPALS:
        raise CryptoError("Unknown signing principal %r" % (principal_id,))
    spec = PRINCIPALS[principal_id]
    if namespace not in spec["namespaces"]:
        raise CryptoError(
            "Principal %s is not authorized to sign in namespace %r (allowed: %r)"
            % (principal_id, namespace, spec["namespaces"])
        )

    ks_dir = get_keystore_dir(keystore_dir)
    _assert_outside_repo(root, ks_dir)
    priv_path = os.path.join(ks_dir, spec["key_filename"])
    if not os.path.isfile(priv_path):
        raise CryptoError("Private key missing in external keystore for %s" % principal_id)

    manifest_abs = os.path.join(root, KEYRING_MANIFEST_REL)
    manifest = canonical.strict_load_file(manifest_abs)
    key_id = manifest["principals"][principal_id]["key_id"]

    proc = subprocess.run(
        ["ssh-keygen", "-Y", "sign", "-f", priv_path, "-n", namespace],
        input=data_bytes,
        check=True,
        capture_output=True,
        timeout=10,
    )
    sig_text = proc.stdout.decode("utf-8").strip()
    sig_obj = {
        "alg": "sshsig-ed25519",
        "key_id": key_id,
        "namespace": namespace,
        "sig": sig_text,
    }

    # Immediate self-verification against allowed_signers (fail-closed)
    ver = verify_signature(data_bytes, sig_obj, principal_id, namespace, root)
    if not ver["valid"]:
        raise CryptoError("Self-verification of generated signature failed: %s" % ver["reason"])
    return sig_obj


def verify_signature(data_bytes, sig_obj, principal_id, expected_namespace, root):
    """Verify an SshSignature object against .antigravity/keys/allowed_signers via ssh-keygen -Y verify."""
    if not isinstance(sig_obj, dict):
        return {"valid": False, "reason": "Signature must be a JSON object"}
    if sig_obj.get("alg") != "sshsig-ed25519":
        return {"valid": False, "reason": "Unsupported signature algorithm %r" % (sig_obj.get("alg"),)}
    if sig_obj.get("namespace") != expected_namespace:
        return {
            "valid": False,
            "reason": "Signature namespace mismatch (%r != %r)" % (sig_obj.get("namespace"), expected_namespace),
        }
    sig_armored = sig_obj.get("sig", "")
    key_id = sig_obj.get("key_id", "")
    if not sig_armored or not key_id.startswith("SHA256:"):
        return {"valid": False, "reason": "Missing sig or invalid key_id"}

    manifest_abs = os.path.join(root, KEYRING_MANIFEST_REL)
    allowed_abs = os.path.join(root, ALLOWED_SIGNERS_REL)
    if not os.path.isfile(manifest_abs) or not os.path.isfile(allowed_abs):
        return {"valid": False, "reason": "Keyring manifest or allowed_signers missing"}

    manifest = canonical.strict_load_file(manifest_abs)
    p_info = manifest.get("principals", {}).get(principal_id)
    if not p_info:
        return {"valid": False, "reason": "Principal %r not registered in keyring_manifest.json" % (principal_id,)}
    if p_info["key_id"] != key_id:
        return {
            "valid": False,
            "reason": "Key ID mismatch for %s (%s != %s)" % (principal_id, key_id, p_info["key_id"]),
        }
    if expected_namespace not in p_info.get("allowed_namespaces", []):
        return {
            "valid": False,
            "reason": "Namespace %r not permitted for principal %s" % (expected_namespace, principal_id),
        }

    fd, sig_file = tempfile.mkstemp(prefix="metaos-sig-", suffix=".sig")
    try:
        with os.fdopen(fd, "wb") as fh:
            fh.write((sig_armored.strip() + "\n").encode("utf-8"))
        proc = subprocess.run(
            [
                "ssh-keygen",
                "-Y",
                "verify",
                "-f",
                allowed_abs,
                "-I",
                principal_id,
                "-n",
                expected_namespace,
                "-s",
                sig_file,
            ],
            input=data_bytes,
            capture_output=True,
            timeout=10,
        )
        stdout = (proc.stdout or b"").decode("utf-8", errors="replace").strip()
        stderr = (proc.stderr or b"").decode("utf-8", errors="replace").strip()
        if proc.returncode != 0:
            return {
                "valid": False,
                "reason": "ssh-keygen -Y verify failed: %s" % (stderr or stdout or "non-zero exit"),
            }
        expected_marker = 'Good "%s" signature for %s' % (expected_namespace, principal_id)
        if expected_marker not in stdout or key_id not in stdout:
            return {
                "valid": False,
                "reason": "Unexpected verify output: %s" % stdout,
            }
        return {
            "valid": True,
            "principal_id": principal_id,
            "key_id": key_id,
            "namespace": expected_namespace,
            "verify_output": stdout,
            "reason": "VALID_SSHSIG_ED25519",
        }
    finally:
        if os.path.exists(sig_file):
            os.unlink(sig_file)


def _parse_iso_utc(ts_str):
    if not isinstance(ts_str, str) or not ts_str.endswith("Z"):
        raise CryptoError("Invalid UTC timestamp %r" % (ts_str,))
    return datetime.datetime.strptime(ts_str, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=datetime.timezone.utc)


def _format_iso_utc(dt):
    return dt.astimezone(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def token_signing_bytes(token_obj):
    """Return canonical JCS bytes of a CapabilityToken excluding issuer_signature."""
    unsigned = dict((k, v) for k, v in token_obj.items() if k != "issuer_signature")
    return canonical.jcs_bytes(unsigned)


def issue_capability_token(
    root,
    file_read,
    file_write,
    tools,
    actions,
    ttl_seconds=1800,
    issued_at=None,
    token_id=None,
    nonce=None,
    egress_allowlist=None,
    agent_role="BuilderAgent",
    keystore_dir=None,
):
    """Issue a short-lived, scope-bounded, cryptographically signed CapabilityToken (I-02)."""
    if not isinstance(ttl_seconds, int) or isinstance(ttl_seconds, bool) or ttl_seconds < 1 or ttl_seconds > MAX_TOKEN_TTL_SECONDS:
        raise CryptoError(
            "I-02: capability token ttl_seconds (%r) must be between 1 and %d seconds"
            % (ttl_seconds, MAX_TOKEN_TTL_SECONDS)
        )
    if not isinstance(actions, list) or not actions or not all(a in ALLOWED_TOKEN_ACTIONS for a in actions):
        raise CryptoError("I-02: actions must be a non-empty subset of %r" % (sorted(ALLOWED_TOKEN_ACTIONS),))
    if not isinstance(file_write, list):
        raise CryptoError("I-02: file_write must be a list")

    for wp in file_write:
        if not isinstance(wp, str) or not wp or wp.startswith("*") or ".." in wp or wp.startswith("/"):
            raise CryptoError("I-02: illegal wildcard, traversal, or absolute path in file_write: %r" % (wp,))
    layer_a_hits = pdp.touches_layer_a(file_write)
    if layer_a_hits:
        raise CryptoError("I-02: refusing to issue CapabilityToken granting write access to Layer A: %r" % (layer_a_hits,))

    if agent_role == "RedTeamVerifierAgent" and any(wp.startswith("src") for wp in file_write):
        raise CryptoError("I-02: RedTeamVerifierAgent is blind/isolated and forbidden from holding src/ write scopes")

    now_str = issued_at or env.utc_now()
    dt_issued = _parse_iso_utc(now_str)
    dt_expires = dt_issued + datetime.timedelta(seconds=ttl_seconds)
    expires_str = _format_iso_utc(dt_expires)

    tok_id = token_id or env.uuid7()
    tok_nonce = nonce or hashlib.sha256((tok_id + ":" + now_str).encode("utf-8")).hexdigest()[:32]

    token = {
        "token_id": tok_id,
        "issued_at": now_str,
        "expires_at": expires_str,
        "scopes": {
            "file_read": list(file_read or []),
            "file_write": list(file_write or []),
            "tools": list(tools or []),
            "actions": list(actions),
            "egress_allowlist": list(egress_allowlist or []),
        },
        "nonce": tok_nonce,
    }
    sig = sign_bytes(
        data_bytes=token_signing_bytes(token),
        principal_id="kernel:authority",
        namespace="metaos.token",
        root=root,
        keystore_dir=keystore_dir,
    )
    token["issuer_signature"] = sig
    return token


def verify_signed_capability_token(root, token, requested_action, requested_tool, target_paths, now_utc):
    """Verify both the cryptographic issuer_signature and I-02 scope/TTL constraints of a CapabilityToken."""
    if not isinstance(token, dict):
        return {"decision": "DENY", "invariant_id": "I-02", "reason": "I-02: token must be a JSON object"}
    sig = token.get("issuer_signature")
    ver = verify_signature(
        data_bytes=token_signing_bytes(token),
        sig_obj=sig,
        principal_id="kernel:authority",
        expected_namespace="metaos.token",
        root=root,
    )
    if not ver["valid"]:
        return {
            "decision": "DENY",
            "invariant_id": "I-02",
            "reason": "I-02: capability_token cryptographic signature invalid: %s" % ver["reason"],
        }
    return pdp.evaluate_capability_token(
        token=token,
        requested_action=requested_action,
        requested_tool=requested_tool,
        target_paths=target_paths,
        now_utc=now_utc,
    )
