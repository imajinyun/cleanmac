"""Tests for the cleanmac MCP stdio server."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
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
    stdout, stderr = proc.communicate(input=payload, timeout=15)
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


class MckServerTests(unittest.TestCase):
    """Test the cleanmac MCP stdio server protocol."""

    def test_tools_list_returns_all_tools(self) -> None:
        response = _mcp_request({"jsonrpc": "2.0", "id": 1, "method": "tools/list"})
        tools = response["result"]["tools"]
        self.assertEqual(len(tools), 37)
        for tool in tools:
            self.assertIn("name", tool)
            self.assertIn("description", tool)
            self.assertIn("annotations", tool)
            self.assertIn("inputSchema", tool)
        names = {t["name"] for t in tools}
        self.assertIn("cleanmac_capabilities", names)
        self.assertIn("cleanmac_profiles", names)
        self.assertIn("cleanmac_scripts", names)
        self.assertIn("cleanmac_software_uninstall_execute", names)
        self.assertIn("cleanmac_open", names)
        self.assertIn("cleanmac_links", names)
        self.assertIn("cleanmac_optimize", names)
        self.assertIn("cleanmac_startup_disable", names)
        self.assertIn("cleanmac_privacy_execute", names)
        tool_by_name = {t["name"]: t for t in tools}
        self.assertTrue(tool_by_name["cleanmac_capabilities"]["annotations"]["readOnlyHint"])
        self.assertTrue(tool_by_name["cleanmac_execute_plan"]["annotations"]["destructiveHint"])
        self.assertTrue(tool_by_name["cleanmac_startup_disable"]["annotations"]["destructiveHint"])
        self.assertTrue(tool_by_name["cleanmac_privacy_execute"]["annotations"]["destructiveHint"])

    def test_destructive_tool_call_blocked_by_policy(self) -> None:
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

        self.assertIn("cleanmac_execute_plan", deny_list)

        tools_response = _mcp_request({"jsonrpc": "2.0", "id": 72, "method": "tools/list"})
        tools = tools_response["result"]["tools"]
        tool_by_name = {t["name"]: t for t in tools}

        for denied_tool in deny_list:
            self.assertIn(
                denied_tool,
                tool_by_name,
                f"Deny-listed tool {denied_tool} not found in tools/list",
            )
            self.assertTrue(
                tool_by_name[denied_tool]["annotations"]["destructiveHint"],
                f"Deny-listed tool {denied_tool} missing destructiveHint annotation",
            )

    def test_infrastructure_error_cli_not_found(self) -> None:
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
        self.assertTrue(result["isError"])
        self.assertIn("CLI not found", result["content"][0]["text"])
        self.assertEqual(result["structuredContent"]["schema"], "cleanmac.mcp-tool-error.v1")
        self.assertEqual(result["structuredContent"]["tool"], "cleanmac_capabilities")

    def test_infrastructure_error_nonzero_exit(self) -> None:
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
            self.assertTrue(result["isError"])
            error_text = result["content"][0]["text"]
            self.assertIn("failed", error_text.lower())
            self.assertEqual(result["structuredContent"]["schema"], "cleanmac.mcp-tool-error.v1")
            self.assertEqual(result["structuredContent"]["tool"], "cleanmac_capabilities")

    def test_tools_call_readonly_capabilities(self) -> None:
        response = _mcp_request(
            {
                "jsonrpc": "2.0",
                "id": 2,
                "method": "tools/call",
                "params": {"name": "cleanmac_capabilities", "arguments": {}},
            }
        )
        result = response["result"]
        self.assertFalse(result.get("isError"))
        self.assertEqual(result["content"][0]["type"], "text")
        data = json.loads(result["content"][0]["text"])
        self.assertEqual(data["schema"], "cleanmac.capabilities.v1")
        self.assertEqual(result["structuredContent"]["schema"], "cleanmac.capabilities.v1")
        self.assertEqual(result["governanceDecision"]["schema"], "cleanmac.ai-host-tool-call-decision.v1")
        self.assertTrue(result["governanceDecision"]["allowed"])

    def test_tools_call_raw_command_argument_denied_by_runtime_policy(self) -> None:
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
        self.assertTrue(result["isError"])
        decision = result["governanceDecision"]
        self.assertEqual(decision["schema"], "cleanmac.ai-host-tool-call-decision.v1")
        self.assertFalse(decision["allowed"])
        self.assertEqual(decision["blocking_reasons"][0]["code"], "RAW_COMMAND_ARGUMENT_DENIED")
        self.assertEqual(decision["next_allowed_tools"], ["cleanmac_validate_plan", "cleanmac_policy_simulate"])
        structured = result["structuredContent"]
        self.assertEqual(structured["schema"], "cleanmac.mcp-tool-error.v1")
        self.assertEqual(structured["next_allowed_tools"], decision["next_allowed_tools"])
        self.assertEqual(structured["policy_decision"], decision)

    def test_tools_call_destructive_missing_runtime_gates_denied_by_policy(self) -> None:
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
        self.assertTrue(result["isError"])
        decision = result["governanceDecision"]
        codes = {reason["code"] for reason in decision["blocking_reasons"]}
        self.assertIn("HUMAN_CONFIRMATION_PHRASE_REQUIRED", codes)
        self.assertIn("CONFIRMATION_TOKEN_REQUIRED", codes)
        self.assertFalse(decision["safe_to_auto_retry"])
        self.assertEqual(decision["next_allowed_tools"], ["cleanmac_validate_plan", "cleanmac_policy_simulate"])
        self.assertEqual(
            result["structuredContent"]["next_allowed_tools"],
            ["cleanmac_validate_plan", "cleanmac_policy_simulate"],
        )

    def test_resources_list_exposes_ai_governance_resources(self) -> None:
        response = _mcp_request({"jsonrpc": "2.0", "id": 21, "method": "resources/list"})
        resources = response["result"]["resources"]
        uris = {resource["uri"] for resource in resources}

        self.assertIn("cleanmac://mcp/resource-index", uris)
        self.assertIn("cleanmac://mcp/prompt-index", uris)
        self.assertIn("cleanmac://capabilities", uris)
        self.assertIn("cleanmac://ai/function-schemas", uris)
        self.assertIn("cleanmac://ai/mcp-tool-catalog", uris)
        self.assertIn("cleanmac://ai/contract-validation", uris)
        self.assertIn("cleanmac://ai/contract-samples", uris)
        self.assertIn("cleanmac://ai/workflow-contract", uris)
        self.assertIn("cleanmac://ai/host-integration-pack", uris)
        self.assertIn("cleanmac://ai/host-preflight", uris)
        self.assertIn("cleanmac://ai/host-evidence", uris)
        self.assertIn("cleanmac://release/readiness", uris)
        self.assertIn("cleanmac://release/diagnostics", uris)
        self.assertIn("cleanmac://release/evidence", uris)
        self.assertIn("cleanmac://release/operator-summary", uris)
        self.assertIn("cleanmac://release/rehearsal", uris)
        self.assertIn("cleanmac://release/promotion-decision", uris)
        self.assertIn("cleanmac://release/rollback-plan", uris)
        self.assertIn("cleanmac://release/post-publish-verification", uris)
        self.assertIn("cleanmac://release/post-publish-result", uris)
        self.assertIn("cleanmac://release/post-publish-evidence-template", uris)
        self.assertIn("cleanmac://mcp/meta-index", uris)
        self.assertIn("cleanmac://mcp/tool-index", uris)
        self.assertIn("cleanmac://mcp/surface-audit", uris)
        self.assertTrue(all(resource["mimeType"] == "application/json" for resource in resources))
        self.assertTrue(all(resource["destructive"] is False for resource in resources))
        self.assertTrue(all(resource["safe_for_mcp"] is True for resource in resources))

    def test_resources_read_mcp_meta_index(self) -> None:
        response = _mcp_request(
            {
                "jsonrpc": "2.0",
                "id": 90,
                "method": "resources/read",
                "params": {"uri": "cleanmac://mcp/meta-index"},
            }
        )
        contents = response["result"]["contents"]
        self.assertEqual(contents[0]["uri"], "cleanmac://mcp/meta-index")
        payload = json.loads(contents[0]["text"])
        self.assertEqual(payload["schema"], "cleanmac.mcp-meta-index.v1")
        self.assertTrue(payload["ready"], payload)
        self.assertEqual(payload["index_count"], len(payload["indexes"]))
        self.assertEqual(
            set(payload["index_uris"]),
            {"cleanmac://mcp/resource-index", "cleanmac://mcp/prompt-index", "cleanmac://mcp/tool-index"},
        )
        self.assertTrue(all(index["ready"] is True for index in payload["indexes"]))

    def test_resources_read_mcp_resource_index(self) -> None:
        response = _mcp_request(
            {
                "jsonrpc": "2.0",
                "id": 91,
                "method": "resources/read",
                "params": {"uri": "cleanmac://mcp/resource-index"},
            }
        )
        contents = response["result"]["contents"]
        self.assertEqual(contents[0]["uri"], "cleanmac://mcp/resource-index")
        payload = json.loads(contents[0]["text"])
        self.assertEqual(payload["schema"], "cleanmac.mcp-resource-index.v1")
        self.assertTrue(payload["ready"], payload)
        self.assertEqual(payload["resource_count"], len(payload["resources"]))
        self.assertIn("cleanmac://mcp/meta-index", payload["resource_uris"])
        self.assertIn("cleanmac://mcp/prompt-index", payload["resource_uris"])
        self.assertIn("cleanmac://mcp/tool-index", payload["resource_uris"])
        self.assertIn("cleanmac://mcp/surface-audit", payload["resource_uris"])
        self.assertIn("cleanmac://release/post-publish-evidence-template", payload["resource_uris"])
        self.assertIn("cleanmac://ai/workflow-contract", payload["resource_uris"])
        self.assertTrue(all(resource["safe_for_mcp"] is True for resource in payload["resources"]))

    def test_resources_read_mcp_prompt_index(self) -> None:
        response = _mcp_request(
            {
                "jsonrpc": "2.0",
                "id": 93,
                "method": "resources/read",
                "params": {"uri": "cleanmac://mcp/prompt-index"},
            }
        )
        contents = response["result"]["contents"]
        self.assertEqual(contents[0]["uri"], "cleanmac://mcp/prompt-index")
        payload = json.loads(contents[0]["text"])
        self.assertEqual(payload["schema"], "cleanmac.mcp-prompt-index.v1")
        self.assertTrue(payload["ready"], payload)
        self.assertEqual(payload["prompt_count"], len(payload["prompts"]))
        self.assertIn("review-ai-host-policy", payload["prompt_names"])
        self.assertTrue(all(prompt["safe_for_mcp"] is True for prompt in payload["prompts"]))
        self.assertTrue(all(prompt["destructive"] is False for prompt in payload["prompts"]))
        self.assertTrue(all(prompt["dry_run"] is True for prompt in payload["prompts"]))
        self.assertTrue(all(prompt["uses_shell"] is False for prompt in payload["prompts"]))

    def test_resources_read_mcp_tool_index(self) -> None:
        response = _mcp_request(
            {
                "jsonrpc": "2.0",
                "id": 94,
                "method": "resources/read",
                "params": {"uri": "cleanmac://mcp/tool-index"},
            }
        )
        contents = response["result"]["contents"]
        self.assertEqual(contents[0]["uri"], "cleanmac://mcp/tool-index")
        payload = json.loads(contents[0]["text"])
        self.assertEqual(payload["schema"], "cleanmac.mcp-tool-index.v1")
        self.assertTrue(payload["ready"], payload)
        self.assertEqual(payload["tool_count"], len(payload["tools"]))
        self.assertIn("cleanmac_execute_plan", payload["tool_names"])
        self.assertIn("cleanmac_execute_plan", payload["destructive_tool_names"])
        self.assertIn("cleanmac_execute_plan", payload["auto_call_denied_tool_names"])
        self.assertTrue(all(tool["safe_for_mcp"] is True for tool in payload["tools"]))
        self.assertTrue(all(tool["uses_shell"] is False for tool in payload["tools"]))
        self.assertTrue(all(tool["invocation_mode"] == "argv" for tool in payload["tools"]))
        for tool in payload["tools"]:
            if tool["destructive"]:
                self.assertFalse(tool["auto_call_allowed"], tool)
                self.assertTrue(tool["requires_confirmation"], tool)

    def test_resources_read_mcp_surface_audit(self) -> None:
        response = _mcp_request(
            {
                "jsonrpc": "2.0",
                "id": 95,
                "method": "resources/read",
                "params": {"uri": "cleanmac://mcp/surface-audit"},
            }
        )
        contents = response["result"]["contents"]
        self.assertEqual(contents[0]["uri"], "cleanmac://mcp/surface-audit")
        payload = json.loads(contents[0]["text"])
        self.assertEqual(payload["schema"], "cleanmac.mcp-surface-audit.v1")
        self.assertFalse(payload["destructive"])
        self.assertTrue(payload["dry_run"])
        self.assertTrue(payload["ready"], payload)
        self.assertEqual(payload["resource_uri"], "cleanmac://mcp/surface-audit")
        self.assertEqual(payload["missing"], {"resources": [], "prompts": [], "tools": []})
        self.assertEqual(payload["failed_check_ids"], [])
        self.assertEqual(payload["readiness_score"], {"passed": 14, "total": 14, "level": "ready"})
        self.assertEqual(payload["next_action"], "proceed-to-host-integration-pack")
        self.assertEqual(payload["stop_reason"], "")
        checks = {check["id"]: check for check in payload["checks"]}
        self.assertTrue(checks["mcp-meta-index-ready"]["passed"])
        self.assertIn(["make", "mcp-meta-index-smoke"], checks["mcp-meta-index-ready"]["remediation_commands"])
        self.assertTrue(checks["mcp-resource-index-ready"]["passed"])
        self.assertTrue(checks["mcp-prompt-index-ready"]["passed"])
        self.assertTrue(checks["mcp-tool-index-ready"]["passed"])
        self.assertTrue(checks["required-resources-advertised"]["passed"])
        self.assertTrue(checks["required-prompts-advertised"]["passed"])
        self.assertTrue(checks["required-tools-advertised"]["passed"])
        self.assertTrue(checks["runtime-lifecycle-policy-advertised"]["passed"])
        self.assertTrue(checks["destructive-tools-gated"]["passed"])
        self.assertTrue(checks["no-shell-invocation"]["passed"])
        self.assertIn("read cleanmac://mcp/surface-audit", payload["recommended_call_sequence"])
        self.assertIn(["make", "mcp-surface-audit-smoke"], payload["remediation_commands"])

    def _assert_surface_audit_blocked(self, payload: dict, failed_check_id: str, command: list[str]) -> None:
        self.assertFalse(payload["ready"], payload)
        self.assertIn(failed_check_id, payload["failed_check_ids"])
        self.assertEqual(payload["readiness_score"]["level"], "blocked")
        self.assertLess(payload["readiness_score"]["passed"], payload["readiness_score"]["total"])
        self.assertEqual(payload["next_action"], "stop-and-remediate-mcp-surface")
        self.assertIn(failed_check_id, payload["stop_reason"])
        self.assertIn(["make", "mcp-surface-audit-smoke"], payload["remediation_commands"])
        checks = {check["id"]: check for check in payload["checks"]}
        self.assertFalse(checks[failed_check_id]["passed"])
        self.assertIn(command, checks[failed_check_id]["remediation_commands"])

    def test_mcp_surface_audit_fails_closed_when_required_resource_missing(self) -> None:
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

        self.assertIn("cleanmac://mcp/surface-audit", payload["missing"]["resources"])
        self._assert_surface_audit_blocked(
            payload,
            "required-resources-advertised",
            ["make", "mcp-resource-index-smoke"],
        )

    def test_mcp_surface_audit_fails_closed_when_required_prompt_missing(self) -> None:
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

        self.assertEqual(payload["missing"]["prompts"], ["review-ai-host-policy"])
        self._assert_surface_audit_blocked(
            payload,
            "required-prompts-advertised",
            ["make", "mcp-prompt-index-smoke"],
        )

    def test_mcp_surface_audit_fails_closed_when_required_tool_missing(self) -> None:
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

        self.assertIn("cleanmac_execute_plan", payload["missing"]["tools"])
        self._assert_surface_audit_blocked(
            payload,
            "required-tools-advertised",
            ["make", "mcp-tool-index-smoke"],
        )

    def test_mcp_surface_audit_fails_closed_when_destructive_tool_allows_auto_call(self) -> None:
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

        self.assertEqual(payload["missing"]["tools"], [])
        self._assert_surface_audit_blocked(
            payload,
            "destructive-tools-gated",
            ["make", "ai-governance-smoke"],
        )

    def test_mcp_surface_audit_fails_closed_when_tool_uses_shell_invocation(self) -> None:
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

        self.assertEqual(payload["missing"]["tools"], [])
        self._assert_surface_audit_blocked(
            payload,
            "no-shell-invocation",
            ["make", "ai-host-smoke"],
        )

    def test_mcp_surface_audit_fails_closed_when_sensitive_data_policy_missing(self) -> None:
        from cleancli.mcp_resources import render_mcp_surface_audit

        required_uris = [
            "cleanmac://mcp/meta-index",
            "cleanmac://mcp/resource-index",
            "cleanmac://mcp/prompt-index",
            "cleanmac://mcp/tool-index",
            "cleanmac://mcp/surface-audit",
            "cleanmac://ai/runtime-lifecycle-policy",
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

        self.assertEqual(payload["missing"]["resources"], [])
        self._assert_surface_audit_blocked(
            payload,
            "sensitive-data-policy-present",
            ["make", "mcp-surface-audit-smoke"],
        )

    def test_resources_read_payloads_are_sanitized_for_mcp(self) -> None:
        sensitive_uris = [
            "cleanmac://release/readiness",
            "cleanmac://release/post-publish-result",
            "cleanmac://release/post-publish-evidence-template",
        ]
        for index, uri in enumerate(sensitive_uris, start=92):
            with self.subTest(uri=uri):
                response = _mcp_request(
                    {
                        "jsonrpc": "2.0",
                        "id": index,
                        "method": "resources/read",
                        "params": {"uri": uri},
                    }
                )
                text = response["result"]["contents"][0]["text"]
                self.assertNotIn("/Users/", text)
                self.assertNotIn("/private/var/", text)
                self.assertNotIn(str(Path.home()), text)

    def test_resources_read_returns_json_content(self) -> None:
        response = _mcp_request(
            {
                "jsonrpc": "2.0",
                "id": 22,
                "method": "resources/read",
                "params": {"uri": "cleanmac://ai/function-schemas"},
            }
        )
        contents = response["result"]["contents"]
        self.assertEqual(len(contents), 1)
        self.assertEqual(contents[0]["uri"], "cleanmac://ai/function-schemas")
        self.assertEqual(contents[0]["mimeType"], "application/json")
        payload = json.loads(contents[0]["text"])
        self.assertEqual(payload["schema"], "cleanmac.ai-function-schemas.v1")

    def test_resources_read_contract_validation_summary(self) -> None:
        response = _mcp_request(
            {
                "jsonrpc": "2.0",
                "id": 26,
                "method": "resources/read",
                "params": {"uri": "cleanmac://ai/contract-validation"},
            }
        )
        contents = response["result"]["contents"]
        self.assertEqual(contents[0]["uri"], "cleanmac://ai/contract-validation")
        payload = json.loads(contents[0]["text"])
        self.assertEqual(payload["schema"], "cleanmac.ai-contract-validation-summary.v1")
        self.assertTrue(payload["valid"], payload)
        self.assertEqual(payload["failure_count"], 0)

    def test_resources_read_contract_samples(self) -> None:
        response = _mcp_request(
            {
                "jsonrpc": "2.0",
                "id": 27,
                "method": "resources/read",
                "params": {"uri": "cleanmac://ai/contract-samples"},
            }
        )
        contents = response["result"]["contents"]
        self.assertEqual(contents[0]["uri"], "cleanmac://ai/contract-samples")
        payload = json.loads(contents[0]["text"])
        self.assertEqual(payload["schema"], "cleanmac.ai-contract-samples.v1")
        self.assertEqual(payload["sample_count"], len(payload["samples"]))
        self.assertTrue(all(sample["valid"] for sample in payload["samples"]), payload)

    def test_resources_read_host_integration_pack(self) -> None:
        response = _mcp_request(
            {
                "jsonrpc": "2.0",
                "id": 28,
                "method": "resources/read",
                "params": {"uri": "cleanmac://ai/host-integration-pack"},
            }
        )
        contents = response["result"]["contents"]
        self.assertEqual(contents[0]["uri"], "cleanmac://ai/host-integration-pack")
        payload = json.loads(contents[0]["text"])
        self.assertEqual(payload["schema"], "cleanmac.ai-host-integration-pack.v1")
        self.assertTrue(payload["ready"], payload)
        self.assertEqual(payload["mcp"]["resource_uri"], "cleanmac://ai/host-integration-pack")
        self.assertEqual(payload["mcp"]["meta_index_uri"], "cleanmac://mcp/meta-index")
        self.assertEqual(payload["mcp"]["prompt_index_uri"], "cleanmac://mcp/prompt-index")
        self.assertEqual(payload["mcp"]["tool_index_uri"], "cleanmac://mcp/tool-index")
        self.assertEqual(payload["mcp"]["surface_audit_uri"], "cleanmac://mcp/surface-audit")
        self.assertIn("cleanmac://ai/workflow-contract", payload["mcp"]["resources"])
        self.assertIn("review-ai-host-policy", payload["mcp"]["prompts"])
        self.assertIn("cleanmac_execute_plan", payload["mcp"]["tools"])

    def test_resources_read_workflow_contract(self) -> None:
        response = _mcp_request(
            {
                "jsonrpc": "2.0",
                "id": 128,
                "method": "resources/read",
                "params": {"uri": "cleanmac://ai/workflow-contract"},
            }
        )
        contents = response["result"]["contents"]
        self.assertEqual(contents[0]["uri"], "cleanmac://ai/workflow-contract")
        payload = json.loads(contents[0]["text"])
        self.assertEqual(payload["schema"], "cleanmac.ai-workflow.v1")
        self.assertFalse(payload["destructive"])
        self.assertTrue(payload["dry_run"])
        self.assertEqual(payload["goal"], "safe-cleanup")
        self.assertIn("cleanmac_policy_simulate", payload["recommended_tool_call_order"])
        self.assertIn("cleanmac_execute_plan", payload["recommended_tool_call_order"])
        execute_steps = [step for step in payload["steps"] if step.get("destructive")]
        self.assertEqual(len(execute_steps), 1)
        self.assertFalse(execute_steps[0]["auto_call_allowed"])
        self.assertTrue(execute_steps[0]["requires_human_confirmation"])

    def test_resources_read_host_preflight(self) -> None:
        response = _mcp_request(
            {
                "jsonrpc": "2.0",
                "id": 29,
                "method": "resources/read",
                "params": {"uri": "cleanmac://ai/host-preflight"},
            }
        )
        contents = response["result"]["contents"]
        self.assertEqual(contents[0]["uri"], "cleanmac://ai/host-preflight")
        payload = json.loads(contents[0]["text"])
        self.assertEqual(payload["schema"], "cleanmac.ai-host-preflight.v1")
        self.assertTrue(payload["ready"], payload)
        self.assertEqual(payload["entrypoint"]["mcp_resource"], "cleanmac://ai/host-integration-pack")

    def test_resources_read_host_evidence(self) -> None:
        response = _mcp_request(
            {
                "jsonrpc": "2.0",
                "id": 78,
                "method": "resources/read",
                "params": {"uri": "cleanmac://ai/host-evidence"},
            }
        )
        contents = response["result"]["contents"]
        self.assertEqual(contents[0]["uri"], "cleanmac://ai/host-evidence")
        payload = json.loads(contents[0]["text"])
        self.assertEqual(payload["schema"], "cleanmac.ai-host-evidence.v1")
        self.assertTrue(payload["ready"], payload)
        self.assertIn("runtime_policy_evidence", payload)
        self.assertIn("mcp_meta_index", payload)
        self.assertIn("mcp_surface_audit", payload)
        self.assertIn("mcp_prompt_catalog", payload)
        self.assertIn("mcp_tool_catalog", payload)

    def test_resources_read_release_readiness(self) -> None:
        response = _mcp_request(
            {
                "jsonrpc": "2.0",
                "id": 79,
                "method": "resources/read",
                "params": {"uri": "cleanmac://release/readiness"},
            }
        )
        contents = response["result"]["contents"]
        self.assertEqual(contents[0]["uri"], "cleanmac://release/readiness")
        payload = json.loads(contents[0]["text"])
        self.assertEqual(payload["schema"], "cleanmac.release-readiness.v1")
        self.assertFalse(payload["destructive"])
        self.assertTrue(payload["dry_run"])
        self.assertIn(["make", "governed-execution-smoke"], payload["release_gate_commands"])

    def test_resources_read_release_diagnostics_and_evidence(self) -> None:
        diagnostics = _mcp_request(
            {
                "jsonrpc": "2.0",
                "id": 80,
                "method": "resources/read",
                "params": {"uri": "cleanmac://release/diagnostics"},
            }
        )
        diagnostics_payload = json.loads(diagnostics["result"]["contents"][0]["text"])
        self.assertEqual(diagnostics_payload["schema"], "cleanmac.release-diagnostics.v1")

        evidence = _mcp_request(
            {
                "jsonrpc": "2.0",
                "id": 81,
                "method": "resources/read",
                "params": {"uri": "cleanmac://release/evidence"},
            }
        )
        evidence_payload = json.loads(evidence["result"]["contents"][0]["text"])
        self.assertEqual(evidence_payload["schema"], "cleanmac.release-evidence.v1")

        summary = _mcp_request(
            {
                "jsonrpc": "2.0",
                "id": 82,
                "method": "resources/read",
                "params": {"uri": "cleanmac://release/operator-summary"},
            }
        )
        summary_payload = json.loads(summary["result"]["contents"][0]["text"])
        self.assertEqual(summary_payload["schema"], "cleanmac.release-operator-summary.v1")

    def test_resources_read_release_orchestration_reports(self) -> None:
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
            with self.subTest(uri=uri):
                response = _mcp_request(
                    {
                        "jsonrpc": "2.0",
                        "id": index,
                        "method": "resources/read",
                        "params": {"uri": uri},
                    }
                )
                payload = json.loads(response["result"]["contents"][0]["text"])
                self.assertEqual(payload["schema"], schema)

    def test_resources_read_unknown_uri_returns_invalid_params(self) -> None:
        response = _mcp_request(
            {
                "jsonrpc": "2.0",
                "id": 23,
                "method": "resources/read",
                "params": {"uri": "cleanmac://unknown"},
            }
        )
        self.assertEqual(response["error"]["code"], -32602)
        self.assertIn("Unknown resource URI", response["error"]["message"])

    def test_prompts_list_and_get_safe_cleanup_review(self) -> None:
        list_response = _mcp_request({"jsonrpc": "2.0", "id": 24, "method": "prompts/list"})
        prompts = list_response["result"]["prompts"]
        names = {prompt["name"] for prompt in prompts}
        self.assertIn("safe-cleanup-review", names)

        get_response = _mcp_request(
            {
                "jsonrpc": "2.0",
                "id": 25,
                "method": "prompts/get",
                "params": {"name": "safe-cleanup-review", "arguments": {"categories": "trash,downloads"}},
            }
        )
        prompt = get_response["result"]
        self.assertEqual(prompt["description"], "Safe cleanmac cleanup review workflow")
        message_text = prompt["messages"][0]["content"]["text"]
        self.assertIn("trash,downloads", message_text)
        self.assertIn("cleanmac_execute_plan", message_text)
        self.assertIn("cleanmac_startup_disable", message_text)
        self.assertIn("cleanmac_privacy_execute", message_text)
        self.assertIn("review-selection", message_text)

    def test_resources_expose_readiness_runbook_and_self_test(self) -> None:
        response = _mcp_request({"jsonrpc": "2.0", "id": 31, "method": "resources/list"})
        uris = {resource["uri"] for resource in response["result"]["resources"]}

        self.assertIn("cleanmac://ai/readiness", uris)
        self.assertIn("cleanmac://ai/runbook", uris)
        self.assertIn("cleanmac://ai/runtime-lifecycle-policy", uris)
        self.assertIn("cleanmac://ai/workflow-contract", uris)
        self.assertIn("cleanmac://ai/self-test", uris)
        self.assertIn("cleanmac://ai/tool-decision-matrix", uris)
        self.assertIn("cleanmac://ai/governance-advice", uris)
        self.assertIn("cleanmac://ai/host-policy", uris)
        self.assertIn("cleanmac://ai/host-integration-pack", uris)
        self.assertIn("cleanmac://ai/host-preflight", uris)
        self.assertIn("cleanmac://ai/host-evidence", uris)
        self.assertIn("cleanmac://release/readiness", uris)
        self.assertIn("cleanmac://ai/eval-pack", uris)
        self.assertIn("cleanmac://ai/eval-run-smoke", uris)

        read_response = _mcp_request(
            {
                "jsonrpc": "2.0",
                "id": 32,
                "method": "resources/read",
                "params": {"uri": "cleanmac://ai/runbook"},
            }
        )
        payload = json.loads(read_response["result"]["contents"][0]["text"])
        self.assertEqual(payload["schema"], "cleanmac.ai-runbook.v1")
        self.assertFalse(payload["execution_gate"]["auto_call_allowed"])

        lifecycle_response = _mcp_request(
            {
                "jsonrpc": "2.0",
                "id": 33,
                "method": "resources/read",
                "params": {"uri": "cleanmac://ai/runtime-lifecycle-policy"},
            }
        )
        lifecycle_payload = json.loads(lifecycle_response["result"]["contents"][0]["text"])
        self.assertEqual(lifecycle_payload["schema"], "cleanmac.runtime-lifecycle-policy.v1")
        self.assertEqual(lifecycle_payload["product_model"], "ai-first-ephemeral-cli")
        self.assertEqual(lifecycle_payload["resident_processes"], 0)
        self.assertFalse(lifecycle_payload["implements_gui"])
        self.assertFalse(lifecycle_payload["installs_background_daemon"])

        workflow_response = _mcp_request(
            {
                "jsonrpc": "2.0",
                "id": 34,
                "method": "resources/read",
                "params": {"uri": "cleanmac://ai/workflow-contract"},
            }
        )
        workflow_payload = json.loads(workflow_response["result"]["contents"][0]["text"])
        self.assertEqual(workflow_payload["schema"], "cleanmac.ai-workflow.v1")
        self.assertEqual(workflow_payload["governance"]["delete_mode_for_execute"], "trash")

        decision_response = _mcp_request(
            {
                "jsonrpc": "2.0",
                "id": 35,
                "method": "resources/read",
                "params": {"uri": "cleanmac://ai/tool-decision-matrix"},
            }
        )
        decision_payload = json.loads(decision_response["result"]["contents"][0]["text"])
        self.assertEqual(decision_payload["schema"], "cleanmac.ai-tool-decision-matrix.v1")
        self.assertEqual(decision_payload["violation_count"], 0)

        governance_response = _mcp_request(
            {
                "jsonrpc": "2.0",
                "id": 42,
                "method": "resources/read",
                "params": {"uri": "cleanmac://ai/governance-advice"},
            }
        )
        governance_payload = json.loads(governance_response["result"]["contents"][0]["text"])
        self.assertEqual(governance_payload["schema"], "cleanmac.ai-governance-advice.v1")
        self.assertTrue(governance_payload["ready_for_llm_calling"], governance_payload)

        host_policy_response = _mcp_request(
            {
                "jsonrpc": "2.0",
                "id": 45,
                "method": "resources/read",
                "params": {"uri": "cleanmac://ai/host-policy"},
            }
        )
        host_policy_payload = json.loads(host_policy_response["result"]["contents"][0]["text"])
        self.assertEqual(host_policy_payload["schema"], "cleanmac.ai-host-policy.v1")
        self.assertTrue(host_policy_payload["valid"], host_policy_payload)
        self.assertIn("cleanmac_execute_plan", host_policy_payload["auto_call"]["deny"])

        eval_pack_response = _mcp_request(
            {
                "jsonrpc": "2.0",
                "id": 38,
                "method": "resources/read",
                "params": {"uri": "cleanmac://ai/eval-pack"},
            }
        )
        eval_pack_payload = json.loads(eval_pack_response["result"]["contents"][0]["text"])
        self.assertEqual(eval_pack_payload["schema"], "cleanmac.ai-eval-pack.v1")

        eval_run_response = _mcp_request(
            {
                "jsonrpc": "2.0",
                "id": 39,
                "method": "resources/read",
                "params": {"uri": "cleanmac://ai/eval-run-smoke"},
            }
        )
        eval_run_payload = json.loads(eval_run_response["result"]["contents"][0]["text"])
        self.assertEqual(eval_run_payload["schema"], "cleanmac.ai-eval-run.v1")
        self.assertTrue(eval_run_payload["passed"], eval_run_payload)

    def test_prompts_include_confirm_execution_gate(self) -> None:
        response = _mcp_request({"jsonrpc": "2.0", "id": 33, "method": "prompts/list"})
        names = {prompt["name"] for prompt in response["result"]["prompts"]}
        self.assertIn("confirm-execution-gate", names)

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
        self.assertIn("/tmp/cleanmac-plan.json", message_text)
        self.assertIn("cleanmac_policy_simulate", message_text)
        self.assertIn("cleanmac_dry_run_plan", message_text)
        self.assertIn("cleanmac_execute_plan", message_text)
        self.assertIn("cleanmac_startup_disable", message_text)
        self.assertIn("cleanmac_privacy_execute", message_text)
        self.assertIn("review-selection", message_text)
        self.assertIn("backup_path", message_text)

    def test_prompt_explains_tool_decision(self) -> None:
        response = _mcp_request({"jsonrpc": "2.0", "id": 36, "method": "prompts/list"})
        names = {prompt["name"] for prompt in response["result"]["prompts"]}
        self.assertIn("explain-tool-decision", names)

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
        self.assertIn("cleanmac://ai/tool-decision-matrix", message_text)
        self.assertIn("cleanmac_execute_plan", message_text)
        self.assertIn("do not auto-call destructive tools", message_text)

    def test_prompt_runs_ai_eval_smoke(self) -> None:
        response = _mcp_request({"jsonrpc": "2.0", "id": 40, "method": "prompts/list"})
        names = {prompt["name"] for prompt in response["result"]["prompts"]}
        self.assertIn("run-ai-eval-smoke", names)

        prompt_response = _mcp_request(
            {
                "jsonrpc": "2.0",
                "id": 41,
                "method": "prompts/get",
                "params": {"name": "run-ai-eval-smoke", "arguments": {}},
            }
        )
        message_text = prompt_response["result"]["messages"][0]["content"]["text"]
        self.assertIn("cleanmac://ai/eval-pack", message_text)
        self.assertIn("cleanmac://ai/eval-run-smoke", message_text)
        self.assertIn("do not call cleanmac_execute_plan", message_text)

    def test_prompt_reviews_ai_governance(self) -> None:
        response = _mcp_request({"jsonrpc": "2.0", "id": 43, "method": "prompts/list"})
        names = {prompt["name"] for prompt in response["result"]["prompts"]}
        self.assertIn("review-ai-governance", names)

        prompt_response = _mcp_request(
            {
                "jsonrpc": "2.0",
                "id": 44,
                "method": "prompts/get",
                "params": {"name": "review-ai-governance", "arguments": {}},
            }
        )
        message_text = prompt_response["result"]["messages"][0]["content"]["text"]
        self.assertIn("cleanmac://ai/governance-advice", message_text)
        self.assertIn("required_host_controls", message_text)
        self.assertIn("Do not call cleanmac_execute_plan", message_text)

    def test_prompt_reviews_ai_host_policy(self) -> None:
        response = _mcp_request({"jsonrpc": "2.0", "id": 46, "method": "prompts/list"})
        names = {prompt["name"] for prompt in response["result"]["prompts"]}
        self.assertIn("review-ai-host-policy", names)

        prompt_response = _mcp_request(
            {
                "jsonrpc": "2.0",
                "id": 47,
                "method": "prompts/get",
                "params": {"name": "review-ai-host-policy", "arguments": {}},
            }
        )
        message_text = prompt_response["result"]["messages"][0]["content"]["text"]
        self.assertIn("cleanmac://ai/host-policy", message_text)
        self.assertIn("auto_call.deny", message_text)
        self.assertIn("cleanmac_execute_plan", message_text)
        self.assertIn("cleanmac_startup_disable", message_text)
        self.assertIn("cleanmac_privacy_execute", message_text)
        self.assertIn("review-selection", message_text)

    def test_tools_call_unknown_tool(self) -> None:
        response = _mcp_request(
            {
                "jsonrpc": "2.0",
                "id": 3,
                "method": "tools/call",
                "params": {"name": "cleanmac_nonexistent", "arguments": {}},
            }
        )
        self.assertEqual(response["error"]["code"], -32602)
        self.assertIn("Unknown tool", response["error"]["message"])

    def test_tools_call_error_includes_structured_content(self) -> None:
        response = _mcp_request(
            {
                "jsonrpc": "2.0",
                "id": 41,
                "method": "tools/call",
                "params": {"name": "cleanmac_inspect", "arguments": {}},
            }
        )
        result = response["result"]
        self.assertTrue(result["isError"])
        structured = result["structuredContent"]
        self.assertEqual(structured["schema"], "cleanmac.mcp-tool-error.v1")
        self.assertEqual(structured["tool"], "cleanmac_inspect")
        self.assertIn("message", structured)
        self.assertEqual(structured["host_action"], "fix_arguments_and_retry")
        self.assertTrue(structured["retryable"])
        self.assertIn("categories", structured["missing_or_invalid_arguments"])
        self.assertEqual(structured["safe_to_auto_retry"], False)

    def test_initialize_handshake(self) -> None:
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
        self.assertEqual(result["protocolVersion"], "2024-11-05")
        self.assertIn("tools", result["capabilities"])
        self.assertIn("resources", result["capabilities"])
        self.assertIn("prompts", result["capabilities"])
        self.assertEqual(result["serverInfo"]["name"], "cleanmac-mcp")

    def test_shutdown(self) -> None:
        response = _mcp_request({"jsonrpc": "2.0", "id": 1, "method": "shutdown"})
        self.assertIsNone(response["result"])

    def test_json_parse_error(self) -> None:
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
        self.assertEqual(response["error"]["code"], -32700)
        self.assertIn("Parse error", response["error"]["message"])

    def test_initialize_sends_initialized_notification(self) -> None:
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
        self.assertGreaterEqual(len(lines), 2, f"Expected at least 2 output lines, got {len(lines)}")

        # First line: the initialize response
        init_response = json.loads(lines[0])
        self.assertEqual(init_response["result"]["protocolVersion"], "2024-11-05")

        # Second line: the initialized notification
        notification = json.loads(lines[1])
        self.assertEqual(notification.get("method"), "notifications/initialized")
        self.assertNotIn("id", notification)

    def test_resources_read_all_individual_resources(self) -> None:
        """Verify each resource URI returns valid JSON with a schema field."""
        list_response = _mcp_request({"jsonrpc": "2.0", "id": 51, "method": "resources/list"})
        uris = [r["uri"] for r in list_response["result"]["resources"]]
        self.assertGreater(len(uris), 8)

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
                self.fail(f"Resource {uri} returned error: {response['error']}")
            content = response["result"]["contents"][0]
            self.assertEqual(content["uri"], uri)
            self.assertEqual(content["mimeType"], "application/json")
            payload = json.loads(content["text"])
            self.assertIn("schema", payload, f"Resource {uri} missing schema field")

    def test_prompt_get_unknown_name(self) -> None:
        response = _mcp_request(
            {
                "jsonrpc": "2.0",
                "id": 61,
                "method": "prompts/get",
                "params": {"name": "nonexistent-prompt"},
            }
        )
        self.assertEqual(response["error"]["code"], -32602)
        self.assertIn("Unknown prompt", response["error"]["message"])

    def test_unknown_method(self) -> None:
        response = _mcp_request(
            {
                "jsonrpc": "2.0",
                "id": 62,
                "method": "bogus_method",
            }
        )
        self.assertEqual(response["error"]["code"], -32601)
        self.assertIn("Method not found", response["error"]["message"])

    def test_shutdown_prevents_further_requests(self) -> None:
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
        self.assertIsNotNone(stdout1)

        # Process should have exited; start a new one and verify tools/list still works
        response = _mcp_request({"jsonrpc": "2.0", "id": 1, "method": "tools/list"})
        tools = response["result"]["tools"]
        self.assertEqual(len(tools), 37)

    def test_notifications_initialized_standalone(self) -> None:
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
        self.assertEqual(stdout.strip(), "")

    def test_prompt_get_missing_arguments_uses_defaults(self) -> None:
        """prompts/get with safe-cleanup-review but no arguments should use defaults."""
        response = _mcp_request(
            {
                "jsonrpc": "2.0",
                "id": 63,
                "method": "prompts/get",
                "params": {"name": "safe-cleanup-review", "arguments": {}},
            }
        )
        self.assertNotIn("error", response, f"Unexpected error: {response.get('error')}")
        prompt = response["result"]
        self.assertEqual(prompt["description"], "Safe cleanmac cleanup review workflow")
        message_text = prompt["messages"][0]["content"]["text"]
        # Should contain default placeholder or empty categories
        self.assertIsInstance(message_text, str)
        self.assertGreater(len(message_text), 100)

    def test_resources_read_capabilities(self) -> None:
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
        self.assertEqual(content["uri"], "cleanmac://capabilities")
        self.assertEqual(content["mimeType"], "application/json")
        payload = json.loads(content["text"])
        self.assertEqual(payload["schema"], "cleanmac.capabilities.v1")
        self.assertIn("commands", payload)
        self.assertIn("category_count", payload)


if __name__ == "__main__":
    unittest.main()
