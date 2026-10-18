---
name: everypixel-mcp
description: Use when analyzing images/videos (keywords, captions, faces, aesthetic/UGC quality), generating or editing images/videos, running lip-sync, synthesizing/cloning/designing TTS voices, transcribing audio, or calling GLM-5.3 chat via the Everypixel Labs API (everypixel_status, everypixel_analyze, everypixel_image, everypixel_video, everypixel_lipsync, everypixel_tts, everypixel_transcribe, everypixel_chat).
capability: "Everypixel Labs v1 media analysis, generation, TTS, transcription, and chat via everypixel-mcp"
side_effect_level: external_export
approval_required: true
requires_tools: "MCP server everypixel-rw-labs; optional everypixel-mcp CLI"
output_schema: "Normalized ToolEnvelope with ok, result, or structured error details"
risk_class: high
---

# Everypixel MCP (Everypixel Labs v1)

Prefer tools from **everypixel-rw-labs** when connected. Calls export media URLs, local media, or
prompts to the paid Everypixel Labs API (`https://api.everypixel.com/v1`). Keep credentials in
environment variables (`EVERYPIXEL_CLIENT_ID` + `EVERYPIXEL_CLIENT_SECRET` or
`EVERYPIXEL_ACCESS_TOKEN`) and never pass `EVERYPIXEL_CLIENT_SECRET` as a Bearer token.

| Tool | Use |
|---|---|
| everypixel_status | Poll or check async job status (`GET /v1/status`, no auth needed) |
| everypixel_analyze | Synchronous keywords, video keywords, captioning, face detection, aesthetic/UGC quality |
| everypixel_image | Async image generation, editing, background removal, vectorization, upscaling, face swap |
| everypixel_video | Async video generation, editing, upscaling, matting, soundtrack, face swap |
| everypixel_lipsync | Async talking-head `image_lipsync` and `video_lipsync` (Data URI inputs required) |
| everypixel_tts | Async speech synthesis, voice cloning, voice design, and saved voice CRUD |
| everypixel_transcribe | Async audio speech-to-text transcription with timestamps |
| everypixel_chat | Synchronous GLM-5.3 chat completion (`POST /v1/chat/completions`) |

Read `everypixel://catalog/endpoints` and `everypixel://catalog/models` for complete model lists,
resolutions, and language codes without making an API request.

## Call workflow

1. Check whether the operation is synchronous (`everypixel_analyze`, `everypixel_chat`, TTS `save_voice` / `list_voices` / `delete_voice`) or asynchronous (`everypixel_image`, `everypixel_video`, `everypixel_lipsync`, `everypixel_transcribe`, TTS `create` / `clone` / `design`).
2. For fast async jobs (image background removal, vectorization, upscale, short TTS), pass `wait=true` (`wait_timeout_seconds` up to `180`). For multi-minute video or lip-sync jobs, leave `wait=false`, record the returned `task_id`, and poll with `everypixel_status`.
3. Inspect the returned `ToolEnvelope` (`ok: true` with `result`, or `ok: false` with `error.code`, `error.retryable`, and `error.next_steps`).
4. Deleting a saved voice via `everypixel_tts(operation="delete_voice")` is permanent and requires explicit user confirmation plus `confirmed=true`.

## Local media and Data URI rules

- Local file paths (`file_path`, `image_path`, `video_path`, `audio_path`, `source_path`, `target_path`) are disabled by default.
- To send a local file, configure `EVERYPIXEL_MEDIA_ROOTS` on the server and pass `allow_local_files=true` on the tool call. Paths outside `EVERYPIXEL_MEDIA_ROOTS` are rejected.
- `everypixel_lipsync` (`image_lipsync` and `video_lipsync`) requires full `data:<mime>;base64,...` Data URIs for `audio_url` and `image_url`/`video_url`. Passing `audio_path` and `image_path`/`video_path` with `allow_local_files=true` automatically encodes local files as Data URIs.
- Face swap (`operation="face_swap"` on `everypixel_image` and `everypixel_video`) uses `GET` with `source_url` + `target_url` for remote URLs, or multipart `POST` with `source_path` + `target_path` for local files.

For server diagnostics run `everypixel-mcp doctor --json` (offline) or `everypixel-mcp doctor --live` (makes one read-only `/v1/tts_voices?limit=1` request).
