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

`cleanmac` 提供 **30+ 项能力**，覆盖 macOS 清理、运营审查和 AI Host 集成全流程：

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
| 🤖 | **AI 工具** | 34 个工具，支持 Anthropic / OpenAI / MCP 三种格式 |
| 🏗️ | **MCP Server** | 基于 stdio 的 Model Context Protocol 服务器 |
| 🧾 | **审查选择** | `cleanmac.review-selection.v1` 文件可约束 clean、startup 和 privacy 执行 |
| 🔍 | **运营预检** | permissions、startup、privacy、外部工具 dry-run 计划 |
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

# 5b️⃣ 可选：把计划转成可审查选择文件
python3 cleanmac.py --json review \
  --input-file /tmp/plan.json \
  --selection-file /tmp/selection.json

# 6️⃣ 执行（确认后！）
python3 cleanmac.py clean run \
  --plan-file /tmp/plan.json \
  --review-selection-file /tmp/selection.json \
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

导出 **34 个工具**，支持三种格式：

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
| `cleanmac_software_inspect` | 检查应用清理候选项 | readonly |
| `cleanmac_startup_audit` | 审计 LaunchAgents/Daemons 和 StartupItems | readonly |
| `cleanmac_startup_plan` | 计划启动项禁用动作，不执行 | planning |
| `cleanmac_startup_disable` | 禁用已审查的用户启动 plist（需确认） | destructive |
| `cleanmac_privacy_inspect` | 检查浏览器/应用隐私清理候选项 | readonly |
| `cleanmac_privacy_plan` | 生成隐私清理计划，不删除数据 | planning |
| `cleanmac_privacy_execute` | 永久删除已审查的隐私数据（需确认） | destructive |
| `cleanmac_tool_plan` | 为外部工具生成语义计划 | planning |
| `cleanmac_tool_execute_dry_run` | Dry-run allowlisted 外部工具命令 | dry-run |
| `cleanmac_review` | 将报告/计划归一化为审查选择 | planning |
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
# 📋 列出全部 34 个工具
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

make mcp-resource-index-smoke
# ✅ 输出：mcp-resource-index-smoke passed
```

AI Host 应先读取 `cleanmac://mcp/resource-index`（`cleanmac.mcp-resource-index.v1`）。这个受治理的 MCP 资源索引会列出每个 MCP resource URI、schema、分类和安全标记，并且所有 resource payload 都会经过脱敏，避免泄露本地路径或凭证。

### 🧭 AI 工作流管线

推荐的 AI 调用流程：

```mermaid
graph LR
    A[🤖 AI] -->|1. capabilities| B[🔍 发现工具]
    B -->|2. diagnose| C[🩺 分析系统]
    C -->|3. inspect| D[👀 预览候选]
    D -->|4. plan| E[🗺️ 生成计划]
    E -->|5. review| F[🧾 审查选择]
    F -->|6. validate| G[✅ 校验计划 + 选择]
    G -->|7. run --execute| H[🛡️ 令牌执行]
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

### 🧾 审查到执行契约

使用 `review` 可把 clean、startup、privacy、tool 或 software 的 plan/report 转成 `cleanmac.review.v1` 和 `cleanmac.review-selection.v1`。把 selection 传给 `clean run`、`policy-simulate`、`startup disable` 或 `privacy execute` 时，cleanmac 会校验 source fingerprint，并只执行已审查选中的条目：

```bash
# 1️⃣ 生成稳定计划
python3 cleanmac.py --json clean plan --categories trash,downloads > /tmp/plan.json

# 2️⃣ 生成审查报告和默认选择文件
python3 cleanmac.py --json review \
  --input-file /tmp/plan.json \
  --selection-file /tmp/selection.json \
  > /tmp/review.json

# 3️⃣ 只 dry-run 已审查选中的项目
python3 cleanmac.py --json clean run \
  --plan-file /tmp/plan.json \
  --review-selection-file /tmp/selection.json \
  --require-plan-context

# 4️⃣ 执行前用策略模拟器查看安全 argv
python3 cleanmac.py --json policy-simulate \
  --plan-file /tmp/plan.json \
  --review-selection-file /tmp/selection.json \
  --execute \
  --delete-mode trash
```

如果 selection 来自其他计划或已过期，命令会在清理或禁用前失败并返回 `SELECTION_VALIDATION_FAILED`。报告中会包含 `cleanmac.review-selection-constraint.v1`，用于审计留痕。破坏性 AI/MCP 工具（`cleanmac_execute_plan`、`cleanmac_startup_disable`、`cleanmac_privacy_execute`）都会 deny auto-call 且 require explicit confirmation。

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
make ai-contract-smoke
make ai-host-smoke
make mcp-smoke
make mcp-resource-index-smoke
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

### 🍺 通过 Homebrew tap 安装

```bash
brew tap cleanmac/tap
brew trust cleanmac/tap
brew install cleanmac
cleanmac --json capabilities
```

Homebrew 6+ 会拒绝加载未信任第三方 tap 中的 formula。`brew trust cleanmac/tap` 会显式信任该 tap；如果只想信任单个 formula，可先执行 `brew trust --formula cleanmac/tap/cleanmac`。

发布自动化会使用 `scripts/generate_homebrew_formula.py` 生成 `release-assets/cleanmac.rb`，把它写入 `cleanmac.release-artifact-manifest.v1`，并通过 `make homebrew-formula-smoke` 校验。若未来 Homebrew core 中存在同名 formula，可使用 `brew install cleanmac/tap/cleanmac` 明确选择 tap。

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
| `startup` | `audit`, `plan`, `disable` | 🚀 启动项审计、禁用计划和已审查禁用执行 |
| `privacy` | `inspect`, `plan`, `execute` | 🔐 浏览器/应用隐私候选项检查、计划和已审查执行 |
| `permissions` | preflight | 🔎 权限和 Full Disk Access 就绪预检 |
| `tool-plan` / `tool-execute` | 外部工具适配器 | 🧰 Docker/Homebrew/Xcode allowlist dry-run 和门禁执行 |
| `review` | 审查归一化 | 🧾 可审查条目、selection、HTML 审计输出 |
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

关键 replay 选项：

| 选项 | 说明 |
|---|---|
| `--plan-file <path>` | replay 现有 `cleanmac.plan.v1` 文件，而不是重新发现候选项 |
| `--review-selection-file <path>` | 校验 `cleanmac.review-selection.v1` 文件，并跳过未被审查选中的计划项 |
| `--require-plan-context` | 要求 replay 计划的 root/home 与当前命令上下文一致 |
| `--require-confirmation-token` | 执行前要求匹配的 AI 确认令牌 |

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

`startup audit` 是只读审计。`startup plan` 为 LaunchAgents、LaunchDaemons 和 StartupItems 输出非破坏性禁用计划。`startup disable` 消费 `cleanmac.startup-plan.v1` 和匹配的 `cleanmac.review-selection.v1`；不加 `--execute` 时是 dry-run，加上 `--execute --yes` 后只禁用已审查选中的用户启动 plist，并记录 `cleanmac.startup-disable-result.v1` / operation-log 审计数据。过期或不匹配的 selection 会以 `SELECTION_VALIDATION_FAILED` fail closed。

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

Privacy 命令用于检查和规划浏览器/应用隐私数据清理，默认保留敏感范围。`privacy execute` 消费 `cleanmac.privacy-plan.v1` 和匹配的 `cleanmac.review-selection.v1`；不加 `--execute` 时是 dry-run，加上 `--execute --yes` 后会永久删除已审查选中的隐私候选项，并记录 `cleanmac.privacy-execute-result.v1` / operation-log 审计数据。过期或不匹配的 selection 会以 `SELECTION_VALIDATION_FAILED` fail closed。

### `permissions`

```bash
python3 cleanmac.py --json permissions --categories trash,systemLogs
```

该预检会报告 Full Disk Access 提示、分类权限、真实根目录要求和执行就绪状态，不修改文件。

### `tool-plan` / `tool-execute`

```bash
python3 cleanmac.py --json tool-plan --tool docker
python3 cleanmac.py --json tool-execute --tool docker
```

外部工具集成使用 allowlist，且默认 dry-run。`tool-execute` 只运行已知 argv 模板，真实执行仍需显式 `--execute --yes`。

### `review`

```bash
python3 cleanmac.py --json review --input-file /tmp/plan.json --selection-file /tmp/selection.json
python3 cleanmac.py --json review --input-file /tmp/plan.json --format html > /tmp/review.html
```

`review` 会把 clean plan/report、startup/privacy/tool plan 和软件卸载计划归一化为可审查条目，并输出 source fingerprint，供 dry-run 或执行前校验选择文件。

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
python3 cleanmac.py --json policy-simulate \
  --plan-file /tmp/plan.json \
  --review-selection-file /tmp/selection.json \
  --execute \
  --delete-mode trash
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
make pytest-governance-smoke                       # Pytest 安全目标策略
make ai-contract-smoke                             # AI 合同样例与 schema fragment
make governed-execution-smoke                      # Startup/privacy 治理执行加固
make open-source-smoke                             # 开源治理检查
make dependency-audit-smoke                        # pip-audit + SBOM.json
make homebrew-formula-smoke                        # Homebrew tap formula 校验
make release-readiness-contract-smoke              # 发布 readiness contract schema 校验
make release-readiness-smoke                       # AI Host 发布 readiness bundle
make release-diagnostics-smoke                     # 发布诊断 + evidence bundle + 操作者摘要
make release-rehearsal-smoke                       # 发布演练 dry-run 门禁
make release-promotion-smoke                       # fail-closed 发布决策
make release-rollback-smoke                        # manual-only 回滚计划
make release-post-publish-smoke                    # manual-only 发布后验证计划
make release-post-publish-result-smoke             # manual-only 发布后闭环证据
make release-post-publish-evidence-template-smoke  # manual-only 发布后证据输入模板
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
| `pytest-governance-smoke` | Pytest 安全目标策略与 release-only parity 范围 |
| `ai-governance-smoke` | AI 治理路线检查 |
| `governed-execution-smoke` | Startup/privacy 治理执行加固 |
| `ai-host-smoke` | AI 主机集成测试套件 |
| `ai-robustness-smoke` | AI 并发、幂等、协议与 trace 回归 |
| `distribution-smoke` | wheel + sdist |
| `homebrew-formula-smoke` | Homebrew tap formula 生成 |
| `release-artifacts-smoke` | SHA256SUMS + ARTIFACT-MANIFEST.json + 证明 |
| `release-readiness-contract-smoke` | 发布 readiness contract 校验 |
| `release-readiness-smoke` | AI Host 发布 readiness 门禁与审计问题单 |
| `release-diagnostics-smoke` | 发布诊断、evidence bundle 和操作者摘要 |
| `release-rehearsal-smoke` | 发布演练阶段与必需证据检查 |
| `release-promotion-smoke` | 缺失证据时发布决策 fail-closed 阻断 |
| `release-rollback-smoke` | PyPI、GitHub Release 与 Homebrew tap 的 manual-only 回滚计划 |
| `release-post-publish-smoke` | PyPI、GitHub Release 与 Homebrew tap 的 manual-only 发布后验证计划 |
| `release-post-publish-result-smoke` | PyPI、GitHub Release 与 Homebrew tap 的 manual-only 发布后闭环结果 |
| `release-post-publish-evidence-template-smoke` | 操作者提供发布后闭环证据的 manual-only 输入模板 |
| `docker-test` | Debian 容器测试 |
| `no-cache-check` | 无缓存全量验证 |
| `no-cache-release-check` | 无缓存发布验证 |
| `no-cache-docker-test` | Docker 测试（--pull=always） |
| `release-check` | 全部门禁串联 |

发布产物验证会通过 `scripts/generate_release_manifest.py` 生成 `cleanmac.release-artifact-manifest.v1`。该 manifest 绑定 wheel/sdist、`SBOM.json`、`cleanmac.rb` 与 `SHA256SUMS`，确保本地 smoke 与 GitHub Actions 对 release candidate 使用同一套校验逻辑。`make pytest-governance-smoke` 校验 pytest parity 使用显式 release-only 安全目标列表，而不是宽泛收集 `test_cleanmac.py tests`。`make release-readiness-contract-smoke` 校验发布 readiness contract 结构，`make release-readiness-smoke` 会在 `make release-check` 与 `make no-cache-release-check` 前校验只读 `cleanmac.release-readiness.v1` bundle。`make release-diagnostics-smoke` 会额外校验 `cleanmac.release-diagnostics.v1`、`cleanmac.release-evidence.v1` 和 `cleanmac.release-operator-summary.v1`。`make release-rehearsal-smoke`、`make release-promotion-smoke`、`make release-rollback-smoke`、`make release-post-publish-smoke`、`make release-post-publish-result-smoke`、`make release-post-publish-evidence-template-smoke` 覆盖 `cleanmac.release-rehearsal.v1`、`cleanmac.release-promotion-decision.v1`、`cleanmac.release-rollback-plan.v1`、`cleanmac.release-post-publish-verification.v1`、`cleanmac.release-post-publish-result.v1` 与 `cleanmac.release-post-publish-evidence-template.v1`；CI 会把 `RELEASE-REHEARSAL.json`、`RELEASE-PROMOTION-DECISION.json`、`RELEASE-ROLLBACK-PLAN.json`、`RELEASE-POST-PUBLISH-VERIFICATION.json`、`RELEASE-POST-PUBLISH-RESULT.json`、`RELEASE-POST-PUBLISH-EVIDENCE.example.json` 随发布证据一起归档。

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
