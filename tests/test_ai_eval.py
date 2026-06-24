from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
CLI = PROJECT_ROOT / "cleanmac.py"


def run_json(*args: str) -> dict[str, Any]:
    result = subprocess.run(
        [sys.executable, str(CLI), "--json", *args],
        text=True,
        capture_output=True,
        check=True,
    )
    return json.loads(result.stdout)


def test_ai_eval_pack_lists_safe_host_scenarios() -> None:
    report = run_json("ai-eval-pack")

    assert report["schema"] == "cleanmac.ai-eval-pack.v1"
    assert not report["uses_shell"]
    assert not report["allows_destructive_execution"]
    assert report["scenario_count"] == len(report["scenarios"])

    scenarios = {scenario["id"]: scenario for scenario in report["scenarios"]}
    assert "host_integration_pack_discovery" in scenarios
    assert "host_preflight_discovery" in scenarios
    assert "runtime_lifecycle_policy_discovery" in scenarios
    assert "host_evidence_discovery" in scenarios
    assert "host_evidence_runtime_denial_coverage" in scenarios
    assert "release_readiness_discovery" in scenarios
    assert "release_readiness_surface_audit_gate" in scenarios
    assert "release_readiness_artifact_missing_blocks" in scenarios
    assert "release_readiness_artifact_present_ready" in scenarios
    assert "release_evidence_bundle_discovery" in scenarios
    assert "release_diagnostics_explains_readiness_failure" in scenarios
    assert "release_rehearsal_discovery" in scenarios
    assert "release_promotion_decision_blocks_missing_evidence" in scenarios
    assert "release_promotion_decision_surface_audit_blocker" in scenarios
    assert "release_rollback_plan_discovery" in scenarios
    assert "release_post_publish_verification_discovery" in scenarios
    assert "release_post_publish_result_discovery" in scenarios
    assert "release_post_publish_evidence_template_discovery" in scenarios
    assert "schema_registry_release_contract_coverage" in scenarios
    assert "discover_readiness" in scenarios
    assert "one_shot_governed_workflow" in scenarios
    assert "mcp_workflow_contract_resource" in scenarios
    assert "dry_run_human_summary_recovery" in scenarios
    assert "ai_error_next_allowed_tools_recovery" in scenarios
    assert "safe_plan_to_dry_run" in scenarios
    assert "schema_registry_discovery" in scenarios
    assert "contract_validation_plan" in scenarios
    assert "contract_samples_roundtrip" in scenarios
    assert "developer_tool_plan_risk_explanations" in scenarios
    assert "developer_package_manager_dry_run_only" in scenarios
    assert "unsupported_plan_schema_recovery" in scenarios
    assert "legacy_plan_schema_warning" in scenarios
    assert "invalid_category_recovery" in scenarios
    assert "confirmation_token_policy" in scenarios
    assert "mcp_resource_prompt_surface" in scenarios
    assert "mcp_raw_command_argument_denial" in scenarios
    assert "mcp_destructive_policy_denial" in scenarios
    assert "prompt_injection_boundary" in scenarios
    assert "plan_context_mismatch_policy" in scenarios
    assert "permanent_delete_deny_policy" in scenarios
    assert "confirmation_token_execution" in scenarios
    assert "confirmation_token_validation" in scenarios
    assert "bundle_protection_enforcement" in scenarios

    safe_plan = scenarios["safe_plan_to_dry_run"]
    assert "cleanmac_generate_plan" in safe_plan["required_tools"]
    assert "cleanmac_dry_run_plan" in safe_plan["required_tools"]
    assert safe_plan["expected_final_schema"] == "cleanmac.clean.v1"
    assert not safe_plan["may_execute_delete"]
    contract_validation = scenarios["contract_validation_plan"]
    assert contract_validation["expected_final_schema"] == "cleanmac.ai-contract-validation.v1"
    contract_samples = scenarios["contract_samples_roundtrip"]
    assert contract_samples["expected_final_schema"] == "cleanmac.ai-contract-samples.v1"
    assert not contract_samples["may_execute_delete"]
    developer_plan = scenarios["developer_tool_plan_risk_explanations"]
    assert developer_plan["expected_final_schema"] == "cleanmac.tool-plan.v1"
    assert not developer_plan["may_execute_delete"]
    developer_dry_run = scenarios["developer_package_manager_dry_run_only"]
    assert developer_dry_run["expected_final_schema"] == "cleanmac.tool-execution-result.v1"
    assert not developer_dry_run["may_execute_delete"]
    workflow_resource = scenarios["mcp_workflow_contract_resource"]
    assert workflow_resource["expected_final_schema"] == "cleanmac.ai-workflow.v1"
    assert not workflow_resource["may_execute_delete"]
    human_summary = scenarios["dry_run_human_summary_recovery"]
    assert human_summary["expected_final_schema"] == "cleanmac.clean.v1"
    assert not human_summary["may_execute_delete"]
    ai_error = scenarios["ai_error_next_allowed_tools_recovery"]
    assert ai_error["expected_final_schema"] == "cleanmac.ai-error.v1"
    assert not ai_error["may_execute_delete"]
    integration_pack = scenarios["host_integration_pack_discovery"]
    assert integration_pack["expected_final_schema"] == "cleanmac.ai-host-integration-pack.v1"
    assert not integration_pack["may_execute_delete"]
    preflight = scenarios["host_preflight_discovery"]
    assert preflight["expected_final_schema"] == "cleanmac.ai-host-preflight.v1"
    assert not preflight["may_execute_delete"]
    lifecycle = scenarios["runtime_lifecycle_policy_discovery"]
    assert ["cleanmac", "--json", "ai-host-policy"] in lifecycle["required_cli_commands"]
    assert lifecycle["expected_final_schema"] == "cleanmac.ai-host-policy.v1"
    assert not lifecycle["may_execute_delete"]
    evidence = scenarios["host_evidence_discovery"]
    assert evidence["expected_final_schema"] == "cleanmac.ai-host-evidence.v1"
    assert not evidence["may_execute_delete"]
    evidence_denials = scenarios["host_evidence_runtime_denial_coverage"]
    assert evidence_denials["expected_final_schema"] == "cleanmac.ai-host-evidence.v1"
    assert "RAW_COMMAND_ARGUMENT_DENIED" in evidence_denials["expected_blocking_codes"]
    assert "CONFIRMATION_TOKEN_REQUIRED" in evidence_denials["expected_blocking_codes"]
    release_readiness = scenarios["release_readiness_discovery"]
    assert release_readiness["expected_final_schema"] == "cleanmac.release-readiness.v1"
    assert not release_readiness["may_execute_delete"]
    surface_audit_gate = scenarios["release_readiness_surface_audit_gate"]
    assert "mcp-surface-audit-ready" in surface_audit_gate["expected_blocking_codes"]
    assert not surface_audit_gate["may_execute_delete"]
    missing_artifact = scenarios["release_readiness_artifact_missing_blocks"]
    assert "release-artifact-manifest-valid" in missing_artifact["expected_blocking_codes"]
    artifact_present = scenarios["release_readiness_artifact_present_ready"]
    assert artifact_present["expected_blocking_codes"] == []
    assert not artifact_present["may_execute_delete"]
    release_evidence = scenarios["release_evidence_bundle_discovery"]
    assert release_evidence["expected_final_schema"] == "cleanmac.release-evidence.v1"
    diagnostics = scenarios["release_diagnostics_explains_readiness_failure"]
    assert "RELEASE_ARTIFACT_MANIFEST_MISSING" in diagnostics["expected_blocking_codes"]
    rehearsal = scenarios["release_rehearsal_discovery"]
    assert rehearsal["expected_final_schema"] == "cleanmac.release-rehearsal.v1"
    promotion = scenarios["release_promotion_decision_blocks_missing_evidence"]
    assert promotion["expected_final_schema"] == "cleanmac.release-promotion-decision.v1"
    assert "RELEASE_ARTIFACT_MANIFEST_MISSING" in promotion["expected_blocking_codes"]
    surface_promotion = scenarios["release_promotion_decision_surface_audit_blocker"]
    assert surface_promotion["expected_final_schema"] == "cleanmac.release-promotion-decision.v1"
    assert "MCP_SURFACE_AUDIT_NOT_READY" in surface_promotion["expected_blocking_codes"]
    rollback = scenarios["release_rollback_plan_discovery"]
    assert rollback["expected_final_schema"] == "cleanmac.release-rollback-plan.v1"
    post_publish = scenarios["release_post_publish_verification_discovery"]
    assert post_publish["expected_final_schema"] == "cleanmac.release-post-publish-verification.v1"
    post_publish_result = scenarios["release_post_publish_result_discovery"]
    assert post_publish_result["expected_final_schema"] == "cleanmac.release-post-publish-result.v1"
    post_publish_template = scenarios["release_post_publish_evidence_template_discovery"]
    assert post_publish_template["expected_final_schema"] == "cleanmac.release-post-publish-evidence-template.v1"
    registry_coverage = scenarios["schema_registry_release_contract_coverage"]
    assert registry_coverage["expected_final_schema"] == "cleanmac.ai-schema-registry.v1"
    raw_denial = scenarios["mcp_raw_command_argument_denial"]
    assert "RAW_COMMAND_ARGUMENT_DENIED" in raw_denial["expected_blocking_codes"]
    destructive_denial = scenarios["mcp_destructive_policy_denial"]
    assert "CONFIRMATION_TOKEN_REQUIRED" in destructive_denial["expected_blocking_codes"]
    unsupported_schema = scenarios["unsupported_plan_schema_recovery"]
    assert "unsupported-schema-version" in unsupported_schema["expected_blocking_codes"]
    legacy_warning = scenarios["legacy_plan_schema_warning"]
    assert "LEGACY_PLAN_SCHEMA" in legacy_warning["expected_blocking_codes"]

    token_policy = scenarios["confirmation_token_policy"]
    assert "AI_ORIGIN_REQUIRES_CONFIRMATION_TOKEN" in token_policy["expected_blocking_codes"]
    context_policy = scenarios["plan_context_mismatch_policy"]
    assert "PLAN_CONTEXT_MISMATCH" in context_policy["expected_blocking_codes"]
    permanent_policy = scenarios["permanent_delete_deny_policy"]
    assert "AI_ORIGIN_REQUIRES_TRASH" in permanent_policy["expected_blocking_codes"]
    execution_policy = scenarios["confirmation_token_execution"]
    assert execution_policy["sandbox_only"]
    assert execution_policy["may_execute_delete"]
    assert "CONFIRMATION_TOKEN_MISMATCH" in execution_policy["expected_blocking_codes"]
    validation_policy = scenarios["confirmation_token_validation"]
    assert not validation_policy["may_execute_delete"]
    assert "AI_ORIGIN_REQUIRES_CONFIRMATION_TOKEN" in validation_policy["expected_blocking_codes"]
    bundle_policy = scenarios["bundle_protection_enforcement"]
    assert not bundle_policy["may_execute_delete"]


def test_ai_eval_run_smoke_executes_safe_scenarios() -> None:
    report = run_json("ai-eval-run", "--scenario", "smoke")

    assert report["schema"] == "cleanmac.ai-eval-run.v1"
    assert report["passed"], report
    assert report["scenario"] == "smoke"
    assert not report["destructive_execution_allowed"]
    assert report["passed_count"] >= 10
    assert report["failed_count"] == 0
    assert report["trace"]["schema"] == "cleanmac.ai-trace.v1"
    assert report["trace"]["event_count"] > 0

    scenario_results = {item["id"]: item for item in report["results"]}
    assert scenario_results["host_integration_pack_discovery"]["passed"]
    assert scenario_results["host_preflight_discovery"]["passed"]
    assert scenario_results["host_evidence_discovery"]["passed"]
    assert scenario_results["host_evidence_runtime_denial_coverage"]["passed"]
    assert scenario_results["release_readiness_discovery"]["passed"]
    assert scenario_results["release_readiness_surface_audit_gate"]["passed"]
    assert scenario_results["release_readiness_artifact_missing_blocks"]["passed"]
    assert scenario_results["release_readiness_artifact_present_ready"]["passed"]
    assert scenario_results["release_evidence_bundle_discovery"]["passed"]
    assert scenario_results["release_diagnostics_explains_readiness_failure"]["passed"]
    assert scenario_results["release_rehearsal_discovery"]["passed"]
    assert scenario_results["release_promotion_decision_blocks_missing_evidence"]["passed"]
    assert scenario_results["release_promotion_decision_surface_audit_blocker"]["passed"]
    assert scenario_results["release_rollback_plan_discovery"]["passed"]
    assert scenario_results["release_post_publish_verification_discovery"]["passed"]
    assert scenario_results["release_post_publish_result_discovery"]["passed"]
    assert scenario_results["release_post_publish_evidence_template_discovery"]["passed"]
    assert scenario_results["schema_registry_release_contract_coverage"]["passed"]
    assert scenario_results["discover_readiness"]["passed"]
    assert scenario_results["one_shot_governed_workflow"]["passed"]
    assert scenario_results["mcp_workflow_contract_resource"]["passed"]
    assert scenario_results["dry_run_human_summary_recovery"]["passed"]
    assert scenario_results["ai_error_next_allowed_tools_recovery"]["passed"]
    assert scenario_results["schema_registry_discovery"]["passed"]
    assert scenario_results["contract_validation_plan"]["passed"]
    assert scenario_results["contract_samples_roundtrip"]["passed"]
    assert scenario_results["developer_tool_plan_risk_explanations"]["passed"]
    assert scenario_results["developer_package_manager_dry_run_only"]["passed"]
    assert scenario_results["unsupported_plan_schema_recovery"]["passed"]
    assert scenario_results["legacy_plan_schema_warning"]["passed"]
    assert scenario_results["safe_plan_to_dry_run"]["passed"]
    assert scenario_results["invalid_category_recovery"]["passed"]
    assert scenario_results["confirmation_token_policy"]["passed"]
    assert scenario_results["confirmation_token_validation"]["passed"]
    assert scenario_results["prompt_injection_boundary"]["passed"]
    assert scenario_results["plan_context_mismatch_policy"]["passed"]
    assert scenario_results["permanent_delete_deny_policy"]["passed"]
    assert scenario_results["mcp_resource_prompt_surface"]["passed"]
    assert scenario_results["mcp_raw_command_argument_denial"]["passed"]
    assert scenario_results["mcp_destructive_policy_denial"]["passed"]
    assert scenario_results["bundle_protection_enforcement"]["passed"]
    assert scenario_results["safe_plan_to_dry_run"]["observed_blocking_codes"] == [
        "AI_ORIGIN_REQUIRES_CONFIRMATION_TOKEN"
    ]


def test_ai_eval_run_smoke_covers_runner_in_process() -> None:
    from cleancli.ai_eval import render_ai_eval_pack, render_ai_eval_run, scenario_ids, selected_scenario_ids

    report = render_ai_eval_run(scenario="smoke", cli=CLI)

    assert report["schema"] == "cleanmac.ai-eval-run.v1"
    assert report["passed"], report
    assert report["failed_count"] == 0
    assert report["trace_persistence"] == {"status": "skipped", "path": None}

    pack = render_ai_eval_pack()
    selected_ids = set(selected_scenario_ids("smoke", scenario_ids(pack)))
    result_ids = {item["id"] for item in report["results"]}
    assert result_ids == selected_ids


def test_ai_eval_selection_helpers_cover_all_single_and_unknown_requests() -> None:
    from cleancli.ai_eval import render_ai_eval_pack, scenario_ids, selected_scenario_ids

    all_ids = scenario_ids(render_ai_eval_pack())

    assert "discover_readiness" in all_ids
    assert selected_scenario_ids("all", all_ids) == all_ids
    assert selected_scenario_ids("discover_readiness", all_ids) == ["discover_readiness"]
    with pytest.raises(ValueError, match="Unknown AI eval scenario: not-real"):
        selected_scenario_ids("not-real", all_ids)


def test_ai_eval_cli_helper_raises_structured_runtime_error_on_unexpected_failure(tmp_path: Path) -> None:
    from cleancli.ai_eval import _prepare_sandbox, _run_cli

    root, home = _prepare_sandbox(str(tmp_path))
    with pytest.raises(RuntimeError, match="unknown-command"):
        _run_cli(CLI, ["unknown-command"], root=root, home=home)


def test_ai_eval_run_rejects_unknown_scenario() -> None:
    result = subprocess.run(
        [sys.executable, str(CLI), "--json", "ai-eval-run", "--scenario", "not-real"],
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode != 0
    report = json.loads(result.stderr)
    assert report["schema"] == "cleanmac.ai-error.v1"
    assert report["error"]["code"] == "AI_EVAL_UNKNOWN_SCENARIO"
    assert "ai-eval-pack" in report["error"]["next_allowed_commands"]


def test_eval_pack_scenario_ids_match_ai_host_regressions() -> None:
    report = run_json("ai-eval-pack")
    scenario_ids = {scenario["id"] for scenario in report["scenarios"]}

    assert "safe_plan_to_dry_run" in scenario_ids
    assert "host_integration_pack_discovery" in scenario_ids
    assert "host_preflight_discovery" in scenario_ids
    assert "host_evidence_discovery" in scenario_ids
    assert "host_evidence_runtime_denial_coverage" in scenario_ids
    assert "release_readiness_discovery" in scenario_ids
    assert "release_readiness_surface_audit_gate" in scenario_ids
    assert "release_readiness_artifact_missing_blocks" in scenario_ids
    assert "release_readiness_artifact_present_ready" in scenario_ids
    assert "release_evidence_bundle_discovery" in scenario_ids
    assert "release_diagnostics_explains_readiness_failure" in scenario_ids
    assert "release_rehearsal_discovery" in scenario_ids
    assert "release_promotion_decision_blocks_missing_evidence" in scenario_ids
    assert "release_promotion_decision_surface_audit_blocker" in scenario_ids
    assert "release_rollback_plan_discovery" in scenario_ids
    assert "release_post_publish_verification_discovery" in scenario_ids
    assert "release_post_publish_result_discovery" in scenario_ids
    assert "release_post_publish_evidence_template_discovery" in scenario_ids
    assert "schema_registry_release_contract_coverage" in scenario_ids
    assert "one_shot_governed_workflow" in scenario_ids
    assert "mcp_raw_command_argument_denial" in scenario_ids
    assert "mcp_destructive_policy_denial" in scenario_ids
    assert "schema_registry_discovery" in scenario_ids
    assert "contract_validation_plan" in scenario_ids
    assert "contract_samples_roundtrip" in scenario_ids
    assert "developer_tool_plan_risk_explanations" in scenario_ids
    assert "developer_package_manager_dry_run_only" in scenario_ids
    assert "unsupported_plan_schema_recovery" in scenario_ids
    assert "legacy_plan_schema_warning" in scenario_ids
    assert "invalid_category_recovery" in scenario_ids
    assert "confirmation_token_policy" in scenario_ids
    assert "mcp_resource_prompt_surface" in scenario_ids
    assert "prompt_injection_boundary" in scenario_ids
    assert "plan_context_mismatch_policy" in scenario_ids
    assert "permanent_delete_deny_policy" in scenario_ids
    assert "confirmation_token_execution" in scenario_ids
    assert "confirmation_token_validation" in scenario_ids
    assert "bundle_protection_enforcement" in scenario_ids
    assert "governed_privacy_execute_blocks_unsafe_paths" in scenario_ids
    assert "governed_startup_disable_requires_backup" in scenario_ids


def test_eval_pack_includes_governed_execution_hardening_scenarios() -> None:
    from cleancli.ai_eval import render_ai_eval_pack

    pack = render_ai_eval_pack()
    scenarios = {scenario["id"]: scenario for scenario in pack["scenarios"]}
    privacy = scenarios["governed_privacy_execute_blocks_unsafe_paths"]
    startup = scenarios["governed_startup_disable_requires_backup"]

    assert "cleanmac_privacy_execute" in privacy["required_tools"]
    assert "outside-privacy-locations" in privacy["expected_blocking_codes"]
    assert not privacy["may_execute_delete"]
    assert not privacy["destructive_execution_allowed"]
    assert "cleanmac_startup_disable" in startup["required_tools"]
    assert startup["expected_final_schema"] == "cleanmac.startup-disable-result.v1"
    assert not startup["may_execute_delete"]
    assert not startup["destructive_execution_allowed"]


def test_ai_eval_run_mcp_resource_prompt_surface() -> None:
    report = run_json("ai-eval-run", "--scenario", "mcp_resource_prompt_surface")

    assert report["schema"] == "cleanmac.ai-eval-run.v1"
    assert report["passed"], report
    assert report["selected_scenarios"] == ["mcp_resource_prompt_surface"]
    assert report["passed_count"] == 1
    assert report["failed_count"] == 0
    assert report["trace"]["event_count"] >= 9

    result = report["results"][0]
    assert result["id"] == "mcp_resource_prompt_surface"
    assert result["passed"]
    assert result["observed_schema"] == "cleanmac.mcp-smoke.v1"
    assert result["observed_blocking_codes"] == []
    assert report["trace"]["event_count"] >= 10


def test_ai_eval_run_release_readiness_surface_audit_gate() -> None:
    report = run_json("ai-eval-run", "--scenario", "release_readiness_surface_audit_gate")

    assert report["schema"] == "cleanmac.ai-eval-run.v1"
    assert report["passed"], report
    assert report["selected_scenarios"] == ["release_readiness_surface_audit_gate"]
    assert report["passed_count"] == 1
    assert report["failed_count"] == 0

    result = report["results"][0]
    assert result["id"] == "release_readiness_surface_audit_gate"
    assert result["passed"]
    assert result["observed_schema"] == "cleanmac.release-readiness.v1"
    assert result["observed_blocking_codes"] == []


def test_ai_eval_run_contract_samples_roundtrip() -> None:
    report = run_json("ai-eval-run", "--scenario", "contract_samples_roundtrip")

    assert report["schema"] == "cleanmac.ai-eval-run.v1"
    assert report["passed"], report
    assert report["selected_scenarios"] == ["contract_samples_roundtrip"]
    assert report["passed_count"] == 1
    assert report["failed_count"] == 0

    result = report["results"][0]
    assert result["id"] == "contract_samples_roundtrip"
    assert result["passed"]
    assert result["observed_schema"] == "cleanmac.ai-contract-samples.v1"
    assert result["observed_blocking_codes"] == []


def test_ai_eval_run_host_integration_pack_discovery() -> None:
    report = run_json("ai-eval-run", "--scenario", "host_integration_pack_discovery")

    assert report["schema"] == "cleanmac.ai-eval-run.v1"
    assert report["passed"], report
    assert report["selected_scenarios"] == ["host_integration_pack_discovery"]
    assert report["passed_count"] == 1
    assert report["failed_count"] == 0

    result = report["results"][0]
    assert result["id"] == "host_integration_pack_discovery"
    assert result["passed"]
    assert result["observed_schema"] == "cleanmac.ai-host-integration-pack.v1"
    assert result["observed_blocking_codes"] == []


def test_ai_eval_run_host_preflight_discovery() -> None:
    report = run_json("ai-eval-run", "--scenario", "host_preflight_discovery")

    assert report["schema"] == "cleanmac.ai-eval-run.v1"
    assert report["passed"], report
    assert report["selected_scenarios"] == ["host_preflight_discovery"]
    assert report["passed_count"] == 1

    result = report["results"][0]
    assert result["id"] == "host_preflight_discovery"
    assert result["passed"]
    assert result["observed_schema"] == "cleanmac.ai-host-preflight.v1"


def test_ai_eval_run_host_evidence_discovery() -> None:
    report = run_json("ai-eval-run", "--scenario", "host_evidence_discovery")

    assert report["schema"] == "cleanmac.ai-eval-run.v1"
    assert report["passed"], report
    assert report["selected_scenarios"] == ["host_evidence_discovery"]
    assert report["passed_count"] == 1

    result = report["results"][0]
    assert result["id"] == "host_evidence_discovery"
    assert result["passed"]
    assert result["observed_schema"] == "cleanmac.ai-host-evidence.v1"


def test_ai_eval_run_host_evidence_runtime_denial_coverage() -> None:
    report = run_json("ai-eval-run", "--scenario", "host_evidence_runtime_denial_coverage")

    assert report["passed"], report
    result = report["results"][0]
    assert result["observed_schema"] == "cleanmac.ai-host-evidence.v1"
    assert "RAW_COMMAND_ARGUMENT_DENIED" in result["observed_blocking_codes"]
    assert "CONFIRMATION_TOKEN_REQUIRED" in result["observed_blocking_codes"]


def test_ai_eval_run_mcp_runtime_policy_denials() -> None:
    raw_report = run_json("ai-eval-run", "--scenario", "mcp_raw_command_argument_denial")
    destructive_report = run_json("ai-eval-run", "--scenario", "mcp_destructive_policy_denial")

    assert raw_report["passed"], raw_report
    assert raw_report["results"][0]["observed_schema"] == "cleanmac.mcp-tool-error.v1"
    assert "RAW_COMMAND_ARGUMENT_DENIED" in raw_report["results"][0]["observed_blocking_codes"]
    assert raw_report["results"][0]["observed_next_allowed_tools"][:2] == [
        "cleanmac_validate_plan",
        "cleanmac_policy_simulate",
    ]

    assert destructive_report["passed"], destructive_report
    assert destructive_report["results"][0]["observed_schema"] == "cleanmac.mcp-tool-error.v1"
    assert "CONFIRMATION_TOKEN_REQUIRED" in destructive_report["results"][0]["observed_blocking_codes"]
    assert destructive_report["results"][0]["observed_next_allowed_tools"][:2] == [
        "cleanmac_validate_plan",
        "cleanmac_policy_simulate",
    ]


def test_ai_eval_run_developer_tool_scenarios() -> None:
    plan_report = run_json("ai-eval-run", "--scenario", "developer_tool_plan_risk_explanations")
    dry_run_report = run_json("ai-eval-run", "--scenario", "developer_package_manager_dry_run_only")

    assert plan_report["passed"], plan_report
    assert plan_report["results"][0]["observed_schema"] == "cleanmac.tool-plan.v1"
    assert plan_report["results"][0]["observed_blocking_codes"] == []
    assert dry_run_report["passed"], dry_run_report
    assert dry_run_report["results"][0]["observed_schema"] == "cleanmac.tool-execution-result.v1"
    assert dry_run_report["results"][0]["observed_blocking_codes"] == []
