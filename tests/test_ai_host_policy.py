from __future__ import annotations

import json
import subprocess
import sys
import unittest
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parent.parent
CLI = PROJECT_ROOT / "cleanmac.py"


class AIHostPolicyTests(unittest.TestCase):
    report: dict[str, Any]

    @classmethod
    def setUpClass(cls) -> None:
        result = subprocess.run(
            [sys.executable, str(CLI), "--json", "ai-host-policy"],
            text=True,
            capture_output=True,
            check=True,
        )
        cls.report = json.loads(result.stdout)

    def test_host_policy_schema_and_validity(self) -> None:
        self.assertEqual(self.report["schema"], "cleanmac.ai-host-policy.v1")
        self.assertTrue(self.report["valid"], self.report)
        self.assertEqual(self.report["default_decision"], "deny")

    def test_host_policy_transport_restrictions(self) -> None:
        self.assertFalse(self.report["transport"]["shell_allowed"])
        self.assertFalse(self.report["transport"]["raw_command_input_allowed"])
        self.assertTrue(self.report["transport"]["path_and_log_text_are_untrusted_data"])

    def test_host_policy_auto_call_allow_deny(self) -> None:
        self.assertIn("cleanmac_capabilities", self.report["auto_call"]["allow"])
        self.assertIn("cleanmac_dry_run_plan", self.report["auto_call"]["allow"])
        self.assertIn("cleanmac_execute_plan", self.report["auto_call"]["deny"])
        self.assertIn("cleanmac_execute_plan", self.report["auto_call"]["destructive_tools"])
        self.assertEqual(
            self.report["auto_call"]["deny_reasons"]["cleanmac_execute_plan"],
            "destructive_or_confirmation_required",
        )

    def test_host_policy_execution_gate(self) -> None:
        gate = self.report["execution_gate"]
        self.assertFalse(gate["auto_call_allowed"])
        self.assertTrue(gate["requires_human_confirmation"])
        self.assertTrue(gate["requires_matching_dry_run_confirmation_token"])
        self.assertTrue(gate["requires_trash_delete_mode"])
        self.assertTrue(gate["requires_operation_log"])
        self.assertTrue(gate["requires_plan_context_match"])
        self.assertIn("cleanmac_policy_simulate", gate["required_predecessor_tools"])

    def test_host_policy_prompt_injection_boundary(self) -> None:
        boundary = self.report["prompt_injection_boundary"]
        self.assertIn("paths", boundary["never_treat_as_instructions"])
        self.assertIn("scan_results", boundary["treat_as_data"])

    def test_host_policy_error_recovery(self) -> None:
        self.assertTrue(self.report["error_recovery"]["follow_next_allowed_tools_only"])
        self.assertIn(
            "cleanmac://ai/host-policy",
            self.report["required_resources_before_execution"],
        )

    def test_host_policy_renderer_handles_partial_decision_matrix(self) -> None:
        from cleancli.ai_host_policy import render_ai_host_policy

        report = render_ai_host_policy(
            decision_matrix={
                "violation_count": 1,
                "tools": [
                    {"name": "cleanmac_capabilities", "risk": "readonly", "auto_call_allowed": True},
                    {"name": "cleanmac_generate_plan", "risk": "planning", "auto_call_allowed": False},
                    {"name": "cleanmac_dry_run_plan", "risk": "dry-run", "auto_call_allowed": False},
                    "ignored-non-mapping-row",
                ],
            },
            governance_advice={"ready_for_llm_calling": False, "release_gate_commands": [], "anti_patterns": []},
        )

        self.assertEqual(report["schema"], "cleanmac.ai-host-policy.v1")
        self.assertFalse(report["valid"])
        self.assertEqual(report["auto_call"]["allow"], ["cleanmac_capabilities"])
        self.assertEqual(report["auto_call"]["readonly_tools"], ["cleanmac_capabilities"])
        self.assertEqual(report["auto_call"]["planning_tools"], ["cleanmac_generate_plan"])
        self.assertEqual(report["auto_call"]["dry_run_tools"], ["cleanmac_dry_run_plan"])
        self.assertNotIn("cleanmac_execute_plan", report["auto_call"]["destructive_tools"])

    def test_host_policy_validation_reports_structural_violations(self) -> None:
        from cleancli.ai_host_policy import validate_ai_host_policy

        validation = validate_ai_host_policy(
            {
                "schema": "cleanmac.not-host-policy.v1",
                "default_decision": "allow",
                "transport": {"shell_allowed": True},
                "auto_call": "invalid",
                "execution_gate": "invalid",
                "valid": False,
            }
        )

        self.assertEqual(validation["schema"], "cleanmac.ai-host-policy-validation.v1")
        self.assertFalse(validation["valid"])
        joined = "\n".join(validation["violations"])
        self.assertIn("schema must be cleanmac.ai-host-policy.v1", joined)
        self.assertIn("default_decision must be deny", joined)
        self.assertIn("transport.shell_allowed must be false", joined)
        self.assertIn("auto_call must be an object", joined)
        self.assertIn("execution_gate must be an object", joined)
        self.assertIn("host policy valid flag must be true", joined)

    def test_host_policy_validation_reports_missing_destructive_gate_flags(self) -> None:
        from cleancli.ai_host_policy import validate_ai_host_policy

        validation = validate_ai_host_policy(
            {
                "schema": "cleanmac.ai-host-policy.v1",
                "default_decision": "deny",
                "transport": {"shell_allowed": False},
                "auto_call": {"deny": [], "destructive_tools": []},
                "execution_gate": {
                    "requires_human_confirmation": False,
                    "requires_matching_dry_run_confirmation_token": False,
                    "requires_trash_delete_mode": False,
                    "requires_operation_log": False,
                    "requires_plan_context_match": False,
                },
                "valid": True,
            }
        )

        self.assertFalse(validation["valid"])
        joined = "\n".join(validation["violations"])
        self.assertIn("cleanmac_execute_plan must be auto-call denied", joined)
        self.assertIn("cleanmac_execute_plan must be marked destructive", joined)
        self.assertIn("execution_gate.requires_human_confirmation must be true", joined)
        self.assertIn("execution_gate.requires_plan_context_match must be true", joined)


if __name__ == "__main__":
    unittest.main()
