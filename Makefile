.PHONY: format lint type-check coverage quality-check local-test pytest-test build-check package-smoke script-smoke bundle-audit-smoke macos-smoke real-macos-smoke security-smoke dependency-audit-smoke docs-smoke governance-smoke ai-governance-smoke ai-contract-smoke governed-execution-smoke open-source-smoke mcp-smoke ai-host-smoke ai-robustness-smoke distribution-smoke homebrew-formula-smoke release-artifacts-smoke release-readiness-smoke no-cache-check docker-test no-cache-docker-test release-check no-cache-release-check

DOCKER_IMAGE ?= debian:bookworm-slim
SANDBOX_MOUNT ?= $(abspath ..)
WORKDIR ?= /work/cleanmac
PYTHON ?= python3
DOCKER_RUN_FLAGS ?=

format:
	$(PYTHON) -m ruff format .
	$(PYTHON) -m ruff check --fix .

lint:
	$(PYTHON) -m ruff format --check .
	$(PYTHON) -m ruff check .

type-check:
	$(PYTHON) -m mypy

coverage:
	$(PYTHON) -m coverage run -m unittest -v
	$(PYTHON) -m coverage report

quality-check: lint type-check coverage

local-test:
	PYTHON=$(PYTHON) ./scripts/test.sh

pytest-test:
	tmpdir=$$(mktemp -d); \
	trap 'rm -rf "$$tmpdir"' EXIT; \
	$(PYTHON) -m venv "$$tmpdir/venv"; \
	"$$tmpdir/venv/bin/python" -m pip install --upgrade pip; \
	"$$tmpdir/venv/bin/python" -m pip install -e '.[test]'; \
	PYTHONDONTWRITEBYTECODE=1 PYTEST_ADDOPTS="-p no:cacheprovider" "$$tmpdir/venv/bin/python" -m pytest --cov=cleancli --cov=cleanmac --cov-report=term-missing -q

build-check:
	tmpdir=$$(mktemp -d); \
	trap 'rm -rf "$$tmpdir"' EXIT; \
	$(PYTHON) -m build --wheel --sdist --outdir "$$tmpdir/dist"; \
	$(PYTHON) -m twine check "$$tmpdir"/dist/*

package-smoke:
	tmpdir=$$(mktemp -d); \
	trap 'rm -rf "$$tmpdir"' EXIT; \
	$(PYTHON) -m venv "$$tmpdir/venv"; \
	"$$tmpdir/venv/bin/python" -m pip install -e .; \
	"$$tmpdir/venv/bin/cleanmac" --json capabilities >"$$tmpdir/capabilities.json"; \
	"$$tmpdir/venv/bin/python" -m json.tool "$$tmpdir/capabilities.json" >/dev/null

script-smoke:
	$(PYTHON) -c 'import json, subprocess, sys; report=json.loads(subprocess.check_output([sys.executable, "cleanmac.py", "--json", "clean", "scripts", "--categories", "trash,systemLogs"], text=True)); validation=report["template_validation"]; assert report["schema"] == "cleanmac.scripts.v1"; assert validation["schema"] == "cleanmac.command-template-validation.v1"; assert validation["valid"], validation["violations"]; assert validation["template_count"] > 0; assert validation["destructive_template_count"] > 0; assert validation["violation_count"] == 0'

bundle-audit-smoke:
	$(PYTHON) -m unittest tests.test_bundle_audit -v

macos-smoke:
	CLEANMAC_TEST_MODE=1 CLEANMAC_TEST_NO_AUTH=1 $(PYTHON) -m unittest \
		test_cleanmac.CleanMacCLITests.test_grouped_analyze_tree_reports_largest_entries \
		test_cleanmac.CleanMacCLITests.test_clean_trash_delete_mode_routes_candidates_to_recoverable_trash \
		test_cleanmac.CleanMacCLITests.test_software_uninstall_plan_routes_official_uninstallers \
		test_cleanmac.CleanMacCLITests.test_clean_execute_uses_default_operation_log_under_remapped_home \
		test_cleanmac.CleanMacCLITests.test_test_mode_blocks_privileged_and_automation_helpers \
		test_cleanmac.CleanMacCLITests.test_path_safety_rejects_dangerous_path_data \
		test_cleanmac.CleanMacCLITests.test_trash_delete_mode_fails_closed_when_trash_root_is_symlink \
		tests.test_bundle_audit tests.test_sudo_guard -v

real-macos-smoke:
	$(PYTHON) -m unittest tests.test_macos_real_smoke -v

security-smoke:
	$(PYTHON) scripts/security_scan.py

dependency-audit-smoke:
	tmpdir=$$(mktemp -d); \
	trap 'rm -rf "$$tmpdir"' EXIT; \
	$(PYTHON) -m pip_audit --skip-editable --progress-spinner off; \
	$(PYTHON) scripts/generate_sbom.py --output "$$tmpdir/SBOM.json"; \
	$(PYTHON) -c 'import json, pathlib, sys; sbom=json.loads(pathlib.Path(sys.argv[1]).read_text(encoding="utf-8")); assert sbom["bomFormat"] == "CycloneDX"; assert sbom["metadata"]["component"]["name"] == "cleanmac"; assert isinstance(sbom["components"], list)' "$$tmpdir/SBOM.json"

docs-smoke:
	$(PYTHON) -c 'from pathlib import Path; required=("make docs-smoke", "make governance-smoke", "make ai-governance-smoke", "make ai-contract-smoke", "make ai-robustness-smoke", "make release-readiness-smoke", "make open-source-smoke", "make dependency-audit-smoke", "make homebrew-formula-smoke", "make no-cache-check", "make no-cache-release-check", "--bundle-allowlist", "--bundle-blocklist", "--delete-mode permanent", "--operation-log", "cleanmac.operation-log-entry.v1", "~/.cleanmac/operations.jsonl", "~/.cleanmac/deletions.log", "cleanmac_debug_session.log", "CLEANMAC_TEST_NO_AUTH", "SBOM.json", "ARTIFACT-MANIFEST.json", "cleanmac.rb", "brew tap cleanmac/tap", "brew install cleanmac", "cleanmac.release-artifact-manifest.v1", "scripts/generate_release_manifest.py", "scripts/generate_homebrew_formula.py", "pip-audit", "official_uninstaller_vendor", "groupContainerCaches", "androidStudio", "jetbrains", "vscode", "docker", "chrome", "firefox", "slack", "zoom", "teams", "nodePackageCaches", "pythonPackageCaches", "goBuildCaches", "rotate_log_once", "deviceFirmware", "appleSiliconCaches"); local_developer_path="/" + "Users" + "/" + "bytedance"; texts={path: Path(path).read_text(encoding="utf-8") for path in ("docs/doc/README.md", "docs/doc/README.CN.md")}; [(_ for _ in ()).throw(AssertionError(f"{path} missing {token}")) for path, text in texts.items() for token in required if token not in text]; [(_ for _ in ()).throw(AssertionError(f"{path} contains local developer path")) for path, text in texts.items() if local_developer_path in text]; makefile=Path("Makefile").read_text(encoding="utf-8"); release_line=next(line for line in makefile.splitlines() if line.startswith("release-check:")); [(_ for _ in ()).throw(AssertionError(f"{path} missing release target {target}")) for path, text in texts.items() for target in release_line.removeprefix("release-check:").split() if f"`{target}`" not in text and target not in text]'

governance-smoke:
	$(PYTHON) -c 'import json, subprocess, sys; run=lambda *args: json.loads(subprocess.check_output([sys.executable, "cleanmac.py", "--json", *args], text=True)); cap=run("capabilities"); guard=cap["safety_guardrails"]; boundary=cap["boundary_governance"]; scripts=run("clean", "scripts", "--categories", "trash,systemLogs"); workflow=run("workflow", "--categories", "trash,mails,xcode", "--dry-run-scope", "selected"); required=workflow["automation_playbook"]["test_acceptance"]["required_commands"]; analyze_tree=run("analyze", "tree", "--path", ".", "--depth", "1", "--top", "3"); permissions=run("permissions", "--categories", "trash,systemLogs"); tool_plan=run("tool-plan", "--tool", "docker"); software=run("software", "uninstall-plan", "--app", "Falcon"); app_categories=set(guard["app_specific_cleanup_categories"]); assert cap["schema"] == "cleanmac.capabilities.v1"; assert guard["dry_run_default"] and guard["delete_requires_execute"]; assert guard["trash_routing_flag"] == "clean --delete-mode trash"; assert guard["operation_log_flag"] == "clean --operation-log"; assert guard["permissions_preflight_command"] == "permissions"; assert guard["tool_semantic_plan_command"] == "tool-plan"; assert permissions["schema"] == "cleanmac.permissions-preflight.v1" and not permissions["destructive"] and permissions["dry_run"]; assert tool_plan["schema"] == "cleanmac.tool-plan.v1" and not tool_plan["destructive"] and not tool_plan["safe_to_auto_execute"]; assert not any(adapter["auto_execute_allowed"] for adapter in tool_plan["adapters"]); assert guard["default_operation_log_file"] == "~/.cleanmac/operations.jsonl"; assert guard["bundle_drift_audit"]["schema"] == "cleanmac.bundle-drift-audit.v1"; assert guard["privileged_command_ownership"]["scan_command"] == "python3 scripts/security_scan.py"; assert guard["default_protected_bundle_count"] >= 40; assert "CrowdStrike" in guard["official_uninstaller_vendors"]; assert guard["group_container_policy"]["category"] == "groupContainerCaches"; assert "androidStudio" in app_categories and "docker" in app_categories; assert {"chrome", "firefox", "slack", "zoom", "teams", "nodePackageCaches", "pythonPackageCaches", "goBuildCaches"}.issubset(app_categories); assert "chrome" in guard["active_process_skip_categories"] and "slack" in guard["active_process_skip_categories"]; assert "CLEANMAC_TEST_NO_AUTH" in guard["test_mode_environment"]["no_auth"]; assert guard["log_rotation"]["rotation_function"] == "rotate_log_once"; assert guard["log_rotation"]["log_rotate_bytes"] == 1048576; assert guard["log_rotation"]["operations_log_rotate_bytes"] == 5242880; assert "deviceFirmware" in guard["deep_system_cleanup_categories"] and "appleSiliconCaches" in guard["deep_system_cleanup_categories"]; assert software["uninstall_plan"]["official_uninstaller_vendor"] == "CrowdStrike"; assert not boundary["script_template_policy"]["auto_execute_allowed"]; assert boundary["script_template_policy"]["recommended_delete_templates_use_cleanmac_cli"]; assert boundary["verification"]["python_test_environment"]["requires_virtualenv"]; assert workflow["automation_playbook"]["test_acceptance"]["environment"]["workflow_python_env"] == "PYTHON=.venv/bin/python"; assert scripts["template_validation"]["valid"], scripts["template_validation"]["violations"]; assert not workflow["automation_playbook"]["destructive_cleanup_allowed"]; assert "make governance-smoke" in required and "make open-source-smoke" in required and "make macos-smoke" in required and "make security-smoke" in required and "make bundle-audit-smoke" in required; assert analyze_tree["schema"] == "cleanmac.analyze-tree.v1" and not analyze_tree["destructive"]'

ai-governance-smoke:
	CLEANMAC_TEST_MODE=1 CLEANMAC_TEST_NO_AUTH=1 $(PYTHON) -c 'import json, subprocess, sys; run=lambda *args: json.loads(subprocess.check_output([sys.executable, "cleanmac.py", "--json", *args], text=True)); advice=run("ai-governance-advice"); assert advice["schema"] == "cleanmac.ai-governance-advice.v1"; assert advice["ready_for_llm_calling"], advice; assert advice["governance_score"]["level"] == "strong"; route={row["id"]: row for row in advice["governance_route"]}; required={"entrypoint-governance", "dry-run-first-default", "destructive-auto-call-deny", "execution-preflight-gate", "prompt-injection-boundary", "structured-error-recovery", "mcp-host-governance", "ci-release-gate", "audit-traceability", "anti-pattern-policy"}; assert required.issubset(route), route; assert all(row["status"] == "satisfied" for row in route.values()), route; assert advice["recommended_call_sequence"][0] == "read cleanmac://ai/host-integration-pack"; assert advice["recommended_call_sequence"][1] == "read cleanmac://ai/host-preflight"; assert advice["recommended_call_sequence"][2] == "read cleanmac://ai/host-evidence"; assert ["cleanmac", "--json", "ai-host-integration-pack"] in advice["release_gate_commands"]; assert ["cleanmac", "--json", "ai-host-preflight"] in advice["release_gate_commands"]; assert ["cleanmac", "--json", "ai-host-evidence"] in advice["release_gate_commands"]; assert ["make", "ai-governance-smoke"] in advice["release_gate_commands"]; assert ["make", "ai-contract-smoke"] in advice["release_gate_commands"]; assert ["make", "ai-host-smoke"] in advice["release_gate_commands"]; assert ["make", "mcp-smoke"] in advice["release_gate_commands"]; assert "cleanmac_execute_plan" in advice["default_policy"]["auto_call_denied_tools"]; eval_run=run("ai-eval-run", "--scenario", "mcp_resource_prompt_surface"); assert eval_run["passed"], eval_run; assert eval_run["passed_count"] == 1; assert eval_run["trace"]["event_count"] >= 5; print("ai-governance-smoke passed")'

ai-contract-smoke:
	CLEANMAC_TEST_MODE=1 CLEANMAC_TEST_NO_AUTH=1 $(PYTHON) -c 'import json, subprocess, sys; run=lambda *args: json.loads(subprocess.check_output([sys.executable, "cleanmac.py", "--json", *args], text=True)); samples=run("ai-contract-samples"); summary=run("ai-readiness")["contract_validation"]; self_test=run("ai-self-test"); eval_run=run("ai-eval-run", "--scenario", "contract_samples_roundtrip"); assert samples["schema"] == "cleanmac.ai-contract-samples.v1"; assert samples["sample_count"] == len(samples["samples"]); sample_schemas={sample["target_schema"] for sample in samples["samples"]}; assert "cleanmac.permissions-preflight.v1" in sample_schemas; assert "cleanmac.tool-plan.v1" in sample_schemas; assert "cleanmac.ai-host-integration-pack.v1" in sample_schemas; assert "cleanmac.ai-host-preflight.v1" in sample_schemas; assert "cleanmac.ai-host-evidence.v1" in sample_schemas; assert "cleanmac.ai-host-tool-call-decision.v1" in sample_schemas; assert all(sample["valid"] for sample in samples["samples"]), samples; assert summary["ready"], summary; critical=set(summary["contract_schema_coverage"]["critical_schemas"]); assert "cleanmac.permissions-preflight.v1" in critical; assert "cleanmac.tool-plan.v1" in critical; assert "cleanmac.ai-host-integration-pack.v1" in critical; assert "cleanmac.ai-host-preflight.v1" in critical; assert "cleanmac.ai-host-evidence.v1" in critical; assert "cleanmac.ai-host-tool-call-decision.v1" in critical; assert summary["contract_schema_coverage"]["missing_stable_ai_schema_fragments"] == []; checks={check["id"]: check for check in self_test["checks"]}; assert checks["contract-validation-smoke"]["passed"], checks["contract-validation-smoke"]; assert eval_run["schema"] == "cleanmac.ai-eval-run.v1"; assert eval_run["passed"], eval_run; assert eval_run["passed_count"] == 1; print("ai-contract-smoke passed")'

governed-execution-smoke:
	CLEANMAC_TEST_MODE=1 CLEANMAC_TEST_NO_AUTH=1 $(PYTHON) -m unittest \
		test_cleanmac.CleanMacCLITests.test_startup_and_privacy_plans_expose_current_execution_gate_names \
		test_cleanmac.CleanMacCLITests.test_startup_disable_requires_review_selection_and_records_audit \
		test_cleanmac.CleanMacCLITests.test_startup_disable_creates_backup_before_plist_write \
		test_cleanmac.CleanMacCLITests.test_privacy_execute_requires_review_selection_and_records_audit \
		test_cleanmac.CleanMacCLITests.test_privacy_execute_blocks_outside_symlink_and_credential_candidates \
		test_cleanmac.CleanMacCLITests.test_privacy_execute_requires_selected_item_id_and_path_to_match_same_candidate \
		tests.test_ai_versioning.AISchemaRegistryTests.test_operational_plan_samples_expose_current_execute_gate_name -v

open-source-smoke:
	$(PYTHON) -c 'import re; from pathlib import Path; required=("LICENSE", "CONTRIBUTING.md", "SECURITY.md", "CODE_OF_CONDUCT.md", "AGENTS.md", ".gitleaks.toml", ".github/PULL_REQUEST_TEMPLATE.md", ".github/dependabot.yml", ".github/workflows/ci.yml", ".github/workflows/bundle_audit.yml", ".github/workflows/codeql.yml", ".github/workflows/dependency-review.yml", ".github/workflows/nightly.yml", ".github/workflows/release.yml", ".github/workflows/scorecards.yml", ".github/ISSUE_TEMPLATE/bug_report.yml", ".github/ISSUE_TEMPLATE/feature_request.yml", ".github/ISSUE_TEMPLATE/config.yml", "scripts/generate_sbom.py"); missing=[path for path in required if not Path(path).is_file()]; assert not missing, missing; assert not Path(".github/templates").exists(), "Use GitHub-recognized ISSUE_TEMPLATE and PULL_REQUEST_TEMPLATE locations"; assert not Path(".github/CODEOWNERS").exists(), "Create CODEOWNERS only after real GitHub teams exist"; pyproject=Path("pyproject.toml").read_text(encoding="utf-8"); [(_ for _ in ()).throw(AssertionError(f"pyproject missing {token}")) for token in ("license = \"MIT\"", "license-files = [\"LICENSE\"]", "[project.urls]", "Homepage =", "Repository =", "Issues =", "Security =", "pip-audit>=") if token not in pyproject]; readme=Path("docs/doc/README.md").read_text(encoding="utf-8"); contributing=Path("CONTRIBUTING.md").read_text(encoding="utf-8"); security=Path("SECURITY.md").read_text(encoding="utf-8"); release=Path(".github/workflows/release.yml").read_text(encoding="utf-8"); agents=Path("AGENTS.md").read_text(encoding="utf-8"); ci=Path(".github/workflows/ci.yml").read_text(encoding="utf-8"); dependency_review=Path(".github/workflows/dependency-review.yml").read_text(encoding="utf-8"); nightly=Path(".github/workflows/nightly.yml").read_text(encoding="utf-8"); scorecards=Path(".github/workflows/scorecards.yml").read_text(encoding="utf-8"); gitleaks=Path(".gitleaks.toml").read_text(encoding="utf-8"); assert "make open-source-smoke" in readme; assert "independent Python implementation" in readme; assert "make open-source-smoke" in contributing; assert "path traversal" in security.lower(); assert "README\\.md" not in gitleaks and "README\\.CN" not in gitleaks; assert "CodeQL" in Path(".github/workflows/codeql.yml").read_text(encoding="utf-8"); assert "gitleaks/gitleaks-action" in ci and "No-cache dependency install" in ci and "macOS smoke" in ci and "Linux container smoke" in ci and "dependency-audit-smoke" in ci; assert "actions/dependency-review-action" in dependency_review and "fail-on-severity: high" in dependency_review; assert "make release-check" in nightly and "make no-cache-check" in nightly and "PYTHON: .venv/bin/python" in nightly and "Create venv and install release-check dependencies" in nightly; assert "ossf/scorecard-action" in scorecards and "results_format: sarif" in scorecards and "github/codeql-action/upload-sarif" in scorecards; uses=[line.strip() for workflow in Path(".github/workflows").glob("*.yml") for line in workflow.read_text(encoding="utf-8").splitlines() if line.strip().startswith("uses: ")]; assert uses; [(_ for _ in ()).throw(AssertionError(f"action is not SHA-pinned: {line}")) for line in uses if not re.search(r"@[0-9a-f]{40}(?:\s|$$)", line)]; [(_ for _ in ()).throw(AssertionError(f"release workflow missing {token}")) for token in ("id-token: write", "attest-build-provenance", "pypa/gh-action-pypi-publish", "SHA256SUMS", "SBOM.json") if token not in release]; [(_ for _ in ()).throw(AssertionError(f"AGENTS.md missing {token}")) for token in ("delete_ops", "CLEANMAC_TEST_NO_AUTH", "launchctl", "tests/data/dangerous_paths.txt", "make docker-test") if token not in agents]; forbidden=("mo" + "le", "MO" + "LE", "github/" + "mo" + "le"); ignored={".git", "build", "dist", "cleanmac.egg-info", "__pycache__", ".mypy_cache", ".pytest_cache", ".ruff_cache", ".venv"}; scanned=[p for p in Path(".").rglob("*") if p.is_file() and not any(part in ignored for part in p.parts)]; [(_ for _ in ()).throw(AssertionError(f"forbidden external project reference {token} in {path}")) for path in scanned for token in forbidden if token in path.read_text(encoding="utf-8", errors="ignore")]'

mcp-smoke:
	CLEANMAC_TEST_MODE=1 CLEANMAC_TEST_NO_AUTH=1 $(PYTHON) -c 'import json, subprocess, sys; call=lambda req: json.loads(subprocess.check_output([sys.executable, "scripts/cleanmac_mcp_server.py"], input=json.dumps(req), text=True).splitlines()[0]); tools=call({"jsonrpc":"2.0","id":1,"method":"tools/list"})["result"]["tools"]; assert len(tools) == 34, "Expected 34 tools, got %d" % len(tools); names={t["name"] for t in tools}; assert "cleanmac_startup_disable" in names and "cleanmac_privacy_execute" in names; resp=call({"jsonrpc":"2.0","id":2,"method":"tools/call","params":{"name":"cleanmac_capabilities","arguments":{}}}); assert not resp["result"].get("isError"), "MCP capabilities call failed"; assert json.loads(resp["result"]["content"][0]["text"])["schema"] == "cleanmac.capabilities.v1"; assert resp["result"]["structuredContent"]["schema"] == "cleanmac.capabilities.v1"; assert resp["result"]["governanceDecision"]["schema"] == "cleanmac.ai-host-tool-call-decision.v1"; resources=call({"jsonrpc":"2.0","id":3,"method":"resources/list"})["result"]["resources"]; uris={r["uri"] for r in resources}; assert {"cleanmac://capabilities", "cleanmac://ai/function-schemas", "cleanmac://ai/mcp-tool-catalog", "cleanmac://ai/readiness", "cleanmac://ai/runbook", "cleanmac://ai/self-test", "cleanmac://ai/tool-decision-matrix", "cleanmac://ai/governance-advice", "cleanmac://ai/host-policy", "cleanmac://ai/host-integration-pack", "cleanmac://ai/host-preflight", "cleanmac://ai/host-evidence", "cleanmac://ai/eval-pack", "cleanmac://ai/eval-run-smoke"}.issubset(uris); resource=call({"jsonrpc":"2.0","id":4,"method":"resources/read","params":{"uri":"cleanmac://ai/function-schemas"}})["result"]["contents"][0]; assert json.loads(resource["text"])["schema"] == "cleanmac.ai-function-schemas.v1"; runbook=call({"jsonrpc":"2.0","id":5,"method":"resources/read","params":{"uri":"cleanmac://ai/runbook"}})["result"]["contents"][0]; assert json.loads(runbook["text"])["schema"] == "cleanmac.ai-runbook.v1"; decision=call({"jsonrpc":"2.0","id":8,"method":"resources/read","params":{"uri":"cleanmac://ai/tool-decision-matrix"}})["result"]["contents"][0]; assert json.loads(decision["text"])["schema"] == "cleanmac.ai-tool-decision-matrix.v1"; governance=call({"jsonrpc":"2.0","id":11,"method":"resources/read","params":{"uri":"cleanmac://ai/governance-advice"}})["result"]["contents"][0]; assert json.loads(governance["text"])["schema"] == "cleanmac.ai-governance-advice.v1"; host_policy=call({"jsonrpc":"2.0","id":12,"method":"resources/read","params":{"uri":"cleanmac://ai/host-policy"}})["result"]["contents"][0]; assert json.loads(host_policy["text"])["schema"] == "cleanmac.ai-host-policy.v1"; integration=call({"jsonrpc":"2.0","id":15,"method":"resources/read","params":{"uri":"cleanmac://ai/host-integration-pack"}})["result"]["contents"][0]; assert json.loads(integration["text"])["schema"] == "cleanmac.ai-host-integration-pack.v1"; preflight=call({"jsonrpc":"2.0","id":16,"method":"resources/read","params":{"uri":"cleanmac://ai/host-preflight"}})["result"]["contents"][0]; assert json.loads(preflight["text"])["schema"] == "cleanmac.ai-host-preflight.v1"; evidence=call({"jsonrpc":"2.0","id":18,"method":"resources/read","params":{"uri":"cleanmac://ai/host-evidence"}})["result"]["contents"][0]; assert json.loads(evidence["text"])["schema"] == "cleanmac.ai-host-evidence.v1"; denied=call({"jsonrpc":"2.0","id":17,"method":"tools/call","params":{"name":"cleanmac_capabilities","arguments":{"raw_command":"rm -rf /"}}})["result"]; assert denied["isError"] and denied["governanceDecision"]["blocking_reasons"][0]["code"] == "RAW_COMMAND_ARGUMENT_DENIED"; eval_pack=call({"jsonrpc":"2.0","id":9,"method":"resources/read","params":{"uri":"cleanmac://ai/eval-pack"}})["result"]["contents"][0]; assert json.loads(eval_pack["text"])["schema"] == "cleanmac.ai-eval-pack.v1"; eval_run=call({"jsonrpc":"2.0","id":10,"method":"resources/read","params":{"uri":"cleanmac://ai/eval-run-smoke"}})["result"]["contents"][0]; assert json.loads(eval_run["text"])["schema"] == "cleanmac.ai-eval-run.v1"; prompts=call({"jsonrpc":"2.0","id":6,"method":"prompts/list"})["result"]["prompts"]; prompt_names={p["name"] for p in prompts}; assert "safe-cleanup-review" in prompt_names and "confirm-execution-gate" in prompt_names and "explain-tool-decision" in prompt_names and "review-ai-governance" in prompt_names and "review-ai-host-policy" in prompt_names and "run-ai-eval-smoke" in prompt_names; prompt=call({"jsonrpc":"2.0","id":7,"method":"prompts/get","params":{"name":"safe-cleanup-review","arguments":{"categories":"trash"}}})["result"]; assert "cleanmac_execute_plan" in prompt["messages"][0]["content"]["text"]; print("mcp-smoke passed")'
	CLEANMAC_TEST_MODE=1 CLEANMAC_TEST_NO_AUTH=1 $(PYTHON) -c 'import json, subprocess, sys; call=lambda req: json.loads(subprocess.check_output([sys.executable, "scripts/cleanmac_mcp_server.py"], input=json.dumps(req), text=True).splitlines()[0]); uris={r["uri"] for r in call({"jsonrpc":"2.0","id":13,"method":"resources/list"})["result"]["resources"]}; assert "cleanmac://ai/schema-registry" in uris; registry=call({"jsonrpc":"2.0","id":14,"method":"resources/read","params":{"uri":"cleanmac://ai/schema-registry"}})["result"]["contents"][0]; assert json.loads(registry["text"])["schema"] == "cleanmac.ai-schema-registry.v1"'

ai-host-smoke:
	CLEANMAC_TEST_MODE=1 CLEANMAC_TEST_NO_AUTH=1 $(PYTHON) -m unittest tests.test_ai_readiness tests.test_ai_runbook tests.test_ai_self_test tests.test_ai_decision_matrix tests.test_ai_governance tests.test_ai_host_policy tests.test_ai_host_evidence tests.test_ai_eval tests.test_ai_host_scenarios tests.test_mcp_server -v
	CLEANMAC_TEST_MODE=1 CLEANMAC_TEST_NO_AUTH=1 $(PYTHON) -c 'import json, subprocess, sys; matrix=json.loads(subprocess.check_output([sys.executable, "cleanmac.py", "--json", "ai-decision-matrix"], text=True)); assert matrix["schema"] == "cleanmac.ai-tool-decision-matrix.v1"; assert matrix["violation_count"] == 0; tools={t["name"]: t for t in matrix["tools"]}; assert tools["cleanmac_execute_plan"]["mcp_annotations"]["destructiveHint"] is True; assert tools["cleanmac_execute_plan"]["auto_call_allowed"] is False; governance=json.loads(subprocess.check_output([sys.executable, "cleanmac.py", "--json", "ai-governance-advice"], text=True)); assert governance["schema"] == "cleanmac.ai-governance-advice.v1"; assert governance["ready_for_llm_calling"]; host_policy=json.loads(subprocess.check_output([sys.executable, "cleanmac.py", "--json", "ai-host-policy"], text=True)); assert host_policy["schema"] == "cleanmac.ai-host-policy.v1"; assert host_policy["valid"]; assert "cleanmac_execute_plan" in host_policy["auto_call"]["deny"]; integration=json.loads(subprocess.check_output([sys.executable, "cleanmac.py", "--json", "ai-host-integration-pack"], text=True)); assert integration["schema"] == "cleanmac.ai-host-integration-pack.v1"; assert integration["ready"], integration; assert integration["host_policy"]["valid"]; assert "cleanmac://ai/host-integration-pack" in integration["mcp"]["resources"]; assert "cleanmac://ai/host-evidence" in integration["mcp"]["resources"]; preflight=json.loads(subprocess.check_output([sys.executable, "cleanmac.py", "--json", "ai-host-preflight"], text=True)); assert preflight["schema"] == "cleanmac.ai-host-preflight.v1"; assert preflight["ready"], preflight; evidence=json.loads(subprocess.check_output([sys.executable, "cleanmac.py", "--json", "ai-host-evidence"], text=True)); assert evidence["schema"] == "cleanmac.ai-host-evidence.v1"; assert evidence["ready"], evidence; eval_run=json.loads(subprocess.check_output([sys.executable, "cleanmac.py", "--json", "ai-eval-run", "--scenario", "smoke"], text=True)); assert eval_run["schema"] == "cleanmac.ai-eval-run.v1"; assert eval_run["passed"]; assert eval_run["failed_count"] == 0; assert "host_integration_pack_discovery" in eval_run["selected_scenarios"]; assert "host_preflight_discovery" in eval_run["selected_scenarios"]; assert "host_evidence_discovery" in eval_run["selected_scenarios"]; assert "host_evidence_runtime_denial_coverage" in eval_run["selected_scenarios"]; assert "mcp_raw_command_argument_denial" in eval_run["selected_scenarios"]; assert "mcp_destructive_policy_denial" in eval_run["selected_scenarios"]; print("ai-host-smoke passed")'

ai-robustness-smoke:
	CLEANMAC_TEST_MODE=1 CLEANMAC_TEST_NO_AUTH=1 $(PYTHON) -m unittest tests.test_ai_versioning tests.test_mcp_protocol tests.test_ai_concurrency tests.test_ai_idempotency tests.test_ai_eval.AITracePersistenceTests -v

distribution-smoke:
	tmpdir=$$(mktemp -d); \
	trap 'rm -rf "$$tmpdir"' EXIT; \
	$(PYTHON) -m venv "$$tmpdir/build-venv"; \
	"$$tmpdir/build-venv/bin/python" -m pip install --upgrade pip wheel build; \
	"$$tmpdir/build-venv/bin/python" -m build --wheel --sdist --outdir "$$tmpdir/dist"; \
	$(PYTHON) -m venv "$$tmpdir/wheel-venv"; \
	"$$tmpdir/wheel-venv/bin/python" -m pip install "$$tmpdir"/dist/cleanmac-*.whl; \
	"$$tmpdir/wheel-venv/bin/python" -c 'import cleanmac, cleancli, cleancli.core, cleancli.delete_ops, cleancli.protection, cleancli.protection_data, cleancli.workflow; assert callable(cleanmac.main); assert cleanmac.main is cleancli.main'; \
	"$$tmpdir/wheel-venv/bin/cleanmac" --json capabilities >"$$tmpdir/wheel-capabilities.json"; \
	"$$tmpdir/wheel-venv/bin/python" -m json.tool "$$tmpdir/wheel-capabilities.json" >/dev/null; \
	"$$tmpdir/wheel-venv/bin/cleanmac" --json ai-contract-samples >"$$tmpdir/wheel-contract-samples.json"; \
	"$$tmpdir/wheel-venv/bin/python" -c 'import json, pathlib, sys; report=json.loads(pathlib.Path(sys.argv[1]).read_text(encoding="utf-8")); assert report["schema"] == "cleanmac.ai-contract-samples.v1"; assert report["sample_count"] == len(report["samples"]); assert any(sample["target_schema"] == "cleanmac.release-artifact-manifest.v1" for sample in report["samples"])' "$$tmpdir/wheel-contract-samples.json"; \
	$(PYTHON) -m venv "$$tmpdir/sdist-venv"; \
	"$$tmpdir/sdist-venv/bin/python" -m pip install "$$tmpdir"/dist/cleanmac-*.tar.gz; \
	"$$tmpdir/sdist-venv/bin/python" -c 'import cleanmac, cleancli, cleancli.core, cleancli.delete_ops, cleancli.protection, cleancli.protection_data, cleancli.workflow; assert callable(cleanmac.main); assert cleanmac.main is cleancli.main'; \
	"$$tmpdir/sdist-venv/bin/cleanmac" --json capabilities >"$$tmpdir/sdist-capabilities.json"; \
	"$$tmpdir/sdist-venv/bin/python" -m json.tool "$$tmpdir/sdist-capabilities.json" >/dev/null; \
	"$$tmpdir/sdist-venv/bin/cleanmac" --json ai-contract-samples >"$$tmpdir/sdist-contract-samples.json"; \
	"$$tmpdir/sdist-venv/bin/python" -c 'import json, pathlib, sys; report=json.loads(pathlib.Path(sys.argv[1]).read_text(encoding="utf-8")); assert report["schema"] == "cleanmac.ai-contract-samples.v1"; assert report["sample_count"] == len(report["samples"]); assert any(sample["target_schema"] == "cleanmac.release-artifact-manifest.v1" for sample in report["samples"])' "$$tmpdir/sdist-contract-samples.json"; \
	mkdir -p "$$tmpdir/zipapp/cleancli"; \
	cp cleanmac.py "$$tmpdir/zipapp/cleanmac.py"; \
	cp cleancli/*.py "$$tmpdir/zipapp/cleancli/"; \
	$(PYTHON) -c 'import pathlib, sys; pathlib.Path(sys.argv[1]).write_text("from cleanmac import main\nraise SystemExit(main())\n", encoding="utf-8")' "$$tmpdir/zipapp/__main__.py"; \
	$(PYTHON) -m zipapp "$$tmpdir/zipapp" --python "/usr/bin/env python3" --output "$$tmpdir/cleanmac.pyz"; \
	$(PYTHON) "$$tmpdir/cleanmac.pyz" --json capabilities >"$$tmpdir/zipapp-capabilities.json"; \
	$(PYTHON) -m json.tool "$$tmpdir/zipapp-capabilities.json" >/dev/null; \
	$(PYTHON) "$$tmpdir/cleanmac.pyz" --json ai-contract-samples >"$$tmpdir/zipapp-contract-samples.json"; \
	$(PYTHON) -c 'import json, pathlib, sys; report=json.loads(pathlib.Path(sys.argv[1]).read_text(encoding="utf-8")); assert report["schema"] == "cleanmac.ai-contract-samples.v1"; assert report["sample_count"] == len(report["samples"]); assert any(sample["target_schema"] == "cleanmac.release-artifact-manifest.v1" for sample in report["samples"])' "$$tmpdir/zipapp-contract-samples.json"; \
	$(PYTHON) scripts/generate_homebrew_formula.py --version 0.1.0 --archive-url https://github.com/cleanmac/cleanmac/archive/refs/tags/v0.1.0.tar.gz --sha256 0000000000000000000000000000000000000000000000000000000000000000 --output "$$tmpdir/cleanmac.rb"; \
	$(PYTHON) -c 'import pathlib, sys; text=pathlib.Path(sys.argv[1]).read_text(encoding="utf-8"); required=("class Cleanmac < Formula", "include Language::Python::Virtualenv", "url ", "sha256 ", "license \"MIT\"", "test do", "shell_output(\"#{bin}/cleanmac --json capabilities\")"); [(_ for _ in ()).throw(AssertionError(token)) for token in required if token not in text]' "$$tmpdir/cleanmac.rb"

homebrew-formula-smoke:
	tmpdir=$$(mktemp -d); \
	trap 'rm -rf "$$tmpdir"' EXIT; \
	$(PYTHON) scripts/generate_homebrew_formula.py --version 0.1.0 --archive-url https://github.com/cleanmac/cleanmac/archive/refs/tags/v0.1.0.tar.gz --sha256 0000000000000000000000000000000000000000000000000000000000000000 --output "$$tmpdir/cleanmac.rb"; \
	$(PYTHON) -c 'import pathlib, subprocess, sys; formula=pathlib.Path(sys.argv[1]); text=formula.read_text(encoding="utf-8"); required=("class Cleanmac < Formula", "include Language::Python::Virtualenv", "homepage \"https://github.com/cleanmac/cleanmac\"", "url \"https://github.com/cleanmac/cleanmac/archive/refs/tags/v0.1.0.tar.gz\"", "sha256 \"0000000000000000000000000000000000000000000000000000000000000000\"", "license \"MIT\"", "depends_on \"python@3.12\"", "virtualenv_install_with_resources", "test do", "shell_output(\"#{bin}/cleanmac --json capabilities\")", "assert_match \"cleanmac.capabilities.v1\", output"); [(_ for _ in ()).throw(AssertionError(token)) for token in required if token not in text]; ruby=subprocess.run(["ruby", "-c", str(formula)], text=True, capture_output=True) if pathlib.Path("/usr/bin/ruby").exists() else None; assert ruby is None or ruby.returncode == 0, ruby.stderr' "$$tmpdir/cleanmac.rb"

release-artifacts-smoke:
	tmpdir=$$(mktemp -d); \
	trap 'rm -rf "$$tmpdir"' EXIT; \
	$(PYTHON) -c 'import shutil, pathlib, sys; src=pathlib.Path.cwd(); dst=pathlib.Path(sys.argv[1]) / "src"; shutil.copytree(src, dst, ignore=shutil.ignore_patterns(".git", "build", "dist", "*.egg-info", "__pycache__", ".mypy_cache", ".pytest_cache", ".ruff_cache"))' "$$tmpdir"; \
	$(PYTHON) -m venv "$$tmpdir/build-venv"; \
	"$$tmpdir/build-venv/bin/python" -m pip install --upgrade pip wheel build; \
	"$$tmpdir/build-venv/bin/python" -m build --wheel --sdist --outdir "$$tmpdir/dist" "$$tmpdir/src"; \
	mkdir -p "$$tmpdir/release-assets"; \
	$(PYTHON) "$$tmpdir/src/scripts/generate_sbom.py" --output "$$tmpdir/release-assets/SBOM.json"; \
	"$$tmpdir/build-venv/bin/python" "$$tmpdir/src/scripts/generate_homebrew_formula.py" --version 0.1.0 --archive-url https://github.com/cleanmac/cleanmac/archive/refs/tags/v0.1.0.tar.gz --sha256 0000000000000000000000000000000000000000000000000000000000000000 --output "$$tmpdir/release-assets/cleanmac.rb"; \
	"$$tmpdir/build-venv/bin/python" "$$tmpdir/src/scripts/generate_release_manifest.py" --dist-dir "$$tmpdir/dist" --assets-dir "$$tmpdir/release-assets"; \
	$(PYTHON) -c 'import hashlib, json, pathlib, sys; dist=pathlib.Path(sys.argv[1]); assets=pathlib.Path(sys.argv[2]); checksums=assets / "SHA256SUMS"; lines=checksums.read_text(encoding="utf-8").splitlines(); assert lines; [(_ for _ in ()).throw(AssertionError(name)) for line in lines for digest, name in [line.split(None, 1)] for base in [assets if name.strip() in {"SBOM.json", "cleanmac.rb"} else dist] if hashlib.sha256((base / name.strip()).read_bytes()).hexdigest() != digest]; manifest=json.loads((assets / "ARTIFACT-MANIFEST.json").read_text(encoding="utf-8")); assert manifest["schema"] == "cleanmac.release-artifact-manifest.v1"; assert manifest["distribution_policy"]["homebrew_formula"] == "tap-publishable"; assert manifest["distribution_policy"]["homebrew_tap"] == "cleanmac/tap"; assert any(row["name"] == "SBOM.json" for row in manifest["artifacts"]); assert any(row["name"] == "cleanmac.rb" and row["kind"] == "homebrew-formula" for row in manifest["artifacts"])' "$$tmpdir/dist" "$$tmpdir/release-assets"; \
	$(PYTHON) -m venv "$$tmpdir/install-venv"; \
	"$$tmpdir/install-venv/bin/python" -m pip install "$$tmpdir"/dist/cleanmac-*.whl; \
	"$$tmpdir/install-venv/bin/cleanmac" --json capabilities >"$$tmpdir/install-capabilities.json"; \
	"$$tmpdir/install-venv/bin/python" -m json.tool "$$tmpdir/install-capabilities.json" >/dev/null

release-readiness-smoke:
	CLEANMAC_TEST_MODE=1 CLEANMAC_TEST_NO_AUTH=1 $(PYTHON) -c 'import json, subprocess, sys; report=json.loads(subprocess.check_output([sys.executable, "cleanmac.py", "--json", "release-readiness"], text=True)); assert report["schema"] == "cleanmac.release-readiness.v1"; assert report["destructive"] is False; assert report["dry_run"] is True; assert report["readiness_score"]["total"] == 7; gate_ids={gate["id"] for gate in report["gates"]}; assert "ai-host-integration-pack-ready" in gate_ids; assert "release-artifact-manifest-valid" in gate_ids; commands={tuple(cmd) for cmd in report["release_gate_commands"]}; assert ("make", "quality-check") in commands; assert ("make", "governed-execution-smoke") in commands; assert ("make", "ai-contract-smoke") in commands; assert ("make", "mcp-smoke") in commands; assert ("make", "ai-host-smoke") in commands; assert ("make", "release-artifacts-smoke") in commands; assert any("release artifacts" in question.lower() for question in report["review_questions"]); print("release-readiness-smoke passed")'

no-cache-check:
	set -e; \
	tmpdir=$$(mktemp -d); \
	mypy_cache="/tmp/cleanmac-mypy-cache-$$$$"; \
	coverage_dir="$$tmpdir/coverage"; \
	cleanup() { \
		/bin/rm -R "$$tmpdir" "$$mypy_cache" 2>/dev/null || true; \
		[ ! -e .pytest_cache ] || /bin/rm -R .pytest_cache; \
		[ ! -e .mypy_cache ] || /bin/rm -R .mypy_cache; \
		[ ! -e .ruff_cache ] || /bin/rm -R .ruff_cache; \
	}; \
	trap cleanup EXIT; \
	mkdir -p "$$coverage_dir"; \
	export PIP_NO_CACHE_DIR=1 PYTHONDONTWRITEBYTECODE=1 CLEANMAC_TEST_NO_AUTH=1 CLEANMAC_TEST_MODE=1 PYTEST_ADDOPTS="-p no:cacheprovider"; \
	$(PYTHON) -m venv "$$tmpdir/venv"; \
	venv_python="$$tmpdir/venv/bin/python"; \
	"$$venv_python" -m pip install --no-cache-dir --upgrade pip; \
	"$$venv_python" -m pip install --no-cache-dir -e '.[dev,build]'; \
	[ ! -e .pytest_cache ] || /bin/rm -R .pytest_cache; \
	[ ! -e .mypy_cache ] || /bin/rm -R .mypy_cache; \
	[ ! -e .ruff_cache ] || /bin/rm -R .ruff_cache; \
	RUFF_CACHE_DIR="$$tmpdir/ruff-cache" "$$venv_python" -m ruff format --check .; \
	RUFF_CACHE_DIR="$$tmpdir/ruff-cache" "$$venv_python" -m ruff check .; \
	"$$venv_python" -m mypy --cache-dir "$$mypy_cache" cleanmac.py cleancli test_cleanmac.py tests; \
	"$$venv_python" -m coverage run --data-file "$$coverage_dir/.coverage" -m unittest -v; \
	"$$venv_python" -m coverage report --data-file "$$coverage_dir/.coverage"; \
	"$$venv_python" -m pytest -q -p no:cacheprovider; \
	PYTHON="$$venv_python" PIP_NO_CACHE_DIR=1 PYTEST_ADDOPTS="-p no:cacheprovider" $(MAKE) local-test build-check package-smoke script-smoke bundle-audit-smoke macos-smoke security-smoke dependency-audit-smoke docs-smoke governance-smoke ai-governance-smoke ai-contract-smoke governed-execution-smoke mcp-smoke ai-host-smoke ai-robustness-smoke open-source-smoke release-readiness-smoke

docker-test:
	docker run --rm \
		$(DOCKER_RUN_FLAGS) \
		-v "$(SANDBOX_MOUNT):/work:ro" \
		-w "$(WORKDIR)" \
		$(DOCKER_IMAGE) \
		sh -lc 'apt-get -o Acquire::Retries=3 -o Acquire::http::Timeout=20 update >/dev/null && DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends python3 python3-venv make >/dev/null && python3 -m venv /tmp/cleanmac-venv && PYTHONDONTWRITEBYTECODE=1 /tmp/cleanmac-venv/bin/python -m unittest -v'

no-cache-docker-test:
	DOCKER_RUN_FLAGS="--pull=always" $(MAKE) docker-test

release-check: quality-check local-test pytest-test build-check package-smoke script-smoke bundle-audit-smoke macos-smoke security-smoke dependency-audit-smoke docs-smoke governance-smoke ai-governance-smoke ai-contract-smoke governed-execution-smoke mcp-smoke ai-host-smoke ai-robustness-smoke open-source-smoke distribution-smoke homebrew-formula-smoke release-artifacts-smoke release-readiness-smoke docker-test

no-cache-release-check:
	PIP_NO_CACHE_DIR=1 $(MAKE) no-cache-check
	PIP_NO_CACHE_DIR=1 $(MAKE) distribution-smoke homebrew-formula-smoke release-artifacts-smoke release-readiness-smoke no-cache-docker-test
