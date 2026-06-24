from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

from cleancli.core import (
    render_release_diagnostics_report,
    render_release_evidence_report,
    render_release_manifest_evidence,
    render_release_operator_summary,
    render_release_post_publish_evidence_template_report,
    render_release_post_publish_result_report,
    render_release_post_publish_verification_report,
    render_release_promotion_decision_report,
    render_release_readiness_report,
    render_release_rehearsal_report,
    render_release_rollback_plan_report,
)
from cleancli.release_artifacts import build_release_artifact_manifest
from cleancli.release_readiness import render_release_readiness


def test_release_readiness_reports_ready_when_all_gates_pass() -> None:
    report = render_release_readiness(
        ai_host_integration_pack={"schema": "cleanmac.ai-host-integration-pack.v1", "ready": True},
        ai_host_preflight={"schema": "cleanmac.ai-host-preflight.v1", "ready": True},
        ai_host_evidence={"schema": "cleanmac.ai-host-evidence.v1", "ready": True},
        ai_first_release_checklist={"schema": "cleanmac.ai-first-release-checklist.v1", "ready": True},
        governance_integrity={"schema": "cleanmac.governance-integrity.v1", "ready": True},
        mcp_surface_audit={"schema": "cleanmac.mcp-surface-audit.v1", "ready": True, "failed_check_ids": []},
        zero_resident_audit={"schema": "cleanmac.zero-resident-audit.v1", "ready": True, "failed_check_ids": []},
        contract_validation={"schema": "cleanmac.ai-contract-validation-summary.v1", "ready": True, "valid": True},
        eval_smoke={"schema": "cleanmac.ai-eval-run.v1", "passed": True, "passed_count": 1, "failed_count": 0},
        release_manifest={"schema": "cleanmac.release-artifact-manifest.v1", "valid": True},
        required_make_targets=[
            "quality-check",
            "governance-integrity-smoke",
            "zero-resident-audit-smoke",
            "governed-execution-smoke",
            "mcp-surface-audit-smoke",
            "ai-host-smoke",
            "release-artifacts-smoke",
        ],
    )

    assert report["schema"] == "cleanmac.release-readiness.v1"
    assert report["destructive"] is False
    assert report["dry_run"] is True
    assert report["ready"] is True
    assert report["readiness_score"] == {"passed": 13, "total": 13, "level": "release-ready"}
    assert report["failed_gate_ids"] == []
    assert ["make", "governance-integrity-smoke"] in report["release_gate_commands"]
    assert ["make", "zero-resident-audit-smoke"] in report["release_gate_commands"]
    assert ["make", "governed-execution-smoke"] in report["release_gate_commands"]
    assert ["make", "mcp-surface-audit-smoke"] in report["release_gate_commands"]
    assert all(gate["severity"] == "none" for gate in report["gates"])
    assert all("next_actions" in gate for gate in report["gates"])

def test_release_readiness_fails_closed_when_evidence_is_missing() -> None:
    report = render_release_readiness(
        ai_host_integration_pack={"schema": "cleanmac.ai-host-integration-pack.v1", "ready": True},
        ai_host_preflight={"schema": "cleanmac.ai-host-preflight.v1", "ready": False},
        ai_host_evidence={"schema": "cleanmac.ai-host-evidence.v1", "ready": False},
        ai_first_release_checklist={"schema": "cleanmac.ai-first-release-checklist.v1", "ready": True},
        governance_integrity={"schema": "cleanmac.governance-integrity.v1", "ready": False},
        mcp_surface_audit={"schema": "cleanmac.mcp-surface-audit.v1", "ready": True, "failed_check_ids": []},
        zero_resident_audit={"schema": "cleanmac.zero-resident-audit.v1", "ready": True, "failed_check_ids": []},
        contract_validation={
            "schema": "cleanmac.ai-contract-validation-summary.v1",
            "ready": False,
            "valid": False,
        },
        eval_smoke={"schema": "cleanmac.ai-eval-run.v1", "passed": False, "passed_count": 0, "failed_count": 1},
        release_manifest={"schema": "cleanmac.release-artifact-manifest.v1", "valid": False},
        required_make_targets=[
            "quality-check",
            "governed-execution-smoke",
            "ai-host-smoke",
            "release-artifacts-smoke",
        ],
    )

    assert report["ready"] is False
    assert report["readiness_score"] == {"passed": 7, "total": 13, "level": "blocked"}
    assert "ai-host-preflight-ready" in report["failed_gate_ids"]
    assert "governance-integrity-ready" in report["failed_gate_ids"]
    assert "release-artifact-manifest-valid" in report["failed_gate_ids"]
    assert report["manual_review_required"] is True
    artifact_gate = {gate["id"]: gate for gate in report["gates"]}["release-artifact-manifest-valid"]
    assert artifact_gate["blocking_code"] == "RELEASE_ARTIFACT_MANIFEST_MISSING"
    assert ["make", "release-artifacts-smoke"] in artifact_gate["next_actions"]

def test_release_readiness_reuses_governance_integrity_remediation() -> None:
    report = render_release_readiness(
        ai_host_integration_pack={"schema": "cleanmac.ai-host-integration-pack.v1", "ready": True},
        ai_host_preflight={"schema": "cleanmac.ai-host-preflight.v1", "ready": True},
        ai_host_evidence={"schema": "cleanmac.ai-host-evidence.v1", "ready": True},
        ai_first_release_checklist={"schema": "cleanmac.ai-first-release-checklist.v1", "ready": True},
        governance_integrity={
            "schema": "cleanmac.governance-integrity.v1",
            "ready": False,
            "failed_check_ids": ["boundary-geo-policy-single-source"],
            "stop_reason": "governance-integrity failed: boundary-geo-policy-single-source",
            "remediation_commands": [
                ["cleanmac", "--json", "governance-integrity"],
                ["make", "governance-integrity-smoke"],
            ],
        },
        mcp_surface_audit={"schema": "cleanmac.mcp-surface-audit.v1", "ready": True, "failed_check_ids": []},
        zero_resident_audit={"schema": "cleanmac.zero-resident-audit.v1", "ready": True, "failed_check_ids": []},
        contract_validation={"schema": "cleanmac.ai-contract-validation-summary.v1", "ready": True, "valid": True},
        eval_smoke={"schema": "cleanmac.ai-eval-run.v1", "passed": True, "passed_count": 1, "failed_count": 0},
        release_manifest={"schema": "cleanmac.release-artifact-manifest.v1", "valid": True},
        required_make_targets=["quality-check", "governance-integrity-smoke", "release-artifacts-smoke"],
    )

    governance_gate = {gate["id"]: gate for gate in report["gates"]}["governance-integrity-ready"]
    assert report["ready"] is False
    assert governance_gate["blocking_code"] == "GOVERNANCE_INTEGRITY_NOT_READY"
    assert governance_gate["diagnostic"] == "governance-integrity failed: boundary-geo-policy-single-source"
    assert governance_gate["next_actions"] == [
        ["cleanmac", "--json", "governance-integrity"],
        ["make", "governance-integrity-smoke"],
    ]

def test_release_readiness_invariants_match_gate_results() -> None:
    report = render_release_readiness(
        ai_host_integration_pack={"schema": "cleanmac.ai-host-integration-pack.v1", "ready": True},
        ai_host_preflight={"schema": "cleanmac.ai-host-preflight.v1", "ready": True},
        ai_host_evidence={"schema": "cleanmac.ai-host-evidence.v1", "ready": True},
        ai_first_release_checklist={"schema": "cleanmac.ai-first-release-checklist.v1", "ready": True},
        governance_integrity={"schema": "cleanmac.governance-integrity.v1", "ready": True},
        mcp_surface_audit={"schema": "cleanmac.mcp-surface-audit.v1", "ready": True, "failed_check_ids": []},
        zero_resident_audit={"schema": "cleanmac.zero-resident-audit.v1", "ready": True, "failed_check_ids": []},
        contract_validation={"schema": "cleanmac.ai-contract-validation-summary.v1", "ready": True, "valid": True},
        eval_smoke={"schema": "cleanmac.ai-eval-run.v1", "passed": True, "passed_count": 1, "failed_count": 0},
        release_manifest={"schema": "cleanmac.release-artifact-manifest.v1", "valid": False},
        required_make_targets=["quality-check", "release-artifacts-smoke"],
    )

    failed_gate_ids = {gate["id"] for gate in report["gates"] if not gate["passed"]}
    assert report["ready"] == (report["failed_gate_ids"] == [])
    assert report["readiness_score"]["total"] == len(report["gates"])
    assert set(report["failed_gate_ids"]) == failed_gate_ids
    assert all(
        {"id", "passed", "evidence_schema", "severity", "next_actions"} <= set(gate) for gate in report["gates"]
    )

def test_release_readiness_fails_closed_when_mcp_surface_audit_is_blocked() -> None:
    report = render_release_readiness(
        ai_host_integration_pack={"schema": "cleanmac.ai-host-integration-pack.v1", "ready": True},
        ai_host_preflight={"schema": "cleanmac.ai-host-preflight.v1", "ready": True},
        ai_host_evidence={"schema": "cleanmac.ai-host-evidence.v1", "ready": True},
        ai_first_release_checklist={"schema": "cleanmac.ai-first-release-checklist.v1", "ready": True},
        governance_integrity={"schema": "cleanmac.governance-integrity.v1", "ready": True},
        mcp_surface_audit={
            "schema": "cleanmac.mcp-surface-audit.v1",
            "ready": False,
            "failed_check_ids": ["required-tools-advertised"],
            "stop_reason": "mcp-surface-audit failed: required-tools-advertised",
        },
        zero_resident_audit={"schema": "cleanmac.zero-resident-audit.v1", "ready": True, "failed_check_ids": []},
        contract_validation={"schema": "cleanmac.ai-contract-validation-summary.v1", "ready": True, "valid": True},
        eval_smoke={"schema": "cleanmac.ai-eval-run.v1", "passed": True, "passed_count": 1, "failed_count": 0},
        release_manifest={"schema": "cleanmac.release-artifact-manifest.v1", "valid": True},
        required_make_targets=["quality-check", "mcp-surface-audit-smoke", "release-artifacts-smoke"],
    )

    gates = {gate["id"]: gate for gate in report["gates"]}
    assert report["ready"] is False
    assert report["manual_review_required"] is True
    assert "mcp-surface-audit-ready" in report["failed_gate_ids"]
    assert report["readiness_score"] == {"passed": 12, "total": 13, "level": "blocked"}
    assert gates["mcp-surface-audit-ready"]["blocking_code"] == "MCP_SURFACE_AUDIT_NOT_READY"
    assert "required-tools-advertised" in gates["mcp-surface-audit-ready"]["diagnostic"]
    assert ["make", "mcp-surface-audit-smoke"] in gates["mcp-surface-audit-ready"]["next_actions"]

def test_release_manifest_evidence_uses_explicit_directories(tmp_path: Path) -> None:
    dist = tmp_path / "dist"
    assets = tmp_path / "release-assets"
    dist.mkdir()
    assets.mkdir()
    (dist / "cleanmac-0.1.0-py3-none-any.whl").write_text("wheel", encoding="utf-8")
    (dist / "cleanmac-0.1.0.tar.gz").write_text("sdist", encoding="utf-8")
    (assets / "SBOM.json").write_text("{}", encoding="utf-8")
    (assets / "cleanmac.rb").write_text("class Cleanmac < Formula\nend\n", encoding="utf-8")
    manifest = build_release_artifact_manifest(dist_dir=dist, assets_dir=assets)
    (assets / "ARTIFACT-MANIFEST.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    evidence = render_release_manifest_evidence(dist_dir=dist, assets_dir=assets)

    assert evidence["schema"] == "cleanmac.release-artifact-manifest.v1"
    assert evidence["valid"] is True, evidence
    assert evidence["path"] == str(assets / "ARTIFACT-MANIFEST.json")

def test_missing_release_manifest_evidence_exposes_publishable_asset_recovery(tmp_path: Path) -> None:
    dist = tmp_path / "dist"
    assets = tmp_path / "release-assets"
    dist.mkdir()
    assets.mkdir()

    evidence = render_release_manifest_evidence(dist_dir=dist, assets_dir=assets)

    assert evidence["schema"] == "cleanmac.release-artifact-manifest.v1"
    assert evidence["valid"] is False
    assert evidence["error_code"] == "RELEASE_ARTIFACT_MANIFEST_MISSING"
    assert str(assets / "ARTIFACT-MANIFEST.json") in evidence["expected_assets"]
    assert evidence["downloadable_asset_manifest"]["manifest"] == str(assets / "ARTIFACT-MANIFEST.json")
    assert evidence["downloadable_asset_manifest"]["sha256sums"] == str(assets / "SHA256SUMS")
    assert ["make", "release-artifacts-smoke"] in evidence["verification_commands"]
    channels = {channel["name"]: channel for channel in evidence["publish_channels"]}
    assert "GitHub Releases" in channels
    assert channels["Homebrew"]["tap"] == "cleanmac/tap"
    assert "trusted-publishing" in channels["PyPI"]["requires"]

def test_release_diagnostics_and_operator_summary_explain_missing_artifacts(tmp_path: Path) -> None:
    dist = tmp_path / "dist"
    assets = tmp_path / "release-assets"
    dist.mkdir()
    assets.mkdir()

    diagnostics = render_release_diagnostics_report(dist_dir=dist, assets_dir=assets)
    summary = render_release_operator_summary(dist_dir=dist, assets_dir=assets)

    assert diagnostics["schema"] == "cleanmac.release-diagnostics.v1"
    assert diagnostics["ready"] is False
    assert "release-artifact-manifest-valid" in diagnostics["failed_gate_ids"]
    assert diagnostics["artifacts"]["error_code"] == "RELEASE_ARTIFACT_MANIFEST_MISSING"
    assert diagnostics["governance_integrity"]["schema"] == "cleanmac.governance-integrity.v1"
    assert diagnostics["governance_integrity"]["ready"] is True, diagnostics["governance_integrity"]
    assert diagnostics["governance_integrity"]["failed_check_ids"] == []
    assert ["make", "governance-integrity-smoke"] in diagnostics["governance_integrity"]["remediation_commands"]
    assert diagnostics["ai_first_release_checklist"]["schema"] == "cleanmac.ai-first-release-checklist.v1"
    assert diagnostics["ai_first_release_checklist"]["ready"] is True, diagnostics["ai_first_release_checklist"]
    assert summary["schema"] == "cleanmac.release-operator-summary.v1"
    assert summary["status"] == "blocked"
    assert summary["must_fix_first"][0]["gate_id"] == "release-artifact-manifest-valid"

def test_release_diagnostics_exposes_governance_integrity_details(tmp_path: Path) -> None:
    dist = tmp_path / "dist"
    assets = tmp_path / "release-assets"
    dist.mkdir()
    assets.mkdir()
    (dist / "cleanmac-0.1.0-py3-none-any.whl").write_text("wheel", encoding="utf-8")
    (dist / "cleanmac-0.1.0.tar.gz").write_text("sdist", encoding="utf-8")
    (assets / "SBOM.json").write_text("{}", encoding="utf-8")
    (assets / "cleanmac.rb").write_text("class Cleanmac < Formula\nend\n", encoding="utf-8")
    manifest = build_release_artifact_manifest(dist_dir=dist, assets_dir=assets)
    (assets / "ARTIFACT-MANIFEST.json").write_text(json.dumps(manifest), encoding="utf-8")

    with patch(
        "cleancli.core.render_governance_integrity",
        return_value={
            "schema": "cleanmac.governance-integrity.v1",
            "ready": False,
            "failed_check_ids": ["boundary-geo-policy-single-source"],
            "stop_reason": "governance-integrity failed: boundary-geo-policy-single-source",
            "readiness_score": {"passed": 7, "total": 8, "level": "blocked"},
            "remediation_commands": [
                ["cleanmac", "--json", "governance-integrity"],
                ["make", "governance-integrity-smoke"],
            ],
        },
    ):
        diagnostics = render_release_diagnostics_report(dist_dir=dist, assets_dir=assets)

    failed_gates = {gate["id"]: gate for gate in diagnostics["failed_gates"]}
    assert diagnostics["ready"] is False
    assert "governance-integrity-ready" in diagnostics["failed_gate_ids"]
    assert (
        diagnostics["governance_integrity"]["stop_reason"]
        == "governance-integrity failed: boundary-geo-policy-single-source"
    )
    assert failed_gates["governance-integrity-ready"]["blocking_code"] == "GOVERNANCE_INTEGRITY_NOT_READY"
    assert ["make", "governance-integrity-smoke"] in diagnostics["recommended_commands"]

def test_release_diagnostics_exposes_mcp_surface_audit_gate_recovery(tmp_path: Path) -> None:
    dist = tmp_path / "dist"
    assets = tmp_path / "release-assets"
    dist.mkdir()
    assets.mkdir()
    (dist / "cleanmac-0.1.0-py3-none-any.whl").write_text("wheel", encoding="utf-8")
    (dist / "cleanmac-0.1.0.tar.gz").write_text("sdist", encoding="utf-8")
    (assets / "SBOM.json").write_text("{}", encoding="utf-8")
    (assets / "cleanmac.rb").write_text("class Cleanmac < Formula\nend\n", encoding="utf-8")
    manifest = build_release_artifact_manifest(dist_dir=dist, assets_dir=assets)
    (assets / "ARTIFACT-MANIFEST.json").write_text(json.dumps(manifest), encoding="utf-8")

    with patch(
        "cleancli.core.render_mcp_surface_audit",
        return_value={
            "schema": "cleanmac.mcp-surface-audit.v1",
            "ready": False,
            "failed_check_ids": ["required-tools-advertised"],
            "stop_reason": "mcp-surface-audit failed: required-tools-advertised",
        },
    ):
        diagnostics = render_release_diagnostics_report(dist_dir=dist, assets_dir=assets)

    failed_gates = {gate["id"]: gate for gate in diagnostics["failed_gates"]}
    assert diagnostics["ready"] is False
    assert "mcp-surface-audit-ready" in diagnostics["failed_gate_ids"]
    assert failed_gates["mcp-surface-audit-ready"]["blocking_code"] == "MCP_SURFACE_AUDIT_NOT_READY"
    assert "required-tools-advertised" in failed_gates["mcp-surface-audit-ready"]["diagnostic"]
    assert ["make", "mcp-surface-audit-smoke"] in failed_gates["mcp-surface-audit-ready"]["next_actions"]
    assert ["make", "mcp-surface-audit-smoke"] in diagnostics["recommended_commands"]

def test_release_evidence_bundle_uses_readiness_and_assets(tmp_path: Path) -> None:
    dist = tmp_path / "dist"
    assets = tmp_path / "release-assets"
    dist.mkdir()
    assets.mkdir()
    (dist / "cleanmac-0.1.0-py3-none-any.whl").write_text("wheel", encoding="utf-8")
    (dist / "cleanmac-0.1.0.tar.gz").write_text("sdist", encoding="utf-8")
    (assets / "SBOM.json").write_text("{}", encoding="utf-8")
    (assets / "cleanmac.rb").write_text("class Cleanmac < Formula\nend\n", encoding="utf-8")
    manifest = build_release_artifact_manifest(dist_dir=dist, assets_dir=assets)
    (assets / "SHA256SUMS").write_text("", encoding="utf-8")
    (assets / "ARTIFACT-MANIFEST.json").write_text(json.dumps(manifest), encoding="utf-8")
    readiness = render_release_readiness_report(dist_dir=dist, assets_dir=assets)
    (assets / "RELEASE-READINESS.json").write_text(json.dumps(readiness), encoding="utf-8")
    diagnostics = render_release_diagnostics_report(dist_dir=dist, assets_dir=assets)
    (assets / "RELEASE-DIAGNOSTICS.json").write_text(json.dumps(diagnostics), encoding="utf-8")
    rollback_plan = render_release_rollback_plan_report(dist_dir=dist, assets_dir=assets)
    (assets / "RELEASE-ROLLBACK-PLAN.json").write_text(json.dumps(rollback_plan), encoding="utf-8")
    post_publish = render_release_post_publish_verification_report(dist_dir=dist, assets_dir=assets)
    (assets / "RELEASE-POST-PUBLISH-VERIFICATION.json").write_text(json.dumps(post_publish), encoding="utf-8")
    post_publish_result = render_release_post_publish_result_report(dist_dir=dist, assets_dir=assets)
    (assets / "RELEASE-POST-PUBLISH-RESULT.json").write_text(json.dumps(post_publish_result), encoding="utf-8")
    post_publish_template = render_release_post_publish_evidence_template_report(dist_dir=dist, assets_dir=assets)
    (assets / "RELEASE-POST-PUBLISH-EVIDENCE.example.json").write_text(
        json.dumps(post_publish_template), encoding="utf-8"
    )
    (assets / "RELEASE-REHEARSAL.json").write_text("{}", encoding="utf-8")
    (assets / "RELEASE-PROMOTION-DECISION.json").write_text("{}", encoding="utf-8")
    rehearsal = render_release_rehearsal_report(dist_dir=dist, assets_dir=assets)
    (assets / "RELEASE-REHEARSAL.json").write_text(json.dumps(rehearsal), encoding="utf-8")
    promotion = render_release_promotion_decision_report(dist_dir=dist, assets_dir=assets)
    (assets / "RELEASE-PROMOTION-DECISION.json").write_text(json.dumps(promotion), encoding="utf-8")

    evidence = render_release_evidence_report(dist_dir=dist, assets_dir=assets)

    assert evidence["schema"] == "cleanmac.release-evidence.v1"
    assert evidence["ready"] is True, evidence
    assert evidence["assets"]["missing"] == []
    assert evidence["post_publish_verification"]["schema"] == "cleanmac.release-post-publish-verification.v1"
    assert evidence["post_publish_result"]["schema"] == "cleanmac.release-post-publish-result.v1"
    assert evidence["post_publish_result"]["ready"] is False
    assert evidence["governance_integrity"]["schema"] == "cleanmac.governance-integrity.v1"
    assert evidence["governance_integrity"]["ready"] is True, evidence["governance_integrity"]
    assert evidence["ai_first_release_checklist"]["schema"] == "cleanmac.ai-first-release-checklist.v1"
    assert evidence["ai_first_release_checklist"]["ready"] is True, evidence["ai_first_release_checklist"]
    assert (
        evidence["post_publish_evidence_template"]["schema"]
        == "cleanmac.release-post-publish-evidence-template.v1"
    )

def test_release_evidence_bundle_includes_mcp_surface_audit_diagnostics(tmp_path: Path) -> None:
    dist = tmp_path / "dist"
    assets = tmp_path / "release-assets"
    dist.mkdir()
    assets.mkdir()
    (dist / "cleanmac-0.1.0-py3-none-any.whl").write_text("wheel", encoding="utf-8")
    (dist / "cleanmac-0.1.0.tar.gz").write_text("sdist", encoding="utf-8")
    (assets / "SBOM.json").write_text("{}", encoding="utf-8")
    (assets / "SHA256SUMS").write_text("", encoding="utf-8")
    (assets / "cleanmac.rb").write_text("class Cleanmac < Formula\nend\n", encoding="utf-8")
    manifest = build_release_artifact_manifest(dist_dir=dist, assets_dir=assets)
    (assets / "ARTIFACT-MANIFEST.json").write_text(json.dumps(manifest), encoding="utf-8")

    with patch(
        "cleancli.core.render_mcp_surface_audit",
        return_value={
            "schema": "cleanmac.mcp-surface-audit.v1",
            "ready": False,
            "failed_check_ids": ["required-tools-advertised"],
            "stop_reason": "mcp-surface-audit failed: required-tools-advertised",
        },
    ):
        evidence = render_release_evidence_report(dist_dir=dist, assets_dir=assets)

    failed_gates = {gate["id"]: gate for gate in evidence["release_diagnostics"]["failed_gates"]}
    assert evidence["ready"] is False
    assert "mcp-surface-audit-ready" in evidence["release_readiness"]["failed_gate_ids"]
    assert failed_gates["mcp-surface-audit-ready"]["blocking_code"] == "MCP_SURFACE_AUDIT_NOT_READY"
    assert ["make", "mcp-surface-audit-smoke"] in evidence["release_diagnostics"]["recommended_commands"]


def test_pytest_release_readiness_fixture_roundtrip_preserves_release_gate(tmp_path: Path) -> None:
    dist = tmp_path / "dist"
    assets = tmp_path / "release-assets"
    dist.mkdir()
    assets.mkdir()
    (dist / "cleanmac-0.1.0-py3-none-any.whl").write_text("wheel", encoding="utf-8")
    (dist / "cleanmac-0.1.0.tar.gz").write_text("sdist", encoding="utf-8")
    (assets / "SBOM.json").write_text("{}", encoding="utf-8")
    (assets / "cleanmac.rb").write_text("class Cleanmac < Formula\nend\n", encoding="utf-8")
    manifest = build_release_artifact_manifest(dist_dir=dist, assets_dir=assets)
    (assets / "ARTIFACT-MANIFEST.json").write_text(json.dumps(manifest), encoding="utf-8")

    readiness = render_release_readiness_report(dist_dir=dist, assets_dir=assets)

    assert readiness["schema"] == "cleanmac.release-readiness.v1"
    assert readiness["ready"] is True
    assert readiness["failed_gate_ids"] == []
    assert {gate["id"] for gate in readiness["gates"] if not gate["passed"]} == set()


def test_pytest_release_diagnostics_exposes_blocking_code_without_artifacts(tmp_path: Path) -> None:
    dist = tmp_path / "dist"
    assets = tmp_path / "release-assets"
    dist.mkdir()
    assets.mkdir()

    diagnostics = render_release_diagnostics_report(dist_dir=dist, assets_dir=assets)

    assert diagnostics["schema"] == "cleanmac.release-diagnostics.v1"
    assert diagnostics["ready"] is False
    assert diagnostics["artifacts"]["error_code"] == "RELEASE_ARTIFACT_MANIFEST_MISSING"
    assert diagnostics["recommended_commands"][0] == ["make", "release-artifacts-smoke"]
