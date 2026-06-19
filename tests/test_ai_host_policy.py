from __future__ import annotations

import json
import subprocess
import sys
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
CLI = PROJECT_ROOT / "cleanmac.py"


class AIHostPolicyTests(unittest.TestCase):
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


if __name__ == "__main__":
    unittest.main()