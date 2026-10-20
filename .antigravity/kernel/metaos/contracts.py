"""Phase A3 - Core schema contracts: lint, consistency and golden fixtures."""
import copy
import os

from . import canonical
from .authority import JSON_DST, derive_states
from .receipt import Receipt
from .schema import Validator, lint_schema

CORE_DIR = ".antigravity/schemas/core"
FIXTURES = CORE_DIR + "/fixtures/core_golden.fixtures.json"
REGISTRY = CORE_DIR + "/registry.json"
RECEIPT_PATH = ".antigravity/genesis/receipts/A3_core_schemas.receipt.json"
CORE = [
    ("intent_contract.schema.json", "IntentContract"),
    ("change_proposal.schema.json", "ChangeProposal"),
    ("task_envelope.schema.json", "TaskEnvelope"),
    ("event_journal_entry.schema.json", "EventJournalEntry"),
]


def load_schema(root, filename):
    return canonical.strict_load_file(os.path.join(root, CORE_DIR, filename))


def apply_mutations(base, mutations):
    doc = copy.deepcopy(base)
    for m in mutations:
        path = m["path"]
        tgt = doc
        for key in path[:-1]:
            tgt = tgt[key]
        if m["op"] == "set":
            tgt[path[-1]] = copy.deepcopy(m["value"])
        elif m["op"] == "remove":
            del tgt[path[-1]]
        else:
            raise ValueError("unknown mutation op " + m["op"])
    return doc


def run(root):
    r = Receipt(root, "A3", "core_schemas")
    schemas = {}
    lint = {}
    parse_errors = {}
    for fn, title in CORE:
        p = os.path.join(root, CORE_DIR, fn)
        try:
            raw = open(p, "rb").read()
            s = canonical.strict_loads(raw.decode("utf-8"))
            schemas[fn] = s
            problems = lint_schema(s)
            if s.get("title") != title:
                problems.append("title != " + title)
            if not canonical.is_canonical_text(raw):
                problems.append("file is not canonical UTF-8/LF/NFC text")
            lint[fn] = problems
        except Exception as e:
            parse_errors[fn] = str(e)
    r.check("A3-C01", "All four core schemas parse strictly", not parse_errors and len(schemas) == 4,
            {"errors": parse_errors})
    if parse_errors:
        return r
    r.check("A3-C02", "Schemas pass fail-closed lint (supported keywords only, closed objects, resolvable refs)",
            all(not v for v in lint.values()), {"problems": lint})

    ids = [s["$id"] for s in schemas.values()]
    r.check("A3-C03", "Schema $id values are unique URNs", len(set(ids)) == 4 and all(i.startswith("urn:metaos:schema:core:") for i in ids),
            {"ids": sorted(ids)})

    shared = {}
    for fn, s in schemas.items():
        for name, d in s.get("$defs", {}).items():
            shared.setdefault(name, set()).add(canonical.jcs_hash(d))
    drift = sorted(n for n, hs in shared.items() if len(hs) > 1)
    r.check("A3-C04", "Shared $defs are byte-identical (JCS) across schemas (no definition drift)", not drift,
            {"drifted": drift, "shared_defs": sorted(shared)})

    authority = canonical.strict_load_file(os.path.join(root, JSON_DST))
    auth_states = derive_states(authority)
    state_sets = {}
    for fn, s in schemas.items():
        st = s.get("$defs", {}).get("State")
        if st:
            state_sets[fn] = sorted(st["enum"])
    ok = bool(state_sets) and all(v == auth_states for v in state_sets.values())
    r.check("A3-C05", "State enums equal the state set derived from machine authority",
            ok, {"authority_state_count": len(auth_states), "schemas_with_state_enum": sorted(state_sets)})

    fixtures = canonical.strict_load_file(os.path.join(root, FIXTURES))
    results = []
    all_ok = True
    for case in fixtures["cases"]:
        v = Validator(schemas[case["schema"]])
        base_errs = v.errors(case["valid"])
        entry = {"schema": case["schema"], "valid_base_accepted": not base_errs, "invalid": []}
        if base_errs:
            entry["valid_base_errors"] = ["%s: %s" % e for e in base_errs][:5]
            all_ok = False
        for inv in case["invalid"]:
            inst = apply_mutations(case["valid"], inv["mutate"])
            rejected = not v.is_valid(inst)
            entry["invalid"].append({"name": inv["name"], "rejected": rejected})
            all_ok = all_ok and rejected
        results.append(entry)
    total_invalid = sum(len(e["invalid"]) for e in results)
    r.check("A3-C06", "Golden fixtures: every valid base accepted, every mutated invalid case rejected",
            all_ok, {"cases": results, "invalid_total": total_invalid})

    registry = {
        "registry_type": "ContractRegistry",
        "schema_version": "1.0.0",
        "dialect": "https://json-schema.org/draft/2020-12/schema",
        "validator": "metaos.kernel.schema (subset; EXPERIMENTAL until full meta-schema validation)",
        "schemas": [
            {"title": s["title"], "id": s["$id"], "path": CORE_DIR + "/" + fn,
             "sha256": canonical.file_sha256(os.path.join(root, CORE_DIR, fn)), "jcs_sha256": canonical.jcs_hash(s)}
            for fn, s in sorted(schemas.items())
        ],
        "fixtures": {"path": FIXTURES, "sha256": canonical.file_sha256(os.path.join(root, FIXTURES))},
    }
    if r.passed:
        with open(os.path.join(root, REGISTRY), "wb") as fh:
            fh.write(canonical.pretty_bytes(registry))
        for fn, _ in CORE:
            r.output(CORE_DIR + "/" + fn, {"jcs_sha256": canonical.jcs_hash(schemas[fn])})
        r.output(FIXTURES)
        r.output(REGISTRY)
    return r
