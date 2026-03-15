# Agent Skills

Portable agent skills packaged once and exposed through multiple installation surfaces.

## Included Skills

| Skill | Purpose |
| --- | --- |
| `test-challenger` | Review tests for coverage, false positives, reliability, and framework-specific gaps. |
| `comprehensive-pr-review` | Run a structured multi-agent PR review before merge. |

`test-challenger` is the normalized packaged name for the original `test-challenge` source skill.

## Repository Layout

```text
.agents/skills/              # Canonical portable skills
.claude/agents/              # Generated Claude Code subagents
commands/skills/             # Generated Gemini CLI commands
scripts/install_skills.py    # Cross-runtime local installer
scripts/sync_adapters.py     # Regenerates Claude/Gemini adapters
```

## Quick Install

### Codex

```bash
python3 scripts/install_skills.py --target codex all
```

### Claude-compatible Skills

```bash
python3 scripts/install_skills.py --target claude-skills all
```

### Claude Code Subagents

```bash
python3 scripts/install_skills.py --target claude-subagents all
```

### Gemini CLI

```bash
gemini extensions install https://github.com/MV011/agent-skills
```

This installs the extension-backed commands:

- `/skills:test-challenger`
- `/skills:comprehensive-pr-review`

### Universal / Open Agent Skills

```bash
python3 scripts/install_skills.py --target universal all
```

That copies the canonical skills into `~/.agents/skills/`, which is the shared install surface used by the open Agent Skills convention and similar toolchains.

## Keeping Adapters In Sync

After changing any `SKILL.md`, regenerate the Claude and Gemini wrappers:

```bash
python3 scripts/sync_adapters.py
```

## More

Detailed install notes and upstream documentation links live in `docs/install.md`.
