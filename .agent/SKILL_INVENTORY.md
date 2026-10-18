# Skill inventory — Everypixel MCP

**Last reviewed:** 2026-10-11. Companion to [SKILL_CHANGE_AST10_REVIEW.md](SKILL_CHANGE_AST10_REVIEW.md)
and [SKILL_COMPILATION.md](SKILL_COMPILATION.md).
Update this file (new row or **Last reviewed** date) in the same PR as any skill change.

Risk tiers: **L1** = advisory/read-mostly (writes limited to docs/reports); **L2** = can run
commands or edit code/config as part of its procedure.

## Skills (`.claude/skills/`)

### SDLC and governance

| Skill | Purpose | Risk | Last reviewed |
|-------|---------|------|---------------|
| agent-memory | Log sessions, dream consolidation, promote memory, load context (bootloader over `scripts/agent-memory/`) | L2 | 2026-07-19 |
| autonomous-run-contract | Metric, budget, revert rule, and stop conditions before an unattended or fanned-out run | L1 | 2026-07-25 |
| backlog-queue | Provider-oriented backlog queue; local markdown, GitHub Issues, optional GitHub Projects | L2 | 2026-07-01 |
| commit-conventions | Conventional Commits and PR title wording | L1 | 2026-07-01 |
| commit-and-push | Stage, commit, and push with git safety rules; pairs with release-bump (**compiled harness**) | L2 | 2026-07-19 |
| critical-commit-audit | Deep post-commit hunt for high-severity bugs | L2 | 2026-07-01 |
| eval | Capture task quality signals to agent memory (**compiled harness**) | L2 | 2026-07-21 |
| export-chat | Export the Cursor agent transcript to Markdown or the clipboard, like Claude Code `/export` | L2 | 2026-10-01 |
| karpathy-guidelines | Deliberate coding checklist: assumptions, simplicity, surgical diffs, verifiable goals | L2 | 2026-07-14 |
| lesson-to-skill | Turn session corrections, mistakes, and repetitions into enriched or new agent assets | L2 | 2026-07-25 |
| mcp-server-design | Design MCP servers with safe transport, discoverable tools, pagination, and validation | L1 | 2026-07-14 |
| release-bump | Semver bump, changelog promotion, release commit prep (**compiled harness**) | L2 | 2026-07-19 |
| security-review | Lightweight pre-merge security sanity check | L1 | 2026-07-01 |
| skill-authoring | Create and improve first-party skills with progressive disclosure and eval guidance | L2 | 2026-07-14 |
| subagent-review | Review-only external CLI orchestration via MCP | L1 | 2026-07-01 |
| systematic-debugging | Evidence-first root-cause debugging with reproduce/minimise/hypothesis/regression loop | L2 | 2026-07-14 |
| test-driven-development | Red-green-refactor workflow for behavior changes with practical test seams | L2 | 2026-07-14 |
| rust-testing | Cargo/nextest unit tests beside modules | L2 | 2026-08-14 |
| threat-modeling-agentic-tools | Threat-model MCP/tool abuse and injection | L1 | 2026-07-01 |
| validate-implementation | Per-AC Verified/Failed/Unknown verdicts with evidence (**compiled harness**) | L2 | 2026-07-19 |
| verification-before-completion | Evidence-backed completion claims with fresh command proof (**compiled harness**) | L1 | 2026-07-19 |

### CLI tooling ([cli-tools-skills-spec.md](cli-tools-skills-spec.md))

| Skill | Purpose | Risk | Last reviewed |
|-------|---------|------|---------------|
| search-tool-selection | Choose fd vs rg vs ast-grep vs fff MCP vs Graphify vs IDE search (**compiled harness**) | L1 | 2026-07-21 |
| safe-command-patterns | Bounded output, inspect-before-edit, confirmation gates | L1 | 2026-07-03 |
| search-and-navigation | rg, fd, bat, tree, navigation | L1 | 2026-07-03 |
| git-and-diff-workflows | git, gh, bounded diffs | L1 | 2026-07-03 |
| cli-tools-overview | Router for CLI skills + shared references (install-tiers, agent-environment) | L1 | 2026-07-04 |
| task-env-package-tools | Task runners, sync/frontmatter/pytest gates (**compiled harness**) | L1 | 2026-07-21 |
| structural-code-search | ast-grep, semgrep, ctags | L1 | 2026-07-03 |
| data-config-tools | jq, yq, curl, sqlite | L1 | 2026-07-03 |
| install-checklist | Human workstation provisioning (not agent-automated) | L2 | 2026-07-03 |
| lint-format-security | ruff, eslint, clippy, trivy, shellcheck (**compiled harness**) | L2 | 2026-08-14 |
| mcp-code-intelligence | MCP tiers; fff, Graphify, Serena, Zoekt, embeddings | L2 | 2026-07-21 |
| graphify-knowledge-graph | Query/refresh Graphify MCP or CLI for architecture paths and communities | L2 | 2026-07-21 |
| windows-agent-tooling | Native Windows agent workflows | L2 | 2026-07-03 |
| wsl2-agent-tooling | WSL2 build/test/MCP workflows | L2 | 2026-07-03 |

### Consolidated reusable setup library

Routing and native discovery: [agent setup](../docs/agent-setup.md).
Jev evidence and reviewed choices: [decision ledger](setup/decisions.json).

| Skill | Purpose | Risk | Last reviewed |
|-------|---------|------|---------------|
| agent-setup | Inventory, review, install, check and roll back native harness setup | L2 | 2026-10-11 |
| resume-task | Recover unfinished local cross-harness work with evidence and a continuation brief | L2 | 2026-10-11 |
| architecture-decisions | Compare consequential alternatives and record ADRs | L1 | 2026-10-11 |
| agent-runtime-handoff | Application agent-runtime contracts and handoff | L2 | 2026-10-11 |
| archive-session-transcripts | Hash-verified, privacy-reviewed transcript archiving | L2 | 2026-10-11 |
| codebase-size-audit | Read-only file and Python AST size report | L1 | 2026-10-11 |
| container-operations | Volume-aware Docker/Compose diagnostics | L2 | 2026-10-11 |
| database-backups | Verified backups and recovery evidence | L2 | 2026-10-11 |
| database-migrations | Schema rollout and rollback contracts | L2 | 2026-10-11 |
| electron-development | Main/preload/renderer and desktop testing contracts | L2 | 2026-10-11 |
| feature-flag-lifecycle | Flag promotion, rollback and removal | L2 | 2026-10-11 |
| gradio-development | Blocks/session/event graphs and diagnostics | L2 | 2026-10-11 |
| hook-loopback-safety | Authenticated local hook queues and event handling | L2 | 2026-10-11 |
| judge-panel | Authorized external vision review and Jev adjudication | L2 | 2026-10-11 |
| logging-and-error-reporting | Bounded, redacted observability and failures | L2 | 2026-10-11 |
| typescript-monorepo-quality | Workspace boundaries, shared schemas and checks | L2 | 2026-10-11 |
| unity-testing | Unity compile/EditMode/PlayMode validation | L2 | 2026-10-11 |
| windows-keep-awake | Explicit bounded Windows sleep prevention | L2 | 2026-10-11 |
| jev-mcp | Typed semantic Choice/Score/Noul decisions over sanitized state | L2 | 2026-10-11 |
| llm-wiki | Explicit-root local wiki query, ingestion and validation | L2 | 2026-10-11 |

Git/fork/PR guidance, environment/dependency guidance and MCP diagnostics were
merged into their existing skills. Existing inventory entries and project-native
specializations remain authoritative. Review notes and trigger cases are in
[setup/review.md](setup/review.md).

## Subagents (`.claude/agents/`)

| Agent | Purpose | Risk | Last reviewed |
|-------|---------|------|---------------|
| critical-commit-audit | High-severity post-commit bug hunt with minimal fixes | L2 | 2026-07-01 |
| external-cli-reviewer | Coordinate review-only Codex + Gemini panel | L1 | 2026-07-01 |
| external-codex-review | Codex-only external review | L1 | 2026-07-01 |
| external-gemini-review | Gemini-only external review | L1 | 2026-07-01 |
| pr-ready-hygiene | Definition-of-done checks and paste-ready PR text | L2 | 2026-07-01 |

Commands (`.claude/commands/`) and rules (`.claude/rules/`) are catalogued in
[AGENT_INFRA_INVENTORY.md](AGENT_INFRA_INVENTORY.md); they follow the same review process.

## Frontmatter invariants (CI-enforced)

`scripts/ci/check_agent_frontmatter.py` enforces these on every PR:

- **Skills:** YAML frontmatter required; `name` is the **first** key and matches the directory
  name; `description` is non-empty; skill names are unique across the tree.
- **Agents:** frontmatter required; `name` matches the file stem; `description` non-empty; names unique.
- **Commands:** YAML frontmatter required and H1 heading of the form `# /<file-stem> …`.
- **Rules:** frontmatter required with non-empty `description`.
- **Commands, skills, and agents:** frontmatter must include the metadata contract fields below
  wherever the field applies to the asset:
  - `capability` — short user-facing statement of what the asset enables.
  - `side_effect_level` — one of `read_only`, `local_write`, `remote_write`,
    `external_export`. Use `external_export` when repository context or task data leaves the
    local workspace, and `remote_write` for GitHub PR/issue/project mutations.
  - `approval_required` — boolean `true` or `false`. Use `true` for high-risk external export
    assets and remote mutations that require explicit human approval.
  - `requires_tools` — compact scalar summary of required CLIs, MCP tools, or platform APIs.
  - `output_schema` — compact scalar summary of the expected response/report shape.
  - `risk_class` — one of `low`, `medium`, `high`.
- **High-risk external review assets:** `risk_class: high` external Codex/Gemini/subagent review
  assets must also set `side_effect_level: external_export` and `approval_required: true`.
- **PR/issue/project mutation commands:** commands that mutate GitHub PRs, issues, or Project
  boards must set `side_effect_level: remote_write`.
- **Model pins:** if a command/skill/agent frontmatter sets `model`, the value must be a bare tier
  alias (`opus`, `sonnet`, `haiku`, `fable`) — never a pinned version ID or a `[1m]`-suffixed ID.
  Aliases resolve at dispatch so one definition follows the asset across model generations and
  providers; a pinned ID silently keeps pointing at its generation after a switch, and a suffixed ID
  cannot be inherited by subagents. Only enforced when a `model` key is present.
- **All files:** plain scalar frontmatter keys only — no exotic YAML tags (`!!`).

Use `python scripts/migrate_agent_frontmatter.py` to populate missing command, skill, and agent
metadata defaults before hand-tuning values. Use `--check` in CI or review workflows to report
assets that still need migration without rewriting files.

Violations fail CI; fix the asset rather than the checker. If the contract itself must change,
update the checker, this file, and [SKILL_CHANGE_AST10_REVIEW.md](SKILL_CHANGE_AST10_REVIEW.md)
in the same PR.

CLI skill structure is additionally checked by `scripts/validate_cli_skills.py`.
