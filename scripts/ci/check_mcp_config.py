#!/usr/bin/env python3
"""Validate project MCP configuration examples and server entries.

The check is intentionally conservative: MCP configs are security-sensitive, so
remote servers, authentication, and write-capable tools must be explicit and
reviewable. The script accepts Claude/Cursor-style JSON with `mcpServers` and
optional `_examples` maps.
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CONFIGS = (".mcp.json", ".cursor/mcp.example.json")

SERVER_NAME_RE = re.compile(r"^[a-z0-9][a-z0-9-]*-(ro|rw|read|write)-[a-z0-9][a-z0-9-]*$")
ENV_REF_RE = re.compile(r"^(?:\$\{[A-Z_][A-Z0-9_]*\}|\$[A-Z_][A-Z0-9_]*)$")
ENV_REF_ANYWHERE_RE = re.compile(r"(?:\$\{[A-Z_][A-Z0-9_]*\}|\$[A-Z_][A-Z0-9_]*)")
SECRET_KEY_RE = re.compile(r"(?i)(authorization|api[_-]?key|token|secret|password|client[_-]?secret)")
SECRET_VALUE_RE = re.compile(
    r"(?i)(bearer\s+[A-Za-z0-9._~+/=-]{16,}|"
    r"sk-[A-Za-z0-9_-]{16,}|"
    r"gh[pousr]_[A-Za-z0-9_]{20,}|"
    r"github_pat_[A-Za-z0-9_]{20,}|"
    r"xox[baprs]-[A-Za-z0-9-]{10,})"
)
REMOTE_URL_RE = re.compile(r"^https?://", re.IGNORECASE)
READ_ONLY_VALUES = {"read-only", "readonly", "read", "ro"}
WRITE_VALUES = {"write-capable", "write", "read-write", "rw"}


def load_json(path: Path, errors: list[str]) -> dict[str, Any] | None:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        errors.append(f"{path}: invalid JSON: {exc}")
        return None
    if not isinstance(data, dict):
        errors.append(f"{path}: top-level value must be an object")
        return None
    return data


def is_env_reference(value: str) -> bool:
    value = value.strip()
    if ENV_REF_RE.fullmatch(value):
        return True
    # Common header form: "Bearer ${TOKEN}". Reject literal bearer tokens.
    if value.lower().startswith("bearer "):
        return ENV_REF_RE.fullmatch(value[7:].strip()) is not None
    return False


def is_remote(server: dict[str, Any]) -> bool:
    url = server.get("url") or server.get("endpoint")
    return isinstance(url, str) and REMOTE_URL_RE.match(url) is not None


def is_disabled(server: dict[str, Any]) -> bool:
    return server.get("enabled") is False or server.get("disabled") is True


def side_effect_class(server: dict[str, Any]) -> str | None:
    value = server.get("side_effects", server.get("sideEffects", server.get("access")))
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in READ_ONLY_VALUES:
            return "read-only"
        if normalized in WRITE_VALUES:
            return "write-capable"
    return None


def iter_secret_fields(value: Any, path: str = ""):
    if isinstance(value, dict):
        for key, nested in value.items():
            nested_path = f"{path}.{key}" if path else str(key)
            yield from iter_secret_fields(nested, nested_path)
    elif isinstance(value, list):
        for index, nested in enumerate(value):
            yield from iter_secret_fields(nested, f"{path}[{index}]")
    elif isinstance(value, str):
        key = path.rsplit(".", 1)[-1]
        if SECRET_KEY_RE.search(key) or SECRET_VALUE_RE.search(value):
            yield path, value


def validate_server(config_path: Path, group: str, name: str, server: Any, errors: list[str]) -> None:
    loc = f"{config_path}:{group}.{name}"
    if not SERVER_NAME_RE.fullmatch(name):
        errors.append(
            f"{loc}: server name must follow <scope>-<ro|rw>-<purpose> "
            "(use ro/read for read-only and rw/write for write-capable servers)"
        )
    if not isinstance(server, dict):
        errors.append(f"{loc}: server definition must be an object")
        return

    classification = side_effect_class(server)
    if classification is None:
        errors.append(f"{loc}: missing side_effects classification (read-only or write-capable)")
    elif ("-rw-" in name or "-write-" in name) and classification != "write-capable":
        errors.append(f"{loc}: rw/write server name must be classified as write-capable")
    elif ("-ro-" in name or "-read-" in name) and classification != "read-only":
        errors.append(f"{loc}: ro/read server name must be classified as read-only")

    if classification == "write-capable":
        approval = server.get("approval_required", server.get("approvalRequired"))
        approval_note = server.get("approval_note", server.get("approvalNote"))
        if approval is not True or not isinstance(approval_note, str) or not approval_note.strip():
            errors.append(f"{loc}: write-capable tools require approval_required=true and approval_note")

    if is_remote(server) and not (is_disabled(server) or server.get("approved") is True):
        errors.append(f"{loc}: remote servers must be disabled by default unless approved=true")

    for field_path, value in iter_secret_fields(server):
        if ENV_REF_ANYWHERE_RE.search(value):
            if not is_env_reference(value):
                errors.append(f"{loc}.{field_path}: auth/secret value must be only an environment-variable reference")
        else:
            errors.append(f"{loc}.{field_path}: possible inline secret; use an environment-variable reference")


def validate_config(path: Path) -> list[str]:
    errors: list[str] = []
    data = load_json(path, errors)
    if data is None:
        return errors
    for group in ("mcpServers", "_examples"):
        servers = data.get(group, {})
        if not isinstance(servers, dict):
            errors.append(f"{path}:{group}: must be an object")
            continue
        for name, server in servers.items():
            validate_server(path, group, name, server, errors)
    return errors


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate MCP config security conventions")
    parser.add_argument("configs", nargs="*", type=Path, help="Config files to validate")
    args = parser.parse_args(argv)
    paths = args.configs or [REPO_ROOT / rel for rel in DEFAULT_CONFIGS]
    all_errors: list[str] = []
    for path in paths:
        if not path.exists():
            all_errors.append(f"{path}: file does not exist")
            continue
        all_errors.extend(validate_config(path))
    if all_errors:
        print(f"MCP config check FAILED ({len(all_errors)} issue(s)):")
        for error in all_errors:
            print(f"  {error}")
        return 1
    print("MCP config check passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
