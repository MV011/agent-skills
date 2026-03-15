#!/usr/bin/env python3

from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
CANONICAL_SKILLS_DIR = REPO_ROOT / ".agents" / "skills"
CLAUDE_AGENTS_DIR = REPO_ROOT / ".claude" / "agents"
DEFAULT_TARGETS = {
    "codex": Path.home() / ".codex" / "skills",
    "claude-skills": Path.home() / ".claude" / "skills",
    "claude-subagents": Path.home() / ".claude" / "agents",
    "universal": Path.home() / ".agents" / "skills",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Install packaged skills into local agent directories.",
    )
    parser.add_argument(
        "--target",
        choices=["all", *DEFAULT_TARGETS.keys()],
        default="codex",
        help="Install target. Use 'all' to install every local-copy target.",
    )
    parser.add_argument(
        "--mode",
        choices=["copy", "link"],
        default="copy",
        help="Copy files or create symlinks into the destination.",
    )
    parser.add_argument(
        "--dest",
        help="Override destination directory. Only valid for a single target.",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Replace existing installed skills or subagents.",
    )
    parser.add_argument(
        "skills",
        nargs="*",
        help="Skill names to install. Use 'all' or omit to install every packaged skill.",
    )
    return parser.parse_args()


def available_skills() -> list[str]:
    return sorted(
        path.name
        for path in CANONICAL_SKILLS_DIR.iterdir()
        if path.is_dir() and (path / "SKILL.md").exists()
    )


def resolve_skills(selected: list[str]) -> list[str]:
    available = available_skills()
    if not selected or selected == ["all"]:
        return available

    unknown = [skill for skill in selected if skill not in available]
    if unknown:
        raise SystemExit(
            f"Unknown skill(s): {', '.join(unknown)}. Available: {', '.join(available)}"
        )
    return selected


def remove_existing(path: Path) -> None:
    if path.is_symlink() or path.is_file():
        path.unlink()
    elif path.is_dir():
        shutil.rmtree(path)


def ensure_parent(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def install_directory(source: Path, destination: Path, mode: str, force: bool) -> None:
    if destination.exists() or destination.is_symlink():
        if not force:
            raise SystemExit(f"Destination already exists: {destination}")
        remove_existing(destination)

    ensure_parent(destination)
    if mode == "link":
        destination.symlink_to(source, target_is_directory=True)
        return
    shutil.copytree(source, destination)


def install_file(source: Path, destination: Path, mode: str, force: bool) -> None:
    if destination.exists() or destination.is_symlink():
        if not force:
            raise SystemExit(f"Destination already exists: {destination}")
        remove_existing(destination)

    ensure_parent(destination)
    if mode == "link":
        destination.symlink_to(source)
        return
    shutil.copy2(source, destination)


def install_target(
    target: str,
    destination_root: Path,
    skills: list[str],
    mode: str,
    force: bool,
) -> None:
    if target == "claude-subagents":
        destination_root.mkdir(parents=True, exist_ok=True)
        for skill in skills:
            source = CLAUDE_AGENTS_DIR / f"{skill}.md"
            if not source.exists():
                raise SystemExit(
                    f"Missing Claude adapter for {skill}. Run scripts/sync_adapters.py first."
                )
            install_file(source, destination_root / source.name, mode, force)
        return

    destination_root.mkdir(parents=True, exist_ok=True)
    for skill in skills:
        source = CANONICAL_SKILLS_DIR / skill
        install_directory(source, destination_root / skill, mode, force)


def main() -> int:
    args = parse_args()
    skills = resolve_skills(args.skills)

    if args.dest and args.target == "all":
        raise SystemExit("--dest can only be used with a single target.")

    targets = list(DEFAULT_TARGETS) if args.target == "all" else [args.target]
    for target in targets:
        destination_root = Path(args.dest).expanduser() if args.dest else DEFAULT_TARGETS[target]
        install_target(target, destination_root, skills, args.mode, args.force)
        print(f"[ok] Installed {', '.join(skills)} to {target}: {destination_root}")

    return 0


if __name__ == "__main__":
    sys.exit(main())

