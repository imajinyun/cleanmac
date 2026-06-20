# 🧹 cleanmac

> **macOS cleanup tool · Dry-run first · AI-native MCP integration**

- [📗 English Docs](/docs/doc/README.md)
- [📕 中文文档](/docs/doc/README.CN.md)

---

## 🚀 TL;DR

```bash
# 🧪 Safe preview
python3 cleanmac.py --json clean inspect --categories trash,mails,xcode --limit 10

# 🤖 AI tool definitions (33 tools)
python3 cleanmac.py --json ai-tools --format anthropic | jq '.tools | keys'

# 🧭 Safe workflow (recommended AI entry)
python3 cleanmac.py --json workflow --categories trash,downloads --dry-run-scope selected

# 🛡️ AI governance release gate
make ai-governance-smoke

# 🛡️ Sandbox execution
python3 cleanmac.py --root /tmp/sandbox --home /Users/tester clean run --categories trash --execute
```

> 🛡️ **Safety principle:** Nothing deleted by default. `clean run` is always a dry-run; only explicit `--execute` triggers deletion. High-risk categories require `--yes`. Live root `/` requires `--allow-live-root`.

---

## ✨ Highlights

| 🏷️ | Description |
|---|---|
| 🧹 **Dry-run first** | All cleanup commands preview only, no files deleted |
| 🤖 **AI-native · 33 tools** | Full tool definitions in Anthropic / OpenAI / MCP formats |
| 🏗️ **MCP Server** | Built-in Model Context Protocol stdio server |
| 🔐 **Multi-layer safety** | Bundle protection, budgets, Trash recovery, confirmation tokens |
| 🧾 **Review-to-execution contract** | `review` selections can constrain plan replay via `--review-selection-file` |
| 🛡️ **AI governance gates** | Machine-readable LLM policy, release smoke, anti-pattern checks |
| 🧪 **Sandbox mode** | `--root` / `--home` path remapping for safe testing |
| 📦 **Zero deps** | Pure Python 3.10+, no external packages required |

---

## 📖 Documentation

| Guide | Link |
|---|---|
| 📗 **English** — full CLI reference, safety model, AI/MCP patterns, development | [docs/doc/README.md](docs/doc/README.md) |
| 📕 **中文** — 完整命令参考、安全模型、AI/MCP 调用姿势、开发验证 | [docs/doc/README.CN.md](docs/doc/README.CN.md) |

---

## 🧩 Quick Index

- [🤖 AI Invocation Patterns](docs/doc/README.md#-ai-invocation-patterns)
- [🏗️ MCP Server Setup](docs/doc/README.md#️-mcp-server)
- [🛡️ Safety Model](docs/doc/README.md#-safety-model)
- [📦 Installation](docs/doc/README.md#-installation)
- [✅ Development & CI](docs/doc/README.md#-development--ci)
- [📕 中文 AI 调用姿势](docs/doc/README.CN.md#-ai-调用姿势)
- [📕 中文 MCP 服务器配置](docs/doc/README.CN.md#-mcp-服务器)

---

## 💻 Installation

```bash
# ▶️ Run directly
python3 cleanmac.py clean list

# 🍺 Install via Homebrew tap
brew tap cleanmac/tap
brew install cleanmac
cleanmac --json capabilities

# 📥 Install as package
python3 -m pip install -e .
cleanmac list
```

> Requires Python 3.10+

---

## 🔗 Links

- [📗 Full English Guide](docs/doc/README.md)
- [📕 中文文档](docs/doc/README.CN.md)
- [🐛 Issues](https://github.com/cleanmac/cleanmac/issues)
- [🔒 Security Policy](SECURITY.md)
