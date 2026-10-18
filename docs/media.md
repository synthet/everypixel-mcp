---
type: Runbook
title: Media Inputs and Confinement
description: Local file confinement under EVERYPIXEL_MEDIA_ROOTS, Data URI encoding, and multipart upload rules.
resource: media.md
tags: [docs, mcp, media, security]
timestamp: 2026-10-18T00:00:00Z
okf_version: 0.1
---

# Media inputs and confinement

Everypixel Labs v1 endpoints accept media in three distinct formats depending on the endpoint family.
See the [API reference](api.md) for tool-level parameters.

## Transport formats by endpoint family

1. **Synchronous analysis (`everypixel_analyze`) and face swap (`face_swap`):**
   - Remote URLs use `GET` with query parameters (`url=...`, or `source_url=...&target_url=...`).
   - Local files use `POST` `multipart/form-data` (`data=@file`, or `source=@file` + `target=@file`).
2. **Async generative, upscale, TTS clone/save, and transcription:**
   - Accept JSON bodies with either an `https://` URL or a `data:<mime>;base64,...` Data URI.
3. **Lipsync (`everypixel_lipsync`):**
   - `/v1/image_lipsync` and `/v1/video_lipsync` strictly require full `data:<mime>;base64,...` Data URIs for `audio_url` and `image_url`/`video_url`. Plain HTTP(S) URLs are rejected before calling upstream.

## Local file confinement policy

Local file access is disabled by default and requires **two** explicit gates:

1. **Server-configured `EVERYPIXEL_MEDIA_ROOTS`:** absolute directory paths separated by `;` on Windows or `:` on POSIX.
2. **Per-request `allow_local_files=true`:** must be explicitly enabled on the tool call.

Every local path (`file_path`, `image_path`, `image_paths`, `video_path`, `audio_path`, `audio_paths`, `source_path`, `target_path`) is resolved with `Path.resolve(strict=True)` and verified with `Path.is_relative_to(root)` against `EVERYPIXEL_MEDIA_ROOTS`. Symlinks or relative segments escaping the configured roots are rejected with `error.code = "invalid_input"`.

## Local byte and format safeguards

| Media kind | Allowed extensions | Max local file size |
|---|---|---|
| Image | `.jpg`, `.jpeg`, `.png`, `.webp`, `.gif` (`.bmp` on analyze) | 20 MiB (`10 MiB` on `vectorize`) |
| Audio | `.mp3`, `.wav`, `.flac`, `.ogg`, `.m4a`, `.aac`, `.opus`, `.wma`, `.webm` | 50 MiB |
| Video | `.mp4`, `.mov`, `.webm`, `.mpeg`, `.mpg`, `.avi`, `.mkv` | 100 MiB (`50 MiB` when Data URI encoded) |
