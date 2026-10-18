#!/usr/bin/env python3
"""Scan tracked files for committed secrets (stdlib only).

Detects common credential shapes:
  - Provider tokens (AWS access keys, GitHub PATs, Slack tokens, OpenAI/Anthropic keys, JWTs)
  - Private key blocks (PEM)
  - Credentialed connection strings (scheme://user:password@host)
  - Suspicious assignments (api_key/token/password/secret = long literal)

Skips placeholders and documented examples: `${VAR}`, `{{ var }}`, `TODO(...)`, `<angle-bracket>`
values, obvious example/dummy words, and `env.example` / lockfile / binary paths.

Exit code 0 when clean, 1 when potential secrets are found. CI complement to .agent/SAFETY.md.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.ci.secret_detection import SKIP_NAME_PARTS, SKIP_SUFFIXES, scan_file as scan_secret_file

SKIP_PATH_PREFIXES = ("scripts/ci/check_secrets.py",)  # this file contains the patterns


def tracked_files(root: Path) -> list[Path]:
    result = subprocess.run(
        ["git", "ls-files"], cwd=root, capture_output=True, text=True, check=False
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or "git ls-files failed")
    return [root / line for line in result.stdout.splitlines() if line.strip()]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Scan tracked files for committed secrets")
    parser.add_argument(
        "--root", type=Path, default=REPO_ROOT, help="Repo root (default: this repo)"
    )
    args = parser.parse_args(argv)
    root = args.root.resolve()

    findings: list[str] = []
    for path in tracked_files(root):
        if not path.is_file():
            continue
        rel = path.relative_to(root).as_posix()
        if rel.startswith(SKIP_PATH_PREFIXES):
            continue
        if path.name.lower() in SKIP_NAME_PARTS or path.suffix.lower() in SKIP_SUFFIXES:
            continue
        file_findings = scan_secret_file(path, rel)
        if file_findings is None:
            continue
        findings.extend(finding.format() for finding in file_findings)

    if findings:
        print(f"Secrets check FAILED ({len(findings)} potential secret(s)):")
        for f in findings:
            print(f"  {f}")
        print("If these are placeholders/examples, mark them clearly (e.g. ${VAR}, <value>, 'example').")
        return 1
    print("Secrets check passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
