---
type: Technical Reference
title: Everypixel MCP API
description: Public MCP tool parameters, catalog resources, authentication modes, and async polling contracts.
resource: api.md
tags: [docs, api, mcp]
timestamp: 2026-10-18T00:00:00Z
okf_version: 0.1
---

# Everypixel MCP API

All eight MCP tools return a normalized `{ok: true, result: ...}` envelope or a sanitized
`{ok: false, error: {code, message, details, retryable, next_steps}}` envelope.

| Tool | Operations / Scope | Sync / Async |
|---|---|---|
| `everypixel_status` | Poll `GET /v1/status?task_id=...` (public, no auth required) | Sync or bounded poll (`wait=true`) |
| `everypixel_analyze` | `keywords`, `video_keywords`, `caption`, `faces`, `quality`, `quality_ugc` | Synchronous |
| `everypixel_image` | `generate`, `edit`, `remove_background`, `vectorize`, `upscale`, `face_swap` | Async (`task_id` or `wait=true`) |
| `everypixel_video` | `generate`, `edit`, `upscale`, `matting`, `soundtrack`, `face_swap` | Async (`task_id` or `wait=true`) |
| `everypixel_lipsync` | `image_lipsync`, `video_lipsync` (requires Data URI inputs) | Async (`task_id` or `wait=true`) |
| `everypixel_tts` | `create`, `clone`, `design`, `save_voice`, `list_voices`, `delete_voice` | Async (`create`/`clone`/`design`), Sync (`save_voice`/`list_voices`/`delete_voice`) |
| `everypixel_transcribe` | Speech-to-text transcription (`/v1/transcribe`) | Async (`task_id` or `wait=true`) |
| `everypixel_chat` | GLM-5.3 chat completion (`POST /v1/chat/completions`, `stream=false`) | Synchronous |

## Static Catalog Resources

- `everypixel://catalog/endpoints` — complete mapping of MCP tools to all 22 Everypixel Labs v1 HTTP endpoints.
- `everypixel://catalog/models` — supported model identifiers, resolutions, aspect ratios, and language codes.

## Authentication

- **HTTP Basic (preferred):** set `EVERYPIXEL_CLIENT_ID` and `EVERYPIXEL_CLIENT_SECRET`.
- **OAuth Bearer:** set `EVERYPIXEL_ACCESS_TOKEN`. Never pass `EVERYPIXEL_CLIENT_SECRET` as `EVERYPIXEL_ACCESS_TOKEN`.
- **Public status endpoint:** `everypixel_status` calls `GET /v1/status` without authentication headers.

## Bounded Polling (`wait=true`)

Asynchronous tools return `{status, task_id, ...}` immediately by default (`wait=false`).
When `wait=true` is passed:
- `wait_timeout_seconds` is bounded to `[1.0, 180.0]` seconds (default `60.0`).
- `poll_interval_seconds` is bounded to `[0.5, 30.0]` seconds (default `2.0`).
- If a task is still `PENDING` or `RUNNING` when `wait_timeout_seconds` expires, the tool returns `error.code = "wait_timeout"` (`retryable = true`) with the `task_id` in `error.details` so the caller can resume polling via `everypixel_status`.

See [media inputs and confinement](media.md) for local file rules and Data URI encoding.
Upstream reference: [Everypixel Labs API documentation](https://labs.everypixel.com/docs).
