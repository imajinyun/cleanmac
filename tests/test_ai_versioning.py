from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
CLI = PROJECT_ROOT / "cleanmac.py"
CLEANCLI_DIR = PROJECT_ROOT / "cleancli"

SCHEMA_PATTERN = re.compile(r'"schema"\s*:\s*"(cleanmac\.[a-zA-Z0-9._-]+\.v\d+)"')


class TestAISchemaRegistry:
    def test_registry_command_emits_schema_inventory(self) -> None:
        result = subprocess.run(
            [sys.executable, str(CLI), "--json", "ai-schema-registry"],
            text=True,
            capture_output=True,
            check=True,
        )
        report = json.loads(result.stdout)

        assert report["schema"] == "cleanmac.ai-schema-registry.v1"
        assert report["entry_count"] >= 15
        names = {entry["name"] for entry in report["entries"]}
        assert "cleanmac.ai-readiness.v1" in names
        assert "cleanmac.ai-runbook.v1" in names
        assert "cleanmac.ai-tool-decision-matrix.v1" in names
        assert "cleanmac.ai-eval-run.v1" in names
        assert "cleanmac.release-readiness.v1" in names
        assert "cleanmac.geo-discoverability-policy.v1" in names
        assert "cleanmac.governance-integrity.v1" in names
        assert "cleanmac.xcode-ios-governance.v1" in names
        assert "cleanmac.zero-resident.v1" in names
        assert "cleanmac.product-surface-drift-audit.v1" in names
        assert "cleanmac.no-disturbance.v1" in names
        assert "cleanmac.no-disturbance-validation.v1" in names
        assert "cleanmac.dependency-governance.v1" in names
        assert "cleanmac.dependency-governance-validation.v1" in names
        for entry in report["entries"]:
            assert "name" in entry
            assert "version" in entry
            assert "module" in entry
            assert "stability" in entry
            assert "kind" in entry
            assert "producer" in entry
            assert "consumers" in entry
            assert "latest" in entry
            assert "deprecated" in entry
            assert "replaced_by" in entry
            assert "compatibility" in entry
            assert "breaking_change_policy" in entry["compatibility"]

    def test_registry_covers_every_v1_schema_emitted_by_codebase(self) -> None:
        from cleancli import ai_versioning

        emitted: set[str] = set()
        for path in CLEANCLI_DIR.rglob("*.py"):
            text = path.read_text(encoding="utf-8")
            emitted.update(SCHEMA_PATTERN.findall(text))
        for path in (PROJECT_ROOT / "scripts").rglob("*.py"):
            text = path.read_text(encoding="utf-8")
            emitted.update(SCHEMA_PATTERN.findall(text))

        registered = {entry["name"] for entry in ai_versioning.render_ai_schema_registry()["entries"]}
        missing = sorted(emitted - registered)
        assert missing == [], f"Schemas missing from registry: {missing}"

    def test_registry_metadata_is_deterministic_and_documents_compatibility_policy(self) -> None:
        from cleancli import ai_versioning

        first = ai_versioning.render_ai_schema_registry()
        second = ai_versioning.render_ai_schema_registry()

        assert first == second
        assert first["entry_count"] == len(first["entries"])
        assert first["stable_schema_count"] >= 20
        assert first["deprecated_schema_count"] == 0
        assert first["latest_plan_schema"] == "cleanmac.plan.v1"
        assert first["supported_plan_schemas"][0] == "cleanmac.plan.v1"
        assert "cleanmac.clean.v1" in first["supported_plan_schemas"]
        assert "cleanmac.clean-plan.v1" in first["supported_plan_schemas"]
        assert "Breaking changes require a new vN suffix" in first["compatibility_policy"]["stable"]
        assert "subject to change" in first["compatibility_policy"]["internal"]
        assert {entry["version"] for entry in first["entries"]} == {1}
        entries = {entry["name"]: entry for entry in first["entries"]}
        assert entries["cleanmac.plan.v1"]["latest"]
        assert not entries["cleanmac.clean.v1"]["latest"]
        assert not entries["cleanmac.clean-plan.v1"]["latest"]
        assert entries["cleanmac.plan.v1"]["producer"] == "clean plan"
        assert "validate-plan" in entries["cleanmac.plan.v1"]["consumers"]
        assert entries["cleanmac.geo-discoverability-policy.v1"]["owner_area"] == "execution"
        assert entries["cleanmac.governance-integrity.v1"]["module"] == "cleancli.governance"
        assert entries["cleanmac.governance-integrity.v1"]["producer_command"] == [
            "cleanmac",
            "--json",
            "governance-integrity",
        ]
        assert entries["cleanmac.software-discovery-governance.v1"]["producer_command"] == [
            "cleanmac",
            "--json",
            "software-discovery-governance",
        ]
        assert entries["cleanmac.software-discovery-governance.v1"]["release_critical"]
        assert entries["cleanmac.xcode-ios-governance.v1"]["producer_command"] == [
            "cleanmac",
            "--json",
            "xcode-ios-governance",
        ]
        assert entries["cleanmac.xcode-ios-governance.v1"]["release_critical"]
        assert entries["cleanmac.zero-resident.v1"]["producer_command"] == [
            "cleanmac",
            "--json",
            "zero-resident",
        ]
        assert entries["cleanmac.product-surface-drift-audit.v1"]["producer_command"] == [
            "cleanmac",
            "--json",
            "product-surface-drift-audit",
        ]
        assert entries["cleanmac.dependency-governance.v1"]["producer_command"] == [
            "cleanmac",
            "--json",
            "dependency-governance",
        ]
        assert entries["cleanmac.no-disturbance.v1"]["producer_command"] == [
            "cleanmac",
            "--json",
            "no-disturbance",
        ]
        assert entries["cleanmac.no-disturbance.v1"]["owner_area"] == "ai-host"
        assert entries["cleanmac.no-disturbance.v1"]["release_critical"]
        assert entries["cleanmac.dependency-governance.v1"]["owner_area"] == "release"
        assert entries["cleanmac.dependency-governance.v1"]["release_critical"]
        assert entries["cleanmac.development-governance-todo.v1"]["module"] == "cleancli.governance"
        assert entries["cleanmac.development-governance-todo.v1"]["producer_command"] == [
            "cleanmac",
            "--json",
            "capabilities",
        ]
        assert entries["cleanmac.development-governance-todo.v1"]["release_critical"]

    def test_registry_exposes_core_json_schema_fragments(self) -> None:
        from cleancli import ai_versioning

        entries = {entry["name"]: entry for entry in ai_versioning.render_ai_schema_registry()["entries"]}
        for schema_name in ai_versioning.AI_HOST_CRITICAL_SCHEMAS:
            assert "json_schema" in entries[schema_name], schema_name
            json_schema = entries[schema_name]["json_schema"]
            assert json_schema["type"] == "object"
            assert "schema" in json_schema["required"]
            assert json_schema["properties"]["schema"]["const"] == schema_name
            assert json_schema["additionalProperties"]

        plan_schema = entries["cleanmac.plan.v1"]["json_schema"]
        assert "destructive" in plan_schema["required"]
        assert "dry_run" in plan_schema["required"]
        assert not plan_schema["properties"]["destructive"]["const"]
        assert plan_schema["properties"]["dry_run"]["const"]
        assert "cleanmac.release-artifact-manifest.v1" in entries
        assert "json_schema" in entries["cleanmac.release-artifact-manifest.v1"]
        assert "cleanmac.release-readiness.v1" in entries
        assert "json_schema" in entries["cleanmac.release-readiness.v1"]
        assert "cleanmac.release-diagnostics.v1" in entries
        assert "cleanmac.release-evidence.v1" in entries
        assert "cleanmac.release-operator-summary.v1" in entries
        assert "cleanmac.release-rehearsal.v1" in entries
        assert "cleanmac.release-promotion-decision.v1" in entries
        assert "cleanmac.release-rollback-plan.v1" in entries
        assert "cleanmac.release-post-publish-verification.v1" in entries
        assert "cleanmac.release-post-publish-evidence-input.v1" in entries
        assert "cleanmac.release-post-publish-evidence-template.v1" in entries
        assert "cleanmac.release-post-publish-result.v1" in entries
        assert "cleanmac.mcp-meta-index.v1" in entries
        assert "json_schema" in entries["cleanmac.mcp-meta-index.v1"]
        assert entries["cleanmac.mcp-meta-index.v1"]["producer_command"] == ["read", "cleanmac://mcp/meta-index"]
        assert "mcp" in entries["cleanmac.mcp-meta-index.v1"]["consumers"]
        assert entries["cleanmac.mcp-meta-index.v1"]["owner_area"] == "mcp"
        assert entries["cleanmac.mcp-meta-index.v1"]["release_critical"]
        assert "cleanmac.mcp-resource-index.v1" in entries
        assert "json_schema" in entries["cleanmac.mcp-resource-index.v1"]
        assert entries["cleanmac.mcp-resource-index.v1"]["producer_command"] == [
            "read",
            "cleanmac://mcp/resource-index",
        ]
        assert "mcp" in entries["cleanmac.mcp-resource-index.v1"]["consumers"]
        assert entries["cleanmac.mcp-resource-index.v1"]["owner_area"] == "mcp"
        assert entries["cleanmac.mcp-resource-index.v1"]["release_critical"]
        assert "cleanmac.mcp-prompt-index.v1" in entries
        assert "json_schema" in entries["cleanmac.mcp-prompt-index.v1"]
        assert entries["cleanmac.mcp-prompt-index.v1"]["producer_command"] == [
            "read",
            "cleanmac://mcp/prompt-index",
        ]
        assert "mcp" in entries["cleanmac.mcp-prompt-index.v1"]["consumers"]
        assert entries["cleanmac.mcp-prompt-index.v1"]["owner_area"] == "mcp"
        assert entries["cleanmac.mcp-prompt-index.v1"]["release_critical"]
        assert "cleanmac.mcp-tool-index.v1" in entries
        assert "json_schema" in entries["cleanmac.mcp-tool-index.v1"]
        assert entries["cleanmac.mcp-tool-index.v1"]["producer_command"] == ["read", "cleanmac://mcp/tool-index"]
        assert "tool-policy" in entries["cleanmac.mcp-tool-index.v1"]["consumers"]
        assert entries["cleanmac.mcp-tool-index.v1"]["owner_area"] == "mcp"
        assert entries["cleanmac.mcp-tool-index.v1"]["release_critical"]
        assert "cleanmac.mcp-destructive-tool-governance.v1" in entries
        assert "json_schema" in entries["cleanmac.mcp-destructive-tool-governance.v1"]
        assert entries["cleanmac.mcp-destructive-tool-governance.v1"]["producer_command"] == [
            "read",
            "cleanmac://mcp/destructive-tool-governance",
        ]
        assert "tool-policy" in entries["cleanmac.mcp-destructive-tool-governance.v1"]["consumers"]
        assert entries["cleanmac.mcp-destructive-tool-governance.v1"]["owner_area"] == "mcp"
        assert entries["cleanmac.mcp-destructive-tool-governance.v1"]["release_critical"]
        assert "cleanmac.operation-log-explainability.v1" in entries
        assert "json_schema" in entries["cleanmac.operation-log-explainability.v1"]
        assert entries["cleanmac.operation-log-explainability.v1"]["producer_command"] == [
            "cleanmac",
            "--json",
            "operation-log-explainability",
        ]
        assert "ai-host" in entries["cleanmac.operation-log-explainability.v1"]["consumers"]
        assert entries["cleanmac.operation-log-explainability.v1"]["owner_area"] == "execution"
        assert entries["cleanmac.operation-log-explainability.v1"]["release_critical"]
        assert "cleanmac.cold-start-budget.v1" in entries
        assert "json_schema" in entries["cleanmac.cold-start-budget.v1"]
        assert entries["cleanmac.cold-start-budget.v1"]["producer_command"] == [
            "cleanmac",
            "--json",
            "cold-start-budget",
        ]
        assert "ai-host" in entries["cleanmac.cold-start-budget.v1"]["consumers"]
        assert entries["cleanmac.cold-start-budget.v1"]["owner_area"] == "ai-host"
        assert entries["cleanmac.cold-start-budget.v1"]["release_critical"]
        assert "cleanmac.dependency-governance.v1" in entries
        assert "json_schema" in entries["cleanmac.dependency-governance.v1"]
        assert entries["cleanmac.dependency-governance.v1"]["producer_command"] == [
            "cleanmac",
            "--json",
            "dependency-governance",
        ]
        assert "ai-host" in entries["cleanmac.dependency-governance.v1"]["consumers"]
        assert entries["cleanmac.dependency-governance.v1"]["owner_area"] == "release"
        assert entries["cleanmac.dependency-governance.v1"]["release_critical"]
        assert "cleanmac.no-disturbance.v1" in entries
        assert "json_schema" in entries["cleanmac.no-disturbance.v1"]
        assert entries["cleanmac.no-disturbance.v1"]["producer_command"] == [
            "cleanmac",
            "--json",
            "no-disturbance",
        ]
        assert "ai-host" in entries["cleanmac.no-disturbance.v1"]["consumers"]
        assert entries["cleanmac.no-disturbance.v1"]["owner_area"] == "ai-host"
        assert entries["cleanmac.no-disturbance.v1"]["release_critical"]
        assert "cleanmac.mcp-surface-audit.v1" in entries
        assert "json_schema" in entries["cleanmac.mcp-surface-audit.v1"]
        assert entries["cleanmac.mcp-surface-audit.v1"]["producer_command"] == [
            "cleanmac",
            "--json",
            "mcp-surface-audit",
        ]
        assert "mcp" in entries["cleanmac.mcp-surface-audit.v1"]["consumers"]
        assert entries["cleanmac.mcp-surface-audit.v1"]["owner_area"] == "mcp"
        assert entries["cleanmac.mcp-surface-audit.v1"]["release_critical"]
        assert "json_schema" in entries["cleanmac.zero-resident.v1"]
        assert "json_schema" in entries["cleanmac.product-surface-drift-audit.v1"]
        assert entries["cleanmac.zero-resident.v1"]["release_critical"]
        assert entries["cleanmac.product-surface-drift-audit.v1"]["release_critical"]
        assert entries["cleanmac.xcode-ios-governance.v1"]["release_critical"]
        assert entries["cleanmac.release-evidence.v1"]["release_critical"]
        assert entries["cleanmac.release-promotion-decision.v1"]["release_critical"]
        assert entries["cleanmac.release-post-publish-verification.v1"]["release_critical"]
        assert entries["cleanmac.release-post-publish-evidence-input.v1"]["release_critical"]
        assert entries["cleanmac.release-post-publish-evidence-template.v1"]["release_critical"]
        assert entries["cleanmac.release-post-publish-result.v1"]["release_critical"]
        assert entries["cleanmac.release-evidence.v1"]["owner_area"] == "release"

    def test_contract_validator_covers_ai_host_critical_schema_shapes(self) -> None:
        from cleancli.ai_versioning import (
            AI_HOST_CRITICAL_SCHEMAS,
            CORE_CONTRACT_SCHEMAS,
            render_ai_contract_samples,
            validate_contract_payload,
        )

        assert set(AI_HOST_CRITICAL_SCHEMAS) <= set(CORE_CONTRACT_SCHEMAS)
        host_policy = {
            "schema": "cleanmac.ai-host-policy.v1",
            "valid": True,
            "default_decision": "deny",
            "auto_call": {
                "allow": [],
                "deny": ["cleanmac_execute_plan", "cleanmac_startup_disable", "cleanmac_privacy_execute"],
            },
            "execution_gate": {"auto_call_allowed": False},
        }
        assert validate_contract_payload("cleanmac.ai-host-policy.v1", host_policy)["valid"]

        missing_auto_call = dict(host_policy)
        del missing_auto_call["auto_call"]
        missing_report = validate_contract_payload("cleanmac.ai-host-policy.v1", missing_auto_call)
        assert not missing_report["valid"]
        assert missing_report["errors"][0]["code"] == "MISSING_REQUIRED_FIELD"

        wrong_schema = dict(host_policy)
        wrong_schema["schema"] = "cleanmac.ai-host-policy.v2"
        const_report = validate_contract_payload("cleanmac.ai-host-policy.v1", wrong_schema)
        assert not const_report["valid"]
        assert const_report["errors"][0]["code"] == "CONST_MISMATCH"

        governance_advice = {
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
        }
        assert validate_contract_payload("cleanmac.ai-governance-advice.v1", governance_advice)["valid"]

        eval_pack = {
            "schema": "cleanmac.ai-eval-pack.v1",
            "scenario_count": 1,
            "scenarios": [{"id": "discover_readiness"}],
            "allows_destructive_execution": False,
            "recommended_runner_command": ["cleanmac", "--json", "ai-eval-run", "--scenario", "smoke"],
        }
        assert validate_contract_payload("cleanmac.ai-eval-pack.v1", eval_pack)["valid"]

        eval_run = {
            "schema": "cleanmac.ai-eval-run.v1",
            "scenario": "smoke",
            "passed": True,
            "passed_count": 1,
            "failed_count": 0,
            "results": [{"id": "discover_readiness", "passed": True}],
        }
        assert validate_contract_payload("cleanmac.ai-eval-run.v1", eval_run)["valid"]

        release_readiness = {
            "schema": "cleanmac.release-readiness.v1",
            "destructive": False,
            "dry_run": True,
            "ready": True,
            "manual_review_required": False,
            "readiness_score": {"passed": 13, "total": 13, "level": "release-ready"},
            "failed_gate_ids": [],
            "gates": [
                {
                    "id": "ai-host-preflight-ready",
                    "passed": True,
                    "evidence_schema": "cleanmac.ai-host-preflight.v1",
                    "severity": "none",
                    "next_actions": [["make", "ai-host-smoke"]],
                },
                {
                    "id": "dependency-governance-ready",
                    "passed": True,
                    "evidence_schema": "cleanmac.dependency-governance.v1",
                    "severity": "none",
                    "next_actions": [["make", "dependency-audit-smoke"]],
                },
            ],
            "release_gate_commands": [["make", "ai-host-smoke"]],
            "review_questions": ["Did ai-host-preflight pass before tool orchestration?"],
        }
        assert validate_contract_payload("cleanmac.release-readiness.v1", release_readiness)["valid"]
        invalid_release_readiness = dict(release_readiness)
        invalid_release_readiness["gates"] = [{"id": "ai-host-preflight-ready", "passed": True}]
        invalid_gate_report = validate_contract_payload("cleanmac.release-readiness.v1", invalid_release_readiness)
        assert not invalid_gate_report["valid"]
        assert invalid_gate_report["errors"][0]["code"] == "MISSING_REQUIRED_FIELD"

        release_diagnostics = {
            "schema": "cleanmac.release-diagnostics.v1",
            "destructive": False,
            "dry_run": True,
            "ready": False,
            "failed_gate_ids": ["release-artifact-manifest-valid"],
            "environment": {"platform": "darwin"},
            "artifacts": {"error_code": "RELEASE_ARTIFACT_MANIFEST_MISSING"},
            "governance_integrity": {"schema": "cleanmac.governance-integrity.v1", "ready": True},
            "ai_first_release_checklist": {"schema": "cleanmac.ai-first-release-checklist.v1", "ready": True},
            "recommended_commands": [["make", "release-artifacts-smoke"]],
        }
        assert validate_contract_payload("cleanmac.release-diagnostics.v1", release_diagnostics)["valid"]

        release_evidence = {
            "schema": "cleanmac.release-evidence.v1",
            "destructive": False,
            "dry_run": True,
            "ready": True,
            "artifact_manifest": {"schema": "cleanmac.release-artifact-manifest.v1", "valid": True},
            "release_readiness": {"schema": "cleanmac.release-readiness.v1", "ready": True},
            "release_diagnostics": {"schema": "cleanmac.release-diagnostics.v1", "ready": True},
            "governance_integrity": {"schema": "cleanmac.governance-integrity.v1", "ready": True},
            "ai_first_release_checklist": {"schema": "cleanmac.ai-first-release-checklist.v1", "ready": True},
            "assets": {"required": ["SBOM.json"], "missing": []},
        }
        assert validate_contract_payload("cleanmac.release-evidence.v1", release_evidence)["valid"]

        release_rehearsal = {
            "schema": "cleanmac.release-rehearsal.v1",
            "destructive": False,
            "dry_run": True,
            "ready": False,
            "phases": [{"id": "artifact-manifest", "status": "blocked"}],
            "failed_phase_ids": ["artifact-manifest"],
            "recommended_commands": [["make", "release-rehearsal-smoke"]],
        }
        assert validate_contract_payload("cleanmac.release-rehearsal.v1", release_rehearsal)["valid"]

        promotion_decision = {
            "schema": "cleanmac.release-promotion-decision.v1",
            "destructive": False,
            "dry_run": True,
            "decision": "block",
            "ready": False,
            "safe_to_publish": False,
            "manual_review_required": True,
            "blocking_codes": ["RELEASE_ARTIFACT_MANIFEST_MISSING"],
            "required_evidence": ["ARTIFACT-MANIFEST.json"],
            "missing_evidence": ["ARTIFACT-MANIFEST.json"],
            "recommended_commands": [["make", "release-check"]],
        }
        assert validate_contract_payload("cleanmac.release-promotion-decision.v1", promotion_decision)["valid"]

        rollback_plan = {
            "schema": "cleanmac.release-rollback-plan.v1",
            "destructive": False,
            "dry_run": True,
            "manual_only": True,
            "rollback_surfaces": [{"id": "pypi"}],
            "pre_rollback_checks": [
                ["cleanmac", "--json", "governance-integrity"],
                ["cleanmac", "--json", "release-diagnostics"],
                ["make", "governance-integrity-smoke"],
            ],
        }
        assert validate_contract_payload("cleanmac.release-rollback-plan.v1", rollback_plan)["valid"]

        post_publish = {
            "schema": "cleanmac.release-post-publish-verification.v1",
            "destructive": False,
            "dry_run": True,
            "manual_only": True,
            "verification_surfaces": [{"id": "pypi"}],
            "required_evidence_after_publish": ["GitHub release asset list"],
            "incident_response_entrypoints": [["cleanmac", "--json", "release-rollback-plan"]],
            "recommended_commands": [["make", "release-post-publish-smoke"]],
        }
        assert validate_contract_payload("cleanmac.release-post-publish-verification.v1", post_publish)["valid"]

        post_publish_evidence_input = {
            "schema": "cleanmac.release-post-publish-evidence-input.v1",
            "surfaces": {
                "github-release": {"status": "verified", "evidence_refs": ["GitHub release asset list"]},
                "pypi": {"status": "verified", "evidence_refs": ["PyPI release page"]},
                "homebrew-tap": {"status": "verified", "evidence_refs": ["Tap formula commit"]},
            },
        }
        assert validate_contract_payload(
            "cleanmac.release-post-publish-evidence-input.v1", post_publish_evidence_input
        )["valid"]

        post_publish_evidence_template = {
            "schema": "cleanmac.release-post-publish-evidence-template.v1",
            "destructive": False,
            "dry_run": True,
            "manual_only": True,
            "target_input_schema": "cleanmac.release-post-publish-evidence-input.v1",
            "template": post_publish_evidence_input,
            "recommended_commands": [
                ["cleanmac", "--json", "release-post-publish-result", "--evidence-file", "post-publish-evidence.json"]
            ],
        }
        assert validate_contract_payload(
            "cleanmac.release-post-publish-evidence-template.v1", post_publish_evidence_template
        )["valid"]

        post_publish_result = {
            "schema": "cleanmac.release-post-publish-result.v1",
            "destructive": False,
            "dry_run": True,
            "manual_only": True,
            "ready": False,
            "surfaces": [{"id": "pypi", "status": "pending"}],
            "evidence_validation_errors": [],
            "failed_surface_ids": [],
            "pending_surface_ids": ["pypi"],
            "incident_response_entrypoints": [["cleanmac", "--json", "release-rollback-plan"]],
            "recommended_commands": [["make", "release-post-publish-result-smoke"]],
        }
        assert validate_contract_payload("cleanmac.release-post-publish-result.v1", post_publish_result)["valid"]

        mcp_meta_index = {
            "schema": "cleanmac.mcp-meta-index.v1",
            "destructive": False,
            "dry_run": True,
            "ready": True,
            "index_count": 4,
            "indexes": [
                {
                    "kind": "resource",
                    "uri": "cleanmac://mcp/resource-index",
                    "schema": "cleanmac.mcp-resource-index.v1",
                },
                {"kind": "prompt", "uri": "cleanmac://mcp/prompt-index", "schema": "cleanmac.mcp-prompt-index.v1"},
                {"kind": "tool", "uri": "cleanmac://mcp/tool-index", "schema": "cleanmac.mcp-tool-index.v1"},
                {
                    "kind": "destructive-tool-governance",
                    "uri": "cleanmac://mcp/destructive-tool-governance",
                    "schema": "cleanmac.mcp-destructive-tool-governance.v1",
                },
            ],
            "index_uris": [
                "cleanmac://mcp/resource-index",
                "cleanmac://mcp/prompt-index",
                "cleanmac://mcp/tool-index",
                "cleanmac://mcp/destructive-tool-governance",
            ],
        }
        assert validate_contract_payload("cleanmac.mcp-meta-index.v1", mcp_meta_index)["valid"]

        mcp_resource_index = {
            "schema": "cleanmac.mcp-resource-index.v1",
            "destructive": False,
            "dry_run": True,
            "ready": True,
            "resource_count": 1,
            "resources": [{"uri": "cleanmac://mcp/resource-index", "safe_for_mcp": True}],
            "resource_uris": ["cleanmac://mcp/resource-index"],
        }
        assert validate_contract_payload("cleanmac.mcp-resource-index.v1", mcp_resource_index)["valid"]

        mcp_prompt_index = {
            "schema": "cleanmac.mcp-prompt-index.v1",
            "destructive": False,
            "dry_run": True,
            "ready": True,
            "prompt_count": 1,
            "prompts": [{"name": "review-ai-host-policy", "safe_for_mcp": True}],
            "prompt_names": ["review-ai-host-policy"],
        }
        assert validate_contract_payload("cleanmac.mcp-prompt-index.v1", mcp_prompt_index)["valid"]

        mcp_tool_index = {
            "schema": "cleanmac.mcp-tool-index.v1",
            "destructive": False,
            "dry_run": True,
            "ready": True,
            "tool_count": 1,
            "tools": [{"name": "cleanmac_execute_plan", "safe_for_mcp": True}],
            "tool_names": ["cleanmac_execute_plan"],
        }
        assert validate_contract_payload("cleanmac.mcp-tool-index.v1", mcp_tool_index)["valid"]

        mcp_surface_audit = {
            "schema": "cleanmac.mcp-surface-audit.v1",
            "destructive": False,
            "dry_run": True,
            "ready": True,
            "resource_uri": "cleanmac://mcp/surface-audit",
            "checks": [{"id": "mcp-meta-index-ready", "passed": True, "evidence": "cleanmac.mcp-meta-index.v1"}],
            "missing": {"resources": [], "prompts": [], "tools": []},
            "failed_check_ids": [],
            "readiness_score": {"passed": 1, "total": 1, "level": "ready"},
            "next_action": "proceed-to-host-integration-pack",
            "stop_reason": "",
            "remediation_commands": [["make", "mcp-surface-audit-smoke"]],
        }
        assert validate_contract_payload("cleanmac.mcp-surface-audit.v1", mcp_surface_audit)["valid"]

        blocked_mcp_surface_audit = dict(mcp_surface_audit)
        blocked_mcp_surface_audit.update(
            {
                "ready": False,
                "checks": [
                    {
                        "id": "required-tools-advertised",
                        "passed": False,
                        "evidence": "cleanmac.mcp-tool-index.v1",
                        "remediation_commands": [["make", "mcp-tool-index-smoke"]],
                    }
                ],
                "missing": {"resources": [], "prompts": [], "tools": ["cleanmac_execute_plan"]},
                "failed_check_ids": ["required-tools-advertised"],
                "readiness_score": {"passed": 12, "total": 13, "level": "blocked"},
                "next_action": "stop-and-remediate-mcp-surface",
                "stop_reason": "mcp-surface-audit failed: required-tools-advertised",
                "remediation_commands": [["make", "mcp-surface-audit-smoke"]],
            }
        )
        assert validate_contract_payload("cleanmac.mcp-surface-audit.v1", blocked_mcp_surface_audit)["valid"]

        zero_resident_contract = {
            "schema": "cleanmac.zero-resident.v1",
            "destructive": False,
            "dry_run": True,
            "ready": True,
            "resident_processes_expected": 0,
            "background_cpu_expected": 0,
            "background_memory_expected": 0,
            "login_items_created": False,
            "launch_agents_created": False,
            "launch_daemons_created": False,
            "auto_scan_enabled": False,
            "implements_tui": False,
            "implements_gui": False,
            "lifecycle": "single-shot",
            "evidence": {"resident_processes": 0, "lifecycle": "single-shot"},
            "failed_fields": [],
            "release_gate_commands": [["cleanmac", "--json", "zero-resident"]],
        }
        assert validate_contract_payload("cleanmac.zero-resident.v1", zero_resident_contract)["valid"]
        invalid_zero_resident_contract = dict(zero_resident_contract)
        invalid_zero_resident_contract["lifecycle"] = "resident"
        assert not validate_contract_payload("cleanmac.zero-resident.v1", invalid_zero_resident_contract)["valid"]

        product_surface_drift_audit = {
            "schema": "cleanmac.product-surface-drift-audit.v1",
            "destructive": False,
            "dry_run": True,
            "ready": True,
            "scan_scope": "forbidden GUI/TUI dependencies and resident product surfaces",
            "forbidden_dependency_families": ["Textual", "PyQt", "rumps"],
            "violation_count": 0,
            "violations": [],
            "failed_check_ids": [],
            "release_gate_commands": [["cleanmac", "--json", "product-surface-drift-audit"]],
        }
        assert validate_contract_payload("cleanmac.product-surface-drift-audit.v1", product_surface_drift_audit)[
            "valid"
        ]

        governance_integrity = {
            "schema": "cleanmac.governance-integrity.v1",
            "destructive": False,
            "dry_run": True,
            "ready": True,
            "failed_check_ids": [],
            "stop_reason": "",
            "next_action": "Run make governance-integrity-smoke before release readiness.",
            "remediation_commands": [["make", "governance-integrity-smoke"]],
            "readiness_score": {"passed": 1, "total": 1, "level": "ready"},
            "checks": [
                {
                    "id": "boundary-runtime-lifecycle-single-source",
                    "passed": True,
                    "remediation_commands": [["make", "governance-integrity-smoke"]],
                }
            ],
            "governed_contracts": ["cleanmac.geo-discoverability-policy.v1"],
            "release_gate_commands": [["make", "governance-integrity-smoke"]],
            "review_questions": ["Do all public positioning fields reuse the centralized GEO policy?"],
        }
        assert validate_contract_payload("cleanmac.governance-integrity.v1", governance_integrity)["valid"]

        invalid_governance_integrity = dict(governance_integrity)
        del invalid_governance_integrity["remediation_commands"]
        invalid_governance_report = validate_contract_payload(
            "cleanmac.governance-integrity.v1", invalid_governance_integrity
        )
        assert not invalid_governance_report["valid"]
        assert invalid_governance_report["errors"][0]["code"] == "MISSING_REQUIRED_FIELD"

        development_governance_todo = {
            "schema": "cleanmac.development-governance-todo.v1",
            "destructive": False,
            "dry_run": True,
            "purpose": "Ordered governance backlog.",
            "ordered": True,
            "item_count": 25,
            "landed_count": 25,
            "pending_count": 0,
            "status": "landed",
            "execution_policy": "Every item is implemented as release-gated evidence.",
            "items": [
                {
                    "order": 1,
                    "id": "strengthen-ai-first-entrypoints",
                    "title": "Strengthen AI-first entrypoints",
                    "governance_action": "Keep AI entrypoints primary.",
                    "status": "landed",
                    "verification_command": ["cleanmac", "--json", "capabilities"],
                    "landing_evidence": {
                        "state": "landed",
                        "evidence_refs": ["cleanmac.capabilities.v1"],
                        "release_gated": True,
                    },
                }
            ],
            "release_gate_commands": [["make", "governance-smoke"]],
        }
        assert validate_contract_payload("cleanmac.development-governance-todo.v1", development_governance_todo)[
            "valid"
        ]
        software_discovery_evidence = {
            "schema": "cleanmac.software-discovery-evidence.v1",
            "app_identity": {
                "name": "Example.app",
                "display_name": "Example",
                "bundle_id": "com.example.app",
                "path": "/Applications/Example.app",
                "protected_from_uninstall": False,
            },
            "candidate_id": "cache:/Users/tester/Library/Caches/com.example.app",
            "candidate_path": "/Users/tester/Library/Caches/com.example.app",
            "path_role": "cache",
            "match_source": "bundle-id",
            "matched_rule": "software-uninstall.cache.bundle-id",
            "installed_app_present": True,
            "deletion_eligibility": {
                "delete_mode": "trash",
                "safe_to_auto_execute": False,
                "requires_review_selection": True,
                "default_selected": True,
                "protected": False,
                "why_not_default": None,
            },
        }
        assert validate_contract_payload(
            "cleanmac.software-discovery-evidence.v1", software_discovery_evidence
        )["valid"]

        samples = render_ai_contract_samples()
        assert samples["schema"] == "cleanmac.ai-contract-samples.v1"
        assert samples["sample_count"] == len(samples["samples"])
        assert {sample["target_schema"] for sample in samples["samples"]} == set(AI_HOST_CRITICAL_SCHEMAS)
        sample_payloads = {sample["target_schema"]: sample["payload"] for sample in samples["samples"]}
        assert sample_payloads["cleanmac.zero-resident.v1"]["lifecycle"] == "single-shot"
        assert sample_payloads["cleanmac.product-surface-drift-audit.v1"]["violation_count"] == 0
        assert sample_payloads["cleanmac.dependency-governance.v1"]["pyproject"]["runtime_dependency_count"] == 0
        assert sample_payloads["cleanmac.release-readiness.v1"]["readiness_score"] == {
            "passed": 13,
            "total": 13,
            "level": "release-ready",
        }
        assert "dependency-governance-ready" in {
            gate["id"] for gate in sample_payloads["cleanmac.release-readiness.v1"]["gates"]
        }
        assert sample_payloads["cleanmac.development-governance-todo.v1"]["item_count"] == 25
        assert sample_payloads["cleanmac.development-governance-todo.v1"]["landed_count"] == 25
        assert sample_payloads["cleanmac.development-governance-todo.v1"]["pending_count"] == 0
        assert sample_payloads["cleanmac.development-governance-todo.v1"]["status"] == "landed"
        assert sample_payloads["cleanmac.software-discovery-governance.v1"]["ready"] is True
        assert sample_payloads["cleanmac.software-discovery-governance.v1"]["landed_backlog_item_ids"] == [
            "p0-software-leftover-discovery",
            "p0-software-orphan-scan",
        ]
        assert sample_payloads["cleanmac.xcode-ios-governance.v1"]["ready"] is True
        assert sample_payloads["cleanmac.xcode-ios-governance.v1"]["in_progress_backlog_item_ids"] == [
            "p0-xcode-ios-deep-cleanup"
        ]
        assert sample_payloads["cleanmac.xcode-ios-governance.v1"]["destructive_paths_absent"] is True
        assert (
            sample_payloads["cleanmac.development-governance-todo.v1"]["items"][0]["id"]
            == "strengthen-ai-first-entrypoints"
        )
        assert sample_payloads["cleanmac.development-governance-todo.v1"]["items"][0]["landing_evidence"][
            "release_gated"
        ]
        for sample in samples["samples"]:
            assert sample["valid"], sample
            validation = validate_contract_payload(sample["target_schema"], sample["payload"])
            assert validation["valid"], validation

    def test_contract_validator_reports_valid_missing_and_unsupported_payloads(self) -> None:
        from cleancli.ai_versioning import render_ai_contract_validation_summary, validate_contract_payload

        valid_plan = {
            "schema": "cleanmac.plan.v1",
            "destructive": False,
            "dry_run": True,
            "generated_at": "2026-06-19T00:00:00+00:00",
            "expires_at": "2026-06-19T00:30:00+00:00",
            "selected_category_keys": ["trash"],
            "candidate_fingerprints": [{"path": "/tmp/old.tmp", "exists": True}],
        }
        assert validate_contract_payload("cleanmac.plan.v1", valid_plan)["valid"]

        missing_required = dict(valid_plan)
        del missing_required["candidate_fingerprints"]
        missing_report = validate_contract_payload("cleanmac.plan.v1", missing_required)
        assert not missing_report["valid"]
        assert missing_report["errors"][0]["code"] == "MISSING_REQUIRED_FIELD"

        unsupported_report = validate_contract_payload("cleanmac.plan." + "v99", valid_plan)
        assert not unsupported_report["valid"]
        assert unsupported_report["errors"][0]["code"] == "UNSUPPORTED_SCHEMA"

        summary = render_ai_contract_validation_summary()
        assert summary["schema"] == "cleanmac.ai-contract-validation-summary.v1"
        assert summary["valid"], summary
        assert summary["failure_count"] == 0
        coverage = summary["contract_schema_coverage"]
        assert coverage["missing_stable_ai_schema_fragments"] == []
        assert coverage["json_schema_fragment_count"] >= len(coverage["critical_schemas"])

    def test_operational_plan_samples_expose_current_execute_gate_name(self) -> None:
        from cleancli.ai_versioning import render_ai_contract_samples, validate_contract_payload

        payloads = {sample["target_schema"]: sample["payload"] for sample in render_ai_contract_samples()["samples"]}
        startup = payloads["cleanmac.startup-plan.v1"]
        privacy = payloads["cleanmac.privacy-plan.v1"]
        assert startup["disable_plan"]["requires_explicit_execute"]
        assert privacy["privacy_plan"]["requires_explicit_execute"]
        assert startup["disable_plan"]["requires_explicit_future_execute"]
        assert privacy["privacy_plan"]["requires_explicit_future_execute"]
        assert validate_contract_payload("cleanmac.startup-plan.v1", startup)["valid"]
        assert validate_contract_payload("cleanmac.privacy-plan.v1", privacy)["valid"]

    def test_contract_validator_reports_nested_array_item_type_mismatch(self) -> None:
        from cleancli.ai_versioning import validate_contract_payload

        payload = {
            "schema": "cleanmac.ai-contract-samples.v1",
            "destructive": False,
            "dry_run": True,
            "sample_count": 1,
            "samples": ["not-an-object"],
        }

        report = validate_contract_payload("cleanmac.ai-contract-samples.v1", payload)

        assert not report["valid"]
        assert report["error_count"] == 1
        assert report["errors"][0]["code"] == "TYPE_MISMATCH"
        assert report["errors"][0]["path"] == "$.samples[0]"

    def test_contract_validator_rejects_boolean_for_integer(self) -> None:
        from cleancli.ai_versioning import validate_contract_payload

        payload = {
            "schema": "cleanmac.ai-contract-samples.v1",
            "destructive": False,
            "dry_run": True,
            "sample_count": True,
            "samples": [],
        }

        report = validate_contract_payload("cleanmac.ai-contract-samples.v1", payload)

        assert not report["valid"]
        assert report["error_count"] == 1
        assert report["errors"][0]["code"] == "TYPE_MISMATCH"
        assert report["errors"][0]["path"] == "$.sample_count"

    def test_contract_validator_reports_const_mismatch_before_type_walk(self) -> None:
        from cleancli.ai_versioning import validate_contract_payload

        payload = {
            "schema": "cleanmac.ai-contract-samples.v2",
            "destructive": False,
            "dry_run": True,
            "sample_count": 0,
            "samples": [],
        }

        report = validate_contract_payload("cleanmac.ai-contract-samples.v1", payload)

        assert not report["valid"]
        assert report["error_count"] == 1
        assert report["errors"][0]["code"] == "CONST_MISMATCH"
        assert report["errors"][0]["path"] == "$.schema"

    def test_plan_schema_negotiation_accepts_only_supported_schema_versions(self) -> None:
        from cleancli.ai_versioning import negotiate_plan_schema

        assert negotiate_plan_schema({"schema": "cleanmac.plan.v1"}) == {
            "accepted": True,
            "schema": "cleanmac.plan.v1",
            "reason": "supported",
            "latest_supported_schema": "cleanmac.plan.v1",
            "legacy": False,
        }
        assert negotiate_plan_schema({}) == {
            "accepted": False,
            "schema": "",
            "reason": "missing-schema-field",
            "latest_supported_schema": "cleanmac.plan.v1",
            "legacy": False,
        }
        assert negotiate_plan_schema({}, allow_legacy_missing=True) == {
            "accepted": True,
            "schema": "",
            "reason": "legacy-missing-schema-field",
            "latest_supported_schema": "cleanmac.plan.v1",
            "legacy": True,
        }
        assert negotiate_plan_schema({"schema": "cleanmac.clean-plan.v1"}) == {
            "accepted": True,
            "schema": "cleanmac.clean-plan.v1",
            "reason": "supported",
            "latest_supported_schema": "cleanmac.plan.v1",
            "legacy": True,
        }
        assert negotiate_plan_schema({"schema": "cleanmac.clean-plan.v2"}) == {
            "accepted": False,
            "schema": "cleanmac.clean-plan.v2",
            "reason": "unsupported-schema-version",
            "latest_supported_schema": "cleanmac.plan.v1",
            "legacy": False,
        }
