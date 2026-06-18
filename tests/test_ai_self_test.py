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
        self.assertIn("mcp-transport", check_ids)
        self.assertTrue(all(check["passed"] for check in report["checks"]), report["checks"])


if __name__ == "__main__":
    unittest.main()
