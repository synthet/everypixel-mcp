#!/usr/bin/env python3
"""Read-only, bounded discovery of transcript candidates; stdlib only."""

from __future__ import annotations

import argparse
import json
import os
import re
from pathlib import Path

SKIP = {
    ".git", ".svn", "node_modules", ".venv", "venv", "__pycache__",
    ".pytest_cache", ".ruff_cache", "dist", "build", "target", "vendor",
    "skills", "agents", "rules", "commands", ".llmwiki", "wiki",
    "quarantine", "worktrees", ".worktrees", "_backup", ".backup", "kb-staging",
    "review-artifacts", "release-builds", "packagecache", "library", "coverage",
    ".next", ".nuxt", "dreams",
}
SUFFIXES = {".md", ".txt", ".jsonl", ".json"}
ROLE = re.compile(
    r"(?im)^\s*(?:#{1,6}\s+|\*\*)?(user|human|assistant|claude|codex|gemini|cursor)"
    r"(?:\*\*)?\s*(?::|$|\[|\()"
)
NAME = re.compile(r"(?i)^(?:(?:codex|claude|cursor|gemini)-session-|rollout-|(?:chat|conversation)[-_](?:export|dump)|transcript[-_])")
DATED = re.compile(r"^\d{4}-\d{2}-\d{2}[-_]\d{6}(?:[-_]|$)")
ANSI = re.compile(r"\x1b\[[0-?]*[ -/]*[@-~]")
TERMINAL_USER = re.compile(r"(?m)^\s*[>❯]\s+\S")
TERMINAL_ASSISTANT = re.compile(r"(?m)^\s*●\s+\S")
INJECTED = re.compile(
    r"<(?P<tag>manually_attached_skills|system[-_]reminder|environment_context|INSTRUCTIONS|"
    r"available_subagent_types|available_subagent_models|dynamic_tools|dynamic_tool_namespaces)"
    r"\b[^>]*>.*?(?:</(?P=tag)\s*>|$)", re.IGNORECASE | re.DOTALL
)


def linked(path: Path) -> bool:
    """Do not traverse symbolic links or Windows junctions."""
    return path.is_symlink() or getattr(path, "is_junction", lambda: False)()


def dialogue_sample(sample: str) -> str:
    """Exclude embedded examples/context from marker discovery, not preservation."""
    sample = INJECTED.sub("\n", sample)
    lines, fence = [], None
    for line in sample.splitlines(keepends=True):
        marker = re.match(r"^\s*(`{3,}|~{3,})", line)
        if marker:
            token = marker.group(1)
            if fence is None:
                fence = (token[0], len(token))
            elif token[0] == fence[0] and len(token) >= fence[1] and not line[marker.end():].strip():
                fence = None
            lines.append("\n")
        elif fence is None:
            lines.append(line)
    return "".join(lines)


def reason(path: Path, sample: str) -> str | None:
    sample = ANSI.sub("", sample)
    dialogue = dialogue_sample(sample)
    roles = {m.group(1).lower() for m in ROLE.finditer(dialogue)}
    if roles & {"user", "human"} and roles - {"user", "human"}:
        return "dialogue-markers"
    if TERMINAL_USER.search(dialogue) and TERMINAL_ASSISTANT.search(dialogue):
        return "claude-terminal-dialogue"
    if path.suffix.lower() in {".json", ".jsonl"}:
        records = []
        try:
            value = json.loads(sample)
            if isinstance(value, dict) and isinstance(value.get("messages"), list):
                records = value["messages"]
            else:
                records = value if isinstance(value, list) else [value]
        except json.JSONDecodeError:
            for line in sample.splitlines():
                try:
                    records.append(json.loads(line))
                except json.JSONDecodeError:
                    continue  # Discovery sample may end mid-record; conversion must not skip.
        for record in records:
            if not isinstance(record, dict):
                continue
            message = record.get("message", record.get("payload", record))
            if isinstance(message, dict) and message.get("role") in {"user", "assistant"}:
                if any(k in message for k in ("content", "text")):
                    return "message-record"
            if record.get("type") == "session_meta" and isinstance(record.get("payload"), dict):
                return "session-metadata"
    if path.suffix.lower() != ".json" and (NAME.search(path.stem) or DATED.match(path.stem)):
        return "filename-only-review-required"
    return None


def scan(root: Path, *, include_docs: bool = False, sample_bytes: int = 65536) -> dict:
    if linked(root):
        raise ValueError("linked root")
    root = root.resolve(strict=True)
    if not root.is_dir():
        raise ValueError("root is not a directory")
    candidates, errors = [], []

    def walk_error(exc: OSError) -> None:
        errors.append({"reason": type(exc).__name__, "operation": "enumerate"})

    for directory, dirs, files in os.walk(root, followlinks=False, onerror=walk_error):
        here = Path(directory)
        dirs[:] = sorted(
            d for d in dirs
            if d.lower() not in SKIP
            and (include_docs or d.lower() not in {"docs", ".docs"})
            and not linked(here / d)
        )
        for name in sorted(files):
            path = here / name
            if path.suffix.lower() not in SUFFIXES or linked(path):
                continue
            if name.lower() in {"secrets.json", "settings.local.json", "mcp.json"}:
                continue
            try:
                # Containment also protects against unexpectedly redirected ancestors.
                path.resolve(strict=True).relative_to(root)
                with path.open("rb") as stream:
                    raw = stream.read(sample_bytes)
                if b"\x00" in raw:
                    continue
                sample = raw.decode("utf-8-sig", errors="replace")
                match = reason(path, sample)
                if match:
                    candidates.append({
                        "path": path.relative_to(root).as_posix(),
                        "bytes": path.stat().st_size,
                        "sample_bytes_read": len(raw),
                        "sample_truncated": path.stat().st_size > len(raw),
                        "reason": match,
                        "confidence": "low" if match == "filename-only-review-required" else "content-pattern",
                        "existing_document": path.relative_to(root).parts[0].lower() in {"docs", ".docs"}
                                             and sample.lstrip().startswith("---"),
                    })
            except (OSError, ValueError) as exc:
                errors.append({"path": path.relative_to(root).as_posix(), "reason": type(exc).__name__})
    return {"root": str(root), "candidates": candidates, "errors": errors}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, action="append", required=True,
                        help="Explicit project root; repeat for multiple projects")
    parser.add_argument("--include-docs", action="store_true", help="Also inspect docs/.docs for raw exports")
    args = parser.parse_args()
    results, failed, seen = [], False, set()
    for root in args.root:
        key = os.path.normcase(str(root.absolute()))
        if key in seen:
            continue
        seen.add(key)
        try:
            result = scan(root, include_docs=args.include_docs)
            failed |= bool(result["errors"])
            results.append(result)
        except (OSError, ValueError) as exc:
            failed = True
            results.append({"root": str(root), "candidates": [], "errors": [{"reason": type(exc).__name__}]})
    print(json.dumps({"projects": results, "read_only": True}, ensure_ascii=True, indent=2))
    return int(failed)


if __name__ == "__main__":
    raise SystemExit(main())
