from __future__ import annotations

import json
import subprocess
import sys
import unittest
from pathlib import Path

from cleancli.ai_versioning import AI_HOST_CRITICAL_SCHEMAS, validate_contract_payload
from cleancli.core import render_ai_host_integration_pack_report

PROJECT_ROOT = Path(__file__).resolve().parent.parent
CLI = PROJECT_ROOT / "cleanmac.py"


class AIHostIntegrationPackTests(unittest.TestCase):
    def test_pack_aggregates_one_stop_host_discovery_metadata(self) -> None:
        pack = render_ai_host_integration_pack_report()

        self.assertEqual(pack["schema"], "cleanmac.ai-host-integration-pack.v1")
        self.assertFalse(pack["destructive"])
        self.assertTrue(pack["dry_run"])
        self.assertTrue(pack["ready"])
        self.assertEqual(pack["schema_registry"]["schema"], "cleanmac.ai-schema-registry.v1")
        self.assertEqual(pack["readiness"]["schema"], "cleanmac.ai-readiness.v1")
        self.assertEqual(pack["runbook"]["schema"], "cleanmac.ai-runbook.v1")
        self.assertEqual(pack["host_policy"]["schema"], "cleanmac.ai-host-policy.v1")
        self.assertEqual(pack["governance_advice"]["schema"], "cleanmac.ai-governance-advice.v1")
        self.assertEqual(pack["eval_pack"]["schema"], "cleanmac.ai-eval-pack.v1")
        self.assertEqual(pack["contract_validation"]["schema"], "cleanmac.ai-contract-validation-summary.v1")
        self.assertEqual(pack["contract_samples"]["schema"], "cleanmac.ai-contract-samples.v1")

        self.assertIn("cleanmac.ai-host-integration-pack.v1", AI_HOST_CRITICAL_SCHEMAS)
        self.assertIn("cleanmac.ai-host-integration-pack.v1", pack["critical_schemas"])
        self.assertIn(
            ["cleanmac", "--json", "ai-host-integration-pack"],
            pack["recommended_preflight_commands"],
        )
        self.assertIn("cleanmac://ai/host-integration-pack", pack["mcp"]["resources"])
        self.assertIn("read cleanmac://ai/host-integration-pack", pack["recommended_call_sequence"])

    def test_pack_validates_against_registered_contract_schema(self) -> None:
        pack = render_ai_host_integration_pack_report()

        validation = validate_contract_payload("cleanmac.ai-host-integration-pack.v1", pack)

        self.assertTrue(validation["valid"], validation)
        self.assertEqual(validation["error_count"], 0)

    def test_cli_emits_host_integration_pack(self) -> None:
        result = subprocess.run(
            [sys.executable, str(CLI), "--json", "ai-host-integration-pack"],
            text=True,
            capture_output=True,
            check=True,
        )
        pack = json.loads(result.stdout)

        self.assertEqual(pack["schema"], "cleanmac.ai-host-integration-pack.v1")
        self.assertTrue(pack["ready"])
        self.assertEqual(pack["mcp"]["resource_uri"], "cleanmac://ai/host-integration-pack")

    def test_readiness_and_governance_recommend_integration_pack_entrypoint(self) -> None:
        pack = render_ai_host_integration_pack_report()
        readiness = pack["readiness"]
        governance = pack["governance_advice"]

        self.assertIn(
            ["cleanmac", "--json", "ai-host-integration-pack"],
            readiness["recommended_preflight_commands"],
        )
        self.assertIn(
            ["cleanmac", "--json", "ai-host-integration-pack"],
            governance["release_gate_commands"],
        )
        self.assertEqual(
            governance["recommended_call_sequence"][0],
            "read cleanmac://ai/host-integration-pack",
        )


if __name__ == "__main__":
    unittest.main()
