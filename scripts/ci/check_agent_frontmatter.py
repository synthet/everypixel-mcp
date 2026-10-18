#!/usr/bin/env python3
"""Validate frontmatter contracts for agent assets under .claude/ (stdlib only)."""

from __future__ import annotations

import argparse
import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]

_KEY_RE = re.compile(r"^([A-Za-z][A-Za-z0-9_-]*):(.*)$")
_MARKDOWN_LINK_RE = re.compile(r"\[[^\]]+\]\(([^)\s]+)(?:\s+\"[^\"]*\")?\)")
SIDE_EFFECT_LEVELS = {"read_only", "local_write", "remote_write", "external_export"}
RISK_CLASSES = {"low", "medium", "high"}
MODEL_ALIASES = {"opus", "sonnet", "haiku", "fable"}
REQUIRED_METADATA = (
    "capability",
    "side_effect_level",
    "approval_required",
    "requires_tools",
    "output_schema",
    "risk_class",
)
MUTATION_COMMAND_RE = re.compile(r"(?:^|[-_])(pr|issue|project|task)(?:[-_]|$)")
EXTERNAL_REVIEW_RE = re.compile(
    r"external|codex|gemini|subagent-review|run-(?:codex|gemini|subagent)-review"
)


def parse_frontmatter(text: str) -> list[tuple[str, str]] | None:
    """Return ordered (key, value) pairs from a leading YAML frontmatter block, or None."""
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return None
    pairs: list[tuple[str, str]] = []
    for line in lines[1:]:
        if line.strip() == "---":
            return pairs
        if not line.strip() or line.startswith((" ", "\t", "-", "#")):
            continue
        m = _KEY_RE.match(line)
        if m:
            pairs.append((m.group(1), m.group(2).strip().strip("\"'")))
    return None


def _value(pairs: list[tuple[str, str]], key: str) -> str | None:
    for k, v in pairs:
        if k == key:
            return v
    return None


def check_no_exotic_yaml(text: str, rel: str, errors: list[str]) -> None:
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return
    for line in lines[1:]:
        if line.strip() == "---":
            return
        if "!!" in line:
            errors.append(f"{rel}: exotic YAML tag in frontmatter ({line.strip()!r})")


def _bool_text(value: str | None) -> bool | None:
    if value is None:
        return None
    lowered = value.lower()
    if lowered == "true":
        return True
    if lowered == "false":
        return False
    return None


def is_high_risk_external_review_asset(rel: str, pairs: list[tuple[str, str]]) -> bool:
    name = _value(pairs, "name") or Path(rel).stem
    capability = _value(pairs, "capability") or ""
    risk_class = _value(pairs, "risk_class")
    return risk_class == "high" and bool(
        EXTERNAL_REVIEW_RE.search(f"{rel} {name} {capability}")
    )


def is_pr_issue_project_mutation_command(
    rel: str, pairs: list[tuple[str, str]], text_body: str = ""
) -> bool:
    if not rel.startswith(".claude/commands/"):
        return False
    stem = Path(rel).stem
    capability = (_value(pairs, "capability") or "").lower()
    text = f"{stem} {capability} {text_body}".lower()
    if MUTATION_COMMAND_RE.search(stem) and any(
        w in capability
        for w in (
            "mutat",
            "create",
            "edit",
            "assign",
            "move",
            "update",
            "claim",
            "ready",
        )
    ):
        return True
    return any(
        phrase in text
        for phrase in (
            "gh issue edit",
            "gh project item-edit",
            "create pr",
            "open pr",
            "project mutation",
            "issue mutation",
        )
    )


def check_metadata_contract(
    rel: str, pairs: list[tuple[str, str]], errors: list[str], text_body: str = ""
) -> None:
    for key in REQUIRED_METADATA:
        if _value(pairs, key) in (None, ""):
            errors.append(f"{rel}: missing or empty `{key}`")

    side_effect_level = _value(pairs, "side_effect_level")
    if side_effect_level and side_effect_level not in SIDE_EFFECT_LEVELS:
        errors.append(
            f"{rel}: invalid `side_effect_level` {side_effect_level!r}; expected one of {sorted(SIDE_EFFECT_LEVELS)}"
        )

    approval_required = _value(pairs, "approval_required")
    if approval_required is not None and _bool_text(approval_required) is None:
        errors.append(f"{rel}: `approval_required` must be boolean true or false")

    risk_class = _value(pairs, "risk_class")
    if risk_class and risk_class not in RISK_CLASSES:
        errors.append(
            f"{rel}: invalid `risk_class` {risk_class!r}; expected one of {sorted(RISK_CLASSES)}"
        )

    if is_high_risk_external_review_asset(rel, pairs):
        if side_effect_level != "external_export":
            errors.append(
                f"{rel}: high-risk external review assets require `side_effect_level: external_export`"
            )
        if _bool_text(approval_required) is not True:
            errors.append(
                f"{rel}: high-risk external review assets require `approval_required: true`"
            )

    if (
        is_pr_issue_project_mutation_command(rel, pairs, text_body)
        and side_effect_level != "remote_write"
    ):
        errors.append(
            f"{rel}: PR/issue/project mutation commands require `side_effect_level: remote_write`"
        )


def check_model_alias(rel: str, pairs: list[tuple[str, str]], errors: list[str]) -> None:
    """If frontmatter pins a `model`, require a bare tier alias, not a version ID.

    Tier aliases resolve at dispatch, so one definition follows the asset across model
    generations and providers. A pinned version ID keeps pointing at that generation after a
    switch (and fails at the provider on Bedrock/Vertex/proxies); a ``[1m]``-suffixed ID cannot be
    inherited by subagents. Only fires when a `model` key is present, so it is a preventive guard.
    """
    model = _value(pairs, "model")
    if model is None or model == "":
        return
    if model not in MODEL_ALIASES:
        errors.append(
            f"{rel}: `model` must be a bare tier alias (one of {sorted(MODEL_ALIASES)}), "
            f"not {model!r}; pinned version IDs and [1m]-suffixed IDs break alias resolution "
            "across generations/providers and subagent inheritance"
        )


def check_relative_markdown_links(path: Path, rel: str, text: str, errors: list[str]) -> None:
    """Require relative Markdown links in skill bodies to resolve on disk."""
    for match in _MARKDOWN_LINK_RE.finditer(text):
        target = match.group(1)
        if (
            "://" in target
            or target.startswith(("#", "mailto:", "tel:"))
            or target.startswith("<")
        ):
            continue
        target_path = target.split("#", 1)[0]
        if not target_path:
            continue
        if not (path.parent / target_path).resolve().exists():
            errors.append(f"{rel}: unresolved relative Markdown link {target!r}")


def check_skills(root: Path, errors: list[str]) -> None:
    skills_dir = root / ".claude" / "skills"
    seen: dict[str, str] = {}
    if not skills_dir.is_dir():
        return
    for skill_dir in sorted(p for p in skills_dir.iterdir() if p.is_dir()):
        skill_md = skill_dir / "SKILL.md"
        rel = skill_md.relative_to(root).as_posix()
        if not skill_md.is_file():
            errors.append(f"{skill_dir.relative_to(root).as_posix()}: missing SKILL.md")
            continue
        text = skill_md.read_text(encoding="utf-8")
        check_no_exotic_yaml(text, rel, errors)
        pairs = parse_frontmatter(text)
        if pairs is None:
            errors.append(f"{rel}: missing or unterminated YAML frontmatter")
            continue
        if not pairs or pairs[0][0] != "name":
            errors.append(f"{rel}: `name` must be the first frontmatter key")
        name = _value(pairs, "name")
        if name and name != skill_dir.name:
            errors.append(
                f"{rel}: name {name!r} does not match directory {skill_dir.name!r}"
            )
        if not _value(pairs, "description"):
            errors.append(f"{rel}: missing or empty `description`")
        check_metadata_contract(rel, pairs, errors, text)
        check_model_alias(rel, pairs, errors)
        if name:
            if name in seen:
                errors.append(
                    f"{rel}: duplicate skill name {name!r} (also in {seen[name]})"
                )
            seen[name] = rel
        check_relative_markdown_links(skill_md, rel, text, errors)


def check_agents(root: Path, errors: list[str]) -> None:
    seen: dict[str, str] = {}
    agents_dir = root / ".claude" / "agents"
    if not agents_dir.is_dir():
        return
    for md in sorted(agents_dir.glob("*.md")):
        rel = md.relative_to(root).as_posix()
        text = md.read_text(encoding="utf-8")
        check_no_exotic_yaml(text, rel, errors)
        pairs = parse_frontmatter(text)
        if pairs is None:
            errors.append(f"{rel}: missing or unterminated YAML frontmatter")
            continue
        name = _value(pairs, "name")
        if not name:
            errors.append(f"{rel}: missing `name` in frontmatter")
        elif name != md.stem:
            errors.append(f"{rel}: name {name!r} does not match file stem {md.stem!r}")
        if not _value(pairs, "description"):
            errors.append(f"{rel}: missing or empty `description`")
        check_metadata_contract(rel, pairs, errors, text)
        check_model_alias(rel, pairs, errors)
        if name:
            if name in seen:
                errors.append(
                    f"{rel}: duplicate agent name {name!r} (also in {seen[name]})"
                )
            seen[name] = rel


def check_rules(root: Path, errors: list[str]) -> None:
    rules_dir = root / ".claude" / "rules"
    if not rules_dir.is_dir():
        return
    for md in sorted(rules_dir.glob("*.md")):
        rel = md.relative_to(root).as_posix()
        text = md.read_text(encoding="utf-8")
        check_no_exotic_yaml(text, rel, errors)
        pairs = parse_frontmatter(text)
        if pairs is None:
            errors.append(f"{rel}: missing or unterminated YAML frontmatter")
            continue
        if not _value(pairs, "description"):
            errors.append(f"{rel}: missing or empty `description`")


def check_commands(root: Path, errors: list[str]) -> None:
    commands_dir = root / ".claude" / "commands"
    if not commands_dir.is_dir():
        return
    for md in sorted(commands_dir.glob("*.md")):
        rel = md.relative_to(root).as_posix()
        text = md.read_text(encoding="utf-8")
        check_no_exotic_yaml(text, rel, errors)
        pairs = parse_frontmatter(text)
        if pairs is None:
            errors.append(f"{rel}: missing or unterminated YAML frontmatter")
        else:
            check_metadata_contract(rel, pairs, errors, text)
            check_model_alias(rel, pairs, errors)
        expected = f"# /{md.stem}"
        for line in text.splitlines():
            if line.startswith(expected) and (
                len(line) == len(expected) or not line[len(expected)].isalnum()
            ):
                break
        else:
            errors.append(f"{rel}: missing H1 heading starting with {expected!r}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Validate .claude/ agent-asset frontmatter"
    )
    parser.add_argument(
        "--root", type=Path, default=REPO_ROOT, help="Repo root (default: this repo)"
    )
    args = parser.parse_args(argv)

    root = args.root.resolve()
    errors: list[str] = []
    check_skills(root, errors)
    check_agents(root, errors)
    check_rules(root, errors)
    check_commands(root, errors)

    if errors:
        print(f"Agent frontmatter check FAILED ({len(errors)} problem(s)):")
        for e in errors:
            print(f"  {e}")
        return 1
    print("Agent frontmatter check passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
