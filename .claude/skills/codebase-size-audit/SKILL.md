---
name: codebase-size-audit
description: "Use for a read-only large-file and function-size audit, god-module investigation, or refactoring hotspot report."
capability: "Use for a read-only large-file and function-size audit, god-module investigation, or refactoring hotspot report."
side_effect_level: read_only
approval_required: false
requires_tools: "Project-documented tools; see body."
output_schema: "Evidence, changes and verification report."
risk_class: low
---

# codebase size audit

Run the bundled stdlib scanner from the skill directory:
```sh
python scripts/audit.py --root <project-root> --file-lines 1000 --function-lines 150
```
Python function lengths use AST spans; other languages receive file-level counts only. Generated/build/vendor directories and linked directories are excluded. Counts are indicators, not proof that a module needs refactoring.
Inspect ownership, callers, tests, and boundaries for the largest results. Propose a bounded extraction with a preserved public contract and focused verification. Never refactor solely to meet a numeric threshold.
