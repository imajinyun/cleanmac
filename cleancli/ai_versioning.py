"""AI schema registry: single source of truth for cleanmac.*.v* schemas.

This module centralizes every machine-readable schema name that cleanmac emits
for AI hosts, so a drift guard test can fail when a new ``cleanmac.*.v1`` schema
is introduced without registering it here. It also exposes a small plan schema
negotiation helper so callers can give structured, explainable refusals instead
of crashing on unknown plan schema versions.
"""

from __future__ import annotations

from typing import Any

# (name, version, module, stability)
# stability: stable | preview | internal
_REGISTRY: tuple[tuple[str, int, str, str], ...] = (
    ("cleanmac.ai-confirmation-token-context.v1", 1, "cleancli.core", "stable"),
    ("cleanmac.ai-schema-validation.v1", 1, "cleancli.ai_schema", "stable"),
    ("cleanmac.ai-contract-compatibility.v1", 1, "cleancli.ai_schema", "stable"),
    ("cleanmac.ai-function-schemas.v1", 1, "cleancli.ai_schema", "stable"),
    ("cleanmac.mcp-tool-catalog.v1", 1, "cleancli.ai_schema", "stable"),
    ("cleanmac.ai-openai-functions.v1", 1, "cleancli.ai_schema", "stable"),
    ("cleanmac.ai-anthropic-tools.v1", 1, "cleancli.ai_schema", "stable"),
    ("cleanmac.ai-provider-export-parity.v1", 1, "cleancli.ai_schema", "stable"),
    ("cleanmac.ai-readiness.v1", 1, "cleancli.ai_readiness", "stable"),
    ("cleanmac.ai-runbook.v1", 1, "cleancli.ai_runbook", "stable"),
    ("cleanmac.ai-tool-decision-matrix.v1", 1, "cleancli.ai_decision", "stable"),
    ("cleanmac.ai-governance-advice.v1", 1, "cleancli.ai_governance", "stable"),
    ("cleanmac.ai-governance-advice-validation.v1", 1, "cleancli.ai_governance", "stable"),
    ("cleanmac.ai-host-policy.v1", 1, "cleancli.ai_host_policy", "stable"),
    ("cleanmac.ai-host-policy-validation.v1", 1, "cleancli.ai_host_policy", "stable"),
    ("cleanmac.ai-eval-pack.v1", 1, "cleancli.ai_eval", "stable"),
    ("cleanmac.ai-eval-run.v1", 1, "cleancli.ai_eval", "stable"),
    ("cleanmac.ai-trace.v1", 1, "cleancli.ai_eval", "stable"),
    ("cleanmac.mcp-response.v1", 1, "cleancli.ai_eval", "internal"),
    ("cleanmac.ai-tool-contract.v1", 1, "cleancli.core", "stable"),
    ("cleanmac.ai-self-test.v1", 1, "cleancli.core", "stable"),
    ("cleanmac.ai-tools.v1", 1, "cleancli.core", "stable"),
    ("cleanmac.ai-error.v1", 1, "cleancli.core", "stable"),
    ("cleanmac.ai-summary.v1", 1, "cleancli.core", "stable"),
    ("cleanmac.ai-confirmation-summary.v1", 1, "cleancli.core", "stable"),
    ("cleanmac.ai-execution-ledger.v1", 1, "cleancli.core", "stable"),
    ("cleanmac.ai-policy-simulation.v1", 1, "cleancli.core", "stable"),
    ("cleanmac.mcp-tool-error.v1", 1, "scripts.cleanmac_mcp_server", "stable"),
    ("cleanmac.ai-schema-registry.v1", 1, "cleancli.ai_versioning", "stable"),
    ("cleanmac.analyze-tree.v1", 1, "cleancli.core", "stable"),
    ("cleanmac.analyze.v1", 1, "cleancli.core", "stable"),
    ("cleanmac.audit.v1", 1, "cleancli.core", "stable"),
    ("cleanmac.boundary-governance.v1", 1, "cleancli.core", "stable"),
    ("cleanmac.bundle-drift-audit.v1", 1, "cleancli.core", "stable"),
    ("cleanmac.capabilities.v1", 1, "cleancli.core", "stable"),
    ("cleanmac.category-list.v1", 1, "cleancli.core", "stable"),
    ("cleanmac.clean.v1", 1, "cleancli.ai_eval", "stable"),
    ("cleanmac.command-template-migration.v1", 1, "cleancli.core", "stable"),
    ("cleanmac.command-template-validation.v1", 1, "cleancli.core", "stable"),
    ("cleanmac.completion-script.v1", 1, "cleancli.core", "stable"),
    ("cleanmac.diagnose.v1", 1, "cleancli.core", "stable"),
    ("cleanmac.distribution-governance.v1", 1, "cleancli.core", "stable"),
    ("cleanmac.doctor.v1", 1, "cleancli.core", "stable"),
    ("cleanmac.inspect.v1", 1, "cleancli.core", "stable"),
    ("cleanmac.links.v1", 1, "cleancli.core", "stable"),
    ("cleanmac.llm-invocation-guide.v1", 1, "cleancli.core", "stable"),
    ("cleanmac.open.v1", 1, "cleancli.core", "stable"),
    ("cleanmac.operation-log-ai-audit.v1", 1, "cleancli.core", "stable"),
    ("cleanmac.operation-log-entry.v1", 1, "cleancli.core", "stable"),
    ("cleanmac.operation-log-status.v1", 1, "cleancli.core", "stable"),
    ("cleanmac.optimize.v1", 1, "cleancli.core", "stable"),
    ("cleanmac.plan-freshness.v1", 1, "cleancli.core", "stable"),
    ("cleanmac.plan-policy.v1", 1, "cleancli.core", "stable"),
    ("cleanmac.plan.v1", 1, "cleancli.core", "stable"),
    ("cleanmac.prompt-injection-policy.v1", 1, "cleancli.core", "stable"),
    ("cleanmac.script-groups.v1", 1, "cleancli.core", "stable"),
    ("cleanmac.scripts.v1", 1, "cleancli.core", "stable"),
    ("cleanmac.software.v1", 1, "cleancli.core", "stable"),
    ("cleanmac.status.snapshot.v1", 1, "cleancli.core", "stable"),
    ("cleanmac.validate-plan.v1", 1, "cleancli.core", "stable"),
    ("cleanmac.workflow-automation.v1", 1, "cleancli.core", "stable"),
    ("cleanmac.workflow-iteration-status.v1", 1, "cleancli.core", "stable"),
    ("cleanmac.workflow.v1", 1, "cleancli.core", "stable"),
)

SUPPORTED_PLAN_SCHEMAS: tuple[str, ...] = ("cleanmac.clean-plan.v1",)


def render_ai_schema_registry() -> dict[str, Any]:
    entries = [
        {"name": name, "version": version, "module": module, "stability": stability}
        for (name, version, module, stability) in _REGISTRY
    ]
    return {
        "schema": "cleanmac.ai-schema-registry.v1",
        "entry_count": len(entries),
        "supported_plan_schemas": list(SUPPORTED_PLAN_SCHEMAS),
        "entries": entries,
        "compatibility_policy": {
            "stable": (
                "Breaking changes require a new vN suffix; old vN must keep working until the deprecation window ends."
            ),
            "preview": "May change without a major bump while marked preview.",
            "internal": "Not part of the public AI host contract; subject to change.",
        },
    }


def negotiate_plan_schema(plan: dict[str, Any]) -> dict[str, Any]:
    """Return {accepted, schema, reason} for a plan dict's schema field."""
    schema = str(plan.get("schema") or "")
    if not schema:
        return {"accepted": False, "schema": "", "reason": "missing-schema-field"}
    if schema in SUPPORTED_PLAN_SCHEMAS:
        return {"accepted": True, "schema": schema, "reason": "supported"}
    return {"accepted": False, "schema": schema, "reason": "unsupported-schema-version"}
