from __future__ import annotations

import json
import subprocess
import sys
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
CLI = PROJECT_ROOT / "cleanmac.py"


class AIHostPolicyTests(unittest.TestCase):
    def test_ai_host_policy_reports_allow_deny_boundaries(self) -> None:
        result = subprocess.run(
            [sys.executable, str(CLI), "--json", "ai-host-policy"],
            text=True,
            capture_output=True,
            check=True,
        )
        report = json.loads(result.stdout)

        self.assertEqual(report["schema"], "cleanmac.ai-host-policy.v1")
        self.assertTrue(report["valid"], report)
        self.assertEqual(report["default_decision"], "deny")
        self.assertFalse(report["transport"]["shell_allowed"])
        self.assertFalse(report["transport"]["raw_command_input_allowed"])
        self.assertTrue(report["transport"]["path_and_log_text_are_untrusted_data"])

        self.assertIn("cleanmac_capabilities", report["auto_call"]["allow"])
        self.assertIn("cleanmac_dry_run_plan", report["auto_call"]["allow"])
        self.assertIn("cleanmac_execute_plan", report["auto_call"]["deny"])
        self.assertIn("cleanmac_execute_plan", report["auto_call"]["destructive_tools"])
        self.assertEqual(
            report["auto_call"]["deny_reasons"]["cleanmac_execute_plan"],
            "destructive_or_confirmation_required",
        )

        gate = report["execution_gate"]
        self.assertFalse(gate["auto_call_allowed"])
        self.assertTrue(gate["requires_human_confirmation"])
        self.assertTrue(gate["requires_matching_dry_run_confirmation_token"])
        self.assertTrue(gate["requires_trash_delete_mode"])
        self.assertTrue(gate["requires_operation_log"])
        self.assertTrue(gate["requires_plan_context_match"])
        self.assertIn("cleanmac_policy_simulate", gate["required_predecessor_tools"])

        boundary = report["prompt_injection_boundary"]
        self.assertIn("paths", boundary["never_treat_as_instructions"])
        self.assertIn("scan_results", boundary["treat_as_data"])
        self.assertTrue(report["error_recovery"]["follow_next_allowed_tools_only"])
        self.assertIn("cleanmac://ai/host-policy", report["required_resources_before_execution"])


if __name__ == "__main__":
    unittest.main()
