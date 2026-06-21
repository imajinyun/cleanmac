"""One-stop AI Host integration pack for cleanmac discovery metadata."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from cleancli.mcp_prompts import MCP_PROMPT_INDEX_URI, mcp_prompt_names
from cleancli.mcp_resources import (
    AI_WORKFLOW_CONTRACT_URI,
    MCP_META_INDEX_URI,
    MCP_RESOURCE_INDEX_URI,
    MCP_SURFACE_AUDIT_URI,
    RUNTIME_LIFECYCLE_POLICY_URI,
    mcp_resource_uris,
)
from cleancli.mcp_tools import MCP_TOOL_INDEX_URI, mcp_tool_names


def render_ai_host_integration_pack(
    *,
    readiness: Mapping[str, Any],
    release_readiness: Mapping[str, Any],
    runbook: Mapping[str, Any],
    decision_matrix: Mapping[str, Any],
    governance_advice: Mapping[str, Any],
    host_policy: Mapping[str, Any],
    runtime_lifecycle: Mapping[str, Any],
    schema_registry: Mapping[str, Any],
    eval_pack: Mapping[str, Any],
    contract_validation: Mapping[str, Any],
    contract_samples: Mapping[str, Any],
    critical_schemas: Sequence[str],
) -> dict[str, Any]:
    """Return a machine-readable one-stop integration pack for AI Hosts."""

    recommended_preflight_commands = [
        ["cleanmac", "--json", "ai-host-integration-pack"],
        ["cleanmac", "--json", "ai-host-evidence"],
        ["cleanmac", "--json", "release-readiness"],
        *list(readiness.get("recommended_preflight_commands", [])),
    ]
    recommended_call_sequence = []
    for step in [
        f"read {MCP_META_INDEX_URI}",
        f"read {MCP_RESOURCE_INDEX_URI}",
        f"read {MCP_PROMPT_INDEX_URI}",
        f"read {MCP_TOOL_INDEX_URI}",
        f"read {MCP_SURFACE_AUDIT_URI}",
        "read cleanmac://ai/host-integration-pack",
        f"read {AI_WORKFLOW_CONTRACT_URI}",
        f"read {RUNTIME_LIFECYCLE_POLICY_URI}",
        *list(governance_advice.get("recommended_call_sequence", [])),
    ]:
        if step not in recommended_call_sequence:
            recommended_call_sequence.append(step)
    mcp_resources = mcp_resource_uris()
    mcp_prompts = mcp_prompt_names()
    mcp_tools = mcp_tool_names()
    ready = bool(
        readiness.get("ready")
        and host_policy.get("valid")
        and governance_advice.get("ready_for_llm_calling")
        and contract_validation.get("valid")
        and eval_pack.get("schema") == "cleanmac.ai-eval-pack.v1"
        and not eval_pack.get("allows_destructive_execution", True)
    )
    return {
        "schema": "cleanmac.ai-host-integration-pack.v1",
        "destructive": False,
        "dry_run": True,
        "ready": ready,
        "purpose": "One-stop AI Host discovery pack for safe cleanmac tool integration.",
        "mcp": {
            "resource_uri": "cleanmac://ai/host-integration-pack",
            "resources": mcp_resources,
            "meta_index_uri": MCP_META_INDEX_URI,
            "prompt_index_uri": MCP_PROMPT_INDEX_URI,
            "prompts": mcp_prompts,
            "tool_index_uri": MCP_TOOL_INDEX_URI,
            "surface_audit_uri": MCP_SURFACE_AUDIT_URI,
            "tools": mcp_tools,
            "transport": "stdio",
            "uses_shell": False,
        },
        "cli": {
            "command": ["cleanmac", "--json", "ai-host-integration-pack"],
            "uses_shell": False,
        },
        "critical_schemas": list(critical_schemas),
        "runtime_lifecycle": dict(runtime_lifecycle),
        "recommended_preflight_commands": recommended_preflight_commands,
        "recommended_call_sequence": recommended_call_sequence,
        "readiness": readiness,
        "release_readiness": dict(release_readiness),
        "runbook": runbook,
        "decision_matrix": decision_matrix,
        "governance_advice": governance_advice,
        "host_policy": host_policy,
        "schema_registry": schema_registry,
        "eval_pack": eval_pack,
        "contract_validation": contract_validation,
        "contract_samples": contract_samples,
    }


def render_ai_host_preflight(
    *,
    integration_pack: Mapping[str, Any],
    runtime_policy_schema_registered: bool,
) -> dict[str, Any]:
    """Return a runtime preflight gate report for AI Host orchestration."""

    host_policy = integration_pack.get("host_policy", {})
    runtime_lifecycle = integration_pack.get("runtime_lifecycle", {})
    contract_validation = integration_pack.get("contract_validation", {})
    mcp = integration_pack.get("mcp", {})
    resources = mcp.get("resources", []) if isinstance(mcp, Mapping) else []
    prompts = mcp.get("prompts", []) if isinstance(mcp, Mapping) else []
    tools = mcp.get("tools", []) if isinstance(mcp, Mapping) else []
    checks = [
        {
            "id": "integration-pack-ready",
            "passed": bool(integration_pack.get("ready")),
            "evidence": "cleanmac.ai-host-integration-pack.v1",
        },
        {
            "id": "host-policy-valid",
            "passed": bool(isinstance(host_policy, Mapping) and host_policy.get("valid")),
            "evidence": "cleanmac.ai-host-policy.v1",
        },
        {
            "id": "contract-validation-valid",
            "passed": bool(isinstance(contract_validation, Mapping) and contract_validation.get("valid")),
            "evidence": "cleanmac.ai-contract-validation-summary.v1",
        },
        {
            "id": "mcp-runtime-policy-present",
            "passed": bool(
                runtime_policy_schema_registered
                and isinstance(resources, list)
                and MCP_META_INDEX_URI in resources
                and MCP_RESOURCE_INDEX_URI in resources
                and MCP_PROMPT_INDEX_URI in resources
                and MCP_TOOL_INDEX_URI in resources
                and MCP_SURFACE_AUDIT_URI in resources
                and isinstance(prompts, list)
                and "review-ai-host-policy" in prompts
                and isinstance(tools, list)
                and "cleanmac_execute_plan" in tools
                and "cleanmac://ai/host-integration-pack" in resources
                and AI_WORKFLOW_CONTRACT_URI in resources
                and RUNTIME_LIFECYCLE_POLICY_URI in resources
            ),
            "evidence": RUNTIME_LIFECYCLE_POLICY_URI,
        },
        {
            "id": "runtime-lifecycle-policy-valid",
            "passed": bool(
                isinstance(runtime_lifecycle, Mapping)
                and runtime_lifecycle.get("schema") == "cleanmac.runtime-lifecycle-policy.v1"
                and runtime_lifecycle.get("product_model") == "ai-first-ephemeral-cli"
                and runtime_lifecycle.get("resident_processes") == 0
                and runtime_lifecycle.get("implements_tui") is False
                and runtime_lifecycle.get("implements_gui") is False
                and runtime_lifecycle.get("installs_background_daemon") is False
                and runtime_lifecycle.get("performs_unsolicited_scans") is False
            ),
            "evidence": "cleanmac.runtime-lifecycle-policy.v1",
        },
    ]
    return {
        "schema": "cleanmac.ai-host-preflight.v1",
        "destructive": False,
        "dry_run": True,
        "ready": all(check["passed"] for check in checks),
        "purpose": "Runtime preflight gate for AI Host cleanmac orchestration.",
        "entrypoint": {
            "cli": ["cleanmac", "--json", "ai-host-integration-pack"],
            "mcp_resource": "cleanmac://ai/host-integration-pack",
            "mcp_meta_index": MCP_META_INDEX_URI,
            "mcp_prompt_index": MCP_PROMPT_INDEX_URI,
            "mcp_tool_index": MCP_TOOL_INDEX_URI,
            "mcp_surface_audit": MCP_SURFACE_AUDIT_URI,
            "workflow_contract": AI_WORKFLOW_CONTRACT_URI,
            "runtime_lifecycle_policy": RUNTIME_LIFECYCLE_POLICY_URI,
        },
        "checks": checks,
        "required_before_destructive_tool": [
            "cleanmac_generate_plan",
            "cleanmac_validate_plan",
            "cleanmac_policy_simulate",
            "cleanmac_dry_run_plan",
            "human_confirmation_phrase",
            "matching_confirmation_token",
            "plan_context_match",
            "trash_delete_mode",
            "operation_log",
        ],
        "release_gate_commands": [
            ["make", "mcp-smoke"],
            ["make", "ai-host-smoke"],
            ["make", "ai-governance-smoke"],
            ["make", "ai-contract-smoke"],
        ],
    }
