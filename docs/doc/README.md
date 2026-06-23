# 🧹 cleanmac — English Guide

> **AI-first macOS cleanup CLI · Ephemeral execution · Dry-run first · MCP integration · Zero dependencies**

cleanmac is an **AI-first cleanup execution kernel**. It does not compete on GUI/TUI retention, does not install resident background surfaces, and is designed to run once for an explicit user/script/AI Host request, emit machine-readable evidence, then exit.

[![🏠 Home](../../README.md)](/README.md) · [![📕 中文文档](README.CN.md)](README.CN.md)

---

## 📋 Table of Contents

- [✨ Capabilities](#-capabilities)
- [🚀 Quick Start](#-quick-start)
- [🤖 AI Invocation Patterns](#-ai-invocation-patterns)
  - [📦 AI Tool Definitions](#-ai-tool-definitions)
  - [🏗️ MCP Server](#️-mcp-server)
  - [🧭 AI Workflow Pipeline](#-ai-workflow-pipeline)
  - [🔐 AI Confirmation Token](#-ai-confirmation-token)
  - [🤝 Claude Desktop Configuration](#-claude-desktop-configuration)
  - [🧪 AI Host Commands](#-ai-host-commands)
- [📦 Installation](#-installation)
- [🛡️ Safety Model](#️-safety-model)
- [⌨️ Command Reference](#️-command-reference)
- [🧪 Sandbox & Filters](#-sandbox--filters)
- [🗂️ Category Overview](#️-category-overview)
- [✅ Development & CI](#-development--ci)

---

## ✨ Capabilities

`cleanmac` provides **30+ capabilities** for macOS cleanup, operational review, and AI-host integration:

`cleanmac` is intentionally **AI-first, not app-first**: it runs only when invoked by a user, script, or AI host; it exits after the requested workflow; it does not provide a resident GUI/TUI, menu bar agent, login item, background daemon, unsolicited scan loop, reminder system, or idle CPU/memory footprint. Durable state is represented as JSON plans, review-selection files, explicit reports, and operation logs.

| # | Capability | Description |
|---|---|---|
| 🧹 | **Category management** | List keys, titles, paths, risk levels |
| 📊 | **Space analysis** | Estimate reclaimable space, no deletion |
| 🔎 | **Candidate inspection** | List files with sort, recursion, filters |
| 🩺 | **Diagnosis** | Risk-based cleanup recommendations |
| 🧾 | **Script audit** | Read-only action plan review |
| 🧭 | **Workflow** | Multi-phase safe pipeline (inspect → diagnose → plan) |
| 🗺️ | **Plans** | Reusable `cleanmac.plan.v1` JSON |
| 📄 | **Reports** | Pre-clean, dry-run, post-execution, audit |
| 🧪 | **Sandbox** | `--root` / `--home` path remapping |
| 🤖 | **AI tools** | 36 tools in Anthropic / OpenAI / MCP formats |
| 🏗️ | **MCP Server** | stdio-based Model Context Protocol server |
| 🧾 | **Review selections** | `cleanmac.review-selection.v1` files constrain clean, startup, and privacy execution |
| 🔍 | **Operational preflight** | Permissions, startup, privacy, and external-tool dry-run planning |
| 🔐 | **Confirmation token** | SHA-256 bound AI execution authorization |
| 🛡️ | **Execution guards** | Budget, risk policy, live-root protection |
| 🎯 | **Filters** | Include, exclude, age, size, regex |
| 🧰 | **Doctor** | Environment & permission diagnostics |
| 🪟 | **Previews** | Finder `open`, symlink `links` |
| 🔐 | **Bundle protection** | Allow/block policies for app containers |
| ♻️ | **Trash mode** | Recoverable deletion routing |
| 📜 | **Operation log** | Persistent JSONL audit trail |
| 💤 | **Zero-resident runtime** | No GUI/TUI, daemon, login item, unsolicited scan, or background resource use |
| 🧾 | **Deletion log** | Forensic TSV records |
| ⏱️ | **Debug timing** | Millisecond PERF logging |
| 🧪 | **Test mode** | Auth guards for CI/testing |

`cleanmac` is an independent Python implementation — no vendored external macOS cleanup sources, no affiliation with other cleanup projects.

---

## 🚀 Quick Start

```bash
# 1️⃣ Check environment
python3 cleanmac.py capabilities
python3 cleanmac.py --json doctor

# 2️⃣ List categories
python3 cleanmac.py clean list
python3 cleanmac.py --json clean list

# 3️⃣ Inspect candidates (dry-run, no deletion)
python3 cleanmac.py --json clean inspect \
  --categories trash,mails,xcode \
  --older-than-days 7 \
  --max-delete-mb 500 \
  --limit 100 \
  > /tmp/inspect.json

# 4️⃣ Generate plan
python3 cleanmac.py --json clean plan \
  --categories trash,mails,xcode \
  --max-delete-mb 500 \
  > /tmp/plan.json

# 5️⃣ Dry-run from plan
python3 cleanmac.py --json clean run \
  --plan-file /tmp/plan.json \
  --require-plan-context

# 5b️⃣ Optional: normalize the plan into reviewable selections
python3 cleanmac.py --json review \
  --input-file /tmp/plan.json \
  --selection-file /tmp/selection.json

# 5c️⃣ Optional: explain the plan/report for AI or human review
python3 cleanmac.py --json explain \
  --input-file /tmp/plan.json

# 6️⃣ Execute (after review!)
python3 cleanmac.py clean run \
  --plan-file /tmp/plan.json \
  --review-selection-file /tmp/selection.json \
  --require-plan-context \
  --delete-mode trash \
  --operation-log /tmp/ops.jsonl \
  --execute
```

> 🛡️ **Safety:** `clean run` without `--execute` is always a dry-run. High-risk categories require `--yes`. Live root `/` requires `--allow-live-root`.

---

## 🤖 AI Invocation Patterns

`cleanmac` is **AI-native** — it provides structured tool definitions, an MCP server, and a confirmation token system for safe AI-driven cleanup.

### 📦 AI Tool Definitions

Export **36 tools** in three formats:

```bash
# 🧠 Anthropic format (Claude)
python3 cleanmac.py --json ai-tools --format anthropic | jq '.tools | keys'

# 🟢 OpenAI format (GPT)
python3 cleanmac.py --json ai-tools --format openai | jq '.tools | length'

# 🔧 MCP format (any MCP client)
python3 cleanmac.py --json ai-tools --format mcp | jq '.tools | length'
```

Tool categories:

| 🤖 Tool | 📝 Description | 🏷️ Risk |
|---|---|---|
| `cleanmac_capabilities` | Describe commands, categories, guardrails | readonly |
| `cleanmac_doctor` | Environment & permission diagnostics | readonly |
| `cleanmac_list_categories` | List all cleanup categories | readonly |
| `cleanmac_diagnose` | Analyze & recommend cleanup actions | readonly |
| `cleanmac_inspect` | Preview candidates, no deletion | readonly |
| `cleanmac_analyze_categories` | Estimate reclaimable space | readonly |
| `cleanmac_analyze_tree` | Scan directory tree for large entries | readonly |
| `cleanmac_status_snapshot` | Read-only system health snapshot | readonly |
| `cleanmac_scripts` | List command templates | readonly |
| `cleanmac_open` | Preview/show Finder targets | readonly |
| `cleanmac_links` | Preview/manage symlink mappings | readonly |
| `cleanmac_optimize` | List/plan maintenance tasks | planning |
| `cleanmac_generate_plan` | Generate cleanup plan | planning |
| `cleanmac_validate_plan` | Validate a plan file | planning |
| `cleanmac_workflow` | Multi-phase safe workflow | readonly |
| `cleanmac_policy_simulate` | Simulate policy enforcement | planning |
| `cleanmac_software_list` | Read-only app inventory | readonly |
| `cleanmac_software_leftovers` | Inspect app leftovers | readonly |
| `cleanmac_software_startup_items` | List startup items | readonly |
| `cleanmac_software_uninstall_plan` | Plan uninstall (no execution) | planning |
| `cleanmac_software_inspect` | Inspect app cleanup candidates | readonly |
| `cleanmac_startup_audit` | Audit LaunchAgents/Daemons and StartupItems | readonly |
| `cleanmac_startup_plan` | Plan startup item disable actions without execution | planning |
| `cleanmac_startup_disable` | Disable reviewed user startup plists (requires confirmation) | destructive |
| `cleanmac_privacy_inspect` | Inspect browser/app privacy cleanup candidates | readonly |
| `cleanmac_privacy_plan` | Plan privacy cleanup without deleting data | planning |
| `cleanmac_privacy_execute` | Permanently delete reviewed privacy data (requires confirmation) | destructive |
| `cleanmac_tool_plan` | Render semantic plans for external tools | planning |
| `cleanmac_tool_execute_dry_run` | Dry-run allowlisted external tool commands | dry-run |
| `cleanmac_review` | Normalize reports/plans into review selections | planning |
| `cleanmac_dry_run_plan` | Dry-run a plan with Trash routing | dry-run |
| `cleanmac_execute_plan` | Execute cleanup (requires confirmation) | destructive |
| `cleanmac_ai_governance_advice` | AI host governance & anti-patterns | readonly |
| `cleanmac_ai_host_policy` | AI host allow/deny policy | readonly |

### 📄 AI Contract Introspection

```bash
# 🔍 Full AI safety contract
python3 cleanmac.py --json capabilities | jq '.ai_contract'

# 🛡️ Safety guardrails
python3 cleanmac.py --json capabilities | jq '.safety_guardrails'

# 🧰 Tool definitions schema
python3 cleanmac.py --json ai-tools --format anthropic | jq '.tools[0]'
```

### 🏗️ MCP Server

Start the **Model Context Protocol** stdio server:

```bash
# ▶️ Direct start
python3 scripts/cleanmac_mcp_server.py

# 🧪 Test mode (safe for development)
CLEANMAC_TEST_MODE=1 CLEANMAC_TEST_NO_AUTH=1 \
  python3 scripts/cleanmac_mcp_server.py
```

**JSON-RPC 2.0 protocol example:**

```bash
# 📋 List all 34 tools
echo '{"jsonrpc":"2.0","id":1,"method":"tools/list"}' | \
  CLEANMAC_TEST_MODE=1 CLEANMAC_TEST_NO_AUTH=1 \
  python3 scripts/cleanmac_mcp_server.py | jq '.result.tools | length'

# 🎯 Call capabilities tool
echo '{"jsonrpc":"2.0","id":2,"method":"tools/call","params":{"name":"cleanmac_capabilities","arguments":{}}}' | \
  CLEANMAC_TEST_MODE=1 CLEANMAC_TEST_NO_AUTH=1 \
  python3 scripts/cleanmac_mcp_server.py | jq '.result.content[0].text' | head -5
```

Verify the server works:

```bash
make mcp-smoke
# ✅ Output: mcp-smoke passed

make mcp-meta-index-smoke
# ✅ Output: mcp-meta-index-smoke passed

make mcp-resource-index-smoke
# ✅ Output: mcp-resource-index-smoke passed

make mcp-prompt-index-smoke
# ✅ Output: mcp-prompt-index-smoke passed

make mcp-tool-index-smoke
# ✅ Output: mcp-tool-index-smoke passed

make mcp-surface-audit-smoke
# ✅ Output: mcp-surface-audit-smoke passed

make ai-host-smoke
# ✅ Output: ai-host-smoke passed
```

AI Hosts should start with `cleanmac://mcp/meta-index` (`cleanmac.mcp-meta-index.v1`), then follow the governed call sequence to `cleanmac://mcp/resource-index` (`cleanmac.mcp-resource-index.v1`), `cleanmac://mcp/prompt-index` (`cleanmac.mcp-prompt-index.v1`), `cleanmac://mcp/tool-index` (`cleanmac.mcp-tool-index.v1`), and `cleanmac://mcp/surface-audit` (`cleanmac.mcp-surface-audit.v1`). Stop orchestration if the surface audit reports `ready=false`.

- `cleanmac://mcp/meta-index` aggregates the governed MCP discovery surface and advertises the recommended call order.
- `cleanmac://mcp/resource-index` lists every MCP resource URI, schema, category, and safety marker.
- `cleanmac://mcp/prompt-index` lists every governed prompt with arguments, categories, and MCP-safe flags.
- `cleanmac://mcp/tool-index` lists every MCP tool with `invocation_mode`, `auto_call_allowed`, `requires_confirmation`, and destructive-policy metadata.
- `cleanmac://mcp/surface-audit` verifies that governed indexes are ready, required resources/prompts/tools are advertised, destructive tools are gated, shell invocation is absent, and sensitive-data policy is present.

All index payloads are sanitized to avoid leaking local paths or credentials.

### 🧭 AI Workflow Pipeline

Recommended AI invocation flow:

```mermaid
graph LR
    A[🤖 AI] -->|1. capabilities| B[🔍 Discover tools]
    B -->|2. diagnose| C[🩺 Analyze system]
    C -->|3. inspect| D[👀 Preview candidates]
    D -->|4. plan| E[🗺️ Generate plan]
    E -->|5. review| F[🧾 Select reviewed items]
    F -->|6. validate| G[✅ Verify plan + selection]
    G -->|7. run --execute| H[🛡️ Execute with token]
```

**Step-by-step for AI:**

```bash
# 🅰️ Pipeline A: diagnose → plan (read-only)
python3 cleanmac.py --json clean inspect --categories trash,downloads --limit 10
python3 cleanmac.py --json plan --categories trash,downloads --max-items 10

# 🅱️ Pipeline B: workflow (single command, recommended!)
python3 cleanmac.py --json workflow \
  --categories trash,downloads \
  --dry-run-scope selected
```

The `workflow` command is the **recommended AI entry point** — it runs inspect → diagnose → plan in one non-destructive call.

### 🧾 Review-to-execution contract

Use `review` to convert a clean, startup, privacy, tool, or software plan/report into `cleanmac.review.v1` plus `cleanmac.review-selection.v1`. Passing that selection into `clean run`, `policy-simulate`, `startup disable`, or `privacy execute` validates the source fingerprint and restricts execution to reviewed selected items only:

```bash
# 1️⃣ Generate a stable plan
python3 cleanmac.py --json clean plan --categories trash,downloads > /tmp/plan.json

# 2️⃣ Produce a review report and default selection file
python3 cleanmac.py --json review \
  --input-file /tmp/plan.json \
  --selection-file /tmp/selection.json \
  > /tmp/review.json

# 3️⃣ Dry-run only the selected reviewed items
python3 cleanmac.py --json clean run \
  --plan-file /tmp/plan.json \
  --review-selection-file /tmp/selection.json \
  --require-plan-context

# 4️⃣ Ask the policy simulator for the safe argv before execution
python3 cleanmac.py --json policy-simulate \
  --plan-file /tmp/plan.json \
  --review-selection-file /tmp/selection.json \
  --execute \
  --delete-mode trash
```

If the selection was generated from a different or stale plan, the command fails before cleanup or disablement with `SELECTION_VALIDATION_FAILED`. The resulting reports include `cleanmac.review-selection-constraint.v1` for auditability. Destructive AI/MCP tools (`cleanmac_execute_plan`, `cleanmac_startup_disable`, and `cleanmac_privacy_execute`) are denied for auto-call and require explicit confirmation.

### 🔐 AI Confirmation Token

For safe AI-originated execution, `cleanmac` uses a **SHA-256 confirmation token** bound to the execution context:

```bash
# 1️⃣ AI generates plan (gets embedded confirmation_token)
python3 cleanmac.py --json plan --categories trash > /tmp/plan.json

# 2️⃣ Extract token
TOKEN=$(python3 -c "
import json
p = json.load(open('/tmp/plan.json'))
print(p['ai_confirmation_summary']['confirmation_token_embedded'])
")

# 3️⃣ Execute with bound token
python3 cleanmac.py --json clean run \
  --categories trash \
  --plan-file /tmp/plan.json \
  --confirmation-token "$TOKEN" \
  --execute
```

Token format: `cleanmac-confirm-<32-hex-chars>` (SHA-256). Same context → same token. Different root, home, or categories → different token.

### 🤝 Claude Desktop Configuration

Add to your `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "cleanmac": {
      "command": "python3",
      "args": ["/absolute/path/to/cleanmac/scripts/cleanmac_mcp_server.py"]
    }
  }
}
```

For Cursor / other MCP clients:

```json
{
  "mcpServers": {
    "cleanmac": {
      "command": "python3",
      "args": ["/absolute/path/to/cleanmac/scripts/cleanmac_mcp_server.py"],
      "env": {
        "CLEANMAC_TEST_MODE": "1",
        "CLEANMAC_TEST_NO_AUTH": "1"
      }
    }
  }
}
```

### 🧪 AI Host Commands

`cleanmac` provides several AI-oriented CLI commands for host integration, introspection, and evaluation:

```bash
# ✅ AI readiness check — verify all AI contracts, tools, and MCP server
python3 cleanmac.py --json ai-readiness

# 📘 AI runbook — show documented AI invocation patterns
python3 cleanmac.py --json ai-runbook

# 🔬 AI self-test — run built-in AI safety self-checks
python3 cleanmac.py --json ai-self-test

# 📊 AI decision matrix — review tool-level MCP annotations and policy
python3 cleanmac.py --json ai-decision-matrix

# 🛡️ AI governance advice — safe LLM calling boundaries and anti-patterns
python3 cleanmac.py --json ai-governance-advice

# 📦 AI eval pack — inspect all evaluation scenarios
python3 cleanmac.py --json ai-eval-pack

# 🏃 AI eval run — execute an evaluation scenario
python3 cleanmac.py --json ai-eval-run --scenario smoke
```

Run all AI host tests together:

```bash
make ai-host-smoke
# ✅ Output: ai-host-smoke passed
```

For release or integration gates, run the governance route check before broad smoke targets:

```bash
make ai-governance-smoke
make ai-contract-smoke
make ai-host-smoke
make mcp-smoke
make mcp-resource-index-smoke
```

The governance route enforces the AI calling policy end to end: entrypoint governance, dry-run-first defaults, destructive auto-call denial, execution preflight gates, prompt-injection boundaries, structured error recovery, MCP host governance, CI/release gates, audit traceability, and anti-pattern checks.

These commands are safe to run in any environment — they are all read-only introspection and validation tools.

---

## 📦 Installation

### ▶️ Run directly (no install)

```bash
git clone https://github.com/cleanmac/cleanmac.git
cd cleanmac
python3 cleanmac.py clean list
```

### 📥 Install as a package

```bash
python3 -m venv .venv
. .venv/bin/activate
python3 -m pip install -e .
cleanmac list
```

### 🍺 Install via Homebrew tap

```bash
brew tap cleanmac/tap
brew trust cleanmac/tap
brew install cleanmac
cleanmac --json capabilities
```

Homebrew 6+ refuses to load formulae from untrusted third-party taps. `brew trust cleanmac/tap` trusts this tap explicitly. For a narrower trust scope, use `brew trust --formula cleanmac/tap/cleanmac` before installing.

Release automation generates `release-assets/cleanmac.rb` with `scripts/generate_homebrew_formula.py`, includes it in `cleanmac.release-artifact-manifest.v1`, and validates it with `make homebrew-formula-smoke`. If a future Homebrew core formula with the same name exists, use `brew install cleanmac/tap/cleanmac` to select the tap explicitly.

### 🐍 Requirements

- Python 3.10+
- macOS (primary) / Linux (limited support)
- No external dependencies required

### 🔧 Install with extras

```bash
python3 -m pip install -e '.[dev,build]'   # development + build
python3 -m pip install -e '.[test]'         # test dependencies
python3 -m pip install -e '.[lint]'         # linting tools
```

---

## 🛡️ Safety Model

### 🧯 Dry-run by default

```bash
python3 cleanmac.py clean run --categories trash
# 👆 Preview only, no files deleted
```

### 🔴 Real deletion requires `--execute`

```bash
python3 cleanmac.py --root /tmp/sandbox --home /Users/tester clean run \
  --categories trash --execute
```

### 🟡 High-risk categories require `--yes`

```bash
python3 cleanmac.py clean run --categories downloads --execute --yes
```

### 🧱 Live-root protection

```bash
python3 cleanmac.py clean run --categories trash --execute --allow-live-root
```

### 🚦 Risk policies

| Policy | Description |
|---|---|
| `default` | high / critical require `--yes` |
| `strict` | medium / high / critical all require `--yes` |
| `permissive` | No extra `--yes` from risk level |

### 🔐 Bundle protection

| Policy | Behavior |
|---|---|
| `--bundle-allowlist <ids>` | Only allow-listed bundle candidates pass |
| `--bundle-blocklist <ids>` | Blocklisted bundle candidates are skipped |
| Default | Apple/iCloud/system bundles protected |

### ♻️ Trash mode

```bash
python3 cleanmac.py clean run \
  --categories downloads \
  --delete-mode trash \
  --execute \
  --yes
```

> `--delete-mode trash` moves files to `~/.Trash/cleanmac-*` for recovery. `--delete-mode permanent` removes directly.

### 📜 Operation log

Default paths: `~/.cleanmac/operations.jsonl` (JSONL audit trail, schema `cleanmac.operation-log-entry.v1`), `~/.cleanmac/deletions.log` (text log), `cleanmac_debug_session.log` (debug timing).

```bash
python3 cleanmac.py clean run \
  --plan-file /tmp/plan.json \
  --operation-log /tmp/ops.jsonl \
  --execute
```

---

## ⌨️ Command Reference

### 🧭 Top-level groups

| Group | Commands | Description |
|---|---|---|
| `clean` | `list`, `inspect`, `plan`, `validate-plan`, `run`, `scripts`, `open`, `links` | 🧹 Cleanup operations |
| `software` | `list`, `leftovers`, `startup-items`, `uninstall-plan` | 📦 App inventory (read-only) |
| `startup` | `audit`, `plan`, `disable` | 🚀 Startup item audit, disable planning, and reviewed disable execution |
| `privacy` | `inspect`, `plan`, `execute` | 🔐 Browser/app privacy candidate inspection, planning, and reviewed execution |
| `permissions` | preflight | 🔎 Permission and Full Disk Access readiness |
| `tool-plan` / `tool-execute` | external tool adapters | 🧰 Allowlisted Docker/Homebrew/Xcode dry-run and gated execution |
| `review` | review normalization | 🧾 Reviewable items, selections, HTML audit output |
| `optimize` | `list`, `plan`, `run` | ⚙️ Maintenance tasks (dry-run only) |
| `analyze` | `categories`, `tree`, `scan` | 📊 Space analysis |
| `status` | `snapshot` | 🩺 System health |

### `capabilities`

```bash
python3 cleanmac.py capabilities        # Human-readable
python3 cleanmac.py --json capabilities  # Machine-readable
```

### `doctor`

```bash
python3 cleanmac.py --json doctor
```

### `clean inspect`

```bash
python3 cleanmac.py --json clean inspect \
  --categories userLogs,userAppLogs,terminal \
  --older-than-days 7 \
  --max-delete-mb 1000 \
  --limit 100
```

### `clean plan`

```bash
python3 cleanmac.py --json clean plan \
  --categories trash,downloads \
  --max-delete-mb 500 \
  --max-items 200 \
  --exclude "*.keep" \
  > /tmp/plan.json
```

### `clean validate-plan`

```bash
python3 cleanmac.py --json clean validate-plan \
  --plan-file /tmp/plan.json
```

### `clean run`

```bash
# Dry-run
python3 cleanmac.py --json clean run --categories trash,mails,xcode

# Execute with full safety
python3 cleanmac.py clean run \
  --plan-file /tmp/plan.json \
  --require-plan-context \
  --delete-mode trash \
  --operation-log /tmp/ops.jsonl \
  --execute
```

Key replay options:

| Option | Description |
|---|---|
| `--plan-file <path>` | Replay an existing `cleanmac.plan.v1` file instead of discovering fresh candidates |
| `--review-selection-file <path>` | Validate a `cleanmac.review-selection.v1` file and skip plan items not selected for review |
| `--require-plan-context` | Require the replayed plan root/home to match the current command context |
| `--require-confirmation-token` | Require a matching AI confirmation token before execution |

### `diagnose`

```bash
python3 cleanmac.py diagnose --categories trash,mails,xcode,userLogs,downloads
```

### `workflow` (recommended AI entry)

```bash
python3 cleanmac.py --json workflow \
  --categories trash,mails,xcode,userLogs,downloads \
  --dry-run-scope selected
```

### `clean scripts`

```bash
python3 cleanmac.py --json clean scripts --categories trash,mails,xcode
python3 cleanmac.py --json clean scripts --group status
```

### `clean open`

```bash
python3 cleanmac.py clean open --categories terminal,userAppLogs,userAppCache
```

### `clean links`

```bash
python3 cleanmac.py clean links
python3 cleanmac.py clean links --kind logs
python3 cleanmac.py --root /tmp/sandbox --home /Users/tester clean links \
  --kind logs --execute
python3 cleanmac.py --root /tmp/sandbox --home /Users/tester clean links \
  --kind logs --remove --execute
```

### `optimize`

```bash
python3 cleanmac.py --json optimize list
python3 cleanmac.py --json optimize plan
python3 cleanmac.py --json optimize run
```

### `status`

```bash
python3 cleanmac.py --json status snapshot
```

### `software`

```bash
python3 cleanmac.py --json software list
python3 cleanmac.py --json software leftovers
python3 cleanmac.py --json software startup-items
python3 cleanmac.py --json software uninstall-plan --app DemoApp
```

### `startup`

```bash
python3 cleanmac.py --json startup audit
python3 cleanmac.py --json startup plan
python3 cleanmac.py --json startup disable \
  --plan-file /tmp/startup-plan.json \
  --review-selection-file /tmp/startup-selection.json
python3 cleanmac.py startup disable \
  --plan-file /tmp/startup-plan.json \
  --review-selection-file /tmp/startup-selection.json \
  --operation-log /tmp/ops.jsonl \
  --execute --yes
```

`startup audit` is read-only. `startup plan` emits non-destructive disable plans for LaunchAgents, LaunchDaemons, and StartupItems. `startup disable` consumes a `cleanmac.startup-plan.v1` plus matching `cleanmac.review-selection.v1`; without `--execute` it is a dry-run, and with `--execute --yes` it disables only reviewed selected user startup plists and records `cleanmac.startup-disable-result.v1` / operation-log audit data. Stale or mismatched selections fail closed with `SELECTION_VALIDATION_FAILED`.

### `privacy`

```bash
python3 cleanmac.py --json privacy inspect --scope cache
python3 cleanmac.py --json privacy plan --scope history
python3 cleanmac.py --json privacy execute \
  --plan-file /tmp/privacy-plan.json \
  --review-selection-file /tmp/privacy-selection.json
python3 cleanmac.py privacy execute \
  --plan-file /tmp/privacy-plan.json \
  --review-selection-file /tmp/privacy-selection.json \
  --operation-log /tmp/ops.jsonl \
  --execute --yes
```

Privacy commands inspect and plan browser/app data cleanup while preserving sensitive scopes by default. `privacy execute` consumes a `cleanmac.privacy-plan.v1` plus matching `cleanmac.review-selection.v1`; without `--execute` it is a dry-run, and with `--execute --yes` it permanently deletes only reviewed selected privacy candidates and records `cleanmac.privacy-execute-result.v1` / operation-log audit data. Stale or mismatched selections fail closed with `SELECTION_VALIDATION_FAILED`.

### `permissions`

```bash
python3 cleanmac.py --json permissions --categories trash,systemLogs
```

This preflight reports Full Disk Access hints, category permissions, live-root requirements, and execution readiness without changing files.

### `tool-plan` / `tool-execute`

```bash
python3 cleanmac.py --json tool-plan --tool docker
python3 cleanmac.py --json tool-execute --tool docker
```

External-tool integration is allowlisted and dry-run first. `tool-execute` only runs known argv templates and still requires explicit `--execute --yes` for real execution.

### `review`

```bash
python3 cleanmac.py --json review --input-file /tmp/plan.json --selection-file /tmp/selection.json
python3 cleanmac.py --json review --input-file /tmp/plan.json --format html > /tmp/review.html
```

The review command normalizes clean plans, reports, startup/privacy/tool plans, and software uninstall plans into reviewable items. It emits source fingerprints so selections can be validated before dry-run or execution.

### `analyze`

```bash
python3 cleanmac.py --json analyze categories --all
python3 cleanmac.py --json analyze tree --path ~/Library --depth 2 --top 20
python3 cleanmac.py --json analyze scan --path ~/Downloads --depth 1 --top 10
```

### `list` (flat alias for `clean list`)

```bash
python3 cleanmac.py --json list
python3 cleanmac.py list
```

### `policy-simulate` (flat alias for `clean policy-simulate`)

```bash
python3 cleanmac.py --json policy-simulate --plan-file /tmp/plan.json --execute --delete-mode trash
python3 cleanmac.py --json policy-simulate \
  --plan-file /tmp/plan.json \
  --review-selection-file /tmp/selection.json \
  --execute \
  --delete-mode trash
```

### `completion`

```bash
python3 cleanmac.py completion bash       # Bash completion script
python3 cleanmac.py completion zsh        # Zsh completion script
python3 cleanmac.py completion fish       # Fish completion script
python3 cleanmac.py --json completion bash  # Machine-readable with schema
```

### `ai-tools`

```bash
python3 cleanmac.py --json ai-tools                          # All formats
python3 cleanmac.py --json ai-tools --format anthropic        # Anthropic/Claude format
python3 cleanmac.py --json ai-tools --format openai           # OpenAI/GPT format
python3 cleanmac.py --json ai-tools --format mcp              # MCP tool catalog format
```

### 5. Generate audit report files

```bash
python3 cleanmac.py --json --report-file /tmp/cleanmac-audit.json clean run \
  --categories trash,mails,xcode \
  > /tmp/cleanmac-clean-preview.json
```

Recommended files to archive:

- `/tmp/cleanmac-clean-preview.json`
- `/tmp/cleanmac-audit.json`
- `/tmp/cleanmac-plan.json`

---

## 🧪 Sandbox & Filters

### 🧪 Sandbox rehearsal

```bash
SANDBOX=$(mktemp -d /tmp/cleanmac-root.XXXXXX)
SANDBOX_HOME=/Users/tester
mkdir -p "$SANDBOX$SANDBOX_HOME/.Trash"
printf 'demo' > "$SANDBOX$SANDBOX_HOME/.Trash/demo.log"

python3 cleanmac.py --root "$SANDBOX" --home "$SANDBOX_HOME" clean inspect \
  --categories trash --limit 20

python3 cleanmac.py --root "$SANDBOX" --home "$SANDBOX_HOME" --json clean run \
  --categories trash --execute
```

### 🎯 Filter options

| Option | Description |
|---|---|
| `--include "*.log"` | Only matching glob |
| `--exclude "*.keep"` | Skip matching glob |
| `--older-than-days 14` | By mtime |
| `--min-size-mb 1` | Minimum size |
| `--name-regex "(log\|tmp)$"` | Regex on basename |
| `--max-delete-mb 500` | Budget: total bytes |
| `--max-items 100` | Budget: count |
| `--fail-on-skipped` | Reject if any skip |

### ⚙️ Global options

| Option | Default | Description |
|---|---|---|
| `--root <path>` | `/` | Path remapping root |
| `--home <path>` | `$HOME` | Home for `~` resolution |
| `--json` | false | JSON output |
| `--report-file <path>` | none | Audit report save |

---

## 🗂️ Category Overview

| Key | Title | Risk | Default | Path |
|---|---|---|---|---|
| `trash` | 🗑️ Trash | low | ✅ | `~/.Trash/` |
| `mails` | 📧 Apple Mail | low | ✅ | `~/Library/Mail Downloads/` |
| `xcode` | 💻 Xcode | low | ✅ | `~/Library/Developer/Xcode/` |
| `incompleteDownloads` | ⬇️ Incomplete | low | ✅ | `~/Downloads/*.part` |
| `bash` | 📜 Bash history | medium | ❌ | `~/.bash_history` |
| `terminal` | 🖥️ Terminal logs | medium | ❌ | `/private/var/log/asl/` |
| `userAppLogs` | 📋 App logs | medium | ❌ | `~/Library/Containers/*/Logs/` |
| `userAppCache` | 🗃️ App caches | medium | ❌ | `~/Library/Containers/*/Caches/` |
| `userCache` | 📦 User caches | medium | ❌ | `~/Library/Caches/` |
| `userLogs` | 📝 User logs | medium | ❌ | `~/Library/logs/` |
| `downloads` | ⬇️ Downloads | high | ❌ | `~/Downloads/` |
| `systemLogs` | 🖥️ System logs | high | ❌ | `/Library/logs/` |
| `imessage` | 💬 iMessage | high | ❌ | `~/Library/Messages/` |
| `userPrefs` | ⚙️ Preferences | critical | ❌ | `~/Library/Preferences/` |
| `docRev` | 📄 Doc revisions | critical | ❌ | `/.DocumentRevisions-V100/` |

Additional app-specific categories: `groupContainerCaches`, `androidStudio`, `jetbrains`, `vscode`, `docker`, `chrome`, `firefox`, `slack`, `zoom`, `teams`, `nodePackageCaches`, `pythonPackageCaches`, `goBuildCaches`. System/deep categories: `rotate_log_once` (log rotation), `deviceFirmware` (firmware caches), `appleSiliconCaches` (Rosetta/M1 caches). Governance: `official_uninstaller_vendor` detects CrowdStrike, etc.

---

## ✅ Development & CI

### 🧪 Local validation

```bash
python3 -m unittest -v                            # All tests
python3 -m unittest tests.test_mcp_server -v      # MCP tests only
make mcp-smoke                                     # MCP smoke test
make mcp-meta-index-smoke                         # MCP meta index contract
make mcp-resource-index-smoke                     # MCP resource index contract
make mcp-prompt-index-smoke                       # MCP prompt index contract
make mcp-tool-index-smoke                         # MCP tool index contract
make mcp-surface-audit-smoke                      # MCP surface audit readiness gate
make ai-host-smoke                                 # AI host integration suite
make ai-robustness-smoke                           # AI robustness regressions
make local-test                                    # Full local suite
make quality-check                                 # lint + type + coverage
make docs-smoke                                    # Doc validation
make governance-smoke                              # Governance contracts
make governance-integrity-smoke                    # Governance integrity release gate
make zero-resident-audit-smoke                     # Zero-resident product boundary audit
make ai-first-release-checklist-smoke              # AI-first release checklist gate
make pytest-governance-smoke                       # Pytest safe target policy
make ai-contract-smoke                             # AI contract samples and schema fragments
make governed-execution-smoke                      # Startup/privacy governed execution hardening
make open-source-smoke                             # Open source governance
make dependency-audit-smoke                        # pip-audit + SBOM.json
make homebrew-formula-smoke                        # Homebrew tap formula validation
make release-readiness-contract-smoke              # Release readiness contract schema validation
make release-readiness-smoke                       # AI Host release readiness bundle
make release-diagnostics-smoke                     # Release diagnostics + evidence + operator summary
make release-rehearsal-smoke                       # Release rehearsal dry-run gates
make release-promotion-smoke                       # Fail-closed promotion decision
make release-rollback-smoke                        # Manual-only rollback plan
make release-post-publish-smoke                    # Manual-only post-publish verification plan
make release-post-publish-result-smoke             # Manual-only post-publish closure evidence
make release-post-publish-evidence-template-smoke  # Manual-only post-publish evidence input template
make no-cache-check                                # No-cache full validation
make no-cache-release-check                        # No-cache release validation
```

### 📊 Make targets

| Target | What it validates |
|---|---|
| `lint` | Ruff format + lint |
| `type-check` | mypy |
| `coverage` | Unit tests + threshold |
| `quality-check` | lint → type-check → coverage |
| `local-test` | No-auth test runner |
| `pytest-test` | Isolated venv pytest |
| `format` | Auto-format code with ruff |
| `package-smoke` | Editable install |
| `script-smoke` | Template governance |
| `mcp-smoke` | MCP tools/list + tools/call |
| `mcp-meta-index-smoke` | MCP meta index over resource, prompt, and tool indexes |
| `mcp-resource-index-smoke` | MCP resource index schema and safety metadata |
| `mcp-prompt-index-smoke` | MCP prompt index schema and safety metadata |
| `mcp-tool-index-smoke` | MCP tool index schema, invocation metadata, and destructive auto-call denial |
| `mcp-surface-audit-smoke` | MCP surface audit readiness, missing-entry, and fail-closed gate checks |
| `bundle-audit-smoke` | Bundle drift audit |
| `build-check` | Build wheel/sdist + twine check |
| `macos-smoke` | macOS-specific tests |
| `real-macos-smoke` | Real macOS readonly tests |
| `security-smoke` | Static security scan |
| `dependency-audit-smoke` | pip-audit + SBOM.json |
| `docs-smoke` | README coverage |
| `governance-smoke` | Governance contracts |
| `governance-integrity-smoke` | Governance integrity contract and release gate |
| `zero-resident-audit-smoke` | Zero-resident product boundary audit and release gate |
| `ai-first-release-checklist-smoke` | AI-first release checklist contract and release gate |
| `pytest-governance-smoke` | Pytest safe target policy and release-only parity scope |
| `ai-governance-smoke` | AI governance route check |
| `governed-execution-smoke` | Startup/privacy governed execution hardening |
| `ai-host-smoke` | AI host integration test suite |
| `ai-robustness-smoke` | AI concurrency, idempotency, protocol, and trace regressions |
| `distribution-smoke` | wheel + sdist |
| `homebrew-formula-smoke` | Homebrew tap formula generation |
| `release-artifacts-smoke` | SHA256SUMS + ARTIFACT-MANIFEST.json + attestation |
| `release-readiness-contract-smoke` | Release readiness contract validation |
| `release-readiness-smoke` | AI Host release readiness gates and review checklist |
| `release-diagnostics-smoke` | Release diagnostics, evidence bundle, and operator summary |
| `release-rehearsal-smoke` | Release rehearsal phases and required evidence checks |
| `release-promotion-smoke` | Promotion decision blocks missing evidence fail-closed |
| `release-rollback-smoke` | Manual-only rollback plan for PyPI, GitHub Release, and Homebrew tap |
| `release-post-publish-smoke` | Manual-only post-publish verification for PyPI, GitHub Release, and Homebrew tap |
| `release-post-publish-result-smoke` | Manual-only post-publish closure result for pending or verified distribution surfaces |
| `release-post-publish-evidence-template-smoke` | Manual-only post-publish evidence input template for operator-provided closure evidence |
| `docker-test` | Debian container tests |
| `no-cache-check` | No-cache full validation |
| `no-cache-release-check` | No-cache release validation |
| `no-cache-docker-test` | Docker test with --pull=always |
| `release-check` | All gates combined |

Release artifact verification also emits `cleanmac.release-artifact-manifest.v1` via `scripts/generate_release_manifest.py`. The manifest binds wheel/sdist artifacts, `SBOM.json`, `cleanmac.rb`, and `SHA256SUMS` so release candidates can be verified consistently in local smoke tests and GitHub Actions. `make governance-integrity-smoke` validates the governance integrity release gate before readiness, and `make zero-resident-audit-smoke` validates `cleanmac.zero-resident-audit.v1`, confirming the AI-first ephemeral CLI boundary: no GUI, no TUI, no daemon, no login item, no unsolicited scan loop, and zero background CPU/memory policy when not invoked. `make ai-first-release-checklist-smoke` validates `cleanmac.ai-first-release-checklist.v1`, binding AI Host entrypoints, JSON contracts, governance integrity, zero-resident evidence, product-surface drift, and MCP surface readiness into one release gate. `make pytest-governance-smoke` validates that pytest parity uses the explicit release-only safe target list instead of broad `test_cleanmac.py tests` collection. `make release-readiness-contract-smoke` validates release readiness contract shape, and `make release-readiness-smoke` validates the read-only `cleanmac.release-readiness.v1` bundle before `make release-check` and `make no-cache-release-check` proceed. `make release-diagnostics-smoke` additionally validates `cleanmac.release-diagnostics.v1`, `cleanmac.release-evidence.v1`, and `cleanmac.release-operator-summary.v1`. `make release-rehearsal-smoke`, `make release-promotion-smoke`, `make release-rollback-smoke`, `make release-post-publish-smoke`, `make release-post-publish-result-smoke`, and `make release-post-publish-evidence-template-smoke` cover `cleanmac.release-rehearsal.v1`, `cleanmac.release-promotion-decision.v1`, `cleanmac.release-rollback-plan.v1`, `cleanmac.release-post-publish-verification.v1`, `cleanmac.release-post-publish-result.v1`, and `cleanmac.release-post-publish-evidence-template.v1`; CI archives `RELEASE-REHEARSAL.json`, `RELEASE-PROMOTION-DECISION.json`, `RELEASE-ROLLBACK-PLAN.json`, `RELEASE-POST-PUBLISH-VERIFICATION.json`, `RELEASE-POST-PUBLISH-RESULT.json`, and `RELEASE-POST-PUBLISH-EVIDENCE.example.json` with the release evidence.

### 🤖 CI Configuration

Built-in workflow documentation lives directly in `.github/workflows/*.yml`:

- **`.github/workflows/ci.yml`** runs on PR and push to `main` with quality gates, repository smoke, explicit governed MCP index checks (`mcp-meta-index-smoke`, `mcp-resource-index-smoke`, `mcp-prompt-index-smoke`, `mcp-tool-index-smoke`), AI host smoke, security, no-cache validation, and Docker smoke.
- **`.github/workflows/release.yml`** re-runs the release quality gates, including the governed MCP index smokes and AI host smoke, before building distributions, emitting release evidence, and publishing attestations.
- **`.github/workflows/nightly.yml`** runs `make release-check` plus `make no-cache-check` on a daily schedule to catch drift outside the PR path.

---

## ⚠️ Notes & Limitations

1. 📝 **No files deleted by default** — always verify dry-run output first
2. 🩺 **Large logs may indicate issues** — diagnose before deleting
3. ♻️ **Caches regenerate** — safe to clean, may impact app startup
4. 🔑 **Full Disk Access** — some paths require macOS permissions
5. 📋 **Keep audit records** — archive plans, dry-run JSON, and reports
6. 🐛 **Issues?** → [github.com/cleanmac/cleanmac/issues](https://github.com/cleanmac/cleanmac/issues)
7. 🔒 **Security?** → see [SECURITY.md](../../SECURITY.md)
