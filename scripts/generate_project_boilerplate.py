#!/usr/bin/env python3
"""Generate starter boilerplate for bootstrapped projects.

The generated files are intentionally small and dependency-light so a new
project has concrete code/resources to iterate from without hiding stack setup
behind a larger framework template. Existing files are preserved unless
``--force`` is requested.
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

SUPPORTED_STACKS = ("python", "node", "go", "rust")
DEFAULT_PROJECT_DESC = "TODO(PROJECT_DESC)"


def _write(path: Path, content: str, *, force: bool) -> bool:
    if path.exists() and not force:
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return True


def _write_files(target: Path, files: dict[Path, str], *, force: bool) -> list[Path]:
    return [
        target / rel
        for rel, content in files.items()
        if _write(target / rel, content, force=force)
    ]


def _toml_string(value: str) -> str:
    """Return a TOML basic-string literal for simple generated metadata."""
    return json.dumps(value)


def _python_package_name(project_slug: str) -> str:
    package = re.sub(r"\W+", "_", project_slug).strip("_").lower()
    if not package or package[0].isdigit():
        package = f"project_{package or 'app'}"
    return package


def _go_module_name(project_slug: str) -> str:
    module = re.sub(r"[^a-zA-Z0-9_./-]+", "", project_slug).strip("./-").lower()
    return module or "app"


def _rust_crate_name(project_slug: str) -> str:
    crate = re.sub(r"[^a-zA-Z0-9]+", "_", project_slug).strip("_").lower()
    if not crate or crate[0].isdigit():
        crate = f"project_{crate or 'app'}"
    return crate


def generate_python(
    target: Path,
    project_slug: str,
    project_desc: str = DEFAULT_PROJECT_DESC,
    *,
    force: bool = False,
) -> list[Path]:
    package = _python_package_name(project_slug)
    files = {
        Path("pyproject.toml"): f"""[build-system]
requires = ["setuptools>=68"]
build-backend = "setuptools.build_meta"

[project]
name = {_toml_string(project_slug)}
version = "0.1.0"
description = {_toml_string(project_desc)}
requires-python = ">=3.11"

[tool.pytest.ini_options]
testpaths = ["tests"]

[tool.ruff]
line-length = 100
""",
        Path("src") / package / "__init__.py": f'''"""Project package."""

__all__ = ["hello"]


def hello() -> str:
    return "hello from {project_slug}"
''',
        Path("tests") / "test_smoke.py": f'''from {package} import hello


def test_hello() -> None:
    assert hello() == "hello from {project_slug}"
''',
    }
    return _write_files(target, files, force=force)


def generate_node(
    target: Path,
    project_slug: str,
    project_desc: str = DEFAULT_PROJECT_DESC,
    *,
    force: bool = False,
) -> list[Path]:
    package_json = {
        "name": project_slug,
        "version": "0.1.0",
        "description": project_desc,
        "private": True,
        "type": "module",
        "scripts": {
            "build": "tsc --noEmit",
            "lint": "tsc --noEmit",
            "test": "node --test",
        },
        "devDependencies": {"typescript": "^5.0.0"},
    }
    files = {
        Path("package.json"): json.dumps(package_json, indent=2) + "\n",
        Path("tsconfig.json"): '''{
  "compilerOptions": {
    "target": "ES2022",
    "module": "NodeNext",
    "moduleResolution": "NodeNext",
    "strict": true,
    "noEmit": true
  },
  "include": ["src/**/*.ts"]
}
''',
        Path("src") / "index.ts": f'''export function hello(): string {{
  return "hello from {project_slug}";
}}
''',
        Path("test") / "smoke.test.mjs": f'''import assert from 'node:assert/strict';
import test from 'node:test';

test('project scaffold has a known greeting', () => {{
  assert.equal('hello from {project_slug}', 'hello from {project_slug}');
}});
''',
    }
    return _write_files(target, files, force=force)


def generate_go(
    target: Path,
    project_slug: str,
    project_desc: str = DEFAULT_PROJECT_DESC,
    *,
    force: bool = False,
) -> list[Path]:
    del project_desc
    module = _go_module_name(project_slug)
    files = {
        Path("go.mod"): f"module {module}\n\ngo 1.22\n",
        Path("main.go"): f'''package main

import "fmt"

func Greeting() string {{
	return "hello from {project_slug}"
}}

func main() {{
	fmt.Println(Greeting())
}}
''',
        Path("main_test.go"): f'''package main

import "testing"

func TestGreeting(t *testing.T) {{
	if got := Greeting(); got != "hello from {project_slug}" {{
		t.Fatalf("Greeting() = %q", got)
	}}
}}
''',
    }
    return _write_files(target, files, force=force)


def generate_rust(
    target: Path,
    project_slug: str,
    project_desc: str = DEFAULT_PROJECT_DESC,
    *,
    force: bool = False,
) -> list[Path]:
    crate = _rust_crate_name(project_slug)
    files = {
        Path("Cargo.toml"): f"""[package]
name = {_toml_string(crate)}
version = "0.1.0"
edition = "2021"
description = {_toml_string(project_desc)}
""",
        Path("src") / "lib.rs": f'''pub fn hello() -> &'static str {{
    "hello from {project_slug}"
}}
''',
        Path("tests") / "smoke.rs": f'''use {crate}::hello;

#[test]
fn hello_returns_known_greeting() {{
    assert_eq!(hello(), "hello from {project_slug}");
}}
''',
    }
    return _write_files(target, files, force=force)


def generate_boilerplate(
    target: Path,
    stack: str,
    project_slug: str,
    project_desc: str = DEFAULT_PROJECT_DESC,
    *,
    force: bool = False,
) -> list[Path]:
    generators = {
        "python": generate_python,
        "node": generate_node,
        "go": generate_go,
        "rust": generate_rust,
    }
    generator = generators.get(stack)
    if generator is None:
        return []
    return generator(target, project_slug, project_desc, force=force)


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate starter project boilerplate")
    parser.add_argument(
        "--target", type=Path, default=Path("."), help="Project root to write into"
    )
    parser.add_argument(
        "--stack", required=True, choices=SUPPORTED_STACKS, help="Boilerplate stack"
    )
    parser.add_argument(
        "--project-slug",
        required=True,
        help="Project/package slug used for generated package names",
    )
    parser.add_argument(
        "--project-desc",
        default=DEFAULT_PROJECT_DESC,
        help="Description to place in generated package metadata",
    )
    parser.add_argument("--force", action="store_true", help="Overwrite existing boilerplate files")
    args = parser.parse_args()

    target = args.target.resolve()
    written = generate_boilerplate(
        target,
        args.stack,
        args.project_slug,
        args.project_desc,
        force=args.force,
    )
    if not written:
        print(f"No boilerplate written for stack {args.stack}.")
    else:
        print("Generated boilerplate files:")
        for path in written:
            print(f"  {path.relative_to(target)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
