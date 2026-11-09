---
name: design-review
description: Architecture-level review of a change from its design surface only (infrastructure-as-code, schemas, data store definitions, event and API contracts, routes, permissions, migrations, config), without reading implementation code. Asks whether the change should be built this way before anyone checks whether it was built correctly. Use before a code review of any PR that adds or changes a data store, queue, topic, function, service, route, role, schedule or contract; on a design doc, HLD, ADR or ticket before code exists; when the user says "design review", "architecture review", "is this the right design", "review the infra/YAML", "should this be X"; and when comprehensive-pr-review triage reports a design-surface hit.
tools: Read, Bash, Glob, Grep
---

# Design Review

Follow the portable skill definition below as the primary workflow for this task.
Adapt it only when Claude Code's tool surface or the current repository requires a direct translation.

Supporting files referenced by the workflow (references/) are installed with the skill at
`~/.claude/skills/design-review/` — read them from there when a step points to one.

If you are running as a subagent that cannot dispatch further agents, do not attempt
fan-out: run the review dimensions sequentially in this context and note the degraded
single-context mode in the report.

# Design Review

Review the **shape** of a change, not its code. A code review asks "does this implementation meet the requirements?". This review asks "is this the right design for the requirements?". It runs first, because one design question (wrong store, wrong event topology, shared identity) often explains a dozen code-level bugs, and fixing the design removes them instead of patching each one.

The reviewer reads **only the design surface**: file names, infrastructure-as-code, schemas, contracts, route and permission maps, migrations, config. It does not read implementation logic. If a question can only be answered by reading code, it becomes a hand-off question for the code review instead.

## When to Use

- A PR adds or changes any of: a data store or index, a queue/topic/bus/stream, a function/service/container, an HTTP route, an IAM role or policy, a schedule, a config source, an event or API contract, a migration.
- Before a code review of such a PR (run this first, pass its questions to the code reviewers).
- A design doc, HLD, ADR or ticket describes a new component, before code exists.
- `comprehensive-pr-review` triage finds a design-surface hit.

Skip it for changes with no design surface (pure logic, copy, styling, tests only). Say so in one line and stop.

## Inputs

1. **Requirements**: the PR description, linked ticket/acceptance criteria, design doc. Access patterns come from here, not from code.
2. **Design-surface diff** of the change (see `references/checklist.md` § Design surface).
3. **Companion changes**: other PRs that deliver the same requirement in other repos (same ticket key in branch names or titles). Read their descriptions and design surface; the requirement is met by the set, not by one diff.
4. **Existing design surface** of the same repo and, when available, sibling repos: stores, buses, roles, shared services that already exist (recipe in step 3).
5. **Existing fitness rules**: policy-as-code, architecture tests, or repo scripts that assert on infrastructure (see `references/fitness-functions.md`).

## What counts as design surface

Read a file when it **declares** structure: infrastructure templates, migrations and schema files, contract and event-schema files, route and permission maps, type/interface declarations for stored or exchanged data, config key definitions, pipeline definitions, design docs.

Grey zone: a file named like a schema, route map or config can still contain logic. Read its declarations or its diff only; anything that needs its logic goes to the hand-off list. Never open handlers, services, adapters, utilities or tests. Runtime guards and validators (hash guards, policy checks, permission evaluators) are logic too: turn questions about them into hand-off items instead of opening them. List every grey-zone file you read in the report's Scope section.

## Workflow

### 1. Collect the design surface

Fetch first: `git fetch` only updates remote-tracking refs, so it is safe in a read-only review, and a stale base hides conflicts and moved generated artifacts. Use the PR's target branch when known. Otherwise detect the trunk:

```bash
TRUNK=$(git symbolic-ref --short refs/remotes/origin/HEAD 2>/dev/null || echo origin/main)
BASE=$(git merge-base "$TRUNK" HEAD)
git diff "$BASE"...HEAD --name-only
git diff "$BASE"...HEAD --stat
```

Filter to design-surface paths. If nothing matches, report "no design surface changed" and stop. Otherwise read each changed design file's diff and the full definitions of any resource it adds.

### 2. Sketch the components

Write a short component sketch from the design surface alone:

- **Added / changed components**: stores (with key schema and indexes), buses/queues/topics, functions/services, routes, schedules, roles.
- **Flows**: what triggers what, which component writes which store, which events each consumer subscribes to, and which components feed the same state.
- **Boundaries**: which identity each component runs as, which config each reads and when (deploy time or runtime), where retries and dead-letter queues sit, log retention.

A plain text list or ASCII diagram is enough. This sketch is the evidence base for every question below.

### 3. Look at what already exists

Bounded searches, names first, open only matching files:

- **Consumers** of anything removed or renamed (events, fields, routes, tables): `git grep -l <name>` in each sibling repo's default branch.
- **Existing capability**: search infrastructure and pipeline definitions and design docs for the capability the change adds (for example: notification, email, audit, scheduler, queue, cache). A parallel mechanism needs a reason.
- **Companion changes**: branches or PRs carrying the same ticket key.

Stop when each search has answered its question. Do not read sibling application code.

### 4. State the access patterns and map them to the store

From the requirements, list how the data will actually be used: who writes and reads, how often, queries (lookups, lists, filters, sort orders, paging, search), tenancy (whose data, who may see which rows), consistency and ordering, retention, audit and deletion.

Then, for **every** store the change adds or changes, fill this table from its key schema, indexes and constraints:

| Access pattern (from requirements) | Served by (key / index / query) | Needs a filter outside the key? | Tenant-scoped by key? | Verdict |
|---|---|---|---|---|

A pattern that needs a post-limit filter, a scan, an unindexed sort, or a tenant scope the keys do not carry is a **store-fit question**. It belongs in this report, not in the hand-off list: the key schema already shows it. Example: a list of "open" items served by an index keyed on kind and time, with "open" as a plain attribute, returns pages that are empty but still carry a cursor.

### 5. Run the checklist

Go through `references/checklist.md`. For each category, compare the sketch (step 2) and the access-pattern map (step 4) against the requirements and obligations. Only raise a question when something concrete is threatened. Each question needs:

- **Evidence**: the design-surface file and line that prompts it.
- **Requirement at risk**: an acceptance criterion, an access pattern, or an obligation. Obligations include the organisation's standing controls (least privilege, credential access controls, retention and audit policy, data protection), even when the ticket does not repeat them.
- **Likely failure**: one concrete scenario (input and state, then the wrong outcome).
- **Options**: at least one alternative design, with its trade-off.
- **Checkable?**: whether a deterministic rule could catch this next time (fitness-function candidate).
- **Goes away if**: the condition under which the question is moot, when it depends on something the design surface cannot show (for example, "if the state is already part of the index key").

### 6. Run fitness rules

Run the repo's existing rules (third-party tools and repo scripts that assert on infrastructure) on the changed files and report results. Do not install dependencies into the target checkout: use an existing install, or skip the check and say so. When a question from step 5 is objectively checkable and likely to recur, propose a rule (`references/fitness-functions.md`). Do not add rules to the repo unless asked.

### 7. Report

```markdown
## Design review: <change title>

**Verdict:** PROCEED | DISCUSS | REDESIGN
(PROCEED = no design questions that threaten a requirement. DISCUSS = questions the author or requirement owner should answer before code review. REDESIGN = the design cannot meet a stated requirement without changing a component.)

### Scope
Base and head (with when each was last fetched), design-surface files read, grey-zone files read (and why), companion changes read, sibling searches run.

### Component sketch
<from step 2>

### Access patterns and store fit
<from step 4, including the mapping table>

### Design questions (at most five, most consequential first)
1. **<question>**
   - Evidence: `path:line`
   - Requirement at risk: ...
   - Likely failure: ...
   - Options: ...
   - Fitness-rule candidate: yes/no (rule sketch if yes)

### Lesser questions
<one line each, with `path:line`>

### Checked, no question
<what was checked and found sound, one line each>

### Fitness rules
<rules run and results; proposed new rules>

### Hand-off to code review
<questions only code can answer, to include in the code reviewers' prompts>
```

Order questions by how many downstream problems each one explains. A question that would remove a whole class of code findings (store fit, event topology, identity) goes above questions about single behaviours. Between questions of similar reach, an obligation (security, compliance, audit, retention) ranks first.

## Rules

- **Do not read implementation logic.** See "What counts as design surface". Generated code and lockfiles are out of scope.
- **Requirements first.** Every question names the requirement or obligation it threatens. "I would have used X" is not a finding.
- **Questions, not verdicts, when the trade-off is real.** If the author may have a good reason (cost, latency, team skills, an existing constraint), ask instead of asserting.
- **Prefer the organisation's existing patterns.** If the repo or its siblings already solve this (a shared store, a notification service, a scheduler, an audit store), a new parallel mechanism needs a reason, agreed by the requirement owner rather than only by the author.
- **Name symptoms you can predict.** If a design choice will show up as specific bugs, say which ones (see the symptom map in `references/checklist.md`), so the code review can confirm them quickly.
- **No style or naming nits.** Those belong to the code review.
- **Read-only.** Do not modify, commit or push anything in the target or sibling repos.
- **Incidental findings.** If you come across a secret (token, key, password) while reading, never copy its value. Report the file paths separately to the user, outside the design report.

## Integration

- **comprehensive-pr-review**: triage matches changed paths against `design_paths` in its `config/dispatch.json`. A hit dispatches `design-review` before the code-review leaves, and its "Hand-off to code review" questions are appended to every leaf prompt.
- **Standalone PR reviews** (any reviewer, any runtime): run this skill as step zero, then start the code reviewers with its hand-off questions in their prompts. Put a REDESIGN or DISCUSS verdict at the top of the review summary.
- **Design docs / tickets**: run steps 2 to 7 on the document instead of a diff. The sketch then comes from the document.
