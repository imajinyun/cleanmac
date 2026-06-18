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
            self.assertIn("inputSchema", tool)
        names = {t["name"] for t in tools}
        self.assertIn("cleanmac_capabilities", names)
        self.assertIn("cleanmac_scripts", names)
        self.assertIn("cleanmac_open", names)
        self.assertIn("cleanmac_links", names)
        self.assertIn("cleanmac_optimize", names)

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


if __name__ == "__main__":
    unittest.main()
