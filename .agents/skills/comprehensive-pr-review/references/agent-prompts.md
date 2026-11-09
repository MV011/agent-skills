# Agent Prompt Templates

Prompt templates for review leaves and implementation agents. The generic template lives in SKILL.md (it is used on every run); this file carries the specialized variants and the finding metadata contract.

## Finding metadata contract

Every leaf reports findings with:

- **Severity**: critical / high / medium / low
- **Confidence**: percentage (e.g., 90%) — how sure this is a real issue, not a false positive
- **File path and line number**
- **Description** of the issue
- **Suggested fix** (code snippet if applicable)

Additionally, every leaf must state explicitly at the **top** of its report if it could not review part of its assignment (declined, blocked, out of scope) — never silently skip files. The coordinator uses this to trigger the fallback loop.

The **coordinator** records per finding after leaves return:

- **model / effort**: which model actually produced it (post-fallback) and at what effort
- **degraded**: `true` when produced by a fallback model after a refusal/failure
- **fix status** (after Step 7): `fixed-verified` / `fixed-unverified` / `skipped` / `open`

## Design review prompt (`design-review`, strong tier, runs first)

If the `design-review` skill is installed in the runtime, tell the leaf to follow it. Otherwise use this condensed form:

```text
Perform an architecture-level design review of branch `{branch}` (vs `{base}`). DO NOT write code. DO NOT read implementation source files: read only the design surface below, the PR description and the linked requirements.
Design-surface files: {design_surface_files}
Requirements: {pr_description_and_ticket}

1. Sketch the added/changed components from the design surface: stores (keys, indexes), buses/queues/topics, functions/services, routes, schedules, roles, config sources, and the flows between them.
2. List the access patterns the requirements imply: who reads/writes, lists, filters, sorts, paging, tenancy, ordering, retention, audit. Map each pattern to the store's keys and indexes. A pattern that needs a filter outside the key, a scan, an unindexed sort, or a tenant scope the keys do not carry is a store-fit question for this report, not a hand-off.
3. Ask whether the design fits: store vs access patterns; tenant key and where authorization is enforced; any state fed by more than one event input; dedupe keys vs real-world identity; retry and dead-letter layers and what operators see on failure; one identity per component and wildcard permissions; runtime vs deploy-time config and missing-config behaviour; contract changes and their consumers; retention and audit records; deploy order and backfill; an existing component that already does this.
4. For each question: evidence (design file:line), requirement at risk, likely concrete failure, options, and whether a deterministic fitness rule could catch it.

Report: verdict PROCEED / DISCUSS / REDESIGN, the design questions (most consequential first, at most about five), and a "Hand-off to code review" list of questions only code can answer.
If you cannot review any part of this assignment, say so explicitly at the top of your report.
```

The coordinator appends the hand-off list to every other leaf's focus areas, and links later code findings that are symptoms of a design question to that question in the report.

## Security review prompt (`security-review` — deep tier)

```text
Perform a security audit on branch `{branch}`. DO NOT write code — research only.
Focus on:
- Input validation gaps (user input, API parameters, file paths)
- Authentication/authorization bypass risks
- Data exposure (fields that shouldn't be public)
- Injection risks (SQL, command, template)
- Privilege escalation paths
- Insecure deserialization or unsafe type casts
Files: {risk_surface_files_only}

Provide findings with severity, confidence %, file:line, description, and suggested fix.
If you cannot review any part of this assignment, say so explicitly at the top of your report.
```

Scope `{risk_surface_files_only}` to just the files that matched `risk_paths` in triage — the deep tier is expensive and capped.

## Performance review prompt (`performance-review`)

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

## Migration review prompt (`migration-review` — deep tier)

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

## Cross-shard consistency pass (large PRs — coordinator, after leaves return)

Not a dispatch — the coordinator itself checks across shard reports for:

- The same logic implemented differently in two shards
- Contract mismatches (one shard changed an interface, another still uses the old shape)
- Naming drift for the same concept
- Fixes flagged in one shard that also apply to unflagged twins in another

## Implementation agent prompt (`apply-patch` — cheap tier)

Narrow contract: **one finding, one file per dispatch.** Never batch multiple findings or multi-file edits into a cheap agent.

```text
Apply exactly this fix and nothing else.

Finding: {finding description + suggested fix from the report}
File: {single file path}

Constraints:
- Do not refactor, rename, or "improve" anything not named in the finding.
- Do not touch any other file.

After editing, run this verification gate and include its FULL output:
{gate command(s), e.g. "$PM run typecheck && $PM test -- {related test file}"}

Report: the exact diff you applied, and the gate output with a clear PASS/FAIL.
```

**Gate rule:** the gate must be machine-checkable (typecheck, tests, lint, or the repo's own verify command). A failure you can't detect isn't cheap — if the repo has no usable gate for a finding, do not dispatch a cheap agent; the coordinator applies that fix itself in the main context.

**Retry loop:** gate fails → re-dispatch the same narrow task once with the failure output included. After `limits.impl_failures_before_escalation` failures (default 2), escalate one rung up the ladder (see `references/model-routing-claude.md` on Claude runtimes) or hand the fix to the coordinator.
