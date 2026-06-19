from __future__ import annotations

import json
import subprocess
import sys
import unittest
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parent.parent
CLI = PROJECT_ROOT / "cleanmac.py"


class AIGovernanceTests(unittest.TestCase):
    report: dict[str, Any]

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

    def test_governance_advice_marks_incomplete_inputs_needs_attention(self) -> None:
        from cleancli.ai_governance import render_ai_governance_advice

        report = render_ai_governance_advice(
            readiness={"ready": False, "eval_pack": {"ready": False}},
            runbook={"uses_shell": True, "default_mode": "execute-first", "execution_gate": "invalid"},
            decision_matrix={
                "violation_count": 2,
                "violations": ["unsafe auto-call"],
                "tools": [
                    {"name": "cleanmac_capabilities", "risk": "readonly", "auto_call_allowed": True},
                    {"name": "cleanmac_execute_plan", "risk": "destructive", "auto_call_allowed": True},
                    "not-a-tool-row",
                ],
            },
            eval_pack={"schema": "cleanmac.ai-eval-pack.v1", "allows_destructive_execution": True, "scenarios": []},
        )

        self.assertEqual(report["schema"], "cleanmac.ai-governance-advice.v1")
        self.assertFalse(report["ready_for_llm_calling"])
        self.assertEqual(report["governance_score"], {"passed": 0, "total": 4, "level": "partial"})

        recommendations = {item["id"]: item for item in report["recommendations"]}
        self.assertEqual(recommendations["preflight-first"]["status"], "needs_attention")
        self.assertEqual(recommendations["deny-auto-destructive"]["status"], "needs_attention")
        self.assertEqual(recommendations["argv-only-transport"]["status"], "needs_attention")
        self.assertEqual(recommendations["dry-run-token-gate"]["status"], "needs_attention")
        self.assertEqual(recommendations["trace-and-eval-regression"]["status"], "needs_attention")
        self.assertEqual(recommendations["structured-error-recovery"]["status"], "needs_attention")

        route = {item["id"]: item for item in report["governance_route"]}
        self.assertEqual(route["prompt-injection-boundary"]["status"], "needs_attention")
        self.assertEqual(route["mcp-host-governance"]["status"], "needs_attention")
        self.assertEqual(route["audit-traceability"]["status"], "needs_attention")

    def test_governance_validation_reports_structural_violations(self) -> None:
        from cleancli.ai_governance import validate_ai_governance_advice

        validation = validate_ai_governance_advice(
            {
                "schema": "cleanmac.not-governance.v1",
                "default_policy": "invalid",
                "recommendations": "invalid",
                "governance_route": "invalid",
                "release_gate_commands": [],
            }
        )

        self.assertEqual(validation["schema"], "cleanmac.ai-governance-advice-validation.v1")
        self.assertFalse(validation["valid"])
        self.assertIn("schema must be cleanmac.ai-governance-advice.v1", validation["violations"])
        self.assertIn("default_policy must be an object", validation["violations"])
        self.assertIn("recommendations must be a sequence", validation["violations"])
        self.assertIn("governance_route must be a sequence", validation["violations"])
        self.assertIn("release_gate_commands must include make ai-governance-smoke", validation["violations"])

    def test_governance_validation_reports_unsatisfied_route_and_policy_gaps(self) -> None:
        from cleancli.ai_governance import validate_ai_governance_advice

        validation = validate_ai_governance_advice(
            {
                "schema": "cleanmac.ai-governance-advice.v1",
                "default_policy": {"shell_allowed": True, "auto_call_denied_tools": []},
                "recommendations": [{"id": str(index)} for index in range(4)],
                "governance_route": [{"id": str(index), "status": "satisfied"} for index in range(9)]
                + [{"id": "blocked", "status": "needs_attention"}],
                "release_gate_commands": [["make", "ai-governance-smoke"]],
            }
        )

        self.assertFalse(validation["valid"])
        joined = "\n".join(validation["violations"])
        self.assertIn("shell_allowed must be false", joined)
        self.assertIn("cleanmac_execute_plan must be denied for auto-call", joined)
        self.assertIn("recommendations must include at least five governance controls", joined)
        self.assertIn("governance_route contains unsatisfied items: blocked", joined)

    def test_governance_validation_requires_ten_route_items(self) -> None:
        from cleancli.ai_governance import validate_ai_governance_advice

        validation = validate_ai_governance_advice(
            {
                "schema": "cleanmac.ai-governance-advice.v1",
                "default_policy": {"shell_allowed": False, "auto_call_denied_tools": ["cleanmac_execute_plan"]},
                "recommendations": [{"id": str(index)} for index in range(5)],
                "governance_route": [{"id": str(index), "status": "satisfied"} for index in range(9)],
                "release_gate_commands": [["make", "ai-governance-smoke"]],
            }
        )

        self.assertFalse(validation["valid"])
        self.assertIn(
            "governance_route must cover the ten governance route items",
            validation["violations"],
        )


if __name__ == "__main__":
    unittest.main()
