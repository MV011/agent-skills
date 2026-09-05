# Gemini Model Routing

**Read this file when leaves or the coordinator run on a Gemini runtime** (Gemini CLI, Antigravity, or direct Google GenAI API).

## Tier → model mapping (Gemini 3.x lineup, current as of September 2026)

| Tier | Model ID | Effort / Thinking | Role | Key constraints |
|---|---|---|---|---|
| `cheap` | `gemini-3.8-flash-lite` | `low` | Triage, patch application, mechanical checks | Fastest turnaround, lowest latency and quota consumption |
| `standard` | `gemini-3.8-flash` | `high` | Most review dimensions (logic, silent failure, style, tests) | Balanced everyday review model with strong reasoning |
| `strong` | `gemini-3.8-pro` | `high` | Coordinator, adjudication, universal fallback | Strong cross-file reasoning, synthesis, and large-context comprehension |
| `deep` | `gemini-3.8-pro` | `max` | Risk-surface (security/migration) review | Maximum thinking depth for deep vulnerability and invariant analysis |

## Hard rules

1. **Coordinator = `strong` (Gemini 3.8 Pro).** The coordinator needs broad context and high synthesis fidelity to adjudicate findings without dropping nuances across multiple leaf reports.
2. **Standard tier uses Gemini 3.8 Flash (High reasoning).** Flash with high reasoning handles patterns, logic errors, and silent failure checks rapidly while maintaining high recall.
3. **Escalation ladder (one rung at a time):** Flash-Lite low → Flash medium → Flash high → Pro high → Pro max. Promote a task one rung when a leaf self-reports low confidence or a verification gate fails twice.
4. **Refusal & Safety Handling:** Gemini safety filters may occasionally flag exploit payloads in security review leaves (e.g. SQL injection or SSRF demonstrations). If a leaf is blocked by content filtering, retry once on the fallback tier with neutral framing (focusing on audit metadata and CWE references rather than attack narratives).
5. **Subagent & Tool Dispatch:** When invoking subagents via Antigravity or Gemini CLI, assign models per task according to the table above.
