"""Phase A2 - Layer A kernel directory scaffold + capability re-baseline."""
import os
import shutil
import subprocess

from . import canonical, env, secrets
from .receipt import Receipt

KERNEL_DIRS = [
    ".antigravity/kernel",
    ".antigravity/policies",
    ".antigravity/events",
    ".antigravity/views",
    ".antigravity/outbox",
    ".antigravity/genesis",
    ".antigravity/schemas/core",
    "scripts",
]
KEEP_DIRS = [".antigravity/policies", ".antigravity/events", ".antigravity/views", ".antigravity/outbox"]
LAYER_B = ["contracts", "invariants", "src", "tests", "receipts", "provenance", "infra", "docs"]
GITIGNORE_RULES = [
    "# Meta-OS kernel hygiene (I-12): never commit secrets or local noise",
    ".DS_Store",
    "__pycache__/",
    "*.pyc",
    ".env",
    ".env.*",
    "*.pem",
    "*.key",
    "id_ed25519",
    "id_rsa",
    ".antigravity/keys/private/",
]
MANIFEST_PATH = ".antigravity/genesis/capability_manifest.json"
RECEIPT_PATH = ".antigravity/genesis/receipts/A2_kernel_scaffold.receipt.json"
PROBE_TOOLS = ["git", "python3", "jq", "sqlite3", "shasum", "ssh-keygen", "openssl", "node", "uv",
               "docker", "podman", "opa", "cosign", "syft", "gitleaks", "gh"]


def _version(tool):
    flags = {"ssh-keygen": None, "openssl": ["version"], "sqlite3": ["--version"]}
    args = flags.get(tool, ["--version"])
    if args is None:
        try:
            out = subprocess.run(["ssh", "-V"], capture_output=True, text=True, timeout=10)
            return (out.stderr or out.stdout).strip().splitlines()[0]
        except Exception:
            return None
    try:
        out = subprocess.run([tool] + args, capture_output=True, text=True, timeout=10)
        text = (out.stdout or out.stderr).strip()
        return text.splitlines()[0][:120] if text else None
    except Exception:
        return None


def capability_manifest(root):
    tools = {}
    for t in PROBE_TOOLS:
        path = shutil.which(t)
        tools[t] = {"present": bool(path), "version": _version(t) if path else None}
    tc_hash, tc = env.toolchain_snapshot()
    remote_raw = ""
    try:
        remote_raw = env.git(root, "remote", "get-url", "origin")
    except Exception:
        pass
    remote, had_cred = env.sanitize_remote(remote_raw)
    return {
        "manifest_type": "CapabilityManifest",
        "schema_version": "1.0.0",
        "substrate": "LOCAL_APFS_GIT",
        "toolchain": tc,
        "toolchain_digest": tc_hash,
        "tools": tools,
        "git": {"head": env.git_head(root), "remote_origin": remote or None,
                "remote_url_contains_credential": had_cred},
        "labels": {
            "ephemeral_container": "UNSUPPORTED" if not (tools["docker"]["present"] or tools["podman"]["present"]) else "AVAILABLE",
            "policy_engine_opa": "OPTIONAL_ABSENT" if not tools["opa"]["present"] else "AVAILABLE",
            "kernel_runtime": "python3-stdlib",
            "json_schema_validator": "kernel-subset (EXPERIMENTAL; full 2020-12 meta-validation pending)",
            "signatures": "sshsig-ed25519 via ssh-keygen -Y (keys provisioned at A7)",
        },
        "observations_from_blueprint_audit": {
            "agent_sandbox_network": "DENIED",
            "agent_sandbox_nested_sandbox_exec": "DENIED",
            "agent_workspace_write_scope": "FULL_WORKSPACE_SAME_OS_USER",
            "source": ".antigravity/genesis/blueprint/system_blueprint_v1.md",
        },
    }


def run(root):
    r = Receipt(root, "A2", "kernel_scaffold")
    present_b = [d for d in LAYER_B if os.path.exists(os.path.join(root, d))]
    if not r.check("A2-C01", "Layer B is absent (created only after kernel lock, spec 4.3)", not present_b,
                   {"present": present_b}):
        return r

    created = []
    for d in KERNEL_DIRS:
        p = os.path.join(root, d)
        if not os.path.isdir(p):
            os.makedirs(p)
            created.append(d)
    for d in KEEP_DIRS:
        keep = os.path.join(root, d, ".gitkeep")
        if not os.path.exists(keep):
            open(keep, "wb").close()

    gi = os.path.join(root, ".gitignore")
    existing = open(gi, encoding="utf-8").read().splitlines() if os.path.exists(gi) else []
    merged = existing + [ln for ln in GITIGNORE_RULES if ln not in existing]
    with open(gi, "wb") as fh:
        fh.write(canonical.canonical_text("\n".join(merged)).encode("utf-8"))

    r.check("A2-C02", "All Layer A kernel directories exist",
            all(os.path.isdir(os.path.join(root, d)) for d in KERNEL_DIRS),
            {"created": created, "required": KERNEL_DIRS})

    wrapper = os.path.join(root, "scripts", "metaos")
    r.check("A2-C03", "scripts/metaos wrapper present and executable",
            os.path.isfile(wrapper) and os.access(wrapper, os.X_OK))

    manifest = capability_manifest(root)
    secrets_hits = secrets.scan_obj(manifest)
    r.check("A2-C04", "Capability manifest contains no secret material (remote credential stripped)",
            not secrets_hits, {"pattern_classes": secrets_hits,
                               "remote_url_contains_credential": manifest["git"]["remote_url_contains_credential"]})
    if manifest["git"]["remote_url_contains_credential"]:
        r.note("SEC-0001 OPEN: git remote 'origin' embeds a credential in .git/config. Remote operations are "
               "fail-closed until the token is revoked and the remote URL is reset by the human owner.")
    with open(os.path.join(root, MANIFEST_PATH), "wb") as fh:
        fh.write(canonical.pretty_bytes(manifest))

    r.check("A2-C05", "Kernel runtime is real (git and python3 resolve to working binaries)",
            bool(manifest["tools"]["git"]["version"]) and bool(manifest["tools"]["python3"]["version"]),
            {"git": manifest["tools"]["git"]["version"], "python3": manifest["tools"]["python3"]["version"]})

    tree_hits = []
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
                tree_hits.append({"path": os.path.relpath(p, root), "classes": hits})
    r.check("A2-C06", "Working tree (excluding .git) contains no secret patterns", not tree_hits,
            {"findings": tree_hits})

    r.output(".gitignore")
    r.output(MANIFEST_PATH, {"jcs_sha256": canonical.jcs_hash(manifest)})
    r.output("scripts/metaos")
    for d in KEEP_DIRS:
        r.output(d + "/.gitkeep")
    return r
