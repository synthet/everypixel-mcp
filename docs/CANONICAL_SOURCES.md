---
type: Source-of-Truth Map
title: Canonical Sources
description: Authority map — the single source of truth for each contract, convention, and config in this project.
resource: CANONICAL_SOURCES.md
tags: [docs, governance, authority]
timestamp: 2026-10-18T00:00:00Z
okf_version: 0.1
---

# Canonical sources

Agents and contributors must check this map before inventing API paths, schema names, config keys, or
status values.

| Contract / convention | Source of truth |
|-----------------------|-----------------|
| Public MCP tool shape | [`src/everypixel_mcp/mcp_server.py`](../src/everypixel_mcp/mcp_server.py) and [`api.md`](api.md) |
| Endpoint & model catalog | [`src/everypixel_mcp/catalog.py`](../src/everypixel_mcp/catalog.py) (`everypixel://catalog/endpoints`, `everypixel://catalog/models`) |
| Config & env keys | [`env.example`](../env.example) and [`src/everypixel_mcp/dotenv_util.py`](../src/everypixel_mcp/dotenv_util.py) |
| Operation & envelope types | [`src/everypixel_mcp/models.py`](../src/everypixel_mcp/models.py) |
| Local media confinement | [`src/everypixel_mcp/media.py`](../src/everypixel_mcp/media.py) and [`media.md`](media.md) |
| Build / test / lint commands | [`../AGENTS.md`](../AGENTS.md) |
| Codex project configuration | [`.codex/config.toml`](../.codex/config.toml) and [`.codex/README.md`](../.codex/README.md) |
| Optional file-search MCP (fff) | [fff repo](https://github.com/dmtrKovalenko/fff); template keys `fff-mcp` / `everypixel-fff` in [`.cursor/mcp.example.json`](../.cursor/mcp.example.json) |
| CLI tooling skills spec | [`.agent/cli-tools-skills-spec.md`](../.agent/cli-tools-skills-spec.md) |
| CLI install tier order | [`.claude/skills/cli-tools-overview/references/install-tiers.md`](../.claude/skills/cli-tools-overview/references/install-tiers.md) |
| Agent CLI environment (PATH, Cursor restart) | [`.claude/skills/cli-tools-overview/references/agent-environment.md`](../.claude/skills/cli-tools-overview/references/agent-environment.md) |
| Agent assets (rules/commands/skills/agents) | [`ai-workflow/README.md`](ai-workflow/README.md) |
| Safety rules | [`../.agent/SAFETY.md`](../.agent/SAFETY.md) |
| Wiki conventions | [`WIKI_SCHEMA.md`](WIKI_SCHEMA.md) |

**Rule:** code and the written contract must never disagree. If you change one, change the other in
the same PR (see [`../.agent/workflows/cross_repo_contract_change.md`](../.agent/workflows/cross_repo_contract_change.md)).
