# Grok / xAI Model Routing

**Read this file when review leaves run on an xAI / Grok runtime.**

## Tier → model mapping (current as of September 2026)

Currently, **Grok 4.6** is the primary model generation worth deploying for code review workflows, with **Grok 4.7** planned as the immediate drop-in upgrade upon release.

| Tier | Model ID | Effort / Thinking | Role | Key constraints |
|---|---|---|---|---|
| `cheap` | `grok-4.6` | `low` | Triage, patch application, mechanical checks | Fast execution with lightweight reasoning |
| `standard` | `grok-4.6` | `medium` | Most review dimensions | High reasoning across patterns and logic |
| `strong` | `grok-4.6` | `high` | Coordinator, adjudication, universal fallback | Extended thinking for cross-shard analysis and adjudication |
| `deep` | `grok-4.6` | `max` | Risk-surface (security/migration) review | Maximum reasoning depth for vulnerability analysis (upgrade to `grok-4.7` upon release) |

## Hard rules

1. **Model generation:** Use `grok-4.6` across all tiers, differentiated by reasoning effort levels. Do not route to older versions. Transition to `grok-4.7` once available.
2. **Escalation ladder (one rung at a time):** grok-4.6 low → grok-4.6 medium → grok-4.6 high → grok-4.6 max.
3. **Fallback:** If max reasoning depth times out or fails, fall back to `grok-4.6` at effort `high`.
4. **Refusal handling:** Tag retried findings `degraded: true` with the producing model and effort recorded.
