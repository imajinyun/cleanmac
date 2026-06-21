from __future__ import annotations

import json
import subprocess
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

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
        self.assertTrue(report["runtime_lifecycle"]["ready"])
        self.assertEqual(report["runtime_lifecycle"]["schema"], "cleanmac.runtime-lifecycle-policy.v1")
        self.assertEqual(report["runtime_lifecycle"]["resource_uri"], "cleanmac://ai/runtime-lifecycle-policy")
        self.assertEqual(report["runtime_lifecycle"]["product_model"], "ai-first-ephemeral-cli")
        self.assertEqual(report["runtime_lifecycle"]["resident_processes"], 0)
        self.assertTrue(report["governance_advice"]["ready"])
        self.assertEqual(report["governance_advice"]["schema"], "cleanmac.ai-governance-advice.v1")
        self.assertEqual(report["governance_advice"]["level"], "strong")
        self.assertTrue(report["host_policy"]["ready"])
        self.assertEqual(report["host_policy"]["schema"], "cleanmac.ai-host-policy.v1")
        self.assertEqual(report["host_policy"]["default_decision"], "deny")
        self.assertTrue(report["schema_registry"]["ready"])
        self.assertEqual(report["schema_registry"]["schema"], "cleanmac.ai-schema-registry.v1")
        self.assertEqual(report["schema_registry"]["latest_plan_schema"], "cleanmac.plan.v1")
        self.assertTrue(report["schema_registry"]["supported_plan_schemas_registered"])
        self.assertTrue(report["schema_registry"]["core_contract_schemas_present"])
        self.assertEqual(report["schema_registry"]["deprecated_schema_count"], 0)
        self.assertTrue(report["contract_validation"]["ready"])
        self.assertEqual(report["contract_validation"]["schema"], "cleanmac.ai-contract-validation-summary.v1")
        self.assertGreaterEqual(report["contract_validation"]["validated_schema_count"], 2)
        self.assertEqual(report["contract_validation"]["failure_count"], 0)
        self.assertEqual(report["release_readiness"]["schema"], "cleanmac.release-readiness.v1")
        self.assertIn("ready", report["release_readiness"])
        self.assertIn("failed_gate_ids", report["release_readiness"])
        self.assertEqual(report["release_readiness"]["required_for"], "release-review")
        self.assertEqual(
            report["release_readiness"]["not_required_for"],
            "runtime-readonly-ai-host-discovery",
        )
        coverage = report["contract_validation"]["contract_schema_coverage"]
        self.assertIn("cleanmac.ai-host-policy.v1", coverage["critical_schemas"])
        self.assertIn("cleanmac.ai-governance-advice.v1", coverage["critical_schemas"])
        self.assertIn("cleanmac.ai-eval-pack.v1", coverage["critical_schemas"])
        self.assertEqual(coverage["missing_stable_ai_schema_fragments"], [])
        self.assertIn(["cleanmac", "--json", "ai-decision-matrix"], report["recommended_preflight_commands"])
        self.assertIn(["cleanmac", "--json", "ai-governance-advice"], report["recommended_preflight_commands"])
        self.assertIn(["cleanmac", "--json", "ai-host-policy"], report["recommended_preflight_commands"])
        self.assertIn(["cleanmac", "--json", "ai-host-evidence"], report["recommended_preflight_commands"])
        self.assertIn(["cleanmac", "--json", "release-readiness"], report["recommended_preflight_commands"])
        self.assertIn(["cleanmac", "--json", "ai-eval-pack"], report["recommended_preflight_commands"])
        self.assertIn(
            ["cleanmac", "--json", "ai-eval-run", "--scenario", "smoke"],
            report["recommended_preflight_commands"],
        )
        self.assertIn("cleanmac_capabilities", report["recommended_starting_tools"])
        self.assertIn("cleanmac_policy_simulate", report["mandatory_before_execute"])

    def test_ai_readiness_fails_closed_when_contract_validation_fails(self) -> None:
        from cleancli.ai_readiness import render_ai_readiness

        failed_contract = {
            "schema": "cleanmac.ai-contract-validation-summary.v1",
            "valid": False,
            "validated_schema_count": 1,
            "failure_count": 1,
            "contract_schema_coverage": {
                "registered_schema_count": 1,
                "json_schema_fragment_count": 0,
                "critical_schemas": ["cleanmac.plan.v1"],
                "critical_schema_count": 1,
                "stable_ai_schema_count": 1,
                "stable_ai_schema_fragment_count": 0,
                "missing_stable_ai_schema_fragments": ["cleanmac.plan.v1"],
            },
        }

        with patch("cleancli.ai_readiness.render_ai_contract_validation_summary", return_value=failed_contract):
            report = render_ai_readiness({"schema": "cleanmac.ai-tool-contract.v1"})

        self.assertEqual(report["schema"], "cleanmac.ai-readiness.v1")
        self.assertFalse(report["ready"])
        self.assertFalse(report["contract_validation"]["ready"])
        self.assertEqual(report["contract_validation"]["failure_count"], 1)
        coverage = report["contract_validation"]["contract_schema_coverage"]
        self.assertEqual(coverage["missing_stable_ai_schema_fragments"], ["cleanmac.plan.v1"])

    def test_ai_readiness_fails_closed_when_host_policy_validation_fails(self) -> None:
        from cleancli.ai_readiness import render_ai_readiness

        with patch(
            "cleancli.ai_readiness.validate_ai_host_policy",
            return_value={
                "schema": "cleanmac.ai-host-policy-validation.v1",
                "valid": False,
                "errors": ["bad-policy"],
            },
        ):
            report = render_ai_readiness({"schema": "cleanmac.ai-tool-contract.v1"})

        self.assertEqual(report["schema"], "cleanmac.ai-readiness.v1")
        self.assertFalse(report["ready"])
        self.assertFalse(report["host_policy"]["ready"])
        self.assertEqual(report["host_policy"]["validation"]["errors"], ["bad-policy"])


if __name__ == "__main__":
    unittest.main()
