"""Central MCP resource catalog and safety metadata for cleanmac AI hosts."""

from __future__ import annotations

from typing import Any

from cleancli.mcp_prompts import MCP_PROMPT_INDEX_SCHEMA, MCP_PROMPT_INDEX_URI

MCP_RESOURCE_INDEX_SCHEMA = "cleanmac.mcp-resource-index.v1"
MCP_RESOURCE_INDEX_URI = "cleanmac://mcp/resource-index"
MCP_RESOURCE_SENSITIVE_DATA_POLICY = "redacted-local-paths-no-credentials"


_RESOURCE_ROWS: tuple[dict[str, Any], ...] = (
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
        "recommended_commands": [["make", "mcp-smoke"], ["make", "ai-host-smoke"]],
    }
