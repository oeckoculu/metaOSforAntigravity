"""Environment, provenance and identity helpers (I-04 reproducibility)."""
import datetime
import os
import platform
import re
import secrets
import subprocess
import sys
import time

from . import canonical

KERNEL_VERSION = "0.1.0-genesis"


def utc_now():
    return datetime.datetime.now(datetime.timezone.utc).replace(microsecond=0).strftime("%Y-%m-%dT%H:%M:%SZ")


def uuid7():
    """RFC 9562 UUIDv7: 48-bit unix ms timestamp, version 7, variant 10."""
    ms = int(time.time() * 1000) & ((1 << 48) - 1)
    rand = secrets.randbits(74)
    rand_a = rand >> 62  # 12 bits
    rand_b = rand & ((1 << 62) - 1)
    value = (ms << 80) | (0x7 << 76) | (rand_a << 64) | (0b10 << 62) | rand_b
    h = "%032x" % value
    return "%s-%s-%s-%s-%s" % (h[0:8], h[8:12], h[12:16], h[16:20], h[20:32])


def git(root, *args):
    out = subprocess.run(["git", "-C", root] + list(args), capture_output=True, text=True)
    if out.returncode != 0:
        raise RuntimeError("git %s failed: %s" % (" ".join(args), out.stderr.strip()))
    return out.stdout.strip()


def git_head(root):
    try:
        return git(root, "rev-parse", "HEAD")
    except Exception:
        return None


def git_tree(root):
    try:
        return git(root, "rev-parse", "HEAD^{tree}")
    except Exception:
        return None


def git_is_clean(root):
    return git(root, "status", "--porcelain") == ""


_CRED_RE = re.compile(r"^(https?://)([^/@]+@)(.*)$")


def sanitize_remote(url):
    """Strip any userinfo (tokens) from a remote URL (I-12)."""
    m = _CRED_RE.match(url or "")
    if m:
        return m.group(1) + m.group(3), True
    return url, False


def _tool_version(cmd):
    try:
        out = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        return (out.stdout or out.stderr).strip().splitlines()[0]
    except Exception:
        return None


def kernel_digest(root):
    base = os.path.join(root, ".antigravity", "kernel")
    entries = []
    for dirpath, dirnames, filenames in os.walk(base):
        dirnames[:] = sorted(d for d in dirnames if d != "__pycache__")
        for fn in sorted(filenames):
            if fn.endswith(".pyc") or fn == ".DS_Store":
                continue
            p = os.path.join(dirpath, fn)
            rel = os.path.relpath(p, root).replace(os.sep, "/")
            entries.append({"path": rel, "sha256": canonical.file_sha256(p)})
    entries.sort(key=lambda e: e["path"])
    return canonical.jcs_hash(entries), entries


def toolchain_snapshot():
    exe = os.path.realpath(sys.executable)
    try:
        exe_hash = canonical.file_sha256(exe)
    except Exception:
        exe_hash = None
    snap = {
        "os": platform.system() + " " + platform.mac_ver()[0],
        "arch": platform.machine(),
        "python": {"version": platform.python_version(), "executable_sha256": exe_hash},
        "git": _tool_version(["git", "--version"]),
    }
    return canonical.jcs_hash(snap), snap


def reproducibility(root, test_seed=0, policy_version="invariants_and_states@1.1.0"):
    tc_hash, _ = toolchain_snapshot()
    return {
        "source_commit": git_head(root),
        "toolchain_digest": tc_hash,
        "lockfile_hash": None,
        "image_digest": None,
        "test_seed": test_seed,
        "model_snapshot": None,
        "policy_version": policy_version,
        "unavailable_reasons": {
            "lockfile_hash": "NO_THIRD_PARTY_DEPENDENCIES_STDLIB_ONLY",
            "image_digest": "NO_CONTAINER_RUNTIME_UNSUPPORTED",
            "model_snapshot": "DETERMINISTIC_KERNEL_STEP_NO_MODEL_INVOLVED",
        },
    }
