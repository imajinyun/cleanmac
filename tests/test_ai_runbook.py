from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
CLI = PROJECT_ROOT / "cleanmac.py"


def test_ai_runbook_reports_safe_host_workflow() -> None:
    result = subprocess.run(
        [sys.executable, str(CLI), "--json", "ai-runbook"],
        text=True,
        capture_output=True,
        check=True,
    )
    report = json.loads(result.stdout)

    assert report["schema"] == "cleanmac.ai-runbook.v1"
    assert report["default_mode"] == "dry-run-first"
    runtime_lifecycle = report["runtime_lifecycle"]
    assert runtime_lifecycle["product_model"] == "ai-first-ephemeral-cli"
    assert runtime_lifecycle["runs_only_when_invoked"]
    assert runtime_lifecycle["exits_after_workflow"]
    assert runtime_lifecycle["resident_processes"] == 0
    assert not runtime_lifecycle["implements_tui"]
    assert not runtime_lifecycle["implements_gui"]
    assert not runtime_lifecycle["installs_background_daemon"]
    assert not runtime_lifecycle["performs_unsolicited_scans"]
    assert not report["uses_shell"]
    assert report["execution_gate"]["destructive_tool"] == "cleanmac_execute_plan"
    assert not report["execution_gate"]["auto_call_allowed"]
    assert "cleanmac_generate_plan" in report["execution_gate"]["required_before_execute"]
    assert "human_confirmation" in report["execution_gate"]["required_before_execute"]
    one_shot = report["one_shot_governed_workflow"]
    assert one_shot["tool"] == "cleanmac_ai_workflow"
    assert one_shot["schema"] == "cleanmac.ai-workflow.v1"
    assert one_shot["auto_call_allowed"]
    assert not one_shot["destructive"]
    phases = {phase["id"]: phase for phase in report["phases"]}
    assert phases["discover"]["tools"] == [
        "cleanmac_capabilities",
        "cleanmac_list_categories",
        "cleanmac_ai_workflow",
    ]
    assert "cleanmac_policy_simulate" in phases["preflight"]["tools"]
    assert "cleanmac_dry_run_plan" in phases["dry_run"]["tools"]
    assert "cleanmac_execute_plan" in phases["execute"]["tools"]
    assert not phases["execute"]["auto_call_allowed"]
