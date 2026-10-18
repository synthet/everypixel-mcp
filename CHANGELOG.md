# Changelog — Everypixel MCP

All notable changes to this project are documented here. Format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/); versions follow
[Semantic Versioning](https://semver.org/).

## [Unreleased]

### Added

- Project seeded from `synthet-code-framework`.
- Implemented `everypixel-mcp` (`0.1.0`) exposing all 22 Everypixel Labs v1 endpoints via 8 domain tools (`everypixel_status`, `everypixel_analyze`, `everypixel_image`, `everypixel_video`, `everypixel_lipsync`, `everypixel_tts`, `everypixel_transcribe`, `everypixel_chat`) and 2 static catalog resources (`everypixel://catalog/endpoints`, `everypixel://catalog/models`).
- Added `EVERYPIXEL_MEDIA_ROOTS` + `allow_local_files=True` local path confinement, automatic Data URI encoding for lip-sync, and `confirmed=True` guard on destructive voice deletion.
- Added `everypixel-mcp doctor` CLI diagnostics, `scripts/run_everypixel_mcp.py`, `scripts/install_everypixel_mcp_workstation.py`, and `.claude/skills/everypixel-mcp/SKILL.md`.
