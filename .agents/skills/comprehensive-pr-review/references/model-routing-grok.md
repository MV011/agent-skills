# Grok / xAI Model Routing

**Read this file when review leaves run on an xAI / Grok runtime.**

## Tier → model mapping (Grok 3 lineup, current as of September 2026)

| Tier | Model ID | Effort / Thinking | Role | Key constraints |
|---|---|---|---|---|
| `cheap` | `grok-3-mini` | `low` | Triage, patch application, mechanical checks | Fast, lightweight reasoning |
| `standard` | `grok-3` | `medium` | Most review dimensions | High general reasoning across code patterns |
| `strong` | `grok-3` | `high` | Coordinator, adjudication, universal fallback | Extended thinking for cross-shard analysis and arbitration |
| `deep` | `grok-3-deepsearch` | `high` | Risk-surface (security/migration) review | Extended reasoning with deep search / verification pass |

## Hard rules

1. **Escalation ladder (one rung at a time):** grok-3-mini low → grok-3-mini high → grok-3 medium → grok-3 high → grok-3-deepsearch.
2. **Fallback:** If deepsearch or extended thinking fails, rate-limits, or times out, fall back to `grok-3` (effort `high`).
3. **Refusal handling:** Tag retried findings `degraded: true` with the producing model recorded in the findings table.
