"""AI schema registry: single source of truth for cleanmac.*.v* schemas.

This module centralizes every machine-readable schema name that cleanmac emits
for AI hosts, so a drift guard test can fail when a new ``cleanmac.*.v1`` schema
is introduced without registering it here. It also exposes a small plan schema
negotiation helper so callers can give structured, explainable refusals instead
of crashing on unknown plan schema versions.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class SchemaEntry:
    name: str
    version: int
    module: str
    stability: str
    kind: str
    producer: str
    consumers: tuple[str, ...]
    latest: bool
    deprecated: bool = False
    replaced_by: str | None = None


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
    ("cleanmac.clean-plan.v1", 1, "cleancli.core", "stable"),
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

LATEST_PLAN_SCHEMA = "cleanmac.plan.v1"
SUPPORTED_PLAN_SCHEMAS: tuple[str, ...] = (
    LATEST_PLAN_SCHEMA,
    "cleanmac.clean.v1",
    "cleanmac.clean-plan.v1",
)

CORE_CONTRACT_SCHEMAS: dict[str, dict[str, Any]] = {
    "cleanmac.plan.v1": {
        "type": "object",
        "required": [
            "schema",
            "destructive",
            "dry_run",
            "generated_at",
            "expires_at",
            "selected_category_keys",
            "candidate_fingerprints",
        ],
        "properties": {
            "schema": {"const": "cleanmac.plan.v1"},
            "destructive": {"const": False},
            "dry_run": {"const": True},
            "generated_at": {"type": "string"},
            "expires_at": {"type": "string"},
            "selected_category_keys": {"type": "array", "items": {"type": "string"}},
            "candidate_fingerprints": {"type": "array", "items": {"type": "string"}},
        },
        "additionalProperties": True,
    },
    "cleanmac.validate-plan.v1": {
        "type": "object",
        "required": ["schema", "destructive", "dry_run", "valid", "plan", "schema_negotiation"],
        "properties": {
            "schema": {"const": "cleanmac.validate-plan.v1"},
            "destructive": {"const": False},
            "dry_run": {"const": True},
            "valid": {"type": "boolean"},
            "plan": {"type": "object"},
            "schema_negotiation": {"type": "object"},
        },
        "additionalProperties": True,
    },
    "cleanmac.ai-policy-simulation.v1": {
        "type": "object",
        "required": ["schema", "destructive", "dry_run", "allowed", "blocking_reasons"],
        "properties": {
            "schema": {"const": "cleanmac.ai-policy-simulation.v1"},
            "destructive": {"const": False},
            "dry_run": {"const": True},
            "allowed": {"type": "boolean"},
            "blocking_reasons": {"type": "array", "items": {"type": "object"}},
        },
        "additionalProperties": True,
    },
    "cleanmac.ai-schema-registry.v1": {
        "type": "object",
        "required": [
            "schema",
            "entry_count",
            "stable_schema_count",
            "deprecated_schema_count",
            "latest_plan_schema",
            "supported_plan_schemas",
            "entries",
            "compatibility_policy",
        ],
        "properties": {
            "schema": {"const": "cleanmac.ai-schema-registry.v1"},
            "entry_count": {"type": "integer"},
            "stable_schema_count": {"type": "integer"},
            "deprecated_schema_count": {"type": "integer"},
            "latest_plan_schema": {"const": LATEST_PLAN_SCHEMA},
            "supported_plan_schemas": {"type": "array", "items": {"type": "string"}},
            "entries": {"type": "array", "items": {"type": "object"}},
            "compatibility_policy": {"type": "object"},
        },
        "additionalProperties": True,
    },
    "cleanmac.ai-readiness.v1": {
        "type": "object",
        "required": ["schema", "ready", "tool_count", "contracts", "schema_registry"],
        "properties": {
            "schema": {"const": "cleanmac.ai-readiness.v1"},
            "ready": {"type": "boolean"},
            "tool_count": {"type": "integer"},
            "contracts": {"type": "object"},
            "schema_registry": {"type": "object"},
        },
        "additionalProperties": True,
    },
}


def _schema_kind(name: str) -> str:
    if name.startswith("cleanmac.mcp-"):
        return "mcp-output"
    if ".ai-" in name:
        return "ai-output"
    return "cli-output"


def _schema_producer(name: str) -> str:
    producer_by_name = {
        "cleanmac.plan.v1": "clean plan",
        "cleanmac.validate-plan.v1": "validate-plan",
        "cleanmac.ai-policy-simulation.v1": "policy-simulate",
        "cleanmac.ai-schema-registry.v1": "ai-schema-registry",
        "cleanmac.ai-readiness.v1": "ai-readiness",
        "cleanmac.clean.v1": "clean run",
        "cleanmac.clean-plan.v1": "legacy clean plan",
    }
    if name in producer_by_name:
        return producer_by_name[name]
    stem = name.removeprefix("cleanmac.").removesuffix(".v1")
    return stem.replace(".", " ")


def _schema_consumers(name: str) -> tuple[str, ...]:
    if name in SUPPORTED_PLAN_SCHEMAS:
        return ("validate-plan", "policy-simulate", "clean run --plan-file", "mcp")
    if name == "cleanmac.ai-schema-registry.v1":
        return ("ai-readiness", "ai-self-test", "mcp")
    if name.startswith("cleanmac.ai-"):
        return ("ai-host", "mcp")
    return ("cli", "mcp")


def _schema_entry(name: str, version: int, module: str, stability: str) -> SchemaEntry:
    return SchemaEntry(
        name=name,
        version=version,
        module=module,
        stability=stability,
        kind=_schema_kind(name),
        producer=_schema_producer(name),
        consumers=_schema_consumers(name),
        latest=name not in set(SUPPORTED_PLAN_SCHEMAS) - {LATEST_PLAN_SCHEMA},
    )


def render_ai_schema_registry() -> dict[str, Any]:
    entries = []
    for row in (_schema_entry(name, version, module, stability) for (name, version, module, stability) in _REGISTRY):
        entry: dict[str, Any] = {
            "name": row.name,
            "version": row.version,
            "module": row.module,
            "stability": row.stability,
            "kind": row.kind,
            "producer": row.producer,
            "consumers": list(row.consumers),
            "latest": row.latest,
            "deprecated": row.deprecated,
            "replaced_by": row.replaced_by,
            "compatibility": {
                "breaking_change_policy": "new-major-schema-required",
                "unknown_fields": "allowed",
                "missing_required_fields": "invalid",
            },
        }
        if row.name in CORE_CONTRACT_SCHEMAS:
            entry["json_schema"] = CORE_CONTRACT_SCHEMAS[row.name]
        entries.append(entry)
    return {
        "schema": "cleanmac.ai-schema-registry.v1",
        "entry_count": len(entries),
        "stable_schema_count": sum(1 for entry in entries if entry["stability"] == "stable"),
        "deprecated_schema_count": sum(1 for entry in entries if entry["deprecated"]),
        "latest_plan_schema": LATEST_PLAN_SCHEMA,
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


def negotiate_plan_schema(plan: dict[str, Any], *, allow_legacy_missing: bool = False) -> dict[str, Any]:
    """Return {accepted, schema, reason} for a plan dict's schema field."""
    schema = str(plan.get("schema") or "")
    if not schema:
        if allow_legacy_missing:
            return {
                "accepted": True,
                "schema": "",
                "reason": "legacy-missing-schema-field",
                "latest_supported_schema": LATEST_PLAN_SCHEMA,
            }
        return {"accepted": False, "schema": "", "reason": "missing-schema-field"}
    if schema in SUPPORTED_PLAN_SCHEMAS:
        return {
            "accepted": True,
            "schema": schema,
            "reason": "supported",
            "latest_supported_schema": LATEST_PLAN_SCHEMA,
        }
    return {
        "accepted": False,
        "schema": schema,
        "reason": "unsupported-schema-version",
        "latest_supported_schema": LATEST_PLAN_SCHEMA,
    }
