---
name: cli-tools-overview
description: Use as the router for agent CLI workflows: installing tools, choosing safe shell patterns, navigating/searching repos, Git/MCP operations, and task runners. Start here whenever the user asks which command-line tool or workflow to use, or when another CLI skill is not obviously more specific.
capability: "cli-tools-overview agent asset workflow"
side_effect_level: read_only
approval_required: false
requires_tools: "See asset body for tool requirements."
output_schema: "Markdown report or documented command output."
risk_class: low
---

# CLI tools overview

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

## Install

Install blocks are shared — See [install-blocks.md](../cli-tools-overview/references/install-blocks.md).

### Windows PowerShell

Use winget blocks from the reference when provisioning a new machine.

### WSL2 Ubuntu

Use apt/curl blocks from the reference; symlink `fdfind` → `fd` if needed.

### macOS

Use Homebrew blocks from the reference.


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
- See [bounded-output-patterns.md](../cli-tools-overview/references/bounded-output-patterns.md).

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

## Commands Requiring Confirmation

See [commands-requiring-confirmation.md](../cli-tools-overview/references/commands-requiring-confirmation.md).

## Troubleshooting

See topic skill for tool-specific failures.

## Windows Notes

- Prefer `rg` and `fd` from winget; PowerShell aliases may shadow Unix names — use full binary names if commands fail.
- See [windows-wsl-split.md](../cli-tools-overview/references/windows-wsl-split.md).

## WSL2 Notes

- Use Linux packages in WSL; avoid calling Windows binaries for repo work when Linux equivalents exist.
- See [windows-wsl-split.md](../cli-tools-overview/references/windows-wsl-split.md).

## Verification Checklist

- [ ] Required tools respond (`--version` or `--help`)
- [ ] Commands use bounded output (See [bounded-output-patterns.md](../cli-tools-overview/references/bounded-output-patterns.md).)
- [ ] Destructive ops gated per confirmation reference
