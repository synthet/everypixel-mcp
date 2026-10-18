# Codex project setup

Codex uses the repository's root `AGENTS.md` for durable instructions and discovers reusable
workflows under `.agents/skills/`. Custom subagents live under `.codex/agents/`. Both trees are
generated from the canonical `.claude/` assets by `scripts/sync_assistant_trees.py`.

## First use

1. Open the repository in Codex and trust it so project-scoped `.codex/config.toml` is loaded.
2. Confirm `AGENTS.md` appears in the project instructions and repository skills are available.
3. Keep credentials, provider configuration, and machine-specific MCP commands in
   `~/.codex/config.toml`. Do not commit them here.
4. After changing `.claude/skills/` or `.claude/agents/`, run:

   ```bash
   python scripts/sync_assistant_trees.py
   python scripts/sync_assistant_trees.py --check
   ```

The checked-in config enables the official OpenAI developer-docs MCP endpoint and conservative
subagent concurrency. It intentionally does not pin a model, approval policy, or sandbox mode;
those remain user/workspace choices.

## Asset mapping

| Canonical asset | Codex surface |
|-----------------|---------------|
| `AGENTS.md` | Repository instructions |
| `.claude/skills/**` | `.agents/skills/**` |
| `.claude/agents/*.md` | `.codex/agents/*.toml` |
| `.agent/workflows/*.md` | Shared workflow reference material |

Claude commands and rules are not converted into Codex slash commands. Ask for the workflow by
name (for example, “run the spec workflow”) or invoke the matching repository skill where one
exists.

Official references: [configuration](https://developers.openai.com/codex/config-reference),
[skills](https://developers.openai.com/codex/skills), and
[subagents](https://developers.openai.com/codex/multi-agent).
