# 🧹 cleanmac — English Guide

> **macOS cleanup tool · Dry-run first · AI-native MCP integration · Zero dependencies**

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
- [📦 Installation](#-installation)
- [🛡️ Safety Model](#️-safety-model)
- [⌨️ Command Reference](#️-command-reference)
- [🧪 Sandbox & Filters](#-sandbox--filters)
- [🗂️ Category Overview](#️-category-overview)
- [✅ Development & CI](#-development--ci)

---

## ✨ Capabilities

`cleanmac` provides **20+ capabilities** for macOS cleanup:

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
| 🤖 | **AI tools** | 22 tools in Anthropic / OpenAI / MCP formats |
| 🏗️ | **MCP Server** | stdio-based Model Context Protocol server |
| 🔐 | **Confirmation token** | SHA-256 bound AI execution authorization |
| 🛡️ | **Execution guards** | Budget, risk policy, live-root protection |
| 🎯 | **Filters** | Include, exclude, age, size, regex |
| 🧰 | **Doctor** | Environment & permission diagnostics |
| 🪟 | **Previews** | Finder `open`, symlink `links` |
| 🔐 | **Bundle protection** | Allow/block policies for app containers |
| ♻️ | **Trash mode** | Recoverable deletion routing |
| 📜 | **Operation log** | Persistent JSONL audit trail |
| 🧾 | **Deletion log** | Forensic TSV records |
| ⏱️ | **Debug timing** | Millisecond PERF logging |
| 🧪 | **Test mode** | Auth guards for CI/testing |

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

# 6️⃣ Execute (after review!)
python3 cleanmac.py clean run \
  --plan-file /tmp/plan.json \
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

Export **22 tools** in three formats:

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
| `cleanmac_plan` | Generate cleanup plan | planning |
| `cleanmac_validate_plan` | Validate a plan file | planning |
| `cleanmac_workflow` | Multi-phase safe workflow | readonly |
| `cleanmac_policy_simulate` | Simulate policy enforcement | readonly |
| `cleanmac_software_list` | Read-only app inventory | readonly |
| `cleanmac_software_startup` | List startup items | readonly |
| `cleanmac_software_uninstall` | Plan uninstall (no execution) | planning |
| `cleanmac_clean_list` | List categories (group command) | readonly |
| `cleanmac_clean_inspect` | Inspect candidates (group command) | readonly |
| `cleanmac_clean_run` | Dry-run or execute cleanup | planning |

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
# 📋 List all 22 tools
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
```

### 🧭 AI Workflow Pipeline

Recommended AI invocation flow:

```mermaid
graph LR
    A[🤖 AI] -->|1. capabilities| B[🔍 Discover tools]
    B -->|2. diagnose| C[🩺 Analyze system]
    C -->|3. inspect| D[👀 Preview candidates]
    D -->|4. plan| E[🗺️ Generate plan]
    E -->|5. validate| F[✅ Verify plan]
    F -->|6. run --execute| G[🛡️ Execute with token]
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
| `software` | `list`, `startup-items`, `uninstall-plan` | 📦 App inventory (read-only) |
| `optimize` | `list`, `plan` | ⚙️ Maintenance tasks (dry-run only) |
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
```

### `status`

```bash
python3 cleanmac.py --json status snapshot
```

### `software`

```bash
python3 cleanmac.py --json software list
python3 cleanmac.py --json software startup-items
python3 cleanmac.py --json software uninstall-plan --app DemoApp
```

### `analyze`

```bash
python3 cleanmac.py --json analyze categories --all
python3 cleanmac.py --json analyze tree --path ~/Library --depth 2 --top 20
python3 cleanmac.py --json analyze scan --path ~/Downloads --depth 1 --top 10
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

*28 categories total. Run `python3 cleanmac.py clean list` for the full table.*

---

## ✅ Development & CI

### 🧪 Local validation

```bash
python3 -m unittest -v                            # All tests
python3 -m unittest tests.test_mcp_server -v      # MCP tests only
make mcp-smoke                                     # MCP smoke test
make local-test                                    # Full local suite
make quality-check                                 # lint + type + coverage
make docs-smoke                                    # Doc validation
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
| `package-smoke` | Editable install |
| `script-smoke` | Template governance |
| `mcp-smoke` | MCP tools/list + tools/call |
| `bundle-audit-smoke` | Bundle drift audit |
| `macos-smoke` | macOS-specific tests |
| `security-smoke` | Static security scan |
| `dependency-audit-smoke` | pip-audit + SBOM |
| `docs-smoke` | README coverage |
| `governance-smoke` | Governance contracts |
| `distribution-smoke` | wheel + sdist |
| `release-artifacts-smoke` | SHA256SUMS + attestation |
| `docker-test` | Debian container tests |
| `release-check` | All gates combined |

### 🤖 CI Configuration

Built-in `.github/workflows/ci.yml` runs on PR and push to `main`:

- **Quality**: lint, type-check, coverage (Python 3.10–3.13)
- **Smoke**: local-test, build-check, package, script, docs, governance, open-source, distribution, dependency audit, **MCP smoke**
- **Security**: unsafe delete patterns, high-risk regression tests, gitleaks
- **No-cache**: `PIP_NO_CACHE_DIR=1` validation
- **Docker**: Linux container tests

---

## ⚠️ Notes & Limitations

1. 📝 **No files deleted by default** — always verify dry-run output first
2. 🩺 **Large logs may indicate issues** — diagnose before deleting
3. ♻️ **Caches regenerate** — safe to clean, may impact app startup
4. 🔑 **Full Disk Access** — some paths require macOS permissions
5. 📋 **Keep audit records** — archive plans, dry-run JSON, and reports
6. 🐛 **Issues?** → [github.com/cleanmac/cleanmac/issues](https://github.com/cleanmac/cleanmac/issues)
7. 🔒 **Security?** → see [SECURITY.md](../../SECURITY.md)