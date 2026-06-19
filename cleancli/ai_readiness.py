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


def render_ai_readiness(contract: Mapping[str, Any]) -> dict[str, Any]:
    schema_validation = ai_schema.validate_ai_tool_definitions()
    compatibility = ai_schema.render_contract_compatibility(contract)
    provider_parity = ai_schema.render_provider_export_parity()
    runbook = render_ai_runbook()
    decision_matrix = render_ai_tool_decision_matrix(ai_schema.AI_TOOL_DEFINITIONS, runbook)
    decision_matrix_ready = decision_matrix["violation_count"] == 0
    eval_pack = render_ai_eval_pack()
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
    host_policy = render_ai_host_policy(decision_matrix=decision_matrix, governance_advice=governance_advice)
    host_policy_validation = validate_ai_host_policy(host_policy)
    host_policy_ready = bool(host_policy["valid"] and host_policy_validation["valid"])
    schema_registry = render_ai_schema_registry()
    contract_validation = render_ai_contract_validation_summary()
    registry_entries = {str(entry["name"]): entry for entry in schema_registry["entries"]}
    required_contract_schemas = {
        "cleanmac.plan.v1",
        "cleanmac.validate-plan.v1",
        "cleanmac.ai-policy-simulation.v1",
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
            and decision_matrix_ready
            and eval_pack_ready
            and governance_ready
            and host_policy_ready
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
        "contract_validation": {
            "schema": contract_validation["schema"],
            "ready": bool(contract_validation["valid"]),
            "validated_schema_count": contract_validation["validated_schema_count"],
            "failure_count": contract_validation["failure_count"],
            "contract_schema_coverage": contract_validation["contract_schema_coverage"],
        },
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
            ["cleanmac", "--json", "ai-self-test"],
            ["cleanmac", "--json", "ai-readiness"],
            ["cleanmac", "--json", "ai-runbook"],
            ["cleanmac", "--json", "ai-decision-matrix"],
            ["cleanmac", "--json", "ai-governance-advice"],
            ["cleanmac", "--json", "ai-host-policy"],
            ["cleanmac", "--json", "ai-schema-registry"],
            ["cleanmac", "--json", "ai-eval-pack"],
            ["cleanmac", "--json", "ai-eval-run", "--scenario", "smoke"],
        ],
    }
