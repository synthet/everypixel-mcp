#!/usr/bin/env python3
"""Detect build/test/lint commands from a project directory.

Probes common config files to infer BUILD_CMD, TEST_CMD, and LINT_CMD.
Returns only keys that were confidently detected; callers should fall back
to stack defaults for any missing keys.

Usage (standalone):
    python scripts/detect_commands.py --target . --stack python
    python scripts/detect_commands.py --target ../my-app --stack rust
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import tomllib
from pathlib import Path
from typing import Any

COMMAND_KEYS = ("BUILD_CMD", "TEST_CMD", "LINT_CMD")


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="ignore")


def _read_toml(path: Path) -> dict[str, Any]:
    try:
        return tomllib.loads(_read_text(path))
    except (OSError, tomllib.TOMLDecodeError):
        return {}


def _makefile_targets(target: Path) -> set[str]:
    """Return the set of top-level Makefile target names."""
    makefile = target / "Makefile"
    if not makefile.is_file():
        return set()
    targets: set[str] = set()
    for line in _read_text(makefile).splitlines():
        m = re.match(r"^([a-zA-Z0-9_-]+)\s*:", line)
        if m:
            targets.add(m.group(1))
    return targets


def _just_targets(target: Path) -> set[str]:
    justfile = target / "justfile"
    if not justfile.is_file():
        return set()
    targets: set[str] = set()
    for line in _read_text(justfile).splitlines():
        m = re.match(r"^([a-zA-Z0-9_-]+)\s*(?:[\w-]+\s*)*:", line)
        if m:
            targets.add(m.group(1))
    return targets


def _taskfile_targets(target: Path) -> set[str]:
    taskfile = target / "Taskfile.yml"
    if not taskfile.is_file():
        return set()
    targets: set[str] = set()
    in_tasks = False
    for line in _read_text(taskfile).splitlines():
        if re.match(r"^tasks:\s*$", line):
            in_tasks = True
            continue
        if in_tasks:
            m = re.match(r"^  ([a-zA-Z0-9_-]+):\s*", line)
            if m:
                targets.add(m.group(1))
            elif line and not line.startswith(" "):
                in_tasks = False
    return targets


def _mise_tasks(target: Path) -> set[str]:
    data = _read_toml(target / ".mise.toml") if (target / ".mise.toml").is_file() else {}
    tasks = data.get("tasks")
    return set(tasks) if isinstance(tasks, dict) else set()


def _apply_runner(result: dict[str, str], targets: set[str], runner: str) -> None:
    for key, name in (("BUILD_CMD", "build"), ("TEST_CMD", "test"), ("LINT_CMD", "lint")):
        if key not in result and name in targets:
            result[key] = f"{runner} {name}"


def _python_runner(target: Path) -> tuple[str, str]:
    if (target / "uv.lock").is_file():
        return "uv run ", "uv sync"
    if (target / "poetry.lock").is_file():
        return "poetry run ", "poetry install"
    return "", "pip install -e ."


def detect_python_commands(target: Path) -> dict[str, str]:
    result: dict[str, str] = {}
    make_targets = _makefile_targets(target)
    run_prefix, install_cmd = _python_runner(target)
    pyproject = target / "pyproject.toml"
    pyproject_data = _read_toml(pyproject) if pyproject.is_file() else {}
    tool = pyproject_data.get("tool", {}) if isinstance(pyproject_data.get("tool"), dict) else {}

    build_system = pyproject_data.get("build-system", {})
    has_build_backend = isinstance(build_system, dict) and "build-backend" in build_system
    if has_build_backend or (target / "setup.py").is_file() or (target / "setup.cfg").is_file():
        result["BUILD_CMD"] = install_cmd
    elif "install" in make_targets:
        result["BUILD_CMD"] = "make install"

    if "test" in make_targets:
        result["TEST_CMD"] = "make test"
    elif (target / "pytest.ini").is_file() or "pytest" in tool or (target / "tests").is_dir():
        result["TEST_CMD"] = f"{run_prefix}pytest" if run_prefix else "python -m pytest"

    if "lint" in make_targets:
        result["LINT_CMD"] = "make lint"
    else:
        linters: list[str] = []
        if (target / "ruff.toml").is_file() or "ruff" in tool:
            linters.append(f"{run_prefix}ruff check ." if run_prefix else "ruff check .")
        if (target / "mypy.ini").is_file() or "mypy" in tool:
            linters.append(f"{run_prefix}mypy ." if run_prefix else "mypy .")
        if linters:
            result["LINT_CMD"] = " && ".join(linters)

    return result


def _node_package_manager(target: Path) -> tuple[str, str]:
    if (target / "pnpm-lock.yaml").is_file():
        return "pnpm", "pnpm install"
    if (target / "yarn.lock").is_file():
        return "yarn", "yarn install"
    if (target / "bun.lockb").is_file():
        return "bun", "bun install"
    if (target / "package-lock.json").is_file():
        return "npm", "npm ci"
    return "npm", "npm install"


def _node_run(pm: str, script: str) -> str:
    if pm == "npm":
        return "npm test" if script == "test" else f"npm run {script}"
    return f"{pm} run {script}"


def detect_node_commands(target: Path) -> dict[str, str]:
    result: dict[str, str] = {}
    pkg = target / "package.json"
    if not pkg.is_file():
        return result
    try:
        data = json.loads(_read_text(pkg))
    except (json.JSONDecodeError, OSError):
        return result
    scripts = data.get("scripts") or {}
    pm, install_cmd = _node_package_manager(target)

    result["BUILD_CMD"] = _node_run(pm, "build") if "build" in scripts else install_cmd
    if "test" in scripts:
        result["TEST_CMD"] = _node_run(pm, "test")
    if "lint" in scripts:
        result["LINT_CMD"] = _node_run(pm, "lint")
    elif "typecheck" in scripts or "type-check" in scripts:
        result["LINT_CMD"] = _node_run(pm, "typecheck" if "typecheck" in scripts else "type-check")

    return result


def detect_go_commands(target: Path) -> dict[str, str]:
    result: dict[str, str] = {}
    if not (target / "go.mod").is_file():
        return result

    make_targets = _makefile_targets(target)

    result["BUILD_CMD"] = "make build" if "build" in make_targets else "go build ./..."
    result["TEST_CMD"] = "make test" if "test" in make_targets else "go test ./..."
    result["LINT_CMD"] = "make lint" if "lint" in make_targets else "go vet ./... && gofmt -l ."

    return result


def detect_rust_commands(target: Path) -> dict[str, str]:
    result: dict[str, str] = {}
    if not (target / "Cargo.toml").is_file():
        return result

    make_targets = _makefile_targets(target)
    has_nextest = (target / "nextest.toml").is_file() or (target / ".config" / "nextest.toml").is_file()
    has_script_clippy = (target / "script" / "clippy").is_file() or (
        target / "script" / "clippy.ps1"
    ).is_file()

    result["BUILD_CMD"] = "make build" if "build" in make_targets else "cargo build"
    if "test" in make_targets:
        result["TEST_CMD"] = "make test"
    elif has_nextest:
        result["TEST_CMD"] = "cargo nextest run"
    else:
        result["TEST_CMD"] = "cargo test"
    if "lint" in make_targets:
        result["LINT_CMD"] = "make lint"
    elif has_script_clippy:
        result["LINT_CMD"] = "./script/clippy"
    else:
        result["LINT_CMD"] = "cargo fmt --check && cargo clippy --all-targets -- -D warnings"

    return result


def detect_generic_commands(target: Path) -> dict[str, str]:
    result: dict[str, str] = {}
    _apply_runner(result, _makefile_targets(target), "make")
    _apply_runner(result, _just_targets(target), "just")
    _apply_runner(result, _taskfile_targets(target), "task")
    _apply_runner(result, _mise_tasks(target), "mise run")
    return result


def detect_commands(target: Path, stack: str) -> dict[str, str]:
    """Return confidently detected BUILD_CMD/TEST_CMD/LINT_CMD for the target directory."""
    detectors = {
        "python": detect_python_commands,
        "node": detect_node_commands,
        "go": detect_go_commands,
        "rust": detect_rust_commands,
    }
    detector = detectors.get(stack, detect_generic_commands)
    result = detector(target)
    if stack != "generic":
        generic = detect_generic_commands(target)
        for key in COMMAND_KEYS:
            if key not in result and key in generic:
                result[key] = generic[key]
    return result


def main() -> int:
    ap = argparse.ArgumentParser(description="Detect build/test/lint commands for a project")
    ap.add_argument("--target", type=Path, default=Path("."), help="Project directory to probe")
    ap.add_argument("--stack", default="generic", help="python|node|go|rust|generic")
    args = ap.parse_args()

    target = args.target.resolve()
    if not target.is_dir():
        print(f"ERROR: target {target} is not a directory", file=sys.stderr)
        return 1

    detected = detect_commands(target, args.stack)
    if not detected:
        print("No commands detected (no recognized config files found).")
        return 0

    for key, value in detected.items():
        print(f"{key}={value}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
