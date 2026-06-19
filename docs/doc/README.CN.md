# 🧹 cleanmac — 中文指南

> **macOS 清理工具 · Dry-run 优先 · AI 原生 MCP 集成 · 零依赖**

[![🏠 首页](../../README.md)](/README.md) · [![📗 English Guide](README.md)](README.md)

---

## 📋 目录

- [✨ 核心能力](#-核心能力)
- [🚀 快速开始](#-快速开始)
- [🤖 AI 调用姿势](#-ai-调用姿势)
  - [📦 AI 工具定义](#-ai-工具定义)
  - [🏗️ MCP 服务器](#️-mcp-服务器)
  - [🧭 AI 工作流管线](#-ai-工作流管线)
  - [🔐 AI 确认令牌](#-ai-确认令牌)
  - [🤝 Claude Desktop 配置](#-claude-desktop-配置)
  - [🧪 AI 主机命令](#-ai-主机命令)
- [📦 安装指南](#-安装指南)
- [🛡️ 安全模型](#️-安全模型)
- [⌨️ 命令详解](#-命令详解)
- [🧪 沙箱演练与过滤器](#-沙箱演练与过滤器)
- [🗂️ 清理分类总览](#️-清理分类总览)
- [✅ 开发验证与 CI](#-开发验证与-ci)

---

## ✨ 核心能力

`cleanmac` 提供 **20+ 项能力**，覆盖 macOS 清理全流程：

| # | 能力 | 说明 |
|---|---|---|
| 🧹 | **分类管理** | 列出 key、标题、路径、风险等级 |
| 📊 | **空间分析** | 估算可回收空间，不删除文件 |
| 🔎 | **候选项检查** | 排序、递归、过滤查看候选文件 |
| 🩺 | **诊断建议** | 基于风险和大小的清理建议 |
| 🧾 | **脚本审计** | 只读分析动作计划 |
| 🧭 | **安全工作流** | inspect → diagnose → plan 多阶段管线 |
| 🗺️ | **清理计划** | 可复用的 `cleanmac.plan.v1` JSON |
| 📄 | **清理报告** | 清理前报告、dry-run 明细、执行后报告 |
| 🧪 | **沙箱模式** | `--root` / `--home` 路径重映射 |
| 🤖 | **AI 工具** | 23 个工具，支持 Anthropic / OpenAI / MCP 三种格式 |
| 🏗️ | **MCP Server** | 基于 stdio 的 Model Context Protocol 服务器 |
| 🔐 | **确认令牌** | SHA-256 绑定的 AI 执行授权 |
| 🛡️ | **执行保护** | 预算上限、风险策略、真实根目录保护 |
| 🎯 | **精细过滤** | include、exclude、时间、大小、正则 |
| 🧰 | **环境检查** | doctor 命令检查运行环境和权限 |
| 🪟 | **辅助预览** | Finder 打开目标、符号链接管理 |
| 🔐 | **Bundle 保护** | 应用容器的 allow/block 策略 |
| ♻️ | **Trash 模式** | 可恢复的删除路由 |
| 📜 | **操作日志** | 持久化 JSONL 审计轨迹 |
| 🧾 | **删除日志** | 取证 TSV 记录 |
| ⏱️ | **Debug 计时** | 毫秒级 PERF 日志 |
| 🧪 | **测试模式** | CI/测试中的授权守卫 |

---

## 🚀 快速开始

```bash
# 1️⃣ 查看环境和能力
python3 cleanmac.py capabilities
python3 cleanmac.py --json doctor

# 2️⃣ 列出分类
python3 cleanmac.py clean list
python3 cleanmac.py --json clean list

# 3️⃣ 预览候选项（dry-run，不删除）
python3 cleanmac.py --json clean inspect \
  --categories trash,mails,xcode \
  --older-than-days 7 \
  --max-delete-mb 500 \
  --limit 100 \
  > /tmp/inspect.json

# 4️⃣ 生成计划
python3 cleanmac.py --json clean plan \
  --categories trash,mails,xcode \
  --max-delete-mb 500 \
  > /tmp/plan.json

# 5️⃣ 从计划 dry-run
python3 cleanmac.py --json clean run \
  --plan-file /tmp/plan.json \
  --require-plan-context

# 6️⃣ 执行（确认后！）
python3 cleanmac.py clean run \
  --plan-file /tmp/plan.json \
  --require-plan-context \
  --delete-mode trash \
  --operation-log /tmp/ops.jsonl \
  --execute
```

> 🛡️ **安全提醒：** `clean run` 不加 `--execute` 永远是 dry-run。高风险分类需要额外 `--yes`。真实根目录 `/` 需要 `--allow-live-root`。

---

## 🤖 AI 调用姿势

`cleanmac` 是 **AI 原生**工具 —— 内置结构化工具定义、MCP 服务器和确认令牌系统，让 AI 安全地驱动 macOS 清理。

### 📦 AI 工具定义

导出 **24 个工具**，支持三种格式：

```bash
# 🧠 Anthropic 格式（Claude）
python3 cleanmac.py --json ai-tools --format anthropic | jq '.tools | keys'

# 🟢 OpenAI 格式（GPT）
python3 cleanmac.py --json ai-tools --format openai | jq '.tools | length'

# 🔧 MCP 格式（任意 MCP 客户端）
python3 cleanmac.py --json ai-tools --format mcp | jq '.tools | length'
```

工具分类总览：

| 🤖 工具名 | 📝 描述 | 🏷️ 风险 |
|---|---|---|
| `cleanmac_capabilities` | 描述命令、分类、安全门禁 | readonly |
| `cleanmac_doctor` | 环境和权限诊断 | readonly |
| `cleanmac_list_categories` | 列出所有清理分类 | readonly |
| `cleanmac_diagnose` | 分析并推荐清理动作 | readonly |
| `cleanmac_inspect` | 预览候选项，不删除 | readonly |
| `cleanmac_analyze_categories` | 估算可回收空间 | readonly |
| `cleanmac_analyze_tree` | 扫描目录大文件 | readonly |
| `cleanmac_status_snapshot` | 只读系统健康快照 | readonly |
| `cleanmac_scripts` | 列出命令模板 | readonly |
| `cleanmac_open` | 预览/打开 Finder 目标 | readonly |
| `cleanmac_links` | 预览/管理符号链接映射 | readonly |
| `cleanmac_optimize` | 列出/计划维护任务 | planning |
| `cleanmac_generate_plan` | 生成清理计划 | planning |
| `cleanmac_validate_plan` | 校验计划文件 | planning |
| `cleanmac_workflow` | 🏆 多阶段安全工作流 | readonly |
| `cleanmac_policy_simulate` | 模拟策略执行 | planning |
| `cleanmac_software_list` | 只读应用清单 | readonly |
| `cleanmac_software_leftovers` | 检查应用残留 | readonly |
| `cleanmac_software_startup_items` | 列出启动项 | readonly |
| `cleanmac_software_uninstall_plan` | 卸载计划（不执行） | planning |
| `cleanmac_dry_run_plan` | Dry-run 计划（Trash 模式） | dry-run |
| `cleanmac_execute_plan` | 执行清理（需确认） | destructive |
| `cleanmac_ai_governance_advice` | AI 治理建议与反模式 | readonly |
| `cleanmac_ai_host_policy` | AI 主机允许/拒绝策略 | readonly |

### 📄 AI 合约自省

```bash
# 🔍 完整的 AI 安全合约
python3 cleanmac.py --json capabilities | jq '.ai_contract'

# 🛡️ 安全门禁详情
python3 cleanmac.py --json capabilities | jq '.safety_guardrails'

# 🧰 第一个工具的完整定义
python3 cleanmac.py --json ai-tools --format anthropic | jq '.tools[0]'
```

### 🏗️ MCP 服务器

启动 **Model Context Protocol** stdio 服务器：

```bash
# ▶️ 直接启动
python3 scripts/cleanmac_mcp_server.py

# 🧪 测试模式（安全开发）
CLEANMAC_TEST_MODE=1 CLEANMAC_TEST_NO_AUTH=1 \
  python3 scripts/cleanmac_mcp_server.py
```

**JSON-RPC 2.0 协议示例：**

```bash
# 📋 列出全部 23 个工具
echo '{"jsonrpc":"2.0","id":1,"method":"tools/list"}' | \
  CLEANMAC_TEST_MODE=1 CLEANMAC_TEST_NO_AUTH=1 \
  python3 scripts/cleanmac_mcp_server.py | jq '.result.tools | length'

# 🎯 调用 capabilities 工具
echo '{"jsonrpc":"2.0","id":2,"method":"tools/call","params":{"name":"cleanmac_capabilities","arguments":{}}}' | \
  CLEANMAC_TEST_MODE=1 CLEANMAC_TEST_NO_AUTH=1 \
  python3 scripts/cleanmac_mcp_server.py | jq '.result.content[0].text' | head -5
```

验证服务器是否正常工作：

```bash
make mcp-smoke
# ✅ 输出：mcp-smoke passed
```

### 🧭 AI 工作流管线

推荐的 AI 调用流程：

```mermaid
graph LR
    A[🤖 AI] -->|1. capabilities| B[🔍 发现工具]
    B -->|2. diagnose| C[🩺 分析系统]
    C -->|3. inspect| D[👀 预览候选]
    D -->|4. plan| E[🗺️ 生成计划]
    E -->|5. validate| F[✅ 校验计划]
    F -->|6. run --execute| G[🛡️ 令牌执行]
```

**AI 分步调用：**

```bash
# 🅰️ 管线 A：diagnose → plan（只读）
python3 cleanmac.py --json clean inspect --categories trash,downloads --limit 10
python3 cleanmac.py --json plan --categories trash,downloads --max-items 10

# 🅱️ 管线 B：workflow（单命令，推荐！）
python3 cleanmac.py --json workflow \
  --categories trash,downloads \
  --dry-run-scope selected
```

`workflow` 命令是 **推荐的 AI 入口点** —— 一条只读命令完成 inspect → diagnose → plan 全流程。

### 🔐 AI 确认令牌

安全 AI 执行使用 **SHA-256 确认令牌**，绑定执行上下文：

```bash
# 1️⃣ AI 生成计划（内含 confirmation_token）
python3 cleanmac.py --json plan --categories trash > /tmp/plan.json

# 2️⃣ 提取令牌
TOKEN=$(python3 -c "
import json
p = json.load(open('/tmp/plan.json'))
print(p['ai_confirmation_summary']['confirmation_token_embedded'])
")

# 3️⃣ 用绑定的令牌执行
python3 cleanmac.py --json clean run \
  --categories trash \
  --plan-file /tmp/plan.json \
  --confirmation-token "$TOKEN" \
  --execute
```

令牌格式：`cleanmac-confirm-<32-十六进制字符>`（SHA-256）。相同上下文 → 相同令牌。不同的 root/home/categories → 不同令牌。

### 🤝 Claude Desktop 配置

添加到你的 `claude_desktop_config.json`：

```json
{
  "mcpServers": {
    "cleanmac": {
      "command": "python3",
      "args": ["/绝对路径/to/cleanmac/scripts/cleanmac_mcp_server.py"]
    }
  }
}
```

Cursor / 其他 MCP 客户端：

```json
{
  "mcpServers": {
    "cleanmac": {
      "command": "python3",
      "args": ["/绝对路径/to/cleanmac/scripts/cleanmac_mcp_server.py"],
      "env": {
        "CLEANMAC_TEST_MODE": "1",
        "CLEANMAC_TEST_NO_AUTH": "1"
      }
    }
  }
}
```

### 🧪 AI 主机命令

`cleanmac` 提供多个面向 AI 主机的 CLI 命令，用于集成检查、自省和评估：

```bash
# ✅ AI 就绪检查 — 验证所有 AI 合约、工具和 MCP 服务器
python3 cleanmac.py --json ai-readiness

# 📘 AI 运行手册 — 展示文档化的 AI 调用模式
python3 cleanmac.py --json ai-runbook

# 🔬 AI 自检 — 运行内置 AI 安全自检
python3 cleanmac.py --json ai-self-test

# 📊 AI 决策矩阵 — 查看工具级 MCP 注释和策略
python3 cleanmac.py --json ai-decision-matrix

# 🛡️ AI 治理建议 — 安全的 LLM 调用边界和反模式
python3 cleanmac.py --json ai-governance-advice

# 📦 AI 评估包 — 查看所有评估场景
python3 cleanmac.py --json ai-eval-pack

# 🏃 AI 评估运行 — 执行评估场景
python3 cleanmac.py --json ai-eval-run --scenario smoke
```

运行全部 AI 主机测试：

```bash
make ai-host-smoke
# ✅ 输出：ai-host-smoke passed
```

发布或集成门禁建议先运行治理路线检查，再运行完整 AI / MCP smoke：

```bash
make ai-governance-smoke
make ai-host-smoke
make mcp-smoke
```

治理路线会端到端校验 AI 调用策略：入口治理、dry-run-first 默认值、禁止自动调用破坏性工具、执行前置门禁、Prompt Injection 边界、结构化错误恢复、MCP Host 治理、CI/发布门禁、审计可追踪性和反模式检查。

这些命令在任何环境中都可以安全运行——它们都是只读的内省和验证工具。

---

## 📦 安装指南

### ▶️ 直接运行（无需安装）

```bash
git clone https://github.com/cleanmac/cleanmac.git
cd cleanmac
python3 cleanmac.py clean list
```

### 📥 安装为包

```bash
python3 -m venv .venv
. .venv/bin/activate
python3 -m pip install -e .
cleanmac list
```

### 🐍 环境要求

- Python 3.10+
- macOS（主要支持）/ Linux（有限支持）
- 无外部依赖

### 🔧 可选安装

```bash
python3 -m pip install -e '.[dev,build]'   # 开发 + 构建
python3 -m pip install -e '.[test]'         # 测试
python3 -m pip install -e '.[lint]'         # 代码检查
```

---

## 🛡️ 安全模型

### 🧯 默认 dry-run

```bash
python3 cleanmac.py clean run --categories trash
# 👆 只预览，不删除
```

### 🔴 必须 `--execute` 才真删

```bash
python3 cleanmac.py --root /tmp/sandbox --home /Users/tester clean run \
  --categories trash --execute
```

### 🟡 高风险分类必须 `--yes`

```bash
python3 cleanmac.py clean run --categories downloads --execute --yes
```

### 🧱 真实根目录保护

```bash
python3 cleanmac.py clean run --categories trash --execute --allow-live-root
```

### 🚦 风险策略

| 策略 | 说明 |
|---|---|
| `default` | high / critical 需要 `--yes` |
| `strict` | medium / high / critical 都需要 `--yes` |
| `permissive` | 不因风险等级额外要求 `--yes` |

### 🔐 Bundle 保护

| 策略 | 行为 |
|---|---|
| `--bundle-allowlist <ids>` | 只允许 allowlist 中的 bundle |
| `--bundle-blocklist <ids>` | 跳过 blocklist 中的 bundle |
| 默认 | Apple / iCloud / 系统 bundle 受保护 |

### ♻️ Trash 模式

```bash
python3 cleanmac.py clean run \
  --categories downloads \
  --delete-mode trash \
  --execute \
  --yes
```

> `--delete-mode trash` 将文件移入 `~/.Trash/cleanmac-*` 便于恢复。`--delete-mode permanent` 直接删除。

### 📜 操作日志

默认路径：`~/.cleanmac/operations.jsonl`（JSONL 审计追踪，schema `cleanmac.operation-log-entry.v1`）、`~/.cleanmac/deletions.log`（文本日志）、`cleanmac_debug_session.log`（调试计时）。

```bash
python3 cleanmac.py clean run \
  --plan-file /tmp/plan.json \
  --operation-log /tmp/ops.jsonl \
  --execute
```

---

## ⌨️ 命令详解

### 🧭 一级命令组

| 命令组 | 子命令 | 说明 |
|---|---|---|
| `clean` | `list`, `inspect`, `plan`, `validate-plan`, `run`, `scripts`, `open`, `links` | 🧹 清理操作 |
| `software` | `list`, `leftovers`, `startup-items`, `uninstall-plan` | 📦 应用清单（只读） |
| `optimize` | `list`, `plan`, `run` | ⚙️ 维护任务（仅 dry-run） |
| `analyze` | `categories`, `tree`, `scan` | 📊 空间分析 |
| `status` | `snapshot` | 🩺 系统健康 |

### `capabilities`

```bash
python3 cleanmac.py capabilities        # 人类可读
python3 cleanmac.py --json capabilities  # 机器可读
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

# 完整安全执行
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

### `workflow`（🏆 推荐 AI 入口）

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

### `analyze`

```bash
python3 cleanmac.py --json analyze categories --all
python3 cleanmac.py --json analyze tree --path ~/Library --depth 2 --top 20
python3 cleanmac.py --json analyze scan --path ~/Downloads --depth 1 --top 10
```

### `list`（`clean list` 的扁平别名）

```bash
python3 cleanmac.py --json list
python3 cleanmac.py list
```

### `policy-simulate`（`clean policy-simulate` 的扁平别名）

```bash
python3 cleanmac.py --json policy-simulate --plan-file /tmp/plan.json --execute --delete-mode trash
```

### `completion`

```bash
python3 cleanmac.py completion bash       # Bash 补全脚本
python3 cleanmac.py completion zsh        # Zsh 补全脚本
python3 cleanmac.py completion fish       # Fish 补全脚本
python3 cleanmac.py --json completion bash  # 机器可读（含 schema）
```

### `ai-tools`

```bash
python3 cleanmac.py --json ai-tools                          # 全部格式
python3 cleanmac.py --json ai-tools --format anthropic        # Anthropic/Claude 格式
python3 cleanmac.py --json ai-tools --format openai           # OpenAI/GPT 格式
python3 cleanmac.py --json ai-tools --format mcp              # MCP 工具目录格式
```

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

---

## 🧪 沙箱演练与过滤器

### 🧪 沙箱演练

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

### 🎯 过滤器选项

| 选项 | 说明 |
|---|---|
| `--include "*.log"` | 只处理匹配 glob 的项 |
| `--exclude "*.keep"` | 跳过匹配 glob 的项 |
| `--older-than-days 14` | 按 mtime 过滤 |
| `--min-size-mb 1` | 最小大小 |
| `--name-regex "(log\|tmp)$"` | 对 basename 用正则 |
| `--max-delete-mb 500` | 预算：总字节 |
| `--max-items 100` | 预算：数量 |
| `--fail-on-skipped` | 有跳过项时拒绝 |

### ⚙️ 全局参数

| 参数 | 默认值 | 说明 |
|---|---|---|
| `--root <path>` | `/` | 路径重映射根目录 |
| `--home <path>` | `$HOME` | 用于解析 `~` |
| `--json` | false | JSON 输出 |
| `--report-file <path>` | 无 | 保存审计报告 |

---

## 🗂️ 清理分类总览

| Key | 标题 | 风险 | 默认 | 路径 |
|---|---|---|---|---|
| `trash` | 🗑️ 废纸篓 | low | ✅ | `~/.Trash/` |
| `mails` | 📧 Apple Mail | low | ✅ | `~/Library/Mail Downloads/` |
| `xcode` | 💻 Xcode | low | ✅ | `~/Library/Developer/Xcode/` |
| `incompleteDownloads` | ⬇️ 未完成下载 | low | ✅ | `~/Downloads/*.part` |
| `bash` | 📜 Bash 历史 | medium | ❌ | `~/.bash_history` |
| `terminal` | 🖥️ 终端日志 | medium | ❌ | `/private/var/log/asl/` |
| `userAppLogs` | 📋 应用日志 | medium | ❌ | `~/Library/Containers/*/Logs/` |
| `userAppCache` | 🗃️ 应用缓存 | medium | ❌ | `~/Library/Containers/*/Caches/` |
| `userCache` | 📦 用户缓存 | medium | ❌ | `~/Library/Caches/` |
| `userLogs` | 📝 用户日志 | medium | ❌ | `~/Library/logs/` |
| `downloads` | ⬇️ 下载 | high | ❌ | `~/Downloads/` |
| `systemLogs` | 🖥️ 系统日志 | high | ❌ | `/Library/logs/` |
| `imessage` | 💬 iMessage | high | ❌ | `~/Library/Messages/` |
| `userPrefs` | ⚙️ 偏好设置 | critical | ❌ | `~/Library/Preferences/` |
| `docRev` | 📄 文档版本 | critical | ❌ | `/.DocumentRevisions-V100/` |

其他应用专用分类：`groupContainerCaches`、`androidStudio`、`jetbrains`、`vscode`、`docker`、`chrome`、`firefox`、`slack`、`zoom`、`teams`、`nodePackageCaches`、`pythonPackageCaches`、`goBuildCaches`。系统/深层分类：`rotate_log_once`（日志轮转）、`deviceFirmware`（固件缓存）、`appleSiliconCaches`（Rosetta/M1 缓存）。治理：`official_uninstaller_vendor` 检测 CrowdStrike 等官方卸载器。

---

## ✅ 开发验证与 CI

### 🧪 本地验证

```bash
python3 -m unittest -v                            # 全部测试
python3 -m unittest tests.test_mcp_server -v      # MCP 专项
make mcp-smoke                                     # MCP 冒烟测试
make ai-robustness-smoke                           # AI 鲁棒性回归测试
make local-test                                    # 完整本地测试
make quality-check                                 # lint + type + coverage
make docs-smoke                                    # 文档校验
make governance-smoke                              # 治理合约检查
make open-source-smoke                             # 开源治理检查
make dependency-audit-smoke                        # pip-audit + SBOM.json
make no-cache-check                                # 无缓存全量验证
make no-cache-release-check                        # 无缓存发布验证
```

### 📊 Makefile 目标

| 目标 | 验证内容 |
|---|---|
| `lint` | Ruff format + lint |
| `type-check` | mypy |
| `coverage` | 单元测试 + 阈值 |
| `quality-check` | lint → type-check → coverage |
| `local-test` | No-auth 测试 |
| `pytest-test` | 隔离 venv pytest |
| `format` | 用 ruff 自动格式化代码 |
| `package-smoke` | Editable 安装 |
| `script-smoke` | 模板治理 |
| `mcp-smoke` | MCP tools/list + tools/call |
| `bundle-audit-smoke` | Bundle drift 审计 |
| `build-check` | 构建 wheel/sdist + twine 检查 |
| `macos-smoke` | macOS 专项测试 |
| `real-macos-smoke` | 真实 macOS 只读测试 |
| `security-smoke` | 静态安全扫描 |
| `dependency-audit-smoke` | pip-audit + SBOM.json |
| `docs-smoke` | README 覆盖检查 |
| `governance-smoke` | 治理合约检查 |
| `ai-governance-smoke` | AI 治理路线检查 |
| `ai-host-smoke` | AI 主机集成测试套件 |
| `ai-robustness-smoke` | AI 并发、幂等、协议与 trace 回归 |
| `distribution-smoke` | wheel + sdist |
| `release-artifacts-smoke` | SHA256SUMS + 证明 |
| `docker-test` | Debian 容器测试 |
| `no-cache-check` | 无缓存全量验证 |
| `no-cache-release-check` | 无缓存发布验证 |
| `no-cache-docker-test` | Docker 测试（--pull=always） |
| `release-check` | 全部门禁串联 |

### 🤖 CI 配置

`.github/workflows/ci.yml` 在 PR 和推送到 `main` 时运行：

- **Quality**：lint、type-check、coverage（Python 3.10–3.13）
- **Smoke**：local-test、build-check、package、script、docs、governance、open-source、distribution、dependency audit、**MCP smoke**
- **Security**：不安全删除模式检查、高风险回归测试、gitleaks
- **No-cache**：`PIP_NO_CACHE_DIR=1` 验证
- **Docker**：Linux 容器测试

---

## ⚠️ 注意事项

1. 📝 **默认不删除** —— 务必先确认 dry-run 输出
2. 🩺 **大日志可能代表异常** —— 先诊断再清理
3. ♻️ **缓存会再生** —— 清理安全，但可能影响应用启动速度
4. 🔑 **Full Disk Access** —— 部分路径需要 macOS 权限授权
5. 📋 **保留审计记录** —— 归档计划、dry-run JSON 和报告
6. 🐛 **问题反馈** → [github.com/cleanmac/cleanmac/issues](https://github.com/cleanmac/cleanmac/issues)
7. 🔒 **安全漏洞** → 见 [SECURITY.md](../../SECURITY.md)
