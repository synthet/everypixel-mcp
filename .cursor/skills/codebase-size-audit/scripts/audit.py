"""Read-only file-size and Python function-span audit (stdlib only)."""
from __future__ import annotations

import argparse
import ast
import json
import os
from pathlib import Path

EXCLUDE = {'.git', 'node_modules', '.venv', 'venv', 'vendor', 'target', 'dist',
           'build', '__pycache__', '.agent', 'generated', '.cache', 'obj', 'bin'}
EXTENSIONS = {'.py', '.rs', '.ts', '.tsx', '.js', '.jsx', '.cs', '.go', '.cpp', '.c', '.h', '.java', '.lua'}


def audit(root: Path, file_lines: int, function_lines: int) -> dict:
    files, functions, errors = [], [], []
    root = root.resolve()
    for directory, dirs, names in os.walk(root, followlinks=False):
        here = Path(directory)
        dirs[:] = [name for name in dirs if name not in EXCLUDE and not (here / name).is_symlink()
                   and not getattr(here / name, 'is_junction', lambda: False)()]
        for name in names:
            path = here / name
            if path.suffix not in EXTENSIONS or path.is_symlink():
                continue
            rel = path.relative_to(root).as_posix()
            try:
                if path.stat().st_size > 8_000_000:
                    errors.append({'path': rel, 'error': 'over-size-limit'})
                    continue
                text = path.read_text(encoding='utf-8')
            except (OSError, UnicodeError) as exc:
                errors.append({'path': rel, 'error': type(exc).__name__})
                continue
            lines = len(text.splitlines())
            if lines >= file_lines:
                files.append({'path': rel, 'lines': lines})
            if path.suffix == '.py':
                try:
                    tree = ast.parse(text)
                except SyntaxError:
                    errors.append({'path': rel, 'error': 'SyntaxError'})
                    continue
                for node in ast.walk(tree):
                    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        span = node.end_lineno - node.lineno + 1
                        if span >= function_lines:
                            functions.append({'path': rel, 'name': node.name, 'line': node.lineno, 'lines': span})
    return {'files': sorted(files, key=lambda x: (-x['lines'], x['path'])),
            'functions': sorted(functions, key=lambda x: (-x['lines'], x['path'], x['line'])),
            'errors': errors, 'function_languages': ['python']}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--file-lines', type=int, default=1000)
    parser.add_argument('--function-lines', type=int, default=150)
    args = parser.parse_args()
    if not args.root.is_dir() or min(args.file_lines, args.function_lines) < 1:
        parser.error('existing root and positive thresholds required')
    result = audit(args.root, args.file_lines, args.function_lines)
    print(json.dumps(result, indent=2))
    return 1 if result['errors'] else 0


if __name__ == '__main__':
    raise SystemExit(main())
