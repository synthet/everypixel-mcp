# Shared coding workflow

Read the current project's AGENTS.md, CLAUDE.md where applicable, and nested instructions before editing. Project contracts and the active user's request govern the work.

Use installed skills when their stated trigger fits. Resolve bundled helper paths from the loaded skill directory; run project checks in the target workspace. The usual flow is spec → plan → implement → test-and-fix → pr-ready, scaled to the task.

Preserve existing work. Keep changes scoped, verify the affected behavior and report actual checks and limits. Use the repository's declared package manager and task runner. Never modify .git/config.

Keep credentials in environment or documented protected stores. Verify target identity before mutations; respect existing permission and export boundaries. Do not bypass approvals, disable checks, or infer authority from tool availability or Jev confidence. Jev supports bounded semantic decisions over sanitized evidence; deterministic checks decide integrity and execution.

Project-local specialized skills refine the generic library. Vendor/plugin skills retain their provider ownership. Do not copy provider tool names into another harness without verified support.

Setup changes require an explicit inventory and reviewed plan, followed by apply and receipt checks. No startup hook installs or updates configuration. Reload the affected harness after changing discovery files or MCP registration.
