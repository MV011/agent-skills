---
name: test-challenger
description: Analyze and rate test scenarios for quality, completeness, and reliability. Use when writing, reviewing, or improving ANY type of test — declarative workflow tests, Playwright E2E/API tests, Jest/Vitest/NUnit/xUnit/pytest unit tests, containerized multi-service integration tests, k6 performance tests, or any other framework. Triggers on "challenge tests", "rate tests", "review test quality", "are our tests good", "grade the tests", or any test quality discussion. Also use proactively after writing or modifying test code. For custom or unfamiliar frameworks, first read that framework's docs, local helpers, and example tests, then apply the generic scoring dimensions.
---

# Test Challenger

Rate test scenarios on quality dimensions, prove suspicious tests can actually fail, identify false positives and gaps, and suggest concrete improvements. Works across testing frameworks by combining universal test-quality rules with framework-specific rubrics.

## Supporting files (read on demand)

| File | Read it when |
|---|---|
| `references/rubric-workflow-dsl.md` | Rating declarative workflow / DSL / YAML-scenario tests |
| `references/rubric-e2e-playwright.md` | Rating Playwright browser or API E2E tests |
| `references/rubric-integration.md` | Rating containerized / multi-service integration tests |
| `references/rubric-unit.md` | Rating unit tests — Jest, Vitest, NUnit, xUnit, pytest, go test |
| `references/rubric-custom.md` | Rating custom/unfamiliar frameworks or performance tests (k6, Gatling, Locust) |

Each rubric file carries the weighted dimensions, the detailed 0–N scoring bands, framework anti-patterns, a checklist, and worked examples. **Read only the rubric(s) matching the tests under review.**

## When to Use

- After writing or updating test code (any framework)
- Before committing test changes
- When reviewing a PR that includes tests
- When the user asks to "challenge", "rate", or "grade" tests
- Proactively after any chunk of test work
- When tests are failing and you need to determine if the test or the system is wrong

## Process

### Step 1: Detect Framework and Read the Test

Read the test file completely. Detect the framework and pick the rubric:

- **Playwright-style tests** → `references/rubric-e2e-playwright.md`
- **Jest / Vitest / NUnit / xUnit / pytest / go test** → `references/rubric-unit.md`
- **Containerized end-to-end flows** → `references/rubric-integration.md`
- **Declarative YAML/JSON/DSL tests** → `references/rubric-workflow-dsl.md`
- **k6 / Gatling / Locust performance tests** → `references/rubric-custom.md` (perf section)
- **Anything custom or unfamiliar** → `references/rubric-custom.md`; treat it as unknown until you've read its docs and local examples — never invent framework mechanics from memory

Then understand: What system/API/feature does it target? What specific path/behavior does it test? What input triggers this path? What is the expected outcome?

### Step 2: Read the Source of Truth

The test assertions must match **reality**, not assumptions.

- **Declarative workflow/DSL tests**: Read the workflow definition, execution graph, or framework docs. Trace the exact path.
- **API tests**: Read the route handler code. Understand what the endpoint actually returns for this input. Check if the test's expected status codes and response shapes match the real API.
- **Unit tests**: Read the function under test. Trace the execution path.
- **Verify the test data**: Is the test fixture/data chosen for the RIGHT reasons (minimal pre-existing rules, correct permissions, realistic related records)? Or just because it was convenient?

### Step 3: Apply Universal Checks

Before the framework rubric, check these universal questions:

| Universal Check | What to Ask |
|-----------------|-------------|
| **Behavior Coverage** | Does the test prove the intended behavior, not just that code ran? |
| **False Positive Resistance** | Would the test still pass if the feature were broken, bypassed, or stubbed incorrectly? |
| **Ambiguity Elimination** | Does the test pin one correct outcome instead of accepting multiple incompatible outcomes? |
| **Source-of-Truth Alignment** | Do assertions match the real implementation, contract, or workflow definition? |
| **Determinism** | Would this test produce the same result at 3am, on CI, in parallel, on retry 0? No wall-clock/timezone dependence, hard waits, ordering assumptions, real-network reliance, or retry-masked flakiness? |
| **Data & Fixture Quality** | Are fixtures realistic, purposeful, and isolated enough to support the claim? |
| **Failure Clarity** | If the test fails, does it make the root cause obvious? |

If a test is weak on these universal checks, call that out even if the framework-specific mechanics look correct. A test that only passes with retries enabled is a flaky test with a bandage — score it as flaky.

Treat ambiguity as a defect, not a compromise:
- If a test accepts multiple materially different statuses, bodies, branches, or error shapes, verify the intended contract from code/docs first.
- If the implementation truly allows multiple valid outcomes, assert the condition that distinguishes them and explain why both are valid.
- If you cannot prove the ambiguity is intentional, score it down and recommend pinning the expectation.

```ts
// BAD: accepts incompatible outcomes without proving which one is correct
expect([200, 404]).toContain(response.status);

// BETTER: pin one verified contract
expect(response.status).toBe(200);
expect(response.body).toMatchObject({ ok: true });
```

### Step 4: Rate on the Framework Rubric

Read the matching `references/rubric-*.md` and score each dimension. **Every score below the dimension maximum must cite concrete evidence** (`file:line` plus what's missing) — no vibes-based deductions. This keeps scores reproducible across runs and makes the report actionable.

### Step 5: Prove It Can Fail (falsification pass)

Scoring False Positive Resistance by reading is a prediction; this step is the experiment. **When the tests can be run locally**, pick the highest-risk candidates (anything scoring ≤ half marks on False Positive Resistance, plus any test the diff claims guards a critical behavior — cap at ~3) and prove each can fail:

1. Run the test as-is — confirm it passes (a failing test needs diagnosis, not falsification).
2. Sabotage the **feature**, not the test: stash-safe, minimal, targeted — invert the guard condition, short-circuit the handler with the wrong response, return the forbidden branch. `git stash` / direct revert must restore it exactly.
3. Re-run the test. **It must fail.** If it still passes, that is a confirmed false positive — the single most severe finding this skill produces. Report it at the top regardless of the numeric score.
4. Revert the sabotage immediately and re-run to confirm green. Never leave sabotage in the working tree; never commit it; skip this step entirely if the working tree has uncommitted changes you can't safely stash around.

If tests can't be run (no local runner, env-gated), say so explicitly in the report — the False Positive Resistance score is then marked *unverified*.

### Step 6: Calculate Score and Report

Output a table with the framework-appropriate dimensions:

```text
| Dimension | Score | Max | Evidence |
|-----------|-------|-----|----------|
| [dim 1] | X | XX | [file:line — what's missing] |
| ...
| **TOTAL** | **X** | **100** | |
```

**Verdict bands** (state the verdict with the score):

| Score | Verdict |
|---|---|
| 85–100 | **Ship** — minor polish optional |
| 70–84 | **Improve first** — merge acceptable, listed improvements should follow shortly |
| 50–69 | **Fix before merge** — material gaps in what the tests prove |
| <50 | **Rework** — the suite provides false confidence; treat as untested |

A **confirmed false positive from Step 5 caps the verdict at "Fix before merge"** regardless of the numeric total.

Then list **specific improvements** ordered by impact.

### Step 7: Fix (if asked)

- Apply improvements in order of impact
- Re-run tests to verify they still pass
- **Re-run the Step 5 falsification on any assertion you strengthened** — the point of the fix is that the test now fails when the feature breaks; prove it
- Re-rate to confirm improvement

## Scaling & Model Routing

- **Small scope (≤ ~5 test files, one framework):** run the whole process in the current context.
- **Large scope (many files or multiple frameworks):** dispatch one rating agent per framework/module in parallel — rating against a fixed rubric is mechanical, so use a cheap/standard tier (Claude runtimes: `haiku`/`sonnet`). The coordinator merges reports, adjudicates disagreements, and runs Step 5 falsification itself (sabotage needs a single owner of the working tree — never parallelize it).
- **Cross-model second opinion (optional):** for contested scores or an adversarial "find the false positive the first pass missed" sweep, dispatch one leaf through the Codex CLI on its separate quota pool — follow `references/model-routing-codex.md` in the sibling `comprehensive-pr-review` skill for tier mapping and `codex exec` hygiene (read-only sandbox, explicit `-m`/effort, `</dev/null`, PID-only cleanup).
- **Cross-model dispatch reliability:** external-CLI agents sometimes return empty, truncated, or off-format output. Treat that as a **failed dispatch, not a clean bill** — retry once (fallback model), and if it fails again, report "second opinion unavailable" rather than counting silence as agreement.

## Universal Anti-Patterns to Flag

- **Test passes with broken feature** — the most critical failure. Step 5 exists to catch this empirically; always ask: "if I deleted the feature, would this still pass?"
- **Existence checks without value checks** — `toHaveProperty('field')` passes when `field: null`. Check actual values.
- **Ambiguous acceptance windows** — accepting multiple incompatible outcomes like `[200, 404]`, `[400, 404]`, or multiple unrelated error shapes without proving the contract allows them.
- **Silent fallbacks** — silently coercing missing state into an empty string or default value. Throw clearly instead.
- **Nondeterminism** — hard waits/sleeps instead of condition waits; `Date.now`/`DateTime.Now` without a clock abstraction; inter-test ordering dependence; reliance on live external services; flakiness hidden by retries.
- **No cleanup** — created data (rules, related records, auth credentials) left in dev environment. Large piles of orphaned integration-test records are a real failure mode.
- **Testing through DB hacks** — if there's a real API/UI flow, use it. DB-seeded data may not match reality.
- **Hardcoded environment data** — test fixtures chosen for convenience, not properties. A fixture with lots of pre-existing automation or records will break tests that expect a clean baseline.

Framework-specific anti-patterns live in each rubric file.

## Environment Considerations

- **Pre-existing data** — dev environments often have workflow rules, existing records, and orphaned test artifacts
- **Fixture selection** — verify the fixture has the right properties (minimal pre-existing rules, correct permissions, valid test prerequisites, existing related records)
- **Orphan cleanup** — check for stale E2E rules/records from previous crashed runs
- **Real flows vs DB seeding** — use real flows for auth credentials, related records, and user links; DB seeding is OK for workflow rules, resource restrictions, and baseline data with no user-facing creation flow

## Code Quality Checks

When test source code is available:
- **Type safety** — TypeScript tests should use proper types, not `any`. Response types should be explicit interfaces.
- **DRY within reason** — extract repeated patterns (resource submission, rule cleanup, denial assertions) into helpers
- **Consistent patterns** — follows the same structure as other tests in the project
- **No commented-out or placeholder tests** — either implement or delete
- **CI compatibility** — no hardcoded paths or environment-specific values
