"""Deterministic canonicalization primitives for the Meta-OS kernel.

- JSON: RFC 8785 (JCS) subset. Kernel documents are restricted to integers
  within the IEEE-754 safe range; floats, NaN and Infinity are rejected
  (fail-closed, I-08) so that ES6 number serialization is never needed.
- Text: UTF-8 (no BOM), LF line endings, Unicode NFC, no trailing
  whitespace, exactly one final newline.

Standard library only (I-04: no unpinned third-party dependencies).
"""
import hashlib
import json
import unicodedata

SAFE_INT = 2 ** 53 - 1
ZERO_HASH = "sha256:" + "0" * 64


class CanonicalizationError(ValueError):
    pass


def _check(o, path="$"):
    if o is None or isinstance(o, bool):
        return
    if isinstance(o, int):
        if abs(o) > SAFE_INT:
            raise CanonicalizationError(path + ": integer outside IEEE-754 safe range")
        return
    if isinstance(o, float):
        raise CanonicalizationError(path + ": floats are forbidden in kernel documents")
    if isinstance(o, str):
        try:
            o.encode("utf-8")
        except UnicodeEncodeError:
            raise CanonicalizationError(path + ": string contains lone surrogate")
        return
    if isinstance(o, list):
        for i, v in enumerate(o):
            _check(v, "%s[%d]" % (path, i))
        return
    if isinstance(o, dict):
        for k, v in o.items():
            if not isinstance(k, str):
                raise CanonicalizationError(path + ": non-string object key")
            _check(k, path + ".<key>")
            _check(v, path + "." + k)
        return
    raise CanonicalizationError(path + ": unsupported type " + type(o).__name__)


def _utf16_key(s):
    # RFC 8785 3.2.3: sort by UTF-16 code units.
    return s.encode("utf-16-be")


def _ser(o):
    if o is None:
        return "null"
    if o is True:
        return "true"
    if o is False:
        return "false"
    if isinstance(o, int):
        return str(o)
    if isinstance(o, str):
        return json.dumps(o, ensure_ascii=False)
    if isinstance(o, list):
        return "[" + ",".join(_ser(v) for v in o) + "]"
    items = sorted(o.items(), key=lambda kv: _utf16_key(kv[0]))
    return "{" + ",".join(json.dumps(k, ensure_ascii=False) + ":" + _ser(v) for k, v in items) + "}"


def jcs_bytes(obj):
    _check(obj)
    return _ser(obj).encode("utf-8")


def sha256_hex(data):
    return hashlib.sha256(data).hexdigest()


def sha256_ref(data):
    return "sha256:" + sha256_hex(data)


def jcs_hash(obj):
    return sha256_ref(jcs_bytes(obj))


def file_sha256(path):
    with open(path, "rb") as fh:
        return sha256_ref(fh.read())


def _reject_constant(name):
    raise CanonicalizationError("non-finite number literal rejected: " + name)


def _reject_float(text):
    raise CanonicalizationError("float literal rejected: " + text)


def _no_duplicates(pairs):
    out = {}
    for k, v in pairs:
        if k in out:
            raise CanonicalizationError("duplicate object key: " + k)
        out[k] = v
    return out


def strict_loads(text):
    """Parse JSON fail-closed: no duplicate keys, no floats, no NaN/Infinity."""
    if isinstance(text, bytes):
        text = text.decode("utf-8")
    obj = json.loads(
        text,
        object_pairs_hook=_no_duplicates,
        parse_constant=_reject_constant,
        parse_float=_reject_float,
    )
    _check(obj)
    return obj


def strict_load_file(path):
    with open(path, "rb") as fh:
        raw = fh.read()
    return strict_loads(raw.decode("utf-8"))


def pretty_bytes(obj):
    """Deterministic human-readable JSON (key order preserved, 2-space indent)."""
    _check(obj)
    return (json.dumps(obj, ensure_ascii=False, indent=2) + "\n").encode("utf-8")


def sorted_pretty_bytes(obj):
    """Deterministic human-readable JSON with sorted keys (for derived views)."""
    _check(obj)
    return (json.dumps(obj, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode("utf-8")


def canonical_text(text):
    if text.startswith("\ufeff"):
        text = text[1:]
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = unicodedata.normalize("NFC", text)
    lines = [ln.rstrip(" \t") for ln in text.split("\n")]
    while lines and lines[-1] == "":
        lines.pop()
    return "\n".join(lines) + "\n"


def is_canonical_text(raw_bytes):
    try:
        text = raw_bytes.decode("utf-8")
    except UnicodeDecodeError:
        return False
    return canonical_text(text).encode("utf-8") == raw_bytes
