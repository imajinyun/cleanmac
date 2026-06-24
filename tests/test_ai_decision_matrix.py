from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
CLI = PROJECT_ROOT / "cleanmac.py"


def load_decision_matrix() -> dict:
    result = subprocess.run(
        [sys.executable, str(CLI), "--json", "ai-decision-matrix"],
        text=True,
        capture_output=True,
        check=True,
    )
    return json.loads(result.stdout)


def test_ai_decision_matrix_reports_tool_boundaries() -> None:
    report = load_decision_matrix()

    assert report["schema"] == "cleanmac.ai-tool-decision-matrix.v1"
    assert report["default_execution_policy"] == "dry-run-first"
    assert not report["uses_shell"]
    assert report["tool_count"] == len(report["tools"])

    tools = {tool["name"]: tool for tool in report["tools"]}
    execute_tool = tools["cleanmac_execute_plan"]
    assert execute_tool["risk"] == "destructive"
    assert not execute_tool["auto_call_allowed"]
    assert execute_tool["requires_human_confirmation"]
    assert execute_tool["phase"] == "execute"
    assert "cleanmac_dry_run_plan" in execute_tool["required_predecessor_tools"]
    assert execute_tool["mcp_annotations"]["destructiveHint"] is True
    assert execute_tool["mcp_annotations"]["readOnlyHint"] is False
    assert execute_tool["on_error"]["host_action"] == "stop_and_show_structured_error"

    inspect_tool = tools["cleanmac_inspect"]
    assert inspect_tool["phase"] == "inspect"
    assert inspect_tool["auto_call_allowed"]
    assert inspect_tool["mcp_annotations"]["readOnlyHint"] is True
    assert inspect_tool["mcp_annotations"]["destructiveHint"] is False


def test_ai_decision_matrix_covers_runbook_phase_tools() -> None:
    report = load_decision_matrix()
    names = {tool["name"] for tool in report["tools"]}

    assert not report["violations"], report["violations"]
    assert "cleanmac_generate_plan" in names
    assert "cleanmac_validate_plan" in names
    assert "cleanmac_policy_simulate" in names
    assert "cleanmac_dry_run_plan" in names
    assert "cleanmac_execute_plan" in names
