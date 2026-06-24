from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest

from cleancli.ai_versioning import validate_contract_payload
from cleancli.core import render_ai_host_evidence_report

PROJECT_ROOT = Path(__file__).resolve().parent.parent
CLI = PROJECT_ROOT / "cleanmac.py"


@pytest.fixture(scope="module")
def evidence_report() -> dict[str, Any]:
    return render_ai_host_evidence_report()


@pytest.fixture(scope="module")
def evidence_checks(evidence_report: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {check["id"]: check for check in evidence_report["evidence_checks"]}


@pytest.fixture(scope="module")
def cli_evidence_report() -> dict[str, Any]:
    result = subprocess.run(
        [sys.executable, str(CLI), "--json", "ai-host-evidence"],
        text=True,
        capture_output=True,
        check=True,
    )
    return json.loads(result.stdout)


def test_evidence_report_is_ready_and_non_destructive(evidence_report: dict[str, Any]) -> None:
    report = evidence_report

    assert report["schema"] == "cleanmac.ai-host-evidence.v1"
    assert not report["destructive"]
    assert report["dry_run"]
    assert report["ready"], report
    assert report["source"] == "cleanmac-ai-host-evidence"
    assert report["preflight"]["schema"] == "cleanmac.ai-host-preflight.v1"
    assert report["preflight"]["ready"], report["preflight"]
    assert report["contract_validation"]["schema"] == "cleanmac.ai-contract-validation-summary.v1"
    assert report["contract_validation"]["valid"], report["contract_validation"]
    assert report["release_readiness"]["schema"] == "cleanmac.release-readiness.v1"
    assert "failed_gate_ids" in report["release_readiness"]
    assert report["release_readiness"]["required_for"] == "release-review"
    assert report["release_readiness"]["not_required_for"] == "runtime-readonly-ai-host-discovery"
    assert report["runtime_lifecycle"]["schema"] == "cleanmac.runtime-lifecycle-policy.v1"
    assert report["runtime_lifecycle"]["product_model"] == "ai-first-ephemeral-cli"
    assert report["runtime_lifecycle"]["resident_processes"] == 0
    assert report["zero_resident_audit"]["schema"] == "cleanmac.zero-resident-audit.v1"
    assert report["zero_resident_audit"]["ready"], report["zero_resident_audit"]
    assert report["zero_resident_audit"]["resident_processes"] == 0
    assert report["no_disturbance"]["schema"] == "cleanmac.no-disturbance.v1"
    assert report["no_disturbance"]["ready"], report["no_disturbance"]
    assert report["no_disturbance"]["silent_by_default"]


def test_evidence_report_exposes_required_host_checks(
    evidence_report: dict[str, Any],
    evidence_checks: dict[str, dict[str, Any]],
) -> None:
    required_check_ids = {
        "release-readiness-resource-advertised",
        "mcp-meta-index-advertised",
        "mcp-meta-index-valid",
        "mcp-resource-index-advertised",
        "mcp-surface-audit-advertised",
        "mcp-surface-audit-ready",
        "ai-safety-chain-advertised",
        "ai-safety-chain-ready",
        "candidate-evidence-chain-exposed",
        "candidate-evidence-chain-preflight-gated",
        "candidate-evidence-chain-release-gated",
        "runtime-lifecycle-policy-advertised",
        "runtime-lifecycle-policy-valid",
        "zero-resident-audit-advertised",
        "zero-resident-audit-ready",
        "no-disturbance-advertised",
        "no-disturbance-ready",
        "mcp-resource-catalog-valid",
        "mcp-prompt-index-advertised",
        "mcp-prompt-catalog-valid",
        "mcp-tool-index-advertised",
        "mcp-tool-catalog-valid",
    }

    missing = sorted(required_check_ids.difference(evidence_checks))
    assert missing == []
    assert all(evidence_checks[check_id]["passed"] for check_id in required_check_ids), evidence_checks
    assert evidence_report["host_evidence_requirements"]["candidate_evidence_chain_ready"]


def test_evidence_report_carries_candidate_evidence_contract(evidence_report: dict[str, Any]) -> None:
    candidate_chain = evidence_report["candidate_evidence_chain"]

    assert candidate_chain["schema"] == "cleanmac.candidate-review-evidence.v1"
    assert candidate_chain["fail_closed_if_missing"]
    assert "review_selection_constraint.selected_review_evidence[]" in candidate_chain["required_artifact_paths"]
    assert "operation_log.ai.candidate_review_evidence" in candidate_chain["required_artifact_paths"]


def test_evidence_report_carries_mcp_catalogs(evidence_report: dict[str, Any]) -> None:
    assert evidence_report["mcp_meta_index"]["missing_index_uris"] == []
    assert evidence_report["mcp_surface_audit"]["schema"] == "cleanmac.mcp-surface-audit.v1"
    assert evidence_report["mcp_surface_audit"]["ready"], evidence_report["mcp_surface_audit"]
    assert evidence_report["mcp_resource_catalog"]["resource_count"] > 0
    assert evidence_report["mcp_resource_catalog"]["duplicate_uris"] == []
    assert evidence_report["mcp_prompt_catalog"]["prompt_count"] > 0
    assert evidence_report["mcp_prompt_catalog"]["duplicate_names"] == []
    assert evidence_report["mcp_tool_catalog"]["tool_count"] > 0
    assert evidence_report["mcp_tool_catalog"]["duplicate_names"] == []


def test_evidence_includes_runtime_denial_samples(evidence_report: dict[str, Any]) -> None:
    samples = {sample["id"]: sample for sample in evidence_report["runtime_policy_evidence"]}

    assert "raw-command-argument-denied" in samples
    assert "destructive-missing-confirmation-denied" in samples
    assert not samples["raw-command-argument-denied"]["decision"]["allowed"]
    assert not samples["destructive-missing-confirmation-denied"]["decision"]["allowed"]
    raw_codes = {
        reason["code"] for reason in samples["raw-command-argument-denied"]["decision"]["blocking_reasons"]
    }
    destructive_codes = {
        reason["code"]
        for reason in samples["destructive-missing-confirmation-denied"]["decision"]["blocking_reasons"]
    }
    assert raw_codes == {"RAW_COMMAND_ARGUMENT_DENIED"}
    assert "HUMAN_CONFIRMATION_PHRASE_REQUIRED" in destructive_codes
    assert "CONFIRMATION_TOKEN_REQUIRED" in destructive_codes


def test_evidence_validates_against_registered_contract_schema(evidence_report: dict[str, Any]) -> None:
    validation = validate_contract_payload("cleanmac.ai-host-evidence.v1", evidence_report)

    assert validation["valid"], validation
    assert validation["error_count"] == 0


def test_cli_emits_host_evidence(cli_evidence_report: dict[str, Any]) -> None:
    report = cli_evidence_report

    assert report["schema"] == "cleanmac.ai-host-evidence.v1"
    assert report["ready"], report
    assert ["make", "ai-host-smoke"] in report["release_gate_commands"]
    assert ["make", "release-readiness-smoke"] in report["release_gate_commands"]
    assert ["cleanmac", "--json", "release-readiness"] in report["release_gate_commands"]


def test_cli_host_evidence_exposes_required_checks(cli_evidence_report: dict[str, Any]) -> None:
    checks = {check["id"]: check for check in cli_evidence_report["evidence_checks"]}
    required_check_ids = {
        "mcp-meta-index-advertised",
        "mcp-meta-index-valid",
        "mcp-resource-index-advertised",
        "mcp-surface-audit-advertised",
        "mcp-surface-audit-ready",
        "runtime-lifecycle-policy-advertised",
        "runtime-lifecycle-policy-valid",
        "zero-resident-audit-advertised",
        "zero-resident-audit-ready",
        "no-disturbance-advertised",
        "no-disturbance-ready",
        "mcp-resource-catalog-valid",
        "mcp-prompt-index-advertised",
        "mcp-prompt-catalog-valid",
        "mcp-tool-index-advertised",
        "mcp-tool-catalog-valid",
    }

    missing = sorted(required_check_ids.difference(checks))
    assert missing == []
    assert all(checks[check_id]["passed"] for check_id in required_check_ids), checks
