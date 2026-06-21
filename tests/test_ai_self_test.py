from __future__ import annotations

import json
import subprocess
import sys
import unittest
from pathlib import Path

from cleancli.ai_self_test import render_ai_self_test
from cleancli.core import render_ai_self_test as render_core_ai_self_test

PROJECT_ROOT = Path(__file__).resolve().parent.parent
CLI = PROJECT_ROOT / "cleanmac.py"


class AISelfTestTests(unittest.TestCase):
    def test_ai_self_test_is_owned_outside_core_and_reexported(self) -> None:
        report = render_ai_self_test()

        self.assertEqual(report, render_core_ai_self_test())
        self.assertEqual(report["schema"], "cleanmac.ai-self-test.v1")
        self.assertTrue(report["passed"], report)

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
        self.assertIn("runtime-lifecycle-policy", check_ids)
        self.assertIn("tool-decision-matrix", check_ids)
        self.assertIn("ai-eval-pack", check_ids)
        self.assertIn("ai-governance-advice", check_ids)
        self.assertIn("ai-host-policy", check_ids)
        self.assertIn("contract-validation-smoke", check_ids)
        self.assertIn("mcp-transport", check_ids)
        checks = {check["id"]: check for check in report["checks"]}
        self.assertTrue(checks["tool-decision-matrix"]["passed"])
        self.assertEqual(checks["tool-decision-matrix"]["detail"]["violation_count"], 0)
        self.assertTrue(checks["runtime-lifecycle-policy"]["passed"])
        self.assertEqual(
            checks["runtime-lifecycle-policy"]["detail"]["schema"],
            "cleanmac.runtime-lifecycle-policy.v1",
        )
        self.assertEqual(checks["runtime-lifecycle-policy"]["detail"]["resident_processes"], 0)
        self.assertTrue(checks["ai-eval-pack"]["passed"])
        self.assertEqual(checks["ai-eval-pack"]["detail"]["schema"], "cleanmac.ai-eval-pack.v1")
        self.assertTrue(checks["ai-governance-advice"]["passed"])
        self.assertEqual(checks["ai-governance-advice"]["detail"]["schema"], "cleanmac.ai-governance-advice.v1")
        self.assertTrue(checks["ai-host-policy"]["passed"])
        self.assertEqual(checks["ai-host-policy"]["detail"]["schema"], "cleanmac.ai-host-policy.v1")
        self.assertTrue(checks["contract-validation-smoke"]["passed"])
        self.assertEqual(
            checks["contract-validation-smoke"]["detail"]["schema"],
            "cleanmac.ai-contract-validation-summary.v1",
        )
        coverage = checks["contract-validation-smoke"]["detail"]["contract_schema_coverage"]
        self.assertIn("cleanmac.ai-eval-run.v1", coverage["critical_schemas"])
        self.assertEqual(coverage["missing_stable_ai_schema_fragments"], [])
        self.assertTrue(all(check["passed"] for check in report["checks"]), report["checks"])


if __name__ == "__main__":
    unittest.main()
