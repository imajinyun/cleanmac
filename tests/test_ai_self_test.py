from __future__ import annotations

import json
import subprocess
import sys
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
CLI = PROJECT_ROOT / "cleanmac.py"


class AISelfTestTests(unittest.TestCase):
    def test_ai_self_test_reports_all_checks_passed(self) -> None:
        result = subprocess.run(
            [sys.executable, str(CLI), "--json", "ai-self-test"],
            text=True,
            capture_output=True,
            check=True,
        )
        report = json.loads(result.stdout)

        self.assertEqual(report["schema"], "cleanmac.ai-self-test.v1")
        self.assertTrue(report["passed"], report)
        check_ids = {check["id"] for check in report["checks"]}
        self.assertIn("schema-validation", check_ids)
        self.assertIn("contract-compatibility", check_ids)
        self.assertIn("provider-export-parity", check_ids)
        self.assertIn("runbook-execution-gate", check_ids)
        self.assertIn("tool-decision-matrix", check_ids)
        self.assertIn("ai-eval-pack", check_ids)
        self.assertIn("ai-governance-advice", check_ids)
        self.assertIn("ai-host-policy", check_ids)
        self.assertIn("mcp-transport", check_ids)
        checks = {check["id"]: check for check in report["checks"]}
        self.assertTrue(checks["tool-decision-matrix"]["passed"])
        self.assertEqual(checks["tool-decision-matrix"]["detail"]["violation_count"], 0)
        self.assertTrue(checks["ai-eval-pack"]["passed"])
        self.assertEqual(checks["ai-eval-pack"]["detail"]["schema"], "cleanmac.ai-eval-pack.v1")
        self.assertTrue(checks["ai-governance-advice"]["passed"])
        self.assertEqual(checks["ai-governance-advice"]["detail"]["schema"], "cleanmac.ai-governance-advice.v1")
        self.assertTrue(checks["ai-host-policy"]["passed"])
        self.assertEqual(checks["ai-host-policy"]["detail"]["schema"], "cleanmac.ai-host-policy.v1")
        self.assertTrue(all(check["passed"] for check in report["checks"]), report["checks"])


if __name__ == "__main__":
    unittest.main()
