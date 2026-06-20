from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from cleancli.core import (
    render_release_diagnostics_report,
    render_release_evidence_report,
    render_release_manifest_evidence,
    render_release_operator_summary,
    render_release_promotion_decision_report,
    render_release_readiness_report,
    render_release_rehearsal_report,
    render_release_rollback_plan_report,
)
from cleancli.release_artifacts import build_release_artifact_manifest
from cleancli.release_readiness import render_release_readiness


class ReleaseReadinessTests(unittest.TestCase):
    def test_release_readiness_reports_ready_when_all_gates_pass(self) -> None:
        report = render_release_readiness(
            ai_host_integration_pack={"schema": "cleanmac.ai-host-integration-pack.v1", "ready": True},
            ai_host_preflight={"schema": "cleanmac.ai-host-preflight.v1", "ready": True},
            ai_host_evidence={"schema": "cleanmac.ai-host-evidence.v1", "ready": True},
            contract_validation={"schema": "cleanmac.ai-contract-validation-summary.v1", "ready": True, "valid": True},
            eval_smoke={"schema": "cleanmac.ai-eval-run.v1", "passed": True, "passed_count": 1, "failed_count": 0},
            release_manifest={"schema": "cleanmac.release-artifact-manifest.v1", "valid": True},
            required_make_targets=[
                "quality-check",
                "governed-execution-smoke",
                "ai-host-smoke",
                "release-artifacts-smoke",
            ],
        )

        self.assertEqual(report["schema"], "cleanmac.release-readiness.v1")
        self.assertFalse(report["destructive"])
        self.assertTrue(report["dry_run"])
        self.assertTrue(report["ready"])
        self.assertEqual(report["readiness_score"], {"passed": 7, "total": 7, "level": "release-ready"})
        self.assertEqual(report["failed_gate_ids"], [])
        self.assertIn(["make", "governed-execution-smoke"], report["release_gate_commands"])
        self.assertTrue(all(gate["severity"] == "none" for gate in report["gates"]))
        self.assertTrue(all("next_actions" in gate for gate in report["gates"]))

    def test_release_readiness_fails_closed_when_evidence_is_missing(self) -> None:
        report = render_release_readiness(
            ai_host_integration_pack={"schema": "cleanmac.ai-host-integration-pack.v1", "ready": True},
            ai_host_preflight={"schema": "cleanmac.ai-host-preflight.v1", "ready": False},
            ai_host_evidence={"schema": "cleanmac.ai-host-evidence.v1", "ready": False},
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

        self.assertFalse(report["ready"])
        self.assertEqual(report["readiness_score"], {"passed": 2, "total": 7, "level": "blocked"})
        self.assertIn("ai-host-preflight-ready", report["failed_gate_ids"])
        self.assertIn("release-artifact-manifest-valid", report["failed_gate_ids"])
        self.assertTrue(report["manual_review_required"])
        artifact_gate = {gate["id"]: gate for gate in report["gates"]}["release-artifact-manifest-valid"]
        self.assertEqual(artifact_gate["blocking_code"], "RELEASE_ARTIFACT_MANIFEST_MISSING")
        self.assertIn(["make", "release-artifacts-smoke"], artifact_gate["next_actions"])

    def test_release_readiness_invariants_match_gate_results(self) -> None:
        report = render_release_readiness(
            ai_host_integration_pack={"schema": "cleanmac.ai-host-integration-pack.v1", "ready": True},
            ai_host_preflight={"schema": "cleanmac.ai-host-preflight.v1", "ready": True},
            ai_host_evidence={"schema": "cleanmac.ai-host-evidence.v1", "ready": True},
            contract_validation={"schema": "cleanmac.ai-contract-validation-summary.v1", "ready": True, "valid": True},
            eval_smoke={"schema": "cleanmac.ai-eval-run.v1", "passed": True, "passed_count": 1, "failed_count": 0},
            release_manifest={"schema": "cleanmac.release-artifact-manifest.v1", "valid": False},
            required_make_targets=["quality-check", "release-artifacts-smoke"],
        )

        failed_gate_ids = {gate["id"] for gate in report["gates"] if not gate["passed"]}
        self.assertEqual(report["ready"], report["failed_gate_ids"] == [])
        self.assertEqual(report["readiness_score"]["total"], len(report["gates"]))
        self.assertEqual(set(report["failed_gate_ids"]), failed_gate_ids)
        self.assertTrue(
            all(
                {"id", "passed", "evidence_schema", "severity", "next_actions"} <= set(gate) for gate in report["gates"]
            )
        )

    def test_release_manifest_evidence_uses_explicit_directories(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            dist = root / "dist"
            assets = root / "release-assets"
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

        self.assertEqual(evidence["schema"], "cleanmac.release-artifact-manifest.v1")
        self.assertTrue(evidence["valid"], evidence)
        self.assertEqual(evidence["path"], str(assets / "ARTIFACT-MANIFEST.json"))

    def test_release_diagnostics_and_operator_summary_explain_missing_artifacts(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            dist = root / "dist"
            assets = root / "release-assets"
            dist.mkdir()
            assets.mkdir()

            diagnostics = render_release_diagnostics_report(dist_dir=dist, assets_dir=assets)
            summary = render_release_operator_summary(dist_dir=dist, assets_dir=assets)

        self.assertEqual(diagnostics["schema"], "cleanmac.release-diagnostics.v1")
        self.assertFalse(diagnostics["ready"])
        self.assertIn("release-artifact-manifest-valid", diagnostics["failed_gate_ids"])
        self.assertEqual(diagnostics["artifacts"]["error_code"], "RELEASE_ARTIFACT_MANIFEST_MISSING")
        self.assertEqual(summary["schema"], "cleanmac.release-operator-summary.v1")
        self.assertEqual(summary["status"], "blocked")
        self.assertEqual(summary["must_fix_first"][0]["gate_id"], "release-artifact-manifest-valid")

    def test_release_evidence_bundle_uses_readiness_and_assets(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
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
            rollback_plan = render_release_rollback_plan_report(dist_dir=dist, assets_dir=assets)
            (assets / "RELEASE-ROLLBACK-PLAN.json").write_text(json.dumps(rollback_plan), encoding="utf-8")
            (assets / "RELEASE-REHEARSAL.json").write_text("{}", encoding="utf-8")
            (assets / "RELEASE-PROMOTION-DECISION.json").write_text("{}", encoding="utf-8")
            rehearsal = render_release_rehearsal_report(dist_dir=dist, assets_dir=assets)
            (assets / "RELEASE-REHEARSAL.json").write_text(json.dumps(rehearsal), encoding="utf-8")
            promotion = render_release_promotion_decision_report(dist_dir=dist, assets_dir=assets)
            (assets / "RELEASE-PROMOTION-DECISION.json").write_text(json.dumps(promotion), encoding="utf-8")

            evidence = render_release_evidence_report(dist_dir=dist, assets_dir=assets)

        self.assertEqual(evidence["schema"], "cleanmac.release-evidence.v1")
        self.assertTrue(evidence["ready"], evidence)
        self.assertEqual(evidence["assets"]["missing"], [])


def test_pytest_release_readiness_fixture_roundtrip_preserves_unittest_gate(tmp_path: Path) -> None:
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


if __name__ == "__main__":
    unittest.main()
