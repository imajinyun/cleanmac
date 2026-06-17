# cleanmac 使用文档

`cleanmac` 是一个面向 macOS 的命令行清理工具，内置常见日志、缓存、临时文件、开发残留和用户目录清理规则。它强调可审计、默认 dry-run、计划复用、预算保护和沙箱验证，避免误删宿主机文件。

`cleanmac` 是独立 Python 实现，不内置外部 macOS 清理工具源码，也不与同类项目存在从属或关联关系；安全边界、治理模型和发布自动化均在本仓库内维护。

> **安全原则：默认不删除。** `cleanmac clean` 默认永远是 dry-run；只有显式传入 `--execute` 才会真正删除文件。对于 high / critical 风险分类，默认还必须额外传入 `--yes`。对真实根目录 `/` 执行还必须显式传入 `--allow-live-root`，推荐始终先使用 `--root` / `--home` 沙箱验证。确需执行时优先使用可恢复的 `--delete-mode trash`；只有在复核候选项、预算、skipped 项、operation log 和备份后，才使用 `--delete-mode permanent`。

---

## 目录

- [核心能力](#核心能力)
- [快速开始](#快速开始)
- [详细操作指南](#详细操作指南)
- [安全模型](#安全模型)
- [安装与运行](#安装与运行)
- [全局参数](#全局参数)
- [分类选择参数](#分类选择参数)
- [清理分类总览](#清理分类总览)
- [命令详解](#命令详解)
- [JSON 输出字段说明](#json-输出字段说明)
- [开发验证](#开发验证)
- [注意事项与限制](#注意事项与限制)

---

## 核心能力

`cleanmac` 当前支持：

1. **清理分类管理**：列出分类 key、标题、路径、风险等级、默认状态、推荐状态和高级状态。
2. **空间分析**：统计选中分类下的可回收空间，不删除文件。
3. **候选项检查**：列出目标目录中的候选文件/目录，支持排序、递归和过滤。
4. **诊断建议**：根据分类风险、目录大小、日志/缓存特征给出清理建议。
5. **脚本审计**：展示分析和删除动作的计划，不自动执行破坏性操作。
6. **固定安全工作流**：一次性运行脚本复核、分析、诊断、检查、dry-run 和人工执行提示。
7. **清理计划**：生成 `cleanmac.plan.v1` JSON，后续可校验和复用。
8. **清理报告**：输出清理前报告、dry-run 明细、执行后报告和审计文件。
9. **沙箱路径重定向**：通过 `--root` / `--home` 将真实路径映射到临时目录。
10. **多层执行保护**：支持 `--execute`、`--yes`、`--allow-live-root`、`--max-delete-mb`、`--max-items`、`--fail-on-skipped`、`--require-plan-context`。
11. **精细过滤**：支持 `--include`、`--exclude`、`--older-than-days`、`--min-size-mb`、`--name-regex`。
12. **环境检查**：`doctor` 只读检查平台、Python、Full Disk Access 提示、真实根目录执行门禁和路径别名归一化。
13. **辅助行为预览**：`open` 预览 Finder 打开目标；`links` 预览或维护日志/缓存符号链接目录。
14. **包化实现**：`cleanmac.py` 是薄入口，实际实现位于 `cleancli` 包中，因此既可以在源码目录直接运行，也可以安装包后通过同一 CLI 运行。
15. **截图式一级命令组**：推荐使用 `clean`、`software`、`optimize`、`analyze`、`status` 五个一级命令组。
16. **机器可消费命令模板**：`scripts` 输出 `command_templates`，包含 `argv`、`uses_shell`、`destructive`、`safe_to_auto_execute`、`manual_review_required`、`placeholders` 等元数据。
17. **一致的对象报告**：对象型 JSON 报告包含 `schema`、`destructive`，并在适用时包含 `dry_run`；`list --json` 仍保持裸分类数组输出。
18. **CLI 安全扩展**：扩展 bundle ID allow/block 策略、应用专属清理规则、Group Container 防护、官方卸载程序路由、持久化 JSONL 操作日志、取证删除日志、debug 计时、测试模式授权守卫和可恢复 Trash 路由。
19. **开源治理**：补齐 license、贡献指南、安全策略、行为准则、Issue/PR 模板、Dependabot、CodeQL、pip-audit smoke 和发布产物 `SBOM.json`，支撑公开协作。
20. **开发质量门禁**：Makefile 提供本地测试、editable 包安装 smoke、脚本/文档/治理/开源 smoke、wheel/sdist 发布包 smoke、Docker 测试和 release-check。

当前 CLI 安全扩展已经落到具体参数和 JSON 字段：

| 能力 | CLI 入口 | JSON / 报告字段 |
|---|---|---|
| Bundle 保护 | `clean run --bundle-allowlist <ids>` 和 `clean run --bundle-blocklist <ids>` | `bundle_allowlist`、`bundle_blocklist`、item 级 `bundle_id`，以及 skipped 原因 `bundle-not-allowlisted` / `bundle-blocklisted` |
| 应用专属清理 | `clean inspect --categories androidStudio,jetbrains,vscode,docker,raycast,unity,unreal,godot,deveco,maestro,chrome,firefox,slack,zoom,teams,nodePackageCaches,pythonPackageCaches,goBuildCaches,groupContainerCaches` | 分类元数据，以及受保护画像、凭证、工作区和 Group Container 数据对应的 `app-protected-data`、`protected-container-data`、`protected-group-container` skipped 原因 |
| 官方卸载程序路由 | `software list` 和 `software uninstall-plan --app <name>` | 对 ESET、Jamf、CrowdStrike、SentinelOne、GlobalProtect、Cisco 输出 `official_uninstaller_vendor`、`official_uninstaller_required` 和厂商卸载提示 |
| 持久化操作日志 | `clean run --operation-log <path>` | 每个执行项追加一行 `cleanmac.operation-log-entry.v1` JSONL 记录 |
| 取证删除日志 | `clean run --execute` | `~/.cleanmac/deletions.log` 以 tab 分隔记录 timestamp、mode、size、status、path 和 detail |
| Debug 计时 | `CLEANMAC_DEBUG=1 cleanmac ...` | `~/.cleanmac/cleanmac_debug_session.log` 记录毫秒级 `PERF` 条目 |
| 测试模式授权守卫 | `CLEANMAC_TEST_MODE=1` / `CLEANMAC_TEST_NO_AUTH=1` | 测试中阻断 sudo / AppleScript helper；`CLEANMAC_TEST_TRASH_DIR` 可把 Trash 测试路由到夹具目录 |
| 可恢复删除 | `clean run --delete-mode trash` | `delete_mode`、item 级 `trash_path`、`safety_gate.delete_mode`、符号链接拒绝和 Trash fail-closed 行为 |

扩展应用缓存规则的 dry-run 示例：

```bash
python3 cleanmac.py --json clean inspect --categories chrome,firefox,slack,zoom,teams,nodePackageCaches,pythonPackageCaches,goBuildCaches
```

---

## 快速开始

> **命令格式提示：** 当前 CLI 的全局参数必须放在一级命令之前，例如 `python3 cleanmac.py --json clean inspect ...`、`python3 cleanmac.py --root /tmp/root --home /Users/tester clean run ...`。子命令参数放在动作之后，例如 `clean inspect --categories ...`、`clean run --plan-file ...`。

### 一级命令组

| 命令组 | 对齐截图 | 当前能力 |
|---|---|---|
| `clean` | 清理 | `list`、`inspect`、`plan`、`validate-plan`、`run`、`scripts`、`open`、`links` |
| `software` | 软件 | 只读软件清单、启动项位置、卸载计划占位，不执行卸载 |
| `optimize` | 优化 | 维护任务清单和 dry-run 计划，不执行系统修改 |
| `analyze` | 分析 | 分类空间分析、目录扫描和 tree 输出 |
| `status` | 状态 | 只读系统快照，当前包含 load average 和磁盘信息 |

### 查看能力和分类

```bash
cd /path/to/cleanmac
python3 cleanmac.py capabilities
python3 cleanmac.py clean list
python3 cleanmac.py --json doctor
```

### 预览常见日志候选项

```bash
python3 cleanmac.py --json clean inspect \
  --categories userLogs,userAppLogs,terminal \
  --older-than-days 7 \
  --max-delete-mb 1000 \
  --max-items 500 \
  > /tmp/cleanmac-logs-inspect.json
```

### 生成、校验并 dry-run 清理计划

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

### 人工确认后执行

```bash
python3 cleanmac.py clean run \
  --plan-file /tmp/cleanmac-logs-plan.json \
  --require-plan-context \
  --execute \
  --allow-live-root
```

> 如果分类包含 high / critical 风险项，还需要额外加 `--yes`。

---

## 详细操作指南

### 1. 第一次运行前检查环境

```bash
cd /path/to/cleanmac

# 查看命令、过滤器和安全门禁
python3 cleanmac.py --json capabilities

# 只读检查运行环境、权限提示、真实根目录保护和路径别名归一化
python3 cleanmac.py --json doctor

# 查看可选分类、风险等级、默认分类和说明
python3 cleanmac.py --json clean list
```

建议先关注：

- `safety_guardrails`：确认 dry-run、执行、预算和真实根目录保护策略。
- `checks.full_disk_access`：部分目录在 macOS 上可能需要 Full Disk Access。
- `risk`：优先从 low / medium 分类开始。

### 2. 推荐的人工清理主流程

固定顺序：**list/capabilities → inspect → plan → validate-plan → dry-run clean → 人工确认 → execute**。

```bash
# 1) 查看能力和分类；不会删除
python3 cleanmac.py clean list
python3 cleanmac.py capabilities

# 2) 先检查候选项；不会删除
python3 cleanmac.py --json clean inspect \
  --categories trash,mails,xcode,userLogs \
  --older-than-days 7 \
  --max-delete-mb 500 \
  --max-items 200 \
  --limit 100 \
  > /tmp/cleanmac-inspect.json

# 3) 生成计划文件；不会删除
python3 cleanmac.py --json clean plan \
  --categories trash,mails,xcode,userLogs \
  --older-than-days 7 \
  --max-delete-mb 500 \
  --max-items 200 \
  --exclude "*.keep" \
  > /tmp/cleanmac-plan.json

# 4) 校验计划；不会删除
python3 cleanmac.py --json clean validate-plan \
  --plan-file /tmp/cleanmac-plan.json

# 5) 复用计划 dry-run；不会删除
python3 cleanmac.py --json clean run \
  --plan-file /tmp/cleanmac-plan.json \
  --require-plan-context \
  > /tmp/cleanmac-dry-run.json
```

阅读 dry-run JSON 时，至少确认：

- `dry_run` 是 `true`。
- `items[]` 都是你愿意删除的目标。
- `safety_gate` 没有异常阻断。
- `skipped_summary` 是否符合预期。
- `pre_clean_report.summary` 中的候选数量和估算空间是否合理。

确认无误后再执行：

```bash
python3 cleanmac.py clean run \
  --plan-file /tmp/cleanmac-plan.json \
  --require-plan-context \
  --delete-mode trash \
  --operation-log /tmp/cleanmac-operations.jsonl \
  --execute \
  --allow-live-root
```

若包含 high / critical 分类：

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

如果要清理应用容器拥有的缓存路径，建议显式声明 bundle 策略：

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

### 3. 沙箱演练

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

沙箱执行只删除映射目录下的候选内容，不会触碰宿主机真实目录。

### 4. 精细过滤和预算保护

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

| 参数 | 作用 |
|---|---|
| `--include` | 只处理匹配 glob 的候选项。 |
| `--exclude` | 跳过匹配 glob 的候选项。 |
| `--older-than-days` | 只处理足够旧的候选项。 |
| `--min-size-mb` | 只处理达到最小大小的候选项。 |
| `--name-regex` | 只处理 basename 命中正则的候选项。 |
| `--max-delete-mb` | 候选总大小超过预算时拒绝执行。 |
| `--max-items` | 候选数量超过预算时拒绝执行。 |
| `--fail-on-skipped` | 存在 skipped 项时拒绝执行。 |

### 5. 生成审计报告文件

```bash
python3 cleanmac.py --json --report-file /tmp/cleanmac-audit.json clean run \
  --categories trash,mails,xcode \
  > /tmp/cleanmac-clean-preview.json
```

建议归档：

- `/tmp/cleanmac-clean-preview.json`
- `/tmp/cleanmac-audit.json`
- `/tmp/cleanmac-plan.json`

### 6. 辅助行为预览

```bash
# 查看 Finder 打开目标；默认只预览
python3 cleanmac.py clean open --categories terminal,userAppLogs,userAppCache

# 预览日志/缓存符号链接映射；不会创建
python3 cleanmac.py clean links

# 在沙箱中真实创建并删除符号链接目录
python3 cleanmac.py --root /tmp/cleanmac-root --home /Users/tester clean links \
  --kind logs \
  --execute
python3 cleanmac.py --root /tmp/cleanmac-root --home /Users/tester clean links \
  --kind logs \
  --remove \
  --execute
```

### 7. 常见故障处理

| 现象 | 处理方式 |
|---|---|
| `clean --execute` 被拒绝 | 检查是否缺少 `--execute`、高风险分类是否缺少 `--yes`、真实根目录是否缺少 `--allow-live-root`。 |
| `validate-plan` 提示 root/home mismatch | 使用相同 `--root` / `--home`，或重新生成计划。 |
| 预算阻断执行 | 缩小分类、增加过滤器，或人工确认后调整预算。 |
| `--fail-on-skipped` 阻断执行 | 查看 `skipped_summary` 和 `skipped[]`，确认跳过原因。 |
| Full Disk Access 提示 | 到 macOS System Settings 给终端或运行环境授予 Full Disk Access。 |
| Docker 测试失败 | 先跑 `make local-test` / `make package-smoke`，待 Docker 恢复后补跑 `make release-check`。 |

### 8. 操作红线

- 自动化治理流程不允许运行 `clean --execute`。
- 未完成 dry-run、plan、validate-plan 和人工确认前，不要对真实根目录 `/` 执行清理。
- 不要自动提权或绕过安全门禁。
- high / critical 分类执行时必须人工确认并加 `--yes`。
- 保留计划文件、dry-run JSON 和 audit report，便于复盘。

---

## 安全模型

### 默认 dry-run

```bash
python3 cleanmac.py clean run --categories trash
```

该命令只输出预清理报告和候选项，不删除文件。

### 真正删除必须显式传入 `--execute`

```bash
python3 cleanmac.py --root /tmp/cleanmac-root --home /Users/tester clean run \
  --categories trash \
  --execute
```

### high / critical 分类必须传入 `--yes`

```bash
python3 cleanmac.py clean run --categories downloads --execute --yes --allow-live-root
```

### 风险策略

默认策略下，high / critical 风险分类执行时需要 `--yes`。

| 策略 | 说明 |
|---|---|
| `strict` | medium / high / critical 都需要 `--yes`。 |
| `permissive` | 不因风险等级额外要求 `--yes`；仍必须显式传入 `--execute`。 |

### 真实根目录执行保护

当 `--root /` 时，即使传入 `--execute` 也会默认拒绝执行。必须显式传入：

```bash
python3 cleanmac.py clean run --categories trash --execute --allow-live-root
```

推荐先使用沙箱或计划文件完成验证。

### 只删除目标内容，不删除父目录

清理语义是删除目标目录下的直接内容，保留目标目录本身。执行后报告会通过 `target_preservation` 校验目标目录是否仍存在。

### Bundle 感知的应用数据保护

对于包含应用容器标识的路径，例如 `~/Library/Containers/com.example.app/...`，`cleanmac` 会提取 bundle ID，并在大小预算或删除动作之前应用 bundle 策略：

| 策略 | 行为 |
|---|---|
| `--bundle-allowlist <ids>` | 排他 allow 模式。候选项带有 bundle ID 且不在 allowlist 中时，会以 `bundle-not-allowlisted` 原因跳过。 |
| `--bundle-blocklist <ids>` | 保护模式。候选项带有 bundle ID 且命中 blocklist 时，会以 `bundle-blocklisted` 原因跳过。 |
| 默认 blocklist | 默认保护一组 Apple 通信 / iCloud / 系统服务 bundle，以及常见云盘、安全、容器和网络工具 bundle；完整列表可查看 `capabilities.safety_guardrails.default_protected_bundle_ids`。 |

Allowlist 优先于 blocklist。Bundle 策略只作用于能够识别 bundle ID 的候选项；无法识别 bundle ID 的路径会继续走普通 include/exclude、年龄、大小和安全检查。

### 可恢复 Trash 路由与操作日志

`--delete-mode permanent` 是默认行为，执行时直接删除候选项。`--delete-mode trash` 会把每个执行候选项移动到重定向后的用户 Trash，并使用类似 `~/.Trash/cleanmac-20260616T120000000000Z-download.bin` 的唯一名称，便于从 Trash 恢复。

执行模式默认会把操作记录写入 `~/.cleanmac/operations.jsonl`；`:operation-log <path>` / `--operation-log <path>` 可覆盖该路径。`cleanmac` 会对每个执行项追加一行 JSONL。每条记录使用 `cleanmac.operation-log-entry.v1`，包含 timestamp、command、category、path、bytes、`bundle_id`、`delete_mode`、`trash_path`、root 和 home。Dry-run 不写入 operation-log 记录。

日志会自动做单步轮转：主日志 `~/.cleanmac/cleanmac.log` 的预算为 1 MB，操作日志 `~/.cleanmac/operations.jsonl` 的预算为 5 MB，超出后通过 `rotate_log_once()` 轮转为 `.1`。

## 安装与运行

### 直接运行脚本

```bash
python3 cleanmac.py clean list
```

### 以 Python 包方式安装

```bash
python3 -m venv .venv
. .venv/bin/activate
python3 -m pip install -e .
cleanmac list
```

### Python 版本

建议使用 Python 3.10+。

---

## 全局参数

| 参数 | 默认值 | 说明 |
|---|---|---|
| `--root <path>` | `/` | 路径重映射根目录。真实执行时 `/` 需要额外确认。 |
| `--home <path>` | 当前用户 home | 用于解析 `~` 路径。 |
| `--json` | false | 输出机器可读 JSON。 |
| `--report-file <path>` | 无 | 保存 JSON 审计报告。 |

---

## 分类选择参数

| 参数 | 说明 |
|---|---|
| `--categories <keys>` | 逗号分隔分类 key，例如 `trash,mails,xcode`。 |
| `--default` | 使用默认分类。 |
| `--all` | 使用全部分类，包括高级/高风险分类。 |

---

## 清理分类总览

| key | 标题 | 路径 | 风险 | 默认 | 推荐 | 高级 | 备注 |
|---|---|---|---|---|---|---|---|
| `trash` | Trash | `~/.Trash/` | low | 是 | 是 | 否 | 用户废纸篓 |
| `mails` | Apple Mail downloads | `~/Library/Mail Downloads/`, `~/Library/Containers/com.apple.mail/Data/Library/Mail Downloads/` | low | 是 | 是 | 否 | 仅清理旧 Mail 下载附件，Mail 运行时跳过 |
| `xcode` | Xcode derived data and device logs | `~/Library/Developer/Xcode/DerivedData/`, `~/Library/Developer/Xcode/Archives/`, `~/Library/Developer/Xcode/Products/`, `~/Library/Developer/Xcode/ModuleCache.noindex/`, `~/Library/Developer/CoreSimulator/Caches/` | low | 是 | 是 | 否 | Xcode 派生数据、归档、构建产物与模拟器缓存 |
| `deviceFirmware` | Xcode device support and firmware caches | `~/Library/Developer/Xcode/* DeviceSupport/` | high | 否 | 否 | 是 | 设备支持符号和固件支持缓存，默认只看旧文件 |
| `bash` | Bash history and sessions | `~/.bash_sessions/`, `~/.bash_history` | medium | 否 | 否 | 是 | shell 历史 |
| `terminal` | Terminal ASL logs | `/private/var/log/asl/*.asl` | medium | 否 | 否 | 是 | 可能需要权限 |
| `userAppLogs` | Sandboxed application logs | `~/Library/Containers/*/Data/Library/Logs/` | medium | 否 | 否 | 是 | 应用沙盒日志 |
| `userAppCache` | Sandboxed application caches | `~/Library/Containers/*/Data/Library/Caches/` | medium | 否 | 否 | 是 | 应用沙盒缓存 |
| `userCache` | User caches | `~/Library/Caches/` | medium | 否 | 否 | 是 | 缓存通常会再生成 |
| `userLogs` | User logs | `~/Library/logs/` | medium | 否 | 否 | 是 | 大日志建议先排查问题 |
| `systemLogs` | System logs | `/Library/logs/`, `/var/log/` | high | 否 | 否 | 是 | 系统日志，谨慎处理 |
| `globalTemp` | Global temporary files | `/tmp/` | high | 否 | 否 | 是 | 全局临时目录 |
| `userPrefs` | User preferences | `~/Library/Preferences/` | critical | 否 | 否 | 是 | 极高风险 |
| `downloads` | Downloads | `~/Downloads/` | high | 否 | 否 | 是 | 用户下载目录，必须显式选择 |
| `incompleteDownloads` | Incomplete browser downloads | `~/Downloads/*.download`, `~/Downloads/*.crdownload`, `~/Downloads/*.part` | low | 是 | 是 | 否 | 未完成下载，跳过正在使用的文件 |
| `spotlight` | Spotlight index | `/.Spotlight-V100/` | high | 否 | 否 | 是 | 可能需要权限 |
| `docRev` | Document revisions | `/.DocumentRevisions-V100/` | critical | 否 | 否 | 是 | 文档版本历史 |
| `imessage` | iMessage attachments | `~/Library/Messages/Attachments/` | high | 否 | 否 | 是 | 可能需要 Full Disk Access |
| `appleSiliconCaches` | Apple Silicon and Rosetta runtime caches | `/private/var/db/oah/`, `/private/var/db/DetachedSignatures/` | high | 否 | 否 | 是 | Apple Silicon/Rosetta 可重建运行时缓存和签名缓存，默认只看旧文件 |
| `systemCaches` | System cache files | `/Library/Caches/**/*.cache`, `/Library/Caches/**/*.tmp`, `/Library/Caches/**/*.log` | high | 否 | 否 | 是 | 系统缓存文件，默认只看旧文件 |
| `systemDiagnostics` | System diagnostic reports | `/Library/Logs/DiagnosticReports/`, `/private/var/db/diagnostics/` 等 | high | 否 | 否 | 是 | 系统诊断日志 |
| `thirdPartySystemLogs` | Third-party system logs | `/Library/Logs/Adobe/`, `/Library/Logs/CreativeCloud/`, `/Library/Logs/adobegc.log` | medium | 否 | 否 | 是 | 第三方系统日志 |
| `macosInstallers` | macOS installer remnants | `/macOS Install Data/`, `/Applications/Install macOS*.app` | high | 否 | 否 | 是 | 旧安装器，跳过运行中和当前系统版本 |
| `systemUpdates` | System update remnants | `/Library/Updates/` | high | 否 | 否 | 是 | 系统更新残留，跳过受限项 |
| `browserCodeSignCache` | Browser code signature caches | 动态扫描 `/private/var/folders/*/*/X/` | medium | 否 | 否 | 是 | 浏览器代码签名缓存 |
| `gpuCaches` | Rebuildable GPU and Metal caches | 动态扫描 `/private/var/folders/*/*/C/` | medium | 否 | 否 | 是 | 仅清理过期可重建 GPU 缓存 |
| `darwinUserTemp` | Darwin user temporary files | `DARWIN_USER_TEMP_DIR` | medium | 否 | 否 | 是 | 当前用户运行时临时目录 |
| `darwinUserCache` | Darwin user runtime caches | `DARWIN_USER_CACHE_DIR` | medium | 否 | 否 | 是 | 当前用户运行时缓存目录 |

---

## 命令详解

当前推荐使用截图对齐的一级命令组：`clean`、`software`、`optimize`、`analyze`、`status`。`--json`、`--root`、`--home`、`--report-file` 等全局参数必须放在一级命令组之前。

### 推荐命令组

```bash
# 清理：预览、计划、校验、dry-run、执行
python3 cleanmac.py clean list
python3 cleanmac.py --json clean inspect --categories trash,mails,xcode
python3 cleanmac.py --json clean plan --categories trash,mails,xcode > /tmp/cleanmac-plan.json
python3 cleanmac.py --json clean validate-plan --plan-file /tmp/cleanmac-plan.json
python3 cleanmac.py --json clean run --plan-file /tmp/cleanmac-plan.json --require-plan-context

# 软件：目前只读规划，不执行卸载
python3 cleanmac.py --json software list
python3 cleanmac.py --json software startup-items
python3 cleanmac.py --json software uninstall-plan --app Demo

# 优化：目前输出 dry-run 维护计划
python3 cleanmac.py --json optimize list
python3 cleanmac.py --json optimize plan

# 分析：分类空间与目录树
python3 cleanmac.py --json analyze categories --all
python3 cleanmac.py --json analyze tree --path ~/Library --depth 2 --top 20

# 状态：只读快照
python3 cleanmac.py --json status snapshot
```

### `clean list`

列出分类。

```bash
python3 cleanmac.py clean list
python3 cleanmac.py --json clean list
```

### `capabilities`

输出 CLI 能力、安全门禁、过滤器和验证约束。

```bash
python3 cleanmac.py capabilities
python3 cleanmac.py --json capabilities
```

### `doctor`

只读检查执行环境和权限提示。

```bash
python3 cleanmac.py --json doctor
```

### `analyze categories`

统计可回收空间，不删除文件。

```bash
python3 cleanmac.py analyze categories --categories trash,mails,xcode
python3 cleanmac.py --json analyze categories --all
```

### `analyze scan` / `analyze tree`

扫描任意目录的空间大项，不删除文件。

```bash
python3 cleanmac.py --json analyze tree --path ~/Library --depth 2 --top 20
python3 cleanmac.py --json analyze scan --path ~/Downloads --depth 1 --top 10
```

### `clean inspect`

列出候选项，不删除文件。

```bash
python3 cleanmac.py --json clean inspect \
  --categories userLogs,userAppLogs,terminal \
  --older-than-days 7 \
  --max-delete-mb 1000 \
  --max-items 500
```

`clean inspect` 中的 `--max-delete-mb` / `--max-items` 只做预算预览，会输出 `budget_summary`；真正执行前的预算阻断由 `clean plan` / `clean run` 负责。

### `clean plan`

生成可复用计划，不删除文件。

```bash
python3 cleanmac.py --json clean plan \
  --categories trash,downloads \
  --max-delete-mb 500 \
  --max-items 200 \
  --exclude "*.keep" \
  > /tmp/cleanmac-plan.json
```

### `clean validate-plan`

校验计划并生成当前上下文 preview。

```bash
python3 cleanmac.py --json clean validate-plan \
  --plan-file /tmp/cleanmac-plan.json
```

### `diagnose`

输出诊断建议、推荐清理分类和谨慎清理分类。

```bash
python3 cleanmac.py diagnose --categories trash,mails,xcode,userLogs,downloads
```

### `clean scripts`

输出脚本和动作审计信息，不执行破坏性操作。

```bash
python3 cleanmac.py --json clean scripts --categories trash,mails,xcode
python3 cleanmac.py --json clean scripts --group status
```

JSON 报告包含 `script_inventory.groups.<group>.command_templates` 数组。每个模板用于自动化复核，字段包括：

| 字段 | 说明 |
|---|---|
| `id` | 稳定模板标识，例如 `clean-inspect-selected` 或 `systemLogs-delete-1`。 |
| `kind` | 模板形态：`argv` 表示直接 CLI 调用，`shell` 表示 `/bin/sh -c` 片段。 |
| `command` | 便于人工阅读的 shell-quoted 命令字符串。 |
| `argv` | 结构化参数数组；当 `uses_shell` 为 false 时可不经 shell 解析直接执行。 |
| `uses_shell` | 是否需要 `/bin/sh -c`。分类级 `du` / `rm` 片段使用 shell 模板；CLI 工作流使用直接 argv 模板。 |
| `destructive` | 模板是否代表破坏性操作。 |
| `safe_to_auto_execute` | 自动化是否可以在无人复核时执行。 |
| `manual_review_required` | 是否必须人工复核；破坏性清理模板会置为 true。 |
| `placeholders` | 必须有意替换的占位符名称，例如 `keys`、`plan.json`、`AppName`。 |
| `execution_policy` | 可机器校验的 shell / 破坏性 / 自动化策略镜像，并包含 `requires_placeholder_substitution`。 |

报告还包含 `script_inventory.command_template_contract`，用于声明模板必需字段，以及“所有破坏性模板必须 `safe_to_auto_execute=false` 且 `manual_review_required=true`”的约束。同一报告还会输出 `template_validation` 自校验结果，包含 `valid`、`template_count`、`destructive_template_count`、`violation_count`、`violations`；`make script-smoke` 会在该校验不干净时失败。

### `workflow`

运行固定安全工作流，不执行破坏性清理。

```bash
python3 cleanmac.py --json workflow \
  --categories trash,mails,xcode,userLogs,downloads \
  --dry-run-scope selected
```

### `clean open`

预览或执行 Finder 打开目标。

```bash
python3 cleanmac.py clean open --categories terminal,userAppLogs,userAppCache
```

### `clean links`

预览、创建或删除日志/缓存符号链接目录。

默认日志链接目录为 `~/.CleanMacAppLogLinks/`，缓存链接目录为 `~/.CleanMacAppCacheLinks/`。

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

默认 dry-run；只有传 `--execute` 才删除。

```bash
python3 cleanmac.py --json clean run --categories trash,mails,xcode

python3 cleanmac.py clean run \
  --plan-file /tmp/cleanmac-plan.json \
  --require-plan-context \
  --execute \
  --allow-live-root
```

常用参数：

| 参数 | 说明 |
|---|---|
| `--plan-file <path>` | 读取计划文件。 |
| `--require-plan-context` | 要求当前 root/home 与计划一致。 |
| `--execute` | 真正删除候选项。 |
| `--yes` | high / critical 风险分类执行确认。 |
| `--allow-live-root` | 允许真实根目录执行。 |
| `--max-delete-mb <n>` | 删除预算。 |
| `--max-items <n>` | 候选数量预算。 |
| `--fail-on-skipped` | skipped 项存在时拒绝执行。 |
| `--bundle-allowlist <ids>` | 逗号分隔的 bundle 排他 allowlist；不在 allowlist 的 bundle 候选项会被跳过。 |
| `--bundle-blocklist <ids>` | 逗号分隔的 bundle 保护列表；默认值为内置 `capabilities.safety_guardrails.default_protected_bundle_ids` 列表。 |
| `--delete-mode permanent\|trash` | 永久删除候选项，或用唯一 `cleanmac-*` 名称移入用户 Trash。 |
| `--operation-log <path>` | 每个执行候选项追加一行 JSONL 审计记录。 |

可恢复删除示例：

```bash
python3 cleanmac.py --json clean run \
  --categories downloads \
  --delete-mode trash \
  --operation-log /tmp/cleanmac-operations.jsonl \
  --execute \
  --yes
```

## JSON 输出字段说明

### 对象报告的常见顶层字段

`list --json` 为兼容现有分类列表消费方仍保持裸分类数组输出。其它 JSON 命令输出带 `schema` 的对象报告；对象报告也会包含 `destructive`，并在表达安全状态时包含 `dry_run`。

| 字段 | 说明 |
|---|---|
| `schema` | 报告 schema 名称。 |
| `destructive` | 命令是否执行或代表破坏性操作。 |
| `dry_run` | 命令是否仅预览工作，常见于清理/工作流类报告。 |
| `selected_categories` | 当前选中的分类元数据，常见于清理类报告。 |
| `items` | 候选项或处理项，常见于 inspect/clean 报告。 |
| `skipped` / `skipped_summary` | 被过滤跳过的候选项，常见于 inspect/clean 报告。 |
| `pre_clean_report` / `post_clean_report` | 清理预览/执行报告；`post_clean_report` 仅执行模式填充。 |
| `safety_gate` / `budget_summary` | clean/inspect/validate-plan 流程中的执行门禁和预算检查。 |
| `report_file` | 使用 `--report-file` 时的审计报告文件路径。 |
| `bundle_allowlist` / `bundle_blocklist` | clean 报告应用的 bundle 策略，并同步写入 `safety_gate`。 |
| `delete_mode` | `permanent` 或 `trash`；出现在 clean 报告和 item 行中。 |
| `operation_log` / `operation_log_entry_count` | JSONL 操作日志路径，以及追加的执行记录数量。 |

当前对象报告 schema 包括 `cleanmac.capabilities.v1`、`cleanmac.doctor.v1`、`cleanmac.inspect.v1`、`cleanmac.analyze.v1`、`cleanmac.analyze-tree.v1`、`cleanmac.diagnose.v1`、`cleanmac.scripts.v1`、`cleanmac.script-groups.v1`、`cleanmac.clean.v1`、`cleanmac.plan.v1`、`cleanmac.links.v1`、`cleanmac.open.v1`、`cleanmac.software.v1`、`cleanmac.optimize.v1`、`cleanmac.status.snapshot.v1`、`cleanmac.validate-plan.v1`、`cleanmac.workflow.v1`、`cleanmac.audit.v1`。操作日志 JSONL 记录使用 `cleanmac.operation-log-entry.v1`。

### `items[]` 常见字段

| 字段 | 说明 |
|---|---|
| `category` | 分类 key。 |
| `parent` | 目标父目录。 |
| `path` | 候选项路径。 |
| `bytes` | 字节大小。 |
| `human` | 人类可读大小。 |
| `bundle_id` | 应用容器候选项的归属 bundle ID；无法识别时为空。 |
| `delete_mode` | 当前行选择的删除路由：`permanent` 或 `trash`。 |
| `trash_path` | `--delete-mode trash` 执行后的目标路径；否则为 `null`。 |
| `deleted` | 是否已删除，仅执行报告中有意义。 |

---

## 开发验证

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

| Target | 验证内容 |
|---|---|
| `lint` | 运行 Ruff format check 和 Ruff lint。 |
| `type-check` | 使用项目配置运行 mypy。 |
| `coverage` | 通过 coverage.py 运行单测，并执行配置的覆盖率阈值。 |
| `quality-check` | 串联 `lint`、`type-check`、`coverage`，作为快速 CI 质量门禁。 |
| `local-test` | 运行 `scripts/test.sh`，设置 `CLEANMAC_TEST_NO_AUTH=1` 和 `CLEANMAC_TEST_MODE=1`，stub 高风险系统命令，然后运行单测、治理 smoke 和脚本 smoke。 |
| `pytest-test` | 创建临时 venv，按需安装 test extra，禁用 pytest cache，并在 venv 中使用 pytest 运行现有测试套件，不依赖全局 pytest；渐进迁移期间 unittest 仍是本地和覆盖率统计的权威入口。 |
| `build-check` | 使用 `build` 构建 wheel/sdist，并通过 `twine check` 校验发布包元数据。 |
| `package-smoke` | 在隔离 editable venv 中安装当前源码，并验证 `cleanmac --json capabilities` 输出合法 JSON。 |
| `script-smoke` | 渲染脚本模板，读取 `template_validation`，并确认破坏性模板不能自动执行。 |
| `bundle-audit-smoke` | 使用 sandbox app fixture 运行 Python bundle drift 审计。 |
| `macos-smoke` | 在 no-auth/test-mode 下运行 macOS 相关 smoke；CI 会在 workflow 创建的 venv 中执行。 |
| `security-smoke` | 运行 raw 删除 primitive 与特权命令所有权的静态治理扫描。 |
| `dependency-audit-smoke` | 验证当前 venv 可使用 `pip-audit`，并通过 `scripts/generate_sbom.py` 生成临时 CycloneDX 风格 `SBOM.json`。 |
| `docs-smoke` | 检查 README 和 README.CN 中命令/治理文档是否覆盖必需参数、schema 和 release 目标。 |
| `governance-smoke` | 快速端到端校验 capabilities、边界规则、脚本模板、workflow 自动化契约和 CLI 分析契约。 |
| `open-source-smoke` | 校验公开项目治理文件、包 URL/license 元数据、Dependabot、CodeQL、Issue 模板和 PR 模板覆盖。 |
| `distribution-smoke` | 构建 wheel 和 sdist，分别安装到独立 venv，验证 `cleanmac` / `cleancli` 可导入，并验证两个产物的 capabilities JSON。 |
| `release-artifacts-smoke` | 构建发布产物，生成并验证 `SHA256SUMS`，安装 wheel，并验证安装后的 capabilities JSON。 |
| `docker-test` | 在只读挂载的 Debian 容器中创建容器内 venv 后运行测试。 |
| `no-cache-check` | 运行无缓存验证路径：创建临时 venv 并设置 `PIP_NO_CACHE_DIR=1`，禁用 pytest cache，使用 `/tmp` 下的临时 mypy cache，将 coverage 数据写入临时目录，并在退出前删除本地 pytest/mypy/ruff cache 目录。 |
| `release-check` | 按顺序串联 `quality-check`、`local-test`、`pytest-test`、`build-check`、`package-smoke`、`script-smoke`、`bundle-audit-smoke`、`macos-smoke`、`security-smoke`、`dependency-audit-smoke`、`docs-smoke`、`governance-smoke`、`open-source-smoke`、`distribution-smoke`、`release-artifacts-smoke`、`docker-test`，是最终质量门禁。 |
| `no-cache-release-check` | 运行 `no-cache-check`、带 `PIP_NO_CACHE_DIR=1` 的 distribution/release artifact smoke，以及带 `--pull=always` 的 Docker 验证；适合发布前或安全审计。 |

CI-ready 治理由 `.pre-commit-config.yaml`、`pyproject.toml` 和 `.github/workflows/ci.yml` 共同承载。GitHub Actions 会使用 SHA-pinned 第三方 action，随后创建显式 venv（`PYTHON=.venv/bin/python`），再通过该 venv 执行所有 Python 测试和 smoke 命令。它会在 pull request 和推送到 `main` 时运行 `quality-check`、pytest 兼容性检查、发布包元数据检查、包安装 smoke、脚本治理 smoke、bundle 审计 smoke、macOS smoke、安全扫描 smoke、dependency/SBOM smoke、文档 smoke、治理 smoke、开源治理 smoke、发布包 smoke、无缓存验证和 Docker 验证。CI 不使用 `actions/cache`；无缓存通道还会设置 `PIP_NO_CACHE_DIR=1`、禁用 pytest cache、使用临时 mypy cache，并用 `--pull=always` 拉取新 Docker 镜像。

Release 供应链检查由 `.github/workflows/release.yml` 承载：tagged release 会先创建 workflow venv，再构建 wheel/sdist，生成 `SBOM.json` 和 `SHA256SUMS`，验证 wheel 安装，请求 GitHub artifact attestation（`actions/attest-build-provenance`），并通过 PyPI trusted publishing 发布。

开源项目基础治理文件包括 `LICENSE`、`CONTRIBUTING.md`、`SECURITY.md`、`CODE_OF_CONDUCT.md`、`AGENTS.md`、`.github/PULL_REQUEST_TEMPLATE.md`、`.github/ISSUE_TEMPLATE/*`、`.github/dependabot.yml`、`.github/workflows/codeql.yml` 和 `.github/workflows/release.yml`。只有在目标 GitHub 组织和维护团队真实存在后，才添加 `.github/CODEOWNERS`，避免无效 owner 让 review 路由失效。

---

## 注意事项与限制

1. 默认不会删除任何文件。
2. 系统日志、下载目录、偏好设置、文档版本历史等分类风险较高，执行前必须仔细检查。
3. 大日志不一定应该直接删除，可能代表应用或系统存在异常，应先诊断根因。
4. 缓存清理后通常会再生成。
5. 部分目录可能需要 Full Disk Access 或管理员权限。
6. 建议保留 plan、dry-run JSON 和 audit report 作为审计记录。
