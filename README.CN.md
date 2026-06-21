# 🧹 cleanmac

> **AI-first macOS 清理 CLI · 一次性运行 · Dry-run 优先 · MCP 集成**

- [📗 English Docs](/docs/doc/README.md)
- [📕 中文文档](/docs/doc/README.CN.md)

---

## 🚀 快速开始

```bash
# 🧪 安全预览
python3 cleanmac.py --json clean inspect --categories trash,mails,xcode --limit 10

# 🧩 面向普通用户的安全 Profile
python3 cleanmac.py --json profiles
python3 cleanmac.py --json clean plan --profile safe --ai-origin

# 🗑️ 软件卸载审查闭环
python3 cleanmac.py --json software inspect --app "Example"
python3 cleanmac.py --json software uninstall-plan --app "Example"

# 🤖 AI 工具清单（36 个工具）
python3 cleanmac.py --json ai-tools --format anthropic | jq '.tools | keys'

# 🧭 安全工作流（AI 推荐入口）
python3 cleanmac.py --json workflow --categories trash,downloads --dry-run-scope selected

# 🗂️ 受治理的 MCP 入口（meta → resource/prompt/tool）
python3 cleanmac.py --json ai-host-integration-pack | jq '.recommended_call_sequence'
```

> 🛡️ **安全原则：** 默认不删除。`clean run` 永远是 dry-run，只有显式 `--execute` 才会真正删除。

---

## 🥇 cleanmac 为什么存在

cleanmac 的目标是在 GitHub 上成为更安全、更可治理、可用性足够好的 CLI macOS cleaner，而不是另一个高风险递归 `rm` 脚本。

- **比临时 shell 脚本更安全**：默认 dry-run、删除预算、受保护 bundle、Trash-only 执行、operation log 审计链。
- **比一次性清理器更可审查**：inspect → plan → review → selection → dry-run → execute 全链路显式且机器可读。
- **比传统清理器更适合 AI/MCP**：工具契约、schema registry、host policy、release readiness 和 smoke gate 都是一等输出。
- **设计上零常驻**：cleanmac 只在用户或 AI Host 调用时运行，按需输出文件/报告/日志，然后退出；不实现 GUI/TUI、菜单栏进程、后台守护或主动扫描循环。

---

## 🧠 AI-first，而不是 App-first

cleanmac 有意不在 TUI/GUI 留存体验上竞争。AI 时代的交互层应该是 AI Host 或显式 CLI 命令；cleanmac 只做受治理的执行内核，在被请求时出现，完成工作流后退出。

- 不提供常驻 GUI、TUI、菜单栏进程、登录项或清理守护进程
- 未被调用时不占用后台 CPU 和内存
- 不主动扫描、不弹提醒、不做遥测、不制造注意力留存循环
- 持久状态只存在于机器可读 plan、review-selection、报告和 operation log 中，而不是长期运行的 App session

---

## ⚡ 三分钟安全清理流程

```bash
# 1) 查看最保守的内置 Profile
python3 cleanmac.py --json profiles

# 2) 生成安全计划
python3 cleanmac.py --json clean plan --profile safe --ai-origin > /tmp/cleanmac-plan.json

# 3) 审查并收窄选择范围
python3 cleanmac.py --json review --input-file /tmp/cleanmac-plan.json --selection-file /tmp/cleanmac-selection.json

# 4) 基于审查选择 dry-run
python3 cleanmac.py --json clean run --plan-file /tmp/cleanmac-plan.json --review-selection-file /tmp/cleanmac-selection.json --require-plan-context --delete-mode trash
```

如果之后选择真实执行，cleanmac 仍会保留 Trash 路由、review-selection 约束和 operation-log 记录，而不是直接进入不可恢复删除。

---

## 🛡️ 为什么比 `rm` 脚本安全

`rm` 脚本通常依赖字符串匹配和 shell 展开。cleanmac 增加了明确的安全门禁：

- 受保护 Apple App、敏感用户数据、Containers、Group Containers 会被策略阻断
- 真实执行要求显式 review selection 文件，而不是“匹配到就删”
- 真实删除路径仍通过 Trash 路由和可审计 operation-log entries
- AI/MCP 破坏性工具默认禁止自动调用，并需要确认契约

---

## 🆚 和 Pearcleaner / CleanMyMac / mac-cleanup-py 的区别

- **Pearcleaner**：偏 app-centric UX；cleanmac 更偏 CLI-first governance、机器可读 review handoff、AI/MCP 安全编排。
- **CleanMyMac**：商业化体验完整；cleanmac 强调可审计契约、开放 release evidence、无隐藏后台启发式。
- **mac-cleanup-py / shell cleanup scripts**：适合作为自动化片段；cleanmac 增加 policy gates、protected bundle 逻辑、reviewed execution 和 release-readiness evidence。

---

## ✨ 核心亮点

| 🏷️ | 说明 |
|---|---|
| 🧹 **Dry-run 优先** | 所有清理命令默认只预览，不删除任何文件 |
| 🤖 **AI 原生 · 36 个工具** | 输出 Anthropic / OpenAI / MCP 格式的完整工具定义 |
| 🏗️ **MCP Server** | 内置 Model Context Protocol stdio server，即开即用 |
| 🗂️ **受治理的 MCP 索引** | 通过 meta index 汇总 resource、prompt 与 tool 目录 |
| 🔐 **多层安全门禁** | Bundle 保护、预算上限、Trash 可恢复、执行确认令牌 |
| 🧾 **审查到执行契约** | `review` 选择文件可通过 `--review-selection-file` 约束 clean、startup 和 privacy 执行 |
| 💤 **零常驻占用** | 不提供 GUI/TUI、后台守护、登录项、主动扫描或空闲 CPU/内存占用 |
| 🧪 **沙箱演练** | `--root` / `--home` 路径重映射，安全测试清理效果 |
| 📦 **零依赖** | 纯 Python 3.10+，无需外部包即可运行 |

---

## 📖 详细文档

| 文档 | 链接 |
|---|---|
| 📕 **中文指南** — 完整命令参考、安全模型、AI/MCP 调用姿势、开发验证 | [docs/doc/README.CN.md](docs/doc/README.CN.md) |
| 📗 **English Guide** — full CLI reference, safety model, AI/MCP patterns, development | [docs/doc/README.md](docs/doc/README.md) |

---

## 💻 安装

```bash
# ▶️ 直接运行
python3 cleanmac.py clean list

# 🍺 通过 Homebrew tap 安装
brew tap cleanmac/tap
brew trust cleanmac/tap
brew install cleanmac
cleanmac --json capabilities

# 📥 安装为包
python3 -m pip install -e .
cleanmac list
```

> 需要 Python 3.10+

---

## 🔗 链接

- [📕 详细中文文档](docs/doc/README.CN.md)
- [📗 English Documentation](docs/doc/README.md)
- [🐛 Issues](https://github.com/cleanmac/cleanmac/issues)
- [🔒 Security Policy](SECURITY.md)
