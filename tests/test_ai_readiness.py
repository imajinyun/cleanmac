from __future__ import annotations

import json
import subprocess
import sys
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
CLI = PROJECT_ROOT / "cleanmac.py"


class AIReadinessTests(unittest.TestCase):
    def test_ai_readiness_reports_host_integration_status(self) -> None:
        result = subprocess.run(
            [sys.executable, str(CLI), "--json", "ai-readiness"],
            text=True,
            capture_output=True,
            check=True,
        )
        report = json.loads(result.stdout)

        self.assertEqual(report["schema"], "cleanmac.ai-readiness.v1")
        self.assertTrue(report["ready"], report)
        self.assertEqual(report["tool_count"], report["provider_exports"]["openai_tool_count"])
        self.assertEqual(report["tool_count"], report["provider_exports"]["anthropic_tool_count"])
        self.assertTrue(report["contracts"]["schema_validation"]["valid"])
        self.assertTrue(report["contracts"]["contract_compatibility"]["compatible"])
        self.assertTrue(report["contracts"]["provider_export_parity"]["same_tool_names"])
        self.assertEqual(report["mcp"]["server_command"], ["cleanmac-mcp"])
        self.assertTrue(report["decision_matrix"]["ready"])
        self.assertEqual(report["decision_matrix"]["schema"], "cleanmac.ai-tool-decision-matrix.v1")
        self.assertEqual(report["decision_matrix"]["violation_count"], 0)
        self.assertTrue(report["eval_pack"]["ready"])
        self.assertEqual(report["eval_pack"]["schema"], "cleanmac.ai-eval-pack.v1")
        self.assertGreaterEqual(report["eval_pack"]["scenario_count"], 4)
        self.assertEqual(report["eval_runner"]["default_scenario"], "smoke")
        self.assertFalse(report["eval_runner"]["destructive_execution_allowed"])
        self.assertIn(["cleanmac", "--json", "ai-decision-matrix"], report["recommended_preflight_commands"])
        self.assertIn(["cleanmac", "--json", "ai-eval-pack"], report["recommended_preflight_commands"])
        self.assertIn(
            ["cleanmac", "--json", "ai-eval-run", "--scenario", "smoke"],
            report["recommended_preflight_commands"],
        )
        self.assertIn("cleanmac_capabilities", report["recommended_starting_tools"])
        self.assertIn("cleanmac_policy_simulate", report["mandatory_before_execute"])


if __name__ == "__main__":
    unittest.main()
