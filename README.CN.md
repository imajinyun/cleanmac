# 🧹 cleanmac

> **macOS 清理工具 · Dry-run 优先 · AI 原生集成**

- [📗 English Docs](/docs/doc/README.md)
- [📕 中文文档](/docs/doc/README.CN.md)

---

## 🚀 快速开始

```bash
# 🧪 安全预览
python3 cleanmac.py --json clean inspect --categories trash,mails,xcode --limit 10

# 🤖 AI 工具清单（34 个工具）
python3 cleanmac.py --json ai-tools --format anthropic | jq '.tools | keys'

# 🧭 安全工作流（AI 推荐入口）
python3 cleanmac.py --json workflow --categories trash,downloads --dry-run-scope selected
```

> 🛡️ **安全原则：** 默认不删除。`clean run` 永远是 dry-run，只有显式 `--execute` 才会真正删除。

---

## ✨ 核心亮点

| 🏷️ | 说明 |
|---|---|
| 🧹 **Dry-run 优先** | 所有清理命令默认只预览，不删除任何文件 |
| 🤖 **AI 原生 · 34 个工具** | 输出 Anthropic / OpenAI / MCP 格式的完整工具定义 |
| 🏗️ **MCP Server** | 内置 Model Context Protocol stdio server，即开即用 |
| 🔐 **多层安全门禁** | Bundle 保护、预算上限、Trash 可恢复、执行确认令牌 |
| 🧾 **审查到执行契约** | `review` 选择文件可通过 `--review-selection-file` 约束 clean、startup 和 privacy 执行 |
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
