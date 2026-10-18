#!/usr/bin/env python3
"""Validate workspace-relative files before external review/export."""

from __future__ import annotations

import argparse
import fnmatch
import os
import sys
from pathlib import Path, PurePosixPath
from typing import Any

try:
    import yaml
except ModuleNotFoundError:  # pragma: no cover - exercised when PyYAML is unavailable
    yaml = None

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.ci.secret_detection import scan_file as scan_secret_file

DEFAULT_POLICY = REPO_ROOT / "agent-policy.yaml"
CREDENTIAL_NAME_PARTS = (
    "secret",
    "credential",
    "credentials",
    "passwd",
    "password",
    "token",
    "apikey",
    "api_key",
    "auth",
    "private_key",
)


class ValidationError(ValueError):
    """Raised when a candidate export is not allowed."""


def _parse_scalar(value: str) -> Any:
    value = value.strip()
    if value in {"true", "True"}:
        return True
    if value in {"false", "False"}:
        return False
    if value in {"{}", ""}:
        return {} if value == "{}" else ""
    if value.isdecimal():
        return int(value)
    return value.strip('"\'')


def _minimal_yaml_load(text: str) -> dict[str, Any]:
    """Parse the policy's small YAML subset when PyYAML is unavailable."""
    root: dict[str, Any] = {}
    stack: list[tuple[int, Any]] = [(-1, root)]
    last_key_at_indent: dict[int, tuple[dict[str, Any], str]] = {}
    for raw_line in text.splitlines():
        if not raw_line.strip() or raw_line.lstrip().startswith("#"):
            continue
        indent = len(raw_line) - len(raw_line.lstrip(" "))
        line = raw_line.strip()
        while stack and indent <= stack[-1][0]:
            stack.pop()
        parent = stack[-1][1]
        if line.startswith("- "):
            if not isinstance(parent, list):
                mapping, key = last_key_at_indent[indent]
                existing = mapping.get(key)
                if isinstance(existing, list):
                    parent = existing
                else:
                    parent = []
                    mapping[key] = parent
                stack.append((indent, parent))
            parent.append(_parse_scalar(line[2:]))
            continue
        key, sep, value = line.partition(":")
        if not sep or not isinstance(parent, dict):
            raise ValidationError(f"unsupported policy YAML line: {raw_line}")
        key = key.strip()
        if value.strip():
            parent[key] = _parse_scalar(value)
        else:
            child: dict[str, Any] = {}
            parent[key] = child
            stack.append((indent, child))
            last_key_at_indent[indent + 2] = (parent, key)
    return root


def _load_policy(path: Path) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8")
    policy = yaml.safe_load(text) if yaml is not None else _minimal_yaml_load(text)
    policy = policy or {}
    if not isinstance(policy, dict):
        raise ValidationError(f"policy is not a mapping: {path}")
    return policy


def _normalize_candidate(candidate: str) -> str:
    raw = candidate.strip()
    if not raw:
        raise ValidationError("empty path is ambiguous")
    path = PurePosixPath(raw.replace(os.sep, "/"))
    if path.is_absolute() or raw.startswith("~"):
        raise ValidationError(f"absolute or home-relative path rejected: {candidate}")
    if any(part in ("", ".", "..") for part in path.parts):
        raise ValidationError(f"ambiguous or traversal path rejected: {candidate}")
    if any(ch in raw for ch in "*?[]"):
        raise ValidationError(f"glob pattern is ambiguous, pass explicit files: {candidate}")
    return path.as_posix()


def _matches(patterns: list[str], rel_path: str) -> bool:
    path = PurePosixPath(rel_path)
    name = path.name
    return any(
        fnmatch.fnmatchcase(rel_path, p)
        or fnmatch.fnmatchcase(name, p)
        or (p.startswith("**/") and fnmatch.fnmatchcase(rel_path, p[3:]))
        for p in patterns
    )


def _looks_like_credentials(rel_path: str) -> bool:
    lowered = rel_path.lower()
    name = PurePosixPath(rel_path).name.lower()
    if name in {".netrc", "kubeconfig", "credentials", "secrets"}:
        return True
    return any(part in lowered for part in CREDENTIAL_NAME_PARTS)


def validate(paths: list[str], *, policy_path: Path = DEFAULT_POLICY, external_export: bool = False, approval_marker: str | None = None) -> list[str]:
    policy = _load_policy(policy_path)
    denied = list(policy.get("denied_globs", []))
    allowed = list(policy.get("allowed_globs", ["**/*"]))
    max_files = int(policy.get("max_files", 0))
    max_total_bytes = int(policy.get("max_total_bytes", 0))

    normalized = [_normalize_candidate(p) for p in paths]
    if len(set(normalized)) != len(normalized):
        raise ValidationError("duplicate paths are ambiguous")
    if max_files and len(normalized) > max_files:
        raise ValidationError(f"too many files: {len(normalized)} > {max_files}")

    approval = policy.get("approval_requirements", {}).get("external_export", {})
    if external_export and approval.get("required", False):
        required_marker = str(approval.get("marker", "APPROVED_EXTERNAL_EXPORT"))
        if approval_marker != required_marker:
            raise ValidationError(f"external export requires approval marker: {required_marker}")

    total = 0
    for rel_path in normalized:
        if _matches(denied, rel_path) or _looks_like_credentials(rel_path):
            raise ValidationError(f"denied path rejected: {rel_path}")
        if allowed and not _matches(allowed, rel_path):
            raise ValidationError(f"path is not in allowed_globs: {rel_path}")
        full = (REPO_ROOT / rel_path).resolve()
        try:
            full.relative_to(REPO_ROOT)
        except ValueError as exc:
            raise ValidationError(f"path escapes workspace: {rel_path}") from exc
        if not full.is_file():
            raise ValidationError(f"path is missing or not a regular file: {rel_path}")
        total += full.stat().st_size
        if max_total_bytes and total > max_total_bytes:
            raise ValidationError(f"total bytes exceed limit: {total} > {max_total_bytes}")
        findings = scan_secret_file(full, rel_path)
        if findings is None:
            raise ValidationError(f"file is not readable UTF-8 text for export: {rel_path}")
        if findings:
            first = findings[0]
            raise ValidationError(
                f"likely secret rejected: {first.rel_path}:{first.line_number}: {first.label}"
            )
    return normalized


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("paths", nargs="+", help="workspace-relative file paths to validate")
    parser.add_argument("--policy", type=Path, default=DEFAULT_POLICY)
    parser.add_argument("--external-export", action="store_true", help="require export approval marker when policy requires it")
    parser.add_argument("--approval-marker", help="explicit approval marker for external export")
    args = parser.parse_args(argv)
    try:
        accepted = validate(args.paths, policy_path=args.policy, external_export=args.external_export, approval_marker=args.approval_marker)
    except ValidationError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    for path in accepted:
        print(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
