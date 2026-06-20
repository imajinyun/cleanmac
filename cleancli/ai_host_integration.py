"""One-stop AI Host integration pack for cleanmac discovery metadata."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from cleancli.mcp_prompts import MCP_PROMPT_INDEX_URI, mcp_prompt_names
from cleancli.mcp_resources import MCP_RESOURCE_INDEX_URI, mcp_resource_uris


def render_ai_host_integration_pack(
    *,
    readiness: Mapping[str, Any],
    release_readiness: Mapping[str, Any],
    runbook: Mapping[str, Any],
    decision_matrix: Mapping[str, Any],
    governance_advice: Mapping[str, Any],
    host_policy: Mapping[str, Any],
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
        f"read {MCP_RESOURCE_INDEX_URI}",
        f"read {MCP_PROMPT_INDEX_URI}",
        "read cleanmac://ai/host-integration-pack",
        *list(governance_advice.get("recommended_call_sequence", [])),
    ]:
        if step not in recommended_call_sequence:
            recommended_call_sequence.append(step)
    mcp_resources = mcp_resource_uris()
    mcp_prompts = mcp_prompt_names()
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
            "prompt_index_uri": MCP_PROMPT_INDEX_URI,
            "prompts": mcp_prompts,
            "transport": "stdio",
            "uses_shell": False,
        },
        "cli": {
            "command": ["cleanmac", "--json", "ai-host-integration-pack"],
            "uses_shell": False,
        },
        "critical_schemas": list(critical_schemas),
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
    contract_validation = integration_pack.get("contract_validation", {})
    mcp = integration_pack.get("mcp", {})
    resources = mcp.get("resources", []) if isinstance(mcp, Mapping) else []
    prompts = mcp.get("prompts", []) if isinstance(mcp, Mapping) else []
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
                and MCP_RESOURCE_INDEX_URI in resources
                and MCP_PROMPT_INDEX_URI in resources
                and isinstance(prompts, list)
                and "review-ai-host-policy" in prompts
                and "cleanmac://ai/host-integration-pack" in resources
            ),
            "evidence": "cleanmac.ai-host-tool-call-decision.v1",
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
            "mcp_prompt_index": MCP_PROMPT_INDEX_URI,
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
