# Grok / xAI Model Routing

**Read this file when review leaves run on an xAI / Grok runtime.**

## Tier → model mapping (current as of September 2026)

**Grok 4.7** (released 2026-09-21; 500K context, $2/$6 per 1M tokens) is the model for every tier. **Its CLI effort enum is `low|medium|high|xhigh`; `max` is rejected** (live-probed 2026-09-22), so `xhigh` is the top rung.

| Tier | Model ID | Effort / Thinking | Role | Key constraints |
|---|---|---|---|---|
| `cheap` | `grok-4.7` | `low` | Triage, patch application, mechanical checks | Fast execution with lightweight reasoning |
| `standard` | `grok-4.7` | `high` | Most review dimensions | Task efforts override this default |
| `strong` | `grok-4.7` | `xhigh` | Coordinator, adjudication, universal fallback | Extended thinking for cross-shard analysis and adjudication |
| `heavy` | `grok-4.7` | `xhigh` | Large-PR deep dive, deep fallback | No rung between strong and deep here, so heavy maps up to deep settings |
| `deep` | `grok-4.7` | `xhigh` | Risk-surface (security/migration) review | Highest effort the CLI accepts |

`grok-4.7-build-fast` is a latency variant at **2x the price**. It is not a cheap tier; use it only when wall-clock matters.

## Hard rules

1. **Model generation:** Use `grok-4.7` across all tiers, differentiated by reasoning effort. `grok-4.6` is the fallback; never `grok-4.5` or older.
2. **Escalation ladder (one rung at a time):** grok-4.7 low → medium → high → xhigh. `xhigh` is the ceiling: task efforts of `max` run at `xhigh`.
3. **Fallback:** If `xhigh` times out or fails, retry on `grok-4.7` `high`, then `grok-4.6` at the same effort.
4. **Refusal handling:** Tag retried findings `degraded: true` with the producing model and effort recorded.
