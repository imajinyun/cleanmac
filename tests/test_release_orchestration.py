from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

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


class ReleaseOrchestrationTests(unittest.TestCase):
    def test_rehearsal_blocks_when_required_assets_are_missing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            dist = root / "dist"
            assets = root / "release-assets"
            dist.mkdir()
            assets.mkdir()

            rehearsal = render_release_rehearsal(dist_dir=dist, assets_dir=assets)

        self.assertEqual(rehearsal["schema"], "cleanmac.release-rehearsal.v1")
        self.assertFalse(rehearsal["ready"])
        self.assertIn("artifact-manifest", rehearsal["failed_phase_ids"])
        self.assertIn("ARTIFACT-MANIFEST.json", rehearsal["assets"]["missing"])

    def test_promotion_decision_promotes_only_when_rehearsal_evidence_is_complete(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            dist, assets = _write_ready_release_assets(Path(tmp))

            rehearsal = render_release_rehearsal(dist_dir=dist, assets_dir=assets)
            decision = render_release_promotion_decision(dist_dir=dist, assets_dir=assets)

        phases = {phase["id"]: phase for phase in rehearsal["phases"]}
        self.assertEqual(phases["release-diagnostics"]["status"], "passed")
        self.assertEqual(
            phases["release-diagnostics"]["governance_integrity"]["schema"],
            "cleanmac.governance-integrity.v1",
        )
        self.assertTrue(phases["release-diagnostics"]["governance_integrity"]["ready"])
        self.assertEqual(decision["schema"], "cleanmac.release-promotion-decision.v1")
        self.assertEqual(decision["decision"], "promote")
        self.assertTrue(decision["safe_to_publish"])
        self.assertFalse(decision["manual_review_required"])

    def test_promotion_decision_blocks_missing_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            dist = root / "dist"
            assets = root / "release-assets"
            dist.mkdir()
            assets.mkdir()

            decision = render_release_promotion_decision(dist_dir=dist, assets_dir=assets)

        self.assertEqual(decision["decision"], "block")
        self.assertFalse(decision["safe_to_publish"])
        self.assertTrue(decision["manual_review_required"])
        self.assertIn("RELEASE_ARTIFACT_MANIFEST_MISSING", decision["blocking_codes"])

    def test_promotion_decision_exposes_mcp_surface_audit_blocking_code(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            dist, assets = _write_ready_release_assets(Path(tmp))
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

        self.assertEqual(decision["decision"], "block")
        self.assertFalse(decision["safe_to_publish"])
        self.assertIn("RELEASE_READINESS_BLOCKED", decision["blocking_codes"])
        self.assertIn("MCP_SURFACE_AUDIT_NOT_READY", decision["blocking_codes"])
        self.assertIn("mcp-surface-audit-ready", decision["rehearsal_summary"]["failed_gate_ids"])

    def test_rehearsal_blocks_when_diagnostics_governance_integrity_is_not_ready(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            dist, assets = _write_ready_release_assets(Path(tmp))
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
        self.assertFalse(rehearsal["ready"])
        self.assertIn("release-diagnostics", rehearsal["failed_phase_ids"])
        self.assertEqual(phases["release-diagnostics"]["blocking_code"], "GOVERNANCE_INTEGRITY_NOT_READY")
        self.assertIn("boundary-geo-policy-single-source", phases["release-diagnostics"]["diagnostic"])
        self.assertIn(["make", "governance-integrity-smoke"], phases["release-diagnostics"]["next_actions"])
        self.assertEqual(decision["decision"], "block")
        self.assertIn("GOVERNANCE_INTEGRITY_NOT_READY", decision["blocking_codes"])

    def test_rollback_plan_is_manual_only_without_destructive_commands(self) -> None:
        plan = render_release_rollback_plan(dist_dir="dist", assets_dir="release-assets")
        forbidden = "rm " + "-rf"

        self.assertEqual(plan["schema"], "cleanmac.release-rollback-plan.v1")
        self.assertTrue(plan["manual_only"])
        self.assertIn(["cleanmac", "--json", "governance-integrity"], plan["pre_rollback_checks"])
        self.assertIn(["make", "governance-integrity-smoke"], plan["pre_rollback_checks"])
        self.assertEqual(
            {surface["id"] for surface in plan["rollback_surfaces"]}, {"pypi", "github-release", "homebrew-tap"}
        )
        self.assertNotIn(forbidden, json.dumps(plan))

    def test_post_publish_verification_is_manual_only_without_destructive_commands(self) -> None:
        plan = render_release_post_publish_verification(dist_dir="dist", assets_dir="release-assets")
        forbidden = "rm " + "-rf"

        self.assertEqual(plan["schema"], "cleanmac.release-post-publish-verification.v1")
        self.assertTrue(plan["manual_only"])
        self.assertEqual(
            {surface["id"] for surface in plan["verification_surfaces"]},
            {"pypi", "github-release", "homebrew-tap"},
        )
        self.assertIn(["cleanmac", "--json", "release-rollback-plan"], plan["incident_response_entrypoints"])
        self.assertNotIn(forbidden, json.dumps(plan))

    def test_post_publish_result_defaults_to_pending_manual_only_without_destructive_commands(self) -> None:
        result = render_release_post_publish_result(dist_dir="dist", assets_dir="release-assets")
        forbidden = "rm " + "-rf"

        self.assertEqual(result["schema"], "cleanmac.release-post-publish-result.v1")
        self.assertTrue(result["manual_only"])
        self.assertFalse(result["destructive"])
        self.assertFalse(result["ready"])
        self.assertEqual(set(result["pending_surface_ids"]), {"pypi", "github-release", "homebrew-tap"})
        self.assertIn(["cleanmac", "--json", "release-rollback-plan"], result["incident_response_entrypoints"])
        self.assertNotIn(forbidden, json.dumps(result))

    def test_post_publish_evidence_template_is_manual_only_and_complete(self) -> None:
        template = render_release_post_publish_evidence_template(dist_dir="dist", assets_dir="release-assets")
        forbidden = "rm " + "-rf"

        self.assertEqual(template["schema"], "cleanmac.release-post-publish-evidence-template.v1")
        self.assertFalse(template["destructive"])
        self.assertTrue(template["dry_run"])
        self.assertTrue(template["manual_only"])
        self.assertEqual(template["target_input_schema"], "cleanmac.release-post-publish-evidence-input.v1")
        self.assertEqual(
            set(template["template"]["surfaces"]),
            {"pypi", "github-release", "homebrew-tap"},
        )
        self.assertEqual(template["template"]["surfaces"]["pypi"]["status"], "pending")
        self.assertIn(
            ["cleanmac", "--json", "release-post-publish-result", "--evidence-file", "post-publish-evidence.json"],
            template["recommended_commands"],
        )
        self.assertNotIn(forbidden, json.dumps(template))

    def test_post_publish_result_accepts_verified_evidence_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            evidence = Path(tmp) / "post-publish-evidence.json"
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

            result = render_release_post_publish_result(
                dist_dir="dist", assets_dir="release-assets", evidence_file=evidence
            )

        self.assertTrue(result["ready"], result)
        self.assertEqual(set(result["verified_surface_ids"]), {"pypi", "github-release", "homebrew-tap"})
        self.assertEqual(result["failed_surface_ids"], [])
        self.assertEqual(result["pending_surface_ids"], [])

    def test_post_publish_result_blocks_failed_surface(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            evidence = Path(tmp) / "post-publish-evidence.json"
            evidence.write_text(
                json.dumps(
                    {
                        "schema": "cleanmac.release-post-publish-evidence-input.v1",
                        "surfaces": {"pypi": {"status": "failed", "evidence_refs": ["pypi-page"]}},
                    }
                ),
                encoding="utf-8",
            )

            result = render_release_post_publish_result(
                dist_dir="dist", assets_dir="release-assets", evidence_file=evidence
            )

        self.assertFalse(result["ready"])
        self.assertIn("pypi", result["failed_surface_ids"])
        failed_surface = next(surface for surface in result["surfaces"] if surface["id"] == "pypi")
        self.assertEqual(failed_surface["blocking_code"], "PYPI_POST_PUBLISH_FAILED")

    def test_post_publish_result_rejects_wrong_evidence_schema_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            evidence = Path(tmp) / "post-publish-evidence.json"
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

            result = render_release_post_publish_result(
                dist_dir="dist", assets_dir="release-assets", evidence_file=evidence
            )

        self.assertFalse(result["ready"])
        self.assertFalse(result["evidence_input"]["valid_schema"])
        self.assertIn("EVIDENCE_SCHEMA_MISMATCH", {error["code"] for error in result["evidence_validation_errors"]})
        self.assertEqual(set(result["pending_surface_ids"]), {"pypi", "github-release", "homebrew-tap"})

    def test_post_publish_result_reports_invalid_status_and_missing_refs(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            evidence = Path(tmp) / "post-publish-evidence.json"
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

            result = render_release_post_publish_result(
                dist_dir="dist", assets_dir="release-assets", evidence_file=evidence
            )

        codes = {error["code"] for error in result["evidence_validation_errors"]}
        self.assertFalse(result["ready"])
        self.assertIn("UNKNOWN_POST_PUBLISH_SURFACE", codes)
        self.assertIn("INVALID_POST_PUBLISH_STATUS", codes)
        self.assertIn("POST_PUBLISH_EVIDENCE_REF_MISSING", codes)
        self.assertIn("github-release", result["failed_surface_ids"])
        self.assertIn("pypi", result["failed_surface_ids"])

    def test_cli_emits_release_orchestration_reports(self) -> None:
        commands = {
            "release-rehearsal": "cleanmac.release-rehearsal.v1",
            "release-promotion-decision": "cleanmac.release-promotion-decision.v1",
            "release-rollback-plan": "cleanmac.release-rollback-plan.v1",
            "release-post-publish-verification": "cleanmac.release-post-publish-verification.v1",
            "release-post-publish-result": "cleanmac.release-post-publish-result.v1",
            "release-post-publish-evidence-template": "cleanmac.release-post-publish-evidence-template.v1",
        }
        for command, schema in commands.items():
            with self.subTest(command=command):
                result = subprocess.run(
                    [sys.executable, str(CLI), "--json", command],
                    text=True,
                    capture_output=True,
                    check=True,
                )
                payload = json.loads(result.stdout)
                self.assertEqual(payload["schema"], schema)
                self.assertFalse(payload["destructive"])
                self.assertTrue(payload["dry_run"])


if __name__ == "__main__":
    unittest.main()
