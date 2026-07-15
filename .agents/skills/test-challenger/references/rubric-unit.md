# Scoring: Unit Tests (Jest / Vitest / NUnit / xUnit / pytest / go test)

The dimensions are language-agnostic; the idiom notes below map them onto each ecosystem.

| Dimension | Weight | What to Check |
|-----------|--------|---------------|
| **Behavior Coverage** | 30 pts | Are all code paths tested? Branches, edge cases, error throws? |
| **Assertion Quality** | 25 pts | Testing behavior not implementation? Meaningful assertions vs snapshot dumps? |
| **Mock Discipline** | 20 pts | Mocking at the right boundary? Not testing the mock itself? |
| **Isolation** | 15 pts | No shared state? Proper setup/teardown? |
| **Edge Cases** | 10 pts | null, undefined/None/default, empty collections, boundary values, concurrent access? |

## Checklist (all ecosystems)

- Arrange-Act-Assert structure? Mock boundaries correct? No over-mocking?
- Teardown for side effects? No shared mutable state between tests?
- Edge cases tested? Descriptive test names?
- Deterministic: no wall-clock (`Date.now`, `DateTime.Now`) without a clock abstraction; no dependence on test execution order; no real network/filesystem unless that IS the boundary under test.

## Ecosystem idiom notes

**Jest / Vitest (TypeScript/JavaScript)**
- `afterEach`/`afterAll` for side effects; `vi.restoreAllMocks()`/`jest.restoreAllMocks()` between tests
- Snapshot tests count toward Assertion Quality only when the snapshot is small and reviewed; a 300-line snapshot dump is a 0-signal assertion
- Fake timers (`vi.useFakeTimers`) for time-dependent logic — never `setTimeout` sleeps

**NUnit / xUnit (.NET)**
- NUnit: `[SetUp]`/`[TearDown]`, `Assert.Multiple` for related assertions, `Assert.ThrowsAsync` for error paths (never `try/catch` + `Assert.Fail`)
- xUnit: constructor/`IDisposable` (or `IAsyncLifetime`) is the isolation unit; class fixtures (`IClassFixture<>`) are shared state — score them as such
- `[TestCase]`/`[Theory]+[InlineData]` for boundary matrices instead of copy-pasted tests
- Async traps: `async void` test methods silently swallow failures — must be `async Task`. Un-awaited tasks pass vacuously.
- Time: inject `TimeProvider` (or a clock interface) — direct `DateTime.Now`/`UtcNow` in tested code paths makes tests time-of-day dependent
- EF Core: in-memory provider diverges from real SQL (no relational constraints, different LINQ translation) — treat "unit tests" that assert query behavior against the in-memory provider as weak evidence; relational behavior belongs in integration tests

**pytest (Python)**
- Fixtures with proper scope (`function` default; wider scopes are shared state — score as such)
- `pytest.raises` with `match=` for error paths; parametrize for boundary matrices
- `freezegun`/`time-machine` for time; `monkeypatch` at the right boundary

**go test**
- Table-driven tests for boundary matrices; `t.Cleanup` for teardown; `t.Parallel` only when actually parallel-safe
- Interfaces + hand-rolled fakes at the boundary; avoid asserting on internal call order
