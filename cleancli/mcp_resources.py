"""Central MCP resource catalog and safety metadata for cleanmac AI hosts."""

from __future__ import annotations

from typing import Any

from cleancli.mcp_prompts import MCP_PROMPT_INDEX_SCHEMA, MCP_PROMPT_INDEX_URI
from cleancli.mcp_tools import (
    MCP_DESTRUCTIVE_TOOL_GOVERNANCE_SCHEMA,
    MCP_DESTRUCTIVE_TOOL_GOVERNANCE_URI,
    MCP_TOOL_INDEX_SCHEMA,
    MCP_TOOL_INDEX_URI,
)

MCP_META_INDEX_SCHEMA = "cleanmac.mcp-meta-index.v1"
MCP_META_INDEX_URI = "cleanmac://mcp/meta-index"
MCP_RESOURCE_INDEX_SCHEMA = "cleanmac.mcp-resource-index.v1"
MCP_RESOURCE_INDEX_URI = "cleanmac://mcp/resource-index"
MCP_SURFACE_AUDIT_SCHEMA = "cleanmac.mcp-surface-audit.v1"
MCP_SURFACE_AUDIT_URI = "cleanmac://mcp/surface-audit"
RUNTIME_LIFECYCLE_POLICY_URI = "cleanmac://ai/runtime-lifecycle-policy"
ZERO_RESIDENT_AUDIT_URI = "cleanmac://ai/zero-resident-audit"
AI_WORKFLOW_CONTRACT_URI = "cleanmac://ai/workflow-contract"
AI_ENTRYPOINT_CONTRACT_URI = "cleanmac://ai/entrypoints"
AI_SAFETY_CHAIN_URI = "cleanmac://ai/safety-chain"
OPERATION_LOG_EXPLAINABILITY_URI = "cleanmac://ai/operation-log-explainability"
OPERATION_LOG_EXPLAINABILITY_SCHEMA = "cleanmac.operation-log-explainability.v1"
DEPENDENCY_GOVERNANCE_URI = "cleanmac://release/dependency-governance"
DEPENDENCY_GOVERNANCE_SCHEMA = "cleanmac.dependency-governance.v1"
NO_DISTURBANCE_URI = "cleanmac://ai/no-disturbance"
NO_DISTURBANCE_SCHEMA = "cleanmac.no-disturbance.v1"
COLD_START_BUDGET_URI = "cleanmac://ai/cold-start-budget"
COLD_START_BUDGET_SCHEMA = "cleanmac.cold-start-budget.v1"
MCP_RESOURCE_SENSITIVE_DATA_POLICY = "redacted-local-paths-no-credentials"


_RESOURCE_ROWS: tuple[dict[str, Any], ...] = (
    {
        "uri": MCP_META_INDEX_URI,
        "name": "cleanmac MCP meta index",
        "description": "Top-level MCP governance index aggregating resource, prompt, and tool indexes.",
        "category": "mcp",
        "schema": MCP_META_INDEX_SCHEMA,
    },
    {
        "uri": MCP_RESOURCE_INDEX_URI,
        "name": "cleanmac MCP resource index",
        "description": "Governed MCP resource catalog with schema, category, and safety metadata.",
        "category": "mcp",
        "schema": MCP_RESOURCE_INDEX_SCHEMA,
    },
    {
        "uri": MCP_PROMPT_INDEX_URI,
        "name": "cleanmac MCP prompt index",
        "description": "Governed MCP prompt catalog with arguments, categories, and safety metadata.",
        "category": "mcp",
        "schema": MCP_PROMPT_INDEX_SCHEMA,
    },
    {
        "uri": MCP_TOOL_INDEX_URI,
        "name": "cleanmac MCP tool index",
        "description": "Governed MCP tool catalog with invocation, risk, and safety metadata.",
        "category": "mcp",
        "schema": MCP_TOOL_INDEX_SCHEMA,
    },
    {
        "uri": MCP_DESTRUCTIVE_TOOL_GOVERNANCE_URI,
        "name": "cleanmac MCP destructive tool governance",
        "description": "Machine-readable destructive MCP tool gates, annotations, and argv-only safety contract.",
        "category": "mcp",
        "schema": MCP_DESTRUCTIVE_TOOL_GOVERNANCE_SCHEMA,
    },
    {
        "uri": MCP_SURFACE_AUDIT_URI,
        "name": "cleanmac MCP surface audit",
        "description": "Read-only audit of MCP resource, prompt, tool, and meta index readiness.",
        "category": "mcp",
        "schema": MCP_SURFACE_AUDIT_SCHEMA,
    },
    {
        "uri": "cleanmac://capabilities",
        "name": "cleanmac capabilities",
        "description": "Full cleanmac capability and AI governance report.",
        "category": "core",
        "schema": "cleanmac.capabilities.v1",
    },
    {
        "uri": "cleanmac://ai/function-schemas",
        "name": "cleanmac function schemas",
        "description": "JSON Schema function definitions for LLM tool calling.",
        "category": "ai",
        "schema": "cleanmac.ai-function-schemas.v1",
    },
    {
        "uri": "cleanmac://ai/mcp-tool-catalog",
        "name": "cleanmac MCP tool catalog",
        "description": "MCP-compatible tool metadata and argv templates.",
        "category": "ai",
        "schema": "cleanmac.mcp-tool-catalog.v1",
    },
    {
        "uri": "cleanmac://ai/readiness",
        "name": "cleanmac AI readiness",
        "description": "AI host readiness report with provider parity and integration status.",
        "category": "ai",
        "schema": "cleanmac.ai-readiness.v1",
    },
    {
        "uri": "cleanmac://ai/runbook",
        "name": "cleanmac AI runbook",
        "description": "Ordered safe workflow phases and execution gate for AI hosts.",
        "category": "ai",
        "schema": "cleanmac.ai-runbook.v1",
    },
    {
        "uri": RUNTIME_LIFECYCLE_POLICY_URI,
        "name": "cleanmac runtime lifecycle policy",
        "description": "First-class AI Host policy proving cleanmac is AI-first, ephemeral, and zero-resident.",
        "category": "ai",
        "schema": "cleanmac.runtime-lifecycle-policy.v1",
    },
    {
        "uri": ZERO_RESIDENT_AUDIT_URI,
        "name": "cleanmac zero-resident audit",
        "description": "Release-gateable audit proving cleanmac has no GUI, TUI, daemon, login item, or unsolicited scan surface.",
        "category": "ai",
        "schema": "cleanmac.zero-resident-audit.v1",
    },
    {
        "uri": AI_WORKFLOW_CONTRACT_URI,
        "name": "cleanmac AI workflow contract",
        "description": "Read-only cleanmac.ai-workflow.v1 contract with governed tool order, schemas, and execution gates.",
        "category": "ai",
        "schema": "cleanmac.ai-workflow.v1",
    },
    {
        "uri": AI_ENTRYPOINT_CONTRACT_URI,
        "name": "cleanmac AI entrypoint contract",
        "description": "Canonical AI Host entrypoints with output schemas, version compatibility, and fail-closed fallbacks.",
        "category": "ai",
        "schema": "cleanmac.ai-entrypoint-contract.v1",
    },
    {
        "uri": AI_SAFETY_CHAIN_URI,
        "name": "cleanmac AI safety chain",
        "description": "Machine-verifiable plan/review/dry-run/execute safety-chain contract for AI Hosts.",
        "category": "ai",
        "schema": "cleanmac.ai-safety-chain.v1",
    },
    {
        "uri": OPERATION_LOG_EXPLAINABILITY_URI,
        "name": "cleanmac operation-log explainability",
        "description": "Read-only contract for AI-replayable operation-log JSONL entries.",
        "category": "ai",
        "schema": OPERATION_LOG_EXPLAINABILITY_SCHEMA,
    },
    {
        "uri": COLD_START_BUDGET_URI,
        "name": "cleanmac cold-start budget",
        "description": "Read-only cold-start and immediate-exit budget contract for AI Host preflight.",
        "category": "ai",
        "schema": COLD_START_BUDGET_SCHEMA,
    },
    {
        "uri": NO_DISTURBANCE_URI,
        "name": "cleanmac no-disturbance standard",
        "description": "Read-only standard proving cleanmac sends no notifications, dialogs, sounds, reminders, or background prompts.",
        "category": "ai",
        "schema": NO_DISTURBANCE_SCHEMA,
    },
    {
        "uri": DEPENDENCY_GOVERNANCE_URI,
        "name": "cleanmac dependency governance",
        "description": "Read-only dependency and supply-chain governance contract for release gates.",
        "category": "release",
        "schema": DEPENDENCY_GOVERNANCE_SCHEMA,
    },
    {
        "uri": "cleanmac://ai/self-test",
        "name": "cleanmac AI self-test",
        "description": "Machine-readable AI host integration self-check report.",
        "category": "ai",
        "schema": "cleanmac.ai-self-test.v1",
    },
    {
        "uri": "cleanmac://ai/tool-decision-matrix",
        "name": "cleanmac AI tool decision matrix",
        "description": "Per-tool AI Host decision metadata, MCP annotations, phase, and recovery guidance.",
        "category": "ai",
        "schema": "cleanmac.ai-tool-decision-matrix.v1",
    },
    {
        "uri": "cleanmac://ai/governance-advice",
        "name": "cleanmac AI governance advice",
        "description": "Governance recommendations for safe large-model cleanmac tool calling.",
        "category": "ai",
        "schema": "cleanmac.ai-governance-advice.v1",
    },
    {
        "uri": "cleanmac://ai/host-policy",
        "name": "cleanmac AI host policy",
        "description": "Machine-readable allow/deny policy for AI Host cleanmac tool calling.",
        "category": "ai",
        "schema": "cleanmac.ai-host-policy.v1",
    },
    {
        "uri": "cleanmac://ai/schema-registry",
        "name": "cleanmac AI schema registry",
        "description": "Inventory of cleanmac.*.v* schemas with stability and compatibility policy.",
        "category": "ai",
        "schema": "cleanmac.ai-schema-registry.v1",
    },
    {
        "uri": "cleanmac://ai/contract-validation",
        "name": "cleanmac AI contract validation",
        "description": "Self-validation report for cleanmac AI/MCP machine-readable contracts.",
        "category": "ai",
        "schema": "cleanmac.ai-contract-validation-summary.v1",
    },
    {
        "uri": "cleanmac://ai/contract-samples",
        "name": "cleanmac AI contract samples",
        "description": "Sample payloads for critical cleanmac AI/MCP machine-readable contracts.",
        "category": "ai",
        "schema": "cleanmac.ai-contract-samples.v1",
    },
    {
        "uri": "cleanmac://ai/host-integration-pack",
        "name": "cleanmac AI host integration pack",
        "description": "One-stop AI Host integration metadata with schemas, policy, governance, eval, and samples.",
        "category": "ai",
        "schema": "cleanmac.ai-host-integration-pack.v1",
    },
    {
        "uri": "cleanmac://ai/host-preflight",
        "name": "cleanmac AI host preflight",
        "description": "Runtime preflight gate for AI Host cleanmac orchestration.",
        "category": "ai",
        "schema": "cleanmac.ai-host-preflight.v1",
    },
    {
        "uri": "cleanmac://ai/host-evidence",
        "name": "cleanmac AI host evidence",
        "description": "Auditable runtime governance evidence pack for AI Host release gates.",
        "category": "ai",
        "schema": "cleanmac.ai-host-evidence.v1",
    },
    {
        "uri": "cleanmac://release/readiness",
        "name": "cleanmac release readiness",
        "description": "Machine-readable release review bundle aggregating AI Host, contract, eval, and artifact gates.",
        "category": "release",
        "schema": "cleanmac.release-readiness.v1",
    },
    {
        "uri": "cleanmac://release/diagnostics",
        "name": "cleanmac release diagnostics",
        "description": "Structured release readiness diagnostics with blocking codes and recovery commands.",
        "category": "release",
        "schema": "cleanmac.release-diagnostics.v1",
    },
    {
        "uri": "cleanmac://release/evidence",
        "name": "cleanmac release evidence",
        "description": "Release evidence bundle tying artifacts, readiness, contracts, eval, and AI Host evidence together.",
        "category": "release",
        "schema": "cleanmac.release-evidence.v1",
    },
    {
        "uri": "cleanmac://release/operator-summary",
        "name": "cleanmac release operator summary",
        "description": "Compact release operator summary with first-fix commands and asset checklist.",
        "category": "release",
        "schema": "cleanmac.release-operator-summary.v1",
    },
    {
        "uri": "cleanmac://release/rehearsal",
        "name": "cleanmac release rehearsal",
        "description": "Dry-run release rehearsal report for promotion evidence review.",
        "category": "release",
        "schema": "cleanmac.release-rehearsal.v1",
    },
    {
        "uri": "cleanmac://release/promotion-decision",
        "name": "cleanmac release promotion decision",
        "description": "Fail-closed release promotion decision derived from rehearsal evidence.",
        "category": "release",
        "schema": "cleanmac.release-promotion-decision.v1",
    },
    {
        "uri": "cleanmac://release/rollback-plan",
        "name": "cleanmac release rollback plan",
        "description": "Manual-only release rollback plan for distribution surfaces.",
        "category": "release",
        "schema": "cleanmac.release-rollback-plan.v1",
        "manual_only": True,
    },
    {
        "uri": "cleanmac://release/post-publish-verification",
        "name": "cleanmac release post-publish verification",
        "description": "Manual-only post-publish verification plan for distribution surfaces.",
        "category": "release",
        "schema": "cleanmac.release-post-publish-verification.v1",
        "manual_only": True,
    },
    {
        "uri": "cleanmac://release/post-publish-result",
        "name": "cleanmac release post-publish result",
        "description": "Manual-only post-publish verification closure evidence for distribution surfaces.",
        "category": "release",
        "schema": "cleanmac.release-post-publish-result.v1",
        "manual_only": True,
    },
    {
        "uri": "cleanmac://release/post-publish-evidence-template",
        "name": "cleanmac release post-publish evidence template",
        "description": "Manual-only template for operator-supplied post-publish evidence input.",
        "category": "release",
        "schema": "cleanmac.release-post-publish-evidence-template.v1",
        "manual_only": True,
    },
    {
        "uri": "cleanmac://ai/eval-pack",
        "name": "cleanmac AI eval pack",
        "description": "Static AI Host integration scenarios and expected safety assertions.",
        "category": "ai",
        "schema": "cleanmac.ai-eval-pack.v1",
    },
    {
        "uri": "cleanmac://ai/eval-run-smoke",
        "name": "cleanmac AI eval smoke run",
        "description": "Safe sandbox replay result for the smoke AI Host integration scenarios.",
        "category": "ai",
        "schema": "cleanmac.ai-eval-run.v1",
    },
)


def _with_safety_defaults(row: dict[str, Any]) -> dict[str, Any]:
    return {
        **row,
        "mimeType": row.get("mimeType", "application/json"),
        "destructive": False,
        "dry_run": True,
        "manual_only": bool(row.get("manual_only", False)),
        "safe_for_mcp": True,
        "sensitive_data_policy": MCP_RESOURCE_SENSITIVE_DATA_POLICY,
    }


def mcp_resource_catalog() -> list[dict[str, Any]]:
    """Return deterministic MCP resource metadata with safety defaults."""

    return [_with_safety_defaults(dict(row)) for row in _RESOURCE_ROWS]


def mcp_resource_uris() -> list[str]:
    return [row["uri"] for row in mcp_resource_catalog()]


def mcp_resource_schema_by_uri() -> dict[str, str]:
    return {row["uri"]: row["schema"] for row in mcp_resource_catalog()}


def validate_mcp_resource_catalog() -> dict[str, Any]:
    resources = mcp_resource_catalog()
    seen: set[str] = set()
    duplicate_uris = []
    invalid_resources = []
    for resource in resources:
        uri = str(resource.get("uri", ""))
        if uri in seen:
            duplicate_uris.append(uri)
        seen.add(uri)
        missing = [key for key in ("uri", "name", "description", "mimeType", "schema") if not resource.get(key)]
        if missing or resource.get("destructive") is not False or resource.get("safe_for_mcp") is not True:
            invalid_resources.append({"uri": uri, "missing": missing})
    return {
        "valid": not duplicate_uris and not invalid_resources,
        "resource_count": len(resources),
        "duplicate_uris": duplicate_uris,
        "invalid_resources": invalid_resources,
    }


def render_mcp_resource_index() -> dict[str, Any]:
    resources = mcp_resource_catalog()
    validation = validate_mcp_resource_catalog()
    return {
        "schema": MCP_RESOURCE_INDEX_SCHEMA,
        "destructive": False,
        "dry_run": True,
        "ready": validation["valid"],
        "resource_count": len(resources),
        "resources": resources,
        "resource_uris": [resource["uri"] for resource in resources],
        "validation": validation,
        "sensitive_data_policy": MCP_RESOURCE_SENSITIVE_DATA_POLICY,
        "recommended_commands": [
            ["make", "mcp-smoke"],
            ["make", "mcp-resource-index-smoke"],
            ["make", "ai-host-smoke"],
        ],
    }


def validate_mcp_meta_index() -> dict[str, Any]:
    from cleancli.mcp_prompts import validate_mcp_prompt_catalog
    from cleancli.mcp_tools import validate_mcp_tool_catalog

    resource_validation = validate_mcp_resource_catalog()
    prompt_validation = validate_mcp_prompt_catalog()
    tool_validation = validate_mcp_tool_catalog()
    index_uris = [
        MCP_RESOURCE_INDEX_URI,
        MCP_PROMPT_INDEX_URI,
        MCP_TOOL_INDEX_URI,
        MCP_DESTRUCTIVE_TOOL_GOVERNANCE_URI,
    ]
    resource_uris = set(mcp_resource_uris())
    missing_index_uris = [uri for uri in index_uris if uri not in resource_uris]
    return {
        "valid": bool(
            resource_validation.get("valid")
            and prompt_validation.get("valid")
            and tool_validation.get("valid")
            and not missing_index_uris
        ),
        "index_count": len(index_uris),
        "missing_index_uris": missing_index_uris,
        "resource_catalog": resource_validation,
        "prompt_catalog": prompt_validation,
        "tool_catalog": tool_validation,
    }


def render_mcp_meta_index() -> dict[str, Any]:
    validation = validate_mcp_meta_index()
    index_rows = [
        {
            "kind": "resource",
            "uri": MCP_RESOURCE_INDEX_URI,
            "schema": MCP_RESOURCE_INDEX_SCHEMA,
            "ready": bool(validation["resource_catalog"].get("valid")),
            "count": validation["resource_catalog"].get("resource_count", 0),
        },
        {
            "kind": "prompt",
            "uri": MCP_PROMPT_INDEX_URI,
            "schema": MCP_PROMPT_INDEX_SCHEMA,
            "ready": bool(validation["prompt_catalog"].get("valid")),
            "count": validation["prompt_catalog"].get("prompt_count", 0),
        },
        {
            "kind": "tool",
            "uri": MCP_TOOL_INDEX_URI,
            "schema": MCP_TOOL_INDEX_SCHEMA,
            "ready": bool(validation["tool_catalog"].get("valid")),
            "count": validation["tool_catalog"].get("tool_count", 0),
        },
        {
            "kind": "destructive-tool-governance",
            "uri": MCP_DESTRUCTIVE_TOOL_GOVERNANCE_URI,
            "schema": MCP_DESTRUCTIVE_TOOL_GOVERNANCE_SCHEMA,
            "ready": bool(validation["tool_catalog"].get("valid")),
            "count": len(validation["tool_catalog"].get("destructive_tool_names", [])),
        },
    ]
    return {
        "schema": MCP_META_INDEX_SCHEMA,
        "destructive": False,
        "dry_run": True,
        "ready": validation["valid"],
        "index_count": len(index_rows),
        "indexes": index_rows,
        "index_uris": [row["uri"] for row in index_rows],
        "validation": validation,
        "sensitive_data_policy": MCP_RESOURCE_SENSITIVE_DATA_POLICY,
        "recommended_call_sequence": [
            f"read {MCP_META_INDEX_URI}",
            f"read {MCP_RESOURCE_INDEX_URI}",
            f"read {MCP_PROMPT_INDEX_URI}",
            f"read {MCP_TOOL_INDEX_URI}",
            f"read {MCP_DESTRUCTIVE_TOOL_GOVERNANCE_URI}",
        ],
        "recommended_commands": [["make", "mcp-smoke"], ["make", "mcp-meta-index-smoke"], ["make", "ai-host-smoke"]],
    }


def render_mcp_surface_audit() -> dict[str, Any]:
    """Return a compact pass/fail audit of the complete MCP discovery surface."""

    meta_index = render_mcp_meta_index()
    resource_index = render_mcp_resource_index()
    from cleancli.mcp_prompts import render_mcp_prompt_index
    from cleancli.mcp_tools import render_mcp_tool_index

    prompt_index = render_mcp_prompt_index()
    tool_index = render_mcp_tool_index()
    resources = resource_index.get("resources", [])
    prompts = prompt_index.get("prompts", [])
    tools = tool_index.get("tools", [])
    resource_uris = set(resource_index.get("resource_uris", []))
    prompt_names = set(prompt_index.get("prompt_names", []))
    tool_names = set(tool_index.get("tool_names", []))
    required_resources = {
        MCP_META_INDEX_URI,
        MCP_RESOURCE_INDEX_URI,
        MCP_PROMPT_INDEX_URI,
        MCP_TOOL_INDEX_URI,
        MCP_DESTRUCTIVE_TOOL_GOVERNANCE_URI,
        MCP_SURFACE_AUDIT_URI,
        RUNTIME_LIFECYCLE_POLICY_URI,
        ZERO_RESIDENT_AUDIT_URI,
        AI_ENTRYPOINT_CONTRACT_URI,
        AI_WORKFLOW_CONTRACT_URI,
        OPERATION_LOG_EXPLAINABILITY_URI,
        COLD_START_BUDGET_URI,
        NO_DISTURBANCE_URI,
        DEPENDENCY_GOVERNANCE_URI,
        "cleanmac://ai/host-integration-pack",
        "cleanmac://ai/host-preflight",
        "cleanmac://ai/host-evidence",
        "cleanmac://ai/host-policy",
    }
    required_prompts = {"review-ai-host-policy"}
    required_tools = {"cleanmac_capabilities", "cleanmac_execute_plan", "cleanmac_policy_simulate"}
    missing_resources = sorted(required_resources - resource_uris)
    missing_prompts = sorted(required_prompts - prompt_names)
    missing_tools = sorted(required_tools - tool_names)
    remediation_by_check = {
        "mcp-meta-index-ready": [["make", "mcp-meta-index-smoke"], ["make", "mcp-smoke"]],
        "mcp-resource-index-ready": [["make", "mcp-resource-index-smoke"], ["make", "mcp-smoke"]],
        "mcp-prompt-index-ready": [["make", "mcp-prompt-index-smoke"], ["make", "mcp-smoke"]],
        "mcp-tool-index-ready": [["make", "mcp-tool-index-smoke"], ["make", "mcp-smoke"]],
        "mcp-destructive-tool-governance-ready": [
            ["cleanmac", "--json", "mcp-destructive-tool-governance"],
            ["make", "mcp-tool-index-smoke"],
        ],
        "required-resources-advertised": [
            ["cleanmac", "--json", "mcp-surface-audit"],
            ["make", "mcp-resource-index-smoke"],
        ],
        "required-prompts-advertised": [
            ["cleanmac", "--json", "mcp-surface-audit"],
            ["make", "mcp-prompt-index-smoke"],
        ],
        "required-tools-advertised": [["cleanmac", "--json", "mcp-surface-audit"], ["make", "mcp-tool-index-smoke"]],
        "runtime-lifecycle-policy-advertised": [
            ["cleanmac", "--json", "mcp-surface-audit"],
            ["make", "mcp-resource-index-smoke"],
        ],
        "zero-resident-audit-advertised": [
            ["cleanmac", "--json", "mcp-surface-audit"],
            ["make", "zero-resident-audit-smoke"],
        ],
        "operation-log-explainability-advertised": [
            ["cleanmac", "--json", "operation-log-explainability"],
            ["python3", "-m", "pytest", "tests/test_operation_log.py", "-q"],
        ],
        "cold-start-budget-advertised": [
            ["cleanmac", "--json", "cold-start-budget"],
            ["make", "ai-host-smoke"],
        ],
        "no-disturbance-advertised": [
            ["cleanmac", "--json", "no-disturbance"],
            ["make", "no-disturbance-smoke"],
        ],
        "dependency-governance-advertised": [
            ["cleanmac", "--json", "dependency-governance"],
            ["make", "dependency-audit-smoke"],
        ],
        "all-resources-mcp-safe": [["make", "mcp-resource-index-smoke"], ["make", "ai-host-smoke"]],
        "all-prompts-mcp-safe": [["make", "mcp-prompt-index-smoke"], ["make", "ai-host-smoke"]],
        "all-tools-mcp-safe": [["make", "mcp-tool-index-smoke"], ["make", "ai-host-smoke"]],
        "destructive-tools-gated": [["make", "mcp-tool-index-smoke"], ["make", "ai-governance-smoke"]],
        "no-shell-invocation": [["make", "mcp-tool-index-smoke"], ["make", "ai-host-smoke"]],
        "sensitive-data-policy-present": [["make", "mcp-resource-index-smoke"], ["make", "mcp-surface-audit-smoke"]],
    }
    checks = [
        {"id": "mcp-meta-index-ready", "passed": bool(meta_index.get("ready")), "evidence": MCP_META_INDEX_SCHEMA},
        {
            "id": "mcp-resource-index-ready",
            "passed": bool(resource_index.get("ready")),
            "evidence": MCP_RESOURCE_INDEX_SCHEMA,
        },
        {
            "id": "mcp-prompt-index-ready",
            "passed": bool(prompt_index.get("ready")),
            "evidence": MCP_PROMPT_INDEX_SCHEMA,
        },
        {
            "id": "mcp-tool-index-ready",
            "passed": bool(tool_index.get("ready")),
            "evidence": MCP_TOOL_INDEX_SCHEMA,
        },
        {
            "id": "mcp-destructive-tool-governance-ready",
            "passed": MCP_DESTRUCTIVE_TOOL_GOVERNANCE_URI in resource_uris,
            "evidence": MCP_DESTRUCTIVE_TOOL_GOVERNANCE_URI,
        },
        {
            "id": "required-resources-advertised",
            "passed": not missing_resources,
            "evidence": MCP_RESOURCE_INDEX_SCHEMA,
        },
        {
            "id": "required-prompts-advertised",
            "passed": not missing_prompts,
            "evidence": MCP_PROMPT_INDEX_SCHEMA,
        },
        {"id": "required-tools-advertised", "passed": not missing_tools, "evidence": MCP_TOOL_INDEX_SCHEMA},
        {
            "id": "runtime-lifecycle-policy-advertised",
            "passed": RUNTIME_LIFECYCLE_POLICY_URI in resource_uris,
            "evidence": RUNTIME_LIFECYCLE_POLICY_URI,
        },
        {
            "id": "zero-resident-audit-advertised",
            "passed": ZERO_RESIDENT_AUDIT_URI in resource_uris,
            "evidence": ZERO_RESIDENT_AUDIT_URI,
        },
        {
            "id": "operation-log-explainability-advertised",
            "passed": OPERATION_LOG_EXPLAINABILITY_URI in resource_uris,
            "evidence": OPERATION_LOG_EXPLAINABILITY_URI,
        },
        {
            "id": "cold-start-budget-advertised",
            "passed": COLD_START_BUDGET_URI in resource_uris,
            "evidence": COLD_START_BUDGET_URI,
        },
        {
            "id": "no-disturbance-advertised",
            "passed": NO_DISTURBANCE_URI in resource_uris,
            "evidence": NO_DISTURBANCE_URI,
        },
        {
            "id": "dependency-governance-advertised",
            "passed": DEPENDENCY_GOVERNANCE_URI in resource_uris,
            "evidence": DEPENDENCY_GOVERNANCE_URI,
        },
        {
            "id": "all-resources-mcp-safe",
            "passed": all(row.get("safe_for_mcp") is True and row.get("destructive") is False for row in resources),
            "evidence": MCP_RESOURCE_INDEX_SCHEMA,
        },
        {
            "id": "all-prompts-mcp-safe",
            "passed": all(row.get("safe_for_mcp") is True and row.get("destructive") is False for row in prompts),
            "evidence": MCP_PROMPT_INDEX_SCHEMA,
        },
        {
            "id": "all-tools-mcp-safe",
            "passed": all(row.get("safe_for_mcp") is True for row in tools),
            "evidence": MCP_TOOL_INDEX_SCHEMA,
        },
        {
            "id": "destructive-tools-gated",
            "passed": all(
                (not row.get("destructive"))
                or (row.get("auto_call_allowed") is False and row.get("requires_confirmation") is True)
                for row in tools
            ),
            "evidence": MCP_TOOL_INDEX_SCHEMA,
        },
        {
            "id": "no-shell-invocation",
            "passed": all(row.get("uses_shell") is False and row.get("invocation_mode") == "argv" for row in tools),
            "evidence": MCP_TOOL_INDEX_SCHEMA,
        },
        {
            "id": "sensitive-data-policy-present",
            "passed": all(row.get("sensitive_data_policy") == MCP_RESOURCE_SENSITIVE_DATA_POLICY for row in resources),
            "evidence": MCP_RESOURCE_SENSITIVE_DATA_POLICY,
        },
    ]
    for check in checks:
        check["remediation_commands"] = remediation_by_check[str(check["id"])]
    passed_count = sum(1 for check in checks if check["passed"])
    failed_check_ids = [str(check["id"]) for check in checks if not check["passed"]]
    ready = not failed_check_ids
    return {
        "schema": MCP_SURFACE_AUDIT_SCHEMA,
        "destructive": False,
        "dry_run": True,
        "ready": ready,
        "resource_uri": MCP_SURFACE_AUDIT_URI,
        "checks": checks,
        "failed_check_ids": failed_check_ids,
        "readiness_score": {
            "passed": passed_count,
            "total": len(checks),
            "level": "ready" if ready else "blocked",
        },
        "next_action": "proceed-to-host-integration-pack" if ready else "stop-and-remediate-mcp-surface",
        "stop_reason": "" if ready else "mcp-surface-audit failed: " + ", ".join(failed_check_ids),
        "missing": {
            "resources": missing_resources,
            "prompts": missing_prompts,
            "tools": missing_tools,
        },
        "counts": {
            "resources": resource_index.get("resource_count", 0),
            "prompts": prompt_index.get("prompt_count", 0),
            "tools": tool_index.get("tool_count", 0),
        },
        "index_uris": [MCP_META_INDEX_URI, MCP_RESOURCE_INDEX_URI, MCP_PROMPT_INDEX_URI, MCP_TOOL_INDEX_URI],
        "recommended_call_sequence": [
            f"read {MCP_META_INDEX_URI}",
            f"read {MCP_RESOURCE_INDEX_URI}",
            f"read {MCP_PROMPT_INDEX_URI}",
            f"read {MCP_TOOL_INDEX_URI}",
            f"read {MCP_DESTRUCTIVE_TOOL_GOVERNANCE_URI}",
            f"read {OPERATION_LOG_EXPLAINABILITY_URI}",
            f"read {COLD_START_BUDGET_URI}",
            f"read {NO_DISTURBANCE_URI}",
            f"read {DEPENDENCY_GOVERNANCE_URI}",
            f"read {MCP_SURFACE_AUDIT_URI}",
            "read cleanmac://ai/host-integration-pack",
        ],
        "release_gate_commands": [
            ["cleanmac", "--json", "mcp-surface-audit"],
            ["make", "mcp-surface-audit-smoke"],
            ["make", "mcp-smoke"],
            ["make", "ai-host-smoke"],
            ["make", "ai-governance-smoke"],
        ],
        "remediation_commands": [
            ["make", "mcp-surface-audit-smoke"],
            ["make", "mcp-smoke"],
            ["make", "ai-host-smoke"],
        ],
        "sensitive_data_policy": MCP_RESOURCE_SENSITIVE_DATA_POLICY,
    }
