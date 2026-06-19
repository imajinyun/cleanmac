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
    ("cleanmac.ai-contract-validation.v1", 1, "cleancli.ai_versioning", "stable"),
    ("cleanmac.ai-contract-validation-summary.v1", 1, "cleancli.ai_versioning", "stable"),
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

AI_HOST_CRITICAL_SCHEMAS: tuple[str, ...] = (
    "cleanmac.plan.v1",
    "cleanmac.validate-plan.v1",
    "cleanmac.ai-policy-simulation.v1",
    "cleanmac.ai-schema-registry.v1",
    "cleanmac.ai-readiness.v1",
    "cleanmac.ai-host-policy.v1",
    "cleanmac.ai-governance-advice.v1",
    "cleanmac.ai-eval-pack.v1",
    "cleanmac.ai-eval-run.v1",
    "cleanmac.ai-contract-validation.v1",
    "cleanmac.ai-contract-validation-summary.v1",
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
            "candidate_fingerprints": {"type": "array", "items": {"type": "object"}},
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
    "cleanmac.ai-host-policy.v1": {
        "type": "object",
        "required": ["schema", "valid", "default_decision", "auto_call", "execution_gate"],
        "properties": {
            "schema": {"const": "cleanmac.ai-host-policy.v1"},
            "valid": {"type": "boolean"},
            "default_decision": {"const": "deny"},
            "auto_call": {"type": "object"},
            "execution_gate": {"type": "object"},
        },
        "additionalProperties": True,
    },
    "cleanmac.ai-governance-advice.v1": {
        "type": "object",
        "required": [
            "schema",
            "ready_for_llm_calling",
            "governance_score",
            "default_policy",
            "required_host_controls",
            "recommended_call_sequence",
            "anti_patterns",
            "governance_route",
            "release_gate_commands",
            "recommendations",
        ],
        "properties": {
            "schema": {"const": "cleanmac.ai-governance-advice.v1"},
            "ready_for_llm_calling": {"type": "boolean"},
            "governance_score": {"type": "object"},
            "default_policy": {"type": "object"},
            "required_host_controls": {"type": "array", "items": {"type": "string"}},
            "recommended_call_sequence": {"type": "array", "items": {"type": "string"}},
            "anti_patterns": {"type": "array", "items": {"type": "string"}},
            "governance_route": {"type": "array", "items": {"type": "object"}},
            "release_gate_commands": {"type": "array", "items": {"type": "array"}},
            "recommendations": {"type": "array", "items": {"type": "object"}},
        },
        "additionalProperties": True,
    },
    "cleanmac.ai-eval-pack.v1": {
        "type": "object",
        "required": [
            "schema",
            "scenario_count",
            "scenarios",
            "allows_destructive_execution",
            "recommended_runner_command",
        ],
        "properties": {
            "schema": {"const": "cleanmac.ai-eval-pack.v1"},
            "scenario_count": {"type": "integer"},
            "scenarios": {"type": "array", "items": {"type": "object"}},
            "allows_destructive_execution": {"const": False},
            "recommended_runner_command": {"type": "array", "items": {"type": "string"}},
        },
        "additionalProperties": True,
    },
    "cleanmac.ai-eval-run.v1": {
        "type": "object",
        "required": ["schema", "scenario", "passed", "passed_count", "failed_count", "results"],
        "properties": {
            "schema": {"const": "cleanmac.ai-eval-run.v1"},
            "scenario": {"type": "string"},
            "passed": {"type": "boolean"},
            "passed_count": {"type": "integer"},
            "failed_count": {"type": "integer"},
            "results": {"type": "array", "items": {"type": "object"}},
        },
        "additionalProperties": True,
    },
    "cleanmac.ai-contract-validation.v1": {
        "type": "object",
        "required": ["schema", "destructive", "dry_run", "valid", "target_schema", "error_count", "errors"],
        "properties": {
            "schema": {"const": "cleanmac.ai-contract-validation.v1"},
            "destructive": {"const": False},
            "dry_run": {"const": True},
            "valid": {"type": "boolean"},
            "target_schema": {"type": "string"},
            "error_count": {"type": "integer"},
            "errors": {"type": "array", "items": {"type": "object"}},
        },
        "additionalProperties": True,
    },
    "cleanmac.ai-contract-validation-summary.v1": {
        "type": "object",
        "required": [
            "schema",
            "destructive",
            "dry_run",
            "valid",
            "validated_schema_count",
            "failure_count",
            "results",
        ],
        "properties": {
            "schema": {"const": "cleanmac.ai-contract-validation-summary.v1"},
            "destructive": {"const": False},
            "dry_run": {"const": True},
            "valid": {"type": "boolean"},
            "validated_schema_count": {"type": "integer"},
            "failure_count": {"type": "integer"},
            "results": {"type": "array", "items": {"type": "object"}},
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
        "cleanmac.ai-contract-validation.v1": "ai-validate-contract",
        "cleanmac.ai-contract-validation-summary.v1": "ai contract validation summary",
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
    if name in {"cleanmac.ai-contract-validation.v1", "cleanmac.ai-contract-validation-summary.v1"}:
        return ("ai-self-test", "ai-readiness", "mcp")
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


def _contract_type_matches(expected_type: str, value: Any) -> bool:
    if expected_type == "object":
        return isinstance(value, dict)
    if expected_type == "array":
        return isinstance(value, list)
    if expected_type == "string":
        return isinstance(value, str)
    if expected_type == "boolean":
        return isinstance(value, bool)
    if expected_type == "integer":
        return isinstance(value, int) and not isinstance(value, bool)
    if expected_type == "number":
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    return True


def _validate_schema_fragment(schema_fragment: dict[str, Any], value: Any, path: str) -> list[dict[str, str]]:
    errors: list[dict[str, str]] = []
    expected_const = schema_fragment.get("const")
    if "const" in schema_fragment and value != expected_const:
        errors.append(
            {
                "code": "CONST_MISMATCH",
                "path": path,
                "message": f"Expected const {expected_const!r} at {path}.",
            }
        )
        return errors
    expected_type = schema_fragment.get("type")
    if isinstance(expected_type, str) and not _contract_type_matches(expected_type, value):
        errors.append(
            {
                "code": "TYPE_MISMATCH",
                "path": path,
                "message": f"Expected type {expected_type} at {path}.",
            }
        )
        return errors
    if expected_type == "object" and isinstance(value, dict):
        required = schema_fragment.get("required", [])
        if isinstance(required, list):
            for field in required:
                if isinstance(field, str) and field not in value:
                    field_path = f"{path}.{field}" if path != "$" else f"$.{field}"
                    errors.append(
                        {
                            "code": "MISSING_REQUIRED_FIELD",
                            "path": field_path,
                            "message": f"Missing required field {field!r}.",
                        }
                    )
        properties = schema_fragment.get("properties", {})
        if isinstance(properties, dict):
            for field, property_schema in properties.items():
                if field in value and isinstance(property_schema, dict):
                    field_path = f"{path}.{field}" if path != "$" else f"$.{field}"
                    errors.extend(_validate_schema_fragment(property_schema, value[field], field_path))
    if expected_type == "array" and isinstance(value, list):
        item_schema = schema_fragment.get("items")
        if isinstance(item_schema, dict):
            for index, item in enumerate(value):
                errors.extend(_validate_schema_fragment(item_schema, item, f"{path}[{index}]"))
    return errors


def validate_contract_payload(schema_name: str, payload: Any) -> dict[str, Any]:
    schema_fragment = CORE_CONTRACT_SCHEMAS.get(schema_name)
    if schema_fragment is None:
        errors = [
            {
                "code": "UNSUPPORTED_SCHEMA",
                "path": "$",
                "message": f"Unsupported schema: {schema_name}",
            }
        ]
    else:
        errors = _validate_schema_fragment(schema_fragment, payload, "$.")
    return {
        "schema": "cleanmac.ai-contract-validation.v1",
        "destructive": False,
        "dry_run": True,
        "valid": not errors,
        "target_schema": schema_name,
        "error_count": len(errors),
        "errors": errors,
    }


def render_ai_contract_validation_summary() -> dict[str, Any]:
    schema_registry_validation = validate_contract_payload(
        "cleanmac.ai-schema-registry.v1",
        render_ai_schema_registry(),
    )
    result_by_schema = {schema_registry_validation["target_schema"]: schema_registry_validation}
    missing_schema_fragments = [
        schema_name for schema_name in AI_HOST_CRITICAL_SCHEMAS if schema_name not in CORE_CONTRACT_SCHEMAS
    ]
    registry = render_ai_schema_registry()
    stable_ai_schemas = [
        entry["name"]
        for entry in registry["entries"]
        if entry["stability"] == "stable"
        and (entry["kind"] == "ai-output" or str(entry["name"]).startswith("cleanmac.mcp-"))
    ]
    stable_ai_schema_fragments = [
        schema_name for schema_name in stable_ai_schemas if schema_name in CORE_CONTRACT_SCHEMAS
    ]
    coverage_result = {
        "schema": "cleanmac.ai-contract-validation.v1",
        "destructive": False,
        "dry_run": True,
        "valid": not missing_schema_fragments,
        "target_schema": "core-contract-schema-coverage",
        "error_count": len(missing_schema_fragments),
        "errors": [
            {
                "code": "MISSING_JSON_SCHEMA_FRAGMENT",
                "path": "$.entries",
                "message": f"Missing JSON Schema fragment for {schema_name}.",
            }
            for schema_name in missing_schema_fragments
        ],
    }
    result_by_schema[coverage_result["target_schema"]] = coverage_result
    results = list(result_by_schema.values())
    failure_count = sum(1 for result in results if not result["valid"])
    return {
        "schema": "cleanmac.ai-contract-validation-summary.v1",
        "destructive": False,
        "dry_run": True,
        "valid": failure_count == 0,
        "validated_schema_count": len(results),
        "failure_count": failure_count,
        "contract_schema_coverage": {
            "registered_schema_count": registry["entry_count"],
            "json_schema_fragment_count": len(CORE_CONTRACT_SCHEMAS),
            "critical_schemas": list(AI_HOST_CRITICAL_SCHEMAS),
            "critical_schema_count": len(AI_HOST_CRITICAL_SCHEMAS),
            "stable_ai_schema_count": len(stable_ai_schemas),
            "stable_ai_schema_fragment_count": len(stable_ai_schema_fragments),
            "missing_stable_ai_schema_fragments": missing_schema_fragments,
        },
        "results": results,
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
                "legacy": True,
            }
        return {
            "accepted": False,
            "schema": "",
            "reason": "missing-schema-field",
            "latest_supported_schema": LATEST_PLAN_SCHEMA,
            "legacy": False,
        }
    if schema in SUPPORTED_PLAN_SCHEMAS:
        return {
            "accepted": True,
            "schema": schema,
            "reason": "supported",
            "latest_supported_schema": LATEST_PLAN_SCHEMA,
            "legacy": schema != LATEST_PLAN_SCHEMA,
        }
    return {
        "accepted": False,
        "schema": schema,
        "reason": "unsupported-schema-version",
        "latest_supported_schema": LATEST_PLAN_SCHEMA,
        "legacy": False,
    }
