# Install Notes

This repository is structured so one canonical skill definition can be consumed from several agent runtimes.

## Canonical Skills

The canonical install surface is:

```text
.agents/skills/<skill-name>/SKILL.md
```

That layout is compatible with the open Agent Skills convention and also works with direct-copy installs for Codex-style and Claude-style skill directories.

## Codex

- Official skills docs: https://developers.openai.com/codex/skills
- Native local install:

```bash
python3 scripts/install_skills.py --target codex all
```

- If you already have OpenAI's `skill-installer` helper available, this repo is also compatible with GitHub path installs:

```bash
python3 scripts/install-skill-from-github.py \
  --repo MV011/agent-skills \
  --path .agents/skills/test-challenger \
  --path .agents/skills/comprehensive-pr-review
```

## Claude

- Claude Code subagents docs: https://docs.anthropic.com/en/docs/claude-code/sub-agents
- Install the generated subagent wrappers globally:

```bash
python3 scripts/install_skills.py --target claude-subagents all
```

- If your Claude-compatible setup scans `~/.claude/skills/`, you can also install the raw portable skills there:

```bash
python3 scripts/install_skills.py --target claude-skills all
```

## Gemini CLI

- Extensions getting started: https://google-gemini.github.io/gemini-cli/docs/extensions/getting-started/
- Custom commands: https://google-gemini.github.io/gemini-cli/docs/extensions/commands/
- Install this repository directly as an extension:

```bash
gemini extensions install https://github.com/MV011/agent-skills
```

After install, use:

- `/skills:test-challenger`
- `/skills:comprehensive-pr-review`

## Universal / Open Agent Skills

- Open Agent Skills standard: https://agentskills.io/
- Integration guide: https://agentskills.io/getting-started/integration-guide/
- Install canonical skills into the shared user directory:

```bash
python3 scripts/install_skills.py --target universal all
```

That copies the skill directories into `~/.agents/skills/`.
