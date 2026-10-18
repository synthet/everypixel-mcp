#!/usr/bin/env python3
"""Generate Cursor and Codex assets from the canonical Claude tree.

Single source of truth: author rules, commands, skills, and agents under
``.claude/``, then run this script. Re-running is idempotent.

Cursor mirrors all Claude assets. Codex receives repository skills under
``.agents/skills`` and custom subagents under ``.codex/agents``. Hand-authored
files such as ``.cursor/mcp.example.json`` and ``.codex/config.toml`` remain
untouched.
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CLAUDE = ROOT / ".claude"
CURSOR = ROOT / ".cursor"
CODEX_SKILLS = ROOT / ".agents" / "skills"
CODEX_AGENTS = ROOT / ".codex" / "agents"
ANTIGRAVITY_RULES = ROOT / ".agents" / "rules"
ANTIGRAVITY_AGENTS = ROOT / ".agents" / "agents"

# (source subdir, destination subdir, mode)
SUBDIRS = [
    ("commands", "commands", "files"),
    ("skills", "skills", "tree"),
    ("agents", "agents", "files"),
    ("rules", "rules", "rules"),
]

_FRONTMATTER_RE = re.compile(r"\A---\s*\n(.*?)\n---\s*\n?(.*)\Z", re.DOTALL)
_KEY_RE = re.compile(r"^([A-Za-z][A-Za-z0-9_-]*):\s*(.*)$")


def _reset_dir(path: Path) -> None:
    root = ROOT.resolve()
    resolved = path.resolve()
    if resolved == root or root not in resolved.parents:
        raise ValueError(f"refusing to reset path outside the repository: {resolved}")
    if path.exists():
        shutil.rmtree(path)
    path.mkdir(parents=True, exist_ok=True)


def _normalise(text: str) -> str:
    return text.replace("\r\n", "\n").replace("\r", "\n")


def _parse_agent(md: Path) -> tuple[str, str, str]:
    text = _normalise(md.read_text(encoding="utf-8"))
    match = _FRONTMATTER_RE.match(text)
    if not match:
        raise ValueError(f"{md}: missing or unterminated YAML frontmatter")
    metadata: dict[str, str] = {}
    for line in match.group(1).splitlines():
        key_match = _KEY_RE.match(line)
        if key_match:
            metadata[key_match.group(1)] = key_match.group(2).strip().strip("\"'")
    name = metadata.get("name", "")
    description = metadata.get("description", "")
    if not name or not description:
        raise ValueError(f"{md}: agent frontmatter requires name and description")
    if name != md.stem:
        raise ValueError(f"{md}: agent name {name!r} must match file stem {md.stem!r}")
    body = match.group(2).strip()
    if '"""' in body:
        raise ValueError(f'{md}: agent body cannot contain TOML delimiter """')
    return name, description, body


def _render_codex_agent(md: Path) -> str:
    name, description, body = _parse_agent(md)
    return (
        f"name = {json.dumps(name, ensure_ascii=False)}\n"
        f"description = {json.dumps(description, ensure_ascii=False)}\n"
        'developer_instructions = """\n'
        f"{body}\n"
        '"""\n'
    )


def _copy_cursor_target(src: Path, dst: Path, mode: str) -> None:
    _reset_dir(dst)
    if mode == "tree":
        for child in sorted(src.iterdir()):
            if child.is_dir():
                shutil.copytree(child, dst / child.name, ignore=shutil.ignore_patterns("__pycache__", "*.pyc", "*.pyo"))
            else:
                shutil.copy2(child, dst / child.name)
    elif mode == "rules":
        for md in sorted(src.glob("*.md")):
            shutil.copyfile(md, dst / f"{md.stem}.mdc")
    else:
        for md in sorted(src.glob("*.md")):
            shutil.copy2(md, dst / md.name)


def _sync_codex() -> None:
    _reset_dir(CODEX_SKILLS)
    for child in sorted((CLAUDE / "skills").iterdir()):
        if child.is_dir():
            shutil.copytree(child, CODEX_SKILLS / child.name, ignore=shutil.ignore_patterns("__pycache__", "*.pyc", "*.pyo"))
        else:
            shutil.copy2(child, CODEX_SKILLS / child.name)
    _reset_dir(CODEX_AGENTS)
    for md in sorted((CLAUDE / "agents").glob("*.md")):
        (CODEX_AGENTS / f"{md.stem}.toml").write_text(
            _render_codex_agent(md), encoding="utf-8", newline="\n"
        )


def _antigravity_expected(kind: str) -> dict[str, str]:
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))
    from scripts.agent_setup import antigravity_agent, antigravity_rule
    render = antigravity_rule if kind == "rules" else antigravity_agent
    return {path.name: render(path.read_text(encoding="utf-8"))
            for path in sorted((CLAUDE / kind).glob("*.md"))}


def _sync_antigravity(check: bool = False) -> list[str]:
    changes = []
    for kind, directory in [("rules", ANTIGRAVITY_RULES), ("agents", ANTIGRAVITY_AGENTS)]:
        expected = _antigravity_expected(kind)
        if not check:
            _reset_dir(directory)
            for name, text in expected.items():
                (directory / name).write_text(text, encoding="utf-8", newline="\n")
            continue
        actual = {p.name: p for p in directory.glob("*.md")}
        label = ".agents/" + kind
        changes.extend(f"missing in {label}: {n}" for n in sorted(expected.keys() - actual.keys()))
        changes.extend(f"stale in {label}: {n}" for n in sorted(actual.keys() - expected.keys()))
        changes.extend(f"differs: {label}/{n}" for n in sorted(expected.keys() & actual.keys())
                       if actual[n].read_text(encoding="utf-8") != expected[n])
    return changes


def sync(
    check: bool = False,
    claude_root: Path | None = None,
    cursor_root: Path | None = None,
) -> int:
    """Sync the default repo, or only Cursor paths when test roots are supplied."""
    claude_root = claude_root or CLAUDE
    cursor_root = cursor_root or CURSOR
    using_default_roots = claude_root == CLAUDE and cursor_root == CURSOR
    changes: list[str] = []
    for src_name, dst_name, mode in SUBDIRS:
        src = claude_root / src_name
        dst = cursor_root / dst_name
        if not src.is_dir():
            continue
        if check:
            changes.extend(_diff(src, dst, mode))
        else:
            _copy_cursor_target(src, dst, mode)
            print(f"synced {src_name} -> {dst.relative_to(ROOT).as_posix() if using_default_roots else dst}")

    if check:
        if using_default_roots:
            changes.extend(_diff_tree(CLAUDE / "skills", CODEX_SKILLS, ".agents/skills"))
            changes.extend(_diff_codex_agents())
            changes.extend(_sync_antigravity(check=True))
        if changes:
            print("OUT OF SYNC:")
            for change in changes:
                print(f"  {change}")
            return 1
        print("in sync: .cursor, .agents/skills, .codex/agents" if using_default_roots else "in sync")
        return 0

    if using_default_roots:
        _sync_codex()
        print("synced skills -> .agents/skills")
        print("synced agents -> .codex/agents")
        _sync_antigravity()
        print("synced rules and agents -> .agents/{rules,agents}")
    return 0


def _tree_paths(root: Path) -> tuple[dict[str, Path], set[str]]:
    if not root.is_dir():
        return {}, set()
    files: dict[str, Path] = {}
    dirs: set[str] = set()
    for path in root.rglob("*"):
        if "__pycache__" in path.relative_to(root).parts or path.suffix in {".pyc", ".pyo"}:
            continue
        relative = path.relative_to(root).as_posix()
        if path.is_file():
            files[relative] = path
        elif path.is_dir():
            dirs.add(relative)
    return files, dirs


def _compare_file_sets(
    src_files: dict[str, Path], dst_files: dict[str, Path], dst_label: str
) -> list[str]:
    out: list[str] = []
    src_names = set(src_files)
    dst_names = set(dst_files)
    for name in sorted(src_names - dst_names):
        out.append(f"missing in .cursor: {dst_label}/{name}")
    for name in sorted(dst_names - src_names):
        out.append(f"stale in .cursor: {dst_label}/{name}")
    for name in sorted(src_names & dst_names):
        if src_files[name].read_bytes() != dst_files[name].read_bytes():
            out.append(f"differs: {dst_label}/{name}")
    return out


def _compare_dir_sets(src_dirs: set[str], dst_dirs: set[str], dst_label: str) -> list[str]:
    out: list[str] = []
    for name in sorted(src_dirs - dst_dirs):
        out.append(f"missing in .cursor: {dst_label}/{name}/")
    for name in sorted(dst_dirs - src_dirs):
        out.append(f"stale in .cursor: {dst_label}/{name}/")
    return out


def _diff(src: Path, dst: Path, mode: str) -> list[str]:
    if mode == "tree":
        src_files, src_dirs = _tree_paths(src)
        dst_files, dst_dirs = _tree_paths(dst)
        return [
            *_compare_dir_sets(src_dirs, dst_dirs, dst.name),
            *_compare_file_sets(src_files, dst_files, dst.name),
        ]
    src_files = {
        (f"{path.stem}.mdc" if mode == "rules" else path.name): path
        for path in sorted(src.glob("*.md"))
    }
    dst_files = (
        {path.relative_to(dst).as_posix(): path for path in sorted(dst.rglob("*")) if path.is_file()}
        if dst.is_dir()
        else {}
    )
    return _compare_file_sets(src_files, dst_files, dst.name)


def _diff_tree(src: Path, dst: Path, label: str | None = None) -> list[str]:
    """Compatibility wrapper for recursive tree checks used by local tests."""
    display = label or dst.as_posix()
    src_files, src_dirs = _tree_paths(src)
    dst_files, dst_dirs = _tree_paths(dst)
    out: list[str] = []
    for name in sorted(src_dirs - dst_dirs):
        out.append(f"missing in {display}: {name}/")
    for name in sorted(dst_dirs - src_dirs):
        out.append(f"stale in {display}: {name}/")
    for name in sorted(src_files.keys() - dst_files.keys()):
        out.append(f"missing in {display}: {name}")
    for name in sorted(dst_files.keys() - src_files.keys()):
        out.append(f"stale in {display}: {name}")
    for name in sorted(src_files.keys() & dst_files.keys()):
        if src_files[name].read_bytes() != dst_files[name].read_bytes():
            out.append(f"differs: {display}/{name}")
    return out


def _diff_codex_agents() -> list[str]:
    expected = {
        f"{md.stem}.toml": _render_codex_agent(md)
        for md in (CLAUDE / "agents").glob("*.md")
    }
    actual = (
        {path.name: path for path in CODEX_AGENTS.glob("*.toml")}
        if CODEX_AGENTS.is_dir()
        else {}
    )
    out: list[str] = []
    for name in sorted(expected.keys() - actual.keys()):
        out.append(f"missing in .codex/agents: {name}")
    for name in sorted(actual.keys() - expected.keys()):
        out.append(f"stale in .codex/agents: {name}")
    for name in sorted(expected.keys() & actual.keys()):
        if _normalise(actual[name].read_text(encoding="utf-8")) != expected[name]:
            out.append(f"differs: .codex/agents/{name}")
    return out


def main() -> int:
    parser = argparse.ArgumentParser(description="Sync Cursor and Codex assets from .claude/")
    parser.add_argument("--check", action="store_true", help="Report drift without writing")
    args = parser.parse_args()
    return sync(check=args.check)


if __name__ == "__main__":
    raise SystemExit(main())
