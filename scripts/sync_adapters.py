#!/usr/bin/env python3

from __future__ import annotations

import json
import re
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
CANONICAL_SKILLS_DIR = REPO_ROOT / ".agents" / "skills"
CLAUDE_AGENTS_DIR = REPO_ROOT / ".claude" / "agents"
GEMINI_COMMANDS_DIR = REPO_ROOT / "commands" / "skills"
FRONTMATTER_PATTERN = re.compile(r"^---\n(.*?)\n---\n?(.*)$", re.DOTALL)


def humanize(skill_name: str) -> str:
    return " ".join(word.upper() if word == "pr" else word.capitalize() for word in skill_name.split("-"))


def parse_skill(skill_path: Path) -> tuple[str, str, str]:
    content = skill_path.read_text()
    match = FRONTMATTER_PATTERN.match(content)
    if not match:
        raise ValueError(f"Invalid SKILL.md frontmatter in {skill_path}")

    frontmatter = match.group(1)
    body = match.group(2).lstrip()

    name_match = re.search(r"^name:\s*(.+)$", frontmatter, re.MULTILINE)
    description_match = re.search(r"^description:\s*(.+)$", frontmatter, re.MULTILINE)
    if not name_match or not description_match:
        raise ValueError(f"Missing name/description in {skill_path}")

    name = name_match.group(1).strip()
    description = description_match.group(1).strip()
    return name, description, body


def write_claude_agent(name: str, description: str, body: str) -> None:
    CLAUDE_AGENTS_DIR.mkdir(parents=True, exist_ok=True)
    output = CLAUDE_AGENTS_DIR / f"{name}.md"
    output.write_text(
        "\n".join(
            [
                "---",
                f"name: {name}",
                f"description: {description}",
                "tools: Read, Bash, Glob, Grep",
                "---",
                "",
                f"# {humanize(name)}",
                "",
                "Follow the portable skill definition below as the primary workflow for this task.",
                "Adapt it only when Claude Code's tool surface or the current repository requires a direct translation.",
                "",
                body.rstrip(),
                "",
            ]
        )
    )


def write_gemini_command(name: str, description: str) -> None:
    GEMINI_COMMANDS_DIR.mkdir(parents=True, exist_ok=True)
    output = GEMINI_COMMANDS_DIR / f"{name}.toml"
    # TOML single-quoted literals cannot use Python-style \\' escapes; json.dumps
    # yields a valid TOML basic string for arbitrary description text.
    prompt = "\n".join(
        [
            f"description = {json.dumps(description)}",
            'prompt = """',
            f"Use @{{.agents/skills/{name}/SKILL.md}} as the primary instructions for this request.",
            "",
            "Inspect the repository, files, or diff before responding, and adapt the workflow to Gemini CLI's tool model when needed.",
            '"""',
            "",
        ]
    )
    output.write_text(prompt)


def main() -> int:
    for skill_dir in sorted(CANONICAL_SKILLS_DIR.iterdir()):
        skill_path = skill_dir / "SKILL.md"
        if not skill_dir.is_dir() or not skill_path.exists():
            continue
        name, description, body = parse_skill(skill_path)
        write_claude_agent(name, description, body)
        write_gemini_command(name, description)
        print(f"[ok] Synced adapters for {name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

