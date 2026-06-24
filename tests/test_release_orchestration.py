from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from cleancli.core import render_release_diagnostics_report, render_release_readiness_report
from cleancli.release_artifacts import build_release_artifact_manifest
from cleancli.release_orchestration import (
    render_release_post_publish_evidence_template,
    render_release_post_publish_result,
    render_release_post_publish_verification,
    render_release_promotion_decision,
    render_release_rehearsal,
    render_release_rollback_plan,
)

PROJECT_ROOT = Path(__file__).resolve().parent.parent
CLI = PROJECT_ROOT / "cleanmac.py"


def _write_ready_release_assets(root: Path) -> tuple[Path, Path]:
    dist = root / "dist"
    assets = root / "release-assets"
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
    (assets / "RELEASE-REHEARSAL.json").write_text(
        json.dumps({"schema": "cleanmac.release-rehearsal.v1", "ready": True}), encoding="utf-8"
    )
    (assets / "RELEASE-ROLLBACK-PLAN.json").write_text(
        json.dumps({"schema": "cleanmac.release-rollback-plan.v1", "manual_only": True}), encoding="utf-8"
    )
    (assets / "RELEASE-POST-PUBLISH-VERIFICATION.json").write_text(
        json.dumps({"schema": "cleanmac.release-post-publish-verification.v1", "manual_only": True}),
        encoding="utf-8",
    )
    (assets / "RELEASE-POST-PUBLISH-RESULT.json").write_text(
        json.dumps({"schema": "cleanmac.release-post-publish-result.v1", "manual_only": True, "ready": False}),
        encoding="utf-8",
    )
    return dist, assets


def test_rehearsal_blocks_when_required_assets_are_missing(tmp_path: Path) -> None:
    dist = tmp_path / "dist"
    assets = tmp_path / "release-assets"
    dist.mkdir()
    assets.mkdir()

    rehearsal = render_release_rehearsal(dist_dir=dist, assets_dir=assets)

    assert rehearsal["schema"] == "cleanmac.release-rehearsal.v1"
    assert rehearsal["ready"] is False
    assert "artifact-manifest" in rehearsal["failed_phase_ids"]
    assert "ARTIFACT-MANIFEST.json" in rehearsal["assets"]["missing"]


def test_promotion_decision_promotes_only_when_rehearsal_evidence_is_complete(tmp_path: Path) -> None:
    dist, assets = _write_ready_release_assets(tmp_path)

    rehearsal = render_release_rehearsal(dist_dir=dist, assets_dir=assets)
    decision = render_release_promotion_decision(dist_dir=dist, assets_dir=assets)

    phases = {phase["id"]: phase for phase in rehearsal["phases"]}
    assert phases["release-diagnostics"]["status"] == "passed"
    assert phases["release-diagnostics"]["governance_integrity"]["schema"] == "cleanmac.governance-integrity.v1"
    assert phases["release-diagnostics"]["governance_integrity"]["ready"] is True
    assert decision["schema"] == "cleanmac.release-promotion-decision.v1"
    assert decision["decision"] == "promote"
    assert decision["safe_to_publish"] is True
    assert decision["manual_review_required"] is False


def test_promotion_decision_blocks_missing_evidence(tmp_path: Path) -> None:
    dist = tmp_path / "dist"
    assets = tmp_path / "release-assets"
    dist.mkdir()
    assets.mkdir()

    decision = render_release_promotion_decision(dist_dir=dist, assets_dir=assets)

    assert decision["decision"] == "block"
    assert decision["safe_to_publish"] is False
    assert decision["manual_review_required"] is True
    assert "RELEASE_ARTIFACT_MANIFEST_MISSING" in decision["blocking_codes"]


def test_promotion_decision_exposes_mcp_surface_audit_blocking_code(tmp_path: Path) -> None:
    dist, assets = _write_ready_release_assets(tmp_path)
    readiness = json.loads((assets / "RELEASE-READINESS.json").read_text(encoding="utf-8"))
    readiness["ready"] = False
    readiness["manual_review_required"] = True
    readiness["readiness_score"] = {"passed": 9, "total": 10, "level": "blocked"}
    readiness["failed_gate_ids"] = ["mcp-surface-audit-ready"]
    for gate in readiness["gates"]:
        if gate["id"] == "mcp-surface-audit-ready":
            gate["passed"] = False
            gate["severity"] = "blocking"
            gate["diagnostic"] = "mcp-surface-audit failed: required-tools-advertised"
            gate["blocking_code"] = "MCP_SURFACE_AUDIT_NOT_READY"
    (assets / "RELEASE-READINESS.json").write_text(json.dumps(readiness), encoding="utf-8")

    decision = render_release_promotion_decision(dist_dir=dist, assets_dir=assets)

    assert decision["decision"] == "block"
    assert decision["safe_to_publish"] is False
    assert "RELEASE_READINESS_BLOCKED" in decision["blocking_codes"]
    assert "MCP_SURFACE_AUDIT_NOT_READY" in decision["blocking_codes"]
    assert "mcp-surface-audit-ready" in decision["rehearsal_summary"]["failed_gate_ids"]


def test_rehearsal_blocks_when_diagnostics_governance_integrity_is_not_ready(tmp_path: Path) -> None:
    dist, assets = _write_ready_release_assets(tmp_path)
    diagnostics = json.loads((assets / "RELEASE-DIAGNOSTICS.json").read_text(encoding="utf-8"))
    diagnostics["ready"] = False
    diagnostics["governance_integrity"] = {
        "schema": "cleanmac.governance-integrity.v1",
        "ready": False,
        "failed_check_ids": ["boundary-geo-policy-single-source"],
        "stop_reason": "governance-integrity failed: boundary-geo-policy-single-source",
        "readiness_score": {"passed": 7, "total": 8, "level": "blocked"},
        "remediation_commands": [
            ["cleanmac", "--json", "governance-integrity"],
            ["make", "governance-integrity-smoke"],
        ],
    }
    (assets / "RELEASE-DIAGNOSTICS.json").write_text(json.dumps(diagnostics), encoding="utf-8")

    rehearsal = render_release_rehearsal(dist_dir=dist, assets_dir=assets)
    decision = render_release_promotion_decision(dist_dir=dist, assets_dir=assets)

    phases = {phase["id"]: phase for phase in rehearsal["phases"]}
    assert rehearsal["ready"] is False
    assert "release-diagnostics" in rehearsal["failed_phase_ids"]
    assert phases["release-diagnostics"]["blocking_code"] == "GOVERNANCE_INTEGRITY_NOT_READY"
    assert "boundary-geo-policy-single-source" in phases["release-diagnostics"]["diagnostic"]
    assert ["make", "governance-integrity-smoke"] in phases["release-diagnostics"]["next_actions"]
    assert decision["decision"] == "block"
    assert "GOVERNANCE_INTEGRITY_NOT_READY" in decision["blocking_codes"]


def test_rollback_plan_is_manual_only_without_destructive_commands() -> None:
    plan = render_release_rollback_plan(dist_dir="dist", assets_dir="release-assets")
    forbidden = "rm " + "-rf"

    assert plan["schema"] == "cleanmac.release-rollback-plan.v1"
    assert plan["manual_only"] is True
    assert ["cleanmac", "--json", "governance-integrity"] in plan["pre_rollback_checks"]
    assert ["make", "governance-integrity-smoke"] in plan["pre_rollback_checks"]
    assert {surface["id"] for surface in plan["rollback_surfaces"]} == {"pypi", "github-release", "homebrew-tap"}
    assert forbidden not in json.dumps(plan)


def test_post_publish_verification_is_manual_only_without_destructive_commands() -> None:
    plan = render_release_post_publish_verification(dist_dir="dist", assets_dir="release-assets")
    forbidden = "rm " + "-rf"

    assert plan["schema"] == "cleanmac.release-post-publish-verification.v1"
    assert plan["manual_only"] is True
    assert {surface["id"] for surface in plan["verification_surfaces"]} == {
        "pypi",
        "github-release",
        "homebrew-tap",
    }
    assert ["cleanmac", "--json", "release-rollback-plan"] in plan["incident_response_entrypoints"]
    assert forbidden not in json.dumps(plan)


def test_post_publish_result_defaults_to_pending_manual_only_without_destructive_commands() -> None:
    result = render_release_post_publish_result(dist_dir="dist", assets_dir="release-assets")
    forbidden = "rm " + "-rf"

    assert result["schema"] == "cleanmac.release-post-publish-result.v1"
    assert result["manual_only"] is True
    assert result["destructive"] is False
    assert result["ready"] is False
    assert set(result["pending_surface_ids"]) == {"pypi", "github-release", "homebrew-tap"}
    assert ["cleanmac", "--json", "release-rollback-plan"] in result["incident_response_entrypoints"]
    assert forbidden not in json.dumps(result)


def test_post_publish_evidence_template_is_manual_only_and_complete() -> None:
    template = render_release_post_publish_evidence_template(dist_dir="dist", assets_dir="release-assets")
    forbidden = "rm " + "-rf"

    assert template["schema"] == "cleanmac.release-post-publish-evidence-template.v1"
    assert template["destructive"] is False
    assert template["dry_run"] is True
    assert template["manual_only"] is True
    assert template["target_input_schema"] == "cleanmac.release-post-publish-evidence-input.v1"
    assert set(template["template"]["surfaces"]) == {"pypi", "github-release", "homebrew-tap"}
    assert template["template"]["surfaces"]["pypi"]["status"] == "pending"
    assert [
        "cleanmac",
        "--json",
        "release-post-publish-result",
        "--evidence-file",
        "post-publish-evidence.json",
    ] in template["recommended_commands"]
    assert forbidden not in json.dumps(template)


def test_post_publish_result_accepts_verified_evidence_file(tmp_path: Path) -> None:
    evidence = tmp_path / "post-publish-evidence.json"
    evidence.write_text(
        json.dumps(
            {
                "schema": "cleanmac.release-post-publish-evidence-input.v1",
                "surfaces": {
                    "github-release": {"status": "verified", "evidence_refs": ["release-assets"]},
                    "pypi": {"status": "verified", "evidence_refs": ["pypi-page"]},
                    "homebrew-tap": {"status": "verified", "evidence_refs": ["tap-commit"]},
                },
            }
        ),
        encoding="utf-8",
    )

    result = render_release_post_publish_result(dist_dir="dist", assets_dir="release-assets", evidence_file=evidence)

    assert result["ready"] is True, result
    assert set(result["verified_surface_ids"]) == {"pypi", "github-release", "homebrew-tap"}
    assert result["failed_surface_ids"] == []
    assert result["pending_surface_ids"] == []


def test_post_publish_result_blocks_failed_surface(tmp_path: Path) -> None:
    evidence = tmp_path / "post-publish-evidence.json"
    evidence.write_text(
        json.dumps(
            {
                "schema": "cleanmac.release-post-publish-evidence-input.v1",
                "surfaces": {"pypi": {"status": "failed", "evidence_refs": ["pypi-page"]}},
            }
        ),
        encoding="utf-8",
    )

    result = render_release_post_publish_result(dist_dir="dist", assets_dir="release-assets", evidence_file=evidence)

    assert result["ready"] is False
    assert "pypi" in result["failed_surface_ids"]
    failed_surface = next(surface for surface in result["surfaces"] if surface["id"] == "pypi")
    assert failed_surface["blocking_code"] == "PYPI_POST_PUBLISH_FAILED"


def test_post_publish_result_rejects_wrong_evidence_schema_fail_closed(tmp_path: Path) -> None:
    evidence = tmp_path / "post-publish-evidence.json"
    evidence.write_text(
        json.dumps(
            {
                "schema": "cleanmac.release-post-publish-evidence-input.v2",
                "surfaces": {
                    "github-release": {"status": "verified", "evidence_refs": ["release-assets"]},
                    "pypi": {"status": "verified", "evidence_refs": ["pypi-page"]},
                    "homebrew-tap": {"status": "verified", "evidence_refs": ["tap-commit"]},
                },
            }
        ),
        encoding="utf-8",
    )

    result = render_release_post_publish_result(dist_dir="dist", assets_dir="release-assets", evidence_file=evidence)

    assert result["ready"] is False
    assert result["evidence_input"]["valid_schema"] is False
    assert "EVIDENCE_SCHEMA_MISMATCH" in {error["code"] for error in result["evidence_validation_errors"]}
    assert set(result["pending_surface_ids"]) == {"pypi", "github-release", "homebrew-tap"}


def test_post_publish_result_reports_invalid_status_and_missing_refs(tmp_path: Path) -> None:
    evidence = tmp_path / "post-publish-evidence.json"
    evidence.write_text(
        json.dumps(
            {
                "schema": "cleanmac.release-post-publish-evidence-input.v1",
                "surfaces": {
                    "github-release": {"status": "verified", "evidence_refs": []},
                    "pypi": {"status": "unknown", "evidence_refs": ["pypi-page"]},
                    "not-real": {"status": "verified", "evidence_refs": ["unexpected"]},
                },
            }
        ),
        encoding="utf-8",
    )

    result = render_release_post_publish_result(dist_dir="dist", assets_dir="release-assets", evidence_file=evidence)

    codes = {error["code"] for error in result["evidence_validation_errors"]}
    assert result["ready"] is False
    assert "UNKNOWN_POST_PUBLISH_SURFACE" in codes
    assert "INVALID_POST_PUBLISH_STATUS" in codes
    assert "POST_PUBLISH_EVIDENCE_REF_MISSING" in codes
    assert "github-release" in result["failed_surface_ids"]
    assert "pypi" in result["failed_surface_ids"]


@pytest.mark.parametrize(
    ("command", "schema"),
    [
        ("release-rehearsal", "cleanmac.release-rehearsal.v1"),
        ("release-promotion-decision", "cleanmac.release-promotion-decision.v1"),
        ("release-rollback-plan", "cleanmac.release-rollback-plan.v1"),
        ("release-post-publish-verification", "cleanmac.release-post-publish-verification.v1"),
        ("release-post-publish-result", "cleanmac.release-post-publish-result.v1"),
        ("release-post-publish-evidence-template", "cleanmac.release-post-publish-evidence-template.v1"),
    ],
)
def test_cli_emits_release_orchestration_reports(command: str, schema: str) -> None:
    result = subprocess.run(
        [sys.executable, str(CLI), "--json", command],
        text=True,
        capture_output=True,
        check=True,
    )
    payload = json.loads(result.stdout)

    assert payload["schema"] == schema
    assert payload["destructive"] is False
    assert payload["dry_run"] is True
