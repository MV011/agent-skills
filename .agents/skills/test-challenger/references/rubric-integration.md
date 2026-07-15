# Scoring: Integration Tests (Containerized / Multi-Service)

Integration tests that run through a chain of real services (API → service → provider or mock boundary) have unique failure modes that unit tests and E2E tests don't share. The core question is: **does the test prove the integration works, or does it only prove one layer works?**

| Dimension | Weight | What to Check |
|-----------|--------|---------------|
| **Service Chain Coverage** | 25 pts | Does the request actually traverse the full chain? Or does it get rejected at an early layer (auth, validation) and never test the integration? |
| **Auth/Permission Setup** | 25 pts | Are custom tokens backed by matching DB records? Does the test actually reach the permission check, or does auth fail first (401 vs 403)? |
| **Contract Verification** | 20 pts | Does the test verify the consumer's request format is accepted by the provider? Would a provider API change break these tests (it should)? |
| **Assertion Depth** | 15 pts | Beyond status codes — are response shapes, field types, key numeric values, and IDs validated? |
| **Cascade Awareness** | 15 pts | Are lifecycle chains (create→process→fetch) structured so step 1 failure is clearly the root cause, not N separate failures? |

## Detailed scoring rubric

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

## Anti-patterns

- **Custom tokens without DB records** — generating custom auth tokens with random client claims but no matching credential record in the database. Auth middleware returns 401 before permission checking runs, so the test thinks it's testing permissions but it's actually testing that auth rejects unknown clients. Fix: create a matching credential record for each token variant using the same helper path used by known-good auth tests.
- **Multiple fixture instances for permission variants** — running separate setup flows for each permission variant can create different users with different resources. Permission tests then reference data from user A while authenticating as user B. Tests pass accidentally if the permission check fires before the ownership check. Fix: run one setup flow, then create custom tokens for the same user with different permission claims.
- **Testing validation as integration** — if all your "passing" tests only exercise the consumer's schema validation (status 400 for bad input) and never reach the downstream service, you haven't tested the integration at all. Check: do any happy-path tests actually get a response from the provider service?
- **Assuming error body shapes** — asserting `resp.data.message || resp.data.error` when the framework might return empty `{}` for validation errors. Different layers (Fastify, Express, custom middleware) return different error shapes. Fix: only assert what you've verified the API actually returns.
- **Lifecycle chain as separate tests** — a create→process→fetch chain where steps 2-4 each independently fail when step 1 fails creates noise. Reviewers see "4 failures" when there's really 1 root cause. Fix: guard later steps with `expect(previousResult).toBeDefined()` so the root cause is immediately clear.
- **Provider branch mismatch** — in local containerized environments, if the provider service is built from a feature branch with different routes/API than what the consumer expects, every integration test fails with generic 404/500. This looks like a test bug but it's a configuration issue. Fix: verify the provider service branch exposes the routes the consumer adapter calls.
- **Query param type coercion** — HTTP query parameters are always strings. If the provider validates a query flag as a native boolean without coercion, it may reject the string form unexpectedly. This is a real integration bug the tests should catch, not a test bug. The consumer contract is the source of truth.

## Checklist

- **Auth setup**: Custom tokens backed by DB credentials? Same user for permission variants (not separate flow instances)?
- **Service chain**: Do happy-path tests actually reach the downstream provider? Or do they only exercise the consumer's validation layer?
- **Contract**: Would a provider API change (route rename, param type change) be caught by these tests?
- **Provider stubs**: Return realistic responses (proper field names, types, numeric values)? No templates that break JSON serialization?
- **Cascade**: Lifecycle chains guard later steps with `expect(previousResult).toBeDefined()`?
- **Branch alignment**: Provider service built from a branch that matches what the consumer expects?

## Worked example: 45/100 → 82/100 — Auth Setup Was Testing Wrong Thing

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
