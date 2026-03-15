---
name: comprehensive-pr-review
description: Multi-agent comprehensive PR review that assesses project scope, determines review dimensions, and dispatches parallel specialized agents. Covers code quality, security, performance, patterns, DRY, type design, silent failures, ambiguous assertions, comments, dependencies, testing gaps, and implementation-specific deep dives. Use this skill whenever the user asks for a code review, PR review, pre-merge check, quality audit, or says things like "review my changes", "check before merging", "comprehensive review", or "run a PR review". Also trigger proactively when completing a major feature and preparing to merge.
tools: Read, Bash, Glob, Grep
---

# Comprehensive PR Review

Follow the portable skill definition below as the primary workflow for this task.
Adapt it only when Claude Code's tool surface or the current repository requires a direct translation.

# Comprehensive PR Review Skill

## Overview

This skill performs an intelligent, multi-agent code review before merging a branch. It assesses the PR scope and nature, then dispatches the optimal set of specialized review agents in parallel based on what was changed. Agents do **research only** — all code fixes happen in the main conversation context after the user reviews findings.

## When to Use

Invoke this skill when:
- You're about to create a PR and want a thorough review first
- The user asks for a comprehensive review, code quality check, or pre-merge review
- After completing a feature branch and before merging

## Step 1: Detect Environment

Before analyzing changes, detect the project environment so all subsequent commands work correctly.

### Base Branch Detection

The base branch varies across repos (`main`, `master`, `develop`, etc.). Detect it reliably:

```bash
# Try common base branch names, fall back to merge-base
BASE=$(git symbolic-ref refs/remotes/origin/HEAD 2>/dev/null | sed 's|refs/remotes/origin/||') \
  || BASE=$(for b in main master develop; do git rev-parse --verify "origin/$b" >/dev/null 2>&1 && echo "$b" && break; done) \
  || BASE=""

# If no remote base found, use merge-base with the most likely candidate
if [ -z "$BASE" ]; then
  echo "Could not auto-detect base branch. Using merge-base with origin/master."
  MERGE_BASE=$(git merge-base origin/master HEAD 2>/dev/null || git merge-base origin/main HEAD 2>/dev/null)
else
  MERGE_BASE=$(git merge-base "origin/$BASE" HEAD)
fi
```

Store the result and use `$MERGE_BASE` for all subsequent diff commands (`git diff $MERGE_BASE...HEAD`).

### Package Manager Detection

Detect the package manager so verification commands work:

```bash
if [ -f "pnpm-lock.yaml" ]; then PM="pnpm"
elif [ -f "yarn.lock" ]; then PM="yarn"
elif [ -f "bun.lockb" ]; then PM="bun"
else PM="npm"; fi
```

Use `$PM run test`, `$PM run build`, `$PM run lint`, etc. throughout. If a `Makefile` is present, check for `make test`/`make lint` targets instead.

### Typecheck Detection

Look for the project's type-checking command:
- If `package.json` has a `typecheck` script → `$PM run typecheck`
- Otherwise → `npx tsc --noEmit`

## Step 2: Assess the PR Scope

### Scope the Diff

Not all diffs are equal. Choose the right scope:

```bash
# Get the diff against the detected base
git diff $MERGE_BASE...HEAD --stat
git diff $MERGE_BASE...HEAD --name-only
git log $MERGE_BASE..HEAD --oneline
# Also check for uncommitted work
git diff HEAD --name-only
```

**Large diffs (whole-repo creation):** If the branch has 50+ files and the base is the initial commit (the entire repo was created on this branch), focus the review on:
1. Uncommitted/unstaged changes first (these are the most recent work)
2. The last 2-3 commits if uncommitted changes are small
3. Specific directories the user mentions

Ask the user: "This branch has X files changed since the base. Should I review everything, or focus on the recent work?"

### Classify Changed Files

Classify files into categories based on what actually exists in the project (don't assume a framework):

- **Source code** (`src/**`, `lib/**`, `app/**`) → code quality, DRY, patterns
- **HTTP/API handlers** (routes, controllers, endpoints) → security, error handling, validation
- **Types/interfaces** (`.d.ts`, type definition files, schema files) → type design
- **Tests** (`tests/**`, `__tests__/**`, `*.test.*`, `*.spec.*`) → test coverage analysis
- **Config/infra** (`package.json`, `Dockerfile`, CI configs) → dependency check
- **Database** (migrations, schemas, seeds) → schema integrity, data safety
- **Documentation** (`*.md`, `docs/**`) → comment accuracy

Detect the project type from the filesystem (look for `package.json`, `go.mod`, `Cargo.toml`, `pyproject.toml`, etc.) rather than assuming any specific framework.

## Step 3: Determine Agent Mix

Based on the scope assessment, select which reviewers or subagents to dispatch. Map the role names below to the closest capabilities available in your runtime.

### Always-On Roles (dispatch for every PR)
1. **Code Quality Reviewer** — Patterns, DRY, clean code, logic bugs, TypeScript best practices
2. **Code Simplifier** — Verbose code, simplification opportunities, extraction candidates
3. **Silent Failure Hunter** — Swallowed errors, inadequate error handling, fallback behavior that masks problems. This role catches data integrity bugs that other reviewers miss, so it should run on every PR regardless of whether API routes are involved.

### Conditional Agents

| Condition | Role | Suggested Capability |
|-----------|-------|------|
| New types/interfaces added | **Type Design Analyzer** | Type-focused reviewer |
| Comments added/changed | **Comment Accuracy Analyzer** | Documentation reviewer |
| Tests present or should be | **Test Coverage Analyzer** | Test-quality reviewer |
| Tests present or assertions changed | **Test Ambiguity Analyzer** | Assertion-specificity reviewer |
| HTTP/API handlers changed | **Security Reviewer** | Security-focused reviewer |
| DB migrations present | **Migration Integrity Reviewer** | Deep code or schema explorer |
| 5+ files changed | **Performance Reviewer** | Performance-focused reviewer |
| Dependencies touched | **Dependency Pattern Checker** | Dependency and ecosystem reviewer |

### Scale by PR Size

| PR Size | Files Changed | Agent Count |
|---------|--------------|-------------|
| Small | 1-5 | 3-4 agents |
| Medium | 6-15 | 5-7 agents |
| Large | 16-30 | 7-9 agents |
| XL | 30+ | 9-12 agents |

For large PRs, also add:
- **Implementation-Specific Deep Dive** — Review architectural decisions specific to what was built

## Step 4: Dispatch Agents in Parallel

Launch ALL selected reviewers simultaneously using whatever agent or subagent mechanism the current runtime provides. Each reviewer should run in its own context and should not modify files.

### Agent Invocation

Use your runtime's equivalent reviewer orchestration with parameters like:
- `role` or `specialization`: The reviewer capability from the table above
- `run concurrently` or `background`: If the runtime supports parallel review
- `prompt`: The review task with specific files and focus areas (use the template below)
- `label`: A descriptive name for tracking (for example, `silent-failure-hunter`)

Recommended reviewer roles:
- **Code quality reviewer** — Finds bugs, logic errors, and code quality issues
- **Code simplifier** — Identifies verbose code and extraction opportunities
- **Silent failure hunter** — Finds swallowed errors and inadequate error handling
- **Type design analyzer** — Reviews type quality, encapsulation, and invariants
- **Comment analyzer** — Checks comment accuracy after refactoring
- **Test analyzer** — Reviews test coverage quality
- **Test ambiguity analyzer** — Finds assertions that accept multiple incompatible outcomes or hide the real contract
- **Code explorer** — Performs deep analysis of execution paths and architecture
- **Architecture reviewer** — Reviews design patterns and structural decisions
- **Security reviewer** — Research-only security audit
- **Performance reviewer** — Research-only performance audit

### Agent Prompt Template

```text
Review the branch `{branch}` (vs `{base}`) focusing on {specialty}.
DO NOT write any code — research and report findings only.

Changed files relevant to your review:
{filtered_file_list}

Focus on:
{specific_focus_areas}

For each finding, provide:
- Severity: critical / high / medium / low
- Confidence: percentage (e.g., 90%) — how sure you are this is a real issue, not a false positive
- File path and line number
- Description of the issue
- Suggested fix (code snippet if applicable)
```

The confidence percentage matters — during consolidation, findings below 70% confidence are deprioritized. This prevents noise from speculative or uncertain findings drowning out real issues.

### Error Handling
- If an agent fails or times out, note it in the consolidated report
- Continue with other agents — don't block the entire review
- Re-run failed agents individually if needed

## Step 5: Collect and Consolidate

After all agents complete, perform a thorough consolidation — this is where the review's value comes together.

### 5a. Tally per-agent results
Count findings per agent and note which agents produced overlapping findings. When two or more agents independently flag the same file:line, that's **corroboration** — increase your confidence that it's a real issue.

### 5b. Deduplicate
Same file:line from different agents = one finding. Keep the most detailed description but note all agents that flagged it (corroboration signal).

### 5c. Filter low-confidence findings
Drop findings below 60% confidence unless they are severity critical. Move findings between 60-75% to a "Worth Investigating" section.

### 5d. Prioritize and present

Present a **"Top 3 Most Impactful"** callout first — the three findings most likely to cause real problems in production. Then present the full table:

```text
## Top 3 Most Impactful

1. **[CRITICAL]** `cli.ts:56` — Duplicate title key silently assigns wrong IDs (Quality + SilentFailure)
2. **[HIGH]** `client.ts:111` — HTTP error response body discarded — users can't debug API failures (SilentFailure)
3. **[HIGH]** `writers/playwright.ts:156` — Unescaped interpolation can produce invalid syntax (Quality)

## All Findings

| # | Severity | File:Line | Issue | Agent(s) | Confidence |
|---|----------|-----------|-------|----------|------------|
| 1 | CRITICAL | cli.ts:56 | Duplicate key assigns wrong IDs | Quality, SilentFailure | 95% |
| 2 | HIGH | client.ts:111 | Error body discarded | SilentFailure | 90% |
```

## Step 6: Apply Fixes (with user approval)

**Do not start fixing until the user approves.** Present the consolidated findings table and explicitly ask:

> "Here are the review findings. Would you like me to fix all of them, just the critical/high ones, or specific items by number?"

Wait for the user's response before proceeding. Then for each approved finding (starting with critical, then high):

1. Read the file
2. Apply the fix
3. After each batch of fixes, run verification:
   ```bash
   $PM run typecheck  # or npx tsc --noEmit
   $PM test
   ```
4. Do NOT commit automatically — let the user decide when to commit

## Step 7: Track Unresolved Findings (optional)

If findings remain unfixed and the user wants to track them:

1. Check if the user has an issue tracker available (Linear, Jira, GitHub Issues, etc.)
2. If yes, offer to create issues for unresolved findings with:
   - Severity level
   - Affected file(s) and line numbers
   - Description and impact
   - Recommended fix
3. If no tracker is available, summarize unresolved findings in a comment block at the bottom of the PR description

Don't assume any specific issue tracker — ask the user what they use.

## Step 8: Final Verification

After all fixes, verify nothing is broken:

```bash
$PM run typecheck   # or npx tsc --noEmit
$PM test            # run test suite
git diff $MERGE_BASE...HEAD --stat  # verify no unintended changes
```

## Specialized Agent Prompt Templates

### Security Review Prompt
```text
Perform a security audit on branch `{branch}`. DO NOT write code — research only.
Focus on:
- Input validation gaps (user input, API parameters, file paths)
- Authentication/authorization bypass risks
- Data exposure (fields that shouldn't be public)
- Injection risks (SQL, command, template)
- Privilege escalation paths
- Insecure deserialization or unsafe type casts
Files: {relevant_files}

Provide findings with severity, confidence %, file:line, description, and suggested fix.
```

### Performance Review Prompt
```text
Review for performance issues. DO NOT write code — research only.
Focus on:
- N+1 query problems or redundant API calls
- Over-fetching (selecting/loading unused data)
- Missing caching opportunities
- Unbounded loops or allocations
- Sequential operations that could be parallel
Files: {relevant_files}

Provide findings with severity, confidence %, file:line, description, and suggested fix.
```

### Migration Review Prompt
```text
Analyze database migrations for integrity and safety. DO NOT write code — research only.
Focus on:
- Idempotency (IF EXISTS/IF NOT EXISTS guards)
- Data migration safety and rollback capability
- Index appropriateness for query patterns
- Foreign key cascade behavior
- Seed data correctness
Files: {migration_files}

Provide findings with severity, confidence %, file:line, description, and suggested fix.
```

## Notes

- This skill adapts to any project type — it detects the framework, package manager, and base branch automatically rather than assuming a specific stack.
- Small PRs get fewer agents. Don't waste compute on a 2-file typo fix.
- **Agents do RESEARCH ONLY** (no code writes). They report findings. The main conversation context applies fixes after user approval.
- The Silent Failure Hunter is always-on because error handling bugs exist everywhere, not just in API routes. In practice, it consistently finds the highest-severity issues.
- When multiple agents flag the same issue independently (corroboration), treat that as strong evidence the issue is real.
