from __future__ import annotations

import json
import subprocess
import sys
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
CLI = PROJECT_ROOT / "cleanmac.py"


class AIGovernanceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        result = subprocess.run(
            [sys.executable, str(CLI), "--json", "ai-governance-advice"],
            text=True,
            capture_output=True,
            check=True,
        )
        cls.report = json.loads(result.stdout)

    def test_governance_advice_schema(self) -> None:
        self.assertEqual(self.report["schema"], "cleanmac.ai-governance-advice.v1")

    def test_governance_advice_ready_for_llm_calling(self) -> None:
        self.assertTrue(self.report["ready_for_llm_calling"], self.report)

    def test_governance_advice_default_policy(self) -> None:
        self.assertEqual(self.report["governance_score"]["level"], "strong")
        self.assertFalse(self.report["default_policy"]["shell_allowed"])
        self.assertIn("cleanmac_execute_plan", self.report["default_policy"]["auto_call_denied_tools"])
        self.assertIn("cleanmac_capabilities", self.report["default_policy"]["auto_call_allowed_tools"])
        self.assertIn(
            "cleanmac_execute_plan",
            self.report["default_policy"]["human_confirmation_required_for"],
        )

    def test_governance_advice_required_host_controls_and_recommendations(self) -> None:
        self.assertGreaterEqual(len(self.report["required_host_controls"]), 5)
        self.assertGreaterEqual(len(self.report["recommendations"]), 5)

    def test_governance_advice_release_gate_commands(self) -> None:
        self.assertIn(["make", "ai-governance-smoke"], self.report["release_gate_commands"])
        self.assertIn(["make", "ai-host-smoke"], self.report["release_gate_commands"])
        self.assertIn(["cleanmac", "--json", "ai-host-policy"], self.report["release_gate_commands"])

    def test_governance_advice_recommendation_statuses(self) -> None:
        self.assertIn("read cleanmac://ai/host-policy", self.report["recommended_call_sequence"])
        recommendations = {item["id"]: item for item in self.report["recommendations"]}
        self.assertEqual(recommendations["preflight-first"]["priority"], "p0")
        self.assertEqual(recommendations["deny-auto-destructive"]["status"], "satisfied")
        self.assertIn(
            "cleanmac_execute_plan",
            recommendations["deny-auto-destructive"]["blocked_tools"],
        )
        self.assertEqual(recommendations["dry-run-token-gate"]["status"], "satisfied")
        self.assertIn(
            "cleanmac_dry_run_plan",
            recommendations["dry-run-token-gate"]["required_before_execute"],
        )
        self.assertIn("Skipping ai-eval-run smoke", "\n".join(self.report["anti_patterns"]))
        self.assertIn("cleanmac.ai-host-policy.v1", "\n".join(self.report["anti_patterns"]))

    def test_governance_advice_governance_route_all_satisfied(self) -> None:
        route = {item["id"]: item for item in self.report["governance_route"]}
        self.assertGreaterEqual(len(route), 10)
        self.assertTrue(all(item["status"] == "satisfied" for item in route.values()), route)
        self.assertIn("ci-release-gate", route)
        self.assertIn("audit-traceability", route)


if __name__ == "__main__":
    unittest.main()