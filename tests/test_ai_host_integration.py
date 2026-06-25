from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from cleancli.ai_versioning import AI_HOST_CRITICAL_SCHEMAS, validate_contract_payload
from cleancli.core import (
    render_ai_host_evidence_report,
    render_ai_host_integration_pack_report,
    render_ai_host_preflight_report,
)

PROJECT_ROOT = Path(__file__).resolve().parent.parent
CLI = PROJECT_ROOT / "cleanmac.py"


def test_pack_aggregates_one_stop_host_discovery_metadata() -> None:
    pack = render_ai_host_integration_pack_report()

    assert pack["schema"] == "cleanmac.ai-host-integration-pack.v1"
    assert pack["destructive"] is False
    assert pack["dry_run"] is True
    assert pack["ready"] is True
    assert pack["schema_registry"]["schema"] == "cleanmac.ai-schema-registry.v1"
    assert pack["readiness"]["schema"] == "cleanmac.ai-readiness.v1"
    assert pack["runbook"]["schema"] == "cleanmac.ai-runbook.v1"
    assert pack["host_policy"]["schema"] == "cleanmac.ai-host-policy.v1"
    assert pack["entrypoint_contract"]["schema"] == "cleanmac.ai-entrypoint-contract.v1"
    assert pack["entrypoint_contract"]["ready"] is True, pack["entrypoint_contract"]
    assert pack["entrypoint_contract"]["entrypoint_count"] == 6
    assert pack["safety_chain"]["schema"] == "cleanmac.ai-safety-chain.v1"
    assert pack["safety_chain"]["ready"] is True, pack["safety_chain"]
    assert pack["safety_chain"]["chain_step_count"] == 6
    assert pack["safety_chain"]["execute_gate"]["auto_call_allowed"] is False
    assert pack["candidate_evidence_chain"] == pack["safety_chain"]["candidate_evidence_chain"]
    assert pack["candidate_evidence_chain"]["schema"] == "cleanmac.candidate-review-evidence.v1"
    assert pack["candidate_evidence_chain"]["fail_closed_if_missing"] is True
    assert (
        "review_selection_constraint.selected_review_evidence[]"
        in pack["candidate_evidence_chain"]["required_artifact_paths"]
    )
    assert "operation_log.ai.candidate_review_evidence" in pack["candidate_evidence_chain"]["required_artifact_paths"]
    assert pack["host_evidence_requirements"]["candidate_evidence_chain_ready"] is True
    assert (
        pack["host_evidence_requirements"]["candidate_evidence_chain_schema"] == "cleanmac.candidate-review-evidence.v1"
    )
    assert pack["operation_log_explainability"]["schema"] == "cleanmac.operation-log-explainability.v1"
    assert pack["operation_log_explainability"]["ready"] is True, pack["operation_log_explainability"]
    assert pack["cold_start_budget"]["schema"] == "cleanmac.cold-start-budget.v1"
    assert pack["cold_start_budget"]["ready"] is True, pack["cold_start_budget"]
    assert pack["cold_start_budget"]["budgets"]["resident_processes_after_exit"] == 0
    assert pack["no_disturbance"]["schema"] == "cleanmac.no-disturbance.v1"
    assert pack["no_disturbance"]["ready"] is True, pack["no_disturbance"]
    assert pack["no_disturbance"]["silent_by_default"] is True
    assert pack["no_disturbance"]["sends_notifications"] is False
    assert pack["runtime_lifecycle"]["schema"] == "cleanmac.runtime-lifecycle-policy.v1"
    assert pack["runtime_lifecycle"]["product_model"] == "ai-first-ephemeral-cli"
    assert pack["runtime_lifecycle"]["resident_processes"] == 0
    assert pack["zero_resident_audit"]["schema"] == "cleanmac.zero-resident-audit.v1"
    assert pack["zero_resident_audit"]["ready"] is True, pack["zero_resident_audit"]
    assert pack["zero_resident_audit"]["resident_processes"] == 0
    assert pack["governance_advice"]["schema"] == "cleanmac.ai-governance-advice.v1"
    assert pack["eval_pack"]["schema"] == "cleanmac.ai-eval-pack.v1"
    assert pack["contract_validation"]["schema"] == "cleanmac.ai-contract-validation-summary.v1"
    assert pack["contract_samples"]["schema"] == "cleanmac.ai-contract-samples.v1"
    assert pack["release_readiness"]["schema"] == "cleanmac.release-readiness.v1"
    assert "failed_gate_ids" in pack["release_readiness"]
    assert pack["release_readiness"]["required_for"] == "release-review"
    assert pack["release_readiness"]["not_required_for"] == "runtime-readonly-ai-host-discovery"
    assert pack["readiness"]["release_readiness"] == pack["release_readiness"]

    assert "cleanmac.ai-host-integration-pack.v1" in AI_HOST_CRITICAL_SCHEMAS
    assert "cleanmac.ai-host-integration-pack.v1" in pack["critical_schemas"]
    assert ["cleanmac", "--json", "ai-host-integration-pack"] in pack["recommended_preflight_commands"]
    assert "cleanmac://ai/host-integration-pack" in pack["mcp"]["resources"]
    assert "cleanmac://ai/runtime-lifecycle-policy" in pack["mcp"]["resources"]
    assert "cleanmac://ai/zero-resident-audit" in pack["mcp"]["resources"]
    assert "cleanmac://ai/host-evidence" in pack["mcp"]["resources"]
    assert "cleanmac://release/readiness" in pack["mcp"]["resources"]
    assert "cleanmac://release/diagnostics" in pack["mcp"]["resources"]
    assert "cleanmac://release/evidence" in pack["mcp"]["resources"]
    assert "cleanmac://release/operator-summary" in pack["mcp"]["resources"]
    assert "cleanmac://release/rehearsal" in pack["mcp"]["resources"]
    assert "cleanmac://release/promotion-decision" in pack["mcp"]["resources"]
    assert "cleanmac://release/rollback-plan" in pack["mcp"]["resources"]
    assert "cleanmac://release/post-publish-verification" in pack["mcp"]["resources"]
    assert "cleanmac://release/post-publish-result" in pack["mcp"]["resources"]
    assert "cleanmac://release/post-publish-evidence-template" in pack["mcp"]["resources"]
    assert "cleanmac://mcp/meta-index" in pack["mcp"]["resources"]
    assert "cleanmac://mcp/resource-index" in pack["mcp"]["resources"]
    assert "cleanmac://mcp/prompt-index" in pack["mcp"]["resources"]
    assert "cleanmac://mcp/tool-index" in pack["mcp"]["resources"]
    assert "cleanmac://mcp/destructive-tool-governance" in pack["mcp"]["resources"]
    assert "cleanmac://ai/operation-log-explainability" in pack["mcp"]["resources"]
    assert "cleanmac://ai/cold-start-budget" in pack["mcp"]["resources"]
    assert "cleanmac://ai/no-disturbance" in pack["mcp"]["resources"]
    assert "cleanmac://release/dependency-governance" in pack["mcp"]["resources"]
    assert "cleanmac://mcp/surface-audit" in pack["mcp"]["resources"]
    assert "cleanmac://ai/entrypoints" in pack["mcp"]["resources"]
    assert "cleanmac://ai/safety-chain" in pack["mcp"]["resources"]
    assert pack["mcp"]["meta_index_uri"] == "cleanmac://mcp/meta-index"
    assert pack["mcp"]["prompt_index_uri"] == "cleanmac://mcp/prompt-index"
    assert pack["mcp"]["tool_index_uri"] == "cleanmac://mcp/tool-index"
    assert pack["mcp"]["destructive_tool_governance_uri"] == "cleanmac://mcp/destructive-tool-governance"
    assert pack["mcp"]["operation_log_explainability_uri"] == "cleanmac://ai/operation-log-explainability"
    assert pack["mcp"]["cold_start_budget_uri"] == "cleanmac://ai/cold-start-budget"
    assert pack["mcp"]["no_disturbance_uri"] == "cleanmac://ai/no-disturbance"
    assert pack["mcp"]["dependency_governance_uri"] == "cleanmac://release/dependency-governance"
    assert pack["mcp"]["surface_audit_uri"] == "cleanmac://mcp/surface-audit"
    assert "cleanmac://ai/workflow-contract" in pack["mcp"]["resources"]
    assert pack["host_evidence_requirements"]["candidate_evidence_chain_ready"] is True
    assert "review-ai-host-policy" in pack["mcp"]["prompts"]
    assert "cleanmac_execute_plan" in pack["mcp"]["tools"]
    assert pack["recommended_call_sequence"][0] == "read cleanmac://mcp/meta-index"
    assert pack["recommended_call_sequence"][1] == "read cleanmac://mcp/resource-index"
    assert pack["recommended_call_sequence"][2] == "read cleanmac://mcp/prompt-index"
    assert pack["recommended_call_sequence"][3] == "read cleanmac://mcp/tool-index"
    assert pack["recommended_call_sequence"][4] == "read cleanmac://mcp/destructive-tool-governance"
    assert pack["recommended_call_sequence"][5] == "read cleanmac://ai/operation-log-explainability"
    assert pack["recommended_call_sequence"][6] == "read cleanmac://ai/cold-start-budget"
    assert pack["recommended_call_sequence"][7] == "read cleanmac://ai/no-disturbance"
    assert pack["recommended_call_sequence"][8] == "read cleanmac://release/dependency-governance"
    assert pack["recommended_call_sequence"][9] == "read cleanmac://mcp/surface-audit"
    assert pack["recommended_call_sequence"][10] == "read cleanmac://ai/host-integration-pack"
    assert pack["recommended_call_sequence"][11] == "read cleanmac://ai/entrypoints"
    assert pack["recommended_call_sequence"][12] == "read cleanmac://ai/safety-chain"
    assert pack["recommended_call_sequence"][13] == "read cleanmac://ai/workflow-contract"
    assert len(pack["recommended_call_sequence"]) == len(set(pack["recommended_call_sequence"]))
    assert "read cleanmac://ai/workflow-contract" in pack["recommended_call_sequence"]
    assert "read cleanmac://ai/entrypoints" in pack["recommended_call_sequence"]
    assert "read cleanmac://ai/safety-chain" in pack["recommended_call_sequence"]
    assert "read cleanmac://mcp/destructive-tool-governance" in pack["recommended_call_sequence"]
    assert "read cleanmac://ai/operation-log-explainability" in pack["recommended_call_sequence"]
    assert "read cleanmac://ai/cold-start-budget" in pack["recommended_call_sequence"]
    assert "read cleanmac://ai/no-disturbance" in pack["recommended_call_sequence"]
    assert "read cleanmac://release/dependency-governance" in pack["recommended_call_sequence"]
    assert "read cleanmac://ai/runtime-lifecycle-policy" in pack["recommended_call_sequence"]
    assert "read cleanmac://ai/zero-resident-audit" in pack["recommended_call_sequence"]
    assert "read cleanmac://ai/host-integration-pack" in pack["recommended_call_sequence"]


def test_pack_validates_against_registered_contract_schema() -> None:
    pack = render_ai_host_integration_pack_report()

    validation = validate_contract_payload("cleanmac.ai-host-integration-pack.v1", pack)

    assert validation["valid"] is True, validation
    assert validation["error_count"] == 0


def test_cli_emits_host_integration_pack() -> None:
    result = subprocess.run(
        [sys.executable, str(CLI), "--json", "ai-host-integration-pack"],
        text=True,
        capture_output=True,
        check=True,
    )
    pack = json.loads(result.stdout)

    assert pack["schema"] == "cleanmac.ai-host-integration-pack.v1"
    assert pack["ready"] is True
    assert pack["mcp"]["resource_uri"] == "cleanmac://ai/host-integration-pack"
    assert pack["mcp"]["meta_index_uri"] == "cleanmac://mcp/meta-index"
    assert pack["mcp"]["prompt_index_uri"] == "cleanmac://mcp/prompt-index"
    assert pack["mcp"]["tool_index_uri"] == "cleanmac://mcp/tool-index"
    assert pack["mcp"]["destructive_tool_governance_uri"] == "cleanmac://mcp/destructive-tool-governance"
    assert pack["mcp"]["operation_log_explainability_uri"] == "cleanmac://ai/operation-log-explainability"
    assert pack["mcp"]["cold_start_budget_uri"] == "cleanmac://ai/cold-start-budget"
    assert pack["mcp"]["no_disturbance_uri"] == "cleanmac://ai/no-disturbance"
    assert pack["mcp"]["dependency_governance_uri"] == "cleanmac://release/dependency-governance"
    assert pack["mcp"]["surface_audit_uri"] == "cleanmac://mcp/surface-audit"
    assert "cleanmac://ai/workflow-contract" in pack["mcp"]["resources"]
    assert "cleanmac://ai/entrypoints" in pack["mcp"]["resources"]
    assert "cleanmac://ai/safety-chain" in pack["mcp"]["resources"]
    assert "cleanmac://mcp/destructive-tool-governance" in pack["mcp"]["resources"]
    assert "cleanmac://ai/operation-log-explainability" in pack["mcp"]["resources"]
    assert "cleanmac://ai/cold-start-budget" in pack["mcp"]["resources"]
    assert "cleanmac://ai/no-disturbance" in pack["mcp"]["resources"]
    assert "cleanmac://release/dependency-governance" in pack["mcp"]["resources"]
    assert "cleanmac://ai/zero-resident-audit" in pack["mcp"]["resources"]


def test_readiness_and_governance_recommend_integration_pack_entrypoint() -> None:
    pack = render_ai_host_integration_pack_report()
    readiness = pack["readiness"]
    governance = pack["governance_advice"]

    assert ["cleanmac", "--json", "ai-host-integration-pack"] in readiness["recommended_preflight_commands"]
    assert ["cleanmac", "--json", "ai-host-preflight"] in readiness["recommended_preflight_commands"]
    assert ["cleanmac", "--json", "ai-host-evidence"] in readiness["recommended_preflight_commands"]
    assert ["cleanmac", "--json", "release-readiness"] in pack["recommended_preflight_commands"]
    assert ["cleanmac", "--json", "ai-host-integration-pack"] in governance["release_gate_commands"]
    assert ["cleanmac", "--json", "ai-host-preflight"] in governance["release_gate_commands"]
    assert ["cleanmac", "--json", "ai-host-evidence"] in governance["release_gate_commands"]
    assert ["cleanmac", "--json", "release-readiness"] in governance["release_gate_commands"]
    assert governance["recommended_call_sequence"][0] == "read cleanmac://ai/host-integration-pack"
    assert governance["recommended_call_sequence"][1] == "read cleanmac://mcp/surface-audit"
    assert governance["recommended_call_sequence"][2] == "read cleanmac://ai/host-preflight"
    assert governance["recommended_call_sequence"][3] == "read cleanmac://ai/host-evidence"
    assert governance["recommended_call_sequence"][4] == "read cleanmac://release/readiness"


def test_evidence_reports_runtime_governance_audit_pack() -> None:
    evidence = render_ai_host_evidence_report()

    assert evidence["schema"] == "cleanmac.ai-host-evidence.v1"
    assert evidence["destructive"] is False
    assert evidence["dry_run"] is True
    assert evidence["ready"] is True, evidence
    assert "RAW_COMMAND_ARGUMENT_DENIED" in evidence["observed_blocking_codes"]
    assert "CONFIRMATION_TOKEN_REQUIRED" in evidence["observed_blocking_codes"]
    checks = {check["id"]: check for check in evidence["evidence_checks"]}
    assert checks["release-readiness-resource-advertised"]["passed"] is True
    assert checks["mcp-surface-audit-advertised"]["passed"] is True
    assert checks["mcp-surface-audit-ready"]["passed"] is True
    assert checks["zero-resident-audit-advertised"]["passed"] is True
    assert checks["zero-resident-audit-ready"]["passed"] is True
    assert checks["candidate-evidence-chain-exposed"]["passed"] is True
    assert checks["candidate-evidence-chain-preflight-gated"]["passed"] is True
    assert checks["candidate-evidence-chain-release-gated"]["passed"] is True
    assert evidence["candidate_evidence_chain"]["schema"] == "cleanmac.candidate-review-evidence.v1"
    assert (
        "operation_log.ai.candidate_review_evidence" in evidence["candidate_evidence_chain"]["required_artifact_paths"]
    )
    assert evidence["mcp_surface_audit"]["schema"] == "cleanmac.mcp-surface-audit.v1"
    assert evidence["mcp_surface_audit"]["ready"] is True, evidence["mcp_surface_audit"]
    assert evidence["zero_resident_audit"]["schema"] == "cleanmac.zero-resident-audit.v1"
    assert evidence["zero_resident_audit"]["ready"] is True, evidence["zero_resident_audit"]
    assert checks["no-disturbance-advertised"]["passed"] is True
    assert checks["no-disturbance-ready"]["passed"] is True
    assert evidence["no_disturbance"]["schema"] == "cleanmac.no-disturbance.v1"
    assert evidence["no_disturbance"]["ready"] is True, evidence["no_disturbance"]
    assert ["make", "release-readiness-smoke"] in evidence["release_gate_commands"]


def test_host_facing_reports_share_candidate_evidence_readiness_contract() -> None:
    pack = render_ai_host_integration_pack_report()
    preflight = render_ai_host_preflight_report()
    evidence = render_ai_host_evidence_report()

    candidate_chain = pack["candidate_evidence_chain"]
    required_paths = set(candidate_chain["required_artifact_paths"])
    preflight_checks = {check["id"]: check for check in preflight["checks"]}
    evidence_checks = {check["id"]: check for check in evidence["evidence_checks"]}

    assert candidate_chain == pack["safety_chain"]["candidate_evidence_chain"]
    assert candidate_chain == evidence["candidate_evidence_chain"]
    assert pack["host_evidence_requirements"] == evidence["host_evidence_requirements"]
    assert pack["host_evidence_requirements"]["candidate_evidence_chain_ready"] is True
    assert pack["host_evidence_requirements"]["source_resource"] == "cleanmac://ai/safety-chain"
    assert preflight["entrypoint"]["candidate_evidence_chain_resource"] == "cleanmac://ai/safety-chain"
    assert required_paths >= {
        "review_selection_constraint.selected_review_evidence[]",
        "dry_run_report.items[].review_evidence",
        "execute_report.items[].review_evidence",
        "operation_log.ai.candidate_review_evidence",
    }
    assert preflight_checks["candidate-evidence-chain-ready"]["passed"] is True
    assert preflight_checks["candidate-evidence-chain-ready"]["evidence"] == "cleanmac.candidate-review-evidence.v1"
    assert "candidate_evidence_chain_ready" in preflight["required_before_destructive_tool"]
    assert evidence_checks["candidate-evidence-chain-exposed"]["passed"] is True
    assert evidence_checks["candidate-evidence-chain-preflight-gated"]["passed"] is True
    assert evidence_checks["candidate-evidence-chain-release-gated"]["passed"] is True
    assert pack["host_evidence_requirements"]["release_gate"] in preflight["release_gate_commands"]
    assert pack["host_evidence_requirements"]["release_gate"] in evidence["release_gate_commands"]


def test_preflight_reports_runtime_governance_gate() -> None:
    preflight = render_ai_host_preflight_report()

    assert preflight["schema"] == "cleanmac.ai-host-preflight.v1"
    assert preflight["destructive"] is False
    assert preflight["dry_run"] is True
    assert preflight["ready"] is True, preflight
    assert preflight["entrypoint"]["cli"] == ["cleanmac", "--json", "ai-host-integration-pack"]
    assert preflight["entrypoint"]["entrypoint_contract"] == ["cleanmac", "--json", "ai-entrypoints"]
    assert preflight["entrypoint"]["entrypoint_contract_resource"] == "cleanmac://ai/entrypoints"
    assert preflight["entrypoint"]["safety_chain"] == ["cleanmac", "--json", "ai-safety-chain"]
    assert preflight["entrypoint"]["safety_chain_resource"] == "cleanmac://ai/safety-chain"
    assert preflight["entrypoint"]["candidate_evidence_chain"] == ["cleanmac", "--json", "ai-safety-chain"]
    assert preflight["entrypoint"]["candidate_evidence_chain_resource"] == "cleanmac://ai/safety-chain"
    assert preflight["entrypoint"]["mcp_resource"] == "cleanmac://ai/host-integration-pack"
    assert preflight["entrypoint"]["mcp_meta_index"] == "cleanmac://mcp/meta-index"
    assert preflight["entrypoint"]["mcp_prompt_index"] == "cleanmac://mcp/prompt-index"
    assert preflight["entrypoint"]["mcp_tool_index"] == "cleanmac://mcp/tool-index"
    assert preflight["entrypoint"]["mcp_destructive_tool_governance"] == "cleanmac://mcp/destructive-tool-governance"
    assert preflight["entrypoint"]["operation_log_explainability"] == "cleanmac://ai/operation-log-explainability"
    assert preflight["entrypoint"]["cold_start_budget"] == "cleanmac://ai/cold-start-budget"
    assert preflight["entrypoint"]["no_disturbance"] == "cleanmac://ai/no-disturbance"
    assert preflight["entrypoint"]["dependency_governance"] == "cleanmac://release/dependency-governance"
    assert preflight["entrypoint"]["mcp_surface_audit"] == "cleanmac://mcp/surface-audit"
    assert preflight["entrypoint"]["workflow_contract"] == "cleanmac://ai/workflow-contract"
    checks = {check["id"]: check for check in preflight["checks"]}
    assert checks["integration-pack-ready"]["passed"] is True
    assert checks["host-policy-valid"]["passed"] is True
    assert checks["ai-entrypoints-ready"]["passed"] is True
    assert checks["ai-safety-chain-ready"]["passed"] is True
    assert checks["candidate-evidence-chain-ready"]["passed"] is True
    assert checks["mcp-destructive-tool-governance-ready"]["passed"] is True
    assert checks["operation-log-explainability-ready"]["passed"] is True
    assert checks["cold-start-budget-ready"]["passed"] is True
    assert checks["no-disturbance-ready"]["passed"] is True
    assert checks["dependency-governance-ready"]["passed"] is True
    assert checks["contract-validation-valid"]["passed"] is True
    assert checks["mcp-runtime-policy-present"]["passed"] is True
    assert checks["runtime-lifecycle-policy-valid"]["passed"] is True
    assert checks["zero-resident-audit-advertised"]["passed"] is True
    assert checks["zero-resident-audit-ready"]["passed"] is True
    assert checks["mcp-runtime-policy-present"]["evidence"] == "cleanmac://ai/runtime-lifecycle-policy"
    assert checks["no-disturbance-ready"]["evidence"] == "cleanmac://ai/no-disturbance"
    assert checks["dependency-governance-ready"]["evidence"] == "cleanmac://release/dependency-governance"
    assert checks["zero-resident-audit-advertised"]["evidence"] == "cleanmac://ai/zero-resident-audit"
    assert preflight["entrypoint"]["runtime_lifecycle_policy"] == "cleanmac://ai/runtime-lifecycle-policy"
    assert preflight["entrypoint"]["zero_resident_audit"] == "cleanmac://ai/zero-resident-audit"
    assert "matching_confirmation_token" in preflight["required_before_destructive_tool"]
    assert "candidate_evidence_chain_ready" in preflight["required_before_destructive_tool"]
    assert "cold_start_budget_ready" in preflight["required_before_destructive_tool"]
    assert "no_disturbance_ready" in preflight["required_before_destructive_tool"]
    assert "dependency_governance_ready" in preflight["required_before_destructive_tool"]


def test_preflight_validates_against_registered_contract_schema() -> None:
    preflight = render_ai_host_preflight_report()

    validation = validate_contract_payload("cleanmac.ai-host-preflight.v1", preflight)

    assert validation["valid"] is True, validation
    assert validation["error_count"] == 0


def test_cli_emits_host_preflight() -> None:
    result = subprocess.run(
        [sys.executable, str(CLI), "--json", "ai-host-preflight"],
        text=True,
        capture_output=True,
        check=True,
    )
    preflight = json.loads(result.stdout)

    assert preflight["schema"] == "cleanmac.ai-host-preflight.v1"
    assert preflight["ready"] is True, preflight
