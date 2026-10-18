# MCP tool reference — subagent-orchestrator

Server display name: **subagent-orchestrator**

Project MCP key: **`cli-review`**. User-level: **`subagent-orchestrator`**.

## detect_subagents

No parameters.

**Example response (shape):**

```json
{
  "agents": {
    "codex": {
      "available": true,
      "command": "codex",
      "mode": "exec",
      "version": "…",
      "notes": []
    },
    "gemini": {
      "available": true,
      "command": "gemini",
      "mode": "prompt",
      "version": "…",
      "notes": []
    },
    "claude": {
      "available": true,
      "command": "claude",
      "mode": "print",
      "version": "…",
      "notes": []
    }
  },
  "detectedAt": "2026-05-27T…"
}
```

## run_subagent

| Field | Type | Required | Default | Notes |
|-------|------|----------|---------|-------|
| `agent` | `"codex"` \| `"gemini"` \| `"claude"` | yes | — | Prefer codex/gemini for live runs |
| `task` | string | yes | — | Max 8000 chars |
| `files` | string[] | no | — | Workspace-relative; max 20 |
| `mode` | `review` \| `implement` \| `explain` \| `test` \| `tie-breaker` | no | `review` | |
| `timeoutMs` | number | no | 300000 | Max 900000 |
| `allowWrites` | boolean | no | `false` | **Rejected in v0.1** |
| `dryRun` | boolean | no | `false` | Command preview only |
| `extraContext` | string | no | — | Max 4000 chars |

**Example — dry run:**

```json
{
  "agent": "codex",
  "task": "Review the changed public API handler for contract drift",
  "files": ["src/api/handler.ts"],
  "mode": "review",
  "allowWrites": false,
  "dryRun": true
}
```

**Example — live review:**

```json
{
  "agent": "gemini",
  "task": "Review the data-access layer for injection and least-privilege",
  "files": ["src/db/queries.ts"],
  "mode": "review",
  "allowWrites": false
}
```

**Example response (shape):**

```json
{
  "ok": true,
  "agent": "codex",
  "exitCode": 0,
  "durationMs": 18422,
  "outputFile": ".agent-runs/20260526-203012-codex-review-api/stdout.md",
  "outputDir": ".agent-runs/20260526-203012-codex-review-api",
  "summary": "…",
  "commandPreview": "codex exec --sandbox read-only …"
}
```

## On-disk artifacts

```text
.agent-runs/YYYYMMDD-HHMMSS-<agent>-<slug>/
  request.json
  stdout.md
  stderr.log
  result.json
```

Written under the **active workspace**, not under `subagent-orchestrator`.
