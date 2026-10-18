#!/usr/bin/env python3
"""Validate CLI tool skills under .claude/skills/ per .agent/cli-tools-skills-spec.md."""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKILLS_DIR = ROOT / ".claude" / "skills"
ROOT_SKILLS = ROOT / "skills"

CLI_SKILL_NAMES = [
    "cli-tools-overview",
    "safe-command-patterns",
    "install-checklist",
    "search-and-navigation",
    "structural-code-search",
    "search-tool-selection",
    "git-and-diff-workflows",
    "data-config-tools",
    "task-env-package-tools",
    "lint-format-security",
    "mcp-code-intelligence",
    "windows-agent-tooling",
    "wsl2-agent-tooling",
]

OVERVIEW_REFERENCES = [
    "install-blocks.md",
    "install-tiers.md",
    "agent-environment.md",
    "bounded-output-patterns.md",
    "commands-requiring-confirmation.md",
    "windows-wsl-split.md",
]

OVERVIEW_REFS_DIR = SKILLS_DIR / "cli-tools-overview" / "references"

REQUIRED_HEADINGS = [
    "## Purpose",
    "## When to Use",
    "## Required Tools",
    "## Install",
    "### Windows PowerShell",
    "### WSL2 Ubuntu",
    "### macOS",
    "## Common Commands",
    "## Agent-Safe Patterns",
    "## Commands Requiring Confirmation",
    "## Troubleshooting",
    "## Windows Notes",
    "## WSL2 Notes",
    "## Verification Checklist",
]

DESTRUCTIVE_PATTERNS = re.compile(
    r"(?i)(git reset --hard|git clean -fd|git push --force|rm -rf|docker system prune)",
)


def validate_skill(name: str, errors: list[str]) -> None:
    skill_md = SKILLS_DIR / name / "SKILL.md"
    rel = skill_md.relative_to(ROOT).as_posix()
    if not skill_md.is_file():
        errors.append(f"missing {rel}")
        return
    text = skill_md.read_text(encoding="utf-8")
    for heading in REQUIRED_HEADINGS:
        if heading not in text:
            errors.append(f"{rel}: missing heading {heading!r}")
    # Destructive examples should mention confirmation nearby or live in confirmation section
    confirm_idx = text.find("## Commands Requiring Confirmation")
    for match in DESTRUCTIVE_PATTERNS.finditer(text):
        pos = match.start()
        if confirm_idx == -1 or pos < confirm_idx:
            snippet = text[max(0, pos - 40) : pos + 40].replace("\n", " ")
            if "confirmation" not in snippet.lower() and "confirm" not in snippet.lower():
                errors.append(
                    f"{rel}: destructive pattern {match.group()!r} outside confirmation context"
                )


def validate_overview_references(errors: list[str]) -> None:
    for name in OVERVIEW_REFERENCES:
        path = OVERVIEW_REFS_DIR / name
        if not path.is_file():
            errors.append(f"missing {path.relative_to(ROOT).as_posix()}")


def main() -> int:
    errors: list[str] = []
    if ROOT_SKILLS.exists():
        errors.append(
            f"repo-root skills/ still exists ({ROOT_SKILLS}) — migrate to .claude/skills/ and remove"
        )
    validate_overview_references(errors)
    for name in CLI_SKILL_NAMES:
        validate_skill(name, errors)
    if errors:
        print("CLI skills validation FAILED:")
        for e in errors:
            print(f"  {e}")
        return 1
    print(f"OK: {len(CLI_SKILL_NAMES)} CLI skills")
    return 0


if __name__ == "__main__":
    sys.exit(main())
