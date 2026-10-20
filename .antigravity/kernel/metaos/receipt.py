"""Phase receipts: machine-readable, hash-sealed evidence of a kernel phase (I-10)."""
import os

from . import canonical, env


class Receipt(object):
    def __init__(self, root, phase, name):
        self.root = root
        self.phase = phase
        self.name = name
        self.checks = []
        self.outputs = []
        self.notes = []

    def check(self, cid, description, ok, detail=None):
        entry = {"id": cid, "description": description, "result": "PASS" if ok else "FAIL"}
        if detail is not None:
            entry["detail"] = detail
        self.checks.append(entry)
        return ok

    def output(self, rel_path, extra=None):
        p = os.path.join(self.root, rel_path)
        entry = {"path": rel_path, "sha256": canonical.file_sha256(p)}
        if extra:
            entry.update(extra)
        self.outputs.append(entry)

    def note(self, text):
        self.notes.append(text)

    @property
    def passed(self):
        return bool(self.checks) and all(c["result"] == "PASS" for c in self.checks)

    def build(self):
        k_hash, _ = env.kernel_digest(self.root)
        body = {
            "receipt_type": "PhaseReceipt",
            "schema_version": "1.0.0",
            "phase": self.phase,
            "name": self.name,
            "status": "PASS" if self.passed else "FAIL",
            "generated_at": env.utc_now(),
            "input": {"commit": env.git_head(self.root), "tree": env.git_tree(self.root)},
            "kernel": {"version": env.KERNEL_VERSION, "digest": k_hash},
            "reproducibility": env.reproducibility(self.root),
            "checks": self.checks,
            "outputs": sorted(self.outputs, key=lambda o: o["path"]),
            "notes": self.notes,
        }
        body["receipt_hash"] = canonical.jcs_hash(body)
        return body

    def write(self, rel_path):
        body = self.build()
        p = os.path.join(self.root, rel_path)
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, "wb") as fh:
            fh.write(canonical.pretty_bytes(body))
        return body


def verify_receipt_file(path):
    body = canonical.strict_load_file(path)
    claimed = body.pop("receipt_hash", None)
    return claimed is not None and claimed == canonical.jcs_hash(body), claimed
