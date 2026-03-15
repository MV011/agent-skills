# Agent Skills Extension

This Gemini CLI extension exposes portable skill definitions as native Gemini commands.

## Commands

- `/skills:test-challenger`
- `/skills:comprehensive-pr-review`

## Source Of Truth

The canonical skill definitions live in `.agents/skills/`.
The Gemini command wrappers in `commands/skills/` are generated from those files.
