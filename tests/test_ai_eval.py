from __future__ import annotations

import json
import subprocess
import sys
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
CLI = PROJECT_ROOT / "cleanmac.py"


class AIEvalTests(unittest.TestCase):
    def run_json(self, *args: str) -> dict:
        result = subprocess.run(
            [sys.executable, str(CLI), "--json", *args],
            text=True,
            capture_output=True,
            check=True,
        )
        return json.loads(result.stdout)

    def test_ai_eval_pack_lists_safe_host_scenarios(self) -> None:
        report = self.run_json("ai-eval-pack")

        self.assertEqual(report["schema"], "cleanmac.ai-eval-pack.v1")
        self.assertFalse(report["uses_shell"])
        self.assertFalse(report["allows_destructive_execution"])
        self.assertEqual(report["scenario_count"], len(report["scenarios"]))

        scenarios = {scenario["id"]: scenario for scenario in report["scenarios"]}
        self.assertIn("discover_readiness", scenarios)
        self.assertIn("safe_plan_to_dry_run", scenarios)
        self.assertIn("invalid_category_recovery", scenarios)
        self.assertIn("confirmation_token_policy", scenarios)
        self.assertIn("mcp_resource_prompt_surface", scenarios)
        self.assertIn("prompt_injection_boundary", scenarios)
        self.assertIn("plan_context_mismatch_policy", scenarios)
        self.assertIn("permanent_delete_deny_policy", scenarios)

        safe_plan = scenarios["safe_plan_to_dry_run"]
        self.assertIn("cleanmac_generate_plan", safe_plan["required_tools"])
        self.assertIn("cleanmac_dry_run_plan", safe_plan["required_tools"])
        self.assertEqual(safe_plan["expected_final_schema"], "cleanmac.clean-report.v1")
        self.assertFalse(safe_plan["may_execute_delete"])

        token_policy = scenarios["confirmation_token_policy"]
        self.assertIn("AI_ORIGIN_REQUIRES_CONFIRMATION_TOKEN", token_policy["expected_blocking_codes"])
        context_policy = scenarios["plan_context_mismatch_policy"]
        self.assertIn("PLAN_CONTEXT_MISMATCH", context_policy["expected_blocking_codes"])
        permanent_policy = scenarios["permanent_delete_deny_policy"]
        self.assertIn("AI_ORIGIN_REQUIRES_TRASH", permanent_policy["expected_blocking_codes"])

    def test_ai_eval_run_smoke_executes_safe_scenarios(self) -> None:
        report = self.run_json("ai-eval-run", "--scenario", "smoke")

        self.assertEqual(report["schema"], "cleanmac.ai-eval-run.v1")
        self.assertTrue(report["passed"], report)
        self.assertEqual(report["scenario"], "smoke")
        self.assertFalse(report["destructive_execution_allowed"])
        self.assertGreaterEqual(report["passed_count"], 7)
        self.assertEqual(report["failed_count"], 0)
        self.assertEqual(report["trace"]["schema"], "cleanmac.ai-trace.v1")
        self.assertGreater(report["trace"]["event_count"], 0)

        scenario_results = {item["id"]: item for item in report["results"]}
        self.assertTrue(scenario_results["discover_readiness"]["passed"])
        self.assertTrue(scenario_results["safe_plan_to_dry_run"]["passed"])
        self.assertTrue(scenario_results["invalid_category_recovery"]["passed"])
        self.assertTrue(scenario_results["confirmation_token_policy"]["passed"])
        self.assertTrue(scenario_results["prompt_injection_boundary"]["passed"])
        self.assertTrue(scenario_results["plan_context_mismatch_policy"]["passed"])
        self.assertTrue(scenario_results["permanent_delete_deny_policy"]["passed"])
        self.assertEqual(
            scenario_results["safe_plan_to_dry_run"]["observed_blocking_codes"],
            ["AI_ORIGIN_REQUIRES_CONFIRMATION_TOKEN"],
        )

    def test_ai_eval_run_rejects_unknown_scenario(self) -> None:
        result = subprocess.run(
            [sys.executable, str(CLI), "--json", "ai-eval-run", "--scenario", "not-real"],
            text=True,
            capture_output=True,
            check=False,
        )

        self.assertNotEqual(result.returncode, 0)
        report = json.loads(result.stderr)
        self.assertEqual(report["schema"], "cleanmac.ai-error.v1")
        self.assertEqual(report["error"]["code"], "AI_EVAL_UNKNOWN_SCENARIO")
        self.assertIn("ai-eval-pack", report["error"]["next_allowed_commands"])

    def test_eval_pack_scenario_ids_match_ai_host_regressions(self) -> None:
        report = self.run_json("ai-eval-pack")
        scenario_ids = {scenario["id"] for scenario in report["scenarios"]}

        self.assertIn("safe_plan_to_dry_run", scenario_ids)
        self.assertIn("invalid_category_recovery", scenario_ids)
        self.assertIn("confirmation_token_policy", scenario_ids)
        self.assertIn("prompt_injection_boundary", scenario_ids)
        self.assertIn("plan_context_mismatch_policy", scenario_ids)
        self.assertIn("permanent_delete_deny_policy", scenario_ids)


if __name__ == "__main__":
    unittest.main()
