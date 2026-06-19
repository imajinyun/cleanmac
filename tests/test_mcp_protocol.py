"""Protocol hardening tests for the cleanmac MCP stdio server."""

from __future__ import annotations

import json
import os
import stat
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
MCP_SERVER = PROJECT_ROOT / "scripts" / "cleanmac_mcp_server.py"


def _mcp_env(**overrides: str) -> dict[str, str]:
    env = os.environ.copy()
    env["CLEANMAC_TEST_MODE"] = "1"
    env["CLEANMAC_TEST_NO_AUTH"] = "1"
    env.update(overrides)
    return env


def _mcp_request(payload: dict, *, env: dict[str, str] | None = None) -> dict:
    proc = subprocess.run(
        [sys.executable, str(MCP_SERVER)],
        input=json.dumps(payload),
        text=True,
        capture_output=True,
        timeout=30,
        env=env or _mcp_env(),
        check=True,
    )
    first_line = proc.stdout.strip().splitlines()[0]
    return json.loads(first_line)


class MCPProtocolTests(unittest.TestCase):
    def test_request_without_jsonrpc_field_returns_invalid_request(self) -> None:
        response = _mcp_request({"id": 1, "method": "tools/list"})

        self.assertEqual(response["error"]["code"], -32600)
        self.assertIn("jsonrpc", response["error"]["message"].lower())

    def test_request_with_wrong_jsonrpc_version_returns_invalid_request(self) -> None:
        response = _mcp_request({"jsonrpc": "1.0", "id": 2, "method": "tools/list"})

        self.assertEqual(response["error"]["code"], -32600)

    def test_tool_call_respects_injected_timeout(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            sleeper = Path(tmp) / "sleepy_cleanmac.py"
            sleeper.write_text(
                "#!/usr/bin/env python3\nimport time\ntime.sleep(2)\nprint('{}')\n",
                encoding="utf-8",
            )
            sleeper.chmod(sleeper.stat().st_mode | stat.S_IXUSR)
            response = _mcp_request(
                {
                    "jsonrpc": "2.0",
                    "id": 3,
                    "method": "tools/call",
                    "params": {"name": "cleanmac_capabilities", "arguments": {}},
                },
                env=_mcp_env(CLEANMAC_CLI=str(sleeper), CLEANMAC_MCP_TOOL_TIMEOUT="0.01"),
            )

        result = response["result"]
        self.assertTrue(result["isError"])
        self.assertEqual(result["structuredContent"]["schema"], "cleanmac.mcp-tool-error.v1")
        self.assertIn("timed out", result["structuredContent"]["message"].lower())

    def test_resource_payload_is_returned_as_data_not_instruction(self) -> None:
        response = _mcp_request(
            {
                "jsonrpc": "2.0",
                "id": 4,
                "method": "resources/read",
                "params": {"uri": "cleanmac://ai/runbook"},
            }
        )

        text = response["result"]["contents"][0]["text"]
        payload = json.loads(text)
        self.assertEqual(payload["schema"], "cleanmac.ai-runbook.v1")
        self.assertFalse(payload["execution_gate"]["auto_call_allowed"])


if __name__ == "__main__":
    unittest.main()
