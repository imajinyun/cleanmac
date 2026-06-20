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
    ("cleanmac.ai-host-tool-call-decision.v1", 1, "cleancli.ai_host_policy", "stable"),
    ("cleanmac.ai-host-integration-pack.v1", 1, "cleancli.ai_host_integration", "stable"),
    ("cleanmac.ai-host-preflight.v1", 1, "cleancli.ai_host_integration", "stable"),
    ("cleanmac.ai-host-evidence.v1", 1, "cleancli.ai_host_evidence", "stable"),
    ("cleanmac.ai-eval-pack.v1", 1, "cleancli.ai_eval", "stable"),
    ("cleanmac.ai-eval-run.v1", 1, "cleancli.ai_eval", "stable"),
    ("cleanmac.ai-trace.v1", 1, "cleancli.ai_eval", "stable"),
    ("cleanmac.ai-contract-validation.v1", 1, "cleancli.ai_versioning", "stable"),
    ("cleanmac.ai-contract-validation-summary.v1", 1, "cleancli.ai_versioning", "stable"),
    ("cleanmac.ai-contract-samples.v1", 1, "cleancli.ai_versioning", "stable"),
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
    ("cleanmac.operation-log-review-selection.v1", 1, "cleancli.core", "stable"),
    ("cleanmac.operation-log-status.v1", 1, "cleancli.core", "stable"),
    ("cleanmac.optimize.v1", 1, "cleancli.core", "stable"),
    ("cleanmac.permissions-preflight.v1", 1, "cleancli.core", "stable"),
    ("cleanmac.plan-freshness.v1", 1, "cleancli.core", "stable"),
    ("cleanmac.plan-policy.v1", 1, "cleancli.core", "stable"),
    ("cleanmac.plan.v1", 1, "cleancli.core", "stable"),
    ("cleanmac.prompt-injection-policy.v1", 1, "cleancli.core", "stable"),
    ("cleanmac.release-artifact-manifest.v1", 1, "cleancli.release_artifacts", "stable"),
    ("cleanmac.review-selection-constraint.v1", 1, "cleancli.core", "stable"),
    ("cleanmac.review-selection-validation.v1", 1, "cleancli.review", "stable"),
    ("cleanmac.review-selection-summary.v1", 1, "cleancli.review", "stable"),
    ("cleanmac.review-selection.v1", 1, "cleancli.review", "stable"),
    ("cleanmac.review.v1", 1, "cleancli.review", "stable"),
    ("cleanmac.script-groups.v1", 1, "cleancli.core", "stable"),
    ("cleanmac.scripts.v1", 1, "cleancli.core", "stable"),
    ("cleanmac.software-inspect.v1", 1, "cleancli.software_uninstall", "stable"),
    ("cleanmac.software-uninstall-plan.v1", 1, "cleancli.software_uninstall", "stable"),
    ("cleanmac.software.v1", 1, "cleancli.core", "stable"),
    ("cleanmac.startup-audit.v1", 1, "cleancli.startup", "stable"),
    ("cleanmac.startup-disable-result.v1", 1, "cleancli.startup", "stable"),
    ("cleanmac.startup-plan.v1", 1, "cleancli.startup", "stable"),
    ("cleanmac.status.snapshot.v1", 1, "cleancli.core", "stable"),
    ("cleanmac.tool-execution-result.v1", 1, "cleancli.tool_adapters", "stable"),
    ("cleanmac.tool-plan.v1", 1, "cleancli.core", "stable"),
    ("cleanmac.privacy-execute-result.v1", 1, "cleancli.privacy", "stable"),
    ("cleanmac.privacy-inspect.v1", 1, "cleancli.privacy", "stable"),
    ("cleanmac.privacy-plan.v1", 1, "cleancli.privacy", "stable"),
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
    "cleanmac.permissions-preflight.v1",
    "cleanmac.tool-plan.v1",
    "cleanmac.tool-execution-result.v1",
    "cleanmac.software-inspect.v1",
    "cleanmac.software-uninstall-plan.v1",
    "cleanmac.startup-audit.v1",
    "cleanmac.startup-disable-result.v1",
    "cleanmac.startup-plan.v1",
    "cleanmac.privacy-execute-result.v1",
    "cleanmac.privacy-inspect.v1",
    "cleanmac.privacy-plan.v1",
    "cleanmac.review.v1",
    "cleanmac.review-selection.v1",
    "cleanmac.review-selection-summary.v1",
    "cleanmac.review-selection-constraint.v1",
    "cleanmac.review-selection-validation.v1",
    "cleanmac.ai-policy-simulation.v1",
    "cleanmac.ai-schema-registry.v1",
    "cleanmac.ai-readiness.v1",
    "cleanmac.ai-host-policy.v1",
    "cleanmac.ai-host-integration-pack.v1",
    "cleanmac.ai-host-preflight.v1",
    "cleanmac.ai-host-evidence.v1",
    "cleanmac.ai-host-tool-call-decision.v1",
    "cleanmac.release-artifact-manifest.v1",
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
    "cleanmac.permissions-preflight.v1": {
        "type": "object",
        "required": [
            "schema",
            "destructive",
            "dry_run",
            "root",
            "home",
            "platform",
            "live_root",
            "sudo_noninteractive",
            "full_disk_access_probe",
            "category_count",
            "blocked_or_needs_attention_count",
            "categories",
            "recommended_next_action",
        ],
        "properties": {
            "schema": {"const": "cleanmac.permissions-preflight.v1"},
            "destructive": {"const": False},
            "dry_run": {"const": True},
            "root": {"type": "string"},
            "home": {"type": "string"},
            "platform": {"type": "string"},
            "live_root": {"type": "boolean"},
            "sudo_noninteractive": {"type": "string"},
            "full_disk_access_probe": {"type": "string"},
            "category_count": {"type": "integer"},
            "blocked_or_needs_attention_count": {"type": "integer"},
            "categories": {
                "type": "array",
                "items": {
                    "type": "object",
                    "required": [
                        "key",
                        "title",
                        "risk",
                        "requires_privilege",
                        "full_disk_access",
                        "execute_ready",
                        "blockers",
                        "hints",
                        "paths",
                    ],
                    "properties": {
                        "key": {"type": "string"},
                        "title": {"type": "string"},
                        "risk": {"type": "string"},
                        "requires_privilege": {"type": "boolean"},
                        "full_disk_access": {"type": "boolean"},
                        "execute_ready": {"type": "boolean"},
                        "blockers": {"type": "array", "items": {"type": "string"}},
                        "hints": {"type": "array", "items": {"type": "string"}},
                        "paths": {"type": "array", "items": {"type": "string"}},
                    },
                    "additionalProperties": True,
                },
            },
            "recommended_next_action": {"type": "string"},
        },
        "additionalProperties": True,
    },
    "cleanmac.tool-plan.v1": {
        "type": "object",
        "required": [
            "schema",
            "destructive",
            "dry_run",
            "root",
            "home",
            "selected_tool",
            "adapter_count",
            "safe_to_auto_execute",
            "adapters",
        ],
        "properties": {
            "schema": {"const": "cleanmac.tool-plan.v1"},
            "destructive": {"const": False},
            "dry_run": {"const": True},
            "root": {"type": "string"},
            "home": {"type": "string"},
            "selected_tool": {"type": "string"},
            "adapter_count": {"type": "integer"},
            "safe_to_auto_execute": {"const": False},
            "adapters": {
                "type": "array",
                "items": {
                    "type": "object",
                    "required": [
                        "key",
                        "title",
                        "risk",
                        "available",
                        "required_binaries",
                        "missing_binaries",
                        "dry_run_commands",
                        "manual_execute_commands",
                        "preserve",
                        "auto_execute_allowed",
                        "notes",
                    ],
                    "properties": {
                        "key": {"type": "string"},
                        "title": {"type": "string"},
                        "risk": {"type": "string"},
                        "available": {"type": "boolean"},
                        "required_binaries": {"type": "array", "items": {"type": "string"}},
                        "missing_binaries": {"type": "array", "items": {"type": "string"}},
                        "dry_run_commands": {"type": "array", "items": {"type": "array"}},
                        "manual_execute_commands": {"type": "array", "items": {"type": "array"}},
                        "preserve": {"type": "array", "items": {"type": "string"}},
                        "auto_execute_allowed": {"const": False},
                        "notes": {"type": "array", "items": {"type": "string"}},
                    },
                    "additionalProperties": True,
                },
            },
        },
        "additionalProperties": True,
    },
    "cleanmac.tool-execution-result.v1": {
        "type": "object",
        "required": [
            "schema",
            "destructive",
            "dry_run",
            "root",
            "home",
            "selected_tool",
            "safe_to_auto_execute",
            "results",
            "succeeded_count",
            "failed_count",
        ],
        "properties": {
            "schema": {"const": "cleanmac.tool-execution-result.v1"},
            "destructive": {"type": "boolean"},
            "dry_run": {"type": "boolean"},
            "root": {"type": "string"},
            "home": {"type": "string"},
            "selected_tool": {"type": "string"},
            "safe_to_auto_execute": {"const": False},
            "results": {"type": "array", "items": {"type": "object"}},
            "succeeded_count": {"type": "integer"},
            "failed_count": {"type": "integer"},
        },
        "additionalProperties": True,
    },
    "cleanmac.software-inspect.v1": {
        "type": "object",
        "required": [
            "schema",
            "destructive",
            "dry_run",
            "root",
            "home",
            "app",
            "found",
            "candidate_count",
            "candidates",
        ],
        "properties": {
            "schema": {"const": "cleanmac.software-inspect.v1"},
            "destructive": {"const": False},
            "dry_run": {"const": True},
            "root": {"type": "string"},
            "home": {"type": "string"},
            "app": {"type": "string"},
            "found": {"type": "boolean"},
            "candidate_count": {"type": "integer"},
            "candidates": {"type": "array", "items": {"type": "object"}},
        },
        "additionalProperties": True,
    },
    "cleanmac.software-uninstall-plan.v1": {
        "type": "object",
        "required": [
            "schema",
            "destructive",
            "dry_run",
            "root",
            "home",
            "app",
            "valid",
            "blocked_reasons",
            "uninstall_plan",
        ],
        "properties": {
            "schema": {"const": "cleanmac.software-uninstall-plan.v1"},
            "destructive": {"const": False},
            "dry_run": {"const": True},
            "root": {"type": "string"},
            "home": {"type": "string"},
            "app": {"type": ["string", "null"]},
            "valid": {"type": "boolean"},
            "blocked_reasons": {"type": "array", "items": {"type": "string"}},
            "uninstall_plan": {"type": ["object", "null"]},
        },
        "additionalProperties": True,
    },
    "cleanmac.startup-audit.v1": {
        "type": "object",
        "required": ["schema", "destructive", "dry_run", "root", "home", "scanned_locations", "item_count", "items"],
        "properties": {
            "schema": {"const": "cleanmac.startup-audit.v1"},
            "destructive": {"const": False},
            "dry_run": {"const": True},
            "root": {"type": "string"},
            "home": {"type": "string"},
            "scanned_locations": {"type": "array", "items": {"type": "string"}},
            "item_count": {"type": "integer"},
            "items": {"type": "array", "items": {"type": "object"}},
        },
        "additionalProperties": True,
    },
    "cleanmac.startup-plan.v1": {
        "type": "object",
        "required": ["schema", "destructive", "dry_run", "root", "home", "valid", "blocked_reasons", "disable_plan"],
        "properties": {
            "schema": {"const": "cleanmac.startup-plan.v1"},
            "destructive": {"const": False},
            "dry_run": {"const": True},
            "root": {"type": "string"},
            "home": {"type": "string"},
            "valid": {"type": "boolean"},
            "blocked_reasons": {"type": "array", "items": {"type": "string"}},
            "disable_plan": {
                "type": "object",
                "properties": {
                    "requires_explicit_execute": {"type": "boolean"},
                    "requires_explicit_future_execute": {"type": "boolean"},
                    "safe_to_auto_execute": {"type": "boolean"},
                },
                "additionalProperties": True,
            },
        },
        "additionalProperties": True,
    },
    "cleanmac.startup-disable-result.v1": {
        "type": "object",
        "required": ["schema", "destructive", "dry_run", "root", "home", "review_selection", "results"],
        "properties": {
            "schema": {"const": "cleanmac.startup-disable-result.v1"},
            "destructive": {"type": "boolean"},
            "dry_run": {"type": "boolean"},
            "root": {"type": "string"},
            "home": {"type": "string"},
            "review_selection": {"type": "object"},
            "results": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "backup_path": {"type": ["string", "null"]},
                        "backup_sha256": {"type": ["string", "null"]},
                    },
                    "additionalProperties": True,
                },
            },
        },
        "additionalProperties": True,
    },
    "cleanmac.privacy-inspect.v1": {
        "type": "object",
        "required": ["schema", "destructive", "dry_run", "root", "home", "scope", "candidate_count", "candidates"],
        "properties": {
            "schema": {"const": "cleanmac.privacy-inspect.v1"},
            "destructive": {"const": False},
            "dry_run": {"const": True},
            "root": {"type": "string"},
            "home": {"type": "string"},
            "scope": {"type": "string"},
            "candidate_count": {"type": "integer"},
            "candidates": {"type": "array", "items": {"type": "object"}},
        },
        "additionalProperties": True,
    },
    "cleanmac.privacy-plan.v1": {
        "type": "object",
        "required": [
            "schema",
            "destructive",
            "dry_run",
            "root",
            "home",
            "scope",
            "valid",
            "blocked_reasons",
            "privacy_plan",
        ],
        "properties": {
            "schema": {"const": "cleanmac.privacy-plan.v1"},
            "destructive": {"const": False},
            "dry_run": {"const": True},
            "root": {"type": "string"},
            "home": {"type": "string"},
            "scope": {"type": "string"},
            "valid": {"type": "boolean"},
            "blocked_reasons": {"type": "array", "items": {"type": "string"}},
            "privacy_plan": {
                "type": "object",
                "properties": {
                    "requires_explicit_execute": {"type": "boolean"},
                    "requires_explicit_future_execute": {"type": "boolean"},
                    "safe_to_auto_execute": {"type": "boolean"},
                },
                "additionalProperties": True,
            },
        },
        "additionalProperties": True,
    },
    "cleanmac.privacy-execute-result.v1": {
        "type": "object",
        "required": ["schema", "destructive", "dry_run", "root", "home", "review_selection", "results"],
        "properties": {
            "schema": {"const": "cleanmac.privacy-execute-result.v1"},
            "destructive": {"type": "boolean"},
            "dry_run": {"type": "boolean"},
            "root": {"type": "string"},
            "home": {"type": "string"},
            "scope": {"type": "string"},
            "review_selection": {"type": "object"},
            "results": {"type": "array", "items": {"type": "object"}},
        },
        "additionalProperties": True,
    },
    "cleanmac.review.v1": {
        "type": "object",
        "required": ["schema", "destructive", "dry_run", "source_fingerprint", "item_count", "items", "selection"],
        "properties": {
            "schema": {"const": "cleanmac.review.v1"},
            "destructive": {"const": False},
            "dry_run": {"const": True},
            "source_fingerprint": {"type": "string"},
            "item_count": {"type": "integer"},
            "items": {"type": "array", "items": {"type": "object"}},
            "selection": {"type": "object"},
        },
        "additionalProperties": True,
    },
    "cleanmac.review-selection.v1": {
        "type": "object",
        "required": ["schema", "source_fingerprint", "selected_item_ids", "excluded_item_ids"],
        "properties": {
            "schema": {"const": "cleanmac.review-selection.v1"},
            "source_fingerprint": {"type": "string"},
            "selected_item_ids": {"type": "array", "items": {"type": "string"}},
            "excluded_item_ids": {"type": "array", "items": {"type": "string"}},
        },
        "additionalProperties": True,
    },
    "cleanmac.review-selection-summary.v1": {
        "type": "object",
        "required": ["schema", "destructive", "dry_run", "item_count", "selected_count", "excluded_count"],
        "properties": {
            "schema": {"const": "cleanmac.review-selection-summary.v1"},
            "destructive": {"const": False},
            "dry_run": {"const": True},
            "item_count": {"type": "integer"},
            "selected_count": {"type": "integer"},
            "excluded_count": {"type": "integer"},
        },
        "additionalProperties": True,
    },
    "cleanmac.review-selection-constraint.v1": {
        "type": "object",
        "required": [
            "schema",
            "selection_file",
            "source_plan_file",
            "selected_item_ids",
            "selected_paths",
            "validation",
        ],
        "properties": {
            "schema": {"const": "cleanmac.review-selection-constraint.v1"},
            "selection_file": {"type": "string"},
            "source_plan_file": {"type": "string"},
            "source_fingerprint": {"type": "string"},
            "selected_item_ids": {"type": "array", "items": {"type": "string"}},
            "selected_paths": {"type": "array", "items": {"type": "string"}},
            "selected_count": {"type": "integer"},
            "validation": {"type": "object"},
        },
        "additionalProperties": True,
    },
    "cleanmac.review-selection-validation.v1": {
        "type": "object",
        "required": ["schema", "destructive", "dry_run", "valid", "blocked_reasons"],
        "properties": {
            "schema": {"const": "cleanmac.review-selection-validation.v1"},
            "destructive": {"const": False},
            "dry_run": {"const": True},
            "valid": {"type": "boolean"},
            "blocked_reasons": {"type": "array", "items": {"type": "string"}},
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
    "cleanmac.ai-host-tool-call-decision.v1": {
        "type": "object",
        "required": [
            "schema",
            "source",
            "tool",
            "risk",
            "allowed",
            "auto_call_allowed",
            "requires_human_confirmation",
            "blocking_reasons",
            "safe_to_auto_retry",
        ],
        "properties": {
            "schema": {"const": "cleanmac.ai-host-tool-call-decision.v1"},
            "source": {"type": "string"},
            "tool": {"type": "string"},
            "risk": {"type": "string"},
            "allowed": {"type": "boolean"},
            "auto_call_allowed": {"type": "boolean"},
            "requires_human_confirmation": {"type": "boolean"},
            "blocking_reasons": {"type": "array", "items": {"type": "object"}},
            "safe_to_auto_retry": {"type": "boolean"},
        },
        "additionalProperties": True,
    },
    "cleanmac.ai-host-integration-pack.v1": {
        "type": "object",
        "required": [
            "schema",
            "destructive",
            "dry_run",
            "ready",
            "mcp",
            "cli",
            "critical_schemas",
            "recommended_preflight_commands",
            "recommended_call_sequence",
            "readiness",
            "runbook",
            "decision_matrix",
            "governance_advice",
            "host_policy",
            "schema_registry",
            "eval_pack",
            "contract_validation",
            "contract_samples",
        ],
        "properties": {
            "schema": {"const": "cleanmac.ai-host-integration-pack.v1"},
            "destructive": {"const": False},
            "dry_run": {"const": True},
            "ready": {"type": "boolean"},
            "mcp": {"type": "object"},
            "cli": {"type": "object"},
            "critical_schemas": {"type": "array", "items": {"type": "string"}},
            "recommended_preflight_commands": {"type": "array", "items": {"type": "array"}},
            "recommended_call_sequence": {"type": "array", "items": {"type": "string"}},
            "readiness": {"type": "object"},
            "runbook": {"type": "object"},
            "decision_matrix": {"type": "object"},
            "governance_advice": {"type": "object"},
            "host_policy": {"type": "object"},
            "schema_registry": {"type": "object"},
            "eval_pack": {"type": "object"},
            "contract_validation": {"type": "object"},
            "contract_samples": {"type": "object"},
        },
        "additionalProperties": True,
    },
    "cleanmac.ai-host-preflight.v1": {
        "type": "object",
        "required": [
            "schema",
            "destructive",
            "dry_run",
            "ready",
            "entrypoint",
            "checks",
            "required_before_destructive_tool",
            "release_gate_commands",
        ],
        "properties": {
            "schema": {"const": "cleanmac.ai-host-preflight.v1"},
            "destructive": {"const": False},
            "dry_run": {"const": True},
            "ready": {"type": "boolean"},
            "entrypoint": {"type": "object"},
            "checks": {"type": "array", "items": {"type": "object"}},
            "required_before_destructive_tool": {"type": "array", "items": {"type": "string"}},
            "release_gate_commands": {"type": "array", "items": {"type": "array"}},
        },
        "additionalProperties": True,
    },
    "cleanmac.ai-host-evidence.v1": {
        "type": "object",
        "required": [
            "schema",
            "destructive",
            "dry_run",
            "ready",
            "source",
            "evidence_checks",
            "runtime_policy_evidence",
            "release_gate_commands",
        ],
        "properties": {
            "schema": {"const": "cleanmac.ai-host-evidence.v1"},
            "destructive": {"const": False},
            "dry_run": {"const": True},
            "ready": {"type": "boolean"},
            "source": {"const": "cleanmac-ai-host-evidence"},
            "critical_schemas": {"type": "array", "items": {"type": "string"}},
            "evidence_checks": {"type": "array", "items": {"type": "object"}},
            "observed_blocking_codes": {"type": "array", "items": {"type": "string"}},
            "integration_pack": {"type": "object"},
            "preflight": {"type": "object"},
            "contract_validation": {"type": "object"},
            "runtime_policy_evidence": {"type": "array", "items": {"type": "object"}},
            "release_gate_commands": {"type": "array", "items": {"type": "array"}},
            "review_questions": {"type": "array", "items": {"type": "string"}},
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
    "cleanmac.ai-contract-samples.v1": {
        "type": "object",
        "required": ["schema", "destructive", "dry_run", "sample_count", "samples"],
        "properties": {
            "schema": {"const": "cleanmac.ai-contract-samples.v1"},
            "destructive": {"const": False},
            "dry_run": {"const": True},
            "sample_count": {"type": "integer"},
            "samples": {"type": "array", "items": {"type": "object"}},
        },
        "additionalProperties": True,
    },
    "cleanmac.release-artifact-manifest.v1": {
        "type": "object",
        "required": ["schema", "python_version", "platform", "artifacts", "distribution_policy"],
        "properties": {
            "schema": {"const": "cleanmac.release-artifact-manifest.v1"},
            "python_version": {"type": "string"},
            "platform": {"type": "string"},
            "artifacts": {
                "type": "array",
                "items": {
                    "type": "object",
                    "required": ["name", "sha256", "kind"],
                    "properties": {
                        "name": {"type": "string"},
                        "sha256": {"type": "string"},
                        "kind": {"type": "string"},
                    },
                    "additionalProperties": True,
                },
            },
            "distribution_policy": {"type": "object"},
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
        errors = _validate_schema_fragment(schema_fragment, payload, "$")
    return {
        "schema": "cleanmac.ai-contract-validation.v1",
        "destructive": False,
        "dry_run": True,
        "valid": not errors,
        "target_schema": schema_name,
        "error_count": len(errors),
        "errors": errors,
    }


def _sample_payload_for_schema(schema_name: str) -> dict[str, Any]:
    samples: dict[str, dict[str, Any]] = {
        "cleanmac.plan.v1": {
            "schema": "cleanmac.plan.v1",
            "destructive": False,
            "dry_run": True,
            "generated_at": "2026-06-19T00:00:00+00:00",
            "expires_at": "2026-06-19T00:30:00+00:00",
            "selected_category_keys": ["trash"],
            "candidate_fingerprints": [{"path": "/tmp/old.tmp", "exists": True}],
        },
        "cleanmac.validate-plan.v1": {
            "schema": "cleanmac.validate-plan.v1",
            "destructive": False,
            "dry_run": True,
            "valid": True,
            "plan": {"schema": "cleanmac.plan.v1", "selected_category_keys": ["trash"]},
            "schema_negotiation": {
                "accepted": True,
                "schema": "cleanmac.plan.v1",
                "reason": "supported",
                "latest_supported_schema": "cleanmac.plan.v1",
                "legacy": False,
            },
        },
        "cleanmac.permissions-preflight.v1": {
            "schema": "cleanmac.permissions-preflight.v1",
            "destructive": False,
            "dry_run": True,
            "root": "/tmp/cleanmac-sandbox",
            "home": "/Users/tester",
            "platform": "darwin",
            "live_root": False,
            "sudo_noninteractive": "not-available-or-needs-auth",
            "full_disk_access_probe": "manual",
            "category_count": 2,
            "blocked_or_needs_attention_count": 1,
            "categories": [
                {
                    "key": "imessage",
                    "title": "Messages attachments and caches",
                    "risk": "medium",
                    "requires_privilege": False,
                    "full_disk_access": True,
                    "process_guard": None,
                    "provider": "cleanmac",
                    "execute_ready": True,
                    "blockers": [],
                    "hints": ["Grant Full Disk Access before scanning protected user data on live root."],
                    "paths": ["/Users/tester/Library/Messages/Attachments"],
                },
                {
                    "key": "systemLogs",
                    "title": "System logs",
                    "risk": "high",
                    "requires_privilege": True,
                    "full_disk_access": False,
                    "process_guard": None,
                    "provider": "cleanmac",
                    "execute_ready": False,
                    "blockers": ["sudo-noninteractive-unavailable"],
                    "hints": ["Run a dry-run first, then retry from an administrator terminal if required."],
                    "paths": ["/Library/Logs"],
                },
            ],
            "recommended_next_action": "review_blockers_before_execute",
        },
        "cleanmac.tool-plan.v1": {
            "schema": "cleanmac.tool-plan.v1",
            "destructive": False,
            "dry_run": True,
            "root": "/tmp/cleanmac-sandbox",
            "home": "/Users/tester",
            "selected_tool": "docker",
            "adapter_count": 1,
            "safe_to_auto_execute": False,
            "adapters": [
                {
                    "key": "docker",
                    "title": "Docker semantic cleanup plan",
                    "risk": "medium",
                    "available": False,
                    "required_binaries": ["docker"],
                    "missing_binaries": ["docker"],
                    "dry_run_commands": [["docker", "system", "df"], ["docker", "builder", "du"]],
                    "manual_execute_commands": [
                        ["docker", "builder", "prune"],
                        ["docker", "image", "prune"],
                        ["docker", "container", "prune"],
                    ],
                    "preserve": ["volumes", "contexts", "auth", "daemon configuration"],
                    "auto_execute_allowed": False,
                    "notes": ["This adapter is read-only and does not run tool prune commands."],
                }
            ],
        },
        "cleanmac.tool-execution-result.v1": {
            "schema": "cleanmac.tool-execution-result.v1",
            "destructive": False,
            "dry_run": True,
            "root": "/tmp/cleanmac-sandbox",
            "home": "/Users/tester",
            "selected_tool": "docker",
            "safe_to_auto_execute": False,
            "blocked_reasons": [],
            "results": [
                {
                    "tool": "docker",
                    "argv": ["docker", "system", "df"],
                    "status": "missing-binary",
                    "returncode": None,
                    "stdout": "",
                    "stderr": "",
                    "error": "Missing binary: docker",
                }
            ],
            "succeeded_count": 0,
            "failed_count": 1,
        },
        "cleanmac.software-inspect.v1": {
            "schema": "cleanmac.software-inspect.v1",
            "destructive": False,
            "dry_run": True,
            "root": "/tmp/cleanmac-sandbox",
            "home": "/Users/tester",
            "app": "Example",
            "found": True,
            "app_identity": {"name": "Example.app", "bundle_id": "com.example.app"},
            "candidate_count": 1,
            "candidates": [
                {
                    "id": "cache:/Users/tester/Library/Caches/com.example.app",
                    "path": "/Users/tester/Library/Caches/com.example.app",
                    "kind": "cache",
                    "bytes": 128,
                    "confidence": "high",
                    "match_reason": "bundle-id",
                    "risk": "low",
                    "default_selected": True,
                    "protected": False,
                    "delete_mode": "trash",
                }
            ],
        },
        "cleanmac.software-uninstall-plan.v1": {
            "schema": "cleanmac.software-uninstall-plan.v1",
            "destructive": False,
            "dry_run": True,
            "root": "/tmp/cleanmac-sandbox",
            "home": "/Users/tester",
            "app": "Example",
            "valid": True,
            "blocked_reasons": [],
            "uninstall_plan": {
                "app": "Example",
                "requires_explicit_future_execute": True,
                "official_uninstaller_required": False,
                "candidate_count": 1,
                "candidates": [
                    {
                        "id": "cache:/Users/tester/Library/Caches/com.example.app",
                        "path": "/Users/tester/Library/Caches/com.example.app",
                        "kind": "cache",
                        "default_selected": True,
                        "protected": False,
                    }
                ],
            },
        },
        "cleanmac.startup-audit.v1": {
            "schema": "cleanmac.startup-audit.v1",
            "destructive": False,
            "dry_run": True,
            "root": "/tmp/cleanmac-sandbox",
            "home": "/Users/tester",
            "scanned_locations": ["/Users/tester/Library/LaunchAgents", "/Library/LaunchDaemons"],
            "item_count": 1,
            "items": [
                {
                    "id": "startup:user-launch-agent:com.example.agent:/Users/tester/Library/LaunchAgents/com.example.agent.plist",
                    "path": "/Users/tester/Library/LaunchAgents/com.example.agent.plist",
                    "kind": "user-launch-agent",
                    "label": "com.example.agent",
                    "risk": "medium",
                    "recommendation": "review-disable",
                    "default_selected": True,
                }
            ],
        },
        "cleanmac.startup-plan.v1": {
            "schema": "cleanmac.startup-plan.v1",
            "destructive": False,
            "dry_run": True,
            "root": "/tmp/cleanmac-sandbox",
            "home": "/Users/tester",
            "valid": True,
            "blocked_reasons": [],
            "disable_plan": {
                "requires_explicit_execute": True,
                "requires_explicit_future_execute": True,
                "safe_to_auto_execute": False,
                "candidate_count": 1,
                "candidates": [
                    {
                        "id": "startup:user-launch-agent:com.example.agent:/Users/tester/Library/LaunchAgents/com.example.agent.plist",
                        "path": "/Users/tester/Library/LaunchAgents/com.example.agent.plist",
                        "recommendation": "review-disable",
                        "default_selected": True,
                    }
                ],
            },
        },
        "cleanmac.startup-disable-result.v1": {
            "schema": "cleanmac.startup-disable-result.v1",
            "destructive": True,
            "dry_run": False,
            "root": "/tmp/cleanmac-sandbox",
            "home": "/Users/tester",
            "review_selection": {
                "schema": "cleanmac.review-selection-constraint.v1",
                "selected_item_ids": [
                    "startup:user-launch-agent:com.example.agent:/Users/tester/Library/LaunchAgents/com.example.agent.plist"
                ],
            },
            "results": [
                {
                    "id": "startup:user-launch-agent:com.example.agent:/Users/tester/Library/LaunchAgents/com.example.agent.plist",
                    "path": "/Users/tester/Library/LaunchAgents/com.example.agent.plist",
                    "status": "disabled",
                    "executed": True,
                    "backup_path": "/Users/tester/Library/LaunchAgents/com.example.agent.plist.cleanmac.bak",
                    "backup_sha256": "b" * 64,
                }
            ],
        },
        "cleanmac.privacy-inspect.v1": {
            "schema": "cleanmac.privacy-inspect.v1",
            "destructive": False,
            "dry_run": True,
            "root": "/tmp/cleanmac-sandbox",
            "home": "/Users/tester",
            "scope": "cache",
            "candidate_count": 1,
            "candidates": [
                {
                    "id": "privacy:Chrome:Default:cache:/Users/tester/Library/Caches/Google/Chrome/Default/Cache",
                    "path": "/Users/tester/Library/Caches/Google/Chrome/Default/Cache",
                    "application": "Chrome",
                    "profile": "Default",
                    "kind": "cache",
                    "scope": "cache",
                    "default_selected": True,
                }
            ],
        },
        "cleanmac.privacy-plan.v1": {
            "schema": "cleanmac.privacy-plan.v1",
            "destructive": False,
            "dry_run": True,
            "root": "/tmp/cleanmac-sandbox",
            "home": "/Users/tester",
            "scope": "cache",
            "valid": True,
            "blocked_reasons": [],
            "privacy_plan": {
                "requires_explicit_execute": True,
                "requires_explicit_future_execute": True,
                "safe_to_auto_execute": False,
                "candidate_count": 1,
                "candidates": [
                    {
                        "id": "privacy:Chrome:Default:cache:/Users/tester/Library/Caches/Google/Chrome/Default/Cache",
                        "path": "/Users/tester/Library/Caches/Google/Chrome/Default/Cache",
                        "scope": "cache",
                        "default_selected": True,
                    }
                ],
            },
        },
        "cleanmac.privacy-execute-result.v1": {
            "schema": "cleanmac.privacy-execute-result.v1",
            "destructive": True,
            "dry_run": False,
            "root": "/tmp/cleanmac-sandbox",
            "home": "/Users/tester",
            "scope": "cache",
            "review_selection": {
                "schema": "cleanmac.review-selection-constraint.v1",
                "source_fingerprint": "a" * 64,
                "selected_count": 1,
                "selected_item_ids": [
                    "privacy:Chrome:Default:cache:/Users/tester/Library/Caches/Google/Chrome/Default/Cache"
                ],
            },
            "result_count": 1,
            "deleted_count": 1,
            "results": [
                {
                    "id": "privacy:Chrome:Default:cache:/Users/tester/Library/Caches/Google/Chrome/Default/Cache",
                    "path": "/Users/tester/Library/Caches/Google/Chrome/Default/Cache",
                    "scope": "cache",
                    "status": "deleted",
                    "executed": True,
                }
            ],
        },
        "cleanmac.review.v1": {
            "schema": "cleanmac.review.v1",
            "destructive": False,
            "dry_run": True,
            "generated_at": "2026-06-20T00:00:00+00:00",
            "source_schema": "cleanmac.software-uninstall-plan.v1",
            "source_fingerprint": "a" * 64,
            "item_count": 1,
            "default_selected_count": 1,
            "items": [{"id": "item-1", "path": "/tmp/cache", "risk": "low", "default_selected": True}],
            "selection": {
                "schema": "cleanmac.review-selection.v1",
                "source_fingerprint": "a" * 64,
                "selected_item_ids": ["item-1"],
                "excluded_item_ids": [],
            },
        },
        "cleanmac.review-selection.v1": {
            "schema": "cleanmac.review-selection.v1",
            "source_fingerprint": "a" * 64,
            "selected_item_ids": ["item-1"],
            "excluded_item_ids": [],
        },
        "cleanmac.review-selection-summary.v1": {
            "schema": "cleanmac.review-selection-summary.v1",
            "destructive": False,
            "dry_run": True,
            "item_count": 1,
            "selected_count": 1,
            "excluded_count": 0,
            "protected_count": 0,
            "unknown_item_count": 0,
            "selected_bytes": 1,
            "excluded_bytes": 0,
            "selected_risk_counts": {"low": 1},
            "excluded_risk_counts": {},
            "selected_scope_counts": {},
            "selected_application_counts": {},
            "selected_kind_counts": {"cache": 1},
            "requires_sensitive_review": False,
        },
        "cleanmac.review-selection-constraint.v1": {
            "schema": "cleanmac.review-selection-constraint.v1",
            "selection_file": "/tmp/selection.json",
            "source_plan_file": "/tmp/plan.json",
            "source_fingerprint": "a" * 64,
            "selected_item_ids": ["item-1"],
            "selected_paths": ["/tmp/cache"],
            "selected_count": 1,
            "validation": {
                "schema": "cleanmac.review-selection-validation.v1",
                "destructive": False,
                "dry_run": True,
                "valid": True,
                "blocked_reasons": [],
            },
        },
        "cleanmac.review-selection-validation.v1": {
            "schema": "cleanmac.review-selection-validation.v1",
            "destructive": False,
            "dry_run": True,
            "valid": True,
            "source_fingerprint": "a" * 64,
            "selection_source_fingerprint": "a" * 64,
            "fingerprint_matches": True,
            "item_count": 1,
            "selected_count": 1,
            "excluded_count": 0,
            "unknown_selected_item_ids": [],
            "unknown_excluded_item_ids": [],
            "protected_selected_item_ids": [],
            "overlap_item_ids": [],
            "blocked_reasons": [],
        },
        "cleanmac.ai-policy-simulation.v1": {
            "schema": "cleanmac.ai-policy-simulation.v1",
            "destructive": False,
            "dry_run": True,
            "allowed": False,
            "blocking_reasons": [{"code": "AI_ORIGIN_REQUIRES_CONFIRMATION_TOKEN"}],
        },
        "cleanmac.ai-schema-registry.v1": render_ai_schema_registry(),
        "cleanmac.ai-readiness.v1": {
            "schema": "cleanmac.ai-readiness.v1",
            "ready": True,
            "tool_count": 1,
            "contracts": {"schema_validation": {"valid": True}},
            "schema_registry": {"ready": True},
        },
        "cleanmac.ai-host-policy.v1": {
            "schema": "cleanmac.ai-host-policy.v1",
            "valid": True,
            "default_decision": "deny",
            "auto_call": {
                "allow": [],
                "deny": ["cleanmac_execute_plan", "cleanmac_startup_disable", "cleanmac_privacy_execute"],
            },
            "execution_gate": {"auto_call_allowed": False},
        },
        "cleanmac.ai-governance-advice.v1": {
            "schema": "cleanmac.ai-governance-advice.v1",
            "ready_for_llm_calling": True,
            "governance_score": {"level": "strong"},
            "default_policy": {"shell_allowed": False},
            "required_host_controls": ["Load host policy before execution."],
            "recommended_call_sequence": ["cleanmac_capabilities"],
            "anti_patterns": ["Calling execute directly."],
            "governance_route": [{"id": "entrypoint-governance", "status": "satisfied"}],
            "release_gate_commands": [["make", "ai-governance-smoke"]],
            "recommendations": [{"id": "preflight-first"}],
        },
        "cleanmac.ai-eval-pack.v1": {
            "schema": "cleanmac.ai-eval-pack.v1",
            "scenario_count": 1,
            "scenarios": [{"id": "discover_readiness"}],
            "allows_destructive_execution": False,
            "recommended_runner_command": ["cleanmac", "--json", "ai-eval-run", "--scenario", "smoke"],
        },
        "cleanmac.ai-eval-run.v1": {
            "schema": "cleanmac.ai-eval-run.v1",
            "scenario": "smoke",
            "passed": True,
            "passed_count": 1,
            "failed_count": 0,
            "results": [{"id": "discover_readiness", "passed": True}],
        },
        "cleanmac.ai-host-integration-pack.v1": {
            "schema": "cleanmac.ai-host-integration-pack.v1",
            "destructive": False,
            "dry_run": True,
            "ready": True,
            "mcp": {
                "resource_uri": "cleanmac://ai/host-integration-pack",
                "resources": ["cleanmac://ai/host-integration-pack"],
                "transport": "stdio",
                "uses_shell": False,
            },
            "cli": {"command": ["cleanmac", "--json", "ai-host-integration-pack"], "uses_shell": False},
            "critical_schemas": ["cleanmac.ai-host-integration-pack.v1"],
            "recommended_preflight_commands": [["cleanmac", "--json", "ai-host-integration-pack"]],
            "recommended_call_sequence": ["read cleanmac://ai/host-integration-pack"],
            "readiness": {"schema": "cleanmac.ai-readiness.v1", "ready": True},
            "runbook": {"schema": "cleanmac.ai-runbook.v1"},
            "decision_matrix": {"schema": "cleanmac.ai-tool-decision-matrix.v1", "violation_count": 0},
            "governance_advice": {
                "schema": "cleanmac.ai-governance-advice.v1",
                "ready_for_llm_calling": True,
            },
            "host_policy": {"schema": "cleanmac.ai-host-policy.v1", "valid": True},
            "schema_registry": {"schema": "cleanmac.ai-schema-registry.v1"},
            "eval_pack": {"schema": "cleanmac.ai-eval-pack.v1", "allows_destructive_execution": False},
            "contract_validation": {"schema": "cleanmac.ai-contract-validation-summary.v1", "valid": True},
            "contract_samples": {"schema": "cleanmac.ai-contract-samples.v1", "sample_count": 1},
        },
        "cleanmac.ai-host-preflight.v1": {
            "schema": "cleanmac.ai-host-preflight.v1",
            "destructive": False,
            "dry_run": True,
            "ready": True,
            "entrypoint": {
                "cli": ["cleanmac", "--json", "ai-host-integration-pack"],
                "mcp_resource": "cleanmac://ai/host-integration-pack",
            },
            "checks": [
                {"id": "integration-pack-ready", "passed": True},
                {"id": "mcp-runtime-policy-present", "passed": True},
            ],
            "required_before_destructive_tool": ["human_confirmation_phrase", "matching_confirmation_token"],
            "release_gate_commands": [["make", "mcp-smoke"], ["make", "ai-host-smoke"]],
        },
        "cleanmac.ai-host-evidence.v1": {
            "schema": "cleanmac.ai-host-evidence.v1",
            "destructive": False,
            "dry_run": True,
            "ready": True,
            "source": "cleanmac-ai-host-evidence",
            "critical_schemas": ["cleanmac.ai-host-evidence.v1"],
            "evidence_checks": [{"id": "preflight-ready", "passed": True, "evidence": "cleanmac.ai-host-preflight.v1"}],
            "observed_blocking_codes": ["RAW_COMMAND_ARGUMENT_DENIED"],
            "integration_pack": {"schema": "cleanmac.ai-host-integration-pack.v1", "ready": True},
            "preflight": {"schema": "cleanmac.ai-host-preflight.v1", "ready": True},
            "contract_validation": {"schema": "cleanmac.ai-contract-validation-summary.v1", "valid": True},
            "runtime_policy_evidence": [
                {
                    "id": "raw-command-argument-denied",
                    "decision": {
                        "schema": "cleanmac.ai-host-tool-call-decision.v1",
                        "source": "sample",
                        "tool": "cleanmac_capabilities",
                        "risk": "readonly",
                        "allowed": False,
                        "auto_call_allowed": True,
                        "requires_human_confirmation": False,
                        "blocking_reasons": [{"code": "RAW_COMMAND_ARGUMENT_DENIED", "field": "raw_command"}],
                        "safe_to_auto_retry": False,
                    },
                }
            ],
            "release_gate_commands": [["make", "ai-host-smoke"]],
            "review_questions": ["Did the host run cleanmac.ai-host-preflight.v1?"],
        },
        "cleanmac.ai-host-tool-call-decision.v1": {
            "schema": "cleanmac.ai-host-tool-call-decision.v1",
            "source": "mcp.tools/call",
            "tool": "cleanmac_capabilities",
            "risk": "readonly",
            "allowed": True,
            "auto_call_allowed": True,
            "requires_human_confirmation": False,
            "blocking_reasons": [],
            "safe_to_auto_retry": True,
        },
        "cleanmac.ai-contract-validation.v1": {
            "schema": "cleanmac.ai-contract-validation.v1",
            "destructive": False,
            "dry_run": True,
            "valid": True,
            "target_schema": "cleanmac.plan.v1",
            "error_count": 0,
            "errors": [],
        },
        "cleanmac.release-artifact-manifest.v1": {
            "schema": "cleanmac.release-artifact-manifest.v1",
            "python_version": "3.12.0",
            "platform": "Linux-6.0-x86_64-with-glibc2.36",
            "artifacts": [
                {"name": "cleanmac-0.1.0-py3-none-any.whl", "sha256": "a" * 64, "kind": "wheel"},
                {"name": "cleanmac-0.1.0.tar.gz", "sha256": "b" * 64, "kind": "sdist"},
                {"name": "SBOM.json", "sha256": "c" * 64, "kind": "sbom"},
            ],
            "distribution_policy": {
                "homebrew_formula": "preflight-only",
                "standalone_zipapp": "smoke-tested outside release upload",
                "publish_after_cross_platform_verification": True,
            },
        },
    }
    if schema_name == "cleanmac.ai-contract-validation-summary.v1":
        result = samples["cleanmac.ai-contract-validation.v1"]
        return {
            "schema": "cleanmac.ai-contract-validation-summary.v1",
            "destructive": False,
            "dry_run": True,
            "valid": True,
            "validated_schema_count": 1,
            "failure_count": 0,
            "results": [result],
        }
    if schema_name not in samples:
        return {"schema": schema_name}
    return samples[schema_name]


def render_ai_contract_samples() -> dict[str, Any]:
    samples = []
    for schema_name in AI_HOST_CRITICAL_SCHEMAS:
        payload = _sample_payload_for_schema(schema_name)
        validation = validate_contract_payload(schema_name, payload)
        samples.append(
            {
                "target_schema": schema_name,
                "valid": validation["valid"],
                "payload": payload,
                "validation": validation,
            }
        )
    return {
        "schema": "cleanmac.ai-contract-samples.v1",
        "destructive": False,
        "dry_run": True,
        "sample_count": len(samples),
        "samples": samples,
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
