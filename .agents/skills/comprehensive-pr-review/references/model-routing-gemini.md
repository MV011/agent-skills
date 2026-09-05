# Gemini Model Routing

**Read this file when leaves or the coordinator run on a Gemini runtime** (Gemini CLI, Antigravity, or Google GenAI API).

## Tier → model mapping (current as of September 2026)

| Tier | Model ID | Effort / Thinking | Role | Key constraints |
|---|---|---|---|---|
| `cheap` | `gemini-3.8-flash` | `low` | Triage, patch application, mechanical checks | Fastest turnaround with minimal thinking overhead |
| `standard` | `gemini-3.8-flash` | `high` | Most review dimensions (logic, silent failure, style, tests) | High reasoning everyday code reviewer |
| `strong` | `gemini-3.1-pro` | `high` | Coordinator, adjudication, universal fallback | Strong cross-file reasoning and large-context synthesis (3.8 Pro is not yet released) |
| `deep` | `gemini-3.1-pro` | `max` | Risk-surface (security/migration) review | Maximum thinking depth for invariant analysis (upgrade to 3.8 Pro upon release) |

## Hard rules

1. **Coordinator = `strong` (Gemini 3.1 Pro).** The coordinator requires high synthesis fidelity to adjudicate multi-agent findings without dropping nuances across diffs.
2. **Standard tier uses Gemini 3.8 Flash (High reasoning).** Flash with high reasoning handles patterns, logic errors, and silent failure checks rapidly while maintaining high recall.
3. **Escalation ladder (one rung at a time):** Flash low → Flash medium → Flash high → 3.1 Pro high → 3.1 Pro max.
4. **Refusal & Safety Handling:** If safety thresholds flag exploit patterns or payloads in security review leaves, retry once on the fallback tier with neutral framing (focusing on audit metadata and CWE references rather than attack narratives).
