#!/usr/bin/env python3
"""Generate CLI tool skills under .claude/skills/ (idempotent content seed)."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKILLS = ROOT / ".claude" / "skills"
REFS = "../cli-tools-overview/references"

INSTALL_LINK = f"See [install-blocks.md]({REFS}/install-blocks.md)."
CONFIRM_LINK = f"See [commands-requiring-confirmation.md]({REFS}/commands-requiring-confirmation.md)."
BOUNDED_LINK = f"See [bounded-output-patterns.md]({REFS}/bounded-output-patterns.md)."
SPLIT_LINK = f"See [windows-wsl-split.md]({REFS}/windows-wsl-split.md)."


SKILL_METADATA: dict[str, tuple[str, str]] = {
    "cli-tools-overview": ("read_only", "low"),
    "safe-command-patterns": ("local_write", "medium"),
    "install-checklist": ("local_write", "medium"),
    "search-and-navigation": ("read_only", "low"),
    "structural-code-search": ("local_write", "medium"),
    "search-tool-selection": ("read_only", "low"),
    "git-and-diff-workflows": ("local_write", "medium"),
    "data-config-tools": ("local_write", "medium"),
    "task-env-package-tools": ("local_write", "medium"),
    "lint-format-security": ("local_write", "medium"),
    "mcp-code-intelligence": ("local_write", "medium"),
    "windows-agent-tooling": ("local_write", "medium"),
    "wsl2-agent-tooling": ("local_write", "medium"),
}


def skill(name: str, description: str, body: str) -> str:
    side_effect_level, risk_class = SKILL_METADATA[name]
    return f"""---
name: {name}
description: {description}
capability: "{name} agent asset workflow"
side_effect_level: {side_effect_level}
approval_required: false
requires_tools: "See asset body for tool requirements."
output_schema: "Markdown report or documented command output."
risk_class: {risk_class}
---

{body.rstrip()}
"""


def platform_install() -> str:
    return f"""## Install

Install blocks are shared — {INSTALL_LINK}

### Windows PowerShell

Use winget blocks from the reference when provisioning a new machine.

### WSL2 Ubuntu

Use apt/curl blocks from the reference; symlink `fdfind` → `fd` if needed.

### macOS

Use Homebrew blocks from the reference.
"""


def tail_sections(extra_troubleshoot: str = "") -> str:
    return f"""## Commands Requiring Confirmation

{CONFIRM_LINK}

## Troubleshooting

{extra_troubleshoot or "- Tool missing: run install-checklist on the workstation, not in agent loops."}

## Windows Notes

- Prefer `rg` and `fd` from winget; PowerShell aliases may shadow Unix names — use full binary names if commands fail.
- {SPLIT_LINK}

## WSL2 Notes

- Use Linux packages in WSL; avoid calling Windows binaries for repo work when Linux equivalents exist.
- {SPLIT_LINK}

## Verification Checklist

- [ ] Required tools respond (`--version` or `--help`)
- [ ] Commands use bounded output ({BOUNDED_LINK})
- [ ] Destructive ops gated per confirmation reference
"""


def write(name: str, description: str, body: str) -> None:
    d = SKILLS / name
    d.mkdir(parents=True, exist_ok=True)
    (d / "SKILL.md").write_text(skill(name, description, body), encoding="utf-8")
    print(f"wrote {name}")


def main() -> None:
    write(
        "cli-tools-overview",
        "Use as the router for agent CLI workflows: installing tools, choosing safe shell patterns, navigating/searching repos, Git/MCP operations, and task runners. Start here whenever the user asks which command-line tool or workflow to use, or when another CLI skill is not obviously more specific.",
        f"""# CLI tools overview

> For **which search tool to use**, see [`search-tool-selection`](../search-tool-selection/SKILL.md).

## Purpose

Index of CLI tooling skills and shared references for coding agents on Windows, WSL2, and macOS.

## When to Use

- Starting work in an unfamiliar repo
- Choosing which specialized CLI skill to load
- Provisioning a human workstation (via install-checklist)

## Required Tools

Varies by topic skill; core: `git`, `rg`, `fd`, `jq`.

## Install tiers

Install in order — see [install-tiers.md](../cli-tools-overview/references/install-tiers.md):

1. **Tier 0:** `git`, `rg`, `fd`, `jq`, `node`
2. **Block A:** canonical block in [install-blocks.md](../cli-tools-overview/references/install-blocks.md)
3. **Block B:** child-skill extensions (`yq`, `just`, `mise`, …)
4. **Deferred:** optional tools per skill (`fzf`, `semgrep`, …)

## Agent environment

After installing CLI tools, **restart Cursor** and verify PATH — see [agent-environment.md](../cli-tools-overview/references/agent-environment.md).

{platform_install()}

## Common Commands

```bash
# Orientation
tree -L 2 -I 'node_modules|dist|build'
rg --files | head -20
git status --short
```

Benchmark/watch helpers (human): `hyperfine`, `entr`, `watchexec` — use for perf comparisons, not in agent loops.

## Agent-Safe Patterns

- Load `safe-command-patterns` before destructive or broad commands.
- Load `search-tool-selection` before repo-wide search.
- {BOUNDED_LINK}

## Shared references

| Reference | Topic |
|-----------|-------|
| [install-blocks.md](../cli-tools-overview/references/install-blocks.md) | Winget / apt / Homebrew install blocks |
| [install-tiers.md](../cli-tools-overview/references/install-tiers.md) | Tier 0 → Block A → Block B → deferred |
| [agent-environment.md](../cli-tools-overview/references/agent-environment.md) | PATH contract, Cursor restart, smoke tests |
| [bounded-output-patterns.md](../cli-tools-overview/references/bounded-output-patterns.md) | Bounded search/read/git patterns |
| [commands-requiring-confirmation.md](../cli-tools-overview/references/commands-requiring-confirmation.md) | Destructive / auto-fix gates |
| [windows-wsl-split.md](../cli-tools-overview/references/windows-wsl-split.md) | Windows host vs WSL2 workloads |

## See also

| Skill | Topic |
|-------|-------|
| [search-tool-selection](../search-tool-selection/SKILL.md) | fd vs rg vs ast-grep vs fff MCP |
| [safe-command-patterns](../safe-command-patterns/SKILL.md) | Bounded output, git hygiene |
| [install-checklist](../install-checklist/SKILL.md) | Human provisioning |
| [search-and-navigation](../search-and-navigation/SKILL.md) | rg, fd, bat, tree |
| [structural-code-search](../structural-code-search/SKILL.md) | ast-grep, semgrep |
| [git-and-diff-workflows](../git-and-diff-workflows/SKILL.md) | git, gh |
| [data-config-tools](../data-config-tools/SKILL.md) | jq, yq, curl |
| [task-env-package-tools](../task-env-package-tools/SKILL.md) | just, uv, docker, project gates |
| [lint-format-security](../lint-format-security/SKILL.md) | ruff, eslint, trivy |
| [mcp-code-intelligence](../mcp-code-intelligence/SKILL.md) | MCP tiers |
| [windows-agent-tooling](../windows-agent-tooling/SKILL.md) | Native Windows |
| [wsl2-agent-tooling](../wsl2-agent-tooling/SKILL.md) | WSL2 workflows |

{tail_sections("See topic skill for tool-specific failures.")}
""",
    )

    write(
        "safe-command-patterns",
        "Use before running shell commands that explore, edit, delete, move, generate, or inspect many files. Apply when constructing safe bounded commands, avoiding destructive operations, or replacing risky patterns with agent-safe alternatives.",
        f"""# Safe command patterns

## Purpose

Default safety rails for agent shell usage: bounded output, inspect-before-edit, confirmation gates.

## When to Use

Throughout every coding task — before search, edit, test, or commit.

## Required Tools

`git`, `rg` or IDE search; optional `bat`, `delta`.

{platform_install()}

## Common Commands

```bash
git status --short
git diff --stat
git diff -- path/to/file
rg "pattern" path/ --max-count 30
```

## Agent-Safe Patterns

- {BOUNDED_LINK}
- When **fff MCP** is connected, prefer `ffgrep`/`fffind` for repeated repo search over many shell roundtrips; one-off probes may still use `rg`/`fd`.
- Never paste secrets into commands or logs.
- Prefer project scripts from AGENTS.md over invented commands.

## Commands Requiring Confirmation

{CONFIRM_LINK}

## Troubleshooting

- Huge command output: add `--max-count`, path prefix, or `-g` globs.
- Wrong directory: `git rev-parse --show-toplevel`.

## Windows Notes

- Use `Get-Content -TotalCount N` instead of dumping full files.
- {SPLIT_LINK}

## WSL2 Notes

- Run repo commands from the WSL checkout, not `/mnt/c/...` unless intentional.
- {SPLIT_LINK}

## Verification Checklist

- [ ] `git status --short` before edits
- [ ] `git diff --stat` before commit
- [ ] No destructive command without user OK
""",
    )

    write(
        "install-checklist",
        "Use when provisioning a human workstation with agent CLI tools via winget, apt, or Homebrew. Apply when the user asks what to install on Windows, WSL2 Ubuntu, or macOS; do not use for automated dependency install loops inside a task.",
        f"""# Install checklist

## Purpose

One-time setup of CLI tools on a developer machine.

## When to Use

- New laptop or VM setup
- Missing `rg`/`fd`/ `gh` errors in agent sessions

**Agents:** recommend this skill to the user; do not run bulk `winget install` without approval.

## Required Tools

Package managers: `winget`, `apt`, or `brew`.

## Install

Choose an install scope first — see [install-tiers.md](../cli-tools-overview/references/install-tiers.md) (Core only / Recommended / Everything missing).

Install blocks are shared — {INSTALL_LINK}

### Windows PowerShell

Use winget blocks from the reference when provisioning a new machine.

### WSL2 Ubuntu

Use apt/curl blocks from the reference; symlink `fdfind` → `fd` if needed.

### macOS

Use Homebrew blocks from the reference.


## Common Commands

Copy full blocks from [install-blocks.md](../cli-tools-overview/references/install-blocks.md).

## Agent-Safe Patterns

- User executes install blocks interactively.
- After install, **restart Cursor** and run the smoke test in [agent-environment.md](../cli-tools-overview/references/agent-environment.md).
- Verify with `--version` commands only.

## Commands Requiring Confirmation

All install/uninstall commands require user initiation. {CONFIRM_LINK}

## Troubleshooting

- `fd` not found on Ubuntu: use `fdfind` or symlink per install reference.
- PATH not updated: restart shell after uv/node installs.

## Windows Notes

- winget may need elevation for some packages.
- fff-mcp: optional; install from [fff](https://github.com/dmtrKovalenko/fff) releases.
- graphify: optional; `uv tool install graphifyy` (MCP: `uv tool install "graphifyy[mcp]"`) — see [Graphify](https://github.com/Graphify-Labs/graphify).

## WSL2 Notes

- Install tools inside WSL, not only on Windows host.
- {SPLIT_LINK}

## Verification Checklist

- [ ] `git --version`, `rg --version`, `fd --version`, `jq --version`, `gh --version`
- [ ] `node --version`, `pnpm --version` if JS repo
- [ ] `uv --version` if Python repo
- [ ] Block B (Recommended scope): `yq --version`, `just --version`, `shellcheck --version`
- [ ] Cursor restarted; smoke test passes per [agent-environment.md](../cli-tools-overview/references/agent-environment.md)
""",
    )

    write(
        "search-and-navigation",
        "Use for fast repo navigation and discovery with rg, fd/find, bat/sed, tree, eza, zoxide, or delta. Apply whenever locating files, finding text, mapping repo layout, or bounding command output for code exploration.",
        f"""# Search and navigation

> **Tool choice first:** [`search-tool-selection`](../search-tool-selection/SKILL.md) — fd → rg → read slice.

## Purpose

Find files and text quickly with gitignore-aware tools and bounded reads.

## When to Use

- Locate files by name (`fd`)
- Search literals/regex in contents (`rg`)
- Orient in a new directory (`tree`, `eza`)
- Read a code slice (`bat`, `sed -n`)

## Required Tools

`rg`, `fd`, `bat`; optional `tree`, `eza`, `zoxide`, `delta`, `fzf` (humans only).

{platform_install()}

## Common Commands

```bash
fd -e py -e md .
rg "pattern" src/ --glob '!node_modules' -n --max-count 40
tree -L 3 -I 'node_modules|dist|build|.git'
bat --line-range 1:120 path/to/file.py
git diff -- path/to/file | delta
```

## Agent-Safe Patterns

- {BOUNDED_LINK}
- Do not use `fzf` in agent loops (interactive TTY).
- Prefer IDE Grep/SemanticSearch/Glob when already bound in Cursor.

## Commands Requiring Confirmation

{CONFIRM_LINK}

## Troubleshooting

- `rg` slow: narrow path, add `-g`, increase excludes for `node_modules`, `dist`, `build`.
- `fd` empty: check cwd is repo root.

## Windows Notes

- `fd` from winget; on Ubuntu WSL use `fdfind` alias.
- {SPLIT_LINK}

## WSL2 Notes

- Default location for heavy search in monorepos.
- {SPLIT_LINK}

## Verification Checklist

- [ ] `rg --version` and `fd --version`
- [ ] Sample search returns bounded lines
""",
    )

    write(
        "structural-code-search",
        "Use when syntax-aware search is needed with ast-grep, semgrep, or ctags, especially after rg has too many false positives. Apply for refactors, API usage patterns, AST shapes, policy rules, or symbol indexes.",
        f"""# Structural code search

> **Tool choice first:** [`search-tool-selection`](../search-tool-selection/SKILL.md).

## Purpose

Match code **shapes** (AST patterns), run security rule packs, or use symbol indexes.

## When to Use

- Refactor targets (function signatures, imports, class shapes)
- Policy/security scans (`semgrep`)
- Repeated def/ref jumps (`ctags`)

## Required Tools

`ast-grep` (`sg`), optional `semgrep`, `universal-ctags`.

{platform_install()}

## Common Commands

```bash
sg run --pattern 'function $NAME($$$) {{ $$$ }}' --lang javascript src/
semgrep scan --config auto --max-target-bytes 1000000
ctags -R --fields=+n src/
rg "SymbolName" --type-add 'lang:*.xyz' -t lang  # fallback text search
```

Preview ast-grep rewrites with diff before applying (`sg run -r`).

## Agent-Safe Patterns

- Try `rg` first for simple literals; escalate here when noisy.
- `semgrep --dryrun` unless user requests fixes.
- {BOUNDED_LINK}

## Commands Requiring Confirmation

Mechanical rewrites and `semgrep --fix` require user approval. {CONFIRM_LINK}

## Troubleshooting

- Language not supported: fall back to `rg` with file-type globs.
- semgrep timeout: narrow paths or configs.

## Windows Notes

- `@ast-grep/cli` via npm global is reliable on Windows.
- {SPLIT_LINK}

## WSL2 Notes

- Prefer WSL for `semgrep` rule caches and large trees.
- {SPLIT_LINK}

## Verification Checklist

- [ ] `sg --version`
- [ ] Test pattern on small subdirectory first
""",
    )

    write(
        "search-tool-selection",
        "Use before any code-finding task to choose fd/find vs rg vs ast-grep vs semgrep vs fff MCP vs IDE search. Apply when deciding filename, text, syntax, symbol, config, or repeated repo-wide search strategy.",
        f"""# Search tool selection

## Purpose

Route agents to the correct search tool **before** running commands.

## When to Use

- Any code-finding or exploration task
- `rg` returns too many false positives
- Unsure whether to use shell, MCP, or IDE tools

## Required Tools

Optional: `fd`, `rg`, `ast-grep`, fff MCP (`ffgrep`, `fffind`, `fff-multi-grep`), IDE Grep/SemanticSearch/Glob.

{platform_install()}

## Common Commands

**Default escalation:** `fd` (filename) → `rg` (content) → `ast-grep` (syntax) → `bat`/`Read` (slice).

| Task | Use | Avoid |
|------|-----|-------|
| File by name/path | `fd` | `grep -r` for filenames |
| Text/literals in contents | `rg` | bare `grep -r .` |
| grep fallback | `grep` with path scope | when `rg` available |
| Syntax/AST shapes | `ast-grep` | regex alone |
| Security rule packs | `semgrep scan` | ad hoc rg for policy |
| Symbol index / cross-ref | `ctags`, Serena MCP, Zoekt | rg for every ref |
| Repo layout | `tree -L 3` | loading all paths |
| Interactive pick (human) | `fzf` | **agents** (non-interactive) |
| Config keys in JSON/YAML | `jq` / `yq` | rg on minified JSON |
| Repeated repo search (MCP connected) | **fff** `ffgrep`/`fffind` | many grep tool roundtrips |
| Architecture / path between concepts | **Graphify** `query`/`path`/`explain` (if graph exists) | broad rg when asking how subsystems connect |
| Cursor agent | Grep / SemanticSearch / Glob | shell when tool bound |

**grep vs rg:** Always prefer `rg`. Use `grep` only if `rg` is unavailable.

**fff MCP:** When connected, prefer fff tools for repo-wide file/content search; keep one-off bounded probes as `rg`/`fd`.

**Graphify (optional):** For architecture / path / community questions when `graphify-out/graph.json` exists, use graphify-knowledge-graph (`query`/`path`/`explain` or Graphify MCP) over broad rg/fff. See mcp-code-intelligence — do not run bare `graphify cursor install` in this scaffold.

**fzf:** Humans only — agents use `--max-count`, `-l`, `-g`, explicit paths.

Exclude globs: `node_modules`, `dist`, `build`, `.git` (add domain dirs in downstream projects).

## Agent-Safe Patterns

- {BOUNDED_LINK}
- Stop escalating when the task is satisfied — do not chain all tools by default.

## Commands Requiring Confirmation

{CONFIRM_LINK}

## Troubleshooting

- Too many rg hits: narrow path, add `-g '!tests'`, or switch to ast-grep.
- fff MCP unavailable: fall back to `rg`/`fd`; see mcp-code-intelligence for setup.

## Windows Notes

- IDE tools often beat shell on Windows for first pass.
- {SPLIT_LINK}

## WSL2 Notes

- ast-grep and semgrep often smoother in WSL for large repos.
- {SPLIT_LINK}

## Verification Checklist

- [ ] Picked tool matches task type (name vs text vs syntax)
- [ ] Output bounded before reading files
- [ ] fff MCP used only when server is connected
""",
    )

    write(
        "git-and-diff-workflows",
        "Use for safe Git and GitHub workflows: status, diffs, logs, branches, staging, commits, PR/issue inspection, and secret checks. Always apply before committing or when the user asks about git state, PRs, issues, or reviewing repository changes.",
        f"""# Git and diff workflows

## Purpose

Repository operations with bounded diffs and explicit confirmation for history rewrites.

## When to Use

- Before/after edits (`status`, `diff`)
- PR/issue work (`gh`)
- Secret scanning (`gitleaks` read-only)

## Required Tools

`git`, `gh`; optional `delta`, `gitleaks`, `git-filter-repo` (human-only).

{platform_install()}

## Common Commands

```bash
git status --short
git diff --stat
git diff -- path/to/file
git log --oneline -n 20
gh pr view 123 --json title,state,url
gh issue list --limit 20
gitleaks detect --source . --no-git -v 2>/dev/null | head -50
```

## Agent-Safe Patterns

- Always `git status --short` before staging.
- Show `git diff --stat` before commit messages.
- {BOUNDED_LINK}

## Commands Requiring Confirmation

{CONFIRM_LINK} — especially reset, clean, force-push, filter-repo.

## Troubleshooting

- Detached HEAD: ask user before checkout.
- `gh` auth: user runs `gh auth login`.

## Windows Notes

- Line endings: watch for CRLF noise in diffs.
- {SPLIT_LINK}

## WSL2 Notes

- Commit from same environment as tests ran.
- {SPLIT_LINK}

## Verification Checklist

- [ ] `git status` clean or changes understood
- [ ] Diff reviewed before commit
""",
    )

    write(
        "data-config-tools",
        "Use when inspecting, querying, validating, or editing JSON, YAML, TOML, CSV, HTTP responses, or local SQLite/config data. Prefer jq/yq/sqlite/curl over raw text search, especially for minified or structured data.",
        f"""# Data and config tools

## Purpose

Structured queries against config files and lightweight API checks.

## When to Use

- Read `package.json`, `docker-compose.yml`, CI YAML keys
- Probe local HTTP endpoints
- Inspect sqlite schemas (read-only)

## Required Tools

`jq`, `yq`, `curl`; optional `dasel`, `sqlite3`, `httpie`.

{platform_install()}

## Common Commands

```bash
jq '.scripts' package.json
jq -r '.dependencies | keys[]' package.json | head -20
yq '.services' docker-compose.yml
curl -fsS -o /dev/null -w '%{{http_code}}\\n' http://localhost:8080/health
sqlite3 app.db '.schema' | head -40
```

## Agent-Safe Patterns

- Prefer jq/yq over `rg` on JSON/YAML.
- curl: no credentials in URLs; {BOUNDED_LINK}

## Commands Requiring Confirmation

POST/PUT/DELETE via curl against production; sqlite writes. {CONFIRM_LINK}

## Troubleshooting

- Invalid JSON: `jq empty < file` to validate.
- yq version differences: note v4 vs mikefarah syntax.

## Windows Notes

- jq via winget; quote JSON paths in PowerShell carefully.
- {SPLIT_LINK}

## WSL2 Notes

- Prefer WSL curl against WSL-hosted services.
- {SPLIT_LINK}

## Verification Checklist

- [ ] `jq --version`, `yq --version`
- [ ] Queries return bounded output
""",
    )

    write(
        "task-env-package-tools",
        "Use for synthet-code-framework task runners, uv, Docker, sync checks, frontmatter validation, OKF lint, pytest, and project verification gates. Apply when running repo-specific tests/checks or diagnosing environment/package tooling.",
        f"""# Task, environment, and package tools

## Purpose

Run builds/tests/lint via project conventions; manage Python/Node envs safely.

## When to Use

- Running framework or bootstrapped project checks
- Docker compose for local services
- Choosing `just`/`mise`/`npm run` over ad hoc commands

## Required Tools

Project-defined; framework defaults: `python`, `uv`, optional `docker`, `just`, `mise`, `pnpm`.

{platform_install()}

## Common Commands

Framework quality gates (this repo):

```bash
python scripts/sync_assistant_trees.py --check
python scripts/ci/check_agent_frontmatter.py
python scripts/okf_lint.py --profile project --exclude-prefix archive/ docs
python -m pytest tests -q
python scripts/validate_cli_skills.py
```

Bootstrapped projects use tokens from AGENTS.md:

```bash
${{BUILD_CMD}}
${{TEST_CMD}}
${{LINT_CMD}}
```

Docker (when compose file exists):

```bash
docker compose config
docker compose up -d --build
docker compose logs --tail=50 service_name
```

## Agent-Safe Patterns

- Read AGENTS.md / Makefile / package.json scripts before inventing commands.
- Docker down/prune needs confirmation. {BOUNDED_LINK}

## Commands Requiring Confirmation

{CONFIRM_LINK}; `docker system prune`, broad `pip install`, production deploy scripts.

## Troubleshooting

- Sync drift: run `python scripts/sync_assistant_trees.py` after editing `.claude/` to update Cursor and Codex mirrors.
- pytest failures: narrow to failing test file first.

## Windows Notes

- Run Python from project venv when documented.
- {SPLIT_LINK}

## WSL2 Notes

- Prefer WSL for Linux CI parity.
- {SPLIT_LINK}

## Verification Checklist

- [ ] `${{TEST_CMD}}` or pytest green for touched area
- [ ] sync + frontmatter checks when agent assets changed
""",
    )

    write(
        "lint-format-security",
        "Use when running or choosing bounded linters, formatters, type checks, or security scanners such as ruff, prettier, eslint, shellcheck, trivy, hadolint, or gitleaks. Apply before merge when the user asks for lint, format, static analysis, or security checks.",
        f"""# Lint, format, and security

## Purpose

Static analysis and container/config scanning without silent auto-fix at scale.

## When to Use

- Python: `ruff`, `pyright`
- JS/TS: `eslint`, `prettier`
- Shell: `shellcheck`
- Containers/IaC: `hadolint`, `trivy`

## Required Tools

Project-defined; common: `ruff`, `eslint`, `prettier`, `shellcheck`, `trivy`.

{platform_install()}

## Common Commands

```bash
ruff check path/to/module --output-format=concise
ruff format --check path/to/module
eslint src/ --max-warnings 0
prettier --check 'src/**/*.{{ts,tsx,json}}'
shellcheck scripts/*.sh
trivy fs --scanners vuln --exit-code 0 .
```

## Agent-Safe Patterns

- Check mode before write/fix mode.
- Scope to changed paths.
- {BOUNDED_LINK}

## Commands Requiring Confirmation

`--fix`, `--write`, `--auto-fix` on broad trees. {CONFIRM_LINK}

## Troubleshooting

- Missing plugins: use project devDependencies / uv tools.
- trivy DB download: may need network once.

## Windows Notes

- Prefer project-local `npx eslint` over global installs.
- {SPLIT_LINK}

## WSL2 Notes

- Match CI linter versions when possible.
- {SPLIT_LINK}

## Verification Checklist

- [ ] Linters run on narrowest scope
- [ ] User approved any auto-fix
""",
    )

    write(
        "mcp-code-intelligence",
        "Use when choosing or comparing code-intelligence/search backends such as text search, ast-grep, Serena, Zoekt, fff MCP, Graphify, embeddings, or IDE semantic search. Apply when repo search is repeated, cross-reference heavy, or plain rg is insufficient.",
        f"""# MCP code intelligence

## Purpose

Choose the right code-intelligence layer: shell tools, MCP servers, embeddings.

## When to Use

- Setting up agent MCP servers
- Deciding fff vs rg vs semantic/embedding search
- Evaluating Serena, Zoekt, Graphify, codebase-memory-mcp

## Required Tools

Optional MCP: fff (`ffgrep`, `fffind`, `fff-multi-grep`), Graphify (`query_graph`, `get_node`, …), ast-grep MCP, Serena, Zoekt, embedding servers.

{platform_install()}

## Common Commands

**Tier recommendation:**

```text
Minimal:  rg + fd + read_file + git diff + patch_file (IDE/shell)
Better:   above + ast-grep + gh + task runner + fff MCP (optional)
Advanced: Serena or codebase-memory-mcp + Zoekt + optional Graphify + optional embeddings
```

**fff MCP (optional):** Install [fff-mcp](https://github.com/dmtrKovalenko/fff); add to `.cursor/mcp.json` from `.cursor/mcp.example.json` `_examples.proj-ro-fff`. Reload MCP. Prefer fff for repeated repo file/content search when connected.

**Graphify (optional knowledge graph):** Package is `graphifyy`; CLI is `graphify`.

1. `uv tool install graphifyy` (MCP: `uv tool install "graphifyy[mcp]"`).
2. Build a local graph: `graphify .` (AST code map is free/local; docs/media may use a model backend).
3. Query via CLI (`graphify query` / `path` / `explain`) or copy `_examples.proj-ro-graphify` from `.cursor/mcp.example.json` / `.mcp.json` into gitignored `.cursor/mcp.json` (needs `graphify-out/graph.json`).
4. **Do not** run bare `graphify cursor install` or `graphify install --project` in this scaffold — those write under `.cursor/` / inject AGENTS.md and fight `.claude/` → sync SoT. Prefer this docs + MCP path, or a user-global install outside the repo.

**Using the graph:** once MCP or `graphify-out/graph.json` exists, follow [graphify-knowledge-graph](../graphify-knowledge-graph/SKILL.md) for query/path/god-node workflows.

**Warning:** Embedding-first indexing is memory-heavy — use after rg/ast-grep/fff.

Compare:

| Layer | Best for |
|-------|----------|
| CLI rg/fd | Fast text, gitignore-aware |
| fff MCP | Indexed repo search, multi-pattern grep |
| ast-grep MCP / sg | Structural patterns |
| Serena / ctags | Symbols, refs |
| Zoekt | Large org code search |
| Graphify | Architecture / path / community queries over `graphify-out/` |
| Embeddings | Fuzzy conceptual search (secondary) |

## Agent-Safe Patterns

- Read MCP tool schemas before CallMcpTool.
- No secrets in MCP args; {BOUNDED_LINK}

## Commands Requiring Confirmation

MCP tools that write files or run jobs need user intent. {CONFIRM_LINK}

## Troubleshooting

- fff not found: add `%LOCALAPPDATA%\\fff-mcp\\bin` to PATH or use full path in mcp.json.
- graphify-mcp won't start: confirm `graphify-out/graph.json` exists and `graphifyy[mcp]` is installed.
- MCP server won't start: check WORKSPACE_ROOT env.

## Windows Notes

- fff-mcp runs natively on Windows; many MCP servers prefer WSL.
- {SPLIT_LINK}

## WSL2 Notes

- Run Unix-first MCP servers here.
- {SPLIT_LINK}

## Verification Checklist

- [ ] MCP tier matches task (text before embeddings)
- [ ] fff optional and documented as opt-in
- [ ] Graphify optional and documented as opt-in (no bare cursor install)
- [ ] Tool schemas read before first call
""",
    )

    write(
        "windows-agent-tooling",
        "Use for native Windows agent workflows involving PowerShell, winget, Cursor IDE, Docker Desktop, path conventions, and decisions about when WSL is optional. Apply when the environment or user request is Windows-specific.",
        f"""# Windows agent tooling

## Purpose

Effective agent work on Windows host without unnecessary WSL hops.

## When to Use

- User workspace is native Windows
- Simple search, edit, gh, uv, pnpm tasks
- Docker Desktop on Windows

## Required Tools

PowerShell, `git`, `rg`, `fd`, `gh`, optional Docker Desktop.

{platform_install()}

## Common Commands

```powershell
git status --short
rg "pattern" . --glob '!node_modules' -n --max-count 30
fd -e md .
Get-Content .\\README.md -TotalCount 80
gh pr list --limit 10
```

## Host / WSL split

```text
Windows host:
  Cursor / VS Code / Claude Desktop / Docker Desktop / local LLM apps
  Simple rg/fd, GitHub CLI, uv/pnpm on native paths

WSL2 Ubuntu:
  repositories (optional), ast-grep, MCP stdio servers, CI-like tests
```

When native Windows is enough: simple search, editing, GitHub CLI, Python with `uv`, Node with `pnpm`.

When WSL2 is better: Bash-heavy repos, Docker Compose Linux paths, MCP Unix servers, monorepo CI parity.

Full diagram: [windows-wsl-split.md](../cli-tools-overview/references/windows-wsl-split.md).

## Agent-Safe Patterns

- Avoid mixing `D:\\` and `/mnt/d/` in one workflow.
- {BOUNDED_LINK}

## Commands Requiring Confirmation

{CONFIRM_LINK}

## Troubleshooting

- Execution policy blocking scripts: user adjusts policy for their profile.
- Docker not running: start Docker Desktop before compose commands.

## Windows Notes

- Primary environment for this skill.
- Optional fff-mcp at `%LOCALAPPDATA%\\fff-mcp\\bin\\fff-mcp.exe`.

## WSL2 Notes

- Escalate to [wsl2-agent-tooling](../wsl2-agent-tooling/SKILL.md) when tools fail on native Windows.
- {SPLIT_LINK}

## Verification Checklist

- [ ] Core tools available in PowerShell
- [ ] Chosen Windows vs WSL for this task
""",
    )

    write(
        "wsl2-agent-tooling",
        "Use for WSL2 Ubuntu agent workflows: repos under Linux filesystem, apt tooling, builds/tests, ast-grep, MCP servers, Docker/Windows interop, and CI-like commands. Apply when the environment or user request is WSL2-specific.",
        f"""# WSL2 agent tooling

## Purpose

Run agent shell work in WSL2 when Linux tooling, paths, or MCP servers require it.

## When to Use

- Bash-heavy repos and shell scripts
- Docker Compose with Linux paths
- ast-grep, semgrep, MCP stdio servers
- Reproducing GitHub Actions locally

## Required Tools

WSL2 Ubuntu, `git`, `rg`, `fd`, build chain for the project.

{platform_install()}

## Common Commands

```bash
cd ~/projects/my-repo
git status --short
rg "pattern" . --glob '!node_modules' -n --max-count 30
sg run --pattern 'import $M from $P' --lang ts src/ | head -40
docker compose up -d
python -m pytest tests/test_foo.py -q
```

## Host / WSL split

```text
Windows host:
  Cursor / VS Code / Claude Desktop / Docker Desktop

WSL2 Ubuntu:
  git checkout, rg/fd/jq/yq, ast-grep, build/test, MCP servers
```

Full diagram: [windows-wsl-split.md](../cli-tools-overview/references/windows-wsl-split.md).

## Agent-Safe Patterns

- Open repo from WSL path (`~/...`), not `/mnt/c/...` when performance matters.
- {BOUNDED_LINK}

## Commands Requiring Confirmation

{CONFIRM_LINK}

## Troubleshooting

- `fd` command: use `fdfind` or symlink from install reference.
- Docker in WSL: enable WSL integration in Docker Desktop.

## Windows Notes

- IDE may edit via `\\\\wsl$\\` — run tests in WSL terminal.
- {SPLIT_LINK}

## WSL2 Notes

- Primary environment for this skill.

## Verification Checklist

- [ ] `uname -a` shows WSL
- [ ] Project tests run in WSL checkout
""",
    )


if __name__ == "__main__":
    main()
