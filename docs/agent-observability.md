---
type: Guide
title: Agent Observability
description: JSONL event logging for agent workflows and optional validation evidence.
resource: agent-observability.md
tags: [docs, agents, observability, jsonl, validation]
timestamp: 2026-07-07T00:00:00Z
okf_version: 0.1
---

# Agent observability

Agent workflows can emit newline-delimited JSON (JSONL) trace artifacts to make execution auditable
without requiring a full telemetry stack. A trace artifact is optional validation evidence for
workflows such as `/test-and-fix`, `/pr-ready`, and external CLI reviews: it records what the agent
attempted, which policy checks ran, whether validation passed, and whether sensitive export was
blocked.

## Artifact format

- Store one complete JSON object per line (`.jsonl`), with no surrounding array.
- Keep events append-only within a trace; do not rewrite earlier decisions except to add a later
  corrective event.
- Use UTC timestamps in RFC 3339 format.
- Treat trace artifacts as potentially sensitive. Redact secrets and avoid logging full prompts,
  full command output, or proprietary payloads unless the repository policy explicitly permits it.
- Prefer paths under `.agent-runs/` for ephemeral local runs. Commit only sanitized examples, such
  as [`docs/examples/agent-workflow-trace.jsonl`](examples/agent-workflow-trace.jsonl).

## Event fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `trace_id` | string | Yes | Stable identifier shared by all events for one workflow run. Use a UUID, ULID, or similarly unique value. |
| `timestamp` | string | Yes | UTC RFC 3339 timestamp for when the event occurred. |
| `phase` | string | Yes | Workflow phase that emitted the event, such as `spec`, `plan`, `implement`, `test-and-fix`, `external-review`, or `pr-ready`. |
| `asset` | string or object | Yes | The workflow asset, command, skill, subagent, file, or artifact being acted on. Use an object when both `type` and `path` are useful. |
| `decision` | string or object | Yes | Decision made at this event. Keep the top-level value concise; use an object for `outcome`, `reason`, and `next_step` when useful. |
| `tool_calls` | array | No | Tool invocations performed or summarized for the event. Include tool name, purpose, and sanitized status; omit secrets and large outputs. |
| `policy_checks` | array | No | Safety or governance checks evaluated, for example `no-secrets`, `allowWrites=false`, `AGENTS.md`, or `sensitive-export`. |
| `validation_status` | string | No | Validation result for the event: `not_run`, `passed`, `failed`, `blocked`, or `not_applicable`. |
| `sensitive_export_blocked` | boolean | Yes | Whether a proposed export of sensitive content was blocked at this point in the workflow. Use `false` when no export was attempted. |

## Recommended conventions

### `tool_calls`

Use compact records that identify the tool and result without leaking full payloads:

```json
[{"name":"pytest","purpose":"run focused tests","status":"passed","summary":"3 tests passed"}]
```

For MCP or external-review tools, include the review mode and whether writes were disabled:

```json
[{"name":"subagent-orchestrator.run_subagent","purpose":"codex review","status":"passed","mode":"review-only","allowWrites":false}]
```

### `policy_checks`

Represent policy checks as strings for simple traces or objects for richer audit trails:

```json
[
  {"name":"no-secrets","status":"passed"},
  {"name":"sensitive-export","status":"passed","details":"export contained only sanitized diff summary"}
]
```

### `asset`

Use the smallest useful reference. Examples:

```json
{"type":"command","path":".claude/commands/pr-ready.md"}
```

```json
{"type":"artifact","path":".agent-runs/2026-07-07T120000Z/trace.jsonl"}
```

## Using traces as validation evidence

Trace artifacts do not replace tests, review, or acceptance-criteria validation. They are optional
supporting evidence that helps maintainers answer:

- Which workflow phase made a decision?
- Which tools were run, and what was their sanitized status?
- Which policy checks were considered before exporting or reviewing content?
- Was a sensitive export attempted and blocked?
- Which validation state (`passed`, `failed`, `blocked`, `not_run`, or `not_applicable`) was known
  at each point?

When including a trace in a PR-ready report or review summary, link to the sanitized artifact path
and summarize the relevant events instead of pasting long JSONL output.
