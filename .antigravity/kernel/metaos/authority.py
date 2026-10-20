"""Phase A1 - Authority normalization.

Converts the Google-Docs-exported authority files into canonical UTF-8
artefacts without semantic change, and locks their hashes.
"""
import os
import re
import unicodedata

from . import canonical
from .receipt import Receipt

SPEC_PATH = "SPEC_META_OS_v1.1.md"
JSON_SRC = ".antigravity/schemas/invariants_and_states_v1.1.json.md"
JSON_DST = ".antigravity/schemas/invariants_and_states.json"
LOCK_PATH = ".antigravity/genesis/authority_lock.json"
RECEIPT_PATH = ".antigravity/genesis/receipts/A1_authority_normalization.receipt.json"

# Markdown-export artefacts that are invalid JSON escapes and carry no meaning.
GDOCS_ESCAPES = ("[", "]", "_")
JSON_ESCAPES = '"\\/bfnrtu'
BLOCK_START = re.compile(r"^\s*([-*+]\s|\d+[.)]\s|#{1,6}\s|>|\|)")
EXPECTED_INVARIANTS = ["I-%02d" % i for i in range(1, 16)]


class NormalizationError(Exception):
    pass


def unescape_gdocs_json(text):
    out = []
    counts = dict((c, 0) for c in GDOCS_ESCAPES)
    i = 0
    n = len(text)
    while i < n:
        ch = text[i]
        if ch != "\\":
            out.append(ch)
            i += 1
            continue
        if i + 1 >= n:
            raise NormalizationError("dangling backslash at offset %d" % i)
        nxt = text[i + 1]
        if nxt in GDOCS_ESCAPES:
            counts[nxt] += 1
            out.append(nxt)
        elif nxt in JSON_ESCAPES:
            out.append(ch)
            out.append(nxt)
        else:
            raise NormalizationError("unknown escape \\%s at offset %d (fail-closed)" % (nxt, i))
        i += 2
    return "".join(out), counts


def hard_break_report(text):
    """Trailing-whitespace removal is rendering-neutral only if every such
    line ends a block (next line is EOF, blank, or a new block start)."""
    lines = text.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    offending = []
    total = 0
    for idx, ln in enumerate(lines):
        if ln != ln.rstrip(" \t"):
            total += 1
            if ln.strip() == "":
                continue
            nxt = lines[idx + 1] if idx + 1 < len(lines) else ""
            if nxt.strip() == "" or BLOCK_START.match(nxt):
                continue
            offending.append(idx + 1)
    return total, offending


def letters_fingerprint(text):
    return "".join(c for c in unicodedata.normalize("NFC", text) if c.isalpha())


def derive_states(doc):
    sm = doc["state_machine"]
    states = set([sm["initial_state"]]) | set(sm["terminal_states"])
    for t in sm["lifecycle_transitions"]:
        states.add(t["current_state"])
        states.update(t["allowed_next_states"])
    for t in sm["exception_and_circuit_breaker_transitions"]:
        for k in ("from_state", "to_state"):
            if t[k] != "ANY_ACTIVE_STATE":
                states.add(t[k])
    return sorted(states)


def structural_check(doc):
    problems = []
    if doc.get("version") != "1.1.0":
        problems.append("version != 1.1.0")
    ids = [i.get("id") for i in doc.get("invariants", [])]
    if ids != EXPECTED_INVARIANTS:
        problems.append("invariant ids not exactly I-01..I-15 in order")
    if any(i.get("requirement_level") != "REQUIRED" for i in doc.get("invariants", [])):
        problems.append("non-REQUIRED invariant present")
    sm = doc.get("state_machine", {})
    for key in ("initial_state", "terminal_states", "lifecycle_transitions",
                "exception_and_circuit_breaker_transitions"):
        if key not in sm:
            problems.append("state_machine." + key + " missing")
    if problems:
        return problems
    sources = [t["current_state"] for t in sm["lifecycle_transitions"]]
    if len(sources) != len(set(sources)):
        problems.append("duplicate lifecycle source state")
    if sm["initial_state"] != sources[0]:
        problems.append("initial_state is not first lifecycle source")
    return problems


def run(root, lineage_json=None, lineage_spec=None, upstream=None):
    r = Receipt(root, "A1", "authority_normalization")
    spec_abs = os.path.join(root, SPEC_PATH)
    src_abs = os.path.join(root, JSON_SRC)
    dst_abs = os.path.join(root, JSON_DST)

    ok = r.check("A1-C01", "Input authority files exist at base paths",
                 os.path.isfile(spec_abs) and os.path.isfile(src_abs) and not os.path.exists(dst_abs),
                 {"spec": SPEC_PATH, "json_source": JSON_SRC, "json_target_absent": not os.path.exists(dst_abs)})
    if not ok:
        return r, None

    spec_raw = open(spec_abs, "rb").read()
    src_raw = open(src_abs, "rb").read()
    input_hashes = {SPEC_PATH: canonical.sha256_ref(spec_raw), JSON_SRC: canonical.sha256_ref(src_raw)}

    try:
        spec_text = spec_raw.decode("utf-8")
        src_text = src_raw.decode("utf-8")
        utf8_ok = True
    except UnicodeDecodeError as e:
        utf8_ok = False
        spec_text = src_text = ""
    r.check("A1-C02", "Inputs decode as strict UTF-8", utf8_ok, {"input_sha256": input_hashes})
    if not utf8_ok:
        return r, None

    total_tw, offending = hard_break_report(spec_text)
    r.check("A1-C03", "Trailing-whitespace removal in spec is rendering-neutral (all hard breaks end a block)",
            not offending, {"trailing_whitespace_lines": total_tw, "offending_lines": offending})

    spec_out = canonical.canonical_text(spec_text)
    r.check("A1-C04", "Spec canonical text form is idempotent",
            canonical.canonical_text(spec_out) == spec_out)
    r.check("A1-C05", "Spec letter content unchanged by normalization",
            letters_fingerprint(spec_text) == letters_fingerprint(spec_out),
            {"letters": len(letters_fingerprint(spec_out))})

    try:
        unescaped, counts = unescape_gdocs_json(src_text)
        esc_ok, esc_detail = True, {"removed_markdown_escapes": counts}
    except NormalizationError as e:
        unescaped, esc_ok, esc_detail = None, False, {"error": str(e)}
    r.check("A1-C06", "JSON source: only Markdown-export escapes \\[ \\] \\_ removed; no unknown escapes", esc_ok, esc_detail)
    if not esc_ok:
        return r, None

    try:
        doc = canonical.strict_loads(unescaped)
        parse_ok, parse_detail = True, None
    except Exception as e:
        doc, parse_ok, parse_detail = None, False, {"error": str(e)}
    r.check("A1-C07", "JSON strict parse (no duplicate keys, no floats, no NaN/Infinity)", parse_ok, parse_detail)
    if not parse_ok:
        return r, None

    problems = structural_check(doc)
    states = derive_states(doc) if not problems else []
    r.check("A1-C08", "Authority structure: v1.1.0, I-01..I-15 REQUIRED, well-formed state machine",
            not problems, {"problems": problems, "state_count": len(states)})

    json_out = canonical.pretty_bytes(doc)
    r.check("A1-C09", "JSON pretty form is idempotent and round-trips to identical JCS",
            canonical.pretty_bytes(canonical.strict_loads(json_out)) == json_out
            and canonical.jcs_hash(canonical.strict_loads(json_out)) == canonical.jcs_hash(doc))

    lineage = []
    if lineage_json:
        try:
            ldoc = canonical.strict_load_file(lineage_json)
            same = canonical.jcs_hash(ldoc) == canonical.jcs_hash(doc)
            det = {"lineage_file_sha256": canonical.file_sha256(lineage_json), "jcs_equal": same}
        except Exception as e:
            same, det = False, {"error": str(e)}
        r.check("A1-C10", "Normalized JSON is semantically identical (JCS) to text extracted from the original .docx", same, det)
    if lineage_spec:
        ltext = open(lineage_spec, encoding="utf-8").read()
        same = letters_fingerprint(ltext) == letters_fingerprint(spec_out)
        r.check("A1-C11", "Spec letter content identical to text extracted from the original .docx", same,
                {"lineage_file_sha256": canonical.file_sha256(lineage_spec)})
    for item in upstream or []:
        name, _, digest = item.partition("=")
        lineage.append({"source": name, "sha256": "sha256:" + digest, "kind": "UPSTREAM_DOCX_SNAPSHOT"})

    if not r.passed:
        return r, None

    # All checks passed: materialize outputs (fail-closed ordering).
    with open(spec_abs, "wb") as fh:
        fh.write(spec_out.encode("utf-8"))
    with open(dst_abs, "wb") as fh:
        fh.write(json_out)
    os.remove(src_abs)

    lock = {
        "lock_type": "AuthorityLock",
        "schema_version": "1.0.0",
        "authority_version": doc["version"],
        "canonicalization": {
            "json": "RFC 8785 JCS (kernel implementation; integers only, floats rejected)",
            "text": "UTF-8 without BOM, LF, Unicode NFC, no trailing whitespace, single final newline",
        },
        "entries": [
            {"path": SPEC_PATH, "role": "HUMAN_CONSTITUTION", "sha256": canonical.sha256_ref(spec_out.encode("utf-8"))},
            {"path": JSON_DST, "role": "MACHINE_AUTHORITY", "sha256": canonical.sha256_ref(json_out),
             "jcs_sha256": canonical.jcs_hash(doc), "state_count": len(states)},
        ],
        "lineage": lineage + [
            {"source": "git:" + SPEC_PATH, "sha256": input_hashes[SPEC_PATH], "kind": "PRE_NORMALIZATION_BLOB"},
            {"source": "git:" + JSON_SRC, "sha256": input_hashes[JSON_SRC], "kind": "PRE_NORMALIZATION_BLOB"},
        ],
        "pending": "Accepted patchset GBP-0000 (C-1..C-8, V12-01..V12-06) is NOT reflected in this v1.1.0 baseline; compiled and tested at phase A5.",
    }
    lock_abs = os.path.join(root, LOCK_PATH)
    os.makedirs(os.path.dirname(lock_abs), exist_ok=True)
    with open(lock_abs, "wb") as fh:
        fh.write(canonical.pretty_bytes(lock))

    r.output(SPEC_PATH)
    r.output(JSON_DST, {"jcs_sha256": canonical.jcs_hash(doc)})
    r.output(LOCK_PATH)
    return r, lock
