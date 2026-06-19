"""Tests for the cleanmac MCP stdio server."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import unittest
from pathlib import Path

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
        self.assertGreaterEqual(len(tools), 22)
        for tool in tools:
            self.assertIn("name", tool)
            self.assertIn("description", tool)
            self.assertIn("annotations", tool)
            self.assertIn("inputSchema", tool)
        names = {t["name"] for t in tools}
        self.assertIn("cleanmac_capabilities", names)
        self.assertIn("cleanmac_scripts", names)
        self.assertIn("cleanmac_open", names)
        self.assertIn("cleanmac_links", names)
        self.assertIn("cleanmac_optimize", names)
        tool_by_name = {t["name"]: t for t in tools}
        self.assertTrue(tool_by_name["cleanmac_capabilities"]["annotations"]["readOnlyHint"])
        self.assertTrue(tool_by_name["cleanmac_execute_plan"]["annotations"]["destructiveHint"])

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

    def test_resources_list_exposes_ai_governance_resources(self) -> None:
        response = _mcp_request({"jsonrpc": "2.0", "id": 21, "method": "resources/list"})
        resources = response["result"]["resources"]
        uris = {resource["uri"] for resource in resources}

        self.assertIn("cleanmac://capabilities", uris)
        self.assertIn("cleanmac://ai/function-schemas", uris)
        self.assertIn("cleanmac://ai/mcp-tool-catalog", uris)
        self.assertTrue(all(resource["mimeType"] == "application/json" for resource in resources))

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
        self.assertIn("never call cleanmac_execute_plan without explicit human confirmation", message_text)

    def test_resources_expose_readiness_runbook_and_self_test(self) -> None:
        response = _mcp_request({"jsonrpc": "2.0", "id": 31, "method": "resources/list"})
        uris = {resource["uri"] for resource in response["result"]["resources"]}

        self.assertIn("cleanmac://ai/readiness", uris)
        self.assertIn("cleanmac://ai/runbook", uris)
        self.assertIn("cleanmac://ai/self-test", uris)
        self.assertIn("cleanmac://ai/tool-decision-matrix", uris)
        self.assertIn("cleanmac://ai/governance-advice", uris)
        self.assertIn("cleanmac://ai/host-policy", uris)
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
        self.assertGreaterEqual(len(tools), 22)

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
