# Subagents and logical roles — Everypixel MCP

Concrete subagent definitions live in [`.claude/agents/`](../../.claude/agents/) (mirrored to
`.cursor/agents/`). This file maps **logical roles** (for planning) to those files and to the
allowed/forbidden edits each role operates under.

## Role matrix

| Logical role | Concrete subagent / skill | Responsibility |
|--------------|---------------------------|----------------|
| implementer | `<your-implementer-agent>` | Targeted feature/fix with minimal diff + tests |
| diagnostics | `<your-diagnostics-agent>` | Read-only triage (logs, health, queries) |
| pr-ready | [`pr-ready-hygiene`](../../.claude/agents/pr-ready-hygiene.md) | Lint/test, self-review, PR text |
| critical-audit | [`critical-commit-audit`](../../.claude/agents/critical-commit-audit.md) | High-severity post-commit bug hunt |
| external-review | [`external-cli-reviewer`](../../.claude/agents/external-cli-reviewer.md) | Review-only Codex/Gemini via MCP |

Add project-specific roles (UI, data layer, infra, …) as you create their agents.

## Allowed vs forbidden edits (defaults)

| Role | Allowed | Forbidden |
|------|---------|-----------|
| Diagnostics | Read-only tool calls, read-only queries, log inspection | write/destructive tools without explicit request |
| Implementer | Targeted code in its scope + tests | out-of-scope code; breaking a contract without coordination |
| PR-ready hygiene | Lint/tests on changed paths | disabling tests; clearing whole-repo lint debt |
| Critical audit | Minimal fix + test when a bug is proven | speculative refactors |
| External review | review-only MCP (`allowWrites:false`); read `.agent-runs/` | auto-applying patches; `allowWrites:true` |

## Validation after implementer roles touch code

- Run lint on touched files and the narrowest test scope that covers the change (per `AGENTS.md`).

## Handoff

- Cross-repo API/schema changes follow
  [`../workflows/cross_repo_contract_change.md`](../workflows/cross_repo_contract_change.md).
