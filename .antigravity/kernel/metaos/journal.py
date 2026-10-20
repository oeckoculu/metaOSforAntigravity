"""Append-only, hash-chained event journal (I-03) with fail-closed admission."""
import os

from . import canonical, env, secrets
from .schema import Validator

SCHEMA_PATH = ".antigravity/schemas/core/event_journal_entry.schema.json"
UNSIGNED = {"status": "UNSIGNED", "reason": "KEYS_NOT_PROVISIONED_UNTIL_A7"}


class JournalError(Exception):
    pass


def entry_hash(entry):
    body = dict((k, v) for k, v in entry.items() if k not in ("entry_hash", "signature"))
    return canonical.jcs_hash(body)


def load_validator(root):
    return Validator(canonical.strict_load_file(os.path.join(root, SCHEMA_PATH)))


def semantic_errors(entry):
    errs = []
    rep = entry.get("reproducibility", {})
    reasons = rep.get("unavailable_reasons", {})
    for field in ("source_commit", "toolchain_digest", "lockfile_hash", "image_digest", "model_snapshot"):
        if rep.get(field) is None and field not in reasons:
            errs.append("reproducibility.%s is null without unavailable_reasons entry (I-04)" % field)
    for field in reasons:
        if rep.get(field) is not None:
            errs.append("unavailable_reasons.%s given for a present value" % field)
    return errs


def build_entry(validator, seq, run_id, prev_hash, event_type, actor, payload, reproducibility,
                transition=None, retroactive=False, occurred_at=None, parent_run_id=None, ts=None):
    entry = {
        "schema_version": "1.0.0",
        "seq": seq,
        "event_id": env.uuid7(),
        "run_id": run_id,
        "parent_run_id": parent_run_id,
        "ts": ts or env.utc_now(),
        "occurred_at": occurred_at,
        "retroactive": retroactive,
        "event_type": event_type,
        "actor": actor,
        "transition": transition,
        "payload": payload,
        "reproducibility": reproducibility,
        "redaction": {"profile": secrets.PROFILE, "result": "CLEAN"},
        "prev_hash": prev_hash,
    }
    secrets.assert_clean(entry)  # I-12: reject before anything touches disk
    entry["entry_hash"] = entry_hash(entry)
    entry["signature"] = dict(UNSIGNED)
    errs = ["%s: %s" % e for e in validator.errors(entry)] + semantic_errors(entry)
    if errs:
        raise JournalError("entry rejected by schema/semantics: " + "; ".join(errs[:6]))
    return entry


def read_lines(path):
    if not os.path.exists(path):
        return []
    with open(path, "rb") as fh:
        data = fh.read()
    if data and not data.endswith(b"\n"):
        raise JournalError("journal does not end with newline (torn write?)")
    return [ln for ln in data.split(b"\n")[:-1]] if data else []


def verify_lines(lines, validator):
    """Return (entries, report). Fail-closed: any anomaly is an error."""
    errors = []
    entries = []
    prev = canonical.ZERO_HASH
    run_id = None
    unsigned = 0
    for idx, raw in enumerate(lines):
        try:
            e = canonical.strict_loads(raw.decode("utf-8"))
        except Exception as ex:
            errors.append("line %d: parse error %s" % (idx, ex))
            break
        if canonical.jcs_bytes(e) != raw:
            errors.append("line %d: not in canonical JCS form" % idx)
        for path, msg in validator.errors(e):
            errors.append("line %d: schema %s %s" % (idx, path, msg))
        errors.extend("line %d: %s" % (idx, m) for m in semantic_errors(e))
        if e.get("seq") != idx:
            errors.append("line %d: seq %r breaks contiguity" % (idx, e.get("seq")))
        if e.get("prev_hash") != prev:
            errors.append("line %d: prev_hash does not chain to previous entry" % idx)
        if e.get("entry_hash") != entry_hash(e):
            errors.append("line %d: entry_hash mismatch (tampered content)" % idx)
        if run_id is None:
            run_id = e.get("run_id")
        elif e.get("run_id") != run_id:
            errors.append("line %d: run_id changes inside journal" % idx)
        if secrets.scan_obj(e):
            errors.append("line %d: secret pattern present" % idx)
        if e.get("signature", {}).get("status") == "UNSIGNED":
            unsigned += 1
        prev = e.get("entry_hash")
        entries.append(e)
    report = {
        "entries": len(entries),
        "head_seq": len(entries) - 1 if entries else None,
        "head_hash": prev if entries else None,
        "run_id": run_id,
        "unsigned_entries": unsigned,
        "valid": not errors,
        "errors": errors,
    }
    return entries, report


def verify_file(path, validator):
    try:
        lines = read_lines(path)
    except JournalError as ex:
        return [], {"valid": False, "errors": [str(ex)], "entries": 0}
    return verify_lines(lines, validator)


def append(path, entry, validator):
    """Append one entry with O_APPEND after re-verifying the existing chain."""
    entries, report = verify_file(path, validator)
    if not report["valid"]:
        raise JournalError("refusing to append to invalid journal: " + "; ".join(report["errors"][:3]))
    expected_seq = len(entries)
    expected_prev = entries[-1]["entry_hash"] if entries else canonical.ZERO_HASH
    if entry["seq"] != expected_seq or entry["prev_hash"] != expected_prev:
        raise JournalError("append rejected: seq/prev_hash do not extend the current head")
    if entries and entry["run_id"] != entries[0]["run_id"]:
        raise JournalError("append rejected: run_id mismatch")
    line = canonical.jcs_bytes(entry) + b"\n"
    fd = os.open(path, os.O_WRONLY | os.O_APPEND | os.O_CREAT, 0o644)
    try:
        os.write(fd, line)
        os.fsync(fd)
    finally:
        os.close(fd)
    return entry["entry_hash"]
