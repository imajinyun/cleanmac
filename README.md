# 🧹 cleanmac

> **macOS cleanup tool · Dry-run first · AI-native MCP integration**

- [📗 English Docs](/docs/doc/README.md)
- [📕 中文文档](/docs/doc/README.CN.md)

---

## 🚀 TL;DR

```bash
# 🧪 Safe preview
python3 cleanmac.py --json clean inspect --categories trash,mails,xcode --limit 10

# 🧩 Productized safe profile for regular users
python3 cleanmac.py --json profiles
python3 cleanmac.py --json clean plan --profile safe --ai-origin

# 🗑️ Reviewed software uninstall closed loop
python3 cleanmac.py --json software inspect --app "Example"
python3 cleanmac.py --json software uninstall-plan --app "Example"

# 🤖 AI tool definitions (36 tools)
python3 cleanmac.py --json ai-tools --format anthropic | jq '.tools | keys'

# 🧭 Safe workflow (recommended AI entry)
python3 cleanmac.py --json workflow --categories trash,downloads --dry-run-scope selected

# 🗂️ Governed MCP entrypoint (meta → resource/prompt/tool)
python3 cleanmac.py --json ai-host-integration-pack | jq '.recommended_call_sequence'

# 🛡️ AI governance release gate
make ai-governance-smoke

# 🛡️ Sandbox execution
python3 cleanmac.py --root /tmp/sandbox --home /Users/tester clean run --categories trash --execute
```

> 🛡️ **Safety principle:** Nothing deleted by default. `clean run` is always a dry-run; only explicit `--execute` triggers deletion. High-risk categories require `--yes`. Live root `/` requires `--allow-live-root`.

---

## 🥇 Why cleanmac exists

cleanmac aims to be the safest, most governable CLI macOS cleaner on GitHub for users who want more than a risky recursive `rm` script.

- **Safer than ad-hoc shell scripts**: dry-run by default, deletion budgets, protected bundle rules, Trash-only governed execution, operation log audit chain.
- **More reviewable than one-shot cleaners**: inspect → plan → review → selection → dry-run → execute is explicit and machine-readable.
- **More AI/MCP ready than traditional cleaners**: tool contracts, schema registry, host policy, release readiness, and smoke gates are first-class outputs.

---

## ⚡ Three-minute safe cleanup flow

```bash
# 1) Discover the safest built-in profile
python3 cleanmac.py --json profiles

# 2) Generate a conservative plan
python3 cleanmac.py --json clean plan --profile safe --ai-origin > /tmp/cleanmac-plan.json

# 3) Review and narrow the selection before any execution
python3 cleanmac.py --json review --input-file /tmp/cleanmac-plan.json --selection-file /tmp/cleanmac-selection.json

# 4) Dry-run the reviewed selection
python3 cleanmac.py --json clean run --plan-file /tmp/cleanmac-plan.json --review-selection-file /tmp/cleanmac-selection.json --require-plan-context --delete-mode trash
```

If you later choose to execute, cleanmac keeps Trash routing, review-selection constraints, and operation-log recording instead of jumping straight to destructive deletion.

---

## 🛡️ Why this is safer than `rm` scripts

`rm` scripts typically trust string matching and shell expansion. cleanmac adds explicit guardrails:

- protected Apple apps, sensitive user data, Containers, and Group Containers are blocked by policy
- governed execution requires an explicit reviewed selection file instead of “delete everything matched”
- live destructive runs still go through Trash routing and auditable operation-log entries
- AI/MCP destructive tools are deny-by-default for auto-call and require confirmation contracts

---

## 🆚 How cleanmac differs from Pearcleaner / CleanMyMac / mac-cleanup-py

- **Pearcleaner**: strong app-centric UX, but cleanmac focuses on CLI-first governance, machine-readable review handoff, and AI/MCP-safe orchestration.
- **CleanMyMac**: polished commercial experience, but cleanmac emphasizes auditable contracts, open release evidence, and no hidden background heuristics.
- **mac-cleanup-py / shell cleanup scripts**: useful automation building blocks, but cleanmac adds policy gates, protected bundle logic, reviewed execution, and release-readiness evidence.

---

## ✨ Highlights

| 🏷️ | Description |
|---|---|
| 🧹 **Dry-run first** | All cleanup commands preview only, no files deleted |
| 🤖 **AI-native · 36 tools** | Full tool definitions in Anthropic / OpenAI / MCP formats |
| 🏗️ **MCP Server** | Built-in Model Context Protocol stdio server |
| 🗂️ **Governed MCP indexes** | Meta index leads hosts to resource, prompt, and tool catalogs |
| 🔐 **Multi-layer safety** | Bundle protection, budgets, Trash recovery, confirmation tokens |
| 🧾 **Review-to-execution contract** | `review` selections can constrain clean, startup, and privacy execution via `--review-selection-file` |
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
brew trust cleanmac/tap
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
