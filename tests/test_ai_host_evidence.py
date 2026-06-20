from __future__ import annotations

import json
import subprocess
import sys
import unittest
from pathlib import Path

from cleancli.ai_versioning import validate_contract_payload
from cleancli.core import render_ai_host_evidence_report

PROJECT_ROOT = Path(__file__).resolve().parent.parent
CLI = PROJECT_ROOT / "cleanmac.py"


class AIHostEvidenceTests(unittest.TestCase):
    def test_evidence_report_is_ready_and_non_destructive(self) -> None:
        report = render_ai_host_evidence_report()

        self.assertEqual(report["schema"], "cleanmac.ai-host-evidence.v1")
        self.assertFalse(report["destructive"])
        self.assertTrue(report["dry_run"])
        self.assertTrue(report["ready"], report)
        self.assertEqual(report["source"], "cleanmac-ai-host-evidence")
        self.assertEqual(report["preflight"]["schema"], "cleanmac.ai-host-preflight.v1")
        self.assertTrue(report["preflight"]["ready"], report["preflight"])
        self.assertEqual(report["contract_validation"]["schema"], "cleanmac.ai-contract-validation-summary.v1")
        self.assertTrue(report["contract_validation"]["valid"], report["contract_validation"])
        self.assertEqual(report["release_readiness"]["schema"], "cleanmac.release-readiness.v1")
        self.assertIn("failed_gate_ids", report["release_readiness"])
        self.assertEqual(report["release_readiness"]["required_for"], "release-review")
        self.assertEqual(
            report["release_readiness"]["not_required_for"],
            "runtime-readonly-ai-host-discovery",
        )
        checks = {check["id"]: check for check in report["evidence_checks"]}
        self.assertTrue(checks["release-readiness-resource-advertised"]["passed"])
        self.assertTrue(checks["mcp-meta-index-advertised"]["passed"])
        self.assertTrue(checks["mcp-meta-index-valid"]["passed"])
        self.assertTrue(checks["mcp-resource-index-advertised"]["passed"])
        self.assertTrue(checks["mcp-resource-catalog-valid"]["passed"])
        self.assertTrue(checks["mcp-prompt-index-advertised"]["passed"])
        self.assertTrue(checks["mcp-prompt-catalog-valid"]["passed"])
        self.assertTrue(checks["mcp-tool-index-advertised"]["passed"])
        self.assertTrue(checks["mcp-tool-catalog-valid"]["passed"])
        self.assertEqual(report["mcp_meta_index"]["missing_index_uris"], [])
        self.assertGreater(report["mcp_resource_catalog"]["resource_count"], 0)
        self.assertEqual(report["mcp_resource_catalog"]["duplicate_uris"], [])
        self.assertGreater(report["mcp_prompt_catalog"]["prompt_count"], 0)
        self.assertEqual(report["mcp_prompt_catalog"]["duplicate_names"], [])
        self.assertGreater(report["mcp_tool_catalog"]["tool_count"], 0)
        self.assertEqual(report["mcp_tool_catalog"]["duplicate_names"], [])

    def test_evidence_includes_runtime_denial_samples(self) -> None:
        report = render_ai_host_evidence_report()
        samples = {sample["id"]: sample for sample in report["runtime_policy_evidence"]}

        self.assertIn("raw-command-argument-denied", samples)
        self.assertIn("destructive-missing-confirmation-denied", samples)
        self.assertFalse(samples["raw-command-argument-denied"]["decision"]["allowed"])
        self.assertFalse(samples["destructive-missing-confirmation-denied"]["decision"]["allowed"])
        raw_codes = {
            reason["code"] for reason in samples["raw-command-argument-denied"]["decision"]["blocking_reasons"]
        }
        destructive_codes = {
            reason["code"]
            for reason in samples["destructive-missing-confirmation-denied"]["decision"]["blocking_reasons"]
        }
        self.assertEqual(raw_codes, {"RAW_COMMAND_ARGUMENT_DENIED"})
        self.assertIn("HUMAN_CONFIRMATION_PHRASE_REQUIRED", destructive_codes)
        self.assertIn("CONFIRMATION_TOKEN_REQUIRED", destructive_codes)

    def test_evidence_validates_against_registered_contract_schema(self) -> None:
        report = render_ai_host_evidence_report()
        validation = validate_contract_payload("cleanmac.ai-host-evidence.v1", report)

        self.assertTrue(validation["valid"], validation)
        self.assertEqual(validation["error_count"], 0)

    def test_cli_emits_host_evidence(self) -> None:
        result = subprocess.run(
            [sys.executable, str(CLI), "--json", "ai-host-evidence"],
            text=True,
            capture_output=True,
            check=True,
        )
        report = json.loads(result.stdout)

        self.assertEqual(report["schema"], "cleanmac.ai-host-evidence.v1")
        self.assertTrue(report["ready"], report)
        self.assertIn(["make", "ai-host-smoke"], report["release_gate_commands"])
        self.assertIn(["make", "release-readiness-smoke"], report["release_gate_commands"])
        self.assertIn(["cleanmac", "--json", "release-readiness"], report["release_gate_commands"])
        checks = {check["id"]: check for check in report["evidence_checks"]}
        self.assertTrue(checks["mcp-meta-index-advertised"]["passed"])
        self.assertTrue(checks["mcp-meta-index-valid"]["passed"])
        self.assertTrue(checks["mcp-resource-index-advertised"]["passed"])
        self.assertTrue(checks["mcp-resource-catalog-valid"]["passed"])
        self.assertTrue(checks["mcp-prompt-index-advertised"]["passed"])
        self.assertTrue(checks["mcp-prompt-catalog-valid"]["passed"])
        self.assertTrue(checks["mcp-tool-index-advertised"]["passed"])
        self.assertTrue(checks["mcp-tool-catalog-valid"]["passed"])


if __name__ == "__main__":
    unittest.main()
