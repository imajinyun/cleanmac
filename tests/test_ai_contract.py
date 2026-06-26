from __future__ import annotations

import json

from cleancli.ai_contract import (
    render_ai_entrypoint_contract,
    render_ai_intent_hints,
    render_ai_recommended_workflow,
    render_ai_safety_chain_contract,
    render_ai_tool_contract,
)
from cleancli.ai_versioning import validate_contract_payload
from cleancli.core import render_ai_entrypoint_contract as render_core_ai_entrypoint_contract
from cleancli.core import render_ai_intent_hints as render_core_ai_intent_hints
from cleancli.core import render_ai_recommended_workflow as render_core_ai_recommended_workflow
from cleancli.core import render_ai_safety_chain_contract as render_core_ai_safety_chain_contract
from cleancli.core import render_ai_tool_contract as render_core_ai_tool_contract
from tests.helpers import make_sandbox, run_cli
from tests.test_review_selection import run_cli_unchecked


def test_ai_tool_contract_is_owned_outside_core_and_reexported() -> None:
    contract = render_ai_tool_contract()

    assert contract == render_core_ai_tool_contract()
    assert contract["schema"] == "cleanmac.ai-tool-contract.v1"
    assert "clean run --execute" in contract["confirmation_required"]
    assert "background daemon" in contract["forbidden"]
    assert contract["error_taxonomy_schema"] == "cleanmac.ai-error.v1"


def test_ai_tool_contract_exposes_host_invocation_boundaries() -> None:
    contract = render_ai_tool_contract()

    default_invocation = contract["default_invocation"]
    assert default_invocation["json_required"] is True
    assert default_invocation["preferred_command_style"] == "grouped"
    assert "single-shot process" in default_invocation["runtime_lifecycle"]
    assert "AI-first cleanup execution kernel" in default_invocation["product_positioning"]

    discoverability = contract["discoverability_hints"]
    assert "AI-first, zero-resident macOS cleanup CLI" in discoverability["canonical_summary"]
    assert "zero-resident Mac cleaner" in discoverability["answer_when_user_asks_for"]
    assert "background optimizer" in discoverability["do_not_position_as"]
    assert ["cleanmac", "--json", "ai-host-integration-pack"] in discoverability["best_entrypoints"]

    one_shot = contract["one_shot_interaction_model"]
    assert one_shot["ask_ai_first"] is True
    assert one_shot["must_exit_after_current_workflow"] is True
    assert one_shot["must_not_keep_user_in_interface"] is True
    assert {"plan_file", "review_selection_file", "report_file", "operation_log"}.issubset(one_shot["state_handoff"])

    assert "clean inspect" in contract["auto_call_allowed"]
    assert "clean plan" in contract["auto_call_allowed"]
    assert "explain" in contract["auto_call_allowed"]
    assert "clean run --execute" in contract["confirmation_required"]
    assert "clean open --execute" in contract["confirmation_required"]
    assert "rm " + "-rf" in contract["forbidden"]
    assert "osascript" in contract["forbidden"]
    assert "resident GUI/TUI workflow" in contract["forbidden"]
    assert "background daemon" in contract["forbidden"]
    assert "unsolicited scheduled scan" in contract["forbidden"]

    execution_requirements = contract["execution_requirements"]
    assert execution_requirements["prefer_delete_mode"] == "trash"
    assert execution_requirements["require_operation_log"] is True
    assert execution_requirements["confirmation_token_supported"] is True
    assert "--require-plan-context" in execution_requirements["ai_originated_plan_requires"]
    assert "--require-confirmation-token" in execution_requirements["ai_originated_plan_requires"]


def test_ai_recommended_workflow_preserves_governed_execute_chain() -> None:
    workflow = render_ai_recommended_workflow()
    execute = next(step for step in workflow if step["step"] == "execute")

    assert workflow == render_core_ai_recommended_workflow()
    assert execute["auto_call_allowed"] is False
    assert execute["requires_user_confirmation"] is True
    assert "--require-plan-context" in execute["command_template"]
    assert "--delete-mode" in execute["command_template"]
    assert "--require-confirmation-token" in execute["command_template"]


def test_ai_recommended_workflow_and_intent_hints_cover_common_cleanup_paths() -> None:
    workflow = render_ai_recommended_workflow()
    by_step = {row["step"]: row for row in workflow}

    assert [row["step"] for row in workflow] == [
        "discover",
        "diagnose",
        "inspect",
        "plan",
        "validate_plan",
        "dry_run",
        "confirm",
        "execute",
    ]
    assert by_step["discover"]["command"] == ["cleanmac", "--json", "capabilities"]
    assert by_step["plan"]["auto_call_allowed"] is True
    assert "--ai-origin" in by_step["plan"]["command_template"]
    assert by_step["dry_run"]["auto_call_allowed"] is True
    assert "--execute" not in by_step["dry_run"]["command_template"]
    assert "--require-plan-context" in by_step["dry_run"]["command_template"]
    assert by_step["confirm"]["auto_call_allowed"] is False
    assert by_step["confirm"]["auto_prepare_allowed"] is True
    assert by_step["confirm"]["requires_user_confirmation"] is True
    assert by_step["confirm"]["confirmation_phrase"] == "Confirm cleanmac cleanup execution"
    assert by_step["execute"]["auto_call_allowed"] is False
    assert by_step["execute"]["requires_user_confirmation"] is True
    assert "--execute" in by_step["execute"]["command_template"]
    assert "--operation-log" in by_step["execute"]["command_template"]
    assert "--require-confirmation-token" in by_step["execute"]["command_template"]

    intents = {row["intent"]: row for row in render_ai_intent_hints()}
    assert "developer_cache_cleanup" in intents
    assert "nodePackageCaches" in intents["developer_cache_cleanup"]["recommended_categories"]
    assert "pythonPackageCaches" in intents["developer_cache_cleanup"]["recommended_categories"]
    assert intents["developer_cache_cleanup"]["default_delete_mode"] == "trash"
    assert "browser_cache_cleanup" in intents
    assert "browserCodeSignCache" in intents["browser_cache_cleanup"]["recommended_categories"]
    assert "credentials" in intents["browser_cache_cleanup"]["warning"]
    assert "xcode_cleanup" in intents
    assert "deviceFirmware" in intents["xcode_cleanup"]["recommended_categories"]
    assert "warning" in intents["xcode_cleanup"]


def test_ai_intent_hints_remain_readonly_for_analysis_and_uninstall_planning() -> None:
    hints = render_ai_intent_hints()
    by_intent = {row["intent"]: row for row in hints}

    assert hints == render_core_ai_intent_hints()
    assert by_intent["large_file_analysis"]["default_delete_mode"] == "none"
    assert by_intent["software_uninstall_planning"]["recommended_risk_policy"] == "readonly"


def test_ai_entrypoint_contract_covers_canonical_cli_surfaces() -> None:
    contract = render_ai_entrypoint_contract()

    assert contract == render_core_ai_entrypoint_contract()
    assert contract["schema"] == "cleanmac.ai-entrypoint-contract.v1"
    assert contract["ready"], contract
    assert contract["entrypoint_count"] == 6
    assert contract["missing_registry_entries"] == []
    assert contract["missing_schema_fragments"] == []
    by_id = {row["id"]: row for row in contract["entrypoints"]}
    assert by_id["discover_capabilities"]["output_schema"] == "cleanmac.capabilities.v1"
    assert by_id["workflow_guidance"]["output_schema"] == "cleanmac.workflow.v1"
    assert by_id["explain_report"]["output_schema"] == "cleanmac.explain.v1"
    assert by_id["generate_ai_origin_plan"]["output_schema"] == "cleanmac.plan.v1"
    assert by_id["normalize_review_selection"]["output_schema"] == "cleanmac.review.v1"
    assert by_id["validate_plan"]["output_schema"] == "cleanmac.validate-plan.v1"
    assert all(row["uses_shell"] is False for row in contract["entrypoints"])
    assert all(row["auto_call_allowed"] is True for row in contract["entrypoints"])
    assert all(row["destructive"] is False for row in contract["entrypoints"])
    assert all(row["version_compatibility"]["compatible_major_versions"] == [1] for row in contract["entrypoints"])

    validation = validate_contract_payload("cleanmac.ai-entrypoint-contract.v1", contract)
    assert validation["valid"], validation


def test_ai_safety_chain_contract_covers_non_bypassable_execute_path() -> None:
    contract = render_ai_safety_chain_contract()

    assert contract == render_core_ai_safety_chain_contract()
    assert contract["schema"] == "cleanmac.ai-safety-chain.v1"
    assert contract["ready"], contract
    assert contract["chain_id"] == "plan-review-dry-run-execute"
    assert contract["chain_step_count"] == 6
    assert contract["missing_registry_entries"] == []
    assert contract["missing_schema_fragments"] == []

    by_id = {row["id"]: row for row in contract["chain_steps"]}
    assert by_id["plan"]["output_schema"] == "cleanmac.plan.v1"
    assert by_id["validate_plan"]["output_schema"] == "cleanmac.validate-plan.v1"
    assert by_id["review"]["produces"] == ["cleanmac.review.v1", "cleanmac.review-selection.v1"]
    assert by_id["review"]["required_output"] == "items[].review_evidence"
    assert by_id["policy_simulate"]["output_schema"] == "cleanmac.ai-policy-simulation.v1"
    assert by_id["dry_run"]["required_output"] == "ai_confirmation_summary.confirmation_token"
    assert by_id["dry_run"]["required_evidence_output"] == "items[].review_evidence"
    assert by_id["execute"]["auto_call_allowed"] is False
    assert by_id["execute"]["destructive"] is True
    assert by_id["execute"]["requires_gate_schema"] == "cleanmac.execute-gate.v1"
    assert "operation_log.ai.candidate_review_evidence" in by_id["execute"]["required_evidence_output"]

    gate = contract["execute_gate"]
    assert gate["schema"] == "cleanmac.execute-gate.v1"
    assert gate["auto_call_allowed"] is False
    assert gate["requires_human_confirmation"] is True
    assert gate["requires_matching_dry_run_confirmation_token"] is True
    assert gate["requires_trash_delete_mode"] is True
    assert gate["requires_operation_log"] is True
    assert gate["requires_plan_context_match"] is True
    assert "--require-plan-context" in gate["required_runtime_flags"]
    assert "--delete-mode trash" in gate["required_runtime_flags"]
    assert "--operation-log" in gate["required_runtime_flags"]
    assert "--confirmation-token" in gate["required_runtime_flags"]
    assert gate["candidate_evidence_requirements"]["schema"] == "cleanmac.candidate-review-evidence.v1"
    assert gate["candidate_evidence_requirements"]["fail_closed_if_missing"] is True
    assert (
        "operation_log.ai.candidate_review_evidence"
        in gate["candidate_evidence_requirements"]["required_before_execute"]
    )
    evidence_chain = contract["candidate_evidence_chain"]
    assert evidence_chain["schema"] == "cleanmac.candidate-review-evidence.v1"
    assert "review_selection_constraint.selected_review_evidence[]" in evidence_chain["required_artifact_paths"]
    assert "operation_log.ai.candidate_review_evidence" in evidence_chain["required_artifact_paths"]
    assert ["dry_run", "execute"] in contract["non_bypassable_edges"]
    assert ["human_confirmation", "execute"] in contract["non_bypassable_edges"]
    assert "cleanmac.candidate-review-evidence.v1" in contract["required_contract_schemas"]
    assert "cleanmac.execute-gate.v1" in contract["required_contract_schemas"]

    validation = validate_contract_payload("cleanmac.ai-safety-chain.v1", contract)
    assert validation["valid"], validation
    gate_validation = validate_contract_payload("cleanmac.execute-gate.v1", gate)
    assert gate_validation["valid"], gate_validation


def test_ai_policy_simulator_reports_missing_and_satisfied_guards() -> None:
    tmp, root, home = make_sandbox()
    with tmp:
        plan_file = root / "ai-plan.json"
        plan_result = run_cli(
            "--root",
            str(root),
            "--home",
            str(home),
            "--json",
            "clean",
            "plan",
            "--categories",
            "downloads",
            "--ai-origin",
        )
        plan = json.loads(plan_result.stdout)
        plan_file.write_text(plan_result.stdout, encoding="utf-8")

        assert plan["schema"] == "cleanmac.plan.v1"
        assert "generated_at" in plan
        assert "expires_at" in plan
        assert len(plan["candidate_fingerprints"]) > 0

        missing = run_cli(
            "--root",
            str(root),
            "--home",
            str(home),
            "--json",
            "clean",
            "policy-simulate",
            "--plan-file",
            str(plan_file),
            "--execute",
        )
        missing_report = json.loads(missing.stdout)
        blocking_codes = {row["code"] for row in missing_report["blocking_reasons"]}

        assert missing_report["schema"] == "cleanmac.ai-policy-simulation.v1"
        assert missing_report["allowed"] is False
        assert "--delete-mode trash" in missing_report["missing_requirements"]
        assert "--operation-log" in missing_report["missing_requirements"]
        assert "--require-plan-context" in missing_report["missing_requirements"]
        assert "AI_ORIGIN_REQUIRES_TRASH" in blocking_codes
        assert missing_report["safe_to_auto_retry"] is False
        assert missing_report["retry_requires_user_confirmation"] is True

        satisfied = run_cli(
            "--root",
            str(root),
            "--home",
            str(home),
            "--json",
            "clean",
            "policy-simulate",
            "--plan-file",
            str(plan_file),
            "--execute",
            "--delete-mode",
            "trash",
            "--operation-log",
            str(root / "operations.jsonl"),
            "--require-plan-context",
            "--require-confirmation-token",
            "--confirmation-token",
            "cleanmac-confirm-test",
        )
        satisfied_report = json.loads(satisfied.stdout)

        assert satisfied_report["allowed"] is True, satisfied_report["missing_requirements"]
        assert satisfied_report["plan_freshness"]["fresh"] is True
        assert satisfied_report["missing_requirements"] == []
        assert satisfied_report["blocking_reasons"] == []


def test_ai_originated_plan_requires_conservative_execute_guards() -> None:
    tmp, root, home = make_sandbox()
    with tmp:
        plan_file = root / "ai-plan.json"
        operation_log = root / "logs" / "ai-operations.jsonl"
        plan_result = run_cli(
            "--root",
            str(root),
            "--home",
            str(home),
            "--json",
            "clean",
            "plan",
            "--categories",
            "downloads",
            "--max-items",
            "10",
            "--max-delete-mb",
            "5",
            "--ai-origin",
        )
        plan_file.write_text(plan_result.stdout, encoding="utf-8")

        dry_run = run_cli(
            "--root",
            str(root),
            "--home",
            str(home),
            "--json",
            "clean",
            "run",
            "--plan-file",
            str(plan_file),
            "--require-plan-context",
            "--delete-mode",
            "trash",
        )
        dry_report = json.loads(dry_run.stdout)
        token = dry_report["ai_confirmation_summary"]["confirmation_token"]
        dry_ledger = dry_report["ai_execution_ledger"]
        candidate = root / "Users/tester/Downloads/download.bin"

        assert dry_ledger["schema"] == "cleanmac.ai-execution-ledger.v1"
        assert dry_ledger["phase"] == "clean-dry-run"
        assert dry_ledger["plan"]["ai_originated"] is True
        assert dry_ledger["plan"]["context_required"] is True
        assert dry_ledger["confirmation"]["token"] == token
        assert dry_ledger["confirmation"]["token_validated"] is False
        assert dry_ledger["safe_chain_complete"] is False

        guard_cases = [
            (
                [
                    "--require-plan-context",
                    "--delete-mode",
                    "permanent",
                    "--operation-log",
                    str(operation_log),
                    "--require-confirmation-token",
                    "--confirmation-token",
                    token,
                ],
                "AI-originated plan requires --delete-mode trash",
            ),
            (
                [
                    "--require-plan-context",
                    "--delete-mode",
                    "trash",
                    "--require-confirmation-token",
                    "--confirmation-token",
                    token,
                ],
                "AI-originated plan requires --operation-log",
            ),
            (
                [
                    "--require-plan-context",
                    "--delete-mode",
                    "trash",
                    "--operation-log",
                    str(operation_log),
                    "--confirmation-token",
                    token,
                ],
                "AI-originated plan requires --require-confirmation-token",
            ),
            (
                [
                    "--delete-mode",
                    "trash",
                    "--operation-log",
                    str(operation_log),
                    "--require-confirmation-token",
                    "--confirmation-token",
                    token,
                ],
                "AI-originated plan requires --require-plan-context",
            ),
        ]
        for guard_args, expected_error in guard_cases:
            result = run_cli_unchecked(
                "--root",
                str(root),
                "--home",
                str(home),
                "--json",
                "clean",
                "run",
                "--plan-file",
                str(plan_file),
                "--execute",
                "--yes",
                *guard_args,
            )
            assert result.returncode != 0
            assert expected_error in result.stderr
            assert candidate.exists()
