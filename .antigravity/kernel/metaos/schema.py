"""Minimal, fail-closed JSON Schema (draft 2020-12 subset) validator.

The kernel is stdlib-only (no pinned third-party `jsonschema` yet), so this
module implements a deliberately small keyword subset. `lint_schema` rejects
any schema that uses an unsupported keyword, so a schema can never silently
rely on semantics this validator does not enforce (I-08).
Full draft 2020-12 meta-schema validation is EXPERIMENTAL / pending.
"""
import re

from . import canonical

DIALECT = "https://json-schema.org/draft/2020-12/schema"
SUPPORTED = frozenset([
    "$schema", "$id", "$comment", "$defs", "$ref", "title", "description",
    "type", "properties", "required", "additionalProperties", "items",
    "enum", "const", "pattern", "minLength", "maxLength", "minimum", "maximum",
    "minItems", "maxItems", "uniqueItems", "oneOf", "anyOf", "allOf", "not",
    "if", "then", "else", "format",
])
TYPES = frozenset(["object", "array", "string", "integer", "boolean", "null"])
FORMATS = {
    "date-time": re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$"),
    "uuid": re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$"),
}


def _strict_eq(a, b):
    # JSON equality without Python's True == 1 coercion.
    return canonical.jcs_bytes(a) == canonical.jcs_bytes(b)


def _type_ok(value, t):
    if t == "object":
        return isinstance(value, dict)
    if t == "array":
        return isinstance(value, list)
    if t == "string":
        return isinstance(value, str)
    if t == "integer":
        return isinstance(value, int) and not isinstance(value, bool)
    if t == "boolean":
        return isinstance(value, bool)
    if t == "null":
        return value is None
    return False


def _resolve(root, ref):
    if not ref.startswith("#/$defs/"):
        raise ValueError("only local #/$defs/ refs are supported: " + ref)
    name = ref[len("#/$defs/"):]
    return root["$defs"][name]


class Validator(object):
    def __init__(self, schema):
        self.root = schema

    def errors(self, instance):
        errs = []
        self._v(self.root, instance, "$", errs)
        return errs

    def is_valid(self, instance):
        return not self.errors(instance)

    def _v(self, s, x, path, errs):
        if s is True:
            return
        if s is False:
            errs.append((path, "schema false: no value allowed"))
            return
        if "$ref" in s:
            self._v(_resolve(self.root, s["$ref"]), x, path, errs)
        if "type" in s:
            ts = s["type"] if isinstance(s["type"], list) else [s["type"]]
            if not any(_type_ok(x, t) for t in ts):
                errs.append((path, "type: expected %s" % "|".join(ts)))
                return
        if "const" in s and not _strict_eq(x, s["const"]):
            errs.append((path, "const mismatch"))
        if "enum" in s and not any(_strict_eq(x, e) for e in s["enum"]):
            errs.append((path, "enum: %r not allowed" % (x,)))
        if isinstance(x, str):
            if "minLength" in s and len(x) < s["minLength"]:
                errs.append((path, "minLength"))
            if "maxLength" in s and len(x) > s["maxLength"]:
                errs.append((path, "maxLength"))
            if "pattern" in s and not re.search(s["pattern"], x):
                errs.append((path, "pattern %s" % s["pattern"]))
            if "format" in s and not FORMATS[s["format"]].match(x):
                errs.append((path, "format %s" % s["format"]))
        if isinstance(x, int) and not isinstance(x, bool):
            if "minimum" in s and x < s["minimum"]:
                errs.append((path, "minimum"))
            if "maximum" in s and x > s["maximum"]:
                errs.append((path, "maximum"))
        if isinstance(x, list):
            if "minItems" in s and len(x) < s["minItems"]:
                errs.append((path, "minItems"))
            if "maxItems" in s and len(x) > s["maxItems"]:
                errs.append((path, "maxItems"))
            if s.get("uniqueItems"):
                seen = []
                for item in x:
                    if item in seen:
                        errs.append((path, "uniqueItems"))
                        break
                    seen.append(item)
            if "items" in s:
                for i, item in enumerate(x):
                    self._v(s["items"], item, "%s[%d]" % (path, i), errs)
        if isinstance(x, dict):
            for req in s.get("required", []):
                if req not in x:
                    errs.append((path, "required: %s" % req))
            props = s.get("properties", {})
            for k, v in x.items():
                if k in props:
                    self._v(props[k], v, path + "." + k, errs)
                elif "additionalProperties" in s:
                    ap = s["additionalProperties"]
                    if ap is False:
                        errs.append((path, "additionalProperties: %s not allowed" % k))
                    elif isinstance(ap, dict):
                        self._v(ap, v, path + "." + k, errs)
        for sub in s.get("allOf", []):
            self._v(sub, x, path, errs)
        if "anyOf" in s:
            if not any(not self._collect(sub, x, path) for sub in s["anyOf"]):
                errs.append((path, "anyOf: no branch matched"))
        if "oneOf" in s:
            n = sum(1 for sub in s["oneOf"] if not self._collect(sub, x, path))
            if n != 1:
                errs.append((path, "oneOf: %d branches matched (expected 1)" % n))
        if "not" in s and not self._collect(s["not"], x, path):
            errs.append((path, "not: forbidden shape matched"))
        if "if" in s:
            if not self._collect(s["if"], x, path):
                if "then" in s:
                    self._v(s["then"], x, path, errs)
            elif "else" in s:
                self._v(s["else"], x, path, errs)

    def _collect(self, s, x, path):
        e = []
        self._v(s, x, path, e)
        return e


def _subschemas(s):
    if not isinstance(s, dict):
        return
    for k in ("properties", "$defs"):
        for v in s.get(k, {}).values():
            yield v
    for k in ("items", "not", "if", "then", "else"):
        if k in s:
            yield s[k]
    if isinstance(s.get("additionalProperties"), dict):
        yield s["additionalProperties"]
    for k in ("allOf", "anyOf", "oneOf"):
        for v in s.get(k, []):
            yield v


def lint_schema(schema):
    """Return a list of problems; empty list means the schema is admissible."""
    problems = []
    if schema.get("$schema") != DIALECT:
        problems.append("$schema must be " + DIALECT)
    for k in ("$id", "title"):
        if not schema.get(k):
            problems.append("root %s missing" % k)

    def walk(s, path):
        if isinstance(s, bool):
            return
        if not isinstance(s, dict):
            problems.append(path + ": schema must be object or boolean")
            return
        unknown = sorted(set(s) - SUPPORTED)
        if unknown:
            problems.append(path + ": unsupported keywords " + ",".join(unknown))
        if "type" in s:
            ts = s["type"] if isinstance(s["type"], list) else [s["type"]]
            bad = [t for t in ts if t not in TYPES]
            if bad:
                problems.append(path + ": unknown type " + ",".join(bad))
            if "object" in ts and "additionalProperties" not in s:
                problems.append(path + ": object schema must declare additionalProperties explicitly")
        if "properties" in s and "additionalProperties" not in s:
            problems.append(path + ": properties without explicit additionalProperties")
        if "pattern" in s:
            try:
                re.compile(s["pattern"])
            except re.error as e:
                problems.append(path + ": bad pattern " + str(e))
        if "format" in s and s["format"] not in FORMATS:
            problems.append(path + ": unsupported format " + s["format"])
        if "$ref" in s:
            try:
                _resolve(schema, s["$ref"])
            except Exception as e:
                problems.append(path + ": unresolvable $ref " + str(e))
        for i, sub in enumerate(_subschemas(s)):
            walk(sub, "%s/<%d>" % (path, i))

    walk(schema, "#")
    return problems
