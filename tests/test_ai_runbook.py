from __future__ import annotations

import json
import subprocess
import sys
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
CLI = PROJECT_ROOT / "cleanmac.py"


class AIRunbookTests(unittest.TestCase):
    def test_ai_runbook_reports_safe_host_workflow(self) -> None:
        result = subprocess.run(
            [sys.executable, str(CLI), "--json", "ai-runbook"],
            text=True,
            capture_output=True,
            check=True,
        )
        report = json.loads(result.stdout)

        self.assertEqual(report["schema"], "cleanmac.ai-runbook.v1")
        self.assertEqual(report["default_mode"], "dry-run-first")
        runtime_lifecycle = report["runtime_lifecycle"]
        self.assertEqual(runtime_lifecycle["product_model"], "ai-first-ephemeral-cli")
        self.assertTrue(runtime_lifecycle["runs_only_when_invoked"])
        self.assertTrue(runtime_lifecycle["exits_after_workflow"])
        self.assertEqual(runtime_lifecycle["resident_processes"], 0)
        self.assertFalse(runtime_lifecycle["implements_tui"])
        self.assertFalse(runtime_lifecycle["implements_gui"])
        self.assertFalse(runtime_lifecycle["installs_background_daemon"])
        self.assertFalse(runtime_lifecycle["performs_unsolicited_scans"])
        self.assertFalse(report["uses_shell"])
        self.assertEqual(report["execution_gate"]["destructive_tool"], "cleanmac_execute_plan")
        self.assertFalse(report["execution_gate"]["auto_call_allowed"])
        self.assertIn("cleanmac_generate_plan", report["execution_gate"]["required_before_execute"])
        self.assertIn("human_confirmation", report["execution_gate"]["required_before_execute"])
        one_shot = report["one_shot_governed_workflow"]
        self.assertEqual(one_shot["tool"], "cleanmac_ai_workflow")
        self.assertEqual(one_shot["schema"], "cleanmac.ai-workflow.v1")
        self.assertTrue(one_shot["auto_call_allowed"])
        self.assertFalse(one_shot["destructive"])
        phases = {phase["id"]: phase for phase in report["phases"]}
        self.assertEqual(
            phases["discover"]["tools"],
            ["cleanmac_capabilities", "cleanmac_list_categories", "cleanmac_ai_workflow"],
        )
        self.assertIn("cleanmac_policy_simulate", phases["preflight"]["tools"])
        self.assertIn("cleanmac_dry_run_plan", phases["dry_run"]["tools"])
        self.assertIn("cleanmac_execute_plan", phases["execute"]["tools"])
        self.assertFalse(phases["execute"]["auto_call_allowed"])


if __name__ == "__main__":
    unittest.main()
