# Claude Model Routing

**Read this file ONLY on a Claude runtime** (Claude Code, Claude Agent SDK, or direct Claude API dispatch). On any other runtime (Codex, Cursor, Gemini CLI, ...), skip this file entirely and map the abstract tiers from `config/dispatch.json` onto the models your runtime offers — see "Portability & Model Routing" in SKILL.md. Everything else in the skill (triage, gates, refusal loop, report format) is runtime-neutral.

## Tier → model mapping (current as of July 2026)

| Tier | API model ID | Claude Code Task `model` | Role | Key constraints |
|---|---|---|---|---|
| `cheap` | `claude-haiku-4-5` | `haiku` | Triage, patch application, mechanical retries | **Never pass an effort value** — Haiku 4.5 rejects the effort parameter (400) |
| `standard` | `claude-sonnet-5` | `sonnet` | Most review dimensions | Effort `low`/`medium`/`high` only (see cost trap below). Ships cyber safeguards — **can refuse**; handle like `deep` |
| `strong` | `claude-opus-4-8` | `opus` | Coordinator, adjudication, universal fallback | No meaningful dual-use classifier refusal risk in normal PR review. The safe choice for anything that must not stall |
| `deep` | `claude-fable-5` | `fable` | Risk-surface security/migration review only | Classifiers refuse security-adjacent content with elevated false positives (auth, vulns, injection). Mandatory 30-day retention, no ZDR. Expensive |

When dispatching with Claude Code's Task/Agent tool, pass the shorthand from the third column as the `model` parameter.

## Hard rules

1. **Coordinator = `strong` (Opus 4.8). Never Fable, never Sonnet.** A classifier refusal at the coordinator kills orchestration state; a refusal at a leaf is a cheap retry.
   - In Claude Code the coordinator *is* the main session model, and this skill cannot change it. If the session runs on Fable and the PR is security-heavy, recommend the user switch (`/model opus`) before the run. Either way, keep coordinator prose neutral: adjudicate finding *metadata* (severity, confidence, file:line), never restate exploit payloads or attack narratives in coordinator text — that detail stays inside leaf reports. This contains any refusal to a single leaf instead of downgrading the whole run.
2. **Sonnet effort ceiling is `high`. Never route to Sonnet at `xhigh`** — Sonnet 5 at xhigh can cost more than Opus 4.8 at comparable accuracy. When a task needs more than Sonnet-high, the next rung is Opus.
3. **Escalation ladder (one rung at a time):** Sonnet low → Sonnet medium → Sonnet high → Opus 4.8 → Fable 5. Promote a task one rung when (a) the agent self-reports low confidence on its own findings, or (b) its verification gate fails twice (`limits.impl_failures_before_escalation`). Never skip rungs to Fable — risk-surface work is the only thing that *starts* on Fable.
4. **Fable cap:** at most `limits.max_fable_dispatches` Fable dispatches per run (default 3). If triage selects more risk-surface file groups than the cap, merge groups into fewer dispatches or send the overflow to Opus.
5. **`sensitive_repo: true`** removes Fable from every route (its 30-day retention requirement is incompatible with ZDR policies) — those tasks go to Opus 4.8 instead. Set per repo in `config/dispatch.json`.
6. **Concurrency:** `limits.max_concurrent_agents` (default 6) caps *simultaneous* dispatches, not the run total. A 12-agent plan runs in waves of ≤6, queuing the rest as slots free up.

## Refusal & failure handling (mechanics)

Both Fable 5 **and** Sonnet 5 can refuse. On the API this is `stop_reason: "refusal"` returned as HTTP 200; in Claude Code it surfaces as a subagent that declines the task or returns refusal language instead of findings. For **every** leaf dispatch:

1. On refusal or hard failure, retry the **identical** task once on the task's `fallback` from `config/dispatch.json`.
2. Tag every finding produced by the retry `degraded: true` and record which model actually produced it (this appears in the report so the coordinator can weigh or re-queue it).
3. If the fallback also refuses/fails, or `fallback` is `null`, record the dimension as **"no coverage — degraded"** in the report. **A refusal must never abort the run or lose accumulated state** — the run always completes with partial results plus a degradation summary.
4. Dispatch surface:
   - **Claude Code / Task-tool dispatch:** implement the retry in the coordinator loop — re-dispatch with the fallback tier's `model` shorthand.
   - **Direct API dispatch:** prefer the server-side `fallbacks` parameter (beta header `server-side-fallback-2026-06-01`, e.g. Fable→Opus) or the SDK's refusal-fallback middleware; always check `stop_reason` before reading `content`.

## Effort mapping

`effort` in `config/dispatch.json` is advisory on Claude Code (the Task tool has no per-dispatch effort parameter) — encode it as depth instructions in the leaf prompt. On direct API dispatch it maps to `output_config.effort`.

| Config effort | Claude Code (add to leaf prompt) | Direct API |
|---|---|---|
| `low` | "Do a quick, focused pass. Report only clear findings; do not deep-dive." | `output_config: {effort: "low"}` |
| `medium` | "Balance depth and speed; investigate anything suspicious one level deep." | `output_config: {effort: "medium"}` |
| `high` | "Be thorough: trace data flows and edge cases before reporting." | `output_config: {effort: "high"}` |

Never attach effort to `cheap` (Haiku rejects it). Never use `xhigh`/`max` on `standard` (Sonnet) — escalate the tier instead.

## Sonnet 5 API notes (direct API dispatch only)

- Do **not** set `temperature` / `top_p` / `top_k` — non-default values return 400.
- Do **not** set manual `thinking.budget_tokens` — returns 400. Omit `thinking` entirely (adaptive is the default).
- New tokenizer: ~30% more tokens for the same text vs Sonnet 4.6 — recount any `max_tokens` budgets carried over from older configs.
