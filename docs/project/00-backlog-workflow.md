---
type: Runbook
title: Backlog Workflow
description: The canonical provider-oriented backlog contract — pick, claim, transition status, and reference work in PRs.
resource: project/00-backlog-workflow.md
tags: [docs, project, backlog, workflow]
timestamp: 2026-06-16T00:00:00Z
okf_version: 0.1
---

# Backlog workflow

The canonical task queue is the project's configured **backlog provider**, not ad hoc `TODO.md`
notes. The full agent-facing rules live in the
[`backlog-queue`](../../.claude/skills/backlog-queue/SKILL.md) skill; provider-specific setup lives
under [`.agent/backlog/`](../../.agent/backlog/README.md).

## Default provider choices

- **Local Markdown** for generic/offline projects.
- **GitHub Issues** for GitHub-hosted projects without a board.
- **GitHub Projects** only when the project explicitly adopts a board provider.

Missing GitHub Projects board IDs are not mandatory for generic projects. Fill them only when using
[the GitHub Projects provider](../../.agent/backlog/providers/github-projects.md).

## The five-step contract

1. **Pick** from the provider's ready queue, sorted by priority. If empty, ask the maintainer — do not
   invent work.
2. **Claim** the item (`/task-claim <item-ref>`): records ownership in the provider.
3. **In Progress** on your first commit.
4. **Blocked** → mark the item blocked and record the blocker + what would unblock it.
5. **Reference** the item in the PR (`Refs <ID>` or `Closes #<N>`); move it to review/done according
   to provider rules.

## Provider setup

| Provider | Use when | Setup |
|----------|----------|-------|
| Local Markdown | Generic/offline project | [`.agent/backlog/providers/local-markdown.md`](../../.agent/backlog/providers/local-markdown.md) |
| GitHub Issues | GitHub issue tracker is the queue | [`.agent/backlog/providers/github-issues.md`](../../.agent/backlog/providers/github-issues.md) |
| GitHub Projects | Optional board fields/stages are needed | [`.agent/backlog/providers/github-projects.md`](../../.agent/backlog/providers/github-projects.md) |

Provider-specific IDs, labels, `gh project` commands, and stage field option IDs belong in the
provider files, not in this generic workflow.
