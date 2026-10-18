#!/usr/bin/env python3
"""Static validator for agent eval fixtures."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_FIXTURE_ROOT = REPO_ROOT / "evals"
REQUIRED_FIELDS = {
    "id": str,
    "description": str,
    "target_asset": str,
    "linked_docs": list,
    "must_contain": list,
    "must_not_contain": list,
}


def _repo_path(raw_path: str) -> Path:
    path = (REPO_ROOT / raw_path).resolve()
    try:
        path.relative_to(REPO_ROOT)
    except ValueError as exc:
        raise ValueError(f"path escapes repository root: {raw_path}") from exc
    return path


def _validate_string_list(value: Any, field: str, fixture_path: Path) -> list[str]:
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        raise ValueError(f"{fixture_path}: {field} must be an array of strings")
    return value


def load_fixture(fixture_path: Path) -> dict[str, Any]:
    try:
        data = json.loads(fixture_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"{fixture_path}: invalid JSON: {exc}") from exc

    if not isinstance(data, dict):
        raise ValueError(f"{fixture_path}: fixture must be a JSON object")

    allowed_fields = set(REQUIRED_FIELDS)
    missing = sorted(allowed_fields - set(data))
    extra = sorted(set(data) - allowed_fields)
    if missing:
        raise ValueError(f"{fixture_path}: missing required fields: {', '.join(missing)}")
    if extra:
        raise ValueError(f"{fixture_path}: unknown fields: {', '.join(extra)}")

    for field, expected_type in REQUIRED_FIELDS.items():
        if not isinstance(data[field], expected_type):
            raise ValueError(f"{fixture_path}: {field} must be {expected_type.__name__}")

    for field in ("linked_docs", "must_contain", "must_not_contain"):
        _validate_string_list(data[field], field, fixture_path)

    if not data["id"].strip():
        raise ValueError(f"{fixture_path}: id must not be empty")
    if not data["description"].strip():
        raise ValueError(f"{fixture_path}: description must not be empty")
    if not data["target_asset"].strip():
        raise ValueError(f"{fixture_path}: target_asset must not be empty")

    return data


def validate_fixture(fixture_path: Path) -> list[str]:
    failures: list[str] = []
    try:
        fixture = load_fixture(fixture_path)
    except ValueError as exc:
        return [str(exc)]

    referenced_paths = [fixture["target_asset"], *fixture["linked_docs"]]
    texts: list[str] = []
    for raw_path in referenced_paths:
        try:
            path = _repo_path(raw_path)
        except ValueError as exc:
            failures.append(f"{fixture_path}: {exc}")
            continue
        if not path.is_file():
            failures.append(f"{fixture_path}: referenced path does not exist or is not a file: {raw_path}")
            continue
        texts.append(path.read_text(encoding="utf-8"))

    combined_text = "\n".join(texts)
    for snippet in fixture["must_contain"]:
        if snippet not in combined_text:
            failures.append(f"{fixture_path}: must_contain snippet not found: {snippet!r}")

    for snippet in fixture["must_not_contain"]:
        if snippet in combined_text:
            failures.append(f"{fixture_path}: must_not_contain snippet found: {snippet!r}")

    return failures


def find_fixtures(root: Path) -> list[Path]:
    return sorted(path for path in root.rglob("*.json") if path.is_file())


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "fixture_root",
        nargs="?",
        default=str(DEFAULT_FIXTURE_ROOT),
        help="Directory containing JSON fixtures (default: evals)",
    )
    args = parser.parse_args(argv)

    fixture_root = Path(args.fixture_root)
    if not fixture_root.is_absolute():
        fixture_root = REPO_ROOT / fixture_root
    fixture_root = fixture_root.resolve()

    if not fixture_root.is_dir():
        print(f"Fixture root does not exist or is not a directory: {fixture_root}", file=sys.stderr)
        return 2

    fixtures = find_fixtures(fixture_root)
    if not fixtures:
        print(f"No JSON fixtures found under {fixture_root}", file=sys.stderr)
        return 2

    failures: list[str] = []
    for fixture_path in fixtures:
        failures.extend(validate_fixture(fixture_path))

    if failures:
        print("Agent eval fixture validation failed:", file=sys.stderr)
        for failure in failures:
            print(f"- {failure}", file=sys.stderr)
        return 1

    print(f"Validated {len(fixtures)} agent eval fixture(s).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
