# Fitness Functions

A fitness function is an automated, objective check of an architectural characteristic: a test for the shape of the system rather than its behaviour. Design review is judgement; fitness functions are the part of that judgement that can be made deterministic and run in CI on every change.

Use them to stop re-asking the same design question. When a design question is objectively checkable and has come up before, propose a rule.

## Detect what the repo already has

```bash
ls .cfn-guard* guard/ rules/ policies/ 2>/dev/null       # cfn-guard
ls .checkov* .conftest* policy/ 2>/dev/null              # checkov / OPA conftest
ls .tflint.hcl 2>/dev/null                               # tflint
ls .dependency-cruiser* 2>/dev/null                      # JS/TS dependency rules
grep -rl "ArchRule\|archunit" --include=*.java . 2>/dev/null | head -1   # ArchUnit
ls .importlinter setup.cfg 2>/dev/null                   # Python import-linter
```

Also look for repo-specific checks that assert on infrastructure: scripts named like `check-*`, `lint-*` or `verify-*` under `scripts/`, and the lint or test steps in `package.json`, `Makefile` and CI definitions. Reading such a script to run it safely is in scope.

Run whatever exists, on the changed files where the tool allows it, and report pass/fail per rule. Do not install dependencies into the target checkout: reuse an existing install of the same version (for Node, point `NODE_PATH` at another checkout's `node_modules`), or skip the check and report it as not run.

## Tools by ecosystem

| Surface | Tools |
|---|---|
| CloudFormation / SAM | cfn-guard, cfn-lint custom rules, checkov |
| Terraform | checkov, tflint, OPA conftest, Sentinel |
| Kubernetes / Helm | OPA conftest, kyverno, kube-linter |
| Code structure (layers, dependencies) | ArchUnit (JVM), dependency-cruiser (JS/TS), import-linter (Python), go-arch-lint |
| Contracts | OpenAPI/AsyncAPI linters (spectral), schema compatibility checks |

## Rule patterns worth proposing

Expressed generically; translate into the repo's tool.

- **One identity per compute unit**: no two functions/services reference the same execution role.
- **No wildcard send/write on public components**: a component behind a public route has no `*` resource on messaging, email or data-write actions.
- **Data protection defaults**: every table/bucket has encryption, point-in-time recovery or versioning, and a declared retention.
- **Retention consistency**: log retention for components in an audit class is at least the class minimum.
- **Failure wiring**: every asynchronous consumer declares its retry policy and a dead-letter destination, and every dead-letter destination has an alarm.
- **Tenant key present**: every new table or event schema in a multi-tenant system includes the tenant/owner attribute.
- **Layering**: UI packages do not import data-access packages; services do not import another service's internals.
- **Contract compatibility**: a removed or renamed event/field fails CI unless explicitly marked as a breaking change.

## Example: cfn-guard

```text
# Every DynamoDB table enables point-in-time recovery.
let tables = Resources.*[ Type == 'AWS::DynamoDB::Table' ]
rule tables_have_pitr when %tables !empty {
  %tables.Properties.PointInTimeRecoverySpecification.PointInTimeRecoveryEnabled == true
}
```

Run: `cfn-guard validate --rules rules/ --data path/to/template.yml`. Guard syntax varies between versions: validate any proposed rule against the repo's templates before committing it.

## Example: dependency-cruiser

```js
module.exports = {
  forbidden: [
    {name: 'ui-not-to-data-access', from: {path: '^src/ui'}, to: {path: '^src/data'}, severity: 'error'},
  ],
};
```

## When not to write a rule

- The question depends on requirements a tool cannot see (is this the right store for these access patterns?). Keep it in design review.
- The rule would need many exceptions to pass on the current codebase. Fix the design first or scope the rule to new resources.
