# Scoring: Playwright / E2E API Tests

| Dimension | Weight | What to Check |
|-----------|--------|---------------|
| **Assertion Strength** | 30 pts | Does the test check VALUES not just existence? Typed responses vs `as any`? Would a broken API still pass? |
| **Data Reliability** | 25 pts | Real fixtures, real API flows, no DB hacking? Correct fixture selection for baseline-sensitive tests? |
| **False Positive Resistance** | 20 pts | Could this pass with the feature removed? Does the test distinguish denial from "not found" instead of accepting both? Response body leak checks? |
| **Isolation & Cleanup** | 15 pts | No shared mutable state between tests? afterEach cleanup? Parallel-safe with other files? Fixture-per-concern for rule-based tests? |
| **Error Path Coverage** | 10 pts | Does it test denial/rejection/validation paths, not just happy paths? Are error response bodies asserted? |

## Detailed scoring rubric

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

## Anti-patterns

- **`as any` on response data** — hides type mismatches, use typed response interfaces
- **Module-level state loading** — runs at import time before fixtures, then fails or falls back too early
- **`test.skip` inside `test.fixme`** — dead code, fixme prevents body execution
- **Multi-status success criteria** — treating more than one materially different HTTP status as "good enough" without checking which contract is correct
- **Broad rules without resource-id guards** — wide predicates can match unrelated records and interfere with concurrent tests
- **Same fixture for all test files** — rule-creating files need separate fixtures for parallel safety
- **Scope header where not needed** — optional scope headers should not be required for tests that do not exercise impersonation or context switching
- **Hard waits (`page.waitForTimeout`, sleeps)** — race-prone; use web-first assertions / event waits (see Determinism, SKILL.md)
- **Retry-masked flakiness** — a test that only passes with `retries > 0` is a flaky test with a bandage; score it as flaky

## Checklist

- **Data**: real fixtures (minimal pre-existing rules for baseline-sensitive tests), real API flows, dynamic related-record creation
- **Parallelism**: fixture-per-concern for rule files, `fullyParallel: false` for file-level isolation
- **Assertions**: typed responses (not `as any`), value checks (not just existence), data leak checks on denials
- **State**: `test.beforeAll` for state reads (not module level), proper afterEach rule cleanup
- **Setup**: setup projects for one-time resources (credentials), consolidate don't duplicate
- **Determinism**: no hard waits; selectors resilient to reordering; no dependence on wall-clock time or run order

## Worked examples

### 75/100 — Solid but Weak Assertions
```text
Assertion Strength: 15/30 (status + existence checks, but 30x `as any` casts)
Data Reliability: 20/25 (real fixtures, but pre-existing rules on the fixture cause false failures)
False Positive Resistance: 15/20 ([403,404] doesn't distinguish denial from generic 404)
Isolation: 15/15 (separate fixtures, afterEach cleanup, parallel-safe)
Error Path: 10/10 (denial, rejection, validation all tested)
```
Improvements: 1) Add typed response interfaces 2) Switch to a low-noise fixture 3) Pin denial status codes

### 35/100 — Near No-Op
```text
Assertion Strength: 5/30 (accepts both 200 and 404 as success — effectively untestable)
Data Reliability: 10/25 (real fixture but no content validation on response)
False Positive Resistance: 0/20 (test literally cannot fail unless server 500s)
Isolation: 15/15 (no mutable state)
Error Path: 5/10 (one non-existent fixture test)
```
This test would pass if the endpoint returned garbage. Needs XML validation on 200, fixed expectations on 404.

### Ambiguous Assertion — Needs Pinning
```text
Status check: 5/20 (`expect([200, 404]).toContain(status)` accepts two incompatible outcomes)
Body check: 5/20 (asserts XML only if status is 200, so the 404 branch stays unverified)
Total signal: low
```
Improvement: read the implementation or contract, determine the real expected outcome, and pin the test to that single verified behavior.
