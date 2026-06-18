# 🧹 cleanmac

`cleanmac` is a macOS-oriented command-line cleanup tool for common logs, caches, temporary files, development leftovers, and user-directory cleanup targets. It emphasizes auditable output, dry-run by default, reusable plans, deletion budgets, and sandbox validation to avoid accidental deletion on the host machine.

`cleanmac` is an independent Python implementation. It does not vendor source code from external macOS cleanup tools, is not affiliated with similarly scoped projects, and keeps safety, governance, and release automation in this repository.

> 🛡️ **Safety principle: nothing is deleted by default.** `cleanmac clean` is always a dry-run unless `--execute` is passed explicitly. For high / critical risk categories, execution also requires `--yes` by default. Executing against the real root `/` additionally requires `--allow-live-root`. Prefer validating with `--root` / `--home` in a sandbox first. When you do execute, prefer recoverable `--delete-mode trash`; use `--delete-mode permanent` only after reviewing candidates, budgets, skipped items, operation-log output, and backups.

Chinese documentation: [README.CN.md](README.CN.md)

---

## 🧭 Table of Contents

- [✨ Capabilities](#-capabilities)
- [🚀 Quick Start](#-quick-start)
- [🧪 Detailed Operation Guide](#-detailed-operation-guide)
- [🛡️ Safety Model](#️-safety-model)
- [📦 Installation and Running](#-installation-and-running)
- [⚙️ Global Options](#️-global-options)
- [🎯 Category Selection Options](#-category-selection-options)
- [🗂️ Cleanup Category Overview](#️-cleanup-category-overview)
- [⌨️ Command Reference](#️-command-reference)
- [📄 JSON Output Fields](#-json-output-fields)
- [✅ Development Validation](#-development-validation)
- [⚠️ Notes and Limitations](#️-notes-and-limitations)

---

## ✨ Capabilities

`cleanmac` currently supports:

1. 🧹 **Cleanup category management**: list category keys, titles, paths, risk levels, default state, recommended state, and advanced state.
2. 📊 **Space analysis**: estimate reclaimable space for selected categories without deleting files.
3. 🔎 **Candidate inspection**: list candidate files/directories with sorting, recursion, and filters.
4. 🩺 **Diagnostic recommendations**: provide cleanup advice based on category risk, directory size, and log/cache characteristics.
5. 🧾 **Script audit**: show analysis and deletion action plans without automatically running destructive actions.
6. 🧭 **Fixed safety workflow**: run script review, analysis, diagnosis, inspection, dry-run, and manual execution guidance in one command.
7. 🗺️ **Cleanup plans**: generate `cleanmac.plan.v1` JSON that can be validated and reused later.
8. 📄 **Cleanup reports**: output pre-clean reports, dry-run details, post-execution reports, and audit files.
9. 🧪 **Sandbox path remapping**: map real paths into a temporary directory with `--root` / `--home`.
10. 🛡️ **Layered execution guards**: support `--execute`, `--yes`, `--allow-live-root`, `--max-delete-mb`, `--max-items`, `--fail-on-skipped`, and `--require-plan-context`.
11. 🎯 **Fine-grained filters**: support `--include`, `--exclude`, `--older-than-days`, `--min-size-mb`, and `--name-regex`.
12. 🧰 **Environment checks**: `doctor` performs read-only checks for platform, Python, Full Disk Access guidance, live-root execution gates, and path alias normalization.
13. 🪟 **Auxiliary previews**: `open` previews Finder targets; `links` previews or manages log/cache symlink directories.
14. 📦 **Packaged implementation**: `cleanmac.py` is a thin entrypoint and the implementation lives in the `cleancli` package, so the same CLI can run directly from the checkout or after package installation.
15. 🧩 **Screenshot-aligned command groups**: `clean`, `software`, `optimize`, `analyze`, and `status` are the preferred top-level command groups.
16. 🤖 **Machine-consumable command templates**: `scripts` exposes `command_templates` with `argv`, `uses_shell`, `destructive`, `safe_to_auto_execute`, `manual_review_required`, and `placeholders` metadata.
17. 🧱 **Consistent object reports**: object-shaped JSON reports include `schema`, `destructive`, and `dry_run` where applicable; `list --json` intentionally remains a raw category array.
18. 🔐 **CLI safety extensions**: expanded bundle ID allow/block policies, app-specific cleanup rules, Group Container safeguards, official uninstaller routing, persistent JSONL operation logs, forensic deletion logs, debug timing, test-mode auth guards, and recoverable Trash routing.
19. 🌍 **Open-source governance**: license, contribution guide, security policy, code of conduct, issue/PR templates, Dependabot, CodeQL, pip-audit smoke, and `SBOM.json` release artifacts are included for public collaboration.
20. ✅ **Development quality gates**: the Makefile provides local tests, editable package smoke tests, script/docs/governance/open-source smoke tests, wheel/sdist distribution smoke tests, Docker tests, and `release-check`.

The current CLI safety extensions are exposed through concrete flags and JSON fields:

| Capability | CLI surface | JSON/report surface |
|---|---|---|
| 🔐 Bundle protection | `clean run --bundle-allowlist <ids>` and `clean run --bundle-blocklist <ids>` | `bundle_allowlist`, `bundle_blocklist`, item-level `bundle_id`, and skipped reasons `bundle-not-allowlisted` / `bundle-blocklisted` |
| 🧩 App-specific cleanup | `clean inspect --categories androidStudio,jetbrains,vscode,docker,raycast,unity,unreal,godot,deveco,maestro,chrome,firefox,slack,zoom,teams,nodePackageCaches,pythonPackageCaches,goBuildCaches,groupContainerCaches` | Category metadata plus `app-protected-data`, `protected-container-data`, and `protected-group-container` skipped reasons for protected profile, credential, workspace, and group-container data |
| 🧯 Official uninstaller routing | `software list` and `software uninstall-plan --app <name>` | `official_uninstaller_vendor`, `official_uninstaller_required`, and a vendor guidance message for ESET, Jamf, CrowdStrike, SentinelOne, GlobalProtect, and Cisco |
| 📜 Persistent operation log | `clean run --operation-log <path>` | One JSONL record per executed item using `cleanmac.operation-log-entry.v1` |
| 🧾 Forensic deletion log | `clean run --execute` | Tab-separated `~/.cleanmac/deletions.log` entries recording timestamp, mode, size, status, path, and detail |
| ⏱️ Debug timing | `CLEANMAC_DEBUG=1 cleanmac ...` | `~/.cleanmac/cleanmac_debug_session.log` with millisecond `PERF` entries |
| 🧪 Test-mode auth guard | `CLEANMAC_TEST_MODE=1` / `CLEANMAC_TEST_NO_AUTH=1` | Blocks sudo/AppleScript helper execution during tests; `CLEANMAC_TEST_TRASH_DIR` can route Trash tests to a fixture directory |
| ♻️ Recoverable deletion | `clean run --delete-mode trash` | `delete_mode`, item-level `trash_path`, `safety_gate.delete_mode`, symlink refusal, and fail-closed Trash behavior |

Example dry-run for expanded app cache rules:

```bash
python3 cleanmac.py --json clean inspect --categories chrome,firefox,slack,zoom,teams,nodePackageCaches,pythonPackageCaches,goBuildCaches
```

---

## 🚀 Quick Start

> 🧭 **Command format note:** global options must appear before the top-level command, for example `python3 cleanmac.py --json clean inspect ...` and `python3 cleanmac.py --root /tmp/root --home /Users/tester clean run ...`. Action options appear after the action, for example `clean inspect --categories ...` and `clean run --plan-file ...`.

### 🧩 Top-level command groups

| Group | Product area | Current capability |
|---|---|---|
| `clean` | 🧹 Cleanup | `list`, `inspect`, `plan`, `validate-plan`, `run`, `scripts`, `open`, `links` |
| `software` | 📦 Software | Read-only app inventory, startup locations, and uninstall-plan placeholders |
| `optimize` | ⚙️ Optimize | Maintenance task inventory and dry-run plans only |
| `analyze` | 📊 Analyze | Category reclaim analysis, directory scan, and tree output |
| `status` | 🩺 Status | Read-only load average and disk snapshot |

### 🔎 Inspect capabilities and categories

```bash
cd /path/to/cleanmac
python3 cleanmac.py capabilities
python3 cleanmac.py clean list
python3 cleanmac.py --json doctor
```

### 👀 Preview common log candidates

```bash
python3 cleanmac.py --json clean inspect \
  --categories userLogs,userAppLogs,terminal \
  --older-than-days 7 \
  --max-delete-mb 1000 \
  --max-items 500 \
  > /tmp/cleanmac-logs-inspect.json
```

### 🗺️ Generate, validate, and dry-run a cleanup plan

```bash
python3 cleanmac.py --json clean plan \
  --categories userLogs,userAppLogs,terminal \
  --older-than-days 7 \
  --max-delete-mb 1000 \
  --max-items 500 \
  > /tmp/cleanmac-logs-plan.json

python3 cleanmac.py --json clean validate-plan \
  --plan-file /tmp/cleanmac-logs-plan.json

python3 cleanmac.py --json clean run \
  --plan-file /tmp/cleanmac-logs-plan.json \
  --require-plan-context \
  > /tmp/cleanmac-logs-dry-run.json
```

### 🛡️ Execute after manual review

```bash
python3 cleanmac.py clean run \
  --plan-file /tmp/cleanmac-logs-plan.json \
  --require-plan-context \
  --execute \
  --allow-live-root
```

> If the selected categories include high / critical risk items, add `--yes` as well.

---

## 🧪 Detailed Operation Guide

### 1. Check the environment before first use

```bash
cd /path/to/cleanmac

# Show commands, filters, and safety gates.
python3 cleanmac.py --json capabilities

# Read-only environment, permission, live-root protection, and path alias checks.
python3 cleanmac.py --json doctor

# Show available categories, risk levels, defaults, and descriptions.
python3 cleanmac.py --json clean list
```

Recommended fields to inspect first:

- `safety_guardrails`: confirm dry-run, execution, budget, and live-root protection rules.
- `checks.full_disk_access`: some macOS directories may require Full Disk Access.
- `risk`: start with low / medium risk categories.

### 2. Recommended manual cleanup flow

Fixed order: **list/capabilities → inspect → plan → validate-plan → dry-run clean → manual review → execute**.

```bash
# 1) Inspect capabilities and categories; does not delete files.
python3 cleanmac.py clean list
python3 cleanmac.py capabilities

# 2) Inspect candidates first; does not delete files.
python3 cleanmac.py --json clean inspect \
  --categories trash,mails,xcode,userLogs \
  --older-than-days 7 \
  --max-delete-mb 500 \
  --max-items 200 \
  --limit 100 \
  > /tmp/cleanmac-inspect.json

# 3) Generate a plan file; does not delete files.
python3 cleanmac.py --json clean plan \
  --categories trash,mails,xcode,userLogs \
  --older-than-days 7 \
  --max-delete-mb 500 \
  --max-items 200 \
  --exclude "*.keep" \
  > /tmp/cleanmac-plan.json

# 4) Validate the plan; does not delete files.
python3 cleanmac.py --json clean validate-plan \
  --plan-file /tmp/cleanmac-plan.json

# 5) Reuse the plan for dry-run; does not delete files.
python3 cleanmac.py --json clean run \
  --plan-file /tmp/cleanmac-plan.json \
  --require-plan-context \
  > /tmp/cleanmac-dry-run.json
```

When reviewing dry-run JSON, verify at least:

- `dry_run` is `true`.
- Every entry in `items[]` is a target you are willing to delete.
- `safety_gate` contains no unexpected blocking or warning state.
- `skipped_summary` matches your expectations.
- Candidate count and estimated size in `pre_clean_report.summary` are reasonable.

After review, execute:

```bash
python3 cleanmac.py clean run \
  --plan-file /tmp/cleanmac-plan.json \
  --require-plan-context \
  --delete-mode trash \
  --operation-log /tmp/cleanmac-operations.jsonl \
  --execute \
  --allow-live-root
```

If selected categories include high / critical risk items:

```bash
python3 cleanmac.py clean run \
  --plan-file /tmp/cleanmac-plan.json \
  --require-plan-context \
  --delete-mode trash \
  --operation-log /tmp/cleanmac-operations.jsonl \
  --execute \
  --yes \
  --allow-live-root
```

For execution against application-owned cache paths, prefer declaring bundle policy explicitly:

```bash
python3 cleanmac.py --json clean run \
  --categories userAppCache \
  --bundle-allowlist com.example.safe-app \
  --bundle-blocklist com.apple.mail,com.apple.MobileSMS \
  --delete-mode trash \
  --operation-log /tmp/cleanmac-operations.jsonl \
  --execute \
  --yes \
  --allow-live-root
```

### 3. Sandbox rehearsal

```bash
SANDBOX=$(mktemp -d /tmp/cleanmac-root.XXXXXX)
SANDBOX_HOME=/Users/tester

mkdir -p "$SANDBOX$SANDBOX_HOME/.Trash"
printf '%s\n' 'demo' > "$SANDBOX$SANDBOX_HOME/.Trash/demo.log"

python3 cleanmac.py --root "$SANDBOX" --home "$SANDBOX_HOME" clean inspect \
  --categories trash \
  --limit 20

python3 cleanmac.py --root "$SANDBOX" --home "$SANDBOX_HOME" --json clean run \
  --categories trash

python3 cleanmac.py --root "$SANDBOX" --home "$SANDBOX_HOME" --json clean run \
  --categories trash \
  --execute
```

Sandbox execution only deletes candidates under the remapped sandbox directory. It does not touch real host paths.

### 4. Fine-grained filters and budget protection

```bash
python3 cleanmac.py --json clean run \
  --categories userLogs,downloads \
  --include "*.log,*.tmp" \
  --exclude "*.keep" \
  --older-than-days 14 \
  --min-size-mb 1 \
  --name-regex "(log|tmp)$" \
  --max-delete-mb 300 \
  --max-items 100 \
  --fail-on-skipped \
  > /tmp/cleanmac-filtered-dry-run.json
```

| Option | Purpose |
|---|---|
| `--include` | Only process candidates matching the glob pattern. |
| `--exclude` | Skip candidates matching the glob pattern. |
| `--older-than-days` | Only process candidates old enough by mtime. |
| `--min-size-mb` | Only process candidates at or above the minimum size. |
| `--name-regex` | Only process candidates whose basename matches the regex. |
| `--max-delete-mb` | Refuse execution when candidate bytes exceed the budget. |
| `--max-items` | Refuse execution when candidate count exceeds the budget. |
| `--fail-on-skipped` | Refuse execution if any candidate is skipped. |

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

### 6. Auxiliary previews

```bash
# Show Finder targets; preview only by default.
python3 cleanmac.py clean open --categories terminal,userAppLogs,userAppCache

# Preview log/cache symlink mapping; does not create symlinks.
python3 cleanmac.py clean links

# Create and remove symlink directories inside a sandbox.
python3 cleanmac.py --root /tmp/cleanmac-root --home /Users/tester clean links \
  --kind logs \
  --execute
python3 cleanmac.py --root /tmp/cleanmac-root --home /Users/tester clean links \
  --kind logs \
  --remove \
  --execute
```

### 7. Troubleshooting

| Symptom | Action |
|---|---|
| `clean --execute` is refused | Check whether `--execute` is missing, high-risk categories need `--yes`, or real-root execution needs `--allow-live-root`. |
| `validate-plan` reports root/home mismatch | Use the same `--root` / `--home`, or regenerate the plan. |
| Budget blocks execution | Narrow categories, add filters, or adjust the budget after manual review. |
| `--fail-on-skipped` blocks execution | Inspect `skipped_summary` and `skipped[]` to confirm skip reasons. |
| Full Disk Access warning | Grant Full Disk Access to the terminal or runtime in macOS System Settings. |
| Docker validation fails | Run `make local-test` / `make package-smoke` first, then retry `make release-check` when Docker is available. |

### 8. Operational red lines

- Automation governance flows must not run `clean --execute`.
- Do not execute cleanup against the real root `/` before completing dry-run, plan, validate-plan, and manual review.
- Do not automatically escalate privileges or bypass safety gates.
- high / critical categories require manual review and `--yes` during execution.
- Keep plan files, dry-run JSON, and audit reports for later review.

---

## 🛡️ Safety Model

### 🧯 Dry-run by default

```bash
python3 cleanmac.py clean run --categories trash
```

This command only prints the pre-clean report and candidates. It does not delete files.

### Real deletion requires `--execute`

```bash
python3 cleanmac.py --root /tmp/cleanmac-root --home /Users/tester clean run \
  --categories trash \
  --execute
```

### high / critical categories require `--yes`

```bash
python3 cleanmac.py clean run --categories downloads --execute --yes --allow-live-root
```

### 🚦 Risk policies

By default, high / critical risk categories require `--yes` during execution.

| Policy | Description |
|---|---|
| `strict` | medium / high / critical all require `--yes`. |
| `permissive` | Risk level does not add an extra `--yes` requirement; `--execute` is still required. |

### 🧱 Live-root execution protection

When `--root /` is used, execution is refused by default even if `--execute` is present. You must explicitly pass:

```bash
python3 cleanmac.py clean run --categories trash --execute --allow-live-root
```

Validate with a sandbox or plan file first.

### 🎯 Delete target contents only, not parent directories

Cleanup semantics delete direct contents under target directories while preserving the target directories themselves. Execution reports verify this through `target_preservation`.

### 🔐 Bundle-aware application data protection

For paths that contain app container identifiers such as `~/Library/Containers/com.example.app/...`, `cleanmac` extracts the bundle ID and applies bundle policy before size budgets or deletion:

| Policy | Behavior |
|---|---|
| `--bundle-allowlist <ids>` | Exclusive allow mode. If a candidate has a bundle ID and it is not in the allowlist, the candidate is skipped as `bundle-not-allowlisted`. |
| `--bundle-blocklist <ids>` | Protection mode. If a candidate has a bundle ID in the blocklist, the candidate is skipped as `bundle-blocklisted`. |
| Default blocklist | A built-in set protects selected Apple communication/iCloud/system service bundles plus common cloud, security, container, and network tool bundles unless explicitly overridden; inspect `capabilities.safety_guardrails.default_protected_bundle_ids` for the complete list. |

Allowlist is evaluated before blocklist. Bundle policy applies to bundle-owned candidates; paths without a recognizable bundle ID continue through the normal include/exclude, age, size, and safety checks.

### ♻️ Recoverable Trash routing and operation logs

`--delete-mode permanent` is the default and removes candidates directly during execution. `--delete-mode trash` moves each executed candidate into the remapped user Trash under a unique name such as `~/.Trash/cleanmac-20260616T120000000000Z-download.bin`, making recovery possible from Trash.

Execution writes operation records to `~/.cleanmac/operations.jsonl` by default; `--operation-log <path>` overrides that path. `cleanmac` appends one JSONL record per executed item. Each record uses `cleanmac.operation-log-entry.v1` and includes timestamp, command, category, path, bytes, `bundle_id`, `delete_mode`, `trash_path`, root, and home. Dry-runs do not write operation-log entries.

`rotate_log_once()` performs single-step log rotation before appending: the main log budget is 1 MB for `~/.cleanmac/cleanmac.log`, and the operation-log budget is 5 MB for `~/.cleanmac/operations.jsonl`.

## 📦 Installation and Running

### ▶️ Run the script directly

```bash
python3 cleanmac.py clean list
```

### 📥 Install as a Python package

```bash
python3 -m venv .venv
. .venv/bin/activate
python3 -m pip install -e .
cleanmac list
```

### 🐍 Python version

Python 3.10+ is recommended.

---

## ⚙️ Global Options

| Option | Default | Description |
|---|---|---|
| `--root <path>` | `/` | Root for path remapping. Real execution against `/` needs extra confirmation. |
| `--home <path>` | Current user home | Used to resolve `~` before `--root` remapping. |
| `--json` | false | Emit machine-readable JSON. |
| `--report-file <path>` | none | Save a JSON audit report. |

---

## 🎯 Category Selection Options

| Option | Description |
|---|---|
| `--categories <keys>` | Comma-separated category keys, for example `trash,mails,xcode`. |
| `--default` | Use default categories. |
| `--all` | Use all categories, including advanced/high-risk categories. |

---

## 🗂️ Cleanup Category Overview

| Key | Title | Path | Risk | Default | Recommended | Advanced | Notes |
|---|---|---|---|---|---|---|---|
| `trash` | Trash | `~/.Trash/` | low | yes | yes | no | User trash |
| `mails` | Apple Mail downloads | `~/Library/Mail Downloads/`, `~/Library/Containers/com.apple.mail/Data/Library/Mail Downloads/` | low | yes | yes | no | Old Mail attachments; skipped while Mail is running |
| `xcode` | Xcode caches, derived data, and device logs | DerivedData, iOS Device Logs, Archives, Products, ModuleCache, CoreSimulator caches | low | yes | yes | no | Development leftovers |
| `deviceFirmware` | Xcode device support and firmware caches | `~/Library/Developer/Xcode/* DeviceSupport/` | high | no | no | yes | Device support symbols and firmware support caches; old files by default |
| `bash` | Bash history and sessions | `~/.bash_sessions/`, `~/.bash_history` | medium | no | no | yes | Shell history |
| `terminal` | Terminal ASL logs | `/private/var/log/asl/*.asl` | medium | no | no | yes | May require permissions |
| `userAppLogs` | Sandboxed application logs | `~/Library/Containers/*/Data/Library/Logs/` | medium | no | no | yes | App sandbox logs |
| `userAppCache` | Sandboxed application caches | `~/Library/Containers/*/Data/Library/Caches/` | medium | no | no | yes | App sandbox caches |
| `userCache` | User caches | `~/Library/Caches/` | medium | no | no | yes | Caches are usually regenerated |
| `userLogs` | User logs | `~/Library/logs/` | medium | no | no | yes | Investigate unusually large logs first |
| `systemLogs` | System logs | `/Library/logs/`, `/var/log/` | high | no | no | yes | System logs; handle carefully |
| `globalTemp` | Global temporary files | `/tmp/` | high | no | no | yes | Global temp directory |
| `userPrefs` | User preferences | `~/Library/Preferences/` | critical | no | no | yes | Extremely high risk |
| `downloads` | Downloads | `~/Downloads/` | high | no | no | yes | User downloads; must be selected explicitly |
| `incompleteDownloads` | Incomplete browser downloads | `~/Downloads/*.download`, `~/Downloads/*.crdownload`, `~/Downloads/*.part` | low | yes | yes | no | Incomplete downloads; active files are skipped |
| `spotlight` | Spotlight index | `/.Spotlight-V100/` | high | no | no | yes | May require permissions |
| `docRev` | Document revisions | `/.DocumentRevisions-V100/` | critical | no | no | yes | Document version history |
| `imessage` | iMessage attachments | `~/Library/Messages/Attachments/` | high | no | no | yes | May require Full Disk Access |
| `systemCaches` | System cache files | `/Library/Caches/**/*.cache`, `/Library/Caches/**/*.tmp`, `/Library/Caches/**/*.log` | high | no | no | yes | System cache files, old files by default |
| `systemDiagnostics` | System diagnostic reports | `/Library/Logs/DiagnosticReports/`, `/private/var/db/diagnostics/`, and related paths | high | no | no | yes | System diagnostic logs |
| `appleSiliconCaches` | Apple Silicon and Rosetta runtime caches | `/private/var/db/oah/`, `/private/var/db/DetachedSignatures/` | high | no | no | yes | Rebuildable runtime/signature caches; old files by default |
| `thirdPartySystemLogs` | Third-party system logs | `/Library/Logs/Adobe/`, `/Library/Logs/CreativeCloud/`, `/Library/Logs/adobegc.log` | medium | no | no | yes | Third-party system logs |
| `macosInstallers` | macOS installer remnants | `/macOS Install Data/`, `/Applications/Install macOS*.app` | high | no | no | yes | Old installers; running and current-version installers are skipped |
| `systemUpdates` | System update remnants | `/Library/Updates/` | high | no | no | yes | System update leftovers; restricted items are skipped |
| `browserCodeSignCache` | Browser code signature caches | Dynamic scan under `/private/var/folders/*/*/X/` | medium | no | no | yes | Browser code signature caches |
| `gpuCaches` | Rebuildable GPU and Metal caches | Dynamic scan under `/private/var/folders/*/*/C/` | medium | no | no | yes | Only stale rebuildable GPU caches |
| `darwinUserTemp` | Darwin user temporary files | `DARWIN_USER_TEMP_DIR` | medium | no | no | yes | Current-user runtime temp directory |
| `darwinUserCache` | Darwin user runtime caches | `DARWIN_USER_CACHE_DIR` | medium | no | no | yes | Current-user runtime cache directory |

---

## ⌨️ Command Reference

Preferred top-level command groups are `clean`, `software`, `optimize`, `analyze`, and `status`. Global options such as `--json`, `--root`, `--home`, and `--report-file` must be placed before the command group.

### 🧭 Recommended command groups

```bash
# Cleanup: inspect, plan, validate, dry-run, execute
python3 cleanmac.py clean list
python3 cleanmac.py --json clean inspect --categories trash,mails,xcode
python3 cleanmac.py --json clean plan --categories trash,mails,xcode > /tmp/cleanmac-plan.json
python3 cleanmac.py --json clean validate-plan --plan-file /tmp/cleanmac-plan.json
python3 cleanmac.py --json clean run --plan-file /tmp/cleanmac-plan.json --require-plan-context

# Software: read-only planning, no uninstall execution
python3 cleanmac.py --json software list
python3 cleanmac.py --json software startup-items
python3 cleanmac.py --json software uninstall-plan --app Demo

# Optimize: dry-run maintenance plans
python3 cleanmac.py --json optimize list
python3 cleanmac.py --json optimize plan

# Analyze: category reclaim and directory tree scans
python3 cleanmac.py --json analyze categories --all
python3 cleanmac.py --json analyze tree --path ~/Library --depth 2 --top 20

# Status: read-only snapshot
python3 cleanmac.py --json status snapshot
```

### `clean list`

List categories.

```bash
python3 cleanmac.py clean list
python3 cleanmac.py --json clean list
```

### `capabilities`

Show CLI capabilities, safety gates, filters, and validation constraints.

```bash
python3 cleanmac.py capabilities
python3 cleanmac.py --json capabilities
```

### `doctor`

Run read-only environment and permission guidance checks.

```bash
python3 cleanmac.py --json doctor
```

### `analyze categories`

Estimate reclaimable space without deleting files.

```bash
python3 cleanmac.py analyze categories --categories trash,mails,xcode
python3 cleanmac.py --json analyze categories --all
```

### `analyze scan` / `analyze tree`

Scan arbitrary directories for large entries without deleting files.

```bash
python3 cleanmac.py --json analyze tree --path ~/Library --depth 2 --top 20
python3 cleanmac.py --json analyze scan --path ~/Downloads --depth 1 --top 10
```

### `clean inspect`

List candidates without deleting files.

```bash
python3 cleanmac.py --json clean inspect \
  --categories userLogs,userAppLogs,terminal \
  --older-than-days 7 \
  --max-delete-mb 1000 \
  --max-items 500
```

`--max-delete-mb` / `--max-items` on `clean inspect` are preview-only budget checks. They output `budget_summary`; execution blocking is enforced by `clean plan` / `clean run` before deletion.

### `clean plan`

Generate a reusable plan without deleting files.

```bash
python3 cleanmac.py --json clean plan \
  --categories trash,downloads \
  --max-delete-mb 500 \
  --max-items 200 \
  --exclude "*.keep" \
  > /tmp/cleanmac-plan.json
```

### `clean validate-plan`

Validate a plan and generate a current-context preview.

```bash
python3 cleanmac.py --json clean validate-plan \
  --plan-file /tmp/cleanmac-plan.json
```

### `diagnose`

Output diagnostic recommendations, recommended cleanup categories, and cautious cleanup categories.

```bash
python3 cleanmac.py diagnose --categories trash,mails,xcode,userLogs,downloads
```

### `clean scripts`

Output script and action audit information without destructive operations.

```bash
python3 cleanmac.py --json clean scripts --categories trash,mails,xcode
python3 cleanmac.py --json clean scripts --group status
```

JSON reports include a `script_inventory.groups.<group>.command_templates` array. Each template is designed for automation review and includes:

| Field | Description |
|---|---|
| `id` | Stable template identifier, for example `clean-inspect-selected` or `systemLogs-delete-1`. |
| `kind` | Template shape: `argv` for direct CLI invocation, `shell` for `/bin/sh -c` snippets. |
| `command` | Human-readable shell-quoted command string. |
| `argv` | Structured argument vector for direct execution without shell parsing when `uses_shell` is false. |
| `uses_shell` | Whether the template requires `/bin/sh -c`. Category-level `du` / `rm` snippets use shell templates; CLI workflows use direct argv templates. |
| `destructive` | Whether the template represents destructive work. |
| `safe_to_auto_execute` | Whether automation may run it without manual review. |
| `manual_review_required` | Whether a human must review before use. Destructive cleanup templates set this to true. |
| `placeholders` | Placeholder names such as `keys`, `plan.json`, or `AppName` that must be replaced intentionally. |
| `execution_policy` | Machine-checkable mirror of shell/destructive/automation flags plus `requires_placeholder_substitution`. |

The report also includes `script_inventory.command_template_contract`, which defines the required template fields and the rule that every destructive template must set `safe_to_auto_execute=false` and `manual_review_required=true`. `template_validation` is emitted in the same report as a machine-readable self-check with `valid`, `template_count`, `destructive_template_count`, `violation_count`, and `violations`; `make script-smoke` fails if this validation is not clean.

### `workflow`

Run the fixed safety workflow without destructive cleanup.

```bash
python3 cleanmac.py --json workflow \
  --categories trash,mails,xcode,userLogs,downloads \
  --dry-run-scope selected
```

### `clean open`

Preview or execute Finder open targets.

```bash
python3 cleanmac.py clean open --categories terminal,userAppLogs,userAppCache
```

### `clean links`

Preview, create, or remove log/cache symlink directories.

By default, log links use `~/.CleanMacAppLogLinks/` and cache links use `~/.CleanMacAppCacheLinks/`.

```bash
python3 cleanmac.py clean links
python3 cleanmac.py clean links --kind logs
python3 cleanmac.py --root /tmp/cleanmac-root --home /Users/tester clean links \
  --kind logs \
  --execute
python3 cleanmac.py --root /tmp/cleanmac-root --home /Users/tester clean links \
  --kind logs \
  --remove \
  --execute
```

### `clean run`

Dry-run by default; deletes only when `--execute` is passed.

```bash
python3 cleanmac.py --json clean run --categories trash,mails,xcode

python3 cleanmac.py clean run \
  --plan-file /tmp/cleanmac-plan.json \
  --require-plan-context \
  --execute \
  --allow-live-root
```

Common options:

| Option | Description |
|---|---|
| `--plan-file <path>` | Read a plan file. |
| `--require-plan-context` | Require the current root/home to match the plan. |
| `--execute` | Actually delete candidates. |
| `--yes` | Confirmation required for high / critical risk execution. |
| `--allow-live-root` | Allow execution against the real root. |
| `--max-delete-mb <n>` | Deletion budget. |
| `--max-items <n>` | Candidate count budget. |
| `--fail-on-skipped` | Refuse execution if skipped items exist. |
| `--bundle-allowlist <ids>` | Comma-separated exclusive allowlist for bundle-owned candidates; non-allowlisted bundle candidates are skipped. |
| `--bundle-blocklist <ids>` | Comma-separated protection list for bundle-owned candidates; defaults to the built-in `capabilities.safety_guardrails.default_protected_bundle_ids` list. |
| `--delete-mode permanent\|trash` | Delete candidates permanently, or move them to the user's Trash with a unique `cleanmac-*` name. |
| `--operation-log <path>` | Append one JSONL audit record per executed candidate. |

Recoverable deletion example:

```bash
python3 cleanmac.py --json clean run \
  --categories downloads \
  --delete-mode trash \
  --operation-log /tmp/cleanmac-operations.jsonl \
  --execute \
  --yes
```

## 📄 JSON Output Fields

### Common object-report top-level fields

`list --json` intentionally remains a raw category array for compatibility with existing category-list consumers. Other JSON commands emit object reports with a `schema` field; object reports also include `destructive` and `dry_run` when they model safety state.

| Field | Description |
|---|---|
| `schema` | Report schema name. |
| `destructive` | Whether the command performs or represents a destructive operation. |
| `dry_run` | Whether the command only previews work. Present on cleanup/workflow-style reports. |
| `selected_categories` | Metadata for selected categories, present on cleanup-oriented reports. |
| `items` | Candidate or processed items, present on inspect/clean reports. |
| `skipped` / `skipped_summary` | Candidates skipped by filters, present on inspect/clean reports. |
| `pre_clean_report` / `post_clean_report` | Clean preview/execution reports; `post_clean_report` is populated only in execution mode. |
| `safety_gate` / `budget_summary` | Execution gate and budget checks for clean/inspect/validate-plan flows. |
| `report_file` | Audit report file path when `--report-file` is used. |
| `bundle_allowlist` / `bundle_blocklist` | Bundle policy applied by clean reports and mirrored in `safety_gate`. |
| `delete_mode` | `permanent` or `trash`; present on clean reports and item rows. |
| `operation_log` / `operation_log_entry_count` | JSONL operation-log path and number of appended execution records. |

Current object report schemas include `cleanmac.capabilities.v1`, `cleanmac.doctor.v1`, `cleanmac.inspect.v1`, `cleanmac.analyze.v1`, `cleanmac.analyze-tree.v1`, `cleanmac.diagnose.v1`, `cleanmac.scripts.v1`, `cleanmac.script-groups.v1`, `cleanmac.clean.v1`, `cleanmac.plan.v1`, `cleanmac.links.v1`, `cleanmac.open.v1`, `cleanmac.software.v1`, `cleanmac.optimize.v1`, `cleanmac.status.snapshot.v1`, `cleanmac.validate-plan.v1`, `cleanmac.workflow.v1`, and `cleanmac.audit.v1`. Operation-log JSONL records use `cleanmac.operation-log-entry.v1`.

### 🧱 Common `items[]` fields

| Field | Description |
|---|---|
| `category` | Category key. |
| `parent` | Target parent directory. |
| `path` | Candidate path. |
| `bytes` | Size in bytes. |
| `human` | Human-readable size. |
| `bundle_id` | Detected owner bundle ID for app-container candidates, when available. |
| `delete_mode` | Deletion route selected for the row: `permanent` or `trash`. |
| `trash_path` | Destination path when `--delete-mode trash` executes; otherwise `null`. |
| `deleted` | Whether it was deleted; meaningful only in execution reports. |

---

## ✅ Development Validation

```bash
python3 -m pip install -e '.[dev,build]'
make lint
make type-check
make coverage
make quality-check
make local-test
make pytest-test
make build-check
make package-smoke
make script-smoke
make bundle-audit-smoke
make macos-smoke
make security-smoke
make dependency-audit-smoke
make docs-smoke
make governance-smoke
make open-source-smoke
make distribution-smoke
make release-artifacts-smoke
make docker-test
make no-cache-check
make release-check
make no-cache-release-check
```

| Target | What it validates |
|---|---|
| `lint` | Runs Ruff format check and Ruff lint. |
| `type-check` | Runs mypy using the project configuration. |
| `coverage` | Runs unit tests under coverage.py and enforces the configured threshold. |
| `quality-check` | Chains `lint`, `type-check`, and `coverage`; this is the fast CI quality gate. |
| `local-test` | Runs `scripts/test.sh`, which enables `CLEANMAC_TEST_NO_AUTH=1` and `CLEANMAC_TEST_MODE=1`, stubs dangerous system commands, then runs unit tests plus governance/script smoke checks. |
| `pytest-test` | Creates a temporary venv, installs the test extra when needed, disables pytest cache, and runs the existing test suite through pytest without relying on global pytest. Unittest remains the authoritative local/coverage path during the gradual migration. |
| `build-check` | Builds wheel/sdist with `build` and validates package metadata with `twine check`. |
| `package-smoke` | Installs the checkout in an isolated editable venv and verifies `cleanmac --json capabilities` is valid JSON. |
| `script-smoke` | Renders script templates, reads `template_validation`, and verifies destructive templates cannot be auto-executed. |
| `bundle-audit-smoke` | Runs the Python bundle drift audit against sandbox app fixtures. |
| `macos-smoke` | Runs macOS-focused smoke coverage with no-auth/test-mode enabled; CI executes it from a workflow-created venv. |
| `security-smoke` | Runs static governance scans for raw deletion primitives and privileged command ownership. |
| `dependency-audit-smoke` | Verifies `pip-audit` is available from the active venv and generates a temporary CycloneDX-style `SBOM.json` with `scripts/generate_sbom.py`. |
| `docs-smoke` | Checks README and README.CN command/governance documentation for required flags, schemas, and release target coverage. |
| `governance-smoke` | Runs a fast end-to-end governance contract check across capabilities, boundary rules, script validation, workflow automation, and CLI analysis contracts. |
| `open-source-smoke` | Verifies public-project governance files, package URLs/license metadata, Dependabot, CodeQL, issue templates, and PR template coverage. |
| `distribution-smoke` | Builds both wheel and sdist, installs each into separate venvs, verifies `cleanmac` / `cleancli` imports, and validates capabilities JSON from both artifacts. |
| `release-artifacts-smoke` | Builds release artifacts, generates and verifies `SHA256SUMS`, installs the wheel, and validates installation-time capabilities JSON. |
| `docker-test` | Runs the test suite in a read-only mounted Debian container from an in-container venv. |
| `no-cache-check` | Runs a no-cache validation path: creates a temporary venv with `PIP_NO_CACHE_DIR=1`, disables pytest cache, uses a temporary mypy cache directory under `/tmp`, writes coverage data to a temporary directory, and removes local pytest/mypy/ruff cache directories before exit. |
| `release-check` | Chains `quality-check`, `local-test`, `pytest-test`, `build-check`, `package-smoke`, `script-smoke`, `bundle-audit-smoke`, `macos-smoke`, `security-smoke`, `dependency-audit-smoke`, `docs-smoke`, `governance-smoke`, `open-source-smoke`, `distribution-smoke`, `release-artifacts-smoke`, and `docker-test` in that order; this is the final quality gate. |
| `no-cache-release-check` | Runs `no-cache-check`, distribution/release artifact smoke checks with `PIP_NO_CACHE_DIR=1`, and Docker validation with `--pull=always`; use this before releases or security audits when cache independence matters. |

CI-ready governance is configured through `.pre-commit-config.yaml`, `pyproject.toml`, and `.github/workflows/ci.yml`. The GitHub Actions workflow uses SHA-pinned third-party actions, then runs all Python test and smoke commands through an explicit venv (`PYTHON=.venv/bin/python`) before invoking `make` targets. It runs `quality-check`, pytest compatibility, package metadata checks, package smoke, script governance smoke, bundle audit smoke, macOS smoke, security smoke, dependency/SBOM smoke, documentation smoke, governance smoke, open-source governance smoke, distribution smoke, no-cache validation, and Docker validation on pull requests and pushes to `main`. CI intentionally does not use `actions/cache`; the no-cache lane also sets `PIP_NO_CACHE_DIR=1`, disables pytest cache, uses a temporary mypy cache, and pulls a fresh Docker image with `--pull=always`.

Release supply-chain checks are configured in `.github/workflows/release.yml`: tagged releases create a workflow venv, build wheel/sdist artifacts, generate `SBOM.json` and `SHA256SUMS`, verify wheel installation, request GitHub artifact attestation with `actions/attest-build-provenance`, and publish to PyPI through trusted publishing.

Open-source project hygiene is covered by `LICENSE`, `CONTRIBUTING.md`, `SECURITY.md`, `CODE_OF_CONDUCT.md`, `AGENTS.md`, `.github/PULL_REQUEST_TEMPLATE.md`, `.github/ISSUE_TEMPLATE/*`, `.github/dependabot.yml`, `.github/workflows/codeql.yml`, and `.github/workflows/release.yml`. Add `.github/CODEOWNERS` only after the target GitHub organization and maintainer teams exist, so invalid owners do not silently disable review routing.

---

## ⚠️ Notes and Limitations

1. No files are deleted by default.
2. System logs, downloads, preferences, document revisions, and similar categories are higher risk and require careful review before execution.
3. Large logs should not always be deleted immediately; they may indicate application or system issues that should be diagnosed first.
4. Caches are usually regenerated after cleanup.
5. Some directories may require Full Disk Access or administrator permissions.
6. Keep plan files, dry-run JSON, and audit reports as audit records.
