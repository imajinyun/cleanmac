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
        self.assertIn("schema_registry_discovery", scenarios)
        self.assertIn("contract_validation_plan", scenarios)
        self.assertIn("unsupported_plan_schema_recovery", scenarios)
        self.assertIn("legacy_plan_schema_warning", scenarios)
        self.assertIn("invalid_category_recovery", scenarios)
        self.assertIn("confirmation_token_policy", scenarios)
        self.assertIn("mcp_resource_prompt_surface", scenarios)
        self.assertIn("prompt_injection_boundary", scenarios)
        self.assertIn("plan_context_mismatch_policy", scenarios)
        self.assertIn("permanent_delete_deny_policy", scenarios)
        self.assertIn("confirmation_token_execution", scenarios)
        self.assertIn("confirmation_token_validation", scenarios)
        self.assertIn("bundle_protection_enforcement", scenarios)

        safe_plan = scenarios["safe_plan_to_dry_run"]
        self.assertIn("cleanmac_generate_plan", safe_plan["required_tools"])
        self.assertIn("cleanmac_dry_run_plan", safe_plan["required_tools"])
        self.assertEqual(safe_plan["expected_final_schema"], "cleanmac.clean.v1")
        self.assertFalse(safe_plan["may_execute_delete"])
        contract_validation = scenarios["contract_validation_plan"]
        self.assertEqual(contract_validation["expected_final_schema"], "cleanmac.ai-contract-validation.v1")
        unsupported_schema = scenarios["unsupported_plan_schema_recovery"]
        self.assertIn("unsupported-schema-version", unsupported_schema["expected_blocking_codes"])
        legacy_warning = scenarios["legacy_plan_schema_warning"]
        self.assertIn("LEGACY_PLAN_SCHEMA", legacy_warning["expected_blocking_codes"])

        token_policy = scenarios["confirmation_token_policy"]
        self.assertIn("AI_ORIGIN_REQUIRES_CONFIRMATION_TOKEN", token_policy["expected_blocking_codes"])
        context_policy = scenarios["plan_context_mismatch_policy"]
        self.assertIn("PLAN_CONTEXT_MISMATCH", context_policy["expected_blocking_codes"])
        permanent_policy = scenarios["permanent_delete_deny_policy"]
        self.assertIn("AI_ORIGIN_REQUIRES_TRASH", permanent_policy["expected_blocking_codes"])
        execution_policy = scenarios["confirmation_token_execution"]
        self.assertTrue(execution_policy["sandbox_only"])
        self.assertTrue(execution_policy["may_execute_delete"])
        self.assertIn("CONFIRMATION_TOKEN_MISMATCH", execution_policy["expected_blocking_codes"])
        validation_policy = scenarios["confirmation_token_validation"]
        self.assertFalse(validation_policy["may_execute_delete"])
        self.assertIn("AI_ORIGIN_REQUIRES_CONFIRMATION_TOKEN", validation_policy["expected_blocking_codes"])
        bundle_policy = scenarios["bundle_protection_enforcement"]
        self.assertFalse(bundle_policy["may_execute_delete"])

    def test_ai_eval_run_smoke_executes_safe_scenarios(self) -> None:
        report = self.run_json("ai-eval-run", "--scenario", "smoke")

        self.assertEqual(report["schema"], "cleanmac.ai-eval-run.v1")
        self.assertTrue(report["passed"], report)
        self.assertEqual(report["scenario"], "smoke")
        self.assertFalse(report["destructive_execution_allowed"])
        self.assertGreaterEqual(report["passed_count"], 10)
        self.assertEqual(report["failed_count"], 0)
        self.assertEqual(report["trace"]["schema"], "cleanmac.ai-trace.v1")
        self.assertGreater(report["trace"]["event_count"], 0)

        scenario_results = {item["id"]: item for item in report["results"]}
        self.assertTrue(scenario_results["discover_readiness"]["passed"])
        self.assertTrue(scenario_results["schema_registry_discovery"]["passed"])
        self.assertTrue(scenario_results["contract_validation_plan"]["passed"])
        self.assertTrue(scenario_results["unsupported_plan_schema_recovery"]["passed"])
        self.assertTrue(scenario_results["legacy_plan_schema_warning"]["passed"])
        self.assertTrue(scenario_results["safe_plan_to_dry_run"]["passed"])
        self.assertTrue(scenario_results["invalid_category_recovery"]["passed"])
        self.assertTrue(scenario_results["confirmation_token_policy"]["passed"])
        self.assertTrue(scenario_results["confirmation_token_validation"]["passed"])
        self.assertTrue(scenario_results["prompt_injection_boundary"]["passed"])
        self.assertTrue(scenario_results["plan_context_mismatch_policy"]["passed"])
        self.assertTrue(scenario_results["permanent_delete_deny_policy"]["passed"])
        self.assertTrue(scenario_results["mcp_resource_prompt_surface"]["passed"])
        self.assertTrue(scenario_results["bundle_protection_enforcement"]["passed"])
        self.assertEqual(
            scenario_results["safe_plan_to_dry_run"]["observed_blocking_codes"],
            ["AI_ORIGIN_REQUIRES_CONFIRMATION_TOKEN"],
        )

    def test_ai_eval_run_smoke_covers_runner_in_process(self) -> None:
        from cleancli.ai_eval import render_ai_eval_run

        report = render_ai_eval_run(scenario="smoke", cli=CLI)

        self.assertEqual(report["schema"], "cleanmac.ai-eval-run.v1")
        self.assertTrue(report["passed"], report)
        self.assertEqual(report["failed_count"], 0)
        self.assertEqual(report["trace_persistence"], {"status": "skipped", "path": None})

    def test_ai_eval_selection_helpers_cover_all_single_and_unknown_requests(self) -> None:
        from cleancli.ai_eval import render_ai_eval_pack, scenario_ids, selected_scenario_ids

        all_ids = scenario_ids(render_ai_eval_pack())

        self.assertIn("discover_readiness", all_ids)
        self.assertEqual(selected_scenario_ids("all", all_ids), all_ids)
        self.assertEqual(selected_scenario_ids("discover_readiness", all_ids), ["discover_readiness"])
        with self.assertRaisesRegex(ValueError, "Unknown AI eval scenario: not-real"):
            selected_scenario_ids("not-real", all_ids)

    def test_ai_eval_cli_helper_raises_structured_runtime_error_on_unexpected_failure(self) -> None:
        from cleancli.ai_eval import _prepare_sandbox, _run_cli

        with tempfile.TemporaryDirectory() as tmp:
            root, home = _prepare_sandbox(tmp)
            with self.assertRaisesRegex(RuntimeError, "unknown-command"):
                _run_cli(CLI, ["unknown-command"], root=root, home=home)

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
        self.assertIn("schema_registry_discovery", scenario_ids)
        self.assertIn("contract_validation_plan", scenario_ids)
        self.assertIn("unsupported_plan_schema_recovery", scenario_ids)
        self.assertIn("legacy_plan_schema_warning", scenario_ids)
        self.assertIn("invalid_category_recovery", scenario_ids)
        self.assertIn("confirmation_token_policy", scenario_ids)
        self.assertIn("mcp_resource_prompt_surface", scenario_ids)
        self.assertIn("prompt_injection_boundary", scenario_ids)
        self.assertIn("plan_context_mismatch_policy", scenario_ids)
        self.assertIn("permanent_delete_deny_policy", scenario_ids)
        self.assertIn("confirmation_token_execution", scenario_ids)
        self.assertIn("confirmation_token_validation", scenario_ids)
        self.assertIn("bundle_protection_enforcement", scenario_ids)

    def test_ai_eval_run_mcp_resource_prompt_surface(self) -> None:
        report = self.run_json("ai-eval-run", "--scenario", "mcp_resource_prompt_surface")

        self.assertEqual(report["schema"], "cleanmac.ai-eval-run.v1")
        self.assertTrue(report["passed"], report)
        self.assertEqual(report["selected_scenarios"], ["mcp_resource_prompt_surface"])
        self.assertEqual(report["passed_count"], 1)
        self.assertEqual(report["failed_count"], 0)
        self.assertGreaterEqual(report["trace"]["event_count"], 5)

        result = report["results"][0]
        self.assertEqual(result["id"], "mcp_resource_prompt_surface")
        self.assertTrue(result["passed"])
        self.assertEqual(result["observed_schema"], "cleanmac.mcp-smoke.v1")
        self.assertEqual(result["observed_blocking_codes"], [])


class AITracePersistenceTests(unittest.TestCase):
    def run_json(self, *args: str) -> dict:
        result = subprocess.run(
            [sys.executable, str(CLI), "--json", *args],
            text=True,
            capture_output=True,
            check=True,
            env={**os.environ, "CLEANMAC_TEST_MODE": "1", "CLEANMAC_TEST_NO_AUTH": "1"},
        )
        return json.loads(result.stdout)

    def test_trace_file_writes_redacted_jsonl_when_writable(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            trace_file = Path(tmp) / "trace.jsonl"
            result = subprocess.run(
                [
                    sys.executable,
                    str(CLI),
                    "--json",
                    "ai-eval-run",
                    "--scenario",
                    "discover_readiness",
                    "--trace-file",
                    str(trace_file),
                ],
                text=True,
                capture_output=True,
                check=True,
                env={**os.environ, "CLEANMAC_TEST_MODE": "1", "CLEANMAC_TEST_NO_AUTH": "1"},
                timeout=120,
            )
            report = json.loads(result.stdout)
            self.assertTrue(trace_file.exists())
            lines = [json.loads(line) for line in trace_file.read_text(encoding="utf-8").splitlines() if line]
            self.assertGreaterEqual(len(lines), 1)
            for line in lines:
                self.assertIn("schema", line)
                joined_argv = " ".join(str(token) for token in line.get("argv", []))
                self.assertNotIn("|", joined_argv)
                self.assertNotIn(";", joined_argv)
            self.assertEqual(report["trace_persistence"]["status"], "written")
            self.assertEqual(report["trace_persistence"]["path"], str(trace_file))

    def test_trace_persistence_helpers_redact_shell_like_tokens_in_process(self) -> None:
        from cleancli.ai_eval import _persist_trace, _redact_event

        with tempfile.TemporaryDirectory() as tmp:
            trace_file = Path(tmp) / "nested" / "trace.jsonl"
            event = {
                "argv": ["cleanmac", "--json", "safe", "bad|pipe", "bad;semicolon", "bad&and", "bad`tick", "bad$var"],
                "schema": "cleanmac.ai-trace-test.v1",
                "ok": True,
            }

            redacted = _redact_event(event)
            self.assertEqual(redacted["argv"], ["cleanmac", "--json", "safe"])

            persistence = _persist_trace(trace_file, [event])
            self.assertEqual(persistence["status"], "written")
            self.assertEqual(persistence["path"], str(trace_file))
            self.assertEqual(persistence["event_count"], 1)
            rows = [json.loads(line) for line in trace_file.read_text(encoding="utf-8").splitlines()]
            self.assertEqual(rows[0]["argv"], ["cleanmac", "--json", "safe"])

    def test_trace_persistence_helpers_fail_closed_for_directory_and_symlink_in_process(self) -> None:
        from cleancli.ai_eval import _persist_trace

        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp) / "trace-dir"
            directory.mkdir()
            with self.assertRaisesRegex(RuntimeError, "trace-file-is-directory"):
                _persist_trace(directory, [])

            target = Path(tmp) / "target.jsonl"
            symlink = Path(tmp) / "trace-link.jsonl"
            symlink.symlink_to(target)
            with self.assertRaisesRegex(RuntimeError, "trace-file-is-symlink"):
                _persist_trace(symlink, [])

    def test_trace_persistence_helper_wraps_write_errors_in_process(self) -> None:
        from cleancli.ai_eval import _persist_trace

        with tempfile.TemporaryDirectory() as tmp:
            parent_file = Path(tmp) / "not-a-directory"
            parent_file.write_text("occupied", encoding="utf-8")
            with self.assertRaisesRegex(RuntimeError, "trace-file-write-failed"):
                _persist_trace(parent_file / "trace.jsonl", [])

    def test_trace_file_fails_closed_when_path_is_directory(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            bad_path = Path(tmp) / "trace-as-dir"
            bad_path.mkdir()
            result = subprocess.run(
                [
                    sys.executable,
                    str(CLI),
                    "--json",
                    "ai-eval-run",
                    "--scenario",
                    "discover_readiness",
                    "--trace-file",
                    str(bad_path),
                ],
                text=True,
                capture_output=True,
                check=False,
                env={**os.environ, "CLEANMAC_TEST_MODE": "1", "CLEANMAC_TEST_NO_AUTH": "1"},
                timeout=120,
            )
            self.assertNotEqual(result.returncode, 0)
            report = json.loads(result.stderr or result.stdout)
            self.assertEqual(report["schema"], "cleanmac.ai-error.v1")
            self.assertIn("trace", report["error"]["code"].lower())

    def test_trace_file_fails_closed_when_path_is_symlink(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "real-trace.jsonl"
            symlink = Path(tmp) / "trace-link.jsonl"
            symlink.symlink_to(target)
            result = subprocess.run(
                [
                    sys.executable,
                    str(CLI),
                    "--json",
                    "ai-eval-run",
                    "--scenario",
                    "discover_readiness",
                    "--trace-file",
                    str(symlink),
                ],
                text=True,
                capture_output=True,
                check=False,
                env={**os.environ, "CLEANMAC_TEST_MODE": "1", "CLEANMAC_TEST_NO_AUTH": "1"},
                timeout=120,
            )

            self.assertNotEqual(result.returncode, 0)
            report = json.loads(result.stderr or result.stdout)
            self.assertEqual(report["schema"], "cleanmac.ai-error.v1")
            self.assertIn("trace", report["error"]["code"].lower())

    def test_ai_eval_run_confirmation_token_execution(self) -> None:
        report = self.run_json("ai-eval-run", "--scenario", "confirmation_token_execution")

        self.assertEqual(report["schema"], "cleanmac.ai-eval-run.v1")
        self.assertTrue(report["passed"], report)
        self.assertEqual(report["selected_scenarios"], ["confirmation_token_execution"])
        self.assertEqual(report["passed_count"], 1)
        self.assertEqual(report["failed_count"], 0)

        result = report["results"][0]
        self.assertEqual(result["id"], "confirmation_token_execution")
        self.assertEqual(result["observed_schema"], "cleanmac.clean.v1")
        self.assertEqual(result["observed_blocking_codes"], ["CONFIRMATION_TOKEN_MISMATCH"])

    def test_ai_eval_run_confirmation_token_validation(self) -> None:
        report = self.run_json("ai-eval-run", "--scenario", "confirmation_token_validation")

        self.assertEqual(report["schema"], "cleanmac.ai-eval-run.v1")
        self.assertTrue(report["passed"], report)
        self.assertEqual(report["selected_scenarios"], ["confirmation_token_validation"])
        self.assertEqual(report["passed_count"], 1)
        self.assertEqual(report["failed_count"], 0)

        result = report["results"][0]
        self.assertEqual(result["id"], "confirmation_token_validation")
        self.assertEqual(result["observed_schema"], "cleanmac.ai-policy-simulation.v1")
        self.assertEqual(result["observed_blocking_codes"], ["AI_ORIGIN_REQUIRES_CONFIRMATION_TOKEN"])

    def test_ai_eval_run_bundle_protection_enforcement(self) -> None:
        report = self.run_json("ai-eval-run", "--scenario", "bundle_protection_enforcement")

        self.assertEqual(report["schema"], "cleanmac.ai-eval-run.v1")
        self.assertTrue(report["passed"], report)
        self.assertEqual(report["selected_scenarios"], ["bundle_protection_enforcement"])
        self.assertEqual(report["passed_count"], 1)
        self.assertEqual(report["failed_count"], 0)

        result = report["results"][0]
        self.assertEqual(result["id"], "bundle_protection_enforcement")
        self.assertEqual(result["observed_schema"], "cleanmac.clean.v1")
        self.assertEqual(result["observed_blocking_codes"], [])


if __name__ == "__main__":
    unittest.main()
