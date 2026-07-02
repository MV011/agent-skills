# Local Quality Gates — Semgrep & LucidShark

Full commands, install instructions, and result-handling for the deterministic gates that run before agent dispatch (SKILL.md Step 3). These tools produce evidence-based findings (exact rule ID + file:line) — higher confidence than any agent review.

This pipeline uses **no external review bots** (CodeRabbit, Greptile, or similar). Local gates are Semgrep + LucidShark; everything else is the skill's own review agents.

## Semgrep SAST scan

**Detect availability:**

```bash
if command -v semgrep &>/dev/null; then SEMGREP_AVAILABLE=true; else SEMGREP_AVAILABLE=false; fi
```

**Scan only changed source files:**

```bash
CHANGED_SRC=$(git diff $MERGE_BASE...HEAD --name-only | grep -E '\.(cs|ts|tsx|js|jsx|py|go|rb|java)$')

if [ -n "$CHANGED_SRC" ] && [ "$SEMGREP_AVAILABLE" = true ]; then
  # Core security rules (language-agnostic)
  semgrep scan \
    --config "p/owasp-top-ten" \
    --config "p/cwe-top-25" \
    --config "p/security-audit" \
    --json --output /tmp/semgrep-results.json \
    $CHANGED_SRC 2>/dev/null

  # Language-specific rules based on detected files
  CS_FILES=$(echo "$CHANGED_SRC" | grep '\.cs$')
  [ -n "$CS_FILES" ] && semgrep scan --config "p/csharp" --json --output /tmp/semgrep-csharp.json $CS_FILES 2>/dev/null

  TS_FILES=$(echo "$CHANGED_SRC" | grep -E '\.(ts|tsx)$')
  [ -n "$TS_FILES" ] && semgrep scan --config "p/typescript" --config "p/react" --json --output /tmp/semgrep-ts.json $TS_FILES 2>/dev/null

  PY_FILES=$(echo "$CHANGED_SRC" | grep '\.py$')
  [ -n "$PY_FILES" ] && semgrep scan --config "p/python" --json --output /tmp/semgrep-python.json $PY_FILES 2>/dev/null

  GO_FILES=$(echo "$CHANGED_SRC" | grep '\.go$')
  [ -n "$GO_FILES" ] && semgrep scan --config "p/golang" --json --output /tmp/semgrep-go.json $GO_FILES 2>/dev/null
fi
```

**Handling results:**

- Semgrep findings are **evidence-based** (exact rule ID + file:line) — treat them as 95%+ confidence.
- Include them as CRITICAL or HIGH findings in the consolidated report.
- Semgrep findings corroborate agent findings when both flag the same area — the strongest corroboration signal.
- If Semgrep is not installed, note it in the report and rely on the agent-based security review.

**Install:** `pip install semgrep` (one-time, runs locally, free for open-source and local use). CI can run it via `.github/workflows/semgrep.yml`.

## LucidShark unified quality gate

[LucidShark](https://lucidshark.com/) is a local-first CLI that bundles linting, formatting, type checking, SAST, SCA, IaC checks, container scanning, tests, coverage, and duplication analysis.

**Binary install (macOS/Linux, user-wide):**

```bash
mkdir -p ~/.local/bin
VER=$(curl -fsSL https://api.github.com/repos/toniantunovi/lucidshark/releases/latest | grep '"tag_name":' | sed -E 's/.*"([^"]+)".*/\1/')
OS=$(uname -s | tr '[:upper:]' '[:lower:]')
ARCH=$(uname -m); case "$ARCH" in x86_64|amd64) A=amd64;; arm64|aarch64) A=arm64;; *) echo "unsupported arch"; exit 1;; esac
curl -fsSL "https://github.com/toniantunovi/lucidshark/releases/download/${VER}/lucidshark-${OS}-${A}" -o ~/.local/bin/lucidshark
chmod +x ~/.local/bin/lucidshark
```

Ensure `~/.local/bin` is on `PATH`. **MCP (optional):** `lucidshark serve --mcp` exposes tools to agents; register that command in each runtime's MCP config (see **LucidShark** in `docs/install.md` in the `MV011/agent-skills` repository for copy-paste snippets).

**Detect availability:**

```bash
if command -v lucidshark &>/dev/null; then LUCIDSHARK_AVAILABLE=true; else LUCIDSHARK_AVAILABLE=false; fi
```

**Run against the PR (scope to the detected base branch):**

```bash
if [ "$LUCIDSHARK_AVAILABLE" = true ]; then
  # Scope deliberately EXCLUDES --all. LucidShark already defaults to
  # changed-files-only, but --all ALSO enables the heavyweight domains
  # (--testing, --coverage, --duplication/duplo, --sca/Trivy) — these are
  # whole-program / whole-dependency-tree passes that CI already runs and that
  # saturate a multi-worktree dev machine when many worktrees scan at once.
  # Keep only the fast, diff-scoped static checks agent review benefits from.
  # Re-add a heavy domain explicitly only for a deliberate one-off deep pass.
  LUCIDSHARK_DOMAINS="--linting --type-checking --formatting --sast"
  if [ -n "$BASE" ]; then
    lucidshark scan $LUCIDSHARK_DOMAINS --base-branch "origin/$BASE" --format ai 2>&1 | tee /tmp/lucidshark-pr-review.txt
  else
    lucidshark scan $LUCIDSHARK_DOMAINS --format ai 2>&1 | tee /tmp/lucidshark-pr-review.txt
  fi
  LUCIDSHARK_EXIT=$?
else
  LUCIDSHARK_EXIT=0
fi
```

Use `--format json` if you need machine parsing; `--format ai` is optimized for agent consumption.

**First-time repos:** If there is no `lucidshark.yml`, run `lucidshark init` in the project (or `lucidshark doctor`) so configuration exists; otherwise the scan may fail or be noisy.

**Handling results:**

- Non-zero exit or any reported issues → fold into the consolidated report with the same severity ladder as other gates.
- Treat findings as **high-confidence** when the tool names a rule and file location (similar to Semgrep).
- LucidShark overlaps Semgrep/SAST on security; when both agree, treat as corroboration.
- If LucidShark is not installed, note that in the report; do not skip the rest of the review.
