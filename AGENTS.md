# AI Agents Configuration — Everypixel MCP

## Overview

This repo ships agent scaffolding for Claude Code, Cursor, and Codex: commands, skills, subagents,
safety rules, an `.agent/` governance hub, a project-memory subsystem, and OKF docs tooling. This
file is the **source of truth** for how agents build/test/run and which tools they may use.

## Authoring & skill source of truth

- **Canonical** assets are authored under `.claude/` (+ `.agent/`).
- The **`.cursor/`** tree and Codex-native **`.agents/skills/`** + **`.codex/agents/`** trees are
  **generated** by `python scripts/sync_assistant_trees.py` — do not hand-edit generated files.
- When you change a skill/command/agent, run the sync and commit all generated mirrors in the **same PR**
  (see [`.agent/SKILL_CHANGE_AST10_REVIEW.md`](.agent/SKILL_CHANGE_AST10_REVIEW.md)).

## Commands

```bash
pip install -e ".[dev]"   # build + test deps
python -m pytest          # unit tests (mocked Everypixel API; no live spend)
ruff check src tests      # lint
everypixel-mcp mcp        # stdio MCP server
everypixel-mcp doctor     # offline readiness + MCP handshake
```

## MCP servers

- Define project servers in [`.mcp.json`](.mcp.json) (Claude Code), copy
  [`.cursor/mcp.example.json`](.cursor/mcp.example.json) → `.cursor/mcp.json` (gitignored) for Cursor,
  and use [`.codex/config.toml`](.codex/config.toml) or `~/.codex/config.toml` for Codex.
- **Naming:** `<scope>-<role>-*` (e.g. `everypixel-rw-labs`).
- **Secrets via env only**, never CLI args. Reload the MCP client after changing keys.
- User-level `~/.cursor/mcp.json` holds cross-repo tools; project keys live in this repo.

### Workstation bootstrap (`everypixel-rw-labs` + `everypixel-mcp` skill)

One command wires the **same** stdio server and copies the **`everypixel-mcp`** skill to active
projects and user-level Codex/Gemini skill dirs:

```bash
python scripts/install_everypixel_mcp_workstation.py   # requires uv; optional EVERYPIXEL_MCP_ROOT
everypixel-mcp doctor                                  # credential + MCP handshake (no live API spend)
```

| Client | Config updated by installer |
|--------|-----------------------------|
| **Cursor** | `~/.cursor/mcp.json` + this repo's `.cursor/mcp.json` |
| **Claude Code** | `~/.claude.json` + project [`.mcp.json`](.mcp.json) |
| **Claude Desktop** | `%APPDATA%\Claude\claude_desktop_config.json` |
| **Codex** | `~/.codex/config.toml` (`[mcp_servers.everypixel-rw-labs]`) + `~/.codex/skills/everypixel-mcp/` |
| **Gemini CLI** | `~/.gemini/settings.json` + `~/.gemini/skills/everypixel-mcp/` |
| **Antigravity** | `~/.gemini/antigravity/mcp_config.json` and `~/.gemini/config/mcp_config.json` |

Reload MCP in each IDE/CLI after install. Secrets stay in checkout `.env` via `EVERYPIXEL_ENV_FILE`; the
installer never writes tokens into JSON/TOML.

## Available tools

<!-- BEGIN MCP TOOL INVENTORY -->
| Server (example key) | Tools (when connected) | Notes |
|----------------------|------------------------|-------|
| `everypixel-rw-labs` | `everypixel_status`, `everypixel_analyze`, `everypixel_image`, `everypixel_video`, `everypixel_lipsync`, `everypixel_tts`, `everypixel_transcribe`, `everypixel_chat` | Everypixel Labs v1; set `EVERYPIXEL_CLIENT_ID` + `EVERYPIXEL_CLIENT_SECRET`; see `.mcp.json` |
| `fff-mcp` / `everypixel-fff` | `ffgrep`, `fffind`, `fff-multi-grep` | Opt-in; see `.cursor/mcp.example.json` |
| `graphify-mcp` / `everypixel-graphify` | `query_graph`, `get_node`, `get_neighbors`, `shortest_path`, … | Opt-in; needs `graphify-out/graph.json`; see `_examples.proj-ro-graphify` |
<!-- END MCP TOOL INVENTORY -->

## Default tool permissions

- **Default mode is read-only.** The active Claude Code allowlist in [`.claude/settings.json`](.claude/settings.json) permits only read-oriented operations: `git status`, `git diff:*`, `git log:*`, and `WebSearch`.
- **Opt into local writes intentionally.** When a maintainer wants an agent to stage or commit local repository changes, copy [`.claude/settings.write.example.json`](.claude/settings.write.example.json) to a local/user settings file or otherwise merge only the needed entries (`Bash(git add:*)`, `Bash(git commit:*)`) into the active allowlist. Do not broaden permissions by default.
- **Remote writes are higher risk than local writes.** `gh pr:*`, `gh issue:*`, and `gh project:*` can mutate GitHub state and notify collaborators. Enable them only for a specific task and verify the target repo/project before use.
- **External export requires explicit approval.** Sending source, prompts, logs, artifacts, or review bundles to external services/providers is not covered by local-write approval; get explicit approval for the export and exclude secrets.
- **Seeded projects inherit this safer default.** Because `.claude/settings.json` is part of the scaffold, newly bootstrapped projects start in read-only mode unless a maintainer deliberately opts into write permissions.

## Common workflows

`/spec → /plan → /implement → /test-and-fix → /pr-ready`. See
[`docs/ai-workflow/README.md`](docs/ai-workflow/README.md) for the full asset map and loop, and
[`.agent/workflows/`](.agent/workflows/) for playbooks.

## Git configuration — do not modify

Never modify `.git/config` or add non-standard git extensions (do not set
`extensions.worktreeConfig` or change `core.repositoryformatversion`). Embedded git libraries in
third-party tooling choke on non-standard extensions and break workspace resolution. If a worktree is
needed, use a temporary one and clean it up immediately.

## Test vocabulary

| You say | Canonical name | Where | How to run |
|---------|----------------|-------|------------|
| Unit tests | Offline unit & MCP protocol tests | `tests/` | `python -m pytest` |
| Live check | Read-only live diagnostic | `src/everypixel_mcp/doctor.py` | `everypixel-mcp doctor --live` |

## Coding-agent contract

- **Code style:** match the surrounding code; follow the repo's formatter/linter.
- **Package boundaries:** touch one module/package per task; use shared types. Do not reach across
  boundaries without an explicit contract change.
- **Security (hard rules):** secrets via env/`secrets.json` only; validate external inputs;
  side-effecting/destructive ops require confirmation; never modify `.git/config`. See
  [`docs/security.md`](docs/security.md) and [`.agent/SAFETY.md`](.agent/SAFETY.md).
- **Change control:** minimal diffs, tests for behavior changes, no unrelated refactors.
- **Prohibited:** committing secrets, disabling/weakening tests to go green, drive-by reformatting,
  inventing API paths / config keys / schema names (check
  [`docs/CANONICAL_SOURCES.md`](docs/CANONICAL_SOURCES.md)).

## RCA / Failure Log

Append-only record of **non-obvious failures** and their root causes, so the next agent does not
re-debug them.

| Date | Symptom | Root cause | Fix / guard |
|------|---------|------------|-------------|
| _(none yet)_ | | | |

## AI workspace assets

| Asset | Location |
|-------|----------|
| Claude commands | `.claude/commands/*.md` |
| Claude skills | `.claude/skills/*/SKILL.md` |
| Claude subagents | `.claude/agents/*.md` |
| Claude rules | `.claude/rules/*.md` |
| Cursor mirror (generated) | `.cursor/{rules,commands,skills,agents}` |
| Codex skills (generated) | `.agents/skills/*/SKILL.md` |
| Codex subagents (generated) | `.codex/agents/*.toml` |
| Codex project config | `.codex/config.toml` |
| MCP templates/config | `.mcp.json`, `.cursor/mcp.example.json`, `.codex/config.toml` |
| Agent governance | `.agent/` |
| Project memory | `.agent-memory/` |
| Workflow playbooks | `.agent/workflows/*.md` |
| Workflow index | `docs/ai-workflow/README.md` |

<!-- BEGIN FRAMEWORK SETUP -->

## Shared agent setup

Project-specific instructions in this file and nested instruction files govern this workspace.
Reusable skills are authored in `.claude/skills/`; other harness trees are generated.
Run installed helpers relative to their skill directory; run project checks from this workspace.
Preserve user edits, credentials, model settings, permissions and unrelated configuration.
- Build: `uv sync`
- Test: `uv run pytest`
- Lint: `uv run ruff check .`

<!-- END FRAMEWORK SETUP -->

<!-- FRAMEWORK RULE REFERENCES -->
Read the always-on project rules before working:
- `.claude/rules/karpathy-coding.md`
- `.claude/rules/safety-and-secrets.md`
- `.claude/rules/sdlc-core.md`
<!-- END FRAMEWORK RULE REFERENCES -->
