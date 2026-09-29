# Claude Model Routing

**Read this file ONLY on a Claude runtime** (Claude Code, Claude Agent SDK, or direct Claude API dispatch). On any other runtime (Codex, Cursor, Gemini CLI, ...), skip this file entirely and map the abstract tiers from `config/dispatch.json` onto the models your runtime offers — see "Portability & Model Routing" in SKILL.md. Everything else in the skill (triage, gates, refusal loop, report format) is runtime-neutral.

## Tier → model mapping (current as of September 2026)

**Sonnet 5.5 is the lowest allowed Claude model** (Bogdan 2026-09-29). It runs the `search` helper and the `cheap` tier (triage, trivial pass, patch application). Every review dimension runs on **Opus 5.5** (`standard` through `heavy`, split by effort) or **Fable 5.1** (`deep`). Sonnet 5 and Haiku 4.5 do not run any role; Haiku 5.5 takes simple tasks once it ships. **Sonnet and Opus top out at `xhigh`, never `max`** (Bogdan 2026-09-29: "they perform their best at xhigh"); `max` is Fable-only.

| Tier | API model ID | Claude Code Task `model` | Role | Key constraints |
|---|---|---|---|---|
| `search` | `claude-sonnet-5-5` | `sonnet` | Codebase search, file location, exploration subagents only | Not a review tier; never produces findings. Effort `low` |
| `cheap` | `claude-sonnet-5-5` | `sonnet` | Triage, patch application, trivial pass | Effort `high` (`trivial-review` `xhigh`). Half the price of Opus 5.5, so the savings go into effort. Five refusal categories, so `triage` and `trivial-review` fall back to `standard` |
| `standard` | `claude-opus-5-5` | `opus` | Core review dimensions (logic, silent failure, tests, performance, types, style, comments) | Primary review workhorse, default effort `high` (task efforts `medium`–`xhigh`). Fable-5.1-class on most benchmarks at $4/$20, cheaper than Opus 5, and the savings go into effort. API default effort is **`medium`**, so always state it |
| `strong` | `claude-opus-5-5` | `opus` | Coordinator, adjudication, universal fallback | Effort `xhigh`. Classifiers are broader than Opus 5's (`cyber` + `bio` + `reasoning_extraction`), so keep coordinator prose neutral (rule 1) |
| `heavy` | `claude-opus-5-5` | `opus` | Large-PR `deep-dive`, deep-tier fallback, Fable-cap overflow | Effort `xhigh` (Opus ceiling), so on Claude it matches `strong`; kept as a tier for runtimes that have a rung here. Spends no `max_fable_dispatches` slot |
| `deep` | `claude-fable-5-1` | `fable` | Risk-surface security/migration review | Effort `max`. Deepest long-horizon reasoning. Fallback is `heavy` (Opus 5.5 xhigh). Mandatory 30-day retention, no ZDR. Most expensive ($10/$50), so it is capped |

When dispatching with Claude Code's Task/Agent tool, pass the shorthand from the third column as the `model` parameter.

## Hard rules

1. **Coordinator = `strong` (Opus 5.5 xhigh). Never Fable, never Sonnet.** A classifier refusal at the coordinator kills orchestration state; a refusal at a leaf is a cheap retry.
   - In Claude Code the coordinator *is* the main session model, and this skill cannot change it. If the session runs on Fable and the PR is security-heavy, recommend the user switch (`/model opus`) before the run. Either way, keep coordinator prose neutral: adjudicate finding *metadata* (severity, confidence, file:line), never restate exploit payloads or attack narratives in coordinator text — that detail stays inside leaf reports. This contains any refusal to a single leaf instead of downgrading the whole run.
2. **Sonnet 5.5 is the floor, and it never reviews a dimension.** It runs `search`, triage, the trivial pass and patch application; every review dimension runs on Opus 5.5 or Fable 5.1. No Sonnet 5 or Haiku 4.5 anywhere; Haiku 5.5 takes simple tasks once it ships.
3. **Escalation ladder (one rung at a time):** Sonnet 5.5 high (`cheap`) → Opus 5.5 high (`standard`) → Opus 5.5 xhigh (`strong` / `heavy`) → Fable 5.1 max (`deep`). Never Sonnet or Opus at `max`.
4. **Refusals fall back to Opus 5.5:** any refusal on Fable 5.1 retries on **Opus 5.5 at xhigh** (`heavy` tier). A Sonnet 5.5 refusal on a `cheap` task retries on `standard` (Opus 5.5 high). On direct API dispatch where Opus 5.5 also refuses on a `cyber` category, `claude-opus-5` is an acceptable last rung (narrower classifier set) before recording no coverage.
5. **Fable cap:** at most `limits.max_fable_dispatches` Fable dispatches per run (default 3). If triage selects more risk-surface file groups than the cap, merge groups into fewer dispatches or send the overflow to `heavy` (Opus 5.5 at xhigh).
6. **`sensitive_repo: true`** removes Fable from every route (its 30-day retention requirement is incompatible with ZDR policies) — those tasks go to Opus 5.5 instead. Set per repo in `config/dispatch.json`.
7. **Concurrency:** `limits.max_concurrent_agents` (default 6) caps *simultaneous* dispatches, not the run total. A 12-agent plan runs in waves of ≤6, queuing the rest as slots free up.

## Refusal & failure handling (mechanics)

Fable 5.1 can refuse on security-adjacent diffs. On the API this is `stop_reason: "refusal"` returned as HTTP 200; in Claude Code it surfaces as a subagent that declines the task or returns refusal language instead of findings. For **every** leaf dispatch:

1. On refusal or hard failure, retry the **identical** task once on the task's fallback tier (`standard`, `strong` or `heavy`, all `claude-opus-5-5`).
2. Tag every finding produced by the retry `degraded: true` and record which model actually produced it (e.g. `opus-5-5`).
3. If the fallback also refuses/fails, or `fallback` is `null`, record the dimension as **"no coverage — degraded"** in the report. **A refusal must never abort the run or lose accumulated state** — the run always completes with partial results plus a degradation summary.
4. Dispatch surface:
   - **Claude Code / Task-tool dispatch:** implement the retry in the coordinator loop — re-dispatch with the fallback tier's `model` shorthand (`opus`).
   - **Direct API dispatch:** prefer the server-side `fallbacks` parameter (beta `server-side-fallback-2026-07-01` + `fallbacks: "default"`, which routes by refusal category; the older `-2026-06-01` array form still works) or the SDK's refusal-fallback middleware; always check `stop_reason` before reading `content`.

## Effort mapping

`effort` in `config/dispatch.json` is advisory on Claude Code (the Task tool has no per-dispatch effort parameter) — encode it as depth instructions in the leaf prompt. On direct API dispatch it maps to `output_config.effort`.

| Config effort | Claude Code (add to leaf prompt) | Direct API |
|---|---|---|
| `low` | "Do a quick, focused pass. Report only clear findings; do not deep-dive." | `output_config: {effort: "low"}` |
| `medium` | "Balance depth and speed; investigate anything suspicious one level deep." | `output_config: {effort: "medium"}` |
| `high` | "Be thorough: trace data flows and edge cases before reporting." | `output_config: {effort: "high"}` |
| `xhigh` | "Be exhaustive: trace every data flow and invariant across files; verify each finding before reporting." | `output_config: {effort: "xhigh"}` |
| `max` (Fable 5.1 only) | "Leave nothing unexamined: trace every path, try to disprove each finding, and cover cross-file invariants before reporting." | `output_config: {effort: "max"}` |

Sonnet 5.5: `low` on `search`, `high` on `cheap` (`trivial-review` `xhigh`). Opus 5.5: `medium`–`xhigh` on `standard` (per task), `xhigh` on `strong` and `heavy`. **Always set it**: omitting it on the API means `medium` for Opus 5.5 and `high` for Sonnet 5.5. Fable 5.1 (`deep`): `max`. **Ceiling: Sonnet and Opus never run at `max`** (Bogdan 2026-09-29); `xhigh` is their best setting. **Never lower effort to exploit the newer model's efficiency** (Bogdan 2026-09-22): the price drop is spent on effort.

## Opus 5.5 API notes (direct API dispatch only)

- Thinking cannot be disabled (`{type: "disabled"}` / `budget_tokens` → 400). Lower effort instead.
- Forced `tool_choice` `any`/`tool` → 400. Use `auto` + `strict: true`, or structured outputs, for finding-format JSON.
- Preserved thinking: its thinking blocks are only read by Fable 5.1 / Mythos 5.1, so a fallback to an older Opus runs without them.

## Sonnet 5.5 API notes (direct API dispatch of `search` / `cheap` only)

- `thinking: {type: "disabled"}` and `budget_tokens` return 400. Omit `thinking` (adaptive is the default). The only thinking-off mode is `{type: "between_tools"}`, accepted at effort `high` or below with no other field.
- Forced `tool_choice` `any` / `tool` returns 400. Use `auto` + `strict: true`, or structured outputs, for finding-format JSON.
- Do **not** set `temperature` / `top_p` / `top_k` — non-default values return 400.
- Effort defaults to `high`, but its levels are recalibrated from Sonnet 5; state it explicitly.
- Refusal categories: `cyber`, `bio`, `frontier_llm`, `reasoning_extraction`, `general_harms`. Server-side `fallbacks: "default"` works only on the Claude API; elsewhere, retry on the task's fallback tier.
- Same tokenizer as Sonnet 5.
