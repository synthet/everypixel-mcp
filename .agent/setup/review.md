# Consolidation review — 2026-10-11

The source inventory covers local project assets and installed global standalone
skills and provider/plugin assets. Reviewed material is authored under `.claude/`
and mirrored through the source-of-truth synchronizer. Provider packages retain
their ownership and are not republished under framework names.

Reviewed prose, helper code, metadata and fenced commands for the new library.
Removed personal wiki/repository paths, ancestor-dependent helper imports and
permission-bypass defaults. Archiving retains verified-ingestion and explicitly
authorized cleanup guards. Vision panels require explicit provider export
authorization. No startup updates, credential collection or Git configuration
writes are introduced. All skills remain below 500 lines; optional code and
references stay in their bundles. Deterministic integrity checks and regression
tests cover path containment, ownership, conflicts, backup/rollback, native
adapters, portability and concurrent MCP state preservation.

## Trigger review cases

Each new specialist was reviewed against an affirmative and a near-miss prompt.
These are qualitative routing cases; provider calls are unnecessary to validate
the stated descriptions.

| Skill | Should trigger | Near miss |
|---|---|---|
| agent-setup | Unify my harness skills and install the reviewed plan | Implement an application feature |
| resume-task | Recover yesterday's unfinished Codex work in this project | Resume an already identified active conversation without scanning stores |
| architecture-decisions | Compare two durable storage designs and record the decision | Rename a variable |
| agent-runtime-handoff | Specify tool contracts and evaluations for an app agent | Install a CLI skill |
| archive-session-transcripts | Archive exported session files with verified ingestion | Read a live chat store implicitly |
| codebase-size-audit | Report oversized modules and functions without edits | Refactor everything automatically |
| container-operations | Diagnose Compose health while preserving volumes | Delete all Docker volumes |
| database-backups | Validate a dump and recovery before migration | Drop a database |
| database-migrations | Review a schema rollout and rollback | Read a SELECT query |
| electron-development | Change preload IPC with renderer contract tests | Edit a static HTML page |
| feature-flag-lifecycle | Promote a rollout flag with rollback gates | Add a normal boolean variable |
| gradio-development | Debug Blocks event/session state | Build an unrelated React app |
| hook-loopback-safety | Review authenticated hook callback queues | Add a normal UI click handler |
| judge-panel | Review rendered images with an authorized blind panel | Send private images without approval |
| logging-and-error-reporting | Add redacted failure diagnostics | Print secrets for debugging |
| typescript-monorepo-quality | Change shared schemas across workspaces | Format a standalone text file |
| unity-testing | Run EditMode tests and inspect NUnit artifacts | Execute Python pytest |
| windows-keep-awake | Keep Windows awake for a bounded two-hour job | Change machine power plans permanently |

Jev judgments support reuse/merge/specialist/vendor decisions; low-confidence
answers remain explicitly advisory. The public ledger stores only sanitized
evidence. Machine-specific plans and backups remain ignored local state.

The user-supplied `resume-task.skill` package was inspected in full (instructions,
format notes and the stdlib harvesting script). Jev classified it as distinct
core workflow with 0.99 confidence (`jev-1.13.0`). It was adapted to preserve
current conversation authority, discover additional profiles only explicitly,
redact all serialized report fields, quote suggested shell arguments and reject
output inside harness stores or on input transcripts. Synthetic tests verify
recovery, redaction, profile scope, output guards and command quoting. No actual
private session stores were harvested during installation.

Eleven existing project synchronization scripts were reviewed in full and
recorded by hash in the manifest (eight Claude canonical, three Cursor canonical).
Their native conversion functions run against isolated planning trees. The only
script changes exclude interpreter caches from copying and comparisons; content
checks remain intact. Required generated mirrors and serialization are retained.
One backend rule reserved for Cursor is removed only from the generated Claude
mirror, with an individual backup. Jev's `preserve_native` judgment is recorded
in `sync-decisions.json`; rollback and staging regression tests enforce integrity.
