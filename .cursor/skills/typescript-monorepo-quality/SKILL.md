---
name: typescript-monorepo-quality
description: "Use when changing TypeScript workspace packages, shared schemas, dependency direction, or monorepo build and test configuration."
capability: "Use when changing TypeScript workspace packages, shared schemas, dependency direction, or monorepo build and test configuration."
side_effect_level: local_write
approval_required: false
requires_tools: "Project-documented tools; see body."
output_schema: "Evidence, changes and verification report."
risk_class: medium
---

# typescript monorepo quality

Inspect packageManager, the lockfile, workspace definition, root scripts and shared tsconfig. Use the declared package manager and existing runner.
Define shared protocol types and runtime validation at the owning boundary before changing consumers. Keep dependencies directed and avoid cycles or imports into another package's internal files.
Preserve strict typing and explicit error contracts. Check affected package builds, typechecks and parser/transport tests first, then documented workspace gates when shared behavior changes.
Do not invent package names, replace lockfiles, or run global dependency installation. Report actual checks and deployment/version compatibility implications.
