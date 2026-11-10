# Design Review Checklist

Use each category as a prompt, not a form. Raise a question only when a concrete requirement is at risk, and cite the design-surface line that prompts it.

## Design surface

Files the review reads (adapt the globs to the repo):

Declarative files only; see "What counts as design surface" in SKILL.md for grey-zone files.

- Infrastructure-as-code: `**/*.tf`, `**/template.y*ml`, `**/cloudformation/**`, `**/serverless*.y*ml`, `**/cdk/**`, `**/*.bicep`, `**/pulumi/**`, `**/k8s/**`, `**/helm/**`, `**/docker-compose*.y*ml`, `**/Dockerfile`
- Data definitions: `**/migrations/**`, `**/Migrations/**` (EF Core: read the migration, skip `*.Designer.cs` and `*ModelSnapshot.cs`), `**/*.sql`, `**/schema*.{prisma,graphql,json,ts}`, `**/schemas/**`, `**/Schemas/**`, ORM model/schema files
- Contracts: `**/openapi*.{y*ml,json}`, `**/*.proto`, `**/asyncapi*`, `**/*contract*`, `**/*.Contracts/**`, `**/api-contracts/**`, event schema files, JSON schemas
- Routing and access: route maps, ACL/permission maps (`**/permission*/**`, `**/Permission*/**`), gateway configs, IAM policies. In .NET the controllers and endpoint classes are the route map, so `**/Controllers/**` and `**/Endpoints/**` are grey-zone files: read the route, verb and authorization declarations in the diff, never the method bodies
- Config: environment/parameter definitions, feature-flag definitions, CI/CD pipeline definitions
- Design docs: `**/docs/**/*.md` ADRs/HLDs touched by the change

Not in scope: application source, tests, generated files, lockfiles.

## 1. Data store fit

- Does the store support every access pattern in the requirements natively? Lists, filters, sorts, paging, ad-hoc operator queries, joins with existing data.
- Key-value / document stores: does a "list with filter" rely on a filter applied after the page limit (pages that come back empty but still carry a cursor)? Is there a scan? Does a single index carry several entity kinds?
- Is ordering or deduplication state being hand-built with conditional writes where the store, or an existing component, already provides it?
- Is there already a system of record for this data? A second store for the same entity needs a reason and a sync story.
- Backups / point-in-time recovery, encryption, retention / TTL, deletion obligations.
- Growth: unbounded tables or partitions, hot keys.

## 2. Tenancy and authorization

- Does every row/message carry the owner or tenant key that consumers must scope by?
- Where is authorization enforced: in the service that owns the data, at the gateway, or only in a UI? UI-only checks are not authorization.
- Can a consumer with a coarse permission read data across tenants through a new list endpoint?

## 3. Event and data-flow topology

- Does any component update the same state from more than one input (a raw event plus a derived event, a webhook plus a poll)? Those inputs race; ordering must be designed, not patched.
- Idempotency and dedupe keys: do they identify the real-world occurrence, or a state value that can legitimately repeat?
- Versioning: can two messages share a version? What wins?
- Replay / redrive: what happens when an old message is reprocessed days later? Do derived timestamps (deadlines, due dates) come from the event or from processing time?
- Removed or renamed events/fields: who consumed them (search sibling repos)?

## 4. Failure semantics

- List every retry layer (client SDK, handler loop, function runtime, trigger/rule, queue redelivery). Is the total intentional? Do non-transient failures get retried pointlessly while transient ones get none?
- Know what each layer covers. An event rule's retry policy usually covers delivery to the target only; handler errors are retried (or not) by the function runtime's own asynchronous retry setting. Counting both as "retries" overstates coverage.
- Dead-letter destinations: what message formats land there, and does the runbook handle each?
- What does an operator see when it fails: an alarm only, or a visible record in the product? Does every failure path leave that record, including config and permission failures that happen before the main write?
- Redrive: does replaying a failed message reach only the consumer that failed, or every subscriber on a shared bus or topic (double processing by unrelated consumers)? Does the runbook's replay step match each dead-letter message format?
- Partial failure between two writes (claim then send; send then record): which state is left, and does a retry fix it or skip it?

## 5. Identity and permissions

- Does each component run as its own identity? A new component reusing an existing role widens that role for both.
- Wildcard resources or actions. Permissions granted to a public-facing component that only a background component needs.
- Secrets and credentials: who can read them, and does the new component need to?

## 6. Configuration

- Deploy-time vs runtime config: what happens when a value is missing? Does the deploy fail loudly, or does the first real event fail at runtime?
- Per-environment values that must exist before go-live: listed in the change?
- Values the requirements say must be configurable (thresholds, windows, recipients): are they config or constants?

## 7. Contracts and consumers

- Producer/consumer field names and shapes match across services and repos.
- Backward compatibility and deploy order: can producer and consumer deploy in either order?
- Paging/cursor contracts: opaque, validated, bounded.

## 8. Observability and audit

- Log and record retention vs the change's audit or regulatory class. Inconsistent retention inside one stack is a smell.
- Is the audit record the requirements ask for (who, what, when, to whom, outcome) actually persisted somewhere, not just logged?
- Alarms: on what, routed where, with a runbook that matches reality?

## 9. Rollout

- Acceptance coverage: does every acceptance criterion map to a component somewhere in the change set (including companion changes)? A criterion with no component is a scope gap.
- Derived artifacts (hashes, counts, generated maps, snapshots) computed on a base that has since moved: check them against the freshly fetched target.
- Deploy order across services and repos; config that must exist first.
- Existing state at deploy time: does the new component need a backfill to see data that already exists?
- Feature flags / kill switches for anything that moves money or contacts people.
- Reversibility of migrations and data shape changes.

## 10. Reuse and deviations

- Does the organisation already have a component for this (notifications, scheduling, storage, audit)? A parallel mechanism needs a stated reason.
- Deviations from the ticket's technical notes: stated, and agreed by the requirement owner rather than only by the author?

## Symptom map

Design choices with predictable code-level symptoms. When you see the cause, tell the code review which symptoms to confirm.

| Design cause | Predictable symptoms |
|---|---|
| Key-value store backing a filtered, paged list | Empty pages with a cursor; "nothing found" while matching rows exist; no tenant scoping |
| One state fed by two event inputs | Ordering races; strict vs non-strict version comparisons disagreeing; stale state resurrected |
| Dedupe key built from a status value | A legitimately repeated status is suppressed |
| Deadline computed at processing time | Deadlines drift on retries, redrives and follow-ups |
| Shared execution role | New permissions leak to an unrelated, often public, component |
| Runtime-only required config | First production event fails; failure invisible outside alarms |
| Retry only around one dependency | Other transient failures go straight to dead-letter |
| No backfill for a new watcher | Items that existed before deploy are never processed |
| Trigger retry policy counted as handler retries (function async retries at zero) | Handler errors go straight to dead-letter; short outages need manual redrive |
| Per-item state overwritten by each new event | Earlier delivery results and audit facts are lost; the record shows only the latest |
