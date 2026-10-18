---
name: electron-development
description: "Use when changing an Electron main/preload/renderer contract, IPC handler, desktop database flow, or Electron test/build workflow."
capability: "Use when changing an Electron main/preload/renderer contract, IPC handler, desktop database flow, or Electron test/build workflow."
side_effect_level: local_write
approval_required: false
requires_tools: "Project-documented tools; see body."
output_schema: "Evidence, changes and verification report."
risk_class: medium
---

# electron development

Read the current main, preload, renderer type declarations and package scripts. Preserve process boundaries: privileged filesystem/database work belongs in the main process.
Expose a narrow typed contextBridge API. Validate IPC payloads and sender/frame context; avoid unrestricted invoke/execute/file APIs. Keep node integration and context isolation at the project's secure settings.
Change handler, preload API, shared types and consumer together. Return a typed failure rather than swallowing errors into an empty list. Test invalid input, denied operation and the successful path.
Verify documented unit/type/build checks and the actual affected desktop flow when available. Account for Windows/WSL/URI path conversions without assuming a sibling project exists.
