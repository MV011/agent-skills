---
name: comprehensive-pr-review
description: Multi-agent comprehensive PR review that triages the diff, routes tiered specialized review agents (config-driven model routing on Claude runtimes), and consolidates findings with per-model provenance. Covers code quality, security, performance, patterns, DRY, type design, silent failures, ambiguous assertions, comments, dependencies, testing gaps, and implementation-specific deep dives. Use this skill whenever the user asks for a code review, PR review, diff review, pre-merge check, quality audit, or says things like "review my changes", "review this branch", "review this MR", "check before merging", "comprehensive review", or "run a PR review". Also trigger proactively when completing a major feature and preparing to merge.
---

# Comprehensive PR Review Skill

## Overview

This skill performs an intelligent, multi-agent code review before merging a branch. A **coordinator** (the main conversation) triages the diff, runs local quality gates, dispatches the optimal set of specialized review agents in parallel, adjudicates their findings, and — only after user approval — drives fixes. Agents do **research only**; all code changes happen after the user reviews findings.

### Supporting files (read on demand)

| File | Read it when |
|---|---|
| `config/dispatch.json` | Selecting agents or models — limits, thresholds, risk paths, task routing |
| `references/model-routing-claude.md` | Running on a **Claude runtime**, before any dispatch — tier→model table, escalation ladder, refusal mechanics |
| `references/triage.md` | Performing Step 2 — full heuristics and the triage-plan schema |
| `references/quality-gates.md` | Performing Step 3 — full Semgrep/LucidShark commands, installs, result handling |
| `references/agent-prompts.md` | Dispatching specialized agents (security/perf/migration) or implementation agents — templates and the finding metadata contract |

## When to Use

- You're about to create a PR and want a thorough review first
- The user asks for a comprehensive review, code quality check, diff review, or pre-merge review
- After completing a feature branch and before merging

## Portability & Model Routing

This skill runs on any agent runtime. Model selection is expressed as **abstract tiers**, resolved per runtime:

- **`cheap`** — triage, patch application, mechanical work
- **`standard`** — most review dimensions
- **`strong`** — the coordinator, adjudication, and the universal fallback (must be a model that will not refuse ordinary review work)
- **`deep`** — the strongest available model, reserved for risk-surface (security/migration) review

**On a Claude runtime** (Claude Code, Claude Agent SDK, direct Claude API): read `references/model-routing-claude.md` and `config/dispatch.json` **before dispatching anything**, and follow them exactly — they encode the tier→model mapping, the escalation ladder, refusal handling, and cost rules.

**On any other runtime** (Codex, Cursor, Gemini CLI, ...): do not read the Claude routing file. Map the four tiers onto the model lineup your runtime offers (cheapest → `cheap`, default → `standard`, strongest reliable → `strong` and `deep`). All other rules in this skill — triage, caps, the refusal/degraded loop, report format — apply unchanged.

**Universal rules (all runtimes):**
- `limits.max_concurrent_agents` (default 6) caps **simultaneous** dispatches, not the total: a 12-agent plan runs in waves of ≤6.
- Any leaf that refuses or fails is retried once on its configured fallback, and its findings are tagged `degraded: true` with the producing model recorded. A refusal never aborts the run — the review always completes with partial results and a degradation summary.

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

### Package Manager & Typecheck Detection

```bash
if [ -f "pnpm-lock.yaml" ]; then PM="pnpm"
elif [ -f "yarn.lock" ]; then PM="yarn"
elif [ -f "bun.lockb" ]; then PM="bun"
else PM="npm"; fi
```

Use `$PM run test`, `$PM run build`, `$PM run lint` throughout. If a `Makefile` is present, check for `make test`/`make lint` targets instead. For type checking: `$PM run typecheck` if the script exists, otherwise `npx tsc --noEmit`. Detect the project type from the filesystem (`package.json`, `go.mod`, `Cargo.toml`, `pyproject.toml`, ...) rather than assuming a framework.

## Step 2: Triage the Diff

Triage is the routing brain of the review — full heuristics in `references/triage.md`. Collect deterministic inputs first:

```bash
git diff $MERGE_BASE...HEAD --stat
git diff $MERGE_BASE...HEAD --name-only
git diff $MERGE_BASE...HEAD --shortstat
git log $MERGE_BASE..HEAD --oneline
git diff HEAD --name-only   # uncommitted work
```

Then classify (thresholds and pattern lists live in `config/dispatch.json`):

1. **Size** — LOC added/removed, files changed, distinct modules touched.
2. **Risk surface** — changed paths matched against `risk_paths` (auth, crypto, payment, sessions, middleware, SQL/migrations, CI/CD, dependency manifests). Any hit = risk-surface PR **regardless of size**.
3. **Nature** — pure refactor / new behavior / dependency bump / generated. Files matching `generated_paths` (lockfiles, snapshots, dist) are excluded from deep review.
4. **Test delta** — are tests added/modified proportionally to source changes?

Produce the **structured triage plan** (schema in `references/triage.md`): which agents, at which tier/effort, over which file groups, and why. **The plan goes into the final report** so routing decisions are auditable.

**Routing verdicts:**
- **Trivial** (within trivial thresholds, no risk-path hits, no behavior change) → a single `trivial-review` pass; skip fan-out entirely and jump to Step 6 after the gates.
- **Typical** → one agent per applicable dimension (Step 4), grouped by module if the PR spans several.
- **Risk-surface hit** (any size) → additionally dispatch `security-review` on the **deep tier**, scoped to just the matched files.
- **Large** (≥ large thresholds) → shard by module/package, one agent per shard per dimension, plus a coordinator **cross-shard consistency pass** after leaves return.

**Whole-repo branches:** if the branch has 50+ files because the entire repo was created on it, ask the user: "This branch has X files changed since the base. Should I review everything, or focus on the recent work?" (uncommitted changes first, then the last 2–3 commits).

## Step 3: Local Quality Gates (if available)

Run deterministic scanners **before** dispatching agents — their findings are evidence-based (rule ID + file:line, treat as 95%+ confidence) and corroborate agent findings. Full commands, installs, and result handling: `references/quality-gates.md`.

```bash
command -v semgrep    &>/dev/null && SEMGREP_AVAILABLE=true    || SEMGREP_AVAILABLE=false
command -v lucidshark &>/dev/null && LUCIDSHARK_AVAILABLE=true || LUCIDSHARK_AVAILABLE=false
```

- **Semgrep** — SAST on changed source files only (`p/owasp-top-ten`, `p/cwe-top-25`, `p/security-audit` + language packs).
- **LucidShark** — unified gate scoped to fast, diff-scoped domains only (`--linting --type-checking --formatting --sast` — deliberately **not** `--all`; the heavyweight whole-program domains belong in CI).
- Neither installed → note it in the report and continue; never skip the rest of the review.

## Step 4: Select Review Agents

Selection is driven by the triage plan. Task names below key into `config/dispatch.json` for tier/effort/fallback routing.

### Always-on (every non-trivial PR)

| Task | Role |
|---|---|
| `logic-review` | **Code Quality Reviewer** — patterns, DRY, clean code, logic bugs, language best practices |
| `style-review` | **Code Simplifier** — verbose code, simplification opportunities, extraction candidates |
| `silent-failure-review` | **Silent Failure Hunter** — swallowed errors, inadequate error handling, fallbacks that mask problems. Always on: it consistently finds the highest-severity issues, everywhere — not just API routes |

### Conditional

| Condition (from triage) | Task | Role |
|---|---|---|
| Any `risk_paths` hit (any PR size) | `security-review` | Security Reviewer — deep tier, scoped to matched files |
| New types/interfaces added | `type-design-review` | Type Design Analyzer |
| Comments added/changed | `comment-review` | Comment Accuracy Analyzer |
| Tests present or should be; assertions changed | `test-review` | Test Coverage Analyzer + Test Ambiguity Analyzer (assertions that accept multiple incompatible outcomes) |
| DB migrations present | `migration-review` | Migration Integrity Reviewer — deep tier |
| 5+ files changed | `performance-review` | Performance Reviewer |
| Dependencies touched | `dependency-review` | Dependency Pattern Checker |
| Large PR verdict | `deep-dive` | Implementation-Specific Deep Dive — architectural decisions specific to what was built |

### Scale by PR size

| PR Size | Files Changed | Agent Count |
|---------|--------------|-------------|
| Trivial | per triage verdict | 1 (`trivial-review` fast path) |
| Small | 1-5 | 3-4 agents |
| Medium | 6-15 | 5-7 agents |
| Large | 16-30 | 7-9 agents, sharded by module |
| XL | 30+ | 9-12 agents, sharded by module + cross-shard pass |

Total agent count may exceed `max_concurrent_agents` — that cap only bounds how many run at once. Respect `max_fable_dispatches` (deep-tier cap) on Claude runtimes: merge risk-surface file groups or overflow to the strong tier.

## Step 5: Dispatch Agents in Parallel

Launch the selected reviewers in waves of ≤ `max_concurrent_agents`, using whatever agent/subagent mechanism the runtime provides. Each reviewer runs in its own context and must not modify files. Pass per dispatch:

- `role`/`specialization`: the reviewer capability from Step 4
- `model`: resolved from the task's tier (Claude runtimes: per `references/model-routing-claude.md`)
- `prompt`: the template below with files and focus areas; add effort/depth instructions per the routing file
- `label`: descriptive name for tracking (e.g., `silent-failure-hunter`)

### Generic prompt template

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

If you cannot review any part of this assignment, say so explicitly at the top of your report — never silently skip files.
```

Specialized templates (security, performance, migration) and the cross-shard pass: `references/agent-prompts.md`. Confidence matters — findings below 70% are deprioritized during consolidation to keep speculative noise from drowning real issues.

### Refusal & failure handling (every dispatch, every runtime)

1. A leaf that **refuses** (safety classifier or model decline) or **hard-fails** → retry the identical task **once** on its configured `fallback` tier.
2. Tag all findings from the retry `degraded: true`; record the model that actually produced them.
3. Fallback also fails, or `fallback` is null → record that dimension as **"no coverage — degraded"** and continue.
4. **Never abort the run.** The review always completes with whatever was gathered, plus a degradation summary. Blast radius of any refusal = that single task.
5. **Escalation ladder** (Claude runtimes — see routing file): promote a task one rung when an agent self-reports low confidence or its gate fails twice. Never promote past the configured caps.

## Step 6: Collect and Consolidate

After all agents complete (or degrade), consolidate:

1. **Tally** findings per agent; note overlaps. Two+ agents independently flagging the same file:line = **corroboration** — treat as strong evidence.
2. **Deduplicate** — same file:line from different agents is one finding; keep the most detailed description, note all flagging agents.
3. **Filter** — drop findings below 60% confidence unless severity critical; move 60–75% to a "Worth Investigating" section.
4. **Present** — triage plan first (auditability), then Top 3, then the full table:

```text
## Triage Plan
{the structured triage block from Step 2, verbatim}

## Top 3 Most Impactful

1. **[CRITICAL]** `cli.ts:56` — Duplicate title key silently assigns wrong IDs (Quality + SilentFailure)
2. **[HIGH]** `client.ts:111` — HTTP error response body discarded (SilentFailure)
3. **[HIGH]** `writers/playwright.ts:156` — Unescaped interpolation can produce invalid syntax (Quality)

## All Findings

| # | Severity | File:Line | Issue | Agent(s) | Model (effort) | Confidence | Degraded |
|---|----------|-----------|-------|----------|----------------|------------|----------|
| 1 | CRITICAL | cli.ts:56 | Duplicate key assigns wrong IDs | Quality, SilentFailure | sonnet-5 (high) | 95% | — |
| 2 | HIGH | auth/session.ts:88 | Token compared with == not constant-time | Security | opus-4.8 | 85% | yes |

## Degradations & Coverage Gaps
- security-review: fable-5 refused (classifier); retried on opus-4.8 — findings above tagged degraded
- {or: "none"}

## Gate Results
- Semgrep: {n findings / not installed}
- LucidShark: {n findings / not installed}
```

## Step 7: Apply Fixes (with user approval)

**Do not start fixing until the user approves.** Present the consolidated findings and explicitly ask:

> "Here are the review findings. Would you like me to fix all of them, just the critical/high ones, or specific items by number?"

Wait for the response. Then, for each approved finding (critical first, then high):

**Tiered path (runtimes with model-tiered dispatch):** dispatch an `apply-patch` implementation agent per finding — **one finding, one file per dispatch** (template in `references/agent-prompts.md`). Every dispatch must include a machine-checkable gate (typecheck, tests, lint, or the repo's verify command). Loop: dispatch → verify gate output → re-dispatch on failure → after `impl_failures_before_escalation` failures (default 2), escalate one rung or take the fix into the coordinator. If no usable gate exists for a finding, skip the cheap agent — the coordinator applies that fix itself.

**Portable path (everywhere else):** apply fixes directly in the main context — read the file, apply, verify.

On both paths:

```bash
$PM run typecheck   # or npx tsc --noEmit
$PM test
```

after each batch, record per-finding fix status (`fixed-verified` / `fixed-unverified` / `skipped` / `open`) for the final report, and **do NOT commit automatically** — the user decides when to commit.

## Step 8: Track Unresolved Findings (optional)

If findings remain unfixed and the user wants to track them: check what issue tracker they use (Linear, Jira, GitHub Issues — ask, don't assume), then create issues carrying severity, file:line, description/impact, and recommended fix. No tracker → summarize unresolved findings in a comment block at the bottom of the PR description.

## Step 9: Final Verification

```bash
$PM run typecheck   # or npx tsc --noEmit
$PM test            # run test suite
git diff $MERGE_BASE...HEAD --stat  # verify no unintended changes
```

Update the findings table with final fix statuses.

## Notes

- Adapts to any project type — framework, package manager, and base branch are detected, never assumed.
- **Agents do RESEARCH ONLY** (no code writes). Fixes happen after user approval, via gated implementation agents or the main context.
- Small PRs get fewer agents; a trivial diff gets exactly one. Don't waste compute on a 2-file typo fix — but a risk-path hit always gets the deep security pass, even on a tiny diff.
- When multiple agents flag the same issue independently (corroboration), treat that as strong evidence it's real.
- **No external review bots.** This pipeline does not invoke CodeRabbit, Greptile, or similar CLIs/services — local gates are Semgrep + LucidShark (Step 3) plus this skill's own agents. Feedback those bots leave on the remote PR is handled by separate skills (`resolve-reviews` / `resolve-agent-reviews`), not here.
- `max_concurrent_agents` bounds parallelism, not coverage: queue, don't cut, when the plan is bigger than the cap.
- On Claude runtimes, all model choices come from `config/dispatch.json` — never hardcode model IDs in prompts or edits to this skill.
