---
name: windows-keep-awake
description: "Use only when the user asks to keep a Windows session awake during a bounded job or prevent sleep temporarily."
capability: "Use only when the user asks to keep a Windows session awake during a bounded job or prevent sleep temporarily."
side_effect_level: local_write
approval_required: false
requires_tools: "Project-documented tools; see body."
output_schema: "Evidence, changes and verification report."
risk_class: medium
---

# windows keep awake

Run the bounded helper from this skill directory:
```powershell
pwsh -NoProfile -File scripts/keep-awake.ps1 -Minutes 30
```
The helper changes the current thread's execution state, keeps that process alive, and restores it in finally. It does not alter system power plans or persist across reboot.
Use a duration appropriate to the authorized work. Stop with Ctrl+C; report the process and planned expiration. Do not launch an indefinite background keep-awake job implicitly.
