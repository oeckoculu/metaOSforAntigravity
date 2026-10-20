"""I-12 secret scanning (scan-and-reject; the kernel never stores secrets)."""
import re

PROFILE = "kernel.secret_scan.v1"

PATTERNS = [
    ("GITHUB_TOKEN", re.compile(r"\bgh[pousr]_[A-Za-z0-9]{30,}\b")),
    ("GITHUB_FINE_GRAINED_PAT", re.compile(r"\bgithub_pat_[A-Za-z0-9_]{22,}\b")),
    ("AWS_ACCESS_KEY_ID", re.compile(r"\b(AKIA|ASIA)[0-9A-Z]{16}\b")),
    ("GOOGLE_API_KEY", re.compile(r"\bAIza[0-9A-Za-z_-]{35}\b")),
    ("SLACK_TOKEN", re.compile(r"\bxox[abprs]-[A-Za-z0-9-]{10,}\b")),
    ("PRIVATE_KEY_BLOCK", re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----")),
    ("URL_EMBEDDED_CREDENTIAL", re.compile(r"\bhttps?://[^/\s:@]+(:[^/\s@]*)?@[^\s]+")),
]


class SecretDetected(Exception):
    pass


def scan_text(text):
    hits = []
    for name, rx in PATTERNS:
        if rx.search(text):
            hits.append(name)
    return hits


def scan_obj(obj):
    hits = set()

    def walk(o):
        if isinstance(o, str):
            hits.update(scan_text(o))
        elif isinstance(o, list):
            for v in o:
                walk(v)
        elif isinstance(o, dict):
            for k, v in o.items():
                walk(k)
                walk(v)

    walk(obj)
    return sorted(hits)


def assert_clean(obj):
    hits = scan_obj(obj)
    if hits:
        # Never echo the matched value (I-12): report pattern classes only.
        raise SecretDetected("secret pattern classes detected: " + ",".join(hits))
