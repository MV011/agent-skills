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

## LucidShark (quality gate + MCP)

[LucidShark](https://lucidshark.com/) is the unified local scanner used as a **gate** in the `comprehensive-pr-review` skill. Install the binary once under your user profile:

```bash
mkdir -p ~/.local/bin
VER=$(curl -fsSL https://api.github.com/repos/toniantunovi/lucidshark/releases/latest | grep '"tag_name":' | sed -E 's/.*"([^"]+)".*/\1/')
OS=$(uname -s | tr '[:upper:]' '[:lower:]')
ARCH=$(uname -m); case "$ARCH" in x86_64|amd64) A=amd64;; arm64|aarch64) A=arm64;; *) echo "unsupported arch"; exit 1;; esac
curl -fsSL "https://github.com/toniantunovi/lucidshark/releases/download/${VER}/lucidshark-${OS}-${A}" -o ~/.local/bin/lucidshark
chmod +x ~/.local/bin/lucidshark
```

Confirm: `lucidshark --version`. Ensure `~/.local/bin` is on `PATH`.

Per-project setup (optional): run `lucidshark init` in a repository to create `lucidshark.yml` and wire defaults.

### MCP server (`lucidshark serve --mcp`)

Use the same absolute path on your machine. Stdio command:

- **Command:** `/Users/YOU/.local/bin/lucidshark` (adjust `YOU`)
- **Arguments:** `serve`, `--mcp`

**Claude Code:** merge into the top-level `mcpServers` object in `~/.claude.json`:

```json
"lucidshark": {
  "type": "stdio",
  "command": "/Users/YOU/.local/bin/lucidshark",
  "args": ["serve", "--mcp"]
}
```

**Cursor:** `~/.cursor/mcp.json` → add under `mcpServers` (same `command` / `args`; Cursor’s file omits `"type"`).

**Open Code:** `~/.config/opencode/mcp.json` (and/or `~/.opencode/mcp.json` if you use that copy) → same `mcpServers` shape as Cursor.

**Codex:** `~/.codex/config.toml`:

```toml
[mcp_servers.lucidshark]
command = "/Users/YOU/.local/bin/lucidshark"
args = ["serve", "--mcp"]
enabled = true
```

**Gemini CLI:** `~/.gemini/settings.json` → `mcpServers.lucidshark` with `"command"` and `"args": ["serve", "--mcp"]`.

Restart the CLI or IDE after editing MCP config. The MCP server uses the **current working directory** of the spawned process as the project root—open the workspace from the repo root so scans target the right tree.
