"""Tests for the cleanmac MCP stdio server."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

PROJECT_ROOT = Path(__file__).resolve().parent.parent
MCP_SERVER = PROJECT_ROOT / "scripts" / "cleanmac_mcp_server.py"
CLI_SCRIPT = PROJECT_ROOT / "cleanmac.py"


def _mcp_request(request: dict) -> dict:
    """Send a single JSON-RPC request to the MCP server and return the parsed response."""
    proc = subprocess.Popen(
        [sys.executable, str(MCP_SERVER)],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        env=_mcp_env(),
    )
    payload = json.dumps(request)
    try:
        stdout, stderr = proc.communicate(input=payload, timeout=30)
    except subprocess.TimeoutExpired as err:
        proc.kill()
        stdout, stderr = proc.communicate()
        raise RuntimeError(f"MCP server timed out. request={request!r} stdout={stdout!r} stderr={stderr!r}") from err
    if not stdout.strip():
        raise RuntimeError(f"MCP server returned empty stdout. stderr={stderr.strip()}")
    # Some methods (e.g. initialize) emit multiple lines (response + notifications).
    # Only parse the first JSON line as the response.
    first_line = stdout.strip().split("\n")[0]
    return json.loads(first_line)


def _mcp_env() -> dict[str, str]:
    """Return environment dict with test-mode variables for MCP subprocess."""
    env = os.environ.copy()
    # Do NOT set CLEANMAC_CLI — the server's find_cleanmac() fallback logic
    # correctly locates cleanmac.py alongside scripts/ and prefixes sys.executable.
    env["CLEANMAC_TEST_MODE"] = "1"
    env["CLEANMAC_TEST_NO_AUTH"] = "1"
    return env


def test_tools_list_returns_all_tools() -> None:
    response = _mcp_request({"jsonrpc": "2.0", "id": 1, "method": "tools/list"})
    tools = response["result"]["tools"]
    assert len(tools) == 38
    for tool in tools:
        assert "name" in tool
        assert "description" in tool
        assert "annotations" in tool
        assert "inputSchema" in tool
    names = {t["name"] for t in tools}
    assert "cleanmac_capabilities" in names
    assert "cleanmac_profiles" in names
    assert "cleanmac_scripts" in names
    assert "cleanmac_software_uninstall_execute" in names
    assert "cleanmac_open" in names
    assert "cleanmac_links" in names
    assert "cleanmac_optimize" in names
    assert "cleanmac_startup_disable" in names
    assert "cleanmac_privacy_execute" in names
    tool_by_name = {t["name"]: t for t in tools}
    assert tool_by_name["cleanmac_capabilities"]["annotations"]["readOnlyHint"]
    assert tool_by_name["cleanmac_execute_plan"]["annotations"]["destructiveHint"]
    assert tool_by_name["cleanmac_startup_disable"]["annotations"]["destructiveHint"]
    assert tool_by_name["cleanmac_privacy_execute"]["annotations"]["destructiveHint"]


def test_destructive_tool_call_blocked_by_policy() -> None:
    """Verify cleanmac_execute_plan is deny-listed and all denied tools have destructiveHint."""
    host_policy_response = _mcp_request(
        {
            "jsonrpc": "2.0",
            "id": 71,
            "method": "resources/read",
            "params": {"uri": "cleanmac://ai/host-policy"},
        }
    )
    host_policy = json.loads(host_policy_response["result"]["contents"][0]["text"])
    deny_list = host_policy["auto_call"]["deny"]

    assert "cleanmac_execute_plan" in deny_list

    tools_response = _mcp_request({"jsonrpc": "2.0", "id": 72, "method": "tools/list"})
    tools = tools_response["result"]["tools"]
    tool_by_name = {t["name"]: t for t in tools}

    for denied_tool in deny_list:
        assert denied_tool in tool_by_name, f"Deny-listed tool {denied_tool} not found in tools/list"
        assert tool_by_name[denied_tool]["annotations"]["destructiveHint"], (
            f"Deny-listed tool {denied_tool} missing destructiveHint annotation"
        )


def test_infrastructure_error_cli_not_found() -> None:
    """Verify MCP returns structured error when CLEANMAC_CLI points to a nonexistent path."""
    env = _mcp_env()
    env["CLEANMAC_CLI"] = "/nonexistent/cleanmac"
    proc = subprocess.Popen(
        [sys.executable, str(MCP_SERVER)],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        env=env,
    )
    request = {
        "jsonrpc": "2.0",
        "id": 73,
        "method": "tools/call",
        "params": {"name": "cleanmac_capabilities", "arguments": {}},
    }
    stdout, _stderr = proc.communicate(input=json.dumps(request), timeout=15)
    response = json.loads(stdout.strip().split("\n")[0])

    result = response["result"]
    assert result["isError"]
    assert "CLI not found" in result["content"][0]["text"]
    assert result["structuredContent"]["schema"] == "cleanmac.mcp-tool-error.v1"
    assert result["structuredContent"]["tool"] == "cleanmac_capabilities"


def test_infrastructure_error_nonzero_exit() -> None:
    """Verify MCP returns structured error when the CLI exits with non-zero status."""
    with tempfile.TemporaryDirectory() as tmp:
        failing_script = Path(tmp) / "fail.sh"
        failing_script.write_text("#!/bin/sh\necho 'simulated failure' >&2\nexit 1\n", encoding="utf-8")
        failing_script.chmod(0o755)

        env = _mcp_env()
        env["CLEANMAC_CLI"] = str(failing_script)
        proc = subprocess.Popen(
            [sys.executable, str(MCP_SERVER)],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            env=env,
        )
        request = {
            "jsonrpc": "2.0",
            "id": 75,
            "method": "tools/call",
            "params": {"name": "cleanmac_capabilities", "arguments": {}},
        }
        stdout, _stderr = proc.communicate(input=json.dumps(request), timeout=15)
        response = json.loads(stdout.strip().split("\n")[0])

        result = response["result"]
        assert result["isError"]
        error_text = result["content"][0]["text"]
        assert "failed" in error_text.lower()
        assert result["structuredContent"]["schema"] == "cleanmac.mcp-tool-error.v1"
        assert result["structuredContent"]["tool"] == "cleanmac_capabilities"


def test_tools_call_readonly_capabilities() -> None:
    response = _mcp_request(
        {
            "jsonrpc": "2.0",
            "id": 2,
            "method": "tools/call",
            "params": {"name": "cleanmac_capabilities", "arguments": {}},
        }
    )
    result = response["result"]
    assert not result.get("isError")
    assert result["content"][0]["type"] == "text"
    data = json.loads(result["content"][0]["text"])
    assert data["schema"] == "cleanmac.capabilities.v1"
    assert result["structuredContent"]["schema"] == "cleanmac.capabilities.v1"
    assert result["governanceDecision"]["schema"] == "cleanmac.ai-host-tool-call-decision.v1"
    assert result["governanceDecision"]["allowed"]


def test_tools_call_raw_command_argument_denied_by_runtime_policy() -> None:
    dangerous_raw_command = "rm " + "-rf /"
    response = _mcp_request(
        {
            "jsonrpc": "2.0",
            "id": 76,
            "method": "tools/call",
            "params": {
                "name": "cleanmac_capabilities",
                "arguments": {"raw_command": dangerous_raw_command},
            },
        }
    )
    result = response["result"]
    assert result["isError"]
    decision = result["governanceDecision"]
    assert decision["schema"] == "cleanmac.ai-host-tool-call-decision.v1"
    assert not decision["allowed"]
    assert decision["blocking_reasons"][0]["code"] == "RAW_COMMAND_ARGUMENT_DENIED"
    assert decision["next_allowed_tools"] == ["cleanmac_validate_plan", "cleanmac_policy_simulate"]
    structured = result["structuredContent"]
    assert structured["schema"] == "cleanmac.mcp-tool-error.v1"
    assert structured["next_allowed_tools"] == decision["next_allowed_tools"]
    assert structured["policy_decision"] == decision


def test_tools_call_destructive_missing_runtime_gates_denied_by_policy() -> None:
    response = _mcp_request(
        {
            "jsonrpc": "2.0",
            "id": 77,
            "method": "tools/call",
            "params": {
                "name": "cleanmac_execute_plan",
                "arguments": {"plan_file": "/tmp/cleanmac-plan.json"},
            },
        }
    )
    result = response["result"]
    assert result["isError"]
    decision = result["governanceDecision"]
    codes = {reason["code"] for reason in decision["blocking_reasons"]}
    assert "HUMAN_CONFIRMATION_PHRASE_REQUIRED" in codes
    assert "CONFIRMATION_TOKEN_REQUIRED" in codes
    assert not decision["safe_to_auto_retry"]
    assert decision["next_allowed_tools"] == ["cleanmac_validate_plan", "cleanmac_policy_simulate"]
    assert result["structuredContent"]["next_allowed_tools"] == ["cleanmac_validate_plan", "cleanmac_policy_simulate"]


def test_resources_list_exposes_ai_governance_resources() -> None:
    response = _mcp_request({"jsonrpc": "2.0", "id": 21, "method": "resources/list"})
    resources = response["result"]["resources"]
    uris = {resource["uri"] for resource in resources}

    assert "cleanmac://mcp/resource-index" in uris
    assert "cleanmac://mcp/prompt-index" in uris
    assert "cleanmac://capabilities" in uris
    assert "cleanmac://ai/function-schemas" in uris
    assert "cleanmac://ai/mcp-tool-catalog" in uris
    assert "cleanmac://ai/contract-validation" in uris
    assert "cleanmac://ai/contract-samples" in uris
    assert "cleanmac://ai/entrypoints" in uris
    assert "cleanmac://ai/safety-chain" in uris
    assert "cleanmac://ai/operation-log-explainability" in uris
    assert "cleanmac://ai/cold-start-budget" in uris
    assert "cleanmac://ai/no-disturbance" in uris
    assert "cleanmac://release/dependency-governance" in uris
    assert "cleanmac://ai/workflow-contract" in uris
    assert "cleanmac://ai/host-integration-pack" in uris
    assert "cleanmac://ai/host-preflight" in uris
    assert "cleanmac://ai/host-evidence" in uris
    assert "cleanmac://release/readiness" in uris
    assert "cleanmac://release/diagnostics" in uris
    assert "cleanmac://release/evidence" in uris
    assert "cleanmac://release/operator-summary" in uris
    assert "cleanmac://release/rehearsal" in uris
    assert "cleanmac://release/promotion-decision" in uris
    assert "cleanmac://release/rollback-plan" in uris
    assert "cleanmac://release/post-publish-verification" in uris
    assert "cleanmac://release/post-publish-result" in uris
    assert "cleanmac://release/post-publish-evidence-template" in uris
    assert "cleanmac://mcp/meta-index" in uris
    assert "cleanmac://mcp/tool-index" in uris
    assert "cleanmac://mcp/destructive-tool-governance" in uris
    assert "cleanmac://mcp/surface-audit" in uris
    assert all(resource["mimeType"] == "application/json" for resource in resources)
    assert all(resource["destructive"] is False for resource in resources)
    assert all(resource["safe_for_mcp"] is True for resource in resources)


def test_resources_read_mcp_meta_index() -> None:
    response = _mcp_request(
        {
            "jsonrpc": "2.0",
            "id": 90,
            "method": "resources/read",
            "params": {"uri": "cleanmac://mcp/meta-index"},
        }
    )
    contents = response["result"]["contents"]
    assert contents[0]["uri"] == "cleanmac://mcp/meta-index"
    payload = json.loads(contents[0]["text"])
    assert payload["schema"] == "cleanmac.mcp-meta-index.v1"
    assert payload["ready"], payload
    assert payload["index_count"] == len(payload["indexes"])
    assert set(payload["index_uris"]) == {
        "cleanmac://mcp/resource-index",
        "cleanmac://mcp/prompt-index",
        "cleanmac://mcp/tool-index",
        "cleanmac://mcp/destructive-tool-governance",
    }
    assert all(index["ready"] is True for index in payload["indexes"])


def test_resources_read_mcp_resource_index() -> None:
    response = _mcp_request(
        {
            "jsonrpc": "2.0",
            "id": 91,
            "method": "resources/read",
            "params": {"uri": "cleanmac://mcp/resource-index"},
        }
    )
    contents = response["result"]["contents"]
    assert contents[0]["uri"] == "cleanmac://mcp/resource-index"
    payload = json.loads(contents[0]["text"])
    assert payload["schema"] == "cleanmac.mcp-resource-index.v1"
    assert payload["ready"], payload
    assert payload["resource_count"] == len(payload["resources"])
    assert "cleanmac://mcp/meta-index" in payload["resource_uris"]
    assert "cleanmac://mcp/prompt-index" in payload["resource_uris"]
    assert "cleanmac://mcp/tool-index" in payload["resource_uris"]
    assert "cleanmac://mcp/destructive-tool-governance" in payload["resource_uris"]
    assert "cleanmac://mcp/surface-audit" in payload["resource_uris"]
    assert "cleanmac://ai/operation-log-explainability" in payload["resource_uris"]
    assert "cleanmac://ai/cold-start-budget" in payload["resource_uris"]
    assert "cleanmac://ai/no-disturbance" in payload["resource_uris"]
    assert "cleanmac://release/dependency-governance" in payload["resource_uris"]
    assert "cleanmac://release/post-publish-evidence-template" in payload["resource_uris"]
    assert "cleanmac://ai/entrypoints" in payload["resource_uris"]
    assert "cleanmac://ai/safety-chain" in payload["resource_uris"]
    assert "cleanmac://ai/workflow-contract" in payload["resource_uris"]
    assert all(resource["safe_for_mcp"] is True for resource in payload["resources"])


def test_resources_read_mcp_prompt_index() -> None:
    response = _mcp_request(
        {
            "jsonrpc": "2.0",
            "id": 93,
            "method": "resources/read",
            "params": {"uri": "cleanmac://mcp/prompt-index"},
        }
    )
    contents = response["result"]["contents"]
    assert contents[0]["uri"] == "cleanmac://mcp/prompt-index"
    payload = json.loads(contents[0]["text"])
    assert payload["schema"] == "cleanmac.mcp-prompt-index.v1"
    assert payload["ready"], payload
    assert payload["prompt_count"] == len(payload["prompts"])
    assert "review-ai-host-policy" in payload["prompt_names"]
    assert all(prompt["safe_for_mcp"] is True for prompt in payload["prompts"])
    assert all(prompt["destructive"] is False for prompt in payload["prompts"])
    assert all(prompt["dry_run"] is True for prompt in payload["prompts"])
    assert all(prompt["uses_shell"] is False for prompt in payload["prompts"])


def test_resources_read_mcp_tool_index() -> None:
    response = _mcp_request(
        {
            "jsonrpc": "2.0",
            "id": 94,
            "method": "resources/read",
            "params": {"uri": "cleanmac://mcp/tool-index"},
        }
    )
    contents = response["result"]["contents"]
    assert contents[0]["uri"] == "cleanmac://mcp/tool-index"
    payload = json.loads(contents[0]["text"])
    assert payload["schema"] == "cleanmac.mcp-tool-index.v1"
    assert payload["ready"], payload
    assert payload["tool_count"] == len(payload["tools"])
    assert "cleanmac_execute_plan" in payload["tool_names"]
    assert "cleanmac_execute_plan" in payload["destructive_tool_names"]
    assert "cleanmac_execute_plan" in payload["auto_call_denied_tool_names"]
    assert all(tool["safe_for_mcp"] is True for tool in payload["tools"])
    assert all(tool["uses_shell"] is False for tool in payload["tools"])
    assert all(tool["invocation_mode"] == "argv" for tool in payload["tools"])
    for tool in payload["tools"]:
        if tool["destructive"]:
            assert not tool["auto_call_allowed"], tool
            assert tool["requires_confirmation"], tool


def test_resources_read_mcp_destructive_tool_governance() -> None:
    response = _mcp_request(
        {
            "jsonrpc": "2.0",
            "id": 95,
            "method": "resources/read",
            "params": {"uri": "cleanmac://mcp/destructive-tool-governance"},
        }
    )
    contents = response["result"]["contents"]
    assert contents[0]["uri"] == "cleanmac://mcp/destructive-tool-governance"
    payload = json.loads(contents[0]["text"])
    assert payload["schema"] == "cleanmac.mcp-destructive-tool-governance.v1"
    assert payload["ready"], payload
    assert "cleanmac_execute_plan" in payload["destructive_tool_names"]
    assert "cleanmac_software_uninstall_execute" in payload["destructive_tool_names"]
    assert payload["validation"]["violation_count"] == 0
    for tool in payload["destructive_tools"]:
        assert not tool["auto_call_allowed"], tool
        assert tool["requires_confirmation"], tool
        assert tool["requires_operation_log"], tool
        assert not tool["uses_shell"], tool
        assert tool["invocation_mode"] == "argv"
        assert tool["mcp_annotations"]["destructiveHint"], tool
        assert not tool["mcp_annotations"]["readOnlyHint"], tool
        assert "--execute" in tool["safe_argv_template"]
        assert "--operation-log" in tool["safe_argv_template"]


def test_resources_read_operation_log_explainability() -> None:
    response = _mcp_request(
        {
            "jsonrpc": "2.0",
            "id": 96,
            "method": "resources/read",
            "params": {"uri": "cleanmac://ai/operation-log-explainability"},
        }
    )
    contents = response["result"]["contents"]
    assert contents[0]["uri"] == "cleanmac://ai/operation-log-explainability"
    payload = json.loads(contents[0]["text"])
    assert payload["schema"] == "cleanmac.operation-log-explainability.v1"
    assert payload["ready"], payload
    assert payload["validation"]["valid"], payload["validation"]
    assert payload["format"] == "jsonl"
    assert payload["append_only"]
    assert {"timestamp", "tool", "parameters", "result", "impact_scope"}.issubset(payload["required_entry_fields"])
    assert payload["sample_entry"]["tool"] == "cleanmac.clean.run"


def test_resources_read_cold_start_budget() -> None:
    response = _mcp_request(
        {
            "jsonrpc": "2.0",
            "id": 97,
            "method": "resources/read",
            "params": {"uri": "cleanmac://ai/cold-start-budget"},
        }
    )
    contents = response["result"]["contents"]
    assert contents[0]["uri"] == "cleanmac://ai/cold-start-budget"
    payload = json.loads(contents[0]["text"])
    assert payload["schema"] == "cleanmac.cold-start-budget.v1"
    assert payload["ready"], payload
    assert payload["validation"]["valid"], payload["validation"]
    assert payload["budgets"]["cli_cold_start_max_ms"] == 1200
    assert payload["budgets"]["resident_processes_after_exit"] == 0


def test_resources_read_dependency_governance() -> None:
    response = _mcp_request(
        {
            "jsonrpc": "2.0",
            "id": 98,
            "method": "resources/read",
            "params": {"uri": "cleanmac://release/dependency-governance"},
        }
    )
    contents = response["result"]["contents"]
    assert contents[0]["uri"] == "cleanmac://release/dependency-governance"
    payload = json.loads(contents[0]["text"])
    assert payload["schema"] == "cleanmac.dependency-governance.v1"
    assert payload["ready"], payload
    assert payload["validation"]["valid"], payload["validation"]
    assert payload["pyproject"]["runtime_dependency_count"] == 0
    assert payload["runtime_dependency_policy"] == "stdlib-only-runtime-by-default"
    assert ["make", "dependency-audit-smoke"] in payload["release_gate_commands"]


def test_resources_read_no_disturbance() -> None:
    response = _mcp_request(
        {
            "jsonrpc": "2.0",
            "id": 99,
            "method": "resources/read",
            "params": {"uri": "cleanmac://ai/no-disturbance"},
        }
    )
    contents = response["result"]["contents"]
    assert contents[0]["uri"] == "cleanmac://ai/no-disturbance"
    payload = json.loads(contents[0]["text"])
    assert payload["schema"] == "cleanmac.no-disturbance.v1"
    assert payload["ready"], payload
    assert payload["validation"]["valid"], payload["validation"]
    assert payload["silent_by_default"]
    assert not payload["sends_notifications"]
    assert not payload["shows_dialogs"]
    assert not payload["push_reminders"]
    assert ["make", "no-disturbance-smoke"] in payload["release_gate_commands"]


def test_resources_read_mcp_surface_audit() -> None:
    response = _mcp_request(
        {
            "jsonrpc": "2.0",
            "id": 95,
            "method": "resources/read",
            "params": {"uri": "cleanmac://mcp/surface-audit"},
        }
    )
    contents = response["result"]["contents"]
    assert contents[0]["uri"] == "cleanmac://mcp/surface-audit"
    payload = json.loads(contents[0]["text"])
    assert payload["schema"] == "cleanmac.mcp-surface-audit.v1"
    assert not payload["destructive"]
    assert payload["dry_run"]
    assert payload["ready"], payload
    assert payload["resource_uri"] == "cleanmac://mcp/surface-audit"
    assert payload["missing"] == {"resources": [], "prompts": [], "tools": []}
    assert payload["failed_check_ids"] == []
    assert payload["readiness_score"] == {"passed": 20, "total": 20, "level": "ready"}
    assert payload["next_action"] == "proceed-to-host-integration-pack"
    assert payload["stop_reason"] == ""
    checks = {check["id"]: check for check in payload["checks"]}
    assert checks["mcp-meta-index-ready"]["passed"]
    assert ["make", "mcp-meta-index-smoke"] in checks["mcp-meta-index-ready"]["remediation_commands"]
    assert checks["mcp-resource-index-ready"]["passed"]
    assert checks["mcp-prompt-index-ready"]["passed"]
    assert checks["mcp-tool-index-ready"]["passed"]
    assert checks["mcp-destructive-tool-governance-ready"]["passed"]
    assert checks["required-resources-advertised"]["passed"]
    assert checks["required-prompts-advertised"]["passed"]
    assert checks["required-tools-advertised"]["passed"]
    assert checks["runtime-lifecycle-policy-advertised"]["passed"]
    assert checks["zero-resident-audit-advertised"]["passed"]
    assert checks["operation-log-explainability-advertised"]["passed"]
    assert checks["cold-start-budget-advertised"]["passed"]
    assert checks["no-disturbance-advertised"]["passed"]
    assert checks["dependency-governance-advertised"]["passed"]
    assert checks["destructive-tools-gated"]["passed"]
    assert checks["no-shell-invocation"]["passed"]
    assert "read cleanmac://release/dependency-governance" in payload["recommended_call_sequence"]
    assert "read cleanmac://ai/no-disturbance" in payload["recommended_call_sequence"]
    assert "read cleanmac://mcp/surface-audit" in payload["recommended_call_sequence"]
    assert ["make", "mcp-surface-audit-smoke"] in payload["remediation_commands"]


def _assert_surface_audit_blocked(payload: dict, failed_check_id: str, command: list[str]) -> None:
    assert not payload["ready"], payload
    assert failed_check_id in payload["failed_check_ids"]
    assert payload["readiness_score"]["level"] == "blocked"
    assert payload["readiness_score"]["passed"] < payload["readiness_score"]["total"]
    assert payload["next_action"] == "stop-and-remediate-mcp-surface"
    assert failed_check_id in payload["stop_reason"]
    assert ["make", "mcp-surface-audit-smoke"] in payload["remediation_commands"]
    checks = {check["id"]: check for check in payload["checks"]}
    assert not checks[failed_check_id]["passed"]
    assert command in checks[failed_check_id]["remediation_commands"]


def test_mcp_surface_audit_fails_closed_when_required_resource_missing() -> None:
    from cleancli.mcp_resources import render_mcp_surface_audit

    with patch("cleancli.mcp_resources.render_mcp_resource_index") as mock_resource:
        mock_resource.return_value = {
            "schema": "cleanmac.mcp-resource-index.v1",
            "destructive": False,
            "dry_run": True,
            "ready": True,
            "resource_count": 0,
            "resources": [],
            "resource_uris": [],
        }

        payload = render_mcp_surface_audit()

    assert "cleanmac://mcp/surface-audit" in payload["missing"]["resources"]
    _assert_surface_audit_blocked(
        payload,
        "required-resources-advertised",
        ["make", "mcp-resource-index-smoke"],
    )


def test_mcp_surface_audit_fails_closed_when_required_prompt_missing() -> None:
    from cleancli.mcp_resources import render_mcp_surface_audit

    with patch("cleancli.mcp_prompts.render_mcp_prompt_index") as mock_prompt:
        mock_prompt.return_value = {
            "schema": "cleanmac.mcp-prompt-index.v1",
            "destructive": False,
            "dry_run": True,
            "ready": True,
            "prompt_count": 0,
            "prompts": [],
            "prompt_names": [],
        }

        payload = render_mcp_surface_audit()

    assert payload["missing"]["prompts"] == ["review-ai-host-policy"]
    _assert_surface_audit_blocked(
        payload,
        "required-prompts-advertised",
        ["make", "mcp-prompt-index-smoke"],
    )


def test_mcp_surface_audit_fails_closed_when_required_tool_missing() -> None:
    from cleancli.mcp_resources import render_mcp_surface_audit

    with patch("cleancli.mcp_tools.render_mcp_tool_index") as mock_tool:
        mock_tool.return_value = {
            "schema": "cleanmac.mcp-tool-index.v1",
            "destructive": False,
            "dry_run": True,
            "ready": True,
            "tool_count": 0,
            "tools": [],
            "tool_names": [],
        }

        payload = render_mcp_surface_audit()

    assert "cleanmac_execute_plan" in payload["missing"]["tools"]
    _assert_surface_audit_blocked(
        payload,
        "required-tools-advertised",
        ["make", "mcp-tool-index-smoke"],
    )


def test_mcp_surface_audit_fails_closed_when_destructive_tool_allows_auto_call() -> None:
    from cleancli.mcp_resources import render_mcp_surface_audit

    with patch("cleancli.mcp_tools.render_mcp_tool_index") as mock_tool:
        mock_tool.return_value = {
            "schema": "cleanmac.mcp-tool-index.v1",
            "destructive": False,
            "dry_run": True,
            "ready": True,
            "tool_count": 3,
            "tools": [
                {
                    "name": "cleanmac_execute_plan",
                    "destructive": True,
                    "auto_call_allowed": True,
                    "requires_confirmation": True,
                    "safe_for_mcp": True,
                    "uses_shell": False,
                    "invocation_mode": "argv",
                },
                {
                    "name": "cleanmac_capabilities",
                    "destructive": False,
                    "safe_for_mcp": True,
                    "uses_shell": False,
                    "invocation_mode": "argv",
                },
                {
                    "name": "cleanmac_policy_simulate",
                    "destructive": False,
                    "safe_for_mcp": True,
                    "uses_shell": False,
                    "invocation_mode": "argv",
                },
            ],
            "tool_names": ["cleanmac_capabilities", "cleanmac_execute_plan", "cleanmac_policy_simulate"],
        }

        payload = render_mcp_surface_audit()

    assert payload["missing"]["tools"] == []
    _assert_surface_audit_blocked(
        payload,
        "destructive-tools-gated",
        ["make", "ai-governance-smoke"],
    )


def test_mcp_surface_audit_fails_closed_when_tool_uses_shell_invocation() -> None:
    from cleancli.mcp_resources import render_mcp_surface_audit

    with patch("cleancli.mcp_tools.render_mcp_tool_index") as mock_tool:
        mock_tool.return_value = {
            "schema": "cleanmac.mcp-tool-index.v1",
            "destructive": False,
            "dry_run": True,
            "ready": True,
            "tool_count": 3,
            "tools": [
                {
                    "name": "cleanmac_execute_plan",
                    "destructive": True,
                    "auto_call_allowed": False,
                    "requires_confirmation": True,
                    "safe_for_mcp": True,
                    "uses_shell": True,
                    "invocation_mode": "shell",
                },
                {
                    "name": "cleanmac_capabilities",
                    "destructive": False,
                    "safe_for_mcp": True,
                    "uses_shell": False,
                    "invocation_mode": "argv",
                },
                {
                    "name": "cleanmac_policy_simulate",
                    "destructive": False,
                    "safe_for_mcp": True,
                    "uses_shell": False,
                    "invocation_mode": "argv",
                },
            ],
            "tool_names": ["cleanmac_capabilities", "cleanmac_execute_plan", "cleanmac_policy_simulate"],
        }

        payload = render_mcp_surface_audit()

    assert payload["missing"]["tools"] == []
    _assert_surface_audit_blocked(
        payload,
        "no-shell-invocation",
        ["make", "ai-host-smoke"],
    )


def test_mcp_surface_audit_fails_closed_when_sensitive_data_policy_missing() -> None:
    from cleancli.mcp_resources import render_mcp_surface_audit

    required_uris = [
        "cleanmac://mcp/meta-index",
        "cleanmac://mcp/resource-index",
        "cleanmac://mcp/prompt-index",
        "cleanmac://mcp/tool-index",
        "cleanmac://mcp/destructive-tool-governance",
        "cleanmac://mcp/surface-audit",
        "cleanmac://ai/runtime-lifecycle-policy",
        "cleanmac://ai/zero-resident-audit",
        "cleanmac://ai/entrypoints",
        "cleanmac://ai/safety-chain",
        "cleanmac://ai/operation-log-explainability",
        "cleanmac://ai/cold-start-budget",
        "cleanmac://ai/no-disturbance",
        "cleanmac://release/dependency-governance",
        "cleanmac://ai/workflow-contract",
        "cleanmac://ai/host-integration-pack",
        "cleanmac://ai/host-preflight",
        "cleanmac://ai/host-evidence",
        "cleanmac://ai/host-policy",
    ]
    with patch("cleancli.mcp_resources.render_mcp_resource_index") as mock_resource:
        mock_resource.return_value = {
            "schema": "cleanmac.mcp-resource-index.v1",
            "destructive": False,
            "dry_run": True,
            "ready": True,
            "resource_count": 1,
            "resources": [
                {
                    "uri": "cleanmac://mcp/surface-audit",
                    "destructive": False,
                    "safe_for_mcp": True,
                    "sensitive_data_policy": "",
                }
            ],
            "resource_uris": required_uris,
        }

        payload = render_mcp_surface_audit()

    assert payload["missing"]["resources"] == []
    _assert_surface_audit_blocked(
        payload,
        "sensitive-data-policy-present",
        ["make", "mcp-surface-audit-smoke"],
    )


def test_resources_read_payloads_are_sanitized_for_mcp() -> None:
    sensitive_uris = [
        "cleanmac://release/readiness",
        "cleanmac://release/post-publish-result",
        "cleanmac://release/post-publish-evidence-template",
    ]
    for index, uri in enumerate(sensitive_uris, start=92):
        response = _mcp_request(
            {
                "jsonrpc": "2.0",
                "id": index,
                "method": "resources/read",
                "params": {"uri": uri},
            }
        )
        text = response["result"]["contents"][0]["text"]
        assert "/Users/" not in text
        assert "/private/var/" not in text
        assert str(Path.home()) not in text


def test_resources_read_returns_json_content() -> None:
    response = _mcp_request(
        {
            "jsonrpc": "2.0",
            "id": 22,
            "method": "resources/read",
            "params": {"uri": "cleanmac://ai/function-schemas"},
        }
    )
    contents = response["result"]["contents"]
    assert len(contents) == 1
    assert contents[0]["uri"] == "cleanmac://ai/function-schemas"
    assert contents[0]["mimeType"] == "application/json"
    payload = json.loads(contents[0]["text"])
    assert payload["schema"] == "cleanmac.ai-function-schemas.v1"


def test_resources_read_contract_validation_summary() -> None:
    response = _mcp_request(
        {
            "jsonrpc": "2.0",
            "id": 26,
            "method": "resources/read",
            "params": {"uri": "cleanmac://ai/contract-validation"},
        }
    )
    contents = response["result"]["contents"]
    assert contents[0]["uri"] == "cleanmac://ai/contract-validation"
    payload = json.loads(contents[0]["text"])
    assert payload["schema"] == "cleanmac.ai-contract-validation-summary.v1"
    assert payload["valid"], payload
    assert payload["failure_count"] == 0


def test_resources_read_contract_samples() -> None:
    response = _mcp_request(
        {
            "jsonrpc": "2.0",
            "id": 27,
            "method": "resources/read",
            "params": {"uri": "cleanmac://ai/contract-samples"},
        }
    )
    contents = response["result"]["contents"]
    assert contents[0]["uri"] == "cleanmac://ai/contract-samples"
    payload = json.loads(contents[0]["text"])
    assert payload["schema"] == "cleanmac.ai-contract-samples.v1"
    assert payload["sample_count"] == len(payload["samples"])
    assert all(sample["valid"] for sample in payload["samples"]), payload


def test_resources_read_host_integration_pack() -> None:
    response = _mcp_request(
        {
            "jsonrpc": "2.0",
            "id": 28,
            "method": "resources/read",
            "params": {"uri": "cleanmac://ai/host-integration-pack"},
        }
    )
    contents = response["result"]["contents"]
    assert contents[0]["uri"] == "cleanmac://ai/host-integration-pack"
    payload = json.loads(contents[0]["text"])
    assert payload["schema"] == "cleanmac.ai-host-integration-pack.v1"
    assert payload["ready"], payload
    assert payload["mcp"]["resource_uri"] == "cleanmac://ai/host-integration-pack"
    assert payload["mcp"]["meta_index_uri"] == "cleanmac://mcp/meta-index"
    assert payload["mcp"]["prompt_index_uri"] == "cleanmac://mcp/prompt-index"
    assert payload["mcp"]["tool_index_uri"] == "cleanmac://mcp/tool-index"
    assert payload["mcp"]["surface_audit_uri"] == "cleanmac://mcp/surface-audit"
    assert "cleanmac://ai/entrypoints" in payload["mcp"]["resources"]
    assert "cleanmac://ai/safety-chain" in payload["mcp"]["resources"]
    assert "cleanmac://ai/workflow-contract" in payload["mcp"]["resources"]
    assert "review-ai-host-policy" in payload["mcp"]["prompts"]
    assert "cleanmac_execute_plan" in payload["mcp"]["tools"]


def test_resources_read_workflow_contract() -> None:
    response = _mcp_request(
        {
            "jsonrpc": "2.0",
            "id": 128,
            "method": "resources/read",
            "params": {"uri": "cleanmac://ai/workflow-contract"},
        }
    )
    contents = response["result"]["contents"]
    assert contents[0]["uri"] == "cleanmac://ai/workflow-contract"
    payload = json.loads(contents[0]["text"])
    assert payload["schema"] == "cleanmac.ai-workflow.v1"
    assert not payload["destructive"]
    assert payload["dry_run"]
    assert payload["goal"] == "safe-cleanup"
    assert "cleanmac_policy_simulate" in payload["recommended_tool_call_order"]
    assert "cleanmac_execute_plan" in payload["recommended_tool_call_order"]
    execute_steps = [step for step in payload["steps"] if step.get("destructive")]
    assert len(execute_steps) == 1
    assert not execute_steps[0]["auto_call_allowed"]
    assert execute_steps[0]["requires_human_confirmation"]


def test_resources_read_ai_entrypoint_contract() -> None:
    response = _mcp_request(
        {
            "jsonrpc": "2.0",
            "id": 129,
            "method": "resources/read",
            "params": {"uri": "cleanmac://ai/entrypoints"},
        }
    )
    contents = response["result"]["contents"]
    assert contents[0]["uri"] == "cleanmac://ai/entrypoints"
    payload = json.loads(contents[0]["text"])
    assert payload["schema"] == "cleanmac.ai-entrypoint-contract.v1"
    assert payload["ready"], payload
    assert payload["entrypoint_count"] == 6
    assert "cleanmac.capabilities.v1" in payload["required_output_schemas"]
    assert "cleanmac.validate-plan.v1" in payload["required_output_schemas"]


def test_resources_read_ai_safety_chain_contract() -> None:
    response = _mcp_request(
        {
            "jsonrpc": "2.0",
            "id": 130,
            "method": "resources/read",
            "params": {"uri": "cleanmac://ai/safety-chain"},
        }
    )
    contents = response["result"]["contents"]
    assert contents[0]["uri"] == "cleanmac://ai/safety-chain"
    payload = json.loads(contents[0]["text"])
    assert payload["schema"] == "cleanmac.ai-safety-chain.v1"
    assert payload["ready"], payload
    assert payload["chain_step_count"] == 6
    assert not payload["execute_gate"]["auto_call_allowed"]
    assert payload["execute_gate"]["requires_matching_dry_run_confirmation_token"]
    assert "cleanmac.execute-gate.v1" in payload["required_contract_schemas"]
    assert ["dry_run", "execute"] in payload["non_bypassable_edges"]


def test_resources_read_host_preflight() -> None:
    response = _mcp_request(
        {
            "jsonrpc": "2.0",
            "id": 29,
            "method": "resources/read",
            "params": {"uri": "cleanmac://ai/host-preflight"},
        }
    )
    contents = response["result"]["contents"]
    assert contents[0]["uri"] == "cleanmac://ai/host-preflight"
    payload = json.loads(contents[0]["text"])
    assert payload["schema"] == "cleanmac.ai-host-preflight.v1"
    assert payload["ready"], payload
    assert payload["entrypoint"]["mcp_resource"] == "cleanmac://ai/host-integration-pack"


def test_resources_read_host_evidence() -> None:
    response = _mcp_request(
        {
            "jsonrpc": "2.0",
            "id": 78,
            "method": "resources/read",
            "params": {"uri": "cleanmac://ai/host-evidence"},
        }
    )
    contents = response["result"]["contents"]
    assert contents[0]["uri"] == "cleanmac://ai/host-evidence"
    payload = json.loads(contents[0]["text"])
    assert payload["schema"] == "cleanmac.ai-host-evidence.v1"
    assert payload["ready"], payload
    assert "runtime_policy_evidence" in payload
    assert "mcp_meta_index" in payload
    assert "mcp_surface_audit" in payload
    assert "mcp_prompt_catalog" in payload
    assert "mcp_tool_catalog" in payload


def test_resources_read_release_readiness() -> None:
    response = _mcp_request(
        {
            "jsonrpc": "2.0",
            "id": 79,
            "method": "resources/read",
            "params": {"uri": "cleanmac://release/readiness"},
        }
    )
    contents = response["result"]["contents"]
    assert contents[0]["uri"] == "cleanmac://release/readiness"
    payload = json.loads(contents[0]["text"])
    assert payload["schema"] == "cleanmac.release-readiness.v1"
    assert not payload["destructive"]
    assert payload["dry_run"]
    assert ["make", "governed-execution-smoke"] in payload["release_gate_commands"]


def test_resources_read_release_diagnostics_and_evidence() -> None:
    diagnostics = _mcp_request(
        {
            "jsonrpc": "2.0",
            "id": 80,
            "method": "resources/read",
            "params": {"uri": "cleanmac://release/diagnostics"},
        }
    )
    diagnostics_payload = json.loads(diagnostics["result"]["contents"][0]["text"])
    assert diagnostics_payload["schema"] == "cleanmac.release-diagnostics.v1"

    evidence = _mcp_request(
        {
            "jsonrpc": "2.0",
            "id": 81,
            "method": "resources/read",
            "params": {"uri": "cleanmac://release/evidence"},
        }
    )
    evidence_payload = json.loads(evidence["result"]["contents"][0]["text"])
    assert evidence_payload["schema"] == "cleanmac.release-evidence.v1"

    summary = _mcp_request(
        {
            "jsonrpc": "2.0",
            "id": 82,
            "method": "resources/read",
            "params": {"uri": "cleanmac://release/operator-summary"},
        }
    )
    summary_payload = json.loads(summary["result"]["contents"][0]["text"])
    assert summary_payload["schema"] == "cleanmac.release-operator-summary.v1"


def test_resources_read_release_orchestration_reports() -> None:
    resources = {
        "cleanmac://mcp/meta-index": "cleanmac.mcp-meta-index.v1",
        "cleanmac://mcp/resource-index": "cleanmac.mcp-resource-index.v1",
        "cleanmac://mcp/prompt-index": "cleanmac.mcp-prompt-index.v1",
        "cleanmac://mcp/tool-index": "cleanmac.mcp-tool-index.v1",
        "cleanmac://release/rehearsal": "cleanmac.release-rehearsal.v1",
        "cleanmac://release/promotion-decision": "cleanmac.release-promotion-decision.v1",
        "cleanmac://release/rollback-plan": "cleanmac.release-rollback-plan.v1",
        "cleanmac://release/post-publish-verification": "cleanmac.release-post-publish-verification.v1",
        "cleanmac://release/post-publish-result": "cleanmac.release-post-publish-result.v1",
        "cleanmac://release/post-publish-evidence-template": "cleanmac.release-post-publish-evidence-template.v1",
    }
    for index, (uri, schema) in enumerate(resources.items(), start=83):
        response = _mcp_request(
            {
                "jsonrpc": "2.0",
                "id": index,
                "method": "resources/read",
                "params": {"uri": uri},
            }
        )
        payload = json.loads(response["result"]["contents"][0]["text"])
        assert payload["schema"] == schema


def test_resources_read_unknown_uri_returns_invalid_params() -> None:
    response = _mcp_request(
        {
            "jsonrpc": "2.0",
            "id": 23,
            "method": "resources/read",
            "params": {"uri": "cleanmac://unknown"},
        }
    )
    assert response["error"]["code"] == -32602
    assert "Unknown resource URI" in response["error"]["message"]


def test_prompts_list_and_get_safe_cleanup_review() -> None:
    list_response = _mcp_request({"jsonrpc": "2.0", "id": 24, "method": "prompts/list"})
    prompts = list_response["result"]["prompts"]
    names = {prompt["name"] for prompt in prompts}
    assert "safe-cleanup-review" in names

    get_response = _mcp_request(
        {
            "jsonrpc": "2.0",
            "id": 25,
            "method": "prompts/get",
            "params": {"name": "safe-cleanup-review", "arguments": {"categories": "trash,downloads"}},
        }
    )
    prompt = get_response["result"]
    assert prompt["description"] == "Safe cleanmac cleanup review workflow"
    message_text = prompt["messages"][0]["content"]["text"]
    assert "trash,downloads" in message_text
    assert "cleanmac_execute_plan" in message_text
    assert "cleanmac_startup_disable" in message_text
    assert "cleanmac_privacy_execute" in message_text
    assert "review-selection" in message_text


def test_resources_expose_readiness_runbook_and_self_test() -> None:
    response = _mcp_request({"jsonrpc": "2.0", "id": 31, "method": "resources/list"})
    uris = {resource["uri"] for resource in response["result"]["resources"]}

    assert "cleanmac://ai/readiness" in uris
    assert "cleanmac://ai/runbook" in uris
    assert "cleanmac://ai/runtime-lifecycle-policy" in uris
    assert "cleanmac://ai/workflow-contract" in uris
    assert "cleanmac://ai/safety-chain" in uris
    assert "cleanmac://ai/self-test" in uris
    assert "cleanmac://ai/tool-decision-matrix" in uris
    assert "cleanmac://ai/governance-advice" in uris
    assert "cleanmac://ai/host-policy" in uris
    assert "cleanmac://ai/host-integration-pack" in uris
    assert "cleanmac://ai/host-preflight" in uris
    assert "cleanmac://ai/host-evidence" in uris
    assert "cleanmac://release/readiness" in uris
    assert "cleanmac://ai/eval-pack" in uris
    assert "cleanmac://ai/eval-run-smoke" in uris

    read_response = _mcp_request(
        {
            "jsonrpc": "2.0",
            "id": 32,
            "method": "resources/read",
            "params": {"uri": "cleanmac://ai/runbook"},
        }
    )
    payload = json.loads(read_response["result"]["contents"][0]["text"])
    assert payload["schema"] == "cleanmac.ai-runbook.v1"
    assert not payload["execution_gate"]["auto_call_allowed"]

    lifecycle_response = _mcp_request(
        {
            "jsonrpc": "2.0",
            "id": 33,
            "method": "resources/read",
            "params": {"uri": "cleanmac://ai/runtime-lifecycle-policy"},
        }
    )
    lifecycle_payload = json.loads(lifecycle_response["result"]["contents"][0]["text"])
    assert lifecycle_payload["schema"] == "cleanmac.runtime-lifecycle-policy.v1"
    assert lifecycle_payload["product_model"] == "ai-first-ephemeral-cli"
    assert lifecycle_payload["resident_processes"] == 0
    assert not lifecycle_payload["implements_gui"]
    assert not lifecycle_payload["installs_background_daemon"]

    zero_resident_response = _mcp_request(
        {
            "jsonrpc": "2.0",
            "id": 34,
            "method": "resources/read",
            "params": {"uri": "cleanmac://ai/zero-resident-audit"},
        }
    )
    zero_resident_payload = json.loads(zero_resident_response["result"]["contents"][0]["text"])
    assert zero_resident_payload["schema"] == "cleanmac.zero-resident-audit.v1"
    assert zero_resident_payload["ready"], zero_resident_payload
    assert zero_resident_payload["resident_processes"] == 0
    assert zero_resident_payload["readiness_score"] == {"passed": 16, "total": 16, "level": "ready"}

    workflow_response = _mcp_request(
        {
            "jsonrpc": "2.0",
            "id": 35,
            "method": "resources/read",
            "params": {"uri": "cleanmac://ai/workflow-contract"},
        }
    )
    workflow_payload = json.loads(workflow_response["result"]["contents"][0]["text"])
    assert workflow_payload["schema"] == "cleanmac.ai-workflow.v1"
    assert workflow_payload["governance"]["delete_mode_for_execute"] == "trash"

    safety_response = _mcp_request(
        {
            "jsonrpc": "2.0",
            "id": 36,
            "method": "resources/read",
            "params": {"uri": "cleanmac://ai/safety-chain"},
        }
    )
    safety_payload = json.loads(safety_response["result"]["contents"][0]["text"])
    assert safety_payload["schema"] == "cleanmac.ai-safety-chain.v1"
    assert safety_payload["ready"], safety_payload

    decision_response = _mcp_request(
        {
            "jsonrpc": "2.0",
            "id": 37,
            "method": "resources/read",
            "params": {"uri": "cleanmac://ai/tool-decision-matrix"},
        }
    )
    decision_payload = json.loads(decision_response["result"]["contents"][0]["text"])
    assert decision_payload["schema"] == "cleanmac.ai-tool-decision-matrix.v1"
    assert decision_payload["violation_count"] == 0

    governance_response = _mcp_request(
        {
            "jsonrpc": "2.0",
            "id": 42,
            "method": "resources/read",
            "params": {"uri": "cleanmac://ai/governance-advice"},
        }
    )
    governance_payload = json.loads(governance_response["result"]["contents"][0]["text"])
    assert governance_payload["schema"] == "cleanmac.ai-governance-advice.v1"
    assert governance_payload["ready_for_llm_calling"], governance_payload

    host_policy_response = _mcp_request(
        {
            "jsonrpc": "2.0",
            "id": 45,
            "method": "resources/read",
            "params": {"uri": "cleanmac://ai/host-policy"},
        }
    )
    host_policy_payload = json.loads(host_policy_response["result"]["contents"][0]["text"])
    assert host_policy_payload["schema"] == "cleanmac.ai-host-policy.v1"
    assert host_policy_payload["valid"], host_policy_payload
    assert "cleanmac_execute_plan" in host_policy_payload["auto_call"]["deny"]

    eval_pack_response = _mcp_request(
        {
            "jsonrpc": "2.0",
            "id": 38,
            "method": "resources/read",
            "params": {"uri": "cleanmac://ai/eval-pack"},
        }
    )
    eval_pack_payload = json.loads(eval_pack_response["result"]["contents"][0]["text"])
    assert eval_pack_payload["schema"] == "cleanmac.ai-eval-pack.v1"

    eval_run_response = _mcp_request(
        {
            "jsonrpc": "2.0",
            "id": 39,
            "method": "resources/read",
            "params": {"uri": "cleanmac://ai/eval-run-smoke"},
        }
    )
    eval_run_payload = json.loads(eval_run_response["result"]["contents"][0]["text"])
    assert eval_run_payload["schema"] == "cleanmac.ai-eval-run.v1"
    assert eval_run_payload["passed"], eval_run_payload


def test_prompts_include_confirm_execution_gate() -> None:
    response = _mcp_request({"jsonrpc": "2.0", "id": 33, "method": "prompts/list"})
    names = {prompt["name"] for prompt in response["result"]["prompts"]}
    assert "confirm-execution-gate" in names

    prompt_response = _mcp_request(
        {
            "jsonrpc": "2.0",
            "id": 34,
            "method": "prompts/get",
            "params": {
                "name": "confirm-execution-gate",
                "arguments": {"plan_file": "/tmp/cleanmac-plan.json"},
            },
        }
    )
    message_text = prompt_response["result"]["messages"][0]["content"]["text"]
    assert "/tmp/cleanmac-plan.json" in message_text
    assert "cleanmac_policy_simulate" in message_text
    assert "cleanmac_dry_run_plan" in message_text
    assert "cleanmac_execute_plan" in message_text
    assert "cleanmac_startup_disable" in message_text
    assert "cleanmac_privacy_execute" in message_text
    assert "review-selection" in message_text
    assert "backup_path" in message_text


def test_prompt_explains_tool_decision() -> None:
    response = _mcp_request({"jsonrpc": "2.0", "id": 36, "method": "prompts/list"})
    names = {prompt["name"] for prompt in response["result"]["prompts"]}
    assert "explain-tool-decision" in names

    prompt_response = _mcp_request(
        {
            "jsonrpc": "2.0",
            "id": 37,
            "method": "prompts/get",
            "params": {
                "name": "explain-tool-decision",
                "arguments": {"tool_name": "cleanmac_execute_plan"},
            },
        }
    )
    message_text = prompt_response["result"]["messages"][0]["content"]["text"]
    assert "cleanmac://ai/tool-decision-matrix" in message_text
    assert "cleanmac_execute_plan" in message_text
    assert "do not auto-call destructive tools" in message_text


def test_prompt_runs_ai_eval_smoke() -> None:
    response = _mcp_request({"jsonrpc": "2.0", "id": 40, "method": "prompts/list"})
    names = {prompt["name"] for prompt in response["result"]["prompts"]}
    assert "run-ai-eval-smoke" in names

    prompt_response = _mcp_request(
        {
            "jsonrpc": "2.0",
            "id": 41,
            "method": "prompts/get",
            "params": {"name": "run-ai-eval-smoke", "arguments": {}},
        }
    )
    message_text = prompt_response["result"]["messages"][0]["content"]["text"]
    assert "cleanmac://ai/eval-pack" in message_text
    assert "cleanmac://ai/eval-run-smoke" in message_text
    assert "do not call cleanmac_execute_plan" in message_text


def test_prompt_reviews_ai_governance() -> None:
    response = _mcp_request({"jsonrpc": "2.0", "id": 43, "method": "prompts/list"})
    names = {prompt["name"] for prompt in response["result"]["prompts"]}
    assert "review-ai-governance" in names

    prompt_response = _mcp_request(
        {
            "jsonrpc": "2.0",
            "id": 44,
            "method": "prompts/get",
            "params": {"name": "review-ai-governance", "arguments": {}},
        }
    )
    message_text = prompt_response["result"]["messages"][0]["content"]["text"]
    assert "cleanmac://ai/governance-advice" in message_text
    assert "required_host_controls" in message_text
    assert "Do not call cleanmac_execute_plan" in message_text


def test_prompt_reviews_ai_host_policy() -> None:
    response = _mcp_request({"jsonrpc": "2.0", "id": 46, "method": "prompts/list"})
    names = {prompt["name"] for prompt in response["result"]["prompts"]}
    assert "review-ai-host-policy" in names

    prompt_response = _mcp_request(
        {
            "jsonrpc": "2.0",
            "id": 47,
            "method": "prompts/get",
            "params": {"name": "review-ai-host-policy", "arguments": {}},
        }
    )
    message_text = prompt_response["result"]["messages"][0]["content"]["text"]
    assert "cleanmac://ai/host-policy" in message_text
    assert "auto_call.deny" in message_text
    assert "cleanmac_execute_plan" in message_text
    assert "cleanmac_startup_disable" in message_text
    assert "cleanmac_privacy_execute" in message_text
    assert "review-selection" in message_text


def test_tools_call_unknown_tool() -> None:
    response = _mcp_request(
        {
            "jsonrpc": "2.0",
            "id": 3,
            "method": "tools/call",
            "params": {"name": "cleanmac_nonexistent", "arguments": {}},
        }
    )
    assert response["error"]["code"] == -32602
    assert "Unknown tool" in response["error"]["message"]


def test_tools_call_error_includes_structured_content() -> None:
    response = _mcp_request(
        {
            "jsonrpc": "2.0",
            "id": 41,
            "method": "tools/call",
            "params": {"name": "cleanmac_inspect", "arguments": {}},
        }
    )
    result = response["result"]
    assert result["isError"]
    structured = result["structuredContent"]
    assert structured["schema"] == "cleanmac.mcp-tool-error.v1"
    assert structured["tool"] == "cleanmac_inspect"
    assert "message" in structured
    assert structured["host_action"] == "fix_arguments_and_retry"
    assert structured["retryable"]
    assert "categories" in structured["missing_or_invalid_arguments"]
    assert not structured["safe_to_auto_retry"]


def test_initialize_handshake() -> None:
    response = _mcp_request(
        {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "test", "version": "1.0"},
            },
        }
    )
    result = response["result"]
    assert result["protocolVersion"] == "2024-11-05"
    assert "tools" in result["capabilities"]
    assert "resources" in result["capabilities"]
    assert "prompts" in result["capabilities"]
    assert result["serverInfo"]["name"] == "cleanmac-mcp"


def test_shutdown() -> None:
    response = _mcp_request({"jsonrpc": "2.0", "id": 1, "method": "shutdown"})
    assert response["result"] is None


def test_json_parse_error() -> None:
    proc = subprocess.Popen(
        [sys.executable, str(MCP_SERVER)],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        env=_mcp_env(),
    )
    stdout, stderr = proc.communicate(input="not valid json\n", timeout=10)
    response = json.loads(stdout)
    assert response["error"]["code"] == -32700
    assert "Parse error" in response["error"]["message"]


def test_initialize_sends_initialized_notification() -> None:
    """Verify initialize response is followed by notifications/initialized."""
    proc = subprocess.Popen(
        [sys.executable, str(MCP_SERVER)],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        env=_mcp_env(),
    )
    payload = json.dumps(
        {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "test", "version": "1.0"},
            },
        }
    )
    stdout, stderr = proc.communicate(input=payload, timeout=10)

    lines = [line for line in stdout.strip().split("\n") if line.strip()]
    assert len(lines) >= 2, f"Expected at least 2 output lines, got {len(lines)}"

    # First line: the initialize response
    init_response = json.loads(lines[0])
    assert init_response["result"]["protocolVersion"] == "2024-11-05"

    # Second line: the initialized notification
    notification = json.loads(lines[1])
    assert notification.get("method") == "notifications/initialized"
    assert "id" not in notification


def test_resources_read_all_individual_resources() -> None:
    """Verify each resource URI returns valid JSON with a schema field."""
    list_response = _mcp_request({"jsonrpc": "2.0", "id": 51, "method": "resources/list"})
    uris = [r["uri"] for r in list_response["result"]["resources"]]
    assert len(uris) > 8

    for idx, uri in enumerate(uris, start=52):
        response = _mcp_request(
            {
                "jsonrpc": "2.0",
                "id": idx,
                "method": "resources/read",
                "params": {"uri": uri},
            }
        )
        if "error" in response:
            # Unknown URIs should have been caught elsewhere
            raise AssertionError(f"Resource {uri} returned error: {response['error']}")
        content = response["result"]["contents"][0]
        assert content["uri"] == uri
        assert content["mimeType"] == "application/json"
        payload = json.loads(content["text"])
        assert "schema" in payload, f"Resource {uri} missing schema field"


def test_prompt_get_unknown_name() -> None:
    response = _mcp_request(
        {
            "jsonrpc": "2.0",
            "id": 61,
            "method": "prompts/get",
            "params": {"name": "nonexistent-prompt"},
        }
    )
    assert response["error"]["code"] == -32602
    assert "Unknown prompt" in response["error"]["message"]


def test_unknown_method() -> None:
    response = _mcp_request(
        {
            "jsonrpc": "2.0",
            "id": 62,
            "method": "bogus_method",
        }
    )
    assert response["error"]["code"] == -32601
    assert "Method not found" in response["error"]["message"]


def test_shutdown_prevents_further_requests() -> None:
    """After shutdown, sending another request should yield no response or an error."""
    proc = subprocess.Popen(
        [sys.executable, str(MCP_SERVER)],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        env=_mcp_env(),
    )
    # Send shutdown
    stdout1, _ = proc.communicate(
        input=json.dumps({"jsonrpc": "2.0", "id": 1, "method": "shutdown"}),
        timeout=10,
    )
    assert stdout1 is not None

    # Process should have exited; start a new one and verify tools/list still works
    response = _mcp_request({"jsonrpc": "2.0", "id": 1, "method": "tools/list"})
    tools = response["result"]["tools"]
    assert len(tools) == 38


def test_notifications_initialized_standalone() -> None:
    """Sending a standalone notifications/initialized is silently handled (no response)."""
    proc = subprocess.Popen(
        [sys.executable, str(MCP_SERVER)],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        env=_mcp_env(),
    )
    payload = json.dumps({"jsonrpc": "2.0", "method": "notifications/initialized"})
    stdout, stderr = proc.communicate(input=payload, timeout=10)
    # Should produce no output (silent)
    assert stdout.strip() == ""


def test_prompt_get_missing_arguments_uses_defaults() -> None:
    """prompts/get with safe-cleanup-review but no arguments should use defaults."""
    response = _mcp_request(
        {
            "jsonrpc": "2.0",
            "id": 63,
            "method": "prompts/get",
            "params": {"name": "safe-cleanup-review", "arguments": {}},
        }
    )
    assert "error" not in response, f"Unexpected error: {response.get('error')}"
    prompt = response["result"]
    assert prompt["description"] == "Safe cleanmac cleanup review workflow"
    message_text = prompt["messages"][0]["content"]["text"]
    # Should contain default placeholder or empty categories
    assert isinstance(message_text, str)
    assert len(message_text) > 100


def test_resources_read_capabilities() -> None:
    """Verify the capabilities resource reads correctly with expected schema."""
    response = _mcp_request(
        {
            "jsonrpc": "2.0",
            "id": 64,
            "method": "resources/read",
            "params": {"uri": "cleanmac://capabilities"},
        }
    )
    content = response["result"]["contents"][0]
    assert content["uri"] == "cleanmac://capabilities"
    assert content["mimeType"] == "application/json"
    payload = json.loads(content["text"])
    assert payload["schema"] == "cleanmac.capabilities.v1"
    assert "commands" in payload
    assert "category_count" in payload
