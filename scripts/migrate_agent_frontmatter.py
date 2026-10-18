#!/usr/bin/env python3
"""Populate required metadata frontmatter for .claude command, skill, and agent assets."""

from __future__ import annotations

import argparse
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
REQUIRED_DEFAULT_ORDER = [
    "capability",
    "side_effect_level",
    "approval_required",
    "requires_tools",
    "output_schema",
    "risk_class",
]


def split_frontmatter(text: str) -> tuple[list[str] | None, str]:
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return None, text
    for idx, line in enumerate(lines[1:], start=1):
        if line.strip() == "---":
            return lines[1:idx], "\n".join(lines[idx + 1 :]) + (
                "\n" if text.endswith("\n") else ""
            )
    return None, text


def existing_keys(frontmatter: list[str]) -> set[str]:
    keys: set[str] = set()
    for line in frontmatter:
        if line and not line.startswith((" ", "\t", "-", "#")) and ":" in line:
            keys.add(line.split(":", 1)[0].strip())
    return keys


def quoted(value: str) -> str:
    return '"' + value.replace('"', '\\"') + '"'


def defaults_for(rel: str, name: str, text: str) -> dict[str, str]:
    haystack = f"{rel} {name} {text[:2000]}".lower()
    is_external = any(
        term in haystack
        for term in ("external", "codex", "gemini", "subagent-orchestrator")
    )
    mutates_remote = any(
        term in haystack
        for term in (
            "gh issue edit",
            "gh project item-edit",
            "gh pr create",
            "pull request",
            "project board",
        )
    )
    if is_external:
        side_effect = "external_export"
        approval = "true"
        risk = "high"
    elif mutates_remote:
        side_effect = "remote_write"
        approval = "true"
        risk = "medium"
    elif any(
        term in haystack
        for term in (
            "edit",
            "write",
            "commit",
            "changelog",
            "memory",
            "release",
            "sync",
        )
    ):
        side_effect = "local_write"
        approval = "false"
        risk = "medium"
    else:
        side_effect = "read_only"
        approval = "false"
        risk = "low"
    return {
        "capability": quoted(f"{name} agent asset workflow"),
        "side_effect_level": side_effect,
        "approval_required": approval,
        "requires_tools": quoted("See asset body for tool requirements."),
        "output_schema": quoted("Markdown report or documented command output."),
        "risk_class": risk,
    }


def migrate_file(path: Path, root: Path) -> bool:
    rel = path.relative_to(root).as_posix()
    text = path.read_text(encoding="utf-8")
    fm, body = split_frontmatter(text)
    name = path.parent.name if path.name == "SKILL.md" else path.stem
    if fm is None:
        fm = []
        body = text
    keys = existing_keys(fm)
    additions = defaults_for(rel, name, text)
    changed = False
    for key in REQUIRED_DEFAULT_ORDER:
        if key not in keys:
            fm.append(f"{key}: {additions[key]}")
            changed = True
    if split_frontmatter(text)[0] is None:
        changed = True
    if not changed:
        return False
    new_text = "---\n" + "\n".join(fm).rstrip() + "\n---\n\n" + body.lstrip("\n")
    path.write_text(new_text, encoding="utf-8")
    return True


def asset_paths(root: Path) -> list[Path]:
    paths: list[Path] = []
    paths.extend(sorted((root / ".claude" / "commands").glob("*.md")))
    paths.extend(sorted((root / ".claude" / "agents").glob("*.md")))
    paths.extend(sorted((root / ".claude" / "skills").glob("*/SKILL.md")))
    return paths


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=REPO_ROOT)
    parser.add_argument(
        "--check",
        action="store_true",
        help="Report files that would change without writing",
    )
    args = parser.parse_args(argv)
    root = args.root.resolve()
    changed: list[str] = []
    for path in asset_paths(root):
        before = path.read_text(encoding="utf-8")
        did_change = migrate_file(path, root)
        if did_change:
            changed.append(path.relative_to(root).as_posix())
            if args.check:
                path.write_text(before, encoding="utf-8")
    if changed:
        print("Updated:" if not args.check else "Would update:")
        for rel in changed:
            print(f"  {rel}")
        return 1 if args.check else 0
    print("Agent frontmatter metadata already complete")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
