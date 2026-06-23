from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from cleancli import ai_schema
from cleancli.ai_decision import render_ai_tool_decision_matrix
from cleancli.ai_eval import render_ai_eval_pack
from cleancli.ai_governance import render_ai_governance_advice, validate_ai_governance_advice
from cleancli.ai_host_policy import render_ai_host_policy, validate_ai_host_policy
from cleancli.ai_runbook import render_ai_runbook
from cleancli.ai_versioning import render_ai_contract_validation_summary, render_ai_schema_registry
from cleancli.mcp_resources import (
    COLD_START_BUDGET_URI,
    DEPENDENCY_GOVERNANCE_URI,
    NO_DISTURBANCE_URI,
    OPERATION_LOG_EXPLAINABILITY_URI,
    RUNTIME_LIFECYCLE_POLICY_URI,
)
from cleancli.mcp_tools import render_mcp_destructive_tool_governance


def render_ai_readiness(
    contract: Mapping[str, Any],
    *,
    release_readiness: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    schema_validation = ai_schema.validate_ai_tool_definitions()
    compatibility = ai_schema.render_contract_compatibility(contract)
    provider_parity = ai_schema.render_provider_export_parity()
    runbook = render_ai_runbook()
    decision_matrix = render_ai_tool_decision_matrix(ai_schema.AI_TOOL_DEFINITIONS, runbook)
    decision_matrix_ready = decision_matrix["violation_count"] == 0
    eval_pack = render_ai_eval_pack()
    runtime_lifecycle = runbook.get("runtime_lifecycle", {})
    runtime_lifecycle_ready = bool(
        isinstance(runtime_lifecycle, Mapping)
        and runtime_lifecycle.get("schema") == "cleanmac.runtime-lifecycle-policy.v1"
        and runtime_lifecycle.get("product_model") == "ai-first-ephemeral-cli"
        and runtime_lifecycle.get("resident_processes") == 0
        and runtime_lifecycle.get("implements_tui") is False
        and runtime_lifecycle.get("implements_gui") is False
        and runtime_lifecycle.get("installs_background_daemon") is False
        and runtime_lifecycle.get("performs_unsolicited_scans") is False
    )
    eval_pack_ready = bool(
        eval_pack["schema"] == "cleanmac.ai-eval-pack.v1"
        and not eval_pack["uses_shell"]
        and not eval_pack["allows_destructive_execution"]
        and eval_pack["scenario_count"] >= 9
    )
    runbook_ready = bool(
        runbook["schema"] == "cleanmac.ai-runbook.v1"
        and not runbook["uses_shell"]
        and not runbook["execution_gate"]["auto_call_allowed"]
    )
    governance_advice = render_ai_governance_advice(
        readiness={"ready": True, "eval_pack": {"ready": eval_pack_ready}},
        runbook=runbook,
        decision_matrix=decision_matrix,
        eval_pack=eval_pack,
    )
    governance_validation = validate_ai_governance_advice(governance_advice)
    governance_ready = bool(governance_advice["ready_for_llm_calling"] and governance_validation["valid"])
    host_policy = render_ai_host_policy(
        decision_matrix=decision_matrix,
        governance_advice=governance_advice,
        runtime_lifecycle=runtime_lifecycle,
    )
    host_policy_validation = validate_ai_host_policy(host_policy)
    host_policy_ready = bool(host_policy["valid"] and host_policy_validation["valid"])
    destructive_tool_governance = render_mcp_destructive_tool_governance()
    destructive_tool_governance_ready = bool(destructive_tool_governance.get("ready"))
    from cleancli.core import (
        render_cold_start_budget_contract,
        render_dependency_governance_contract,
        render_no_disturbance_contract,
        render_operation_log_explainability_contract,
    )

    operation_log_explainability = render_operation_log_explainability_contract()
    operation_log_explainability_ready = bool(operation_log_explainability.get("ready"))
    cold_start_budget = render_cold_start_budget_contract()
    cold_start_budget_ready = bool(cold_start_budget.get("ready"))
    no_disturbance = render_no_disturbance_contract()
    no_disturbance_ready = bool(no_disturbance.get("ready"))
    dependency_governance = render_dependency_governance_contract()
    dependency_governance_ready = bool(dependency_governance.get("ready"))
    schema_registry = render_ai_schema_registry()
    contract_validation = render_ai_contract_validation_summary()
    registry_entries = {str(entry["name"]): entry for entry in schema_registry["entries"]}
    required_contract_schemas = {
        "cleanmac.capabilities.v1",
        "cleanmac.workflow.v1",
        "cleanmac.explain.v1",
        "cleanmac.plan.v1",
        "cleanmac.review.v1",
        "cleanmac.validate-plan.v1",
        "cleanmac.ai-policy-simulation.v1",
        "cleanmac.ai-entrypoint-contract.v1",
        "cleanmac.ai-safety-chain.v1",
        "cleanmac.mcp-destructive-tool-governance.v1",
        "cleanmac.operation-log-explainability.v1",
        "cleanmac.cold-start-budget.v1",
        "cleanmac.no-disturbance.v1",
        "cleanmac.dependency-governance.v1",
        "cleanmac.execute-gate.v1",
        "cleanmac.plan-policy.v1",
        "cleanmac.ai-schema-registry.v1",
        "cleanmac.ai-readiness.v1",
    }
    supported_plan_schemas_registered = all(
        str(schema_name) in registry_entries for schema_name in schema_registry["supported_plan_schemas"]
    )
    core_contract_schemas_present = all(
        "json_schema" in registry_entries.get(schema_name, {}) for schema_name in required_contract_schemas
    )
    schema_registry_ready = bool(
        schema_registry["schema"] == "cleanmac.ai-schema-registry.v1"
        and schema_registry["entry_count"] >= 20
        and schema_registry["latest_plan_schema"] == "cleanmac.plan.v1"
        and supported_plan_schemas_registered
        and core_contract_schemas_present
    )
    return {
        "schema": "cleanmac.ai-readiness.v1",
        "ready": bool(
            schema_validation["valid"]
            and compatibility["compatible"]
            and provider_parity["same_tool_names"]
            and provider_parity["same_tool_count"]
            and runbook_ready
            and runtime_lifecycle_ready
            and decision_matrix_ready
            and eval_pack_ready
            and governance_ready
            and host_policy_ready
            and destructive_tool_governance_ready
            and operation_log_explainability_ready
            and cold_start_budget_ready
            and no_disturbance_ready
            and dependency_governance_ready
            and schema_registry_ready
            and contract_validation["valid"]
        ),
        "tool_count": provider_parity["tool_count"],
        "provider_exports": {
            "function_tool_count": provider_parity["function_tool_count"],
            "openai_tool_count": provider_parity["openai_tool_count"],
            "anthropic_tool_count": provider_parity["anthropic_tool_count"],
            "mcp_tool_count": provider_parity["mcp_tool_count"],
            "same_tool_names": provider_parity["same_tool_names"],
            "same_tool_count": provider_parity["same_tool_count"],
        },
        "contracts": {
            "schema_validation": schema_validation,
            "contract_compatibility": compatibility,
            "provider_export_parity": provider_parity,
        },
        "mcp": {
            "transport": "stdio",
            "server_command": ["cleanmac-mcp"],
            "script_command": ["python3", "scripts/cleanmac_mcp_server.py"],
            "uses_shell": False,
            "resources_supported": True,
            "prompts_supported": True,
            "structured_content_supported": True,
            "self_test_supported": True,
        },
        "runbook": {
            "schema": runbook["schema"],
            "ready": runbook_ready,
            "phase_count": len(runbook["phases"]),
            "execution_auto_call_allowed": runbook["execution_gate"]["auto_call_allowed"],
        },
        "runtime_lifecycle": {
            "schema": runtime_lifecycle.get("schema") if isinstance(runtime_lifecycle, Mapping) else None,
            "ready": runtime_lifecycle_ready,
            "resource_uri": RUNTIME_LIFECYCLE_POLICY_URI,
            "product_model": runtime_lifecycle.get("product_model") if isinstance(runtime_lifecycle, Mapping) else None,
            "resident_processes": runtime_lifecycle.get("resident_processes")
            if isinstance(runtime_lifecycle, Mapping)
            else None,
        },
        "decision_matrix": {
            "schema": decision_matrix["schema"],
            "ready": decision_matrix_ready,
            "tool_count": decision_matrix["tool_count"],
            "violation_count": decision_matrix["violation_count"],
        },
        "eval_pack": {
            "schema": eval_pack["schema"],
            "ready": eval_pack_ready,
            "scenario_count": eval_pack["scenario_count"],
        },
        "eval_runner": {
            "default_scenario": "smoke",
            "destructive_execution_allowed": False,
            "safe_to_run_in_ci": True,
        },
        "trace_persistence": {
            "supported": True,
            "format": "jsonl",
            "redaction": "shell-metachar-argv-filter",
        },
        "governance_advice": {
            "schema": governance_advice["schema"],
            "ready": governance_ready,
            "level": governance_advice["governance_score"]["level"],
            "validation": governance_validation,
        },
        "host_policy": {
            "schema": host_policy["schema"],
            "ready": host_policy_ready,
            "default_decision": host_policy["default_decision"],
            "validation": host_policy_validation,
        },
        "schema_registry": {
            "schema": schema_registry["schema"],
            "ready": schema_registry_ready,
            "entry_count": schema_registry["entry_count"],
            "stable_schema_count": schema_registry["stable_schema_count"],
            "deprecated_schema_count": schema_registry["deprecated_schema_count"],
            "latest_plan_schema": schema_registry["latest_plan_schema"],
            "supported_plan_schemas_registered": supported_plan_schemas_registered,
            "core_contract_schemas_present": core_contract_schemas_present,
        },
        "entrypoint_contract": {
            "schema": "cleanmac.ai-entrypoint-contract.v1",
            "ready": "json_schema" in registry_entries.get("cleanmac.ai-entrypoint-contract.v1", {}),
            "canonical_entrypoint_schemas": [
                "cleanmac.capabilities.v1",
                "cleanmac.workflow.v1",
                "cleanmac.explain.v1",
                "cleanmac.plan.v1",
                "cleanmac.review.v1",
                "cleanmac.validate-plan.v1",
            ],
        },
        "safety_chain": {
            "schema": "cleanmac.ai-safety-chain.v1",
            "ready": "json_schema" in registry_entries.get("cleanmac.ai-safety-chain.v1", {}),
            "required_contract_schemas": [
                "cleanmac.plan.v1",
                "cleanmac.plan-policy.v1",
                "cleanmac.validate-plan.v1",
                "cleanmac.review.v1",
                "cleanmac.review-selection.v1",
                "cleanmac.review-selection-constraint.v1",
                "cleanmac.review-selection-validation.v1",
                "cleanmac.ai-policy-simulation.v1",
                "cleanmac.clean.v1",
                "cleanmac.execute-gate.v1",
            ],
        },
        "destructive_tool_governance": {
            "schema": destructive_tool_governance["schema"],
            "ready": destructive_tool_governance_ready,
            "destructive_tool_count": destructive_tool_governance["destructive_tool_count"],
            "destructive_tool_names": destructive_tool_governance["destructive_tool_names"],
            "validation": destructive_tool_governance["validation"],
        },
        "operation_log_explainability": {
            "schema": operation_log_explainability["schema"],
            "ready": operation_log_explainability_ready,
            "resource_uri": OPERATION_LOG_EXPLAINABILITY_URI,
            "required_entry_fields": operation_log_explainability["required_entry_fields"],
            "validation": operation_log_explainability["validation"],
        },
        "cold_start_budget": {
            "schema": cold_start_budget["schema"],
            "ready": cold_start_budget_ready,
            "resource_uri": COLD_START_BUDGET_URI,
            "budgets": cold_start_budget["budgets"],
            "validation": cold_start_budget["validation"],
        },
        "no_disturbance": {
            "schema": no_disturbance["schema"],
            "ready": no_disturbance_ready,
            "resource_uri": NO_DISTURBANCE_URI,
            "silent_by_default": no_disturbance["silent_by_default"],
            "validation": no_disturbance["validation"],
        },
        "dependency_governance": {
            "schema": dependency_governance["schema"],
            "ready": dependency_governance_ready,
            "resource_uri": DEPENDENCY_GOVERNANCE_URI,
            "runtime_dependency_policy": dependency_governance["runtime_dependency_policy"],
            "validation": dependency_governance["validation"],
        },
        "contract_validation": {
            "schema": contract_validation["schema"],
            "ready": bool(contract_validation["valid"]),
            "validated_schema_count": contract_validation["validated_schema_count"],
            "failure_count": contract_validation["failure_count"],
            "contract_schema_coverage": contract_validation["contract_schema_coverage"],
        },
        "release_readiness": dict(release_readiness or {}),
        "recommended_starting_tools": [
            "cleanmac_capabilities",
            "cleanmac_list_categories",
            "cleanmac_workflow",
        ],
        "mandatory_before_execute": [
            "cleanmac_generate_plan",
            "cleanmac_validate_plan",
            "cleanmac_policy_simulate",
            "cleanmac_dry_run_plan",
            "human_confirmation",
        ],
        "recommended_preflight_commands": [
            ["cleanmac", "--json", "ai-host-integration-pack"],
            ["cleanmac", "--json", "ai-host-preflight"],
            ["cleanmac", "--json", "ai-host-evidence"],
            ["cleanmac", "--json", "release-readiness"],
            ["cleanmac", "--json", "ai-self-test"],
            ["cleanmac", "--json", "ai-readiness"],
            ["cleanmac", "--json", "ai-runbook"],
            ["cleanmac", "--json", "ai-decision-matrix"],
            ["cleanmac", "--json", "ai-governance-advice"],
            ["cleanmac", "--json", "ai-host-policy"],
            ["cleanmac", "--json", "mcp-destructive-tool-governance"],
            ["cleanmac", "--json", "operation-log-explainability"],
            ["cleanmac", "--json", "cold-start-budget"],
            ["cleanmac", "--json", "no-disturbance"],
            ["cleanmac", "--json", "dependency-governance"],
            ["cleanmac", "--json", "ai-schema-registry"],
            ["cleanmac", "--json", "ai-eval-pack"],
            ["cleanmac", "--json", "ai-eval-run", "--scenario", "smoke"],
        ],
    }
