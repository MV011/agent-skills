# Scoring: Custom / Unfamiliar Frameworks & Performance Tests

## Custom / unfamiliar frameworks

If the test framework is custom, repo-local, or unfamiliar, do not invent framework mechanics from memory. First read its docs and examples, then score it using these dimensions:

| Dimension | Weight | What to Check |
|-----------|--------|---------------|
| **Framework Semantics Fit** | 25 pts | Are you using the framework's own assertion/fixture semantics correctly? |
| **Behavior Coverage** | 25 pts | Does the test cover the intended paths, states, or behaviors this framework is meant to express? |
| **False Positive Resistance** | 20 pts | Could framework defaults, loose matching, or implicit retries hide a broken feature? |
| **Data & Isolation** | 15 pts | Are fixtures/setup/cleanup correct for how the framework manages test state? |
| **Failure Clarity** | 15 pts | Would a failure be diagnosable to someone who knows the framework? |

When reporting on a custom framework, name the framework-specific primitives you found in its docs or examples and explain how they map to the generic dimensions.

## Performance tests (k6 / Gatling / Locust / JMeter)

Performance tests use the custom-framework dimensions with these interpretations:

| Dimension | Performance interpretation |
|---|---|
| **Framework Semantics Fit** (25) | Load model matches the claim being made: closed vs open model (`constant-vus` vs `constant-arrival-rate` in k6), ramping stages, realistic think time. A "load test" with 1 VU is a smoke test — say so. |
| **Behavior Coverage** (25) | The scenario exercises the real user journey (auth → browse → act), not one cherry-picked cheap endpoint. Payloads vary (data parameterization), not one cached request repeated. |
| **False Positive Resistance** (20) | **`thresholds` are defined and fail the run** — recording `http_req_duration` without a threshold means the test cannot fail on regression. k6 `check()`s are recorded-but-non-failing by default: verify checks feed a threshold (e.g. `checks: ['rate>0.99']`) or abort logic. A perf test with no thresholds is a dashboard, not a test. |
| **Data & Isolation** (15) | Test data setup/teardown at scale (does the run leave 50k orphan records?); environment pinned and stated (perf numbers from a laptop against a shared dev DB are noise); no cross-run contamination. |
| **Failure Clarity** (15) | Failing threshold names the metric, percentile, and endpoint (per-URL tags/groups), not one aggregate number across all routes. |

Perf-specific anti-patterns:
- **Thresholdless metrics** — the run "passes" at any latency
- **Checks without threshold wiring** (k6) — failed checks don't fail the run by default
- **Unrealistic load model** — constant VUs asserting arrival-rate claims, no ramp-up, zero think time
- **Aggregate-only percentiles** — one slow endpoint hides behind the average of fast ones
- **Environment-blind runs** — no record of target env, dataset size, or concurrent noise
