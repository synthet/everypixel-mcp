---
name: unity-testing
description: "Use when running or diagnosing Unity EditMode/PlayMode tests, batch validation, compile failures or NUnit result artifacts."
capability: "Use when running or diagnosing Unity EditMode/PlayMode tests, batch validation, compile failures or NUnit result artifacts."
side_effect_level: local_write
approval_required: false
requires_tools: "Project-documented tools; see body."
output_schema: "Evidence, changes and verification report."
risk_class: medium
---

# unity testing

Read ProjectSettings/ProjectVersion.txt, the project test runner and AGENTS test vocabulary. Use the matching installed Editor and documented runner.
Keep validation, EditMode and PlayMode distinct. Run a narrow test filter first; preserve logs and NUnit XML, inspect result counts, and fail on missing/stale result files or failures.
Resolve editor locking, assembly definitions and missing Editor paths before inventing alternate runners. On Windows, inspect the project's Unity version-specific handling of -runTests/-quit rather than assuming generic flags.
Use official Unity test execution for managed game assemblies; avoid PowerShell reflection one-liners loading Editor/Temp DLLs. Report Editor absence or unavailable platform coverage plainly.
