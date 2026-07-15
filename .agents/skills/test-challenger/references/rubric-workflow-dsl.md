# Scoring: Declarative Workflow / DSL Tests

| Dimension | Weight | What to Check |
|-----------|--------|---------------|
| **Path Completeness** | 30 pts | Does the test cover the full expected path through the workflow or decision graph? |
| **Negative Branch Assertions** | 20 pts | Does the test block wrong branches or forbidden outcomes instead of only asserting the happy path? |
| **Intermediate Output Validation** | 20 pts | Does it check meaningful state/output data at key decision points, not just the final outcome? |
| **Child/Subflow Verification** | 15 pts | Are nested flows, spawned jobs, or child executions asserted with enough specificity to catch duplicates or omissions? |
| **Error Specificity** | 15 pts | Does it trace the exact error chain, not just "outcome: failed"? |

## Detailed scoring rubric

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

## Anti-patterns

- **Loose path matching without wrong-branch guards** — the test passes regardless of which branch executed
- **Asserting only the terminal state** — tells you nothing about the actual path taken
- **Missing child/subflow occurrence checks** — duplicate or missing nested executions go undetected
- **Asserting mocked behavior only** — mocked responses prove little about production behavior

## Checklist

- Are environment-specific steps properly guarded?
- If the framework allows loose path matching, is it paired with explicit wrong-branch assertions? (CRITICAL)
- Cleanup steps run for both success and failure?
- `${uuid}` / `${timestamp}` for isolation?

## Environment notes (workflow systems)

- Locally synthesized execution graphs may differ from deployed runtime graphs when environment-specific transforms are applied
- Mock-based failure scenarios may only exist in local environments
- Tests passing locally should be verified in the target runtime when possible

## Worked example: 84/100 — Good but Missing Output Validation

```text
Flow: 28/30 (covers all states)
Negative: 18/20 (blocks 12 wrong-path states)
Output: 8/20 (only checks a summary value, not downstream result data)
Child: 15/15 (child/subflow checks include occurrence counts)
Error: 15/15 (exact error chain asserted)
```
Improvement: Add intermediate output assertions for workflow result data.
