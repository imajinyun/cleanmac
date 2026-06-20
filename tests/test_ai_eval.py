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
        self.assertIn("host_integration_pack_discovery", scenarios)
        self.assertIn("host_preflight_discovery", scenarios)
        self.assertIn("host_evidence_discovery", scenarios)
        self.assertIn("host_evidence_runtime_denial_coverage", scenarios)
        self.assertIn("release_readiness_discovery", scenarios)
        self.assertIn("release_readiness_artifact_missing_blocks", scenarios)
        self.assertIn("release_readiness_artifact_present_ready", scenarios)
        self.assertIn("release_evidence_bundle_discovery", scenarios)
        self.assertIn("release_diagnostics_explains_readiness_failure", scenarios)
        self.assertIn("release_rehearsal_discovery", scenarios)
        self.assertIn("release_promotion_decision_blocks_missing_evidence", scenarios)
        self.assertIn("release_rollback_plan_discovery", scenarios)
        self.assertIn("release_post_publish_verification_discovery", scenarios)
        self.assertIn("release_post_publish_result_discovery", scenarios)
        self.assertIn("release_post_publish_evidence_template_discovery", scenarios)
        self.assertIn("schema_registry_release_contract_coverage", scenarios)
        self.assertIn("discover_readiness", scenarios)
        self.assertIn("safe_plan_to_dry_run", scenarios)
        self.assertIn("schema_registry_discovery", scenarios)
        self.assertIn("contract_validation_plan", scenarios)
        self.assertIn("contract_samples_roundtrip", scenarios)
        self.assertIn("unsupported_plan_schema_recovery", scenarios)
        self.assertIn("legacy_plan_schema_warning", scenarios)
        self.assertIn("invalid_category_recovery", scenarios)
        self.assertIn("confirmation_token_policy", scenarios)
        self.assertIn("mcp_resource_prompt_surface", scenarios)
        self.assertIn("mcp_raw_command_argument_denial", scenarios)
        self.assertIn("mcp_destructive_policy_denial", scenarios)
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
        contract_samples = scenarios["contract_samples_roundtrip"]
        self.assertEqual(contract_samples["expected_final_schema"], "cleanmac.ai-contract-samples.v1")
        self.assertFalse(contract_samples["may_execute_delete"])
        integration_pack = scenarios["host_integration_pack_discovery"]
        self.assertEqual(integration_pack["expected_final_schema"], "cleanmac.ai-host-integration-pack.v1")
        self.assertFalse(integration_pack["may_execute_delete"])
        preflight = scenarios["host_preflight_discovery"]
        self.assertEqual(preflight["expected_final_schema"], "cleanmac.ai-host-preflight.v1")
        self.assertFalse(preflight["may_execute_delete"])
        evidence = scenarios["host_evidence_discovery"]
        self.assertEqual(evidence["expected_final_schema"], "cleanmac.ai-host-evidence.v1")
        self.assertFalse(evidence["may_execute_delete"])
        evidence_denials = scenarios["host_evidence_runtime_denial_coverage"]
        self.assertEqual(evidence_denials["expected_final_schema"], "cleanmac.ai-host-evidence.v1")
        self.assertIn("RAW_COMMAND_ARGUMENT_DENIED", evidence_denials["expected_blocking_codes"])
        self.assertIn("CONFIRMATION_TOKEN_REQUIRED", evidence_denials["expected_blocking_codes"])
        release_readiness = scenarios["release_readiness_discovery"]
        self.assertEqual(release_readiness["expected_final_schema"], "cleanmac.release-readiness.v1")
        self.assertFalse(release_readiness["may_execute_delete"])
        missing_artifact = scenarios["release_readiness_artifact_missing_blocks"]
        self.assertIn("release-artifact-manifest-valid", missing_artifact["expected_blocking_codes"])
        artifact_present = scenarios["release_readiness_artifact_present_ready"]
        self.assertEqual(artifact_present["expected_blocking_codes"], [])
        self.assertFalse(artifact_present["may_execute_delete"])
        release_evidence = scenarios["release_evidence_bundle_discovery"]
        self.assertEqual(release_evidence["expected_final_schema"], "cleanmac.release-evidence.v1")
        diagnostics = scenarios["release_diagnostics_explains_readiness_failure"]
        self.assertIn("RELEASE_ARTIFACT_MANIFEST_MISSING", diagnostics["expected_blocking_codes"])
        rehearsal = scenarios["release_rehearsal_discovery"]
        self.assertEqual(rehearsal["expected_final_schema"], "cleanmac.release-rehearsal.v1")
        promotion = scenarios["release_promotion_decision_blocks_missing_evidence"]
        self.assertEqual(promotion["expected_final_schema"], "cleanmac.release-promotion-decision.v1")
        self.assertIn("RELEASE_ARTIFACT_MANIFEST_MISSING", promotion["expected_blocking_codes"])
        rollback = scenarios["release_rollback_plan_discovery"]
        self.assertEqual(rollback["expected_final_schema"], "cleanmac.release-rollback-plan.v1")
        post_publish = scenarios["release_post_publish_verification_discovery"]
        self.assertEqual(post_publish["expected_final_schema"], "cleanmac.release-post-publish-verification.v1")
        post_publish_result = scenarios["release_post_publish_result_discovery"]
        self.assertEqual(post_publish_result["expected_final_schema"], "cleanmac.release-post-publish-result.v1")
        post_publish_template = scenarios["release_post_publish_evidence_template_discovery"]
        self.assertEqual(
            post_publish_template["expected_final_schema"], "cleanmac.release-post-publish-evidence-template.v1"
        )
        registry_coverage = scenarios["schema_registry_release_contract_coverage"]
        self.assertEqual(registry_coverage["expected_final_schema"], "cleanmac.ai-schema-registry.v1")
        raw_denial = scenarios["mcp_raw_command_argument_denial"]
        self.assertIn("RAW_COMMAND_ARGUMENT_DENIED", raw_denial["expected_blocking_codes"])
        destructive_denial = scenarios["mcp_destructive_policy_denial"]
        self.assertIn("CONFIRMATION_TOKEN_REQUIRED", destructive_denial["expected_blocking_codes"])
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
        self.assertTrue(scenario_results["host_integration_pack_discovery"]["passed"])
        self.assertTrue(scenario_results["host_preflight_discovery"]["passed"])
        self.assertTrue(scenario_results["host_evidence_discovery"]["passed"])
        self.assertTrue(scenario_results["host_evidence_runtime_denial_coverage"]["passed"])
        self.assertTrue(scenario_results["release_readiness_discovery"]["passed"])
        self.assertTrue(scenario_results["release_readiness_artifact_missing_blocks"]["passed"])
        self.assertTrue(scenario_results["release_readiness_artifact_present_ready"]["passed"])
        self.assertTrue(scenario_results["release_evidence_bundle_discovery"]["passed"])
        self.assertTrue(scenario_results["release_diagnostics_explains_readiness_failure"]["passed"])
        self.assertTrue(scenario_results["release_rehearsal_discovery"]["passed"])
        self.assertTrue(scenario_results["release_promotion_decision_blocks_missing_evidence"]["passed"])
        self.assertTrue(scenario_results["release_rollback_plan_discovery"]["passed"])
        self.assertTrue(scenario_results["release_post_publish_verification_discovery"]["passed"])
        self.assertTrue(scenario_results["release_post_publish_result_discovery"]["passed"])
        self.assertTrue(scenario_results["release_post_publish_evidence_template_discovery"]["passed"])
        self.assertTrue(scenario_results["schema_registry_release_contract_coverage"]["passed"])
        self.assertTrue(scenario_results["discover_readiness"]["passed"])
        self.assertTrue(scenario_results["schema_registry_discovery"]["passed"])
        self.assertTrue(scenario_results["contract_validation_plan"]["passed"])
        self.assertTrue(scenario_results["contract_samples_roundtrip"]["passed"])
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
        self.assertTrue(scenario_results["mcp_raw_command_argument_denial"]["passed"])
        self.assertTrue(scenario_results["mcp_destructive_policy_denial"]["passed"])
        self.assertTrue(scenario_results["bundle_protection_enforcement"]["passed"])
        self.assertEqual(
            scenario_results["safe_plan_to_dry_run"]["observed_blocking_codes"],
            ["AI_ORIGIN_REQUIRES_CONFIRMATION_TOKEN"],
        )

    def test_ai_eval_run_smoke_covers_runner_in_process(self) -> None:
        from cleancli.ai_eval import render_ai_eval_pack, render_ai_eval_run, scenario_ids, selected_scenario_ids

        report = render_ai_eval_run(scenario="smoke", cli=CLI)

        self.assertEqual(report["schema"], "cleanmac.ai-eval-run.v1")
        self.assertTrue(report["passed"], report)
        self.assertEqual(report["failed_count"], 0)
        self.assertEqual(report["trace_persistence"], {"status": "skipped", "path": None})

        pack = render_ai_eval_pack()
        selected_ids = set(selected_scenario_ids("smoke", scenario_ids(pack)))
        result_ids = {item["id"] for item in report["results"]}
        self.assertEqual(result_ids, selected_ids)

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
        self.assertIn("host_integration_pack_discovery", scenario_ids)
        self.assertIn("host_preflight_discovery", scenario_ids)
        self.assertIn("host_evidence_discovery", scenario_ids)
        self.assertIn("host_evidence_runtime_denial_coverage", scenario_ids)
        self.assertIn("release_readiness_discovery", scenario_ids)
        self.assertIn("release_readiness_artifact_missing_blocks", scenario_ids)
        self.assertIn("release_readiness_artifact_present_ready", scenario_ids)
        self.assertIn("release_evidence_bundle_discovery", scenario_ids)
        self.assertIn("release_diagnostics_explains_readiness_failure", scenario_ids)
        self.assertIn("release_rehearsal_discovery", scenario_ids)
        self.assertIn("release_promotion_decision_blocks_missing_evidence", scenario_ids)
        self.assertIn("release_rollback_plan_discovery", scenario_ids)
        self.assertIn("release_post_publish_verification_discovery", scenario_ids)
        self.assertIn("release_post_publish_result_discovery", scenario_ids)
        self.assertIn("release_post_publish_evidence_template_discovery", scenario_ids)
        self.assertIn("schema_registry_release_contract_coverage", scenario_ids)
        self.assertIn("mcp_raw_command_argument_denial", scenario_ids)
        self.assertIn("mcp_destructive_policy_denial", scenario_ids)
        self.assertIn("schema_registry_discovery", scenario_ids)
        self.assertIn("contract_validation_plan", scenario_ids)
        self.assertIn("contract_samples_roundtrip", scenario_ids)
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
        self.assertIn("governed_privacy_execute_blocks_unsafe_paths", scenario_ids)
        self.assertIn("governed_startup_disable_requires_backup", scenario_ids)

    def test_eval_pack_includes_governed_execution_hardening_scenarios(self) -> None:
        from cleancli.ai_eval import render_ai_eval_pack

        pack = render_ai_eval_pack()
        scenarios = {scenario["id"]: scenario for scenario in pack["scenarios"]}
        privacy = scenarios["governed_privacy_execute_blocks_unsafe_paths"]
        startup = scenarios["governed_startup_disable_requires_backup"]

        self.assertIn("cleanmac_privacy_execute", privacy["required_tools"])
        self.assertIn("outside-privacy-locations", privacy["expected_blocking_codes"])
        self.assertFalse(privacy["may_execute_delete"])
        self.assertFalse(privacy["destructive_execution_allowed"])
        self.assertIn("cleanmac_startup_disable", startup["required_tools"])
        self.assertEqual(startup["expected_final_schema"], "cleanmac.startup-disable-result.v1")
        self.assertFalse(startup["may_execute_delete"])
        self.assertFalse(startup["destructive_execution_allowed"])

    def test_ai_eval_run_mcp_resource_prompt_surface(self) -> None:
        report = self.run_json("ai-eval-run", "--scenario", "mcp_resource_prompt_surface")

        self.assertEqual(report["schema"], "cleanmac.ai-eval-run.v1")
        self.assertTrue(report["passed"], report)
        self.assertEqual(report["selected_scenarios"], ["mcp_resource_prompt_surface"])
        self.assertEqual(report["passed_count"], 1)
        self.assertEqual(report["failed_count"], 0)
        self.assertGreaterEqual(report["trace"]["event_count"], 8)

        result = report["results"][0]
        self.assertEqual(result["id"], "mcp_resource_prompt_surface")
        self.assertTrue(result["passed"])
        self.assertEqual(result["observed_schema"], "cleanmac.mcp-smoke.v1")
        self.assertEqual(result["observed_blocking_codes"], [])
        self.assertGreaterEqual(report["trace"]["event_count"], 9)

    def test_ai_eval_run_contract_samples_roundtrip(self) -> None:
        report = self.run_json("ai-eval-run", "--scenario", "contract_samples_roundtrip")

        self.assertEqual(report["schema"], "cleanmac.ai-eval-run.v1")
        self.assertTrue(report["passed"], report)
        self.assertEqual(report["selected_scenarios"], ["contract_samples_roundtrip"])
        self.assertEqual(report["passed_count"], 1)
        self.assertEqual(report["failed_count"], 0)

        result = report["results"][0]
        self.assertEqual(result["id"], "contract_samples_roundtrip")
        self.assertTrue(result["passed"])
        self.assertEqual(result["observed_schema"], "cleanmac.ai-contract-samples.v1")
        self.assertEqual(result["observed_blocking_codes"], [])

    def test_ai_eval_run_host_integration_pack_discovery(self) -> None:
        report = self.run_json("ai-eval-run", "--scenario", "host_integration_pack_discovery")

        self.assertEqual(report["schema"], "cleanmac.ai-eval-run.v1")
        self.assertTrue(report["passed"], report)
        self.assertEqual(report["selected_scenarios"], ["host_integration_pack_discovery"])
        self.assertEqual(report["passed_count"], 1)
        self.assertEqual(report["failed_count"], 0)

        result = report["results"][0]
        self.assertEqual(result["id"], "host_integration_pack_discovery")
        self.assertTrue(result["passed"])
        self.assertEqual(result["observed_schema"], "cleanmac.ai-host-integration-pack.v1")
        self.assertEqual(result["observed_blocking_codes"], [])

    def test_ai_eval_run_host_preflight_discovery(self) -> None:
        report = self.run_json("ai-eval-run", "--scenario", "host_preflight_discovery")

        self.assertEqual(report["schema"], "cleanmac.ai-eval-run.v1")
        self.assertTrue(report["passed"], report)
        self.assertEqual(report["selected_scenarios"], ["host_preflight_discovery"])
        self.assertEqual(report["passed_count"], 1)

        result = report["results"][0]
        self.assertEqual(result["id"], "host_preflight_discovery")
        self.assertTrue(result["passed"])
        self.assertEqual(result["observed_schema"], "cleanmac.ai-host-preflight.v1")

    def test_ai_eval_run_host_evidence_discovery(self) -> None:
        report = self.run_json("ai-eval-run", "--scenario", "host_evidence_discovery")

        self.assertEqual(report["schema"], "cleanmac.ai-eval-run.v1")
        self.assertTrue(report["passed"], report)
        self.assertEqual(report["selected_scenarios"], ["host_evidence_discovery"])
        self.assertEqual(report["passed_count"], 1)

        result = report["results"][0]
        self.assertEqual(result["id"], "host_evidence_discovery")
        self.assertTrue(result["passed"])
        self.assertEqual(result["observed_schema"], "cleanmac.ai-host-evidence.v1")

    def test_ai_eval_run_host_evidence_runtime_denial_coverage(self) -> None:
        report = self.run_json("ai-eval-run", "--scenario", "host_evidence_runtime_denial_coverage")

        self.assertTrue(report["passed"], report)
        result = report["results"][0]
        self.assertEqual(result["observed_schema"], "cleanmac.ai-host-evidence.v1")
        self.assertIn("RAW_COMMAND_ARGUMENT_DENIED", result["observed_blocking_codes"])
        self.assertIn("CONFIRMATION_TOKEN_REQUIRED", result["observed_blocking_codes"])

    def test_ai_eval_run_mcp_runtime_policy_denials(self) -> None:
        raw_report = self.run_json("ai-eval-run", "--scenario", "mcp_raw_command_argument_denial")
        destructive_report = self.run_json("ai-eval-run", "--scenario", "mcp_destructive_policy_denial")

        self.assertTrue(raw_report["passed"], raw_report)
        self.assertEqual(raw_report["results"][0]["observed_schema"], "cleanmac.mcp-tool-error.v1")
        self.assertIn("RAW_COMMAND_ARGUMENT_DENIED", raw_report["results"][0]["observed_blocking_codes"])

        self.assertTrue(destructive_report["passed"], destructive_report)
        self.assertEqual(destructive_report["results"][0]["observed_schema"], "cleanmac.mcp-tool-error.v1")
        self.assertIn("CONFIRMATION_TOKEN_REQUIRED", destructive_report["results"][0]["observed_blocking_codes"])


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
