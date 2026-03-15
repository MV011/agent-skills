---
name: test-challenger
description: Analyze and rate test scenarios for quality, completeness, and reliability. Use when writing, reviewing, or improving ANY type of test — declarative workflow tests, Playwright E2E/API tests, Jest or Vitest unit/integration tests, containerized multi-service integration tests, or any other framework. Triggers on "challenge tests", "rate tests", "review test quality", "are our tests good", "grade the tests", or any test quality discussion. Also use proactively after writing or modifying test code. For custom or unfamiliar frameworks, first read that framework's docs, local helpers, and example tests, then apply the generic scoring dimensions below.
tools: Read, Bash, Glob, Grep
---

# Test Challenger

Follow the portable skill definition below as the primary workflow for this task.
Adapt it only when Claude Code's tool surface or the current repository requires a direct translation.

# Test Challenger

Rate test scenarios on quality dimensions, identify false positives and gaps, and suggest concrete improvements. Works across testing frameworks by combining universal test-quality rules with framework-specific checks.

## When to Use

- After writing or updating test code (any framework)
- Before committing test changes
- When reviewing a PR that includes tests
- When the user asks to "challenge", "rate", or "grade" tests
- Proactively after any chunk of test work
- When tests are failing and you need to determine if the test or the system is wrong

## Process

### Step 1: Detect Framework and Read the Test

Read the test file completely. Detect the framework:
- **Playwright-style tests** → Browser or API E2E/integration test
- **Jest or Vitest-style tests** → Unit or integration test
- **Containerized end-to-end flows** → Multi-service integration test
- **k6-style files** → Performance test
- **Declarative YAML/JSON/DSL tests** → Workflow/path scenario test
- **Anything custom or unfamiliar** → Custom framework; treat it as unknown until you've read its docs and local examples

Then understand:
- What system/API/feature does it target?
- What specific path/behavior does it test?
- What input triggers this path?
- What is the expected outcome?

For common public frameworks, apply the framework patterns below.

For a custom or unfamiliar framework:
- Read the framework docs or local reference material first.
- Inspect helper functions, assertion primitives, and example tests in the repo.
- Translate the generic scoring dimensions into that framework's equivalents rather than assuming familiar matcher names.
- If the framework has its own concepts for path coverage, child execution, snapshots, fixtures, retries, or error assertions, use those terms in the review.

### Step 2: Read the Source of Truth

The test assertions must match **reality**, not assumptions.

- **Declarative workflow/DSL tests**: Read the workflow definition, execution graph, or framework docs. Trace the exact path.
- **API tests**: Read the route handler code. Understand what the endpoint actually returns for this input. Check if the test's expected status codes and response shapes match the real API.
- **Unit tests**: Read the function under test. Trace the execution path.
- **Verify the test data**: Is the test fixture/data chosen for the RIGHT reasons (minimal pre-existing rules, correct permissions, realistic related records)? Or just because it was convenient?

### Step 3: Apply Universal Checks

Before using any framework-specific rubric, check these universal questions:

| Universal Check | What to Ask |
|-----------------|-------------|
| **Behavior Coverage** | Does the test prove the intended behavior, not just that code ran? |
| **False Positive Resistance** | Would the test still pass if the feature were broken, bypassed, or stubbed incorrectly? |
| **Ambiguity Elimination** | Does the test pin one correct outcome instead of accepting multiple incompatible outcomes? |
| **Source-of-Truth Alignment** | Do assertions match the real implementation, contract, or workflow definition? |
| **Data & Fixture Quality** | Are fixtures realistic, purposeful, and isolated enough to support the claim? |
| **Failure Clarity** | If the test fails, does it make the root cause obvious? |

If a test is weak on these universal checks, call that out even if the framework-specific mechanics look correct.

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

### Step 4: Rate on Framework-Specific Dimensions

**Choose the scoring guide that matches the framework.** The dimensions are intentionally different because different frameworks have different failure modes.

---

#### Scoring: Declarative Workflow / DSL Tests

| Dimension | Weight | What to Check |
|-----------|--------|---------------|
| **Path Completeness** | 30 pts | Does the test cover the full expected path through the workflow or decision graph? |
| **Negative Branch Assertions** | 20 pts | Does the test block wrong branches or forbidden outcomes instead of only asserting the happy path? |
| **Intermediate Output Validation** | 20 pts | Does it check meaningful state/output data at key decision points, not just the final outcome? |
| **Child/Subflow Verification** | 15 pts | Are nested flows, spawned jobs, or child executions asserted with enough specificity to catch duplicates or omissions? |
| **Error Specificity** | 15 pts | Does it trace the exact error chain, not just "outcome: failed"? |

<details>
<summary>Detailed scoring rubric (click to expand)</summary>

**Path Completeness (0-30):**
- 0: No meaningful path assertion
- 10: Path assertion covers <50% of executed states
- 20: 50-80% coverage
- 25: 80-95% coverage
- 30: ALL executed states covered

**Negative Branch Assertions (0-20):**
- 0: No wrong-branch or forbidden-outcome assertion
- 10: Covers obvious wrong paths
- 20: Covers all alternative branches AND terminal error states

**Intermediate Output Validation (0-20):**
- 0: No intermediate output/state checks
- 10: 1-2 key states checked
- 20: All key decision points + persisted-state verification

**Child/Subflow Verification (0-15):**
- 0: Children invoked but not asserted
- 10: Child/subflow outcomes asserted for all
- 15: Child/subflow outcomes asserted with occurrence/count checks
- N/A (15): No children invoked

**Error Specificity (0-15):**
- 0: No outcome assertion
- 10: Failure outcome + specific error states in path
- 15: Exact error chain + error-data assertions
- N/A (15): Happy path with a clear outcome assertion

</details>

---

#### Scoring: Playwright / E2E API Tests

| Dimension | Weight | What to Check |
|-----------|--------|---------------|
| **Assertion Strength** | 30 pts | Does the test check VALUES not just existence? Typed responses vs `as any`? Would a broken API still pass? |
| **Data Reliability** | 25 pts | Real fixtures, real API flows, no DB hacking? Correct fixture selection for baseline-sensitive tests? |
| **False Positive Resistance** | 20 pts | Could this pass with the feature removed? Does the test distinguish denial from "not found" instead of accepting both? Response body leak checks? |
| **Isolation & Cleanup** | 15 pts | No shared mutable state between tests? afterEach cleanup? Parallel-safe with other files? Fixture-per-concern for rule-based tests? |
| **Error Path Coverage** | 10 pts | Does it test denial/rejection/validation paths, not just happy paths? Are error response bodies asserted? |

<details>
<summary>Detailed scoring rubric (click to expand)</summary>

**Assertion Strength (0-30):**
- 0: Status code only (`expect(status).toBe(200)`)
- 10: Status + existence checks (`toHaveProperty`)
- 15: Status + value checks on 1-2 fields
- 20: Typed response interface, multiple value checks
- 25: Typed responses, value checks, negative leak checks
- 30: Full typed responses, value + type + range checks, compile-time safety via generics

**Data Reliability (0-25):**
- 0: Hardcoded fake data, DB-seeded credentials, wrong fixture
- 10: Real fixtures but wrong properties (e.g., a fixture with lots of pre-existing rules for a clean-baseline assertion)
- 15: Correct fixture selection, but some data created via DB hacking
- 20: Real fixtures, real API flows for data creation, proper fixture properties
- 25: All data through real flows, fixture chosen for specific properties, related records created through the public API

**False Positive Resistance (0-20):**
- 0: Test passes with feature completely removed (e.g., `[403, 404]` matches generic 404)
- 5: Status code check only, no body validation
- 10: Status + basic body check, but ambiguous (accepts multiple unrelated failure modes)
- 15: Specific status + body value checks, but could still pass with wrong error
- 20: Pinned status code + specific error code/message + data leak checks (`body.internalId` undefined)

**Isolation & Cleanup (0-15):**
- 0: Shared mutable state, no cleanup, module-level state loading with silent fallback
- 5: Some cleanup but missed cases (orphan rules from crashed runs)
- 10: afterEach cleanup, but cross-file interference possible (broad rules on a shared fixture)
- 15: Full cleanup, fixture isolation, `test.beforeAll` for state reads with proper error throwing

**Error Path Coverage (0-10):**
- 0: Happy path only
- 5: One error case (e.g., 404 for non-existent resource)
- 10: Multiple error paths tested — denial, rejection, validation, scope enforcement

</details>

---

#### Scoring: Integration Tests (Containerized / Multi-Service)

Integration tests that run through a chain of real services (API → service → provider or mock boundary) have unique failure modes that unit tests and E2E tests don't share. The core question is: **does the test prove the integration works, or does it only prove one layer works?**

| Dimension | Weight | What to Check |
|-----------|--------|---------------|
| **Service Chain Coverage** | 25 pts | Does the request actually traverse the full chain? Or does it get rejected at an early layer (auth, validation) and never test the integration? |
| **Auth/Permission Setup** | 25 pts | Are custom tokens backed by matching DB records? Does the test actually reach the permission check, or does auth fail first (401 vs 403)? |
| **Contract Verification** | 20 pts | Does the test verify the consumer's request format is accepted by the provider? Would a provider API change break these tests (it should)? |
| **Assertion Depth** | 15 pts | Beyond status codes — are response shapes, field types, key numeric values, and IDs validated? |
| **Cascade Awareness** | 15 pts | Are lifecycle chains (create→process→fetch) structured so step 1 failure is clearly the root cause, not N separate failures? |

<details>
<summary>Detailed scoring rubric (click to expand)</summary>

**Service Chain Coverage (0-25):**
- 0: All assertions pass before the request reaches the downstream service (validation-only tests masquerading as integration tests)
- 10: Request reaches the immediate downstream service but not the full chain
- 20: Request traverses the full chain with real services (no mocking of internal services)
- 25: Full chain + realistic provider stubs return realistic responses (not empty `{}`)

**Auth/Permission Setup (0-25):**
- 0: Custom tokens with random client claims that don't exist in the DB — auth fails before permission check runs, test passes for the wrong reason
- 10: Tokens reuse existing flow-generated credentials but don't test permission variants
- 15: Permission variants tested but by running separate fixture instances (creates different USERS, not different permissions for same user)
- 20: Client credentials created in DB for each permission variant, same user, different token permission claims
- 25: Full matrix — same user with read-only, write-only, no-permission, and full-permission tokens, all backed by DB credentials

**Contract Verification (0-20):**
- 0: Test only checks the consumer layer's validation (schema checks, auth) — never actually calls the provider
- 10: Test calls the provider but doesn't verify the provider accepts the consumer's exact request format (method, path params, query param types)
- 15: Test verifies the happy path works end-to-end but doesn't catch type mismatches (e.g., string vs boolean query params)
- 20: Test would break if the provider changed its API — catches method mismatches, route changes, query param type coercion issues

**Assertion Depth (0-15):**
- 0: Status code only
- 5: Status + `data.operation` or similar top-level field
- 10: Status + response shape + key field values (numeric fields > 0, references match)
- 15: Full response validation — field types, numeric consistency, IDs are non-empty strings, timestamps are valid ISO

**Cascade Awareness (0-15):**
- 0: Lifecycle tests (create→process→fetch) report N separate failures when step 1 fails — confusing noise
- 10: Later steps check `expect(previousStepResult).toBeDefined()` to fail fast with a clear message
- 15: Steps are structured so root cause is immediately obvious — either sequential with guards, or the describe block is skipped if setup fails

</details>

---

#### Scoring: Jest / Vitest Unit Tests

| Dimension | Weight | What to Check |
|-----------|--------|---------------|
| **Behavior Coverage** | 30 pts | Are all code paths tested? Branches, edge cases, error throws? |
| **Assertion Quality** | 25 pts | Testing behavior not implementation? Meaningful assertions vs snapshot dumps? |
| **Mock Discipline** | 20 pts | Mocking at the right boundary? Not testing the mock itself? |
| **Isolation** | 15 pts | No shared state? Proper setup/teardown? |
| **Edge Cases** | 10 pts | null, undefined, empty arrays, boundary values, concurrent access? |

#### Scoring: Custom / Unfamiliar Frameworks

If the test framework is custom, repo-local, or unfamiliar, do not invent framework mechanics from memory. First read its docs and examples, then score it using these dimensions:

| Dimension | Weight | What to Check |
|-----------|--------|---------------|
| **Framework Semantics Fit** | 25 pts | Are you using the framework's own assertion/fixture semantics correctly? |
| **Behavior Coverage** | 25 pts | Does the test cover the intended paths, states, or behaviors this framework is meant to express? |
| **False Positive Resistance** | 20 pts | Could framework defaults, loose matching, or implicit retries hide a broken feature? |
| **Data & Isolation** | 15 pts | Are fixtures/setup/cleanup correct for how the framework manages test state? |
| **Failure Clarity** | 15 pts | Would a failure be diagnosable to someone who knows the framework? |

When reporting on a custom framework, name the framework-specific primitives you found in its docs or examples and explain how they map to the generic dimensions.

### Step 5: Calculate Score and Report

Output a table with the framework-appropriate dimensions:

```text
| Dimension | Score | Max | Notes |
|-----------|-------|-----|-------|
| [dim 1] | X | XX | [what's missing] |
| [dim 2] | X | XX | [what's missing] |
| ...
| **TOTAL** | **X** | **100** | |
```

Then list **specific improvements** ordered by impact.

### Step 6: Fix (if asked)

- Apply improvements in order of impact
- Re-run tests to verify they still pass
- Re-rate to confirm improvement

## Anti-Patterns to Flag

### Universal Anti-Patterns
- **Test passes with broken feature** — the most critical failure. Always ask: "if I deleted the feature, would this still pass?"
- **Existence checks without value checks** — `toHaveProperty('field')` passes when `field: null`. Check actual values.
- **Ambiguous acceptance windows** — accepting multiple incompatible outcomes like `[200, 404]`, `[400, 404]`, or multiple unrelated error shapes without proving the contract allows them.
- **Silent fallbacks** — silently coercing missing state into an empty string or default value. Throw clearly instead.
- **No cleanup** — created data (rules, related records, auth credentials) left in dev environment. Large piles of orphaned integration-test records are a real failure mode.
- **Testing through DB hacks** — if there's a real API/UI flow, use it. DB-seeded data may not match reality.
- **Hardcoded environment data** — test fixtures chosen for convenience, not properties. A fixture with lots of pre-existing automation or records will break tests that expect a clean baseline.

### Integration Test Anti-Patterns
- **Custom tokens without DB records** — generating custom auth tokens with random client claims but no matching credential record in the database. Auth middleware returns 401 before permission checking runs, so the test thinks it's testing permissions but it's actually testing that auth rejects unknown clients. Fix: create a matching credential record for each token variant using the same helper path used by known-good auth tests.
- **Multiple fixture instances for permission variants** — running separate setup flows for each permission variant can create different users with different resources. Permission tests then reference data from user A while authenticating as user B. Tests pass accidentally if the permission check fires before the ownership check. Fix: run one setup flow, then create custom tokens for the same user with different permission claims.
- **Testing validation as integration** — if all your "passing" tests only exercise the consumer's schema validation (status 400 for bad input) and never reach the downstream service, you haven't tested the integration at all. Check: do any happy-path tests actually get a response from the provider service?
- **Assuming error body shapes** — asserting `resp.data.message || resp.data.error` when the framework might return empty `{}` for validation errors. Different layers (Fastify, Express, custom middleware) return different error shapes. Fix: only assert what you've verified the API actually returns.
- **Lifecycle chain as separate tests** — a create→process→fetch chain where steps 2-4 each independently fail when step 1 fails creates noise. Reviewers see "4 failures" when there's really 1 root cause. Fix: guard later steps with `expect(previousResult).toBeDefined()` so the root cause is immediately clear.
- **Provider branch mismatch** — in local containerized environments, if the provider service is built from a feature branch with different routes/API than what the consumer expects, every integration test fails with generic 404/500. This looks like a test bug but it's a configuration issue. Fix: verify the provider service branch exposes the routes the consumer adapter calls.
- **Query param type coercion** — HTTP query parameters are always strings. If the provider validates a query flag as a native boolean without coercion, it may reject the string form unexpectedly. This is a real integration bug the tests should catch, not a test bug. The consumer contract is the source of truth.

### Declarative Workflow / DSL Anti-Patterns
- **Loose path matching without wrong-branch guards** — the test passes regardless of which branch executed
- **Asserting only the terminal state** — tells you nothing about the actual path taken
- **Missing child/subflow occurrence checks** — duplicate or missing nested executions go undetected
- **Asserting mocked behavior only** — mocked responses prove little about production behavior

### Playwright / E2E Anti-Patterns
- **`as any` on response data** — hides type mismatches, use typed response interfaces
- **Module-level state loading** — runs at import time before fixtures, then fails or falls back too early
- **`test.skip` inside `test.fixme`** — dead code, fixme prevents body execution
- **Multi-status success criteria** — treating more than one materially different HTTP status as "good enough" without checking which contract is correct
- **Broad rules without resource-id guards** — wide predicates can match unrelated records and interfere with concurrent tests
- **Same fixture for all test files** — rule-creating files need separate fixtures for parallel safety
- **Scope header where not needed** — optional scope headers should not be required for tests that do not exercise impersonation or context switching

## Environment Considerations

### Dev Environment Awareness
- **Pre-existing data** — dev environments often have workflow rules, existing records, and orphaned test artifacts
- **Fixture selection** — verify the fixture has the right properties (minimal pre-existing rules, correct permissions, valid test prerequisites, existing related records)
- **Orphan cleanup** — check for stale E2E rules/records from previous crashed runs

### Local vs Remote Runtime (Workflow Systems)
- Locally synthesized execution graphs may differ from deployed runtime graphs when environment-specific transforms are applied
- Mock-based failure scenarios may only exist in local environments
- Tests passing locally should be verified in the target runtime when possible

### Real Flows vs DB Hacking
- **Use real flows for**: auth credentials (real auth flow), related records (real write API), user links (real integration endpoint)
- **DB seeding OK for**: workflow rules, resource restrictions, and baseline test data that has no real user-facing creation flow

## Framework-Specific Checklists

### Declarative Workflow / DSL Tests
- Are environment-specific steps properly guarded?
- If the framework allows loose path matching, is it paired with explicit wrong-branch assertions? (CRITICAL)
- Cleanup steps run for both success and failure?
- `${uuid}` / `${timestamp}` for isolation?

### Playwright / E2E API Tests
- **Data**: real fixtures (minimal pre-existing rules for baseline-sensitive tests), real API flows, dynamic related-record creation
- **Parallelism**: fixture-per-concern for rule files, `fullyParallel: false` for file-level isolation
- **Assertions**: typed responses (not `as any`), value checks (not just existence), data leak checks on denials
- **State**: `test.beforeAll` for state reads (not module level), proper afterEach rule cleanup
- **Setup**: setup projects for one-time resources (credentials), consolidate don't duplicate

### Integration Tests (Containerized / Multi-Service)
- **Auth setup**: Custom tokens backed by DB credentials? Same user for permission variants (not separate flow instances)?
- **Service chain**: Do happy-path tests actually reach the downstream provider? Or do they only exercise the consumer's validation layer?
- **Contract**: Would a provider API change (route rename, param type change) be caught by these tests?
- **Provider stubs**: Return realistic responses (proper field names, types, numeric values)? No templates that break JSON serialization?
- **Cascade**: Lifecycle chains guard later steps with `expect(previousResult).toBeDefined()`?
- **Branch alignment**: Provider service built from a branch that matches what the consumer expects?

### Jest / Vitest
- Arrange-Act-Assert structure? Mock boundaries correct? No over-mocking?
- `afterEach`/`afterAll` for side effects? No shared mutable state?
- Edge cases tested? Descriptive test names?

## Code Quality Checks

When test source code is available:
- **Type safety** — TypeScript tests should use proper types, not `any`. Response types should be explicit interfaces.
- **DRY within reason** — extract repeated patterns (resource submission, rule cleanup, denial assertions) into helpers
- **Consistent patterns** — follows the same structure as other tests in the project
- **No commented-out or placeholder tests** — either implement or delete
- **CI compatibility** — no hardcoded paths or environment-specific values

## Examples

### Workflow DSL: 84/100 — Good but Missing Output Validation
```text
Flow: 28/30 (covers all states)
Negative: 18/20 (blocks 12 wrong-path states)
Output: 8/20 (only checks a summary value, not downstream result data)
Child: 15/15 (child/subflow checks include occurrence counts)
Error: 15/15 (exact error chain asserted)
```
Improvement: Add intermediate output assertions for workflow result data.

### Playwright API: 75/100 — Solid but Weak Assertions
```text
Assertion Strength: 15/30 (status + existence checks, but 30x `as any` casts)
Data Reliability: 20/25 (real fixtures, but pre-existing rules on the fixture cause false failures)
False Positive Resistance: 15/20 ([403,404] doesn't distinguish denial from generic 404)
Isolation: 15/15 (separate fixtures, afterEach cleanup, parallel-safe)
Error Path: 10/10 (denial, rejection, validation all tested)
```
Improvements: 1) Add typed response interfaces 2) Switch to a low-noise fixture 3) Pin denial status codes

### Playwright API: 35/100 — Near No-Op
```text
Assertion Strength: 5/30 (accepts both 200 and 404 as success — effectively untestable)
Data Reliability: 10/25 (real fixture but no content validation on response)
False Positive Resistance: 0/20 (test literally cannot fail unless server 500s)
Isolation: 15/15 (no mutable state)
Error Path: 5/10 (one non-existent fixture test)
```
This test would pass if the endpoint returned garbage. Needs XML validation on 200, fixed expectations on 404.

### Ambiguous Assertion Example — Needs Pinning
```text
Status check: 5/20 (`expect([200, 404]).toContain(status)` accepts two incompatible outcomes)
Body check: 5/20 (asserts XML only if status is 200, so the 404 branch stays unverified)
Total signal: low
```
Improvement: read the implementation or contract, determine the real expected outcome, and pin the test to that single verified behavior.

### Integration Test: 45/100 → 82/100 — Auth Setup Was Testing Wrong Thing

**Before (45/100):**
```text
Service Chain: 10/25 (validation tests pass, but happy paths all 500 — never actually tested the integration)
Auth/Permission: 0/25 (3 separate flow instances = 3 different users; custom tokens with random client claims = 401 not 403)
Contract: 0/20 (downstream schema bug rejects the consumer's query params — tests expose it, but the suite is not structured to distinguish test bug vs real bug)
Assertion Depth: 15/15 (strong assertions on happy paths, but none could run)
Cascade: 5/15 (lifecycle chain reported 4 failures for 1 root cause)
```

**After fixing auth setup (82/100):**
```text
Service Chain: 20/25 (full chain works when provider bug is fixed; 10 tests blocked by 1 known downstream bug)
Auth/Permission: 20/25 (single flow, client credentials created per permission variant, same user with different permission claims)
Contract: 20/20 (tests correctly surface a downstream schema bug — the consumer contract is the source of truth)
Assertion Depth: 12/15 (numeric fields > 0, references match, record ID non-empty, status in expected enum)
Cascade: 10/15 (lifecycle steps 2-4 guard with `expect(initialStepId).toBeDefined()`)
```
Takeaway: A large score jump after fixing setup usually means the original suite was exercising the wrong layer or failing too early to validate the real integration.
