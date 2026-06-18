from __future__ import annotations

import json
import subprocess
import sys
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
CLI = PROJECT_ROOT / "cleanmac.py"


class AIDecisionMatrixTests(unittest.TestCase):
    def test_ai_decision_matrix_reports_tool_boundaries(self) -> None:
        result = subprocess.run(
            [sys.executable, str(CLI), "--json", "ai-decision-matrix"],
            text=True,
            capture_output=True,
            check=True,
        )
        report = json.loads(result.stdout)

        self.assertEqual(report["schema"], "cleanmac.ai-tool-decision-matrix.v1")
        self.assertEqual(report["default_execution_policy"], "dry-run-first")
        self.assertFalse(report["uses_shell"])
        self.assertEqual(report["tool_count"], len(report["tools"]))

        tools = {tool["name"]: tool for tool in report["tools"]}
        execute_tool = tools["cleanmac_execute_plan"]
        self.assertEqual(execute_tool["risk"], "destructive")
        self.assertFalse(execute_tool["auto_call_allowed"])
        self.assertTrue(execute_tool["requires_human_confirmation"])
        self.assertEqual(execute_tool["phase"], "execute")
        self.assertIn("cleanmac_dry_run_plan", execute_tool["required_predecessor_tools"])
        self.assertEqual(execute_tool["mcp_annotations"]["destructiveHint"], True)
        self.assertEqual(execute_tool["mcp_annotations"]["readOnlyHint"], False)
        self.assertEqual(execute_tool["on_error"]["host_action"], "stop_and_show_structured_error")

        inspect_tool = tools["cleanmac_inspect"]
        self.assertEqual(inspect_tool["phase"], "inspect")
        self.assertTrue(inspect_tool["auto_call_allowed"])
        self.assertEqual(inspect_tool["mcp_annotations"]["readOnlyHint"], True)
        self.assertEqual(inspect_tool["mcp_annotations"]["destructiveHint"], False)

    def test_ai_decision_matrix_covers_runbook_phase_tools(self) -> None:
        result = subprocess.run(
            [sys.executable, str(CLI), "--json", "ai-decision-matrix"],
            text=True,
            capture_output=True,
            check=True,
        )
        report = json.loads(result.stdout)
        names = {tool["name"] for tool in report["tools"]}

        self.assertFalse(report["violations"], report["violations"])
        self.assertIn("cleanmac_generate_plan", names)
        self.assertIn("cleanmac_validate_plan", names)
        self.assertIn("cleanmac_policy_simulate", names)
        self.assertIn("cleanmac_dry_run_plan", names)
        self.assertIn("cleanmac_execute_plan", names)


if __name__ == "__main__":
    unittest.main()
