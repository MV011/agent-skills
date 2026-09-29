# Codex / GPT Model Routing

**Read this file when leaves run on GPT models** — either (a) the skill itself is running on a Codex runtime, or (b) a Claude (or other) runtime cross-dispatches review leaves through the Codex CLI (`codex exec`) for second opinions on a separate quota pool. On a Claude runtime dispatching Claude subagents, use `references/model-routing-claude.md` instead; the two can coexist in one run (e.g. Claude leaves + one Codex adversarial pass).

## Tier → model mapping (GPT-6.1 Sol + GPT-6 Astra, live-verified 2026-09-30)

Owner ruling (2026-09-30): "use sol 6.1 for as much as possible, cheap and capable, astra 6 at the very top for now (xhigh)". Every tier below `deep` runs `gpt-6.1-sol`, split by effort; `gpt-6-astra` runs only `deep`, at `xhigh`.

| Tier | Model ID | Effort | Role | Key constraints |
|---|---|---|---|---|
| `cheap` | `gpt-6.1-sol` | `high` | Triage, mechanical checks, patch application, **style + comment review** (via task `codex` overrides) | Replaced `gpt-6-luna` on 2026-09-30. Same model and default effort as `standard`; on Codex the two differ only through per-task efforts |
| `standard` | `gpt-6.1-sol` | `high`–`xhigh` | Most review dimensions (logic + silent-failure at `xhigh`) | $2/$10 per 1M, cached input $0.10. Nearly matches astra on agentic coding at a fifth of the price. Fallback: `gpt-6-sol` at the same effort, then `gpt-5.6-terra` |
| `strong` | `gpt-6.1-sol` | `xhigh`–`max` | Coordinator-grade adjudication, universal fallback | Same model as `standard`, one effort band up. Also the vision tier (`-i`). Fallback: `gpt-6-sol` at the same effort |
| `heavy` | `gpt-6.1-sol` | `max` | Large-PR `deep-dive`, fallback when a `deep` dispatch fails | One rung below deep. Was `gpt-6-astra` `high` until 2026-09-30; astra is now reserved for `deep`. Fallback: `gpt-6-sol` `max` |
| `deep` | `gpt-6-astra` | `xhigh` | Risk-surface (security/migration) review | The only astra tier. `xhigh` is the ceiling for now; `max` only on explicit request. Flagship, $10/$50. Fallback: `gpt-6.1-sol` at `max` |

`gpt-6.1-sol` needs **Codex CLI ≥ 0.159**: 0.158 rejects the ID on a ChatGPT login ("model is not supported when using Codex with a ChatGPT account"). Upgrade the CLI (`brew upgrade --cask codex`) before assuming the model is unavailable. Supported efforts: `low`…`max` plus `ultra`.

Beyond `deep`: effort **`ultra`** (astra and the sols; not luna) spawns parallel delegate subagents — a different execution mode, not just more thinking. It is slow and the most expensive option there is. **Opt-in only**, for plan-level/architecture-level passes on very large PRs; never route ordinary review dimensions to it.

`gpt-5.3-codex-spark` (near-instant, text-only) is **no longer in the Codex model cache** as of 2026-09-22. Use `gpt-6.1-sol` `low` for fast paths unless a live probe shows spark is back.

Do **not** route to `gpt-5.5` or older generations. Use GPT-6.1, GPT-6 and GPT-5.6 only. If a model misbehaves on a task, fall back within those families (`gpt-6.1-sol` → `gpt-6-sol` → `gpt-5.6-terra`; astra → `gpt-6.1-sol`), never to a prior generation. `gpt-6-luna` is off the review routing since 2026-09-30.

**Verify before trusting this table on a new machine or after a model-generation bump:** `~/.codex/models_cache.json` is the Codex CLI's own authoritative model list; confirm a candidate with `codex exec --skip-git-repo-check -m <id> -c model_reasoning_effort=low "Reply OK" </dev/null`. Never guess model IDs from training data.

## Hard rules

1. **Always pass `-m` and `-c model_reasoning_effort` explicitly on every dispatch.** The user's `~/.codex/config.toml` default may be the most expensive combination available (e.g. astra at `max`); an unspecified leaf silently inherits it and burns quota.
2. **Review leaves are read-only: pass `-s read-only` explicitly.** Reviewers must not modify files, and on machines configured with `sandbox_mode = "danger-full-access"` a bare `codex exec` has full write access. Only Step-7 `apply-patch` dispatches may run writable.
3. **Escalation ladder (one rung at a time):** gpt-6.1-sol high → gpt-6.1-sol xhigh → gpt-6.1-sol max (`heavy`) → astra xhigh (`deep`). `gpt-6-sol` and `gpt-5.6-terra` are off the ladder; they are only fallbacks when a `gpt-6.1-sol` dispatch errors.
4. **The coordinator never runs on a cross-dispatched Codex leaf.** Cross-model dispatch is for leaves only; orchestration state stays in the host runtime.
5. **Refusal/failure handling is unchanged** (see SKILL.md): GPT models don't share Claude's cyber-classifier refusal profile, but API errors, rate limits, and declines still happen — retry once on the task's fallback tier, tag `degraded: true`. If that fallback tier resolves to the same model that just failed (e.g. `triage`: `cheap` → `standard`, both `gpt-6.1-sol`), retry on `gpt-6-sol` at the fallback tier's effort instead of re-sending the same dispatch. Then record the producing model (e.g. `gpt-6-astra (xhigh)`, `gpt-6.1-sol (high)`, or `gpt-6-sol (high)` on a fallback) in the findings table.
6. **Vision dimensions route to `gpt-6.1-sol` or astra.** If the PR includes UI screenshots, visual diffs, or asset changes needing visual judgment, attach images with `-i <file>` and use `strong` or `deep` regardless of the dimension's normal tier.

## Headless dispatch mechanics (`codex exec` from any runtime)

```bash
LOG=$(mktemp -t codex-review)
codex exec --skip-git-repo-check \
  -m gpt-6.1-sol -c model_reasoning_effort=high \
  -s read-only \
  [-i screenshot.png] \
  "<self-contained leaf prompt>" </dev/null >"$LOG" 2>&1 &
CODEX_PID=$!
```

- **`</dev/null` is mandatory** — codex exec waits on stdin after finishing when stdin is an open pipe, leaving an idle zombie process.
- Log to a file; poll `kill -0 $CODEX_PID` + `tail`; enforce a timeout (scale up for sol max or astra xhigh/ultra). macOS has no `timeout`: poll `kill -0 $CODEX_PID` against a deadline.
- **Cleanup is PID-only** (`kill $CODEX_PID`, children via `pkill -P $CODEX_PID`). NEVER `pkill -f codex` / `killall codex` — other Codex jobs run concurrently on the machine and a pattern kill takes them all down.
- Prompts must be **self-contained**: GPT leaves have zero conversation context. Include branch, base, file list, focus areas, and the finding-format contract verbatim from `references/agent-prompts.md`.
- Sessions are resumable (`codex exec resume --last`) — prefer resuming for follow-up rounds on the same leaf.

## Per-task `codex` overrides

A task in `config/dispatch.json` may carry a `codex` block (`{tier, effort}`) that applies **only** on Codex runtimes / `codex exec` cross-dispatch. Resolution: `task.codex.effort` > the override tier's `codex_tiers` effort > `task.effort` > `codex_tiers[tier].effort`. Current overrides: `style-review` and `comment-review` → `cheap` (`gpt-6.1-sol` high, up from the task's `medium`). Other runtimes ignore the block, so style review stays on Opus 5.5 on Claude.

## Effort mapping

`effort` values in `config/dispatch.json` map 1:1 onto `-c model_reasoning_effort=<value>` (low/medium/high/xhigh/max — all first-class CLI values, unlike Claude Code where effort is prompt-encoded). Respect each tier's ceiling from the table above: `gpt-6-astra` stops at `xhigh` for now. `gpt-6-luna` rejects `ultra`.
