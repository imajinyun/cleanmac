from __future__ import annotations

import unittest

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


if __name__ == "__main__":
    unittest.main()
