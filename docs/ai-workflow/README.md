---
type: Documentation Hub
title: AI Workflow & Asset Map
description: Where every agent asset lives (rules, commands, skills, agents, memory, workflows) and the SDLC loop they support.
resource: ai-workflow/README.md
tags: [docs, agents, workflow]
timestamp: 2026-07-03T00:00:00Z
okf_version: 0.1
---

# AI workflow & asset map

## Where agent assets live

| Asset | Location | Notes |
|-------|----------|-------|
| Claude commands | `.claude/commands/*.md` | **Canonical** authoring source |
| Claude skills | `.claude/skills/*/SKILL.md` | **Canonical** authoring source |
| Claude subagents | `.claude/agents/*.md` | **Canonical** authoring source |
| Claude rules | `.claude/rules/*.md` | Always-on guidance |
| Cursor mirror | `.cursor/{rules,commands,skills,agents}` | **Generated** from `.claude/` — do not edit by hand |
| Codex skills | `.agents/skills/*/SKILL.md` | **Generated** from `.claude/skills/` — do not edit by hand |
| Codex subagents | `.codex/agents/*.toml` | **Generated** from `.claude/agents/` — do not edit by hand |
| Codex config | `.codex/config.toml` | Project-scoped defaults and portable MCP endpoints |
| MCP template | `.cursor/mcp.example.json`, `.mcp.json` | Copy to gitignored `.cursor/mcp.json` to attach servers |
| Agent governance | `.agent/` | Safety, inventory, subagent role matrix, workflow playbooks |
| Project memory | `.agent-memory/` | log → dream → promote (see `CURSOR_USAGE.md`) |
| Workflow playbooks | `.agent/workflows/*.md` | spec / plan / tasks / implement / pr-ready / test-and-fix / … |

**Single source of truth:** edit assets under `.claude/` + `.agent/`, then run
`python scripts/sync_assistant_trees.py` to regenerate the Cursor and Codex mirrors.

## CLI tooling skills

Thirteen skills under `.claude/skills/` cover agent-safe CLI usage (see [`.agent/cli-tools-skills-spec.md`](../../.agent/cli-tools-skills-spec.md)):

| Skill | Role |
|-------|------|
| `cli-tools-overview` | Router + shared references (install-tiers, agent-environment) |
| `search-tool-selection` | **Start here for search** — fd → rg → ast-grep |
| `safe-command-patterns` | Bounded output, git hygiene |
| `search-and-navigation` | rg, fd, bat, tree |
| `structural-code-search` | ast-grep, semgrep |
| `git-and-diff-workflows` | git, gh |
| `data-config-tools` | jq, yq, curl |
| `task-env-package-tools` | Task runners, framework quality gates |
| `lint-format-security` | ruff, eslint, clippy, trivy |
| `mcp-code-intelligence` | MCP tiers (incl. optional fff) |
| `install-checklist` | Human workstation provisioning |
| `windows-agent-tooling` / `wsl2-agent-tooling` | Platform split |

Validate after changes: `python scripts/validate_cli_skills.py`.

**Install tiers:** Human provisioning order (Tier 0 → Block A → Block B → deferred) and operator scopes live in `cli-tools-overview/references/install-tiers.md`. After installs, restart Cursor and smoke-test PATH per `agent-environment.md`.

**Downstream pattern:** Cursor-first forks (e.g. image-scoring-gallery) may consolidate into `agent-cli-hub` + topic skills; cherry-pick individual flat skills from this framework as needed.

## Optional MCP (fff)

[fff](https://github.com/dmtrKovalenko/fff) optional file-search MCP (`ffgrep`, `fffind`, `fff-multi-grep`). Opt-in template in `.cursor/mcp.example.json` → copy to gitignored `.cursor/mcp.json`. See [`AGENTS.md`](../../AGENTS.md).

## The SDLC loop

```
/spec  →  /clarify  →  /plan  →  /tasks  →  /analyze  →  /implement  →  /test-and-fix  →  /pr-ready  →  (optional) /subagent-review  →  /release-notes
```

### Phase gates

Each phase produces an artifact that gates the next one. Do not skip a gate silently — if a phase
is unnecessary (trivial fix), say so explicitly. The `/spec` → `/plan` → `/tasks` split follows Spec Kit-style spec-driven development: define product outcomes first, choose implementation strategy second, and only then create executable task slices.

| Phase | Artifact produced | Gate to pass before the next phase |
|-------|-------------------|-------------------------------------|
| `/spec` | Spec with EARS `AC-n` acceptance criteria | User approves; no criterion is AMBIGUOUS |
| `/clarify` | Prioritized decisions plus spec patch notes | Material ambiguity is answered, defaulted, or carried as an explicit risk |
| `/plan` | Implementation plan (files, approach, tests, rollback) | User approves the plan; skipped `/tasks` gate is justified only for trivial/single-step work |
| `/tasks` | Traceable `T-n` task list mapped to `AC-n` criteria and verification commands | Every acceptance criterion has task coverage and evidence path |
| `/analyze` | Cross-artifact coverage and consistency report | No blockers across spec, plan, tasks, governance, or verification paths |
| `/implement` | Minimal-diff change set with tests | Lint + narrowest tests green |
| `/test-and-fix` | Green test run (or written blocker); RCA log entry for non-obvious failures; optional JSONL trace artifact | Tests pass or blocker documented |
| `validate-implementation` (skill) | Per-AC Verified/Failed/Unknown report with evidence | Every AC Verified, or open items accepted by the user |
| `/pr-ready` | Definition-of-done report + paste-ready PR text; optional JSONL trace evidence | Checks green, provider-specific backlog reference present, review-ready status set only when the provider tracks status |

- **Backlog first:** pick and claim work via the [backlog contract](../project/00-backlog-workflow.md) (`/task-claim`); default to Local Markdown or GitHub Issues unless project docs explicitly opt into GitHub Projects.
- **Review:** `/critical-commit-audit` for high-severity bug hunts; `/check-subagents` +
  `/run-codex-review` / `/run-gemini-review` for external second opinions. Sanitized JSONL trace artifacts can be linked as optional validation evidence; see [`../agent-observability.md`](../agent-observability.md).
- **Docs:** `/wiki-ingest`, `/wiki-lint`, `/wiki-query` keep `docs/` healthy (see [WIKI_SCHEMA](../WIKI_SCHEMA.md)).
- **Memory:** `/log-session` → `/dream-memory` → `/promote-memory` → `/memory-context`.
- **Asset growth:** `/mine` turns an external document, repo, or transcript into agent assets;
  `lesson-to-skill` does the same for the current conversation; `/compile-skill` lowers a stable
  skill into a harness. All three propose before writing.

## Safety

All of the above operate under [`.agent/SAFETY.md`](../../.agent/SAFETY.md) and
[`security.md`](../security.md).
