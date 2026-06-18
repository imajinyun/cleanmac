from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from cleancli import ai_schema
from cleancli.ai_decision import render_ai_tool_decision_matrix
from cleancli.ai_eval import render_ai_eval_pack
from cleancli.ai_governance import render_ai_governance_advice, validate_ai_governance_advice
from cleancli.ai_runbook import render_ai_runbook


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
        and eval_pack["scenario_count"] >= 4
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
        "governance_advice": {
            "schema": governance_advice["schema"],
            "ready": governance_ready,
            "level": governance_advice["governance_score"]["level"],
            "validation": governance_validation,
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
            ["cleanmac", "--json", "ai-self-test"],
            ["cleanmac", "--json", "ai-readiness"],
            ["cleanmac", "--json", "ai-runbook"],
            ["cleanmac", "--json", "ai-decision-matrix"],
            ["cleanmac", "--json", "ai-governance-advice"],
            ["cleanmac", "--json", "ai-eval-pack"],
            ["cleanmac", "--json", "ai-eval-run", "--scenario", "smoke"],
        ],
    }
