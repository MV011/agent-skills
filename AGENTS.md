# Agent Skills

This repository packages portable agent skills for multiple agent runtimes.

## Layout

- Canonical skill definitions live in `.agents/skills/<skill-name>/SKILL.md`.
- Codex UI metadata lives in `.agents/skills/<skill-name>/agents/openai.yaml`.
- Claude Code adapters are generated into `.claude/agents/`.
- Gemini CLI command wrappers are generated into `commands/skills/`.
- Install helpers live in `scripts/`.

## Working Rules

- Treat `.agents/skills/` as the source of truth.
- After adding or editing a skill, run `python3 scripts/sync_adapters.py`.
- Keep skill names hyphen-case and filenames canonical as `SKILL.md`.
- Prefer updating the shared skill first, then regenerate adapters instead of hand-editing wrappers.
- See `README.md` for quick install commands and `docs/install.md` for target-specific details.
