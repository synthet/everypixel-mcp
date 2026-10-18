---
type: Reference
title: Multi-harness agent setup
description: Explicit inventory, review, deployment and verification of portable agent assets.
resource: agent-setup.md
tags: [agents, skills, configuration]
timestamp: 2026-10-11T00:00:00Z
okf_version: 0.1
---

# Multi-harness agent setup

The framework maintains a portable library for Claude Code, Codex, Cursor and
Antigravity. Author skills, commands, agents and rules under `.claude/`; author
governance under `.agent/`. Generate the framework mirrors with
`python scripts/sync_assistant_trees.py`. Workstation deployment is a separate,
explicit inventory → review plan → apply → check workflow.

```powershell
python -X utf8 scripts/agent_setup.py inventory
python -X utf8 scripts/agent_setup.py plan --out .agent/local/setup/plan.json
# Review coverage, conflicts, dependencies and each destination before applying.
python -X utf8 scripts/agent_setup.py apply --input .agent/local/setup/plan.json
python -X utf8 scripts/agent_setup.py check --input <receipt.json>
```

Use `--project <name>` repeatedly for a pilot, or `--scope global|projects`.
Override `--projects-root` and `--user-root` for another workstation. Python
3.11+ is required; the installer has no third-party dependencies. Use the
project's declared Python runner if `python` is unavailable. Installation never
runs on harness startup and never downloads or upgrades harnesses.

## Library and routing

[The manifest](../.agent/setup/library.json) defines 55 reusable skills: 40 core
skills and 15 specialists. All are available globally; self-contained project
deployments receive core skills, applicable specialist packs and their existing
project-specific skills. [The decision ledger](../.agent/setup/decisions.json)
records Jev judgments and reviewed routing; [rollout judgments](../.agent/setup/rollout-decisions.json)
cover native variants and hook portability. Jev receives sanitized, bounded
evidence; confidence is advisory. File hashes, native schemas and project
contracts determine whether an operation can execute.

Specialist packs cover agent tools, knowledge/transcript archiving, maintenance,
containers, databases, Electron, rollout flags, Gradio, vision evaluation,
observability, TypeScript, Unity and bounded Windows keep-awake jobs. Existing
specialist workflows take precedence over generic library assets. Equivalent
PR, fork, dependency and MCP diagnostic guidance is merged into existing skills.
Provider-owned plugins retain their native ownership and activation settings.

## Native discovery

| Asset | Claude Code | Codex | Cursor | Antigravity |
|---|---|---|---|---|
| Project guidance | `CLAUDE.md` includes `AGENTS.md` | `AGENTS.md` | `AGENTS.md` and native rules | `AGENTS.md`, compatibility `GEMINI.md` |
| Project skills | `.claude/skills` | `.agents/skills` | Shared `.agents/skills` / `.claude/skills` | `.agents/skills` |
| Project agents | `.claude/agents/*.md` | `.codex/agents/*.toml` | `.cursor/agents/*.md` | `.agents/agents/*.md` |
| Project rules | `.claude/rules/*.md`, native `paths` | Always-on references in `AGENTS.md` | `.cursor/rules/*.mdc` | `.agents/rules/*.md`, native triggers |
| Project MCP | `.mcp.json` | `.codex/config.toml` | `.cursor/mcp.json` | `.agents/mcp_config.json` |
| Global guidance | `~/.claude/CLAUDE.md` | `~/.codex/AGENTS.md` | `~/.cursor/rules/framework-shared.mdc` | `~/.gemini/GEMINI.md` and config rule |
| Global skills | `~/.claude/skills` | `~/.agents/skills` | Shared user skill roots | `~/.gemini/config/skills`, CLI skill root |
| Global MCP | `~/.claude.json` | `~/.codex/config.toml` | `~/.cursor/mcp.json` | `~/.gemini/config/mcp_config.json` |

Commands remain native Claude/Cursor commands. Explicit `framework-<command>`
skills provide the same workflow to other harnesses without replacing built-in
commands. Manual Cursor rules become explicit Claude skills rather than loading
unconditionally. Agent models and tools are adapted only to supported native
fields. Legacy installations are preserved. Equivalent Codex discovery copies
can be disabled in user configuration while repositories remain standalone.

## Preservation and receipts

Inventory includes maintained roots, upstream checkouts, archives, aliases and
installed provider packages. Apply selects synthet-owned repositories and local
maintained source projects; it excludes upstream-owned checkouts, archives,
linked aliases and duplicate worktrees. The framework itself uses its canonical
synchronizer. Review ownership before applying on another workstation.

Existing project synchronizers retain their declared canonical direction.
Reviewed generators render in an isolated staging tree during planning, including
their native rule conversions and any required Cursor mirrors. Only generated
stale files are removed, with individual backups; Python caches are excluded
without relaxing content comparisons. Project-specific generators are not
replaced with the framework generator.

Plans contain exact content and before/after hashes. Apply verifies the reviewed
manifest and installer, guards paths against traversal and links, backs up every
replacement and writes a durable journal and receipt. Unknown differences and
overlapping edits remain conflicts. Owned assets permit nonoverlapping merges.
Live MCP configuration changes permit only narrow additive replay of reviewed
registrations; current credentials, permissions, models and caches survive.
Rollback restores only writes whose hashes still match the receipt:

```powershell
python -X utf8 scripts/agent_setup.py rollback --input <receipt.json>
```

Private inventories, plans, ownership baselines and backups are in ignored
`.agent/local/setup/`. They may contain original private configuration: do not
commit or export them. `.git/config` is read only. Existing model choices,
credentials, permission allowlists, hooks and plugin activation remain intact.

MCP adapters add validated missing registrations. Credentials stay in inherited
environment references. Disabled sources, unsupported authentication and missing
executables/paths are reported rather than activated. Existing conflicting
registrations remain authoritative. Native hooks are inventoried and preserved;
Claude Warp/OSC callbacks are not copied to incompatible event protocols.

Receipt integrity proves installation, not server health. Reload each affected
harness and check its MCP/discovery UI; remote connectivity and authentication
must be checked in that harness. Re-run plan to verify convergence after reload.

Native references: [Claude MCP](https://code.claude.com/docs/en/mcp),
[Codex skills](https://learn.chatgpt.com/docs/build-skills),
[Codex agents](https://learn.chatgpt.com/docs/agent-configuration/subagents),
[Cursor skills](https://cursor.com/docs/skills),
[Cursor MCP](https://cursor.com/docs/mcp),
[Antigravity skills](https://antigravity.google/docs/skills),
[Antigravity rules](https://antigravity.google/docs/rules).
