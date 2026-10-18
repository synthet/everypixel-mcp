# Everypixel MCP

MCP server exposing the [Everypixel Labs API v1](https://labs.everypixel.com/docs) (media analysis, image/video generation & editing, lip-sync, TTS/voice cloning, speech transcription, and GLM-5.3 chat) to AI agents.

## Quick start

```bash
pip install -e ".[dev]"
cp env.example .env   # set EVERYPIXEL_CLIENT_ID and EVERYPIXEL_CLIENT_SECRET
everypixel-mcp mcp    # stdio MCP server
```

Or via the checkout launcher used by [`.mcp.json`](.mcp.json):

```bash
uv run --project . python scripts/run_everypixel_mcp.py
```

### Tools

| Tool | Purpose |
|------|---------|
| `everypixel_status` | Poll or check async job status (`GET /v1/status`, public, no auth needed) |
| `everypixel_analyze` | Synchronous image/video keywords, captioning, face detection, aesthetic/UGC quality |
| `everypixel_image` | Async image generation, editing, background removal, vectorization, upscaling, face swap |
| `everypixel_video` | Async video generation, editing, upscaling, matting, soundtrack, face swap |
| `everypixel_lipsync` | Async talking-head `image_lipsync` and `video_lipsync` (Data URI inputs) |
| `everypixel_tts` | Async speech synthesis, voice cloning, voice design, and saved voice CRUD |
| `everypixel_transcribe` | Async speech-to-text transcription with word timestamps |
| `everypixel_chat` | Synchronous GLM-5.3 chat completion (`POST /v1/chat/completions`) |

### Resources

- `everypixel://catalog/endpoints` — complete endpoint catalog mapped by MCP tool
- `everypixel://catalog/models` — supported models, resolutions, and language codes

Secrets are loaded from environment variables only (`EVERYPIXEL_CLIENT_ID` + `EVERYPIXEL_CLIENT_SECRET` preferred, or `EVERYPIXEL_ACCESS_TOKEN`). Local file inputs require per-request `allow_local_files=true` and confinement under `EVERYPIXEL_MEDIA_ROOTS`. See [API contracts](docs/api.md) and [media inputs and confinement](docs/media.md).

### Workstation MCP (user-level)

Wire `everypixel-rw-labs` into Claude Code, Claude Desktop, Cursor, Codex, Gemini, and Antigravity,
and install the portable `everypixel-mcp` skill into active sibling projects:

```bash
python scripts/install_everypixel_mcp_workstation.py
```

Requires `uv` on PATH. The installer points `EVERYPIXEL_ENV_FILE` at this checkout's `.env`
and never writes credentials into config files. Reload MCP in each client after running.
Canonical skill: `.claude/skills/everypixel-mcp/` (mirrored to `.cursor/` and `.agents/` via
`python scripts/sync_assistant_trees.py`).

Verify install without spending API quota:

```bash
everypixel-mcp doctor
python -m pytest -q
```

Agent scaffolding lives in `.claude/`, `.cursor/`, `.agents/`, `.codex/`, `.agent/`, and
`.agent-memory/`. Start with [`CLAUDE.md`](CLAUDE.md) and [`AGENTS.md`](AGENTS.md).
