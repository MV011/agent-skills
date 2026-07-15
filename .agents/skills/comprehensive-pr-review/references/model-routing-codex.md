# Codex / GPT Model Routing

**Read this file when leaves run on GPT models** — either (a) the skill itself is running on a Codex runtime, or (b) a Claude (or other) runtime cross-dispatches review leaves through the Codex CLI (`codex exec`) for second opinions on a separate quota pool. On a Claude runtime dispatching Claude subagents, use `references/model-routing-claude.md` instead; the two can coexist in one run (e.g. Claude leaves + one Codex adversarial pass).

## Tier → model mapping (GPT 5.6 lineup, live-verified 2026-07-09)

| Tier | Model ID | Effort | Role | Key constraints |
|---|---|---|---|---|
| `cheap` | `gpt-5.6-luna` | `low` (`medium` for larger shards) | Triage, mechanical checks, patch application | Cheapest/fastest ($1/$6 per 1M). Supports low…max; `ultra` accepted but may silently clamp |
| `standard` | `gpt-5.6-terra` | `medium`–`high` | Most review dimensions | GPT-5.5-class capability at ~half cost ($2.50/$15) |
| `strong` | `gpt-5.6-sol` | `high`–`xhigh` | Adjudication-grade review, universal fallback | Flagship ($5/$30). Also the vision tier — GPT vision outperforms Claude Opus 4.8 on screenshot/UI review |
| `deep` | `gpt-5.6-sol` | `max` | Risk-surface (security/migration) review | `max` is a first-class deep effort as of Codex v0.143.0 |

Beyond `deep`: effort **`ultra`** on sol spawns parallel delegate subagents — a different execution mode, not just more thinking. It is slow and the most expensive option there is. **Opt-in only**, for plan-level/architecture-level passes on very large PRs; never route ordinary review dimensions to it.

Also available: `gpt-5.3-codex-spark` — near-instant, text-only; sanity checks and trivial-review fast paths.

Do **not** route to `gpt-5.5` or older generations — the 5.6 family only. If a 5.6 model misbehaves on a task, fall back within the family (sol ↔ terra), never to a prior generation.

**Verify before trusting this table on a new machine or after a model-generation bump:** `~/.codex/models_cache.json` is the Codex CLI's own authoritative model list; confirm a candidate with `codex exec --skip-git-repo-check -m <id> -c model_reasoning_effort=low "Reply OK" </dev/null`. Never guess model IDs from training data.

## Hard rules

1. **Always pass `-m` and `-c model_reasoning_effort` explicitly on every dispatch.** The user's `~/.codex/config.toml` default may be the most expensive combination available (e.g. sol at `max`); an unspecified leaf silently inherits it and burns quota.
2. **Review leaves are read-only: pass `-s read-only` explicitly.** Reviewers must not modify files, and on machines configured with `sandbox_mode = "danger-full-access"` a bare `codex exec` has full write access. Only Step-7 `apply-patch` dispatches may run writable.
3. **Escalation ladder (one rung at a time):** luna low → luna medium → terra medium → terra high → sol high → sol xhigh → sol max. Same promotion triggers as the Claude ladder (self-reported low confidence, or gate fails twice). `ultra` is not on the ladder — it is a deliberate coordinator decision, never an automatic escalation.
4. **The coordinator never runs on a cross-dispatched Codex leaf.** Cross-model dispatch is for leaves only; orchestration state stays in the host runtime.
5. **Refusal/failure handling is unchanged** (see SKILL.md): GPT models don't share Claude's cyber-classifier refusal profile, but API errors, rate limits, and declines still happen — retry once on the task's fallback tier, tag `degraded: true`, record the producing model (e.g. `gpt-5.6-terra (high)`) in the findings table.
6. **Vision dimensions route to sol.** If the PR includes UI screenshots, visual diffs, or asset changes needing visual judgment, attach images with `-i <file>` and use `strong` regardless of the dimension's normal tier.

## Headless dispatch mechanics (`codex exec` from any runtime)

```bash
LOG=$(mktemp -t codex-review)
codex exec --skip-git-repo-check \
  -m gpt-5.6-terra -c model_reasoning_effort=high \
  -s read-only \
  [-i screenshot.png] \
  "<self-contained leaf prompt>" </dev/null >"$LOG" 2>&1 &
CODEX_PID=$!
```

- **`</dev/null` is mandatory** — codex exec waits on stdin after finishing when stdin is an open pipe, leaving an idle zombie process.
- Log to a file; poll `kill -0 $CODEX_PID` + `tail`; enforce a timeout (scale up for sol max/ultra).
- **Cleanup is PID-only** (`kill $CODEX_PID`, children via `pkill -P $CODEX_PID`). NEVER `pkill -f codex` / `killall codex` — other Codex jobs run concurrently on the machine and a pattern kill takes them all down.
- Prompts must be **self-contained**: GPT leaves have zero conversation context. Include branch, base, file list, focus areas, and the finding-format contract verbatim from `references/agent-prompts.md`.
- Sessions are resumable (`codex exec resume --last`) — prefer resuming for follow-up rounds on the same leaf.

## Effort mapping

`effort` values in `config/dispatch.json` map 1:1 onto `-c model_reasoning_effort=<value>` (low/medium/high/xhigh/max — all first-class CLI values, unlike Claude Code where effort is prompt-encoded). No model in the lineup rejects an effort parameter, but respect each tier's ceiling from the table above.
