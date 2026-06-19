"""One-stop AI Host integration pack for cleanmac discovery metadata."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any


def render_ai_host_integration_pack(
    *,
    readiness: Mapping[str, Any],
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
        *list(readiness.get("recommended_preflight_commands", [])),
    ]
    recommended_call_sequence = [
        "read cleanmac://ai/host-integration-pack",
        *list(governance_advice.get("recommended_call_sequence", [])),
    ]
    mcp_resources = [
        "cleanmac://ai/host-integration-pack",
        "cleanmac://capabilities",
        "cleanmac://ai/function-schemas",
        "cleanmac://ai/mcp-tool-catalog",
        "cleanmac://ai/readiness",
        "cleanmac://ai/runbook",
        "cleanmac://ai/tool-decision-matrix",
        "cleanmac://ai/governance-advice",
        "cleanmac://ai/host-policy",
        "cleanmac://ai/schema-registry",
        "cleanmac://ai/contract-validation",
        "cleanmac://ai/contract-samples",
        "cleanmac://ai/eval-pack",
        "cleanmac://ai/eval-run-smoke",
    ]
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
        "runbook": runbook,
        "decision_matrix": decision_matrix,
        "governance_advice": governance_advice,
        "host_policy": host_policy,
        "schema_registry": schema_registry,
        "eval_pack": eval_pack,
        "contract_validation": contract_validation,
        "contract_samples": contract_samples,
    }
