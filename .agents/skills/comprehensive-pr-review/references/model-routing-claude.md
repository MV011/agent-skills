# Claude Model Routing

**Read this file ONLY on a Claude runtime** (Claude Code, Claude Agent SDK, or direct Claude API dispatch). On any other runtime (Codex, Cursor, Gemini CLI, ...), skip this file entirely and map the abstract tiers from `config/dispatch.json` onto the models your runtime offers — see "Portability & Model Routing" in SKILL.md. Everything else in the skill (triage, gates, refusal loop, report format) is runtime-neutral.

## Tier → model mapping (current as of September 2026)

Claude code reviews run **strictly on Opus 5 and Fable 5.1**. Sonnet 5 is restricted to the **very low end** (`cheap` tier only: triage, single-file patch application, mechanical tasks). Substantive review dimensions never run on Sonnet.

| Tier | API model ID | Claude Code Task `model` | Role | Key constraints |
|---|---|---|---|---|
| `cheap` | `claude-sonnet-5` | `sonnet` | Very low end: triage, patch application, mechanical retries, trivial pass | Effort `low` only. Relegated strictly to low-end mechanical and triage work |
| `standard` | `claude-opus-5` | `opus` | Core review dimensions (logic, silent failure, tests, performance, types, style, comments) | Primary review workhorse. Highest code reasoning fidelity, zero classifier refusal risk in normal reviews |
| `strong` | `claude-opus-5` | `opus` | Coordinator, adjudication, universal fallback | Safe, robust coordinator that never stalls on dual-use classifiers |
| `deep` | `claude-fable-5-1` | `fable` | Risk-surface security/migration review and architectural deep dives | Deepest reasoning for vulnerability and data invariant analysis. Fallback is Opus 5. Mandatory 30-day retention, no ZDR. Expensive |

When dispatching with Claude Code's Task/Agent tool, pass the shorthand from the third column as the `model` parameter.

## Hard rules

1. **Coordinator = `strong` (Opus 5). Never Fable, never Sonnet.** A classifier refusal at the coordinator kills orchestration state; a refusal at a leaf is a cheap retry.
   - In Claude Code the coordinator *is* the main session model, and this skill cannot change it. If the session runs on Fable and the PR is security-heavy, recommend the user switch (`/model opus`) before the run. Either way, keep coordinator prose neutral: adjudicate finding *metadata* (severity, confidence, file:line), never restate exploit payloads or attack narratives in coordinator text — that detail stays inside leaf reports. This contains any refusal to a single leaf instead of downgrading the whole run.
2. **Sonnet 5 is restricted to the very low end (`cheap` tier).** Never route substantive review dimensions to Sonnet. Reviews run on Opus 5 (`standard`) and Fable 5.1 (`deep`). Sonnet effort ceiling is capped at `low`.
3. **Escalation ladder (one rung at a time):** Sonnet low (cheap/mechanical) → Opus 5 (standard/strong review dimensions) → Fable 5.1 (deep risk-surface review).
4. **Refusals fall back to Opus 5:** While Fable 5.1 refuses significantly fewer legitimate checks than 5.0, any refusal on Fable 5.1 retries on **Opus 5** (`strong` tier).
5. **Fable cap:** at most `limits.max_fable_dispatches` Fable dispatches per run (default 3). If triage selects more risk-surface file groups than the cap, merge groups into fewer dispatches or send the overflow to Opus 5.
6. **`sensitive_repo: true`** removes Fable from every route (its 30-day retention requirement is incompatible with ZDR policies) — those tasks go to Opus 5 instead. Set per repo in `config/dispatch.json`.
7. **Concurrency:** `limits.max_concurrent_agents` (default 6) caps *simultaneous* dispatches, not the run total. A 12-agent plan runs in waves of ≤6, queuing the rest as slots free up.

## Refusal & failure handling (mechanics)

Fable 5.1 can refuse on security-adjacent diffs. On the API this is `stop_reason: "refusal"` returned as HTTP 200; in Claude Code it surfaces as a subagent that declines the task or returns refusal language instead of findings. For **every** leaf dispatch:

1. On refusal or hard failure, retry the **identical** task once on `strong` (`claude-opus-5`).
2. Tag every finding produced by the retry `degraded: true` and record which model actually produced it (e.g. `opus-5`).
3. If the fallback also refuses/fails, or `fallback` is `null`, record the dimension as **"no coverage — degraded"** in the report. **A refusal must never abort the run or lose accumulated state** — the run always completes with partial results plus a degradation summary.
4. Dispatch surface:
   - **Claude Code / Task-tool dispatch:** implement the retry in the coordinator loop — re-dispatch with the fallback tier's `model` shorthand (`opus`).
   - **Direct API dispatch:** prefer the server-side `fallbacks` parameter (beta header `server-side-fallback-2026-06-01`, e.g. Fable→Opus) or the SDK's refusal-fallback middleware; always check `stop_reason` before reading `content`.

## Effort mapping

`effort` in `config/dispatch.json` is advisory on Claude Code (the Task tool has no per-dispatch effort parameter) — encode it as depth instructions in the leaf prompt. On direct API dispatch it maps to `output_config.effort`.

| Config effort | Claude Code (add to leaf prompt) | Direct API |
|---|---|---|
| `low` | "Do a quick, focused pass. Report only clear findings; do not deep-dive." | `output_config: {effort: "low"}` |
| `medium` | "Balance depth and speed; investigate anything suspicious one level deep." | `output_config: {effort: "medium"}` |
| `high` | "Be thorough: trace data flows and edge cases before reporting." | `output_config: {effort: "high"}` |

Sonnet 5 (`cheap`): effort `low` only. Opus 5 (`standard`/`strong`): effort `medium` or `high`. Fable 5.1 (`deep`): effort `high` or `max`.

## Sonnet 5 API notes (direct API dispatch only)

- Do **not** set `temperature` / `top_p` / `top_k` — non-default values return 400.
- Do **not** set manual `thinking.budget_tokens` — returns 400. Omit `thinking` entirely (adaptive is the default).
- New tokenizer: ~30% more tokens for the same text vs Sonnet 4.6 — recount any `max_tokens` budgets carried over from older configs.
