from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
CLI = PROJECT_ROOT / "cleanmac.py"
SAFE_PLAN_TO_DRY_RUN_SCENARIO = "safe_plan_to_dry_run"
ONE_SHOT_GOVERNED_WORKFLOW_SCENARIO = "one_shot_governed_workflow"
INVALID_CATEGORY_RECOVERY_SCENARIO = "invalid_category_recovery"
CONFIRMATION_TOKEN_POLICY_SCENARIO = "confirmation_token_policy"


def run_cli(*args: str, root: Path, home: Path) -> dict:
    env = os.environ.copy()
    env["CLEANMAC_TEST_MODE"] = "1"
    env["CLEANMAC_TEST_NO_AUTH"] = "1"
    result = subprocess.run(
        [sys.executable, str(CLI), "--json", "--root", str(root), "--home", str(home), *args],
        text=True,
        capture_output=True,
        check=True,
        env=env,
    )
    return json.loads(result.stdout)


def run_cli_process(*args: str, root: Path, home: Path) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env["CLEANMAC_TEST_MODE"] = "1"
    env["CLEANMAC_TEST_NO_AUTH"] = "1"
    return subprocess.run(
        [sys.executable, str(CLI), "--json", "--root", str(root), "--home", str(home), *args],
        text=True,
        capture_output=True,
        check=False,
        env=env,
    )


class AIHostScenarioTests(unittest.TestCase):
    def test_one_shot_governed_workflow_exposes_safe_cleanup_route(self) -> None:
        self.assertEqual(ONE_SHOT_GOVERNED_WORKFLOW_SCENARIO, "one_shot_governed_workflow")
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "root"
            home = root / "Users" / "tester"
            home.mkdir(parents=True)

            report = run_cli(
                "ai-workflow",
                "--goal",
                "safe-cleanup",
                "--categories",
                "trash,downloads,xcode",
                root=root,
                home=home,
            )
            steps = {step["id"]: step for step in report["steps"]}

            self.assertEqual(report["schema"], "cleanmac.ai-workflow.v1")
            self.assertFalse(report["destructive"])
            self.assertTrue(report["dry_run"])
            self.assertIn("cleanmac_policy_simulate", report["recommended_tool_call_order"])
            self.assertEqual(steps["simulate_execute_policy"]["output_schema"], "cleanmac.ai-policy-simulation.v1")
            self.assertEqual(steps["simulate_execute_policy"]["input_schema"]["type"], "object")
            self.assertEqual(steps["simulate_execute_policy"]["input"]["delete_mode"], "trash")
            self.assertFalse(steps["execute_after_human_confirmation"]["auto_call_allowed"])
            self.assertTrue(steps["execute_after_human_confirmation"]["requires_human_confirmation"])
            self.assertEqual(report["governance"]["delete_mode_for_execute"], "trash")
            self.assertFalse(report["governance"]["destructive_auto_call_allowed"])

    def test_safe_ai_host_plan_to_dry_run_sequence(self) -> None:
        self.assertEqual(SAFE_PLAN_TO_DRY_RUN_SCENARIO, "safe_plan_to_dry_run")
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "root"
            home = root / "Users" / "tester"
            trash = home / ".Trash"
            downloads = home / "Downloads"
            downloads.mkdir(parents=True)
            trash.mkdir(parents=True)
            candidate = downloads / "old-cache.tmp"
            candidate.write_text("cache", encoding="utf-8")
            plan_file = Path(tmp) / "plan.json"

            capabilities = run_cli("capabilities", root=root, home=home)
            self.assertEqual(capabilities["schema"], "cleanmac.capabilities.v1")
            self.assertTrue(capabilities["ai_readiness"]["ready"])

            plan = run_cli("clean", "plan", "--categories", "downloads", "--ai-origin", root=root, home=home)
            plan_file.write_text(json.dumps(plan), encoding="utf-8")
            self.assertEqual(plan["schema"], "cleanmac.plan.v1")
            self.assertTrue(plan["ai_origin"])

            validation = run_cli("clean", "validate-plan", "--plan-file", str(plan_file), root=root, home=home)
            self.assertTrue(validation["valid"], validation)

            simulation = run_cli(
                "clean",
                "policy-simulate",
                "--plan-file",
                str(plan_file),
                "--execute",
                "--delete-mode",
                "trash",
                "--require-plan-context",
                "--require-confirmation-token",
                root=root,
                home=home,
            )
            self.assertFalse(simulation["allowed"])
            blocking_codes = {row["code"] for row in simulation["blocking_reasons"]}
            self.assertIn("AI_ORIGIN_REQUIRES_CONFIRMATION_TOKEN", blocking_codes)

            dry_run = run_cli(
                "clean", "run", "--plan-file", str(plan_file), "--delete-mode", "trash", root=root, home=home
            )
            self.assertTrue(dry_run["dry_run"])
            self.assertTrue(dry_run["ai_confirmation_summary"]["confirmation_token_embedded"])
            self.assertEqual(dry_run["human_summary"]["schema"], "cleanmac.human-summary.v1")
            self.assertFalse(dry_run["human_summary"]["safe_to_execute"])
            self.assertIn("--execute", dry_run["human_summary"]["next_command"])
            self.assertIn("--confirmation-token", dry_run["human_summary"]["next_command"])
            self.assertTrue(dry_run["human_summary"]["top_reasons_to_review"])

            review = run_cli("review", "--input-file", str(plan_file), root=root, home=home)
            self.assertEqual(review["human_summary"]["schema"], "cleanmac.human-summary.v1")
            self.assertFalse(review["human_summary"]["safe_to_execute"])
            self.assertIn("Review selected", review["human_summary"]["headline"])
            self.assertIn("--review-selection-file", review["human_summary"]["next_command"])

    def test_ai_host_policy_simulate_allows_execute_intent_with_dry_run_token(self) -> None:
        self.assertEqual(CONFIRMATION_TOKEN_POLICY_SCENARIO, "confirmation_token_policy")
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "root"
            home = root / "Users" / "tester"
            trash = home / ".Trash"
            downloads = home / "Downloads"
            downloads.mkdir(parents=True)
            trash.mkdir(parents=True)
            (downloads / "old-cache.tmp").write_text("cache", encoding="utf-8")
            plan_file = Path(tmp) / "plan.json"
            operation_log = Path(tmp) / "operations.jsonl"

            plan = run_cli("clean", "plan", "--categories", "downloads", "--ai-origin", root=root, home=home)
            plan_file.write_text(json.dumps(plan), encoding="utf-8")
            dry_run = run_cli(
                "clean",
                "run",
                "--plan-file",
                str(plan_file),
                "--delete-mode",
                "trash",
                root=root,
                home=home,
            )
            token = dry_run["ai_confirmation_summary"]["confirmation_token"]

            simulation = run_cli(
                "clean",
                "policy-simulate",
                "--plan-file",
                str(plan_file),
                "--execute",
                "--delete-mode",
                "trash",
                "--operation-log",
                str(operation_log),
                "--require-plan-context",
                "--require-confirmation-token",
                "--confirmation-token",
                token,
                root=root,
                home=home,
            )

            self.assertTrue(simulation["allowed"], simulation)
            self.assertFalse(simulation["blocking_reasons"], simulation["blocking_reasons"])
            decisions = {row["rule"]: row["result"] for row in simulation["policy_decisions"]}
            self.assertEqual(decisions["ai_origin_requires_confirmation_token"], "pass")
            self.assertEqual(decisions["ai_origin_requires_operation_log"], "pass")
            self.assertEqual(decisions["plan_context_matches"], "pass")

    def test_prompt_injection_boundary_path_text_treated_as_data(self) -> None:
        """Verify the host policy declares that paths and filenames are treated as untrusted data."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "root"
            home = root / "Users" / "tester"
            home.mkdir(parents=True)

            result = run_cli(
                "ai-governance-advice",
                root=root,
                home=home,
            )

            self.assertEqual(result["schema"], "cleanmac.ai-governance-advice.v1")
            host_controls = result.get("required_host_controls", [])
            path_data_statements = [
                c
                for c in host_controls
                if "path" in str(c).lower() or "data" in str(c).lower() or "untrusted" in str(c).lower()
            ]
            self.assertGreaterEqual(
                len(path_data_statements),
                1,
                "Host controls must include path/data/untrusted handling",
            )

    def test_plan_context_mismatch_policy_blocks_execution(self) -> None:
        """Verify execution intent is blocked when plan root/home differs from sandbox context."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "root"
            home = root / "Users" / "tester"
            other_root = Path(tmp) / "other_root"
            other_home = other_root / "Users" / "other"
            downloads = home / "Downloads"
            downloads.mkdir(parents=True)
            (downloads / "old-cache.tmp").write_text("cache", encoding="utf-8")
            plan_file = Path(tmp) / "plan.json"
            operation_log = Path(tmp) / "operations.jsonl"

            plan = run_cli("clean", "plan", "--categories", "downloads", "--ai-origin", root=root, home=home)
            plan_file.write_text(json.dumps(plan), encoding="utf-8")

            plan_for_token = run_cli(
                "clean", "run", "--plan-file", str(plan_file), "--delete-mode", "trash", root=root, home=home
            )
            token = plan_for_token["ai_confirmation_summary"]["confirmation_token"]

            result = run_cli(
                "clean",
                "policy-simulate",
                "--plan-file",
                str(plan_file),
                "--execute",
                "--delete-mode",
                "trash",
                "--operation-log",
                str(operation_log),
                "--require-plan-context",
                "--require-confirmation-token",
                "--confirmation-token",
                token,
                root=other_root,
                home=other_home,
            )

            self.assertFalse(result["allowed"], "Policy simulate with mismatched context should be denied")
            blocking_codes = {row["code"] for row in result["blocking_reasons"]}
            self.assertIn(
                "PLAN_CONTEXT_MISMATCH",
                blocking_codes,
                f"Expected PLAN_CONTEXT_MISMATCH in blocking reasons, got: {blocking_codes}",
            )

    def test_permanent_delete_deny_policy_blocks_ai_origin(self) -> None:
        """Verify AI-originated execute intent using permanent delete mode is blocked by policy."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "root"
            home = root / "Users" / "tester"
            downloads = home / "Downloads"
            downloads.mkdir(parents=True)
            (downloads / "old-cache.tmp").write_text("cache", encoding="utf-8")
            plan_file = Path(tmp) / "plan.json"
            operation_log = Path(tmp) / "operations.jsonl"

            plan = run_cli("clean", "plan", "--categories", "downloads", "--ai-origin", root=root, home=home)
            plan_file.write_text(json.dumps(plan), encoding="utf-8")

            plan_for_token = run_cli(
                "clean", "run", "--plan-file", str(plan_file), "--delete-mode", "trash", root=root, home=home
            )
            token = plan_for_token["ai_confirmation_summary"]["confirmation_token"]

            result = run_cli(
                "clean",
                "policy-simulate",
                "--plan-file",
                str(plan_file),
                "--execute",
                "--delete-mode",
                "permanent",
                "--operation-log",
                str(operation_log),
                "--require-plan-context",
                "--require-confirmation-token",
                "--confirmation-token",
                token,
                root=root,
                home=home,
            )

            self.assertFalse(result["allowed"], "Permanent delete simulate with AI origin should be denied")
            blocking_codes = {row["code"] for row in result["blocking_reasons"]}
            self.assertIn(
                "AI_ORIGIN_REQUIRES_TRASH",
                blocking_codes,
                f"Expected AI_ORIGIN_REQUIRES_TRASH in blocking reasons, got: {blocking_codes}",
            )

    def test_ai_host_invalid_category_error_is_machine_readable(self) -> None:
        self.assertEqual(INVALID_CATEGORY_RECOVERY_SCENARIO, "invalid_category_recovery")
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "root"
            home = root / "Users" / "tester"
            home.mkdir(parents=True)

            result = run_cli_process("clean", "inspect", "--categories", "notACategory", root=root, home=home)

            self.assertNotEqual(result.returncode, 0)
            report = json.loads(result.stderr)
            self.assertEqual(report["schema"], "cleanmac.ai-error.v1")
            self.assertEqual(report["error"]["code"], "UNKNOWN_CATEGORY")
            self.assertTrue(report["error"]["retryable_after_fix"])
            self.assertIn("cleanmac_list_categories", report["error"]["next_allowed_tools"])


if __name__ == "__main__":
    unittest.main()
