from __future__ import annotations

import json
import subprocess
import sys
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
CLI = PROJECT_ROOT / "cleanmac.py"


class AIGovernanceTests(unittest.TestCase):
    def test_ai_governance_advice_reports_llm_calling_controls(self) -> None:
        result = subprocess.run(
            [sys.executable, str(CLI), "--json", "ai-governance-advice"],
            text=True,
            capture_output=True,
            check=True,
        )
        report = json.loads(result.stdout)

        self.assertEqual(report["schema"], "cleanmac.ai-governance-advice.v1")
        self.assertTrue(report["ready_for_llm_calling"], report)
        self.assertEqual(report["governance_score"]["level"], "strong")
        self.assertFalse(report["default_policy"]["shell_allowed"])
        self.assertIn("cleanmac_execute_plan", report["default_policy"]["auto_call_denied_tools"])
        self.assertIn("cleanmac_capabilities", report["default_policy"]["auto_call_allowed_tools"])
        self.assertIn("cleanmac_execute_plan", report["default_policy"]["human_confirmation_required_for"])
        self.assertGreaterEqual(len(report["required_host_controls"]), 5)
        self.assertGreaterEqual(len(report["recommendations"]), 5)

        recommendations = {item["id"]: item for item in report["recommendations"]}
        self.assertEqual(recommendations["preflight-first"]["priority"], "p0")
        self.assertEqual(recommendations["deny-auto-destructive"]["status"], "satisfied")
        self.assertIn("cleanmac_execute_plan", recommendations["deny-auto-destructive"]["blocked_tools"])
        self.assertEqual(recommendations["dry-run-token-gate"]["status"], "satisfied")
        self.assertIn("cleanmac_dry_run_plan", recommendations["dry-run-token-gate"]["required_before_execute"])
        self.assertIn("Skipping ai-eval-run smoke", "\n".join(report["anti_patterns"]))


if __name__ == "__main__":
    unittest.main()
