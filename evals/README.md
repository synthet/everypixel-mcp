# Agent eval fixtures

This directory contains static evaluation fixtures for command and skill assets. The first runner,
`scripts/run_agent_eval_fixtures.py`, is intentionally lightweight: it validates fixture structure,
checks that referenced assets exist, and asserts that required guardrail text is present (or absent)
in the target asset plus any explicitly linked supporting docs.

## Fixture schema

Each JSON fixture is an object with these fields:

- `id` (string): stable kebab-case fixture id.
- `description` (string): what behavior the fixture protects.
- `target_asset` (string): repository-relative path to the primary command or skill file.
- `linked_docs` (array of strings): repository-relative supporting files to include in text checks.
- `must_contain` (array of strings): snippets that must appear in the target asset or linked docs.
- `must_not_contain` (array of strings): snippets that must not appear in the target asset or linked docs.

Run locally with:

```bash
python scripts/run_agent_eval_fixtures.py
```
