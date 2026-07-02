# Triage Heuristics

Triage runs **before** any review agent is selected. It is cheap by design: prefer deterministic shell over model calls; where judgment is needed (nature classification, module grouping), use the `triage` task tier from `config/dispatch.json` on runtimes that support tiered dispatch, or do it inline in the coordinator otherwise.

## Inputs (deterministic)

```bash
git diff $MERGE_BASE...HEAD --stat
git diff $MERGE_BASE...HEAD --name-only
git diff $MERGE_BASE...HEAD --shortstat    # files changed, insertions, deletions
git log $MERGE_BASE..HEAD --oneline
git diff HEAD --name-only                   # uncommitted work counts too
```

## Classification

1. **Size** — LOC added+removed, file count, distinct top-level modules touched. Compare against `triage_thresholds` in `config/dispatch.json` (trivial: ≤50 LOC and ≤3 files; large: ≥800 LOC or ≥20 files by default).
2. **Risk surface** — match every changed path against the `risk_paths` globs. **Any hit makes this a risk-surface PR regardless of size.** Record which file matched which pattern.
3. **Nature** (per file group) — pure refactor / new behavior / dependency bump / generated. Files matching `generated_paths` (lockfiles, snapshots, dist, minified) are **excluded from deep review** — list them in the plan as excluded; for dependency bumps, review the manifest change, not the lockfile.
4. **Test delta** — count changed source files vs changed test files. Flag `proportional: no` when behavior-changing source edits arrive with no test changes; that strengthens the case for `test-review`.

## Routing decision

| Verdict | Condition | Plan |
|---|---|---|
| **Trivial** | Within trivial thresholds AND zero risk-path hits AND no behavior change | Single `trivial-review` pass. No fan-out. |
| **Typical** | Everything else | One agent per applicable dimension (Step 4 table in SKILL.md), grouped by module if the PR spans several. |
| **Risk-surface** | Any `risk_paths` hit — at any size, even trivial | ALWAYS add `security-review` (deep tier) scoped to **just the matched files**, on top of whatever the size verdict selects. |
| **Large** | At/above large thresholds | Shard by module/package: one agent per shard per applicable dimension. Add a coordinator **cross-shard consistency pass** after leaves return (naming, duplicated logic, contract mismatches across shards). |

## Triage plan — structured block

This block **must appear verbatim in the final report** so routing decisions are auditable: every dispatched agent traces back to a plan line.

```yaml
triage:
  size: { files: 12, loc_added: 640, loc_removed: 120, modules: [api, web] }
  risk_surface:
    - { path: "api/src/auth/session.ts", matched: "**/auth/**" }
  nature: behavior          # refactor | behavior | dep-bump | generated | mixed
  excluded_generated: [ "pnpm-lock.yaml" ]
  test_delta: { source_changed: 9, tests_changed: 1, proportional: no }
  verdict: typical          # trivial | typical | large
  plan:
    - { task: security-review, tier: deep, files: ["api/src/auth/**"], reason: "risk path **/auth/** matched" }
    - { task: logic-review, tier: standard, effort: high, files: ["api/src/**", "web/src/**"], reason: "always-on" }
    - { task: silent-failure-review, tier: standard, effort: high, files: ["api/src/**"], reason: "always-on" }
    - { task: test-review, tier: standard, effort: medium, files: ["**"], reason: "test delta not proportional" }
```

On non-Claude runtimes, replace `tier` values with the runtime's mapped models — the plan structure stays the same.
