"""Auditable AI Host evidence pack for cleanmac runtime governance."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from cleancli.mcp_prompts import MCP_PROMPT_INDEX_URI, validate_mcp_prompt_catalog
from cleancli.mcp_resources import (
    AI_SAFETY_CHAIN_URI,
    MCP_META_INDEX_URI,
    NO_DISTURBANCE_URI,
    MCP_RESOURCE_INDEX_URI,
    MCP_SURFACE_AUDIT_URI,
    RUNTIME_LIFECYCLE_POLICY_URI,
    ZERO_RESIDENT_AUDIT_URI,
    render_mcp_surface_audit,
    validate_mcp_meta_index,
    validate_mcp_resource_catalog,
)
from cleancli.mcp_tools import MCP_TOOL_INDEX_URI, validate_mcp_tool_catalog


def _all_decisions_denied(samples: Sequence[Mapping[str, Any]]) -> bool:
    return all(
        isinstance(sample.get("decision"), Mapping) and sample["decision"].get("allowed") is False for sample in samples
    )


def _blocking_codes(samples: Sequence[Mapping[str, Any]]) -> list[str]:
    codes: set[str] = set()
    for sample in samples:
        decision = sample.get("decision", {})
        if not isinstance(decision, Mapping):
            continue
        for reason in decision.get("blocking_reasons", []):
            if isinstance(reason, Mapping) and reason.get("code"):
                codes.add(str(reason["code"]))
    return sorted(codes)


def _candidate_evidence_chain_ready(candidate_evidence_chain: Mapping[str, Any]) -> bool:
    required_paths = candidate_evidence_chain.get("required_artifact_paths", [])
    return bool(
        candidate_evidence_chain.get("schema") == "cleanmac.candidate-review-evidence.v1"
        and candidate_evidence_chain.get("fail_closed_if_missing") is True
        and isinstance(required_paths, list)
        and "review_selection_constraint.selected_review_evidence[]" in required_paths
        and "dry_run_report.items[].review_evidence" in required_paths
        and "execute_report.items[].review_evidence" in required_paths
        and "operation_log.ai.candidate_review_evidence" in required_paths
    )


def render_ai_host_evidence(
    *,
    integration_pack: Mapping[str, Any],
    preflight: Mapping[str, Any],
    contract_validation: Mapping[str, Any],
    release_readiness: Mapping[str, Any],
    runtime_lifecycle: Mapping[str, Any],
    zero_resident_audit: Mapping[str, Any],
    no_disturbance: Mapping[str, Any],
    runtime_policy_evidence: Sequence[Mapping[str, Any]],
    critical_schemas: Sequence[str],
) -> dict[str, Any]:
    """Return a non-destructive audit evidence pack for AI Host release gates."""

    mcp = integration_pack.get("mcp", {})
    resources = mcp.get("resources", []) if isinstance(mcp, Mapping) else []
    prompts = mcp.get("prompts", []) if isinstance(mcp, Mapping) else []
    tools = mcp.get("tools", []) if isinstance(mcp, Mapping) else []
    meta_validation = validate_mcp_meta_index()
    surface_audit = render_mcp_surface_audit()
    resource_validation = validate_mcp_resource_catalog()
    prompt_validation = validate_mcp_prompt_catalog()
    tool_validation = validate_mcp_tool_catalog()
    safety_chain = integration_pack.get("safety_chain", {})
    candidate_evidence_chain = integration_pack.get("candidate_evidence_chain", {})
    candidate_evidence_requirements = integration_pack.get("host_evidence_requirements", {})
    evidence_checks = [
        {
            "id": "integration-pack-ready",
            "passed": bool(integration_pack.get("ready")),
            "evidence": "cleanmac.ai-host-integration-pack.v1",
        },
        {
            "id": "preflight-ready",
            "passed": bool(preflight.get("ready")),
            "evidence": "cleanmac.ai-host-preflight.v1",
        },
        {
            "id": "contract-validation-ready",
            "passed": bool(contract_validation.get("valid")),
            "evidence": "cleanmac.ai-contract-validation-summary.v1",
        },
        {
            "id": "runtime-denials-covered",
            "passed": _all_decisions_denied(runtime_policy_evidence),
            "evidence": "cleanmac.ai-host-tool-call-decision.v1",
        },
        {
            "id": "mcp-evidence-resource-advertised",
            "passed": "cleanmac://ai/host-evidence" in resources,
            "evidence": "cleanmac://ai/host-evidence",
        },
        {
            "id": "mcp-meta-index-advertised",
            "passed": MCP_META_INDEX_URI in resources,
            "evidence": MCP_META_INDEX_URI,
        },
        {
            "id": "mcp-meta-index-valid",
            "passed": bool(meta_validation.get("valid")),
            "evidence": "cleanmac.mcp-meta-index.v1",
        },
        {
            "id": "mcp-resource-index-advertised",
            "passed": MCP_RESOURCE_INDEX_URI in resources,
            "evidence": MCP_RESOURCE_INDEX_URI,
        },
        {
            "id": "mcp-surface-audit-advertised",
            "passed": MCP_SURFACE_AUDIT_URI in resources,
            "evidence": MCP_SURFACE_AUDIT_URI,
        },
        {
            "id": "mcp-surface-audit-ready",
            "passed": bool(surface_audit.get("ready")) and MCP_SURFACE_AUDIT_URI in resources,
            "evidence": "cleanmac.mcp-surface-audit.v1",
        },
        {
            "id": "runtime-lifecycle-policy-advertised",
            "passed": RUNTIME_LIFECYCLE_POLICY_URI in resources,
            "evidence": RUNTIME_LIFECYCLE_POLICY_URI,
        },
        {
            "id": "ai-safety-chain-advertised",
            "passed": AI_SAFETY_CHAIN_URI in resources,
            "evidence": AI_SAFETY_CHAIN_URI,
        },
        {
            "id": "ai-safety-chain-ready",
            "passed": bool(
                isinstance(safety_chain, Mapping)
                and safety_chain.get("schema") == "cleanmac.ai-safety-chain.v1"
                and safety_chain.get("ready") is True
            ),
            "evidence": "cleanmac.ai-safety-chain.v1",
        },
        {
            "id": "candidate-evidence-chain-exposed",
            "passed": bool(
                isinstance(candidate_evidence_chain, Mapping)
                and _candidate_evidence_chain_ready(candidate_evidence_chain)
                and isinstance(safety_chain, Mapping)
                and safety_chain.get("candidate_evidence_chain") == candidate_evidence_chain
            ),
            "evidence": "cleanmac.candidate-review-evidence.v1",
        },
        {
            "id": "candidate-evidence-chain-preflight-gated",
            "passed": bool(
                isinstance(preflight, Mapping)
                and any(
                    isinstance(check, Mapping)
                    and check.get("id") == "candidate-evidence-chain-ready"
                    and check.get("passed") is True
                    for check in preflight.get("checks", [])
                )
                and "candidate_evidence_chain_ready" in preflight.get("required_before_destructive_tool", [])
            ),
            "evidence": "cleanmac.ai-host-preflight.v1",
        },
        {
            "id": "candidate-evidence-chain-release-gated",
            "passed": bool(
                isinstance(candidate_evidence_requirements, Mapping)
                and candidate_evidence_requirements.get("candidate_evidence_chain_ready") is True
                and candidate_evidence_requirements.get("candidate_evidence_chain_schema")
                == "cleanmac.candidate-review-evidence.v1"
            ),
            "evidence": "cleanmac.ai-host-integration-pack.v1",
        },
        {
            "id": "runtime-lifecycle-policy-valid",
            "passed": bool(
                isinstance(runtime_lifecycle, Mapping)
                and runtime_lifecycle.get("schema") == "cleanmac.runtime-lifecycle-policy.v1"
                and runtime_lifecycle.get("product_model") == "ai-first-ephemeral-cli"
                and runtime_lifecycle.get("runs_only_when_invoked") is True
                and runtime_lifecycle.get("exits_after_workflow") is True
                and runtime_lifecycle.get("resident_processes") == 0
                and runtime_lifecycle.get("implements_tui") is False
                and runtime_lifecycle.get("implements_gui") is False
                and runtime_lifecycle.get("installs_background_daemon") is False
                and runtime_lifecycle.get("performs_unsolicited_scans") is False
            ),
            "evidence": "cleanmac.runtime-lifecycle-policy.v1",
        },
        {
            "id": "zero-resident-audit-advertised",
            "passed": ZERO_RESIDENT_AUDIT_URI in resources,
            "evidence": ZERO_RESIDENT_AUDIT_URI,
        },
        {
            "id": "zero-resident-audit-ready",
            "passed": bool(
                isinstance(zero_resident_audit, Mapping)
                and zero_resident_audit.get("schema") == "cleanmac.zero-resident-audit.v1"
                and zero_resident_audit.get("ready") is True
                and zero_resident_audit.get("product_model") == "ai-first-ephemeral-cli"
                and zero_resident_audit.get("resident_processes") == 0
                and zero_resident_audit.get("failed_check_ids") == []
            ),
            "evidence": "cleanmac.zero-resident-audit.v1",
        },
        {
            "id": "no-disturbance-advertised",
            "passed": NO_DISTURBANCE_URI in resources,
            "evidence": NO_DISTURBANCE_URI,
        },
        {
            "id": "no-disturbance-ready",
            "passed": bool(
                isinstance(no_disturbance, Mapping)
                and no_disturbance.get("schema") == "cleanmac.no-disturbance.v1"
                and no_disturbance.get("ready") is True
                and no_disturbance.get("silent_by_default") is True
                and no_disturbance.get("sends_notifications") is False
                and no_disturbance.get("shows_dialogs") is False
                and no_disturbance.get("push_reminders") is False
                and no_disturbance.get("background_prompts") is False
            ),
            "evidence": "cleanmac.no-disturbance.v1",
        },
        {
            "id": "mcp-resource-catalog-valid",
            "passed": bool(resource_validation.get("valid")),
            "evidence": "cleanmac.mcp-resource-index.v1",
        },
        {
            "id": "mcp-prompt-index-advertised",
            "passed": MCP_PROMPT_INDEX_URI in resources,
            "evidence": MCP_PROMPT_INDEX_URI,
        },
        {
            "id": "mcp-prompt-catalog-valid",
            "passed": bool(prompt_validation.get("valid"))
            and isinstance(prompts, list)
            and "review-ai-host-policy" in prompts,
            "evidence": "cleanmac.mcp-prompt-index.v1",
        },
        {
            "id": "mcp-tool-index-advertised",
            "passed": MCP_TOOL_INDEX_URI in resources,
            "evidence": MCP_TOOL_INDEX_URI,
        },
        {
            "id": "mcp-tool-catalog-valid",
            "passed": bool(tool_validation.get("valid"))
            and isinstance(tools, list)
            and "cleanmac_execute_plan" in tools,
            "evidence": "cleanmac.mcp-tool-index.v1",
        },
        {
            "id": "release-readiness-resource-advertised",
            "passed": "cleanmac://release/readiness" in resources,
            "evidence": "cleanmac://release/readiness",
        },
    ]
    return {
        "schema": "cleanmac.ai-host-evidence.v1",
        "destructive": False,
        "dry_run": True,
        "ready": all(check["passed"] for check in evidence_checks),
        "source": "cleanmac-ai-host-evidence",
        "purpose": "Auditable evidence pack for AI Host runtime governance release gates.",
        "critical_schemas": list(critical_schemas),
        "evidence_checks": evidence_checks,
        "mcp_meta_index": meta_validation,
        "mcp_surface_audit": surface_audit,
        "mcp_resource_catalog": resource_validation,
        "mcp_prompt_catalog": prompt_validation,
        "mcp_tool_catalog": tool_validation,
        "runtime_lifecycle": dict(runtime_lifecycle),
        "zero_resident_audit": dict(zero_resident_audit),
        "no_disturbance": dict(no_disturbance),
        "candidate_evidence_chain": dict(candidate_evidence_chain)
        if isinstance(candidate_evidence_chain, Mapping)
        else {},
        "host_evidence_requirements": dict(candidate_evidence_requirements)
        if isinstance(candidate_evidence_requirements, Mapping)
        else {},
        "observed_blocking_codes": _blocking_codes(runtime_policy_evidence),
        "integration_pack": {
            "schema": integration_pack.get("schema"),
            "ready": bool(integration_pack.get("ready")),
            "mcp_resource": "cleanmac://ai/host-integration-pack",
        },
        "preflight": dict(preflight),
        "contract_validation": dict(contract_validation),
        "release_readiness": dict(release_readiness),
        "runtime_policy_evidence": [dict(sample) for sample in runtime_policy_evidence],
        "release_gate_commands": [
            ["cleanmac", "--json", "ai-host-integration-pack"],
            ["cleanmac", "--json", "ai-host-preflight"],
            ["cleanmac", "--json", "ai-host-evidence"],
            ["cleanmac", "--json", "mcp-surface-audit"],
            ["cleanmac", "--json", "zero-resident-audit"],
            ["cleanmac", "--json", "no-disturbance"],
            ["cleanmac", "--json", "release-readiness"],
            ["make", "ai-contract-smoke"],
            ["make", "mcp-smoke"],
            ["make", "mcp-surface-audit-smoke"],
            ["make", "zero-resident-audit-smoke"],
            ["make", "no-disturbance-smoke"],
            ["make", "ai-governance-smoke"],
            ["make", "ai-host-smoke"],
            ["make", "release-readiness-smoke"],
        ],
        "review_questions": [
            "Did the host load cleanmac://ai/host-integration-pack before tool calls?",
            "Did the host run cleanmac.ai-host-preflight.v1 and stop if ready=false?",
            "Did the host verify candidate evidence continuity before dry-run, execution, and operation-log review?",
            "Did the host verify cleanmac.zero-resident-audit.v1 before orchestration?",
            "Did the host verify cleanmac.no-disturbance.v1 before orchestration?",
            "Were raw command arguments denied before CLI execution?",
            "Were destructive calls denied when confirmation gates were missing?",
            "Did CI run ai-contract-smoke, mcp-smoke, ai-governance-smoke, and ai-host-smoke?",
            "Did release-readiness-smoke aggregate AI Host, contract, eval, and artifact evidence?",
        ],
    }
