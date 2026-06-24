"""Concurrency regression tests for AI-friendly cleanmac entry points."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import threading
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
CLI = PROJECT_ROOT / "cleanmac.py"
MCP_SERVER = PROJECT_ROOT / "scripts" / "cleanmac_mcp_server.py"


def _no_auth_env() -> dict[str, str]:
    env = os.environ.copy()
    env["CLEANMAC_TEST_MODE"] = "1"
    env["CLEANMAC_TEST_NO_AUTH"] = "1"
    return env


def _run_cli_json(*args: str) -> dict:
    result = subprocess.run(
        [sys.executable, str(CLI), "--json", *args],
        text=True,
        capture_output=True,
        check=True,
        env=_no_auth_env(),
        timeout=60,
    )
    return json.loads(result.stdout)


def _mcp_call(tool: str) -> dict:
    payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "tools/call",
        "params": {"name": tool, "arguments": {}},
    }
    result = subprocess.run(
        [sys.executable, str(MCP_SERVER)],
        input=json.dumps(payload),
        text=True,
        capture_output=True,
        check=True,
        env=_no_auth_env(),
        timeout=60,
    )
    return json.loads(result.stdout.strip().splitlines()[0])


def test_concurrent_capabilities_calls_are_deterministic() -> None:
    results: list[dict] = []
    errors: list[BaseException] = []
    lock = threading.Lock()

    def worker() -> None:
        try:
            result = _run_cli_json("capabilities")
            with lock:
                results.append(result)
        except BaseException as exc:  # pragma: no cover - defensive diagnostic path
            with lock:
                errors.append(exc)

    threads = [threading.Thread(target=worker) for _ in range(8)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    assert errors == []
    assert len(results) == 8
    assert {result["schema"] for result in results} == {"cleanmac.capabilities.v1"}
    assert {result["ai_readiness"]["ready"] for result in results} == {True}
    assert {result["ai_self_test"]["passed"] for result in results} == {True}


def test_concurrent_mcp_tool_calls_do_not_cross_pollute() -> None:
    results: list[dict] = []
    errors: list[BaseException] = []
    lock = threading.Lock()

    def worker(tool: str) -> None:
        try:
            result = _mcp_call(tool)
            with lock:
                results.append(result)
        except BaseException as exc:  # pragma: no cover - defensive diagnostic path
            with lock:
                errors.append(exc)

    tools = [
        "cleanmac_capabilities",
        "cleanmac_list_categories",
        "cleanmac_capabilities",
        "cleanmac_list_categories",
    ]
    threads = [threading.Thread(target=worker, args=(tool,)) for tool in tools]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    assert errors == []
    assert len(results) == len(tools)
    for response in results:
        assert response["result"]["isError"] is False, response
        assert "structuredContent" in response["result"]
