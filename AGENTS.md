# cleanmac Agent Guide

本文件是维护者和 AI Agent 修改 cleanmac 时的共享操作规约。cleanmac 是 AI-first、一次性运行的 Python CLI，不实现 TUI/GUI，不安装后台 daemon、菜单栏常驻进程、登录项或主动扫描循环。任何改动都必须优先保持机器可读治理模型、dry-run 默认值、no-auth 测试默认值和真实执行安全，不要照搬外部 shell 项目或 GUI 清理 App 的结构。

## 产品定位红线

- cleanmac 只在用户、脚本或 AI Host 显式调用时运行，完成当前 workflow 后退出生命周期。
- 不允许新增常驻 GUI/TUI、menu bar app、LaunchAgent/LaunchDaemon、login item、后台扫描、后台提醒或自动清理循环。
- 不允许把用户选择状态保存在长期运行的 App session 中；必须使用机器可读 plan、review-selection、report 和 operation log。
- AI Host / CLI 是交互层，cleanmac 是受治理执行内核；新增能力必须优先暴露稳定 JSON/schema/MCP/argv 合约。
- 未被调用时，cleanmac 的后台 CPU、内存和进程占用目标必须为 0。

## 项目地图

- `cleanmac.py`：命令行入口，仅负责把执行交给 `cleancli.main`。
- `cleancli/core.py`：当前主编排层，注册 CLI 参数、清理分类、候选发现、报告输出、计划 replay、operation log 和 grouped command 兼容逻辑。这里可以编排，但不能拥有真实删除 primitive。
- `cleancli/delete_ops.py`：唯一真实删除出口，负责 path validation、Trash 路由、永久删除、test/no-auth 命令阻断。
- `cleancli/protection_data.py`：保护策略纯数据，包含 bundle blocklist、系统路径、敏感用户数据片段、官方卸载器和 app cleanup 规则。不要在这里写逻辑。
- `cleancli/protection.py`：保护策略逻辑，包含 bundle/container/group-container 判断、敏感数据保护、官方卸载器 vendor 匹配、protected descendant 检查。
- `cleancli/scripts.py` / `cleancli/governance.py`：脚本模板、自动化边界、命令模板安全验证和 governance 报告。
- `cleancli/workflow.py`：固定安全工作流和 automation playbook，不允许把破坏性清理塞进 workflow 默认路径。
- `cleancli/software.py`：软件 inventory、startup item、leftover 和 uninstall-plan 相关能力。
- `cleancli/analyze.py`、`cleancli/status.py`、`cleancli/optimize.py`、`cleancli/finder.py`：只读分析、状态、维护计划和 Finder preview 能力。
- `scripts/test.sh`：默认本地测试入口，设置 no-auth/test-mode，并 stub `sudo`、`osascript`、`launchctl`、`rm`。
- `tests/`：事故驱动回归测试，覆盖 delete safety、path safety、Trash fail-closed、sudo guard、Group Containers、operation log、script governance、app protection。
- `tests/data/dangerous_paths.txt`：高风险路径测试数据，新增危险路径时必须追加并保持测试通过。
- `scripts/cleanmac_mcp_server.py`：MCP stdio server entry point（JSON-RPC 2.0）
- `cleancli/ai_schema.py`：AI 工具定义、schema 校验、三种 provider 格式导出
- `cleancli/ai_readiness.py`：AI readiness 检查
- `cleancli/ai_runbook.py`：AI runbook / invocation patterns
- `cleancli/ai_decision.py`：AI 工具决策矩阵
- `cleancli/ai_governance.py`：AI 治理建议与路线验证
- `cleancli/ai_host_policy.py`：AI 主机允许/拒绝策略
- `cleancli/ai_eval.py`：AI 评估场景编排与 runner
- `cleancli/review.py`：把 plan/report/startup/privacy/tool/software 输出归一化为 `cleanmac.review.v1`，生成和校验 `cleanmac.review-selection.v1`，为执行前 selection handoff 提供 source fingerprint。
- `tests/test_ai_readiness.py`、`tests/test_ai_runbook.py`、`tests/test_ai_self_test.py`、
  `tests/test_ai_decision_matrix.py`、`tests/test_ai_governance.py`、`tests/test_ai_eval.py`、
  `tests/test_ai_host_scenarios.py`、`tests/test_mcp_server.py`：AI/MCP 专项测试
- `.github/workflows/ci.yml`：真实 CI，包含 quality、smoke、macOS smoke、security/gitleaks、no-cache、Linux container smoke、MCP smoke、AI governance smoke、AI host smoke。
- `.github/workflows/release.yml`：release 构建、`SHA256SUMS`、artifact attestation、wheel 安装验证、PyPI trusted publishing。

## 常用命令

```bash
python3 cleanmac.py --json capabilities
python3 cleanmac.py --json clean inspect --categories trash
python3 cleanmac.py --json plan --categories trash --max-items 10
python3 cleanmac.py --json validate-plan --plan-file /tmp/cleanmac-plan.json
python3 cleanmac.py --json workflow --categories trash,mails,xcode --dry-run-scope selected
```

验证命令：

```bash
python3 -m unittest -v
make pytest-test
make quality-check
make local-test
make package-smoke
make script-smoke
make docs-smoke
make governance-smoke
make ai-governance-smoke
make open-source-smoke
make mcp-smoke
make ai-host-smoke
make distribution-smoke
make release-artifacts-smoke
make docker-test
```

pytest 验证必须使用 `make pytest-test`，该目标会创建临时 venv、安装 test extra，并在 venv 中运行 pytest；不要直接依赖全局 pytest。如果全局环境缺少 `mypy`、`ruff`、`build` 或 `twine`，使用临时 venv 验证，不要把虚拟环境写入仓库：

```bash
tmpdir=$(mktemp -d)
python3 -m venv "$tmpdir/venv"
"$tmpdir/venv/bin/python" -m pip install --upgrade pip
"$tmpdir/venv/bin/python" -m pip install -e '.[dev,build]'
"$tmpdir/venv/bin/python" -m ruff format --check .
"$tmpdir/venv/bin/python" -m ruff check .
"$tmpdir/venv/bin/python" -m mypy cleanmac.py cleancli test_cleanmac.py tests
"$tmpdir/venv/bin/python" -m pytest -q
rm -R "$tmpdir"
```

## 关键安全规则

- 默认必须是 dry-run。真实删除必须同时满足用户显式选择 `clean`、传入 `--execute`，且高风险分类按 policy 需要 `--yes` 时必须提供确认。
- 所有真实删除、递归删除、Trash 路由、覆盖旧 symlink/file 的动作都必须走 `cleancli/delete_ops.py`。
- 不允许在 `cleancli/core.py` 或其他业务模块中新增 `shutil.rmtree(...)`、`shutil.move(...)`、`.unlink(...)` 作为清理删除路径。
- 不允许业务逻辑直接通过 `subprocess` 调用 `rm`、`sudo rm`、Finder 删除或 AppleScript 删除。
- `cleancli/delete_ops.py` 是唯一可以拥有低层删除 primitive 的模块；调用者只能传入 `DeletePolicy` 和候选路径。
- 测试和普通验证必须使用 no-auth/test-mode：`CLEANMAC_TEST_MODE=1`、`CLEANMAC_TEST_NO_AUTH=1`。
- 测试或 no-auth 模式下，`sudo`、`osascript`、`launchctl` 必须被阻断或 stub；新增直接调用必须有 test-mode guard 和测试覆盖。
- Trash 模式必须 fail-closed：Trash 目录是 symlink、不可创建、不可写或移动失败时，不能 fallback 到永久删除。
- 计划 replay 使用 `--require-plan-context` 时必须校验 root/home，一旦不一致必须在删除前失败。
- operation log 写入失败不能伪装成功；执行报告必须暴露失败状态，避免用户误以为已经安全记录。
- 脚本模板和 workflow 只能生成/展示命令，不能自动执行破坏性模板；`safe_to_auto_execute` 对 destructive template 必须为 false。

## AI & MCP 安全规则
- MCP server（`scripts/cleanmac_mcp_server.py`）不接受 shell/raw command 输入；所有工具调用必须走 argv_template
- 破坏性工具（`cleanmac_execute_plan`、`cleanmac_startup_disable`、`cleanmac_privacy_execute`）必须同时 deny auto_call 且 require confirmation
- 确认令牌是 SHA-256 绑定的上下文令牌，不匹配时拒绝执行
- MCP resources 不能暴露敏感路径或凭证信息
- 修改 MCP server 后必须运行 `make mcp-smoke` 和 `make ai-host-smoke`
- AI 工具定义修改后必须运行 `python3 cleanmac.py --json ai-tools` 验证 provider 导出 parity
- `review` 选择文件只能作为约束输入；`--review-selection-file` 必须搭配 `--plan-file`，校验 source fingerprint 后才允许进入 dry-run / execute 路径，失败必须映射为 `SELECTION_VALIDATION_FAILED`。
- AI/MCP 的 `cleanmac_dry_run_plan`、`cleanmac_execute_plan`、`cleanmac_policy_simulate`、`cleanmac_startup_disable`、`cleanmac_privacy_execute` 如暴露 `review_selection_file`，argv_template 必须保留对应执行门禁，不能绕过 review selection 校验。Clean 执行路径还必须保留 `--require-plan-context`、Trash 路由和确认令牌门禁。

## 高风险模块所有权与必跑测试

### `cleancli/delete_ops.py`

职责：唯一删除出口、路径校验、symlink 防护、Trash 路由、test-mode 命令阻断。

修改后必须运行：

```bash
python3 -m unittest test_cleanmac.CleanMacCLITests.test_real_delete_primitives_are_owned_by_delete_ops -v
python3 -m unittest test_cleanmac.CleanMacCLITests.test_delete_safety_rejects_malformed_and_protected_paths -v
python3 -m unittest test_cleanmac.CleanMacCLITests.test_delete_safety_rejects_symlink_to_protected_path -v
python3 -m unittest test_cleanmac.CleanMacCLITests.test_trash_delete_mode_fails_closed_when_trash_root_is_symlink -v
python3 -m unittest tests.test_delete_ops tests.test_path_safety tests.test_trash_mode -v
make docker-test
```

### `cleancli/protection_data.py` 和 `cleancli/protection.py`

职责：bundle blocklist/allowlist、Apple container 和 Group Container 保护、敏感用户数据保护、官方卸载器规则、protected descendant 检查。

修改后必须运行：

```bash
python3 -m unittest test_cleanmac.CleanMacCLITests.test_protection_data_is_centralized_outside_core -v
python3 -m unittest test_cleanmac.CleanMacCLITests.test_expanded_app_cleanup_rules_preserve_user_data_and_credentials -v
python3 -m unittest test_cleanmac.CleanMacCLITests.test_group_container_policy_skips_apple_and_allows_non_protected_cache -v
python3 -m unittest tests.test_group_containers tests.test_app_protection -v
```

### `cleancli/core.py` clean execution

职责：分类选择、候选过滤、budget/max-items、plan replay、review-selection constraint、execute 前置检查、operation log 汇总。

修改后必须运行：

```bash
python3 -m unittest test_cleanmac.CleanMacCLITests.test_clean_defaults_to_dry_run -v
python3 -m unittest test_cleanmac.CleanMacCLITests.test_clean_max_delete_budget_blocks_execute_before_deleting -v
python3 -m unittest test_cleanmac.CleanMacCLITests.test_clean_max_items_blocks_execute_before_deleting -v
python3 -m unittest test_cleanmac.CleanMacCLITests.test_require_plan_context_rejects_root_mismatch -v
python3 -m unittest test_cleanmac.CleanMacCLITests.test_require_plan_context_rejects_home_mismatch -v
python3 -m unittest test_cleanmac.CleanMacCLITests.test_clean_plan_dry_run_can_be_constrained_by_review_selection -v
python3 -m unittest test_cleanmac.CleanMacCLITests.test_clean_review_selection_file_must_match_plan_fingerprint -v
python3 -m unittest test_cleanmac.CleanMacCLITests.test_policy_simulate_includes_review_selection_in_safe_argv -v
python3 -m unittest tests.test_operation_log -v
make local-test
```

### `cleancli/scripts.py`、`cleancli/governance.py`、`cleancli/workflow.py`

职责：脚本模板 inventory、template validation、automation playbook、workflow 安全边界。

修改后必须运行：

```bash
python3 -m unittest test_cleanmac.CleanMacCLITests.test_command_template_validation_reports_policy_violations -v
python3 -m unittest test_cleanmac.CleanMacCLITests.test_scripts_reports_current_command_templates -v
python3 -m unittest test_cleanmac.CleanMacCLITests.test_workflow_runs_fixed_non_destructive_phases -v
python3 -m unittest tests.test_script_governance -v
make script-smoke
make governance-smoke
```

### package、CI、release 与供应链

职责：`pyproject.toml`、`.github/workflows/*`、`.gitleaks.toml`、README/CONTRIBUTING/SECURITY、release artifact 证明。

- `cleancli/release_artifacts.py` and `scripts/generate_release_manifest.py` own release manifest generation; do not duplicate checksum/manifest logic in workflow YAML or Makefile one-liners.

修改后必须运行：

```bash
python3 -m unittest test_cleanmac.CleanMacCLITests.test_python_quality_tooling_is_configured -v
python3 -m unittest test_cleanmac.CleanMacCLITests.test_open_source_governance_files_are_configured -v
python3 -m unittest test_cleanmac.CleanMacCLITests.test_release_workflow_generates_checksums_attestation_and_pypi_publish -v
make open-source-smoke
make release-artifacts-smoke
```

### AI schema / governance / eval

职责：AI 工具定义、provider 格式导出、确认令牌、治理路线、主机策略、评估场景。

修改后必须运行：

```bash
python3 -m unittest tests.test_ai_governance tests.test_ai_readiness tests.test_ai_runbook -v
python3 -m unittest tests.test_ai_self_test tests.test_ai_decision_matrix tests.test_ai_eval -v
python3 -m unittest tests.test_ai_host_scenarios tests.test_mcp_server -v
python3 -m unittest test_cleanmac.CleanMacCLITests.test_ai_tools_exports_provider_specific_tool_formats -v
python3 -m unittest test_cleanmac.CleanMacCLITests.test_ai_schema_builds_safe_argv_without_shell_or_implicit_execute -v
make mcp-smoke
make ai-host-smoke
make ai-governance-smoke
```

## 高风险路径回归规则

- 新增清理分类时必须考虑 `/`、`/System`、`/Library`、`/private`、`~/Library/Mail`、`~/Library/Messages`、Keychains、CloudDocs、Group Containers、应用 Containers。
- 新增事故路径必须追加到 `tests/data/dangerous_paths.txt`，并保持以下测试通过：

```bash
python3 -m unittest test_cleanmac.CleanMacCLITests.test_path_safety_rejects_dangerous_path_data -v
python3 -m unittest test_cleanmac.CleanMacCLITests.test_delete_safety_rejects_malformed_and_protected_paths -v
```

## 历史事故和踩坑案例

- **Symlink 指向系统路径**：候选位于 sandbox 内不代表安全。必须 resolve symlink 并按 policy path 检查目标；指向 `/System`、`/Library`、Keychains 等保护路径时拒绝删除。
- **Group Container wildcard**：不要使用 TeamID 前缀或宽泛 wildcard 去匹配 Group Containers。`group.com.apple.*`、Safari extension、受保护 bundle 的 container/cache 必须默认跳过。
- **Trash fail-closed**：Trash 目录为 symlink、不可用或移动失败时，必须失败并保留原文件，不能改走永久删除。
- **sudo prompt / AppleScript prompt**：测试不能触发真实 `sudo`、Touch ID、密码框、`osascript` 授权弹窗或 `launchctl` 系统服务变更。默认通过 `scripts/test.sh` 或 no-auth 环境验证。
- **Plan replay root/home 不一致**：plan 文件来自另一个 root/home 时，`--require-plan-context` 必须在执行前拒绝，避免把旧计划应用到真实用户目录或错误 sandbox。
- **Operation log 不可写**：执行模式下日志不可写、目录不可创建或轮转失败不能静默吞掉。报告必须让调用者看到失败，避免审计链断裂。
- **Shell template unsafe auto execution**：`clean scripts` 可以展示破坏性 shell 模板，但必须标记为 destructive、manual review required，并禁止自动执行。
- **测试依赖缺失**：全局 Python 经常缺少 `mypy` 或 `pytest`。遇到缺失时创建临时 venv 安装 `.[dev,build]`，不要降低验证标准。
- **文档示例也会被安全扫描**：README/AGENTS/CI 中出现危险命令文本会触发 unsafe grep。示例应使用 `mktemp -d` sandbox 和安全清理方式，避免教用户复制危险命令。
- **默认 bundle blocklist 文档漂移**：不要把默认保护列表写成只有 `com.apple.mail,com.apple.MobileSMS`。完整列表以 `capabilities.safety_guardrails.default_protected_bundle_ids` 为准。

## 最低交付标准

- 任何改动至少运行与 touched file 对应的 targeted unittest。
- 触碰安全、删除、保护、CI、release、脚本模板时，必须额外运行 `make local-test` 或对应 smoke。
- 发布前或大范围改动后运行临时 venv 的 lint/type/pytest，加上 `make docker-test`。
- 不要因为本机缺少依赖就跳过验证；先用临时 venv 补齐依赖，再记录实际结果。
