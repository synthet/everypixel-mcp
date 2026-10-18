---
name: feature-flag-lifecycle
description: "Use when adding, promoting, testing, or removing a feature flag or staged rollout."
capability: "Use when adding, promoting, testing, or removing a feature flag or staged rollout."
side_effect_level: local_write
approval_required: false
requires_tools: "Project-documented tools; see body."
output_schema: "Evidence, changes and verification report."
risk_class: medium
---

# feature flag lifecycle

Locate the repository's flag registry, evaluation API, default/cohort configuration, rollout controls and existing tests. Do not introduce a second flag system.
Define owner, purpose, safe default, cohorts, expiry/removal condition and rollback. Gate the behavior at a stable boundary, with tests for enabled and disabled paths and relevant permission/error behavior.
Promotion is an operational change: verify task authority, target environment, health criteria and rollback before changing audience. Observe errors and usability, not exposure counts alone.
After stabilization, remove the old path, flag entries, docs and tests that only exercise the obsolete path. Preserve tests for the intended final behavior.
