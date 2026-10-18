"""Shared secret detection helpers for repository and export scans."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class SecretFinding:
    """A likely secret occurrence in a text file."""

    rel_path: str
    line_number: int
    label: str

    def format(self) -> str:
        return f"{self.rel_path}:{self.line_number}: possible {self.label}"


TOKEN_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("AWS access key id", re.compile(r"\b(AKIA|ASIA)[0-9A-Z]{16}\b")),
    ("GitHub token", re.compile(r"\bgh[pousr]_[A-Za-z0-9]{36,}\b")),
    ("GitHub fine-grained token", re.compile(r"\bgithub_pat_[A-Za-z0-9_]{22,}\b")),
    ("Slack token", re.compile(r"\bxox[baprs]-[A-Za-z0-9-]{10,}\b")),
    ("OpenAI key", re.compile(r"\bsk-[A-Za-z0-9_-]{20,}\b")),
    ("Anthropic key", re.compile(r"\bsk-ant-[A-Za-z0-9_-]{20,}\b")),
    ("Google API key", re.compile(r"\bAIza[0-9A-Za-z_-]{35}\b")),
    ("JWT", re.compile(r"\beyJ[A-Za-z0-9_-]{10,}\.eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\b")),
    ("Private key block", re.compile(r"-----BEGIN (?:RSA |EC |DSA |OPENSSH )?PRIVATE KEY-----")),
    (
        "Credentialed URL",
        re.compile(r"\b[a-z][a-z0-9+.-]*://[^\s:/@\"']+:[^\s:/@\"']+@[^\s\"']+"),
    ),
    (
        "Suspicious assignment",
        re.compile(
            r"(?i)\b(api[_-]?key|auth[_-]?token|access[_-]?token|client[_-]?secret|password|passwd)\b"
            r"\s*[:=]\s*[\"']([A-Za-z0-9+/_=-]{16,})[\"']"
        ),
    ),
]

# A matched candidate value matching any of these is treated as a placeholder/example, not a secret.
ALLOW_VALUE_RE = re.compile(
    r"^\$\{[A-Z0-9_]+\}$"          # ${PLACEHOLDER}
    r"|^\{\{[^}]*\}\}$"            # {{ template }}
    r"|^TODO\([^)]*\)$"             # TODO(KEY) markers
    r"|^<[A-Za-z][A-Za-z0-9 _-]*>$"  # <angle-bracket placeholder>
    r"|(?i:\b(example|placeholder|dummy|sample|fake|redacted|changeme|your[_-]))"
    r"|^x{6,}$|^\*{4,}$|^\.{3}$",
)

SKIP_NAME_PARTS = {"env.example", ".env.example"}
SKIP_SUFFIXES = {
    ".png", ".jpg", ".jpeg", ".gif", ".webp", ".ico", ".pdf", ".zip", ".woff", ".woff2",
    ".lock", ".svg",
}


def matched_secret_value(match: re.Match[str]) -> str:
    """Return the concrete candidate value from a token-pattern match."""
    if match.lastindex and match.lastindex >= 2 and match.group(2) is not None:
        return match.group(2)
    return match.group(0)


def is_allowed_secret_match(match: re.Match[str]) -> bool:
    """Return true when the matched candidate itself is a documented dummy value."""
    return bool(ALLOW_VALUE_RE.search(matched_secret_value(match).strip()))


def scan_text(text: str, rel_path: str) -> list[SecretFinding]:
    """Return likely secret findings in UTF-8 text."""

    findings: list[SecretFinding] = []
    for lineno, line in enumerate(text.splitlines(), start=1):
        for label, pattern in TOKEN_PATTERNS:
            if any(not is_allowed_secret_match(match) for match in pattern.finditer(line)):
                findings.append(SecretFinding(rel_path, lineno, label))
                break
    return findings


def scan_file(path: Path, rel_path: str) -> list[SecretFinding] | None:
    """Scan a UTF-8 text file, or return None if it cannot be decoded/read."""

    try:
        text = path.read_text(encoding="utf-8")
    except (UnicodeDecodeError, OSError):
        return None
    return scan_text(text, rel_path)
