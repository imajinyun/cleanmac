from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
CLI = PROJECT_ROOT / "cleanmac.py"


@pytest.fixture(scope="module")
def host_policy_report() -> dict[str, Any]:
    result = subprocess.run(
        [sys.executable, str(CLI), "--json", "ai-host-policy"],
        text=True,
        capture_output=True,
        check=True,
    )
    return json.loads(result.stdout)


def test_host_policy_schema_and_validity(host_policy_report: dict[str, Any]) -> None:
    assert host_policy_report["schema"] == "cleanmac.ai-host-policy.v1"
    assert host_policy_report["valid"], host_policy_report
    assert host_policy_report["default_decision"] == "deny"


def test_host_policy_embeds_runtime_lifecycle_obligations(host_policy_report: dict[str, Any]) -> None:
    lifecycle = host_policy_report["runtime_lifecycle"]
    assert lifecycle["schema"] == "cleanmac.runtime-lifecycle-policy.v1"
    assert lifecycle["product_model"] == "ai-first-ephemeral-cli"
    assert lifecycle["runs_only_when_invoked"]
    assert lifecycle["exits_after_workflow"]
    assert lifecycle["resident_processes"] == 0
    assert not lifecycle["implements_tui"]
    assert not lifecycle["implements_gui"]
    assert not lifecycle["installs_background_daemon"]
    assert not lifecycle["performs_unsolicited_scans"]
    obligations = host_policy_report["host_runtime_obligations"]
    assert obligations["must_read_resource_before_execution"] == "cleanmac://ai/runtime-lifecycle-policy"
    assert obligations["must_not_expect_resident_process"]
    assert obligations["must_not_schedule_background_scans"]
    assert obligations["must_not_install_login_item_or_daemon"]
    assert obligations["must_not_send_notifications_or_prompts"]


def test_host_policy_transport_restrictions(host_policy_report: dict[str, Any]) -> None:
    assert not host_policy_report["transport"]["shell_allowed"]
    assert not host_policy_report["transport"]["raw_command_input_allowed"]
    assert host_policy_report["transport"]["path_and_log_text_are_untrusted_data"]


def test_host_policy_auto_call_allow_deny(host_policy_report: dict[str, Any]) -> None:
    assert "cleanmac_capabilities" in host_policy_report["auto_call"]["allow"]
    assert "cleanmac_dry_run_plan" in host_policy_report["auto_call"]["allow"]
    assert "cleanmac_execute_plan" in host_policy_report["auto_call"]["deny"]
    assert "cleanmac_execute_plan" in host_policy_report["auto_call"]["destructive_tools"]
    assert host_policy_report["auto_call"]["deny_reasons"]["cleanmac_execute_plan"] == (
        "destructive_or_confirmation_required"
    )


def test_host_policy_execution_gate(host_policy_report: dict[str, Any]) -> None:
    gate = host_policy_report["execution_gate"]
    assert not gate["auto_call_allowed"]
    assert gate["requires_human_confirmation"]
    assert gate["requires_matching_dry_run_confirmation_token"]
    assert gate["requires_trash_delete_mode"]
    assert gate["requires_operation_log"]
    assert gate["requires_plan_context_match"]
    assert "cleanmac_policy_simulate" in gate["required_predecessor_tools"]


def test_host_policy_prompt_injection_boundary(host_policy_report: dict[str, Any]) -> None:
    boundary = host_policy_report["prompt_injection_boundary"]
    assert "paths" in boundary["never_treat_as_instructions"]
    assert "scan_results" in boundary["treat_as_data"]


def test_host_policy_error_recovery(host_policy_report: dict[str, Any]) -> None:
    assert host_policy_report["error_recovery"]["follow_next_allowed_tools_only"]
    assert "cleanmac://ai/host-policy" in host_policy_report["required_resources_before_execution"]
    assert "cleanmac://ai/runtime-lifecycle-policy" in host_policy_report["required_resources_before_execution"]
    assert "cleanmac://ai/cold-start-budget" in host_policy_report["required_resources_before_execution"]
    assert "cleanmac://ai/no-disturbance" in host_policy_report["required_resources_before_execution"]
    assert "cleanmac://release/dependency-governance" in host_policy_report["required_resources_before_execution"]


def test_host_policy_renderer_handles_partial_decision_matrix() -> None:
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
        runtime_lifecycle={"schema": "cleanmac.runtime-lifecycle-policy.v1"},
    )

    assert report["schema"] == "cleanmac.ai-host-policy.v1"
    assert not report["valid"]
    assert report["auto_call"]["allow"] == ["cleanmac_capabilities"]
    assert report["auto_call"]["readonly_tools"] == ["cleanmac_capabilities"]
    assert report["auto_call"]["planning_tools"] == ["cleanmac_generate_plan"]
    assert report["auto_call"]["dry_run_tools"] == ["cleanmac_dry_run_plan"]
    assert "cleanmac_execute_plan" not in report["auto_call"]["destructive_tools"]


def test_host_policy_validation_reports_structural_violations() -> None:
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

    assert validation["schema"] == "cleanmac.ai-host-policy-validation.v1"
    assert not validation["valid"]
    joined = "\n".join(validation["violations"])
    assert "schema must be cleanmac.ai-host-policy.v1" in joined
    assert "default_decision must be deny" in joined
    assert "transport.shell_allowed must be false" in joined
    assert "auto_call must be an object" in joined
    assert "execution_gate must be an object" in joined
    assert "runtime_lifecycle must be an object" in joined
    assert "host_runtime_obligations must be an object" in joined
    assert "host policy valid flag must be true" in joined


def test_host_policy_validation_reports_missing_destructive_gate_flags() -> None:
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
            "runtime_lifecycle": {"schema": "cleanmac.runtime-lifecycle-policy.v1"},
            "host_runtime_obligations": {},
            "valid": True,
        }
    )

    assert not validation["valid"]
    joined = "\n".join(validation["violations"])
    assert "cleanmac_execute_plan must be auto-call denied" in joined
    assert "cleanmac_execute_plan must be marked destructive" in joined
    assert "execution_gate.requires_human_confirmation must be true" in joined
    assert "execution_gate.requires_plan_context_match must be true" in joined
    assert "runtime_lifecycle.product_model must be 'ai-first-ephemeral-cli'" in joined
    assert "required_resources_before_execution must include runtime lifecycle policy resource" in joined


def test_tool_call_decision_allows_readonly_structured_arguments() -> None:
    from cleancli.ai_host_policy import evaluate_ai_host_tool_call

    decision = evaluate_ai_host_tool_call(
        tool={
            "name": "cleanmac_capabilities",
            "risk": "readonly",
            "auto_call_allowed": True,
            "requires_confirmation": False,
        },
        arguments={},
        source="unit-test",
    )

    assert decision["schema"] == "cleanmac.ai-host-tool-call-decision.v1"
    assert decision["allowed"], decision
    assert decision["safe_to_auto_retry"]
    assert decision["blocking_reasons"] == []
    assert decision["next_allowed_tools"] == []


def test_standard_blocked_next_allowed_tools_are_deduplicated() -> None:
    from cleancli.ai_schema import next_allowed_tools_for_block

    assert next_allowed_tools_for_block(("cleanmac_policy_simulate", "cleanmac_dry_run_plan")) == [
        "cleanmac_validate_plan",
        "cleanmac_policy_simulate",
        "cleanmac_dry_run_plan",
    ]


def test_tool_call_decision_denies_raw_command_arguments() -> None:
    from cleancli.ai_host_policy import evaluate_ai_host_tool_call

    dangerous_raw_command = "rm " + "-rf /"
    decision = evaluate_ai_host_tool_call(
        tool={
            "name": "cleanmac_capabilities",
            "risk": "readonly",
            "auto_call_allowed": True,
            "requires_confirmation": False,
        },
        arguments={"raw_command": dangerous_raw_command, "shell": True},
        source="unit-test",
    )

    assert not decision["allowed"]
    assert not decision["safe_to_auto_retry"]
    codes = [reason["code"] for reason in decision["blocking_reasons"]]
    assert codes == ["RAW_COMMAND_ARGUMENT_DENIED", "RAW_COMMAND_ARGUMENT_DENIED"]
    assert [reason["field"] for reason in decision["blocking_reasons"]] == ["raw_command", "shell"]
    assert decision["next_allowed_tools"] == ["cleanmac_validate_plan", "cleanmac_policy_simulate"]


def test_tool_call_decision_denies_destructive_call_without_runtime_gates() -> None:
    from cleancli.ai_host_policy import evaluate_ai_host_tool_call

    decision = evaluate_ai_host_tool_call(
        tool={
            "name": "cleanmac_execute_plan",
            "risk": "destructive",
            "auto_call_allowed": False,
            "requires_confirmation": True,
        },
        arguments={"plan_file": "/tmp/plan.json", "require_plan_context": False},
        source="unit-test",
    )

    assert not decision["allowed"]
    assert not decision["safe_to_auto_retry"]
    codes = {reason["code"] for reason in decision["blocking_reasons"]}
    assert "HUMAN_CONFIRMATION_PHRASE_REQUIRED" in codes
    assert "CONFIRMATION_TOKEN_REQUIRED" in codes
    assert "OPERATION_LOG_REQUIRED" in codes
    assert "PLAN_CONTEXT_REQUIRED" in codes
    assert decision["next_allowed_tools"] == ["cleanmac_validate_plan", "cleanmac_policy_simulate"]


def test_tool_call_decision_allows_destructive_call_only_with_runtime_gates() -> None:
    from cleancli.ai_host_policy import evaluate_ai_host_tool_call

    decision = evaluate_ai_host_tool_call(
        tool={
            "name": "cleanmac_execute_plan",
            "risk": "destructive",
            "auto_call_allowed": False,
            "requires_confirmation": True,
        },
        arguments={
            "plan_file": "/tmp/plan.json",
            "confirmation_phrase": "Confirm cleanmac cleanup execution",
            "confirmation_token": "abc123",
            "operation_log": "/tmp/cleanmac-operations.jsonl",
            "require_plan_context": True,
        },
        source="unit-test",
    )

    assert decision["allowed"], decision
    assert not decision["safe_to_auto_retry"]
    assert decision["blocking_reasons"] == []
    assert decision["next_allowed_tools"] == []
