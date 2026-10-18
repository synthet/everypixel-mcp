#!/usr/bin/env python3
"""Inventory, plan, install, check and roll back local multi-harness setups.

Inventory and plan never change destinations. Plans and receipts contain private
machine paths and belong in ignored local state, not in the portable library.
No downloads, provider requests, Git configuration writes or permission changes.
"""
from __future__ import annotations

import argparse
import base64
import configparser
import contextlib
import copy
import difflib
import hashlib
import io
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
import tomllib
import types
import uuid
from pathlib import Path
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]
SCHEMA_VERSION = 1
SKIP = {".git", "node_modules", ".venv", "venv", "__pycache__", "target", "dist",
        "build", ".cache", ".pytest_cache", ".ruff_cache", "graphify-out", "scratch",
        "raw-sessions", "sessions", "conversations", "history", "browser", "local",
        "site-packages", ".gradle", ".terraform", ".nuget", "obj"}
AGENT_DIRS = {".claude", ".cursor", ".codex", ".agents", ".agent", ".gemini",
              ".antigravity", ".windsurf", ".github", ".vscode"}
INSTRUCTIONS = {"agents.md", "agents.override.md", "claude.md", "claude.local.md",
                "gemini.md", ".cursorrules", ".windsurfrules", "copilot-instructions.md"}
CONFIG_NAMES = {".mcp.json", "mcp.json", "mcp_config.json", "mcp.json.example",
                "agent-policy.yaml", "agent-policy.yml", "hooks.json", "settings.json",
                "settings.local.json", "config.toml", "plugin.json", "marketplace.json"}
ASSET_EXTENSIONS = {".md", ".mdc", ".toml", ".json", ".yaml", ".yml", ".py", ".ps1", ".psm1", ".psd1", ".sh", ".cmd", ".bat", ".js", ".cjs", ".mjs", ".ts", ".tsx", ".sql", ".ini", ".conf", ".xml"}
GLOBAL_ROOTS = [".claude/skills", ".claude/agents", ".claude/commands", ".claude/rules",
                ".claude/hooks", ".claude/plugins", ".agents/skills", ".codex/skills",
                ".codex/agents", ".codex/rules", ".codex/hooks", ".codex/plugins/cache",
                ".cursor/skills", ".cursor/agents", ".cursor/commands", ".cursor/rules",
                ".cursor/hooks", ".cursor/plugins", ".gemini/skills", ".gemini/agents",
                ".gemini/commands", ".gemini/config/skills", ".gemini/config/agents",
                ".gemini/config/rules", ".gemini/config/plugins",
                ".gemini/antigravity/skills", ".gemini/antigravity/global_workflows",
                ".gemini/antigravity-cli/skills", ".gemini/antigravity-cli/agents"]
GLOBAL_CONFIGS = [".claude.json", ".claude/CLAUDE.md", ".claude/settings.json",
                  ".claude/plugins/installed_plugins.json", ".codex/AGENTS.md",
                  ".codex/config.toml", ".cursor/mcp.json", ".cursor/hooks.json",
                  ".cursor/cli-config.json", ".gemini/GEMINI.md", ".gemini/AGENTS.md",
                  ".gemini/settings.json", ".gemini/config/config.json",
                  ".gemini/config/mcp_config.json", ".gemini/config/hooks.json",
                  ".gemini/antigravity/mcp_config.json",
                  ".gemini/antigravity-cli/settings.json"]
SECRET = re.compile(r"(?i)(?:sk-[a-z0-9_-]{16,}|gh[pousr]_[a-z0-9_]{20,}|github_pat_[a-z0-9_]{20,}|Bearer\s+[^\s\"']+)")
CREDENTIAL_DATA = re.compile(r"(?i)(?:sk-[a-z0-9_-]{20,}|gh[pousr]_[a-z0-9_]{20,}|github_pat_[a-z0-9_]{20,}|Bearer\s+(?!\$\{|<)[a-z0-9_.-]{24,})")


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def linked(path: Path) -> bool:
    return path.is_symlink() or bool(getattr(path, "is_junction", lambda: False)())


def frontmatter(text: str) -> dict[str, str]:
    """Read only leading plain YAML fields; never evaluate YAML constructors."""
    match = re.match(r"\A\ufeff?---\s*\n(.*?)\n---(?:\s*\n|$)", text.replace("\r\n", "\n"), re.S)
    if not match:
        return {}
    result: dict[str, str] = {}
    lines = match.group(1).splitlines()
    for i, line in enumerate(lines):
        m = re.match(r"^([a-zA-Z][\w-]*):\s*(.*)$", line)
        if not m:
            continue
        key, value = m.groups()
        if value in {"|", "|-", ">", ">-"}:
            following = []
            for tail in lines[i + 1:]:
                if tail and not tail[0].isspace():
                    break
                following.append(tail.strip())
            value = " ".join(following).strip()
        elif not value:
            values = []
            for tail in lines[i + 1:]:
                if tail and not tail[0].isspace():
                    break
                item = re.match(r"\s+-\s+(.+)", tail)
                if item:
                    values.append(item.group(1).strip().strip("\"'"))
            if values:
                value = json.dumps(values)
        value = value.strip()
        if value.startswith('"') and value.endswith('"'):
            try:
                value = json.loads(value)
            except ValueError:
                value = value[1:-1]
        elif value.startswith("'") and value.endswith("'"):
            value = value[1:-1]
        result[key] = value
    return result


def body(text: str) -> str:
    return re.sub(r"\A\ufeff?---\s*\n.*?\n---\s*\n?", "", text.replace("\r\n", "\n"), count=1, flags=re.S)


def safe_text(text: str) -> str:
    text = SECRET.sub("[redacted]", text)
    return re.sub(r"(?i)[A-Z]:[\\/](?:Users|Projects)[\\/][^\s\"`<>]+", "<local-path>", text)


def read_config(path: Path) -> dict:
    text = path.read_text(encoding="utf-8-sig")
    data = tomllib.loads(text) if path.suffix == ".toml" else json.loads(text)
    if not isinstance(data, dict):
        raise ValueError("configuration must be an object")
    return data


def config_summary(path: Path) -> dict:
    try:
        data = read_config(path)
    except (ValueError, OSError) as exc:
        return {"parse_error": type(exc).__name__}
    servers = data.get("mcpServers", data.get("mcp_servers", {}))
    plugins = data.get("enabledPlugins", data.get("plugins", {}))
    return {"keys": list(data), "servers": list(servers) if isinstance(servers, dict) else [],
            "hooks": list(data.get("hooks", {})),
            "plugins": [{"id": k, "enabled": v if isinstance(v, bool) else v.get("enabled") if isinstance(v, dict) else None}
                        for k, v in plugins.items()] if isinstance(plugins, dict) else []}


def project_info(path: Path, owner: str = "synthet") -> dict:
    git_dir = path / ".git"
    worktree = git_dir.is_file()
    config = git_dir / "config"
    if worktree:
        text = git_dir.read_text(encoding="utf-8", errors="replace")
        m = re.match(r"gitdir:\s*(.*)", text)
        if m:
            git_dir = (path / m.group(1).strip()).resolve()
            config = git_dir / "config"
            if not config.exists() and (git_dir / "commondir").exists():
                config = (git_dir / (git_dir / "commondir").read_text().strip()).resolve() / "config"
    remotes = []
    if config.exists():
        parser = configparser.RawConfigParser(strict=False)
        parser.read(config, encoding="utf-8")
        for section in parser.sections():
            if not section.startswith('remote "'):
                continue
            url = parser.get(section, "url", fallback="")
            if "://" in url:
                parsed = urlsplit(url)
                remote = (parsed.hostname or "") + parsed.path
            else:
                remote = re.sub(r"^[^@]+@", "", url).replace(":", "/", 1)
            remotes.append(remote)
    excluded = path.name.startswith(("_backup", ".")) or worktree or linked(path)
    own = any(f"github.com/{owner}/" in remote.lower() for remote in remotes)
    evidence = any((path / n).exists() for n in ["package.json", "pyproject.toml", "Cargo.toml",
                                                "requirements.txt", "AGENTS.md", "CLAUDE.md"])
    evidence |= any(path.glob("*.csproj")) or (path / "src").is_dir() or (path / "themes").is_dir()
    eligible = not excluded and (own or not remotes and evidence)
    reason = "maintained" if eligible else "alias/worktree/archive" if excluded else "upstream" if remotes else "assets/vendor/no-source"
    return {"name": path.name, "root": str(path.absolute()), "eligible": eligible,
            "reason": reason, "remotes": remotes, "worktree": worktree}


def _files(root: Path, errors: list, *, global_scan: bool = False):
    def onerror(exc):
        errors.append({"path": str(exc.filename), "error": type(exc).__name__})
    for directory, dirs, files in os.walk(root, followlinks=False, onerror=onerror):
        current = Path(directory)
        dirs[:] = sorted(d for d in dirs if d not in SKIP and not linked(current / d))
        directory_rel = current.relative_to(root)
        agent_directory = global_scan or bool(AGENT_DIRS.intersection(directory_rel.parts))
        for name in sorted(files):
            lower = name.lower()
            if lower.startswith((".env", "secrets", "credentials", "oauth", "auth.json")):
                continue
            if not (lower in INSTRUCTIONS or name == "SKILL.md" or lower in CONFIG_NAMES or agent_directory and Path(name).suffix in ASSET_EXTENSIONS):
                continue
            path = current / name
            if linked(path):
                continue
            rel = path.relative_to(root)
            if name.lower() in INSTRUCTIONS or name == "SKILL.md" or name.lower() in CONFIG_NAMES or (global_scan or AGENT_DIRS.intersection(rel.parts)) and path.suffix in ASSET_EXTENSIONS:
                # Debug/session/state material is not configuration source.
                if any(x in {"debug", "brain", "implicit", "knowledge", "file-history", "backups"} for x in rel.parts):
                    continue
                yield path


def inventory(projects_root: Path, user: Path, owner: str = "synthet") -> dict:
    assets, projects, errors, aliases = [], [], [], []
    visited: set[Path] = set()

    def collect(root: Path, label: str, scope: str, global_scan: bool = False):
        for path in _files(root, errors, global_scan=global_scan):
            resolved = path.resolve()
            if resolved in visited:
                continue
            visited.add(resolved)
            try:
                data = path.read_bytes()
                text = data.decode("utf-8", errors="replace")
            except OSError as exc:
                errors.append({"path": str(path), "error": type(exc).__name__})
                continue
            rel = path.relative_to(root).as_posix()
            metadata = frontmatter(text)
            kind = "skill" if path.name == "SKILL.md" else "instruction" if path.name.lower() in INSTRUCTIONS else "config" if path.name.lower() in CONFIG_NAMES else next((n[:-1] for n in ["commands", "agents", "rules", "hooks", "workflows"] if n in path.parts), "support")
            asset = {"path": str(path.absolute()), "relative": rel, "project": label, "scope": scope,
                     "kind": kind, "name": metadata.get("name", path.parent.name if kind == "skill" else path.stem),
                     "sha256": digest(data), "body_sha256": digest(body(text).encode()), "bytes": len(data),
                     "description": safe_text(metadata.get("description", "")),
                     "provider_managed": "/plugins/" in path.as_posix() or "/.system/" in path.as_posix() or "/synced/" in path.as_posix()}
            if kind == "config" and path.suffix in {".json", ".toml"}:
                asset["config"] = config_summary(path)
            assets.append(asset)

    if projects_root.exists():
        for path in sorted(projects_root.iterdir()):
            if not path.is_dir():
                continue
            if linked(path):
                aliases.append({"path": str(path), "target": str(path.resolve())})
                continue
            info = project_info(path, owner)
            projects.append(info)
            print("inventory: " + info["name"], file=sys.stderr, flush=True)
            collect(path, info["name"], "project")
    for rel in GLOBAL_ROOTS:
        root = user / rel
        if root.is_dir():
            collect(root, "user", "global", True)
    for rel in GLOBAL_CONFIGS:
        path = user / rel
        if path.is_file() and path.resolve() not in visited:
            # Reuse the same parser without recursively scanning the user profile.
            try:
                data = path.read_bytes()
            except OSError as exc:
                errors.append({"path": str(path), "error": type(exc).__name__})
                continue
            assets.append({"path": str(path.absolute()), "relative": rel, "project": "user", "scope": "global",
                           "kind": "instruction" if path.name.lower() in INSTRUCTIONS else "config", "name": path.name,
                           "sha256": digest(data), "bytes": len(data), "config": config_summary(path) if path.suffix in {".json", ".toml"} else {}})
    groups: dict[str, list[str]] = {}
    for asset in assets:
        groups.setdefault(asset["sha256"], []).append(asset["path"])
    return {"schema_version": SCHEMA_VERSION, "projects_root": str(projects_root.absolute()), "user_root": str(user.absolute()),
            "projects": projects, "assets": assets, "aliases": aliases, "errors": errors,
            "duplicate_groups": [v for v in groups.values() if len(v) > 1],
            "summary": {"projects": len(projects), "eligible": sum(p["eligible"] for p in projects), "assets": len(assets), "unique_contents": len(groups)}}


def merge_text(base: str, current: str, wanted: str) -> str | None:
    """Merge nonoverlapping line edits; ambiguous overlaps remain conflicts."""
    if current == base or current == wanted:
        return wanted
    if wanted == base:
        return current
    old = base.splitlines(keepends=True)
    def edits(text):
        new = text.splitlines(keepends=True)
        return [(i, j, new[a:b]) for op, i, j, a, b in difflib.SequenceMatcher(None, old, new).get_opcodes() if op != "equal"]
    ours, theirs = edits(current), edits(wanted)
    for i, j, a in ours:
        for x, y, b in theirs:
            if (i, j, a) == (x, y, b):
                continue
            if max(i, x) < min(j, y) or i == j == x == y or i == j and x <= i < y or x == y and i <= x < j:
                return None
    combined = ours + [e for e in theirs if e not in ours]
    for i, j, replacement in sorted(combined, key=lambda e: (e[0], e[1]), reverse=True):
        old[i:j] = replacement
    return "".join(old)


def merge_json(current: dict, additions: dict) -> dict:
    """Add missing entries, preserving every existing conflicting user setting."""
    result = copy.deepcopy(current)
    for key, value in additions.items():
        if key not in result:
            result[key] = copy.deepcopy(value)
        elif isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = merge_json(result[key], value)
    return result


def plan_files(root: Path, desired: dict[str, bytes], owned: dict, adopt: set[str] | None = None) -> list[dict]:
    result = []
    for rel, wanted in sorted(desired.items()):
        path = root / rel
        _contain(path, [root])
        current = path.read_bytes() if path.exists() else None
        if current is not None and current != wanted:
            try:
                if current.decode().replace("\r\n", "\n") == wanted.decode().replace("\r\n", "\n"):
                    wanted = current
                elif path.suffix == ".toml" and "agents" in path.parts:
                    old_agent, new_agent = tomllib.loads(current.decode()), tomllib.loads(wanted.decode())
                    for agent in [old_agent, new_agent]:
                        if "developer_instructions" in agent:
                            agent["developer_instructions"] = agent["developer_instructions"].strip()
                    if old_agent == new_agent:
                        wanted = current
            except (UnicodeError, ValueError):
                pass
        action = "create" if current is None else "unchanged" if current == wanted else "conflict"
        if action == "conflict" and rel in (adopt or set()):
            action = "update"
        elif action == "conflict" and rel in owned:
            base = base64.b64decode(owned[rel]["content"])
            try:
                merged = merge_text(base.decode(), current.decode(), wanted.decode())
            except UnicodeDecodeError:
                merged = None
            if merged is not None:
                wanted = merged.encode()
                action = "unchanged" if wanted == current else "update"
        result.append({"path": str(path.absolute()), "relative": rel, "action": action,
                       "before_sha256": digest(current) if current is not None else None,
                       "after_sha256": digest(wanted), "content": base64.b64encode(wanted).decode(),
                       "before_content": base64.b64encode(current).decode() if current is not None and (rel in {".claude.json", ".codex/config.toml", ".cursor/mcp.json", ".mcp.json", ".agents/mcp_config.json", ".gemini/config/mcp_config.json", ".gemini/antigravity/mcp_config.json"}) else None})
    return result


def _contain(path: Path, roots: list[Path]) -> None:
    resolved = path.resolve()
    # Resolve only lexical candidate roots. Resolving every one of forty
    # workstation roots for each of tens of thousands of files is quadratic
    # filesystem I/O. Both the selected root and destination are still freshly
    # resolved on every call; link checks below remain unchanged.
    absolute = path.absolute()
    allowed = [r.resolve() for r in roots if absolute.is_relative_to(r.absolute())]
    if not any(resolved != r and resolved.is_relative_to(r) for r in allowed):
        raise ValueError(f"destination outside allowed roots: {path}")
    if ".git" in path.parts or path.name in {"auth.json", ".credentials.json", "oauth_creds.json"}:
        raise ValueError(f"protected destination: {path}")
    # Do not write through junctions/symlinks, even when their target is inside.
    for candidate in (path, *path.parents):
        if candidate in allowed:
            break
        if linked(candidate):
            raise ValueError(f"linked destination: {path}")


def atomic_write(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=".agent-setup-", dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def write_json(path: Path, data: dict) -> None:
    atomic_write(path, (json.dumps(data, indent=2, ensure_ascii=False) + "\n").encode())


def apply_operations(operations: list[dict], state: Path, allowed: list[Path]) -> Path:
    # Validate the entire destination set before the first write.
    for op in operations:
        _contain(Path(op["path"]), allowed)
        if op["action"] not in {"create", "update", "delete", "unchanged", "conflict"}:
            raise ValueError("unknown plan action")
        if op["action"] != "delete" and digest(base64.b64decode(op["content"])) != op["after_sha256"]:
            raise ValueError("plan content hash mismatch")
    run_dir = state / "runs" / (time.strftime("%Y%m%d-%H%M%S") + "-" + uuid.uuid4().hex[:8])
    receipt = run_dir / "receipt.json"
    data = {"schema_version": SCHEMA_VERSION, "allowed_roots": [str(p.absolute()) for p in allowed], "writes": [], "verified": [], "conflicts": [], "complete": False}
    write_json(receipt, data)
    journal = run_dir / "journal.jsonl"

    def record(entry):
        # Linear-size write-ahead journal; rewriting the whole receipt per file
        # makes a large workstation install quadratic in bytes and I/O.
        with journal.open("a", encoding="utf-8") as stream:
            stream.write(json.dumps(entry, ensure_ascii=False) + "\n")
            stream.flush()
            os.fsync(stream.fileno())

    for index, op in enumerate(operations):
        path = Path(op["path"])
        if op["action"] == "conflict":
            data["conflicts"].append({"path": str(path), "reason": "unmanaged or overlapping edit"})
            continue
        _contain(path, allowed)
        current = path.read_bytes() if path.exists() else None
        if (digest(current) if current is not None else None) != op["before_sha256"]:
            merged = concurrent_config_merge(op, current) if current is not None else None
            if merged is None:
                data["conflicts"].append({"path": str(path), "reason": "changed after planning"})
                continue
            op = {**op, "action": "update", "before_sha256": digest(current),
                  "after_sha256": digest(merged), "content": base64.b64encode(merged).decode()}
        if op["action"] == "unchanged":
            data["verified"].append({"path": str(path), "sha256": op["after_sha256"],
                                     "relative": op["relative"],
                                     "content": op["content"] if op.get("before_content") else None})
            continue
        backup = None
        if current is not None:
            backup = run_dir / "backups" / str(index)
            atomic_write(backup, current)
        entry = {k: op[k] for k in ["path", "relative", "before_sha256", "after_sha256", "content"]}
        entry["backup"] = str(backup) if backup else None
        entry["status"] = "pending"
        if (digest(path.read_bytes()) if path.exists() else None) != op["before_sha256"]:
            data["conflicts"].append({"path": str(path), "reason": "changed again before writing"})
            continue
        data["writes"].append(entry)
        record(entry)
        if op["action"] == "delete":
            path.unlink()
        else:
            atomic_write(path, base64.b64decode(op["content"]))
        entry["status"] = "written"
        record({"path": str(path), "status": "written"})
    data["complete"] = True
    write_json(receipt, data)
    return receipt


def concurrent_config_merge(op: dict, current: bytes) -> bytes | None:
    """Replay only reviewed additive MCP/skill entries onto live harness state.

    Claude updates its state file during normal sessions. A whole-file retry
    must never restore stale caches, credentials, permission or model settings.
    """
    if not op.get("before_content"):
        return None
    base = base64.b64decode(op["before_content"])
    wanted = base64.b64decode(op["content"])
    try:
        if op["relative"] == ".codex/config.toml":
            old, new, live = (tomllib.loads(value.decode()) for value in [base, wanted, current])
            for key in old.keys() | new.keys():
                if key not in {"mcp_servers", "skills"} and old.get(key) != new.get(key):
                    return None
            additions = {name: value for name, value in new.get("mcp_servers", {}).items()
                         if name not in old.get("mcp_servers", {})}
            if any(new.get("mcp_servers", {}).get(k) != v for k, v in old.get("mcp_servers", {}).items()):
                return None
            text = add_toml_servers(current.decode(), additions)
            before = old.get("skills", {}).get("config", [])
            existing = {e.get("path") for e in live.get("skills", {}).get("config", [])}
            for entry in new.get("skills", {}).get("config", []):
                if entry not in before and entry.get("path") not in existing:
                    if set(entry) != {"path", "enabled"} or entry["enabled"] is not False:
                        return None
                    text += '\n[[skills.config]]\npath = ' + json.dumps(entry["path"]) + '\nenabled = false\n'
            return text.encode()
        if op["relative"] not in {".claude.json", ".cursor/mcp.json", ".mcp.json", ".agents/mcp_config.json", ".gemini/config/mcp_config.json", ".gemini/antigravity/mcp_config.json"}:
            return None
        old, new, live = (json.loads(value) for value in [base, wanted, current])
        if any(old.get(k) != new.get(k) for k in old.keys() | new.keys() if k != "mcpServers"):
            return None
        if any(new.get("mcpServers", {}).get(k) != v for k, v in old.get("mcpServers", {}).items()):
            return None
        additions = {name: value for name, value in new.get("mcpServers", {}).items()
                     if name not in old.get("mcpServers", {})}
        return _json_bytes(merge_json(live, {"mcpServers": additions}))
    except (ValueError, UnicodeError, TypeError):
        return None


def load_receipt(receipt: Path) -> dict:
    data = json.loads(receipt.read_text(encoding="utf-8"))
    if not data["complete"] and (receipt.parent / "journal.jsonl").exists():
        writes = {}
        for line in (receipt.parent / "journal.jsonl").read_text(encoding="utf-8").splitlines():
            try:
                entry = json.loads(line)
            except ValueError:
                break  # Incomplete last record after an interrupted append.
            if entry["status"] == "pending":
                writes[entry["path"]] = entry
            elif entry["path"] in writes:
                writes[entry["path"]]["status"] = "written"
        data["writes"] = list(writes.values())
    return data


def check_run(receipt: Path) -> dict:
    data = load_receipt(receipt)
    drift = []
    live_state_changes = []
    for entry in [*data["writes"], *data.get("verified", [])]:
        path = Path(entry["path"])
        expected = entry.get("after_sha256", entry.get("sha256"))
        if expected is None and not path.exists():
            continue
        if not path.is_file() or digest(path.read_bytes()) != expected:
            same_registration = False
            if path.is_file() and entry.get("content"):
                try:
                    installed = base64.b64decode(entry["content"]).decode("utf-8-sig")
                    if entry.get("relative") == ".codex/config.toml":
                        before, current = tomllib.loads(installed), read_config(path)
                        same_registration = all(current.get("mcp_servers", {}).get(k) == v for k, v in before.get("mcp_servers", {}).items()) and all(item in current.get("skills", {}).get("config", []) for item in before.get("skills", {}).get("config", []))
                    elif entry.get("relative") in {".claude.json", ".cursor/mcp.json", ".mcp.json", ".agents/mcp_config.json", ".gemini/config/mcp_config.json", ".gemini/antigravity/mcp_config.json"}:
                        before, current = json.loads(installed), read_config(path)
                        same_registration = all(current.get("mcpServers", {}).get(k) == v for k, v in before.get("mcpServers", {}).items())
                except (ValueError, OSError, UnicodeError):
                    pass
            (live_state_changes if same_registration else drift).append(str(path))
    return {"ok": not drift and not data["conflicts"] and data["complete"], "drift": drift, "live_state_changes": live_state_changes, "conflicts": data["conflicts"], "writes": len(data["writes"])}


def rollback(receipt: Path, allowed: list[Path]) -> dict:
    data = load_receipt(receipt)
    for entry in data["writes"]:
        _contain(Path(entry["path"]), allowed)
    conflicts, restored = [], []
    for entry in reversed(data["writes"]):
        path = Path(entry["path"])
        current = path.read_bytes() if path.is_file() else None
        actual = digest(current) if current is not None else None
        if actual == entry["before_sha256"]:
            continue  # Already rolled back, or a pending write never happened.
        if actual != entry["after_sha256"]:
            conflicts.append(str(path))
            continue
        if entry["backup"]:
            backup = Path(entry["backup"])
            if not backup.resolve().is_relative_to(receipt.parent.resolve()):
                raise ValueError("backup outside receipt directory")
            prior = backup.read_bytes()
            if digest(prior) != entry["before_sha256"]:
                raise ValueError("backup integrity mismatch")
            atomic_write(path, prior)
        else:
            path.unlink()
        restored.append(str(path))
    return {"ok": not conflicts, "restored": restored, "conflicts": conflicts}


def skill_bundle(framework: Path, name: str, source: Path | None = None) -> dict[str, bytes]:
    source = source or framework / ".claude/skills" / name
    files = {}
    for path in source.rglob("*"):
        if not path.is_file() or linked(path) or any(x in SKIP for x in path.relative_to(source).parts):
            continue
        if path.suffix in {".pyc", ".pyo"} or path.name.startswith(".env"):
            continue
        data = path.read_bytes()
        if path.suffix in {".md", ".py", ".json", ".yaml", ".yml", ".toml", ".ps1", ".js"}:
            if CREDENTIAL_DATA.search(data.decode("utf-8", errors="replace")):
                raise ValueError(f"credential pattern in skill resource: {name}/{path.name}")
        files[path.relative_to(source).as_posix()] = data
    if "SKILL.md" in files:
        text = files["SKILL.md"].decode("utf-8")
        meta = frontmatter(text)
        if meta.get("name") and meta["name"] != name:
            # Discovery names follow their installed directory. Retain the
            # complete project-specific workflow and its human-facing title.
            header, remainder = text.split("---", 2)[1:]
            header = re.sub(r"(?m)^name:\s*.*$", "name: " + name, header, count=1)
            files["SKILL.md"] = ("---" + header + "---" + remainder).encode()
    # Existing compiled skills import scripts.skill_harness using an ancestor
    # of their location. Ship their shared runtime, with a location-local root.
    for rel, data in list(files.items()):
        if rel.endswith(".py") and "_runtime" not in Path(rel).parts and b"from scripts.skill_harness" in data:
            text = data.decode()
            text = text.replace("_ROOT = Path(__file__).resolve().parents[4]", "_ROOT = Path(__file__).resolve().parent / '_runtime'")
            files[rel] = text.encode()
            local_runtime = source.parent.parent.parent / "scripts/skill_harness"
            runtime = local_runtime if local_runtime.is_dir() else framework / "scripts/skill_harness"
            for helper in runtime.glob("*.py"):
                files[f"{Path(rel).parent.as_posix()}/_runtime/scripts/skill_harness/{helper.name}"] = helper.read_bytes()
    if source.resolve() == (framework / ".claude/skills" / name).resolve():
        for rel, data in list(files.items()):
            if rel.endswith(".md"):
                text = data.decode("utf-8")
                text = text.replace("Everypixel MCP", "the current project")
                text = text.replace(f".claude/skills/{name}/scripts/", "scripts/")
                for placeholder, wording in {"pip install -e .": "<documented-build-command>", "python -m pytest": "<documented-test-command>", "ruff check .": "<documented-lint-command>"}.items():
                    text = text.replace(placeholder, wording)
                if rel == "SKILL.md":
                    text += "\nResolve helper paths from this skill directory. Run project commands from the target workspace.\n"
                files[rel] = text.encode()
        if name in {"agent-memory", "eval"}:
            for helper in (framework / "scripts/agent-memory").glob("*.py"):
                text = helper.read_text(encoding="utf-8").replace("_ROOT = Path(__file__).resolve().parents[2]", "_ROOT = Path(__file__).resolve().parent.parent / '_runtime'")
                files[f"scripts/agent-memory/{helper.name}"] = text.encode()
            for helper in (framework / "scripts/agent_memory").glob("*.py"):
                files[f"scripts/_runtime/scripts/agent_memory/{helper.name}"] = helper.read_bytes()
        # Preserve Markdown references without depending on another checkout.
        for rel, data in list(files.items()):
            if not rel.endswith(".md"):
                continue
            text = data.decode("utf-8")
            for link in re.findall(r"\[[^\]]+\]\((\.\./[^)]+)\)", text):
                resource = (source / Path(rel).parent / link.split("#")[0]).resolve()
                if resource.is_file() and resource.is_relative_to(framework.resolve()) and ".git" not in resource.parts:
                    target = "references/shared/" + resource.relative_to(framework.resolve()).as_posix()
                    files[target] = resource.read_bytes()
                    replacement = os.path.relpath(target, str(Path(rel).parent)).replace("\\", "/")
                    text = text.replace("](" + link + ")", "](" + replacement + ")")
            files[rel] = text.encode()
    return files


def project_instructions(project: Path, info: dict, skills: list[str], canonical: str = ".claude") -> dict[str, bytes]:
    start, end = "<!-- BEGIN FRAMEWORK SETUP -->", "<!-- END FRAMEWORK SETUP -->"
    contract = project / "AGENTS.md"
    text = contract.read_bytes().decode("utf-8") if contract.exists() else f"# {info['name']} — agent instructions\n"
    block = "\n".join([start, "", "## Shared agent setup", "", "Project-specific instructions in this file and nested instruction files govern this workspace.",
                       f"Reusable skills are authored in `{canonical}/skills/`; other harness trees are generated.",
                       "Run installed helpers relative to their skill directory; run project checks from this workspace.",
                       "Preserve user edits, credentials, model settings, permissions and unrelated configuration.", ""])
    commands = info.get("commands", {})
    block += "\n".join(f"- {label}: `{commands[key]}`" for key, label in [("BUILD_CMD", "Build"), ("TEST_CMD", "Test"), ("LINT_CMD", "Lint")] if key in commands)
    if not commands:
        block += "Project build/test/lint commands were not detected; consult project documentation before executing checks."
    block += "\n\n" + f"Installed library: {len(skills)} applicable skills. Synchronize explicitly; startup hooks never install updates.\n" + end
    if start in text and end in text:
        text = re.sub(re.escape(start) + r".*?" + re.escape(end), lambda _: block, text, flags=re.S)
    else:
        text = text.rstrip() + "\n\n" + block + "\n"
    result = {"AGENTS.md": text.encode()}
    if not (project / "CLAUDE.md").exists():
        result["CLAUDE.md"] = b"@AGENTS.md\n"
    else:
        old = (project / "CLAUDE.md").read_bytes().decode("utf-8")
        if "@AGENTS.md" not in old:
            result["CLAUDE.md"] = (old.rstrip() + "\n\n@AGENTS.md\n").encode()
    # Antigravity reads AGENTS.md natively; the compatibility file adds no copy
    # of the instructions and does not depend on Claude's include semantics.
    if not (project / "GEMINI.md").exists():
        result["GEMINI.md"] = b"# Project guidance\n\nRead the project AGENTS.md and applicable nested instruction files before working.\n"
    return result


def rule_globs(meta: dict) -> list[str]:
    value = meta.get("globs", meta.get("paths", ""))
    if value.startswith("["):
        try:
            items = json.loads(value)
            if isinstance(items, list):
                return [str(item) for item in items]
        except ValueError:
            # Plain YAML inline arrays are common in native rule headers.
            return [item.strip().strip("\"'") for item in value[1:-1].split(",") if item.strip()]
    return [item.strip() for item in value.split(",") if item.strip()]


def antigravity_rule(text: str) -> str:
    meta = frontmatter(text)
    globs = rule_globs(meta)
    trigger = "always_on" if meta.get("alwaysApply", "").lower() == "true" else "glob" if globs else "model_decision" if meta.get("description") else "manual"
    fields = ["---", f"trigger: {trigger}", "description: " + json.dumps(meta.get("description", "Project guidance"))]
    if trigger == "glob":
        fields.append("globs: " + json.dumps(",".join(globs)))
    return "\n".join(fields) + "\n---\n\n" + body(text)


def antigravity_agent(text: str, name: str = "reviewer") -> str:
    meta = frontmatter(text)
    model = meta.get("model", "inherit")
    if model not in {"inherit", "flash", "pro"}:
        model = "inherit"
    fields = ["---", "name: " + json.dumps(meta.get("name", name)),
              "description: " + json.dumps(meta.get("description", "Review project changes")),
              "model: " + model, "mainAgent: false", "subagent: true",
              "tools: [view_file, grep_search, run_command" + (", replace_file_content" if meta.get("side_effect_level") in {"local_write", "remote_write"} else "") + "]",
              "commandExecutionPolicy: sandbox", "---", ""]
    return "\n".join(fields) + body(text)


def codex_agent(text: str, name: str) -> str:
    meta = frontmatter(text)
    return "\n".join(["name = " + json.dumps(name), "description = " + json.dumps(meta.get("description", name)),
                      "developer_instructions = " + json.dumps(body(text), ensure_ascii=False), ""])


def convert_server(source: dict, harness: str) -> tuple[dict, list[str]]:
    issues = []
    allowed = {"command", "args", "cwd", "env", "url", "serverUrl", "httpUrl", "headers", "env_vars", "type",
               "bearer_token_env_var", "startup_timeout_sec", "tool_timeout_sec", "enabled", "disabled"}
    out = {k: copy.deepcopy(v) for k, v in source.items() if k in allowed}
    if any(k in source for k in {"authProviderType", "oauth", "auth", "headersHelper", "envFile"}):
        issues.append("native authentication or envFile requires harness-specific registration")
    if source.get("disabled") is True or source.get("enabled") is False:
        issues.append("source disabled")
    env, inherited = {}, list(out.pop("env_vars", []))
    def env_ref(key):
        return "${" + ("env:" if harness == "cursor" else "") + key + "}"
    if harness != "codex":
        env.update({key: env_ref(key) for key in inherited})
    for key, value in out.pop("env", {}).items():
        reference = isinstance(value, str) and re.fullmatch(r"\$\{(?:env:)?([A-Z_][A-Z0-9_]*)\}", value)
        secret_key = re.search(r"(?i)key|token|password|secret|credential", key)
        if isinstance(value, str) and "://" in value:
            parsed_value = urlsplit(value)
            secret_key = secret_key or parsed_value.username or parsed_value.password or parsed_value.query
        if reference or secret_key:
            inherited.append(reference.group(1) if reference else key)
            if secret_key and not reference:
                issues.append(f"literal credential excluded; supply {key} through environment")
            if harness != "codex":
                env[key] = env_ref(reference.group(1) if reference else key)
        else:
            env[key] = value
    if env:
        out["env"] = env
    if harness == "codex" and inherited:
        out["env_vars"] = sorted(set(inherited))
    headers = out.get("headers", {})
    headers.update(copy.deepcopy(source.get("http_headers", {})))
    for key, variable in source.get("env_http_headers", {}).items():
        headers[key] = "${" + variable + "}"
    if harness != "codex" and out.get("bearer_token_env_var"):
        headers["Authorization"] = "Bearer " + env_ref(out.pop("bearer_token_env_var"))
    if headers:
        out["headers"] = headers
    for key, value in list(headers.items()):
        if re.search(r"(?i)authorization|key|token|secret", key):
            ref = re.search(r"\$\{(?:env:)?([A-Z_][A-Z0-9_]*)\}", str(value))
            if not ref:
                headers.pop(key)
                issues.append("literal authentication header excluded")
            elif harness == "codex":
                headers.pop(key)
                if key.lower() == "authorization":
                    out["bearer_token_env_var"] = ref.group(1)
                else:
                    out.setdefault("env_http_headers", {})[key] = ref.group(1)
            elif ref:
                headers[key] = re.sub(r"\$\{(?:env:)?[A-Z_][A-Z0-9_]*\}", lambda _: env_ref(ref.group(1)), str(value))
    if not headers:
        out.pop("headers", None)
    elif harness == "codex":
        out["http_headers"] = out.pop("headers")
    url = out.pop("url", None) or out.pop("serverUrl", None) or out.pop("httpUrl", None)
    if url:
        parsed = urlsplit(str(url))
        if parsed.username or parsed.password or parsed.query:
            issues.append("credential-bearing or query URL requires manual review")
        else:
            out["serverUrl" if harness == "antigravity" else "url"] = url
            if harness == "claude":
                out["type"] = source.get("type", "http")
            elif source.get("type") in {"sse", "ws", "websocket"}:
                issues.append("transport needs native compatibility review")
    if harness != "claude":
        out.pop("type", None)
    if harness == "cursor":
        out["type"] = "http" if url else "stdio"
    for field in ["command", "args", "cwd", "url", "serverUrl"]:
        if "${" in str(out.get(field, "")):
            issues.append("interpolated executable/path/URL needs native compatibility review")
    if harness == "codex":
        out.pop("disabled", None)
    else:
        out.pop("startup_timeout_sec", None)
        out.pop("tool_timeout_sec", None)
        out.pop("enabled", None)
        out.pop("disabled", None)
    return out, issues


def _toml_value(value) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)):
        return str(value)
    if isinstance(value, list):
        return "[" + ", ".join(_toml_value(v) for v in value) + "]"
    return json.dumps(str(value), ensure_ascii=False)


def add_toml_servers(existing: str, servers: dict) -> str:
    parsed = tomllib.loads(existing) if existing.strip() else {}
    text = existing.rstrip() + "\n"
    for name, entry in sorted(servers.items()):
        if name in parsed.get("mcp_servers", {}):
            continue
        key = "mcp_servers." + json.dumps(name)
        text += "\n[" + key + "]\n"
        for field, value in entry.items():
            if not isinstance(value, dict):
                text += field + " = " + _toml_value(value) + "\n"
        for field, mapping in entry.items():
            if isinstance(mapping, dict):
                text += "\n[" + key + "." + field + "]\n"
                text += "".join(json.dumps(k) + " = " + _toml_value(v) + "\n" for k, v in mapping.items())
    tomllib.loads(text)
    return text


def detect_project_commands(project: Path) -> dict:
    # Prefer recorded project contracts; do not execute inferred commands.
    try:
        from scripts.detect_commands import detect_commands
    except ImportError:
        sys.path.insert(0, str(ROOT))
        from scripts.detect_commands import detect_commands
    stack = "rust" if (project / "Cargo.toml").exists() else "node" if (project / "package.json").exists() else "python" if (project / "pyproject.toml").exists() or (project / "requirements.txt").exists() else "generic"
    try:
        return detect_commands(project, stack)
    except (OSError, ValueError):
        return {}


def report_markdown(report: dict) -> str:
    lines = ["# Agent setup inventory", "", "Machine-specific inventory; keep this report private and untracked.", "",
             "## Projects", "", "| Project | Update | Reason |", "|---|---|---|"]
    lines.extend(f"| {p['name']} | {'yes' if p['eligible'] else 'no'} | {p['reason']} |" for p in report["projects"])
    lines += ["", "## Skills", "", "| Scope | Project | Skill | Source |", "|---|---|---|---|"]
    lines.extend(f"| {a['scope']} | {a['project']} | {a['name']} | {a['relative']} |" for a in report["assets"] if a["kind"] == "skill")
    lines += ["", "## Summary", "", json.dumps(report["summary"], indent=2), "",
              f"Unreadable locations: {len(report['errors'])}. Duplicate groups: {len(report['duplicate_groups'])}.", ""]
    return "\n".join(lines)


def _json_bytes(value: dict) -> bytes:
    return (json.dumps(value, indent=2, ensure_ascii=False) + "\n").encode()


def native_assets(framework: Path, skill_sources: dict[str, Path], command_sources: dict[str, Path],
                  agent_sources: dict[str, Path], rule_sources: dict[str, Path], *, global_scope: bool = False,
                  antigravity_cli: bool = True) -> dict[str, bytes]:
    result: dict[str, bytes] = {}
    skill_roots = [".claude/skills", ".agents/skills"]
    if global_scope:
        skill_roots += [".gemini/config/skills"]
        if antigravity_cli:
            skill_roots += [".gemini/antigravity-cli/skills"]
    # Cursor discovers .agents/skills and .claude/skills; avoid an additional
    # generated skill directory in deployment. The framework's legacy mirrors
    # are still generated by its source-of-truth synchronizer.
    for name, source in skill_sources.items():
        for rel, data in skill_bundle(framework, name, source).items():
            for prefix in skill_roots:
                result[f"{prefix}/{name}/{rel}"] = data
    for name, source in command_sources.items():
        text = source.read_bytes().decode("utf-8")
        if source.is_relative_to(framework):
            text = text.replace("Everypixel MCP", "the current project")
        result[f".claude/commands/{name}.md"] = text.encode()
        result[f".cursor/commands/{name}.md"] = text.encode()
        alias = "framework-" + name
        # Explicit commands stay explicit across adapters. The namespace avoids
        # collisions with built-in commands such as /plan and /review.
        generated = "---\nname: " + alias + "\ndescription: " + json.dumps("Explicit framework workflow: " + name) + "\ndisable-model-invocation: true\n---\n\n" + body(text)
        for prefix in skill_roots:
            result[f"{prefix}/{alias}/SKILL.md"] = generated.encode()
    for name, source in agent_sources.items():
        text = source.read_bytes().decode("utf-8")
        if source.is_relative_to(framework):
            text = text.replace("Everypixel MCP", "the current project")
        result[f".claude/agents/{name}.md"] = text.encode()
        result[f".cursor/agents/{name}.md"] = text.encode()
        result[f".codex/agents/{name}.toml"] = codex_agent(text, name).encode()
        prefix = ".gemini/config/agents" if global_scope else ".agents/agents"
        result[f"{prefix}/{name}.md"] = antigravity_agent(text, name).encode()
        if global_scope and antigravity_cli:
            result[f".gemini/antigravity-cli/agents/{name}.md"] = antigravity_agent(text, name).encode()
    for name, source in rule_sources.items():
        text = source.read_bytes().decode("utf-8")
        meta = frontmatter(text)
        globs = rule_globs(meta)
        cursor_source = source.suffix == ".mdc" or ".cursor" in source.parts
        if cursor_source and meta.get("alwaysApply", "").lower() != "true" and not globs:
            # Claude has no model-decision rule trigger. Keep this guidance
            # explicitly invocable instead of accidentally making it always-on.
            alias = "project-rule-" + name
            result[f".claude/skills/{alias}/SKILL.md"] = ("---\nname: " + alias + "\ndescription: " + json.dumps("Explicit project rule: " + meta.get("description", name)) + "\ndisable-model-invocation: true\n---\n\n" + body(text)).encode()
        elif cursor_source:
            header = "---\npaths: " + json.dumps(globs) + "\n---\n\n" if globs else ""
            result[f".claude/rules/{name}.md"] = (header + body(text)).encode()
        else:
            result[f".claude/rules/{name}.md"] = text.encode()
        if cursor_source or "alwaysApply" in meta or "globs" in meta:
            result[f".cursor/rules/{name}.mdc"] = text.encode()
        else:
            header = "---\ndescription: " + json.dumps(meta.get("description", name)) + "\nalwaysApply: " + ("false" if globs else "true") + "\n"
            if globs:
                header += "globs: " + json.dumps(",".join(globs)) + "\n"
            result[f".cursor/rules/{name}.mdc"] = (header + "---\n\n" + body(text)).encode()
        prefix = ".gemini/config/rules" if global_scope else ".agents/rules"
        result[f"{prefix}/{name}.md"] = antigravity_rule(text).encode()
    if not global_scope:
        for directory in ["scripts/agent-memory", "scripts/agent_memory", "scripts/skill_harness", ".agent/workflows"]:
            for resource in (framework / directory).glob("*"):
                if resource.is_file() and resource.suffix in {".py", ".md"}:
                    result[f"{directory}/{resource.name}"] = resource.read_bytes()
        for resource in (framework / ".agent").glob("*.md"):
            if resource.name not in {"SKILL_INVENTORY.md", "SESSION_NOTES.md"}:
                result[f".agent/{resource.name}"] = resource.read_bytes()
        for name in ["schema.md", "CURSOR_USAGE.md"]:
            resource = framework / ".agent-memory" / name
            if resource.exists():
                result[f".agent-memory/{name}"] = resource.read_bytes()
    return result


def owned_files(state: Path, target: Path) -> dict:
    key = digest(str(target.resolve()).encode())[:20]
    manifest = state / "targets" / (key + ".json")
    if not manifest.exists():
        return {}
    data = json.loads(manifest.read_text(encoding="utf-8"))
    if Path(data["root"]).resolve() != target.resolve():
        raise ValueError("ownership manifest target mismatch")
    return data["files"]


def save_ownership(state: Path, receipt: Path, target: Path) -> None:
    owned = owned_files(state, target)
    run = load_receipt(receipt)
    for entry in run["writes"]:
        path = Path(entry["path"])
        if path.is_relative_to(target) and entry["status"] == "written":
            rel = path.relative_to(target).as_posix()
            if entry["after_sha256"] is None:
                owned.pop(rel, None)
            else:
                owned[rel] = {"content": entry["content"], "sha256": entry["after_sha256"]}
    key = digest(str(target.resolve()).encode())[:20]
    write_json(state / "targets" / (key + ".json"), {"root": str(target), "files": owned})


def library_sources(framework: Path, manifest: dict, project_name: str | None = None) -> tuple[dict, dict, dict, dict]:
    skills = {}
    for entry in manifest["skills"]:
        if entry["pack"] == "core" or project_name is None and entry.get("global", False) or project_name is not None and project_name in entry.get("projects", []):
            skills[entry["id"]] = framework / entry["source"]
    commands = {p.stem: p for p in (framework / ".claude/commands").glob("*.md")}
    agents = {p.stem: p for p in (framework / ".claude/agents").glob("*.md")}
    rules = {p.stem: p for p in (framework / ".claude/rules").glob("*.md")}
    return skills, commands, agents, rules


def _mcp_sources(root: Path, global_scope: bool) -> dict:
    paths = [".cursor/mcp.json", ".mcp.json", ".codex/config.toml"]
    if global_scope:
        paths = [".codex/config.toml", ".cursor/mcp.json", ".claude.json", ".gemini/config/mcp_config.json", ".gemini/antigravity/mcp_config.json"]
    servers = {}
    for rel in paths:
        path = root / rel
        if not path.exists():
            continue
        try:
            data = read_config(path)
        except (ValueError, OSError):
            continue
        for name, server in data.get("mcp_servers", data.get("mcpServers", {})).items():
            if isinstance(server, dict) and name not in servers:
                servers[name] = server
    if global_scope:
        # Project endpoints are never promoted just because they appear in a
        # user-level config. Keep existing registrations, but do not spread them.
        servers = {name: value for name, value in servers.items()
                   if any(x in name.lower() for x in ["llmwiki", "jev", "agent-mail", "openaideveloperdocs", "context7", "fff", "graphify", "github", "docker-mcp", "subagent-orchestrator"])
                   and not any(x in name.lower() for x in ["project-twelve", "unity", "is-be", "ingame"])}
    return servers


def dependency_issues(server: dict) -> list[str]:
    issues = []
    command = server.get("command")
    if command and not (Path(command).is_file() or shutil.which(command)):
        issues.append("executable unavailable")
    for arg in server.get("args", []):
        if not isinstance(arg, str):
            issues.append("argument is not a string")
        elif re.match(r"(?i)(--api[-_]key|--token|--password|--secret)(=|$)", arg):
            issues.append("credential CLI argument requires review")
        elif Path(arg).is_absolute() and not Path(arg).exists():
            issues.append("absolute argument path unavailable")
    return issues


def mcp_files(root: Path, *, global_scope: bool) -> tuple[dict[str, bytes], list[dict], set[str]]:
    sources = _mcp_sources(root, global_scope)
    files, diagnostics, adopt = {}, [], set()
    locations = {"claude": ".claude.json" if global_scope else ".mcp.json",
                 "cursor": ".cursor/mcp.json", "codex": ".codex/config.toml",
                 "antigravity": ".gemini/config/mcp_config.json" if global_scope else ".agents/mcp_config.json"}
    if global_scope and (root / ".gemini/antigravity/mcp_config.json").exists():
        locations["antigravity-legacy"] = ".gemini/antigravity/mcp_config.json"
    for harness, rel in locations.items():
        path = root / rel
        converted = {}
        for name, server in sources.items():
            if not global_scope:
                server = copy.deepcopy(server)
                for field in ["command", "cwd", "args"]:
                    values = server.get(field)
                    def resolve(value):
                        return value.replace("${workspaceFolder}", str(root.absolute())).replace("${/}", os.sep) if isinstance(value, str) else value
                    if isinstance(values, list):
                        server[field] = [resolve(value) for value in values]
                    elif values is not None:
                        server[field] = resolve(values)
            entry, issues = convert_server(server, harness.split("-")[0])
            issues += dependency_issues(entry)
            if issues:
                diagnostics.append({"harness": harness, "server": name, "status": "preserved_existing/not_added", "issues": issues})
                continue
            converted[name] = entry
        try:
            if harness == "codex":
                old = path.read_text(encoding="utf-8") if path.exists() else ""
                new = add_toml_servers(old, converted)
                files[rel] = new.encode()
            else:
                old = read_config(path) if path.exists() else {}
                new = merge_json(old, {"mcpServers": converted})
                files[rel] = path.read_bytes() if path.exists() and new == old else _json_bytes(new)
            adopt.add(rel)
        except (OSError, ValueError) as exc:
            diagnostics.append({"harness": harness, "status": "invalid existing config preserved", "issues": [type(exc).__name__]})
    return files, diagnostics, adopt


def _instructions_merge(path: Path, addition: str) -> bytes:
    old = path.read_bytes().decode("utf-8") if path.exists() else ""
    start, end = "<!-- BEGIN FRAMEWORK GLOBAL -->", "<!-- END FRAMEWORK GLOBAL -->"
    block = start + "\n" + addition.strip() + "\n" + end
    if start in old and end in old:
        old = re.sub(re.escape(start) + r".*?" + re.escape(end), lambda _: block, old, flags=re.S)
    else:
        old = old.rstrip() + "\n\n" + block + "\n"
    return old.encode()


def _project_sources(framework: Path, project: Path, manifest: dict, owned: dict | None = None):
    selected = list(library_sources(framework, manifest, project.name))
    # Existing project canonical assets carry real project contracts. Preserve
    # these and generate missing/native mirrors from them, rather than replacing
    # project-specific versions with a generic source.
    for index, kind in enumerate(["skills", "commands", "agents", "rules"]):
        canonical = manifest.get("project_sync_contracts", {}).get(project.name, {}).get("canonical", ".claude")
        prefixes = [".agent", ".agents", ".claude", ".cursor"] if canonical == ".cursor" else [".agent", ".agents", ".cursor", ".claude"]
        for prefix in prefixes:
            directory = project / prefix / kind
            if not directory.is_dir():
                continue
            if kind == "skills":
                for skill in directory.iterdir():
                    if skill.is_dir() and not linked(skill) and (skill / "SKILL.md").exists():
                        meta = frontmatter((skill / "SKILL.md").read_text(encoding="utf-8"))
                        if skill.name.startswith("framework-") and meta.get("description", "").startswith("Explicit framework workflow:"):
                            continue
                        if skill.name.startswith("project-rule-") and meta.get("description", "").startswith("Explicit project rule:"):
                            continue
                        if skill.name in selected[index] and (skill / "SKILL.md").relative_to(project).as_posix() in (owned or {}):
                            continue
                        selected[index][skill.name] = skill
            else:
                for asset in directory.glob("*"):
                    if asset.is_file() and asset.suffix in {".md", ".mdc"} and asset.stem.lower() not in {"readme", "index"}:
                        if asset.stem in selected[index] and asset.relative_to(project).as_posix() in (owned or {}):
                            continue
                        selected[index][asset.stem] = asset
    return selected


def project_sync_contract(project: Path, files: dict, contract: dict, owned: dict, state: Path):
    """Render a reviewed repo's own generator in an isolated temporary tree.

    Only hash-reviewed stdlib generators can run. No real destination is
    touched while planning, and MCP, permission, hook and Git files are absent.
    Native canonical direction and repository-specific rule conversions win.
    """
    script_rel = "scripts/sync_assistant_trees.py"
    script = project / script_rel
    current = script.read_bytes()
    baseline = owned.get(script_rel)
    if digest(current) != contract["sha256"] and not (baseline and digest(current) == baseline["sha256"]):
        raise ValueError(f"unreviewed project synchronization script: {project.name}")
    source = current.decode("utf-8").replace("\r\n", "\n")
    source = source.replace("shutil.copytree(child, dst / child.name)", 'shutil.copytree(child, dst / child.name, ignore=shutil.ignore_patterns("__pycache__", "*.pyc", "*.pyo"))')
    source = source.replace("shutil.copytree(child, CODEX_SKILLS / child.name)", 'shutil.copytree(child, CODEX_SKILLS / child.name, ignore=shutil.ignore_patterns("__pycache__", "*.pyc", "*.pyo"))')
    if 'if "__pycache__" in path.parts or path.suffix in {".pyc", ".pyo"}:' not in source:
        source = source.replace('for path in root.rglob("*"):\n', 'for path in root.rglob("*"):\n        if "__pycache__" in path.parts or path.suffix in {".pyc", ".pyo"}:\n            continue\n')
    source = source.replace("if sub.is_file():", 'if sub.is_file() and "__pycache__" not in sub.parts and sub.suffix not in {".pyc", ".pyo"}:')
    prefixes = tuple(f"{h}/{k}/" for h in [".claude", ".cursor"] for k in ["skills", "commands", "agents", "rules"])
    prefixes += (".agents/skills/", ".codex/agents/")
    staging = state / "staging"
    staging.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=project.name + "-", dir=staging) as temporary:
        root = Path(temporary)
        existing = {}
        for prefix in prefixes:
            directory = project / prefix
            if not directory.is_dir():
                continue
            for path in directory.rglob("*"):
                if not path.is_file() or linked(path) or any(part in SKIP for part in path.relative_to(directory).parts) or path.name.startswith(".env"):
                    continue
                rel = path.relative_to(project).as_posix()
                existing[rel] = path.read_bytes()
                dest = root / rel
                dest.parent.mkdir(parents=True, exist_ok=True)
                dest.write_bytes(existing[rel])
        for rel, content in files.items():
            if rel.startswith(prefixes) or rel == "AGENTS.md":
                dest = root / rel
                dest.parent.mkdir(parents=True, exist_ok=True)
                dest.write_bytes(content)
        if contract["canonical"] == ".cursor":
            for rel, content in files.items():
                if rel.startswith(".claude/skills/"):
                    dest = root / rel.replace(".claude/skills/", ".cursor/skills/", 1)
                    dest.parent.mkdir(parents=True, exist_ok=True)
                    dest.write_bytes(content)
        (root / "scripts").mkdir(exist_ok=True)
        module = types.ModuleType("reviewed_project_sync")
        module.__file__ = str(root / script_rel)
        with contextlib.redirect_stdout(io.StringIO()):
            exec(compile(source, module.__file__, "exec"), module.__dict__)
            function = module.sync_cursor_to_claude if contract["canonical"] == ".cursor" else module.sync
            if function(check=False) != 0:
                raise ValueError("project generator failed")
        rendered = {}
        for prefix in prefixes:
            for path in (root / prefix).rglob("*"):
                if path.is_file() and not any(part in SKIP for part in path.relative_to(root).parts):
                    rendered[path.relative_to(root).as_posix()] = path.read_bytes()
        if (root / ".agents/AGENTS.md").is_file():
            rendered[".agents/AGENTS.md"] = (root / ".agents/AGENTS.md").read_bytes()
        # Preserve the repo generator's Codex agent serialization exactly.
        # Plan comparison may otherwise retain a semantically equivalent TOML
        # spelling that an older strict byte comparison rejects.
        exact = {rel for rel in rendered if rel.startswith(".codex/agents/")}
        deletions = []
        for rel in set(existing) - set(rendered):
            path = project / rel
            deletions.append({"path": str(path.absolute()), "relative": rel, "action": "delete", "before_sha256": digest(existing[rel]), "after_sha256": None, "content": "", "before_content": None})
        for rel in list(files):
            if rel.startswith(prefixes):
                files.pop(rel)
        files.update(rendered)
        files[script_rel] = source.encode()
        return set(rendered) | {script_rel}, deletions, exact


def build_plan(framework: Path, projects_root: Path, user: Path, state: Path,
               selected_projects: list[str] | None = None, scope: str = "all") -> dict:
    manifest = json.loads((framework / ".agent/setup/library.json").read_text(encoding="utf-8"))
    operations, targets, coverage, diagnostics = [], [], [], []
    global_sources = library_sources(framework, manifest)
    global_files = native_assets(framework, *global_sources, global_scope=True)
    # Bring existing personal copies onto the same portable content without
    # creating more legacy discovery roots. Only reviewed hashes can be adopted.
    reviewed = manifest.get("reviewed_global_adoptions", [])
    global_owned = owned_files(state, user)
    global_reviewed_adopt = set()
    for entry in reviewed:
        rel = entry["relative"]
        path = user / rel
        if not path.is_file() or digest(path.read_bytes()) != entry["sha256"] and rel not in global_owned:
            continue
        skill_root = Path(rel).parent
        source = global_sources[0].get(entry["skill"])
        if source:
            for child, content in skill_bundle(framework, entry["skill"], source).items():
                target = (skill_root / child).as_posix()
                global_files[target] = content
                # Retain unknown changed helpers; SKILL.md is the reviewed file.
                if child == "SKILL.md" and digest(path.read_bytes()) == entry["sha256"]:
                    global_reviewed_adopt.add(target)
    for entry in manifest.get("reviewed_resource_adoptions", []):
        path = user / entry["relative"]
        if entry["relative"] in global_files and path.is_file() and digest(path.read_bytes()) == entry["sha256"]:
            global_reviewed_adopt.add(entry["relative"])
    # Global rules must not drag project scaffold assumptions, unresolved board
    # IDs or project-local links into every repository.
    for rel in list(global_files):
        if rel.startswith((".claude/rules/", ".cursor/rules/", ".gemini/config/rules/")):
            del global_files[rel]
    global_guidance = (framework / ".agent/setup/global-instructions.md").read_text(encoding="utf-8")
    for rel in [".claude/CLAUDE.md", ".codex/AGENTS.md", ".gemini/GEMINI.md"]:
        global_files[rel] = _instructions_merge(user / rel, global_guidance)
    global_files[".cursor/rules/framework-shared.mdc"] = ("---\ndescription: Shared coding workflow\nalwaysApply: true\n---\n\n" + global_guidance).encode()
    global_files[".gemini/config/rules/framework-shared.md"] = ("---\ntrigger: always_on\ndescription: Shared coding workflow\n---\n\n" + global_guidance).encode()
    mcp, issues, global_adopt = mcp_files(user, global_scope=True)
    global_files.update(mcp)
    global_adopt |= global_reviewed_adopt
    global_adopt |= {".claude/CLAUDE.md", ".codex/AGENTS.md", ".gemini/GEMINI.md"}
    diagnostics.extend({"target": "global", **issue} for issue in issues)
    infos = [project_info(p) for p in sorted(projects_root.iterdir()) if p.is_dir() and not linked(p)]
    names = set(selected_projects or [])
    if names - {i["name"] for i in infos if i["eligible"]}:
        raise ValueError("selected project is absent or ineligible")
    local_equivalents = []
    global_bundles = {}
    for rel, content in global_files.items():
        if rel.startswith(".agents/skills/"):
            parts = Path(rel).parts
            global_bundles.setdefault(parts[2], {})["/".join(parts[3:])] = digest(content)
    if scope != "global":
        for info in infos:
            project = Path(info["root"])
            if not info["eligible"] or names and info["name"] not in names or project.resolve() == framework.resolve():
                continue
            owned = owned_files(state, project)
            print("plan: " + info["name"], file=sys.stderr, flush=True)
            sources = _project_sources(framework, project, manifest, owned)
            files = native_assets(framework, *sources)
            for rel in list(files):
                if (rel.startswith(".agent/") or rel.startswith(".agent-memory/")) and (project / rel).exists():
                    files[rel] = (project / rel).read_bytes()
                # Existing native variants and runtime implementations remain
                # authoritative. Skill-local runtime bundles make new library
                # helpers portable without replacing a project's shared code.
                if rel not in owned and rel.startswith((".cursor/commands/", ".cursor/agents/", ".cursor/rules/", "scripts/")) and (project / rel).is_file():
                    files[rel] = (project / rel).read_bytes()
            canonical = manifest.get("project_sync_contracts", {}).get(project.name, {}).get("canonical", ".claude")
            files.update(project_instructions(project, {**info, "commands": detect_project_commands(project)}, list(sources[0]), canonical))
            # Give Codex the always-on project rules through its native contract.
            always = [name for name, source in sources[3].items() if frontmatter(source.read_text(encoding="utf-8")).get("alwaysApply", "").lower() == "true"]
            if always:
                agents = files["AGENTS.md"].decode()
                marker = "<!-- FRAMEWORK RULE REFERENCES -->"
                section = marker + "\nRead the always-on project rules before working:\n" + "\n".join(f"- `.claude/rules/{name}.md`" for name in sorted(always)) + "\n<!-- END FRAMEWORK RULE REFERENCES -->"
                if marker in agents:
                    agents = re.sub(re.escape(marker) + r".*?<!-- END FRAMEWORK RULE REFERENCES -->", lambda _: section, agents, flags=re.S)
                else:
                    agents = agents.rstrip() + "\n\n" + section + "\n"
                files["AGENTS.md"] = agents.encode()
            ignore = (project / ".gitignore").read_bytes().decode("utf-8") if (project / ".gitignore").exists() else ""
            for pattern in ["/.agent/local/", "/.cursor/mcp.json", "/.claude/settings.local.json", "/.agents/mcp_config.json"]:
                if pattern not in ignore.splitlines():
                    ignore = ignore.rstrip() + "\n" + pattern + "\n"
            files[".gitignore"] = ignore.encode()
            mcp, issues, adopt = mcp_files(project, global_scope=False)
            files.update(mcp)
            adopt |= {"AGENTS.md", "CLAUDE.md", "GEMINI.md", ".gitignore"}
            for entry in manifest.get("reviewed_project_adoptions", []):
                path = project / entry["relative"]
                if entry["project"] == project.name and path.is_file() and digest(path.read_bytes()) == entry["sha256"]:
                    adopt.add(entry["relative"])
            # Packaging an existing skill's helper imports changes only how its
            # same code is located; preserve its actual workflow and resources.
            for rel in files:
                if rel.startswith(".claude/skills/"):
                    canonical = project / rel
                    if canonical.exists() and any(canonical.is_relative_to(src) for src in sources[0].values()):
                        original = canonical.read_bytes()
                        if b"from scripts.skill_harness" in original:
                            adopt.add(rel)
                if rel.startswith(".agents/skills/"):
                    parts = Path(rel).parts
                    source = sources[0].get(parts[2])
                    current = project / rel
                    origin = source.joinpath(*parts[3:]) if source else None
                    if current.is_file() and origin and origin.is_file():
                        if current.read_bytes().replace(b"\r\n", b"\n") == origin.read_bytes().replace(b"\r\n", b"\n"):
                            adopt.add(rel)
            deletions, exact = [], set()
            contract = manifest.get("project_sync_contracts", {}).get(project.name)
            if contract:
                generated_adopt, deletions, exact = project_sync_contract(project, files, contract, owned, state)
                adopt |= generated_adopt
            target_ops = plan_files(project, files, owned, adopt)
            for op in target_ops:
                if op["relative"] in exact:
                    wanted = files[op["relative"]]
                    op["content"], op["after_sha256"] = base64.b64encode(wanted).decode(), digest(wanted)
                    op["action"] = "unchanged" if op["before_sha256"] == op["after_sha256"] else "update" if op["before_sha256"] else "create"
            target_ops += deletions
            operations += target_ops
            targets.append(str(project))
            conflicts = [op["relative"] for op in target_ops if op["action"] == "conflict"]
            coverage.append({"project": info["name"], "root": str(project), "skills": len(sources[0]),
                             "commands": len(sources[1]), "agents": len(sources[2]), "rules": len(sources[3]),
                             "conflicts": conflicts, "commands_detected": detect_project_commands(project)})
            diagnostics.extend({"target": info["name"], **issue} for issue in issues)
            bundles, conflicting = {}, set()
            for op in target_ops:
                if op["relative"].startswith(".agents/skills/"):
                    parts = Path(op["relative"]).parts
                    bundles.setdefault(parts[2], {})["/".join(parts[3:])] = op["after_sha256"]
                    if op["action"] == "conflict":
                        conflicting.add(parts[2])
            for name, bundle in bundles.items():
                if name not in conflicting and bundle == global_bundles.get(name):
                    local_equivalents.append(project / ".agents/skills" / name / "SKILL.md")
    # Codex explicitly exposes same-name copies. Disable only equivalent repo
    # copies in workstation state; repository files remain standalone elsewhere.
    codex_rel = ".codex/config.toml"
    codex_text = global_files.get(codex_rel, (user / codex_rel).read_bytes() if (user / codex_rel).exists() else b"").decode()
    parsed = tomllib.loads(codex_text) if codex_text.strip() else {}
    configured = {entry.get("path") for entry in parsed.get("skills", {}).get("config", [])}
    for entry in reviewed:
        if entry["relative"].startswith(".codex/skills/"):
            local_equivalents.append(user / entry["relative"])
    for path in local_equivalents:
        absolute = str(path.absolute())
        if absolute not in configured:
            codex_text += '\n[[skills.config]]\npath = ' + json.dumps(absolute) + '\nenabled = false\n'
    global_files[codex_rel] = codex_text.encode()
    global_adopt.add(codex_rel)
    if scope != "projects":
        operations += plan_files(user, global_files, owned_files(state, user), global_adopt)
        targets.append(str(user.absolute()))
    summary = {"targets": len(targets), "operations": len(operations),
               **{action: sum(op["action"] == action for op in operations) for action in ["create", "update", "delete", "unchanged", "conflict"]},
               "dependency_diagnostics": len(diagnostics)}
    return {"schema_version": SCHEMA_VERSION, "allowed_roots": [str(p.resolve()) for p in [user, projects_root]],
            "targets": targets, "operations": operations, "coverage": coverage,
            "diagnostics": diagnostics, "summary": summary,
            "library_sha256": digest((framework / ".agent/setup/library.json").read_bytes()),
            "generator_sha256": digest(Path(__file__).read_bytes())}


def validate_plan(plan: dict, projects_root: Path, user: Path, framework: Path) -> list[Path]:
    if plan.get("schema_version") != SCHEMA_VERSION:
        raise ValueError("unsupported plan schema")
    if plan.get("library_sha256") != digest((framework / ".agent/setup/library.json").read_bytes()):
        raise ValueError("library changed after planning")
    if plan.get("generator_sha256") != digest(Path(__file__).read_bytes()):
        raise ValueError("installer changed after planning")
    targets = []
    for value in plan["targets"]:
        target = Path(value).resolve()
        if linked(Path(value)):
            raise ValueError("linked target")
        if target != user.resolve():
            if target.parent != projects_root.resolve() or not project_info(target)["eligible"]:
                raise ValueError("target no longer eligible")
        targets.append(target)
    for op in plan["operations"]:
        path = Path(op["path"])
        matches = [t for t in targets if path.is_relative_to(t)]
        if len(matches) != 1 or path.relative_to(matches[0]).as_posix() != op["relative"]:
            raise ValueError("operation differs from reviewed target")
        rel = Path(op["relative"])
        if rel.parts[0] not in {".claude", ".cursor", ".agents", ".codex", ".gemini", ".agent", ".agent-memory", "scripts", "AGENTS.md", "CLAUDE.md", "GEMINI.md", ".gitignore", ".mcp.json", ".claude.json"}:
            raise ValueError("not an agent setup destination")
        if rel.parts[0] == "scripts" and op["relative"] != "scripts/sync_assistant_trees.py" and (len(rel.parts) < 3 or rel.parts[1] not in {"agent-memory", "agent_memory", "skill_harness"}):
            raise ValueError("not a bundled runtime destination")
        if path.name in {"settings.json", "settings.local.json", "cli-config.json", "config.json", "hooks.json"}:
            raise ValueError("installer may not replace permissions or hook settings")
        _contain(path, targets)
    return targets


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["inventory", "plan", "apply", "check", "rollback"])
    parser.add_argument("--projects-root", type=Path, default=ROOT.parent)
    parser.add_argument("--user-root", type=Path, default=Path.home())
    parser.add_argument("--framework", type=Path, default=ROOT)
    parser.add_argument("--state", type=Path, default=ROOT / ".agent/local/setup")
    parser.add_argument("--out", type=Path)
    parser.add_argument("--input", type=Path)
    parser.add_argument("--project", action="append", default=[])
    parser.add_argument("--scope", choices=["all", "global", "projects"], default="all")
    args = parser.parse_args(argv)
    if args.action == "inventory":
        report = inventory(args.projects_root, args.user_root)
        output = args.out or args.state / "inventory.json"
        write_json(output, report)
        atomic_write(output.with_suffix(".md"), report_markdown(report).encode())
        print(json.dumps({"report": str(output), **report["summary"], "errors": len(report["errors"])}))
        return 0 if not report["errors"] else 1
    if args.action in {"check", "rollback"}:
        if not args.input:
            parser.error("--input receipt.json is required")
        result = check_run(args.input) if args.action == "check" else rollback(args.input, [args.user_root, args.projects_root])
        print(json.dumps(result, indent=2))
        return 0 if result["ok"] else 1
    if args.action == "plan":
        plan = build_plan(args.framework, args.projects_root, args.user_root, args.state, args.project, args.scope)
        output = args.out or args.state / "plan.json"
        write_json(output, plan)
        print(json.dumps({"plan": str(output), **plan["summary"]}))
        return 0
    if not args.input:
        parser.error("--input plan.json is required; apply never regenerates a plan")
    plan = json.loads(args.input.read_text(encoding="utf-8"))
    allowed = [args.user_root, args.projects_root]
    # Explicit CLI roots must match those reviewed in the plan.
    if {str(p.resolve()) for p in allowed} != set(plan["allowed_roots"]):
        parser.error("plan roots differ from the supplied target roots")
    targets = validate_plan(plan, args.projects_root, args.user_root, args.framework)
    receipt = apply_operations(plan["operations"], args.state, targets)
    for target in plan["targets"]:
        save_ownership(args.state, receipt, Path(target))
    print(json.dumps({"receipt": str(receipt), **check_run(receipt)}))
    return 0 if check_run(receipt)["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
