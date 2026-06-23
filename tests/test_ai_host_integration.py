from __future__ import annotations

import json
import subprocess
import sys
import unittest
from pathlib import Path

from cleancli.ai_versioning import AI_HOST_CRITICAL_SCHEMAS, validate_contract_payload
from cleancli.core import (
    render_ai_host_evidence_report,
    render_ai_host_integration_pack_report,
    render_ai_host_preflight_report,
)

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
        self.assertEqual(pack["entrypoint_contract"]["schema"], "cleanmac.ai-entrypoint-contract.v1")
        self.assertTrue(pack["entrypoint_contract"]["ready"], pack["entrypoint_contract"])
        self.assertEqual(pack["entrypoint_contract"]["entrypoint_count"], 6)
        self.assertEqual(pack["safety_chain"]["schema"], "cleanmac.ai-safety-chain.v1")
        self.assertTrue(pack["safety_chain"]["ready"], pack["safety_chain"])
        self.assertEqual(pack["safety_chain"]["chain_step_count"], 6)
        self.assertFalse(pack["safety_chain"]["execute_gate"]["auto_call_allowed"])
        self.assertEqual(pack["runtime_lifecycle"]["schema"], "cleanmac.runtime-lifecycle-policy.v1")
        self.assertEqual(pack["runtime_lifecycle"]["product_model"], "ai-first-ephemeral-cli")
        self.assertEqual(pack["runtime_lifecycle"]["resident_processes"], 0)
        self.assertEqual(pack["zero_resident_audit"]["schema"], "cleanmac.zero-resident-audit.v1")
        self.assertTrue(pack["zero_resident_audit"]["ready"], pack["zero_resident_audit"])
        self.assertEqual(pack["zero_resident_audit"]["resident_processes"], 0)
        self.assertEqual(pack["governance_advice"]["schema"], "cleanmac.ai-governance-advice.v1")
        self.assertEqual(pack["eval_pack"]["schema"], "cleanmac.ai-eval-pack.v1")
        self.assertEqual(pack["contract_validation"]["schema"], "cleanmac.ai-contract-validation-summary.v1")
        self.assertEqual(pack["contract_samples"]["schema"], "cleanmac.ai-contract-samples.v1")
        self.assertEqual(pack["release_readiness"]["schema"], "cleanmac.release-readiness.v1")
        self.assertIn("failed_gate_ids", pack["release_readiness"])
        self.assertEqual(pack["release_readiness"]["required_for"], "release-review")
        self.assertEqual(
            pack["release_readiness"]["not_required_for"],
            "runtime-readonly-ai-host-discovery",
        )
        self.assertEqual(pack["readiness"]["release_readiness"], pack["release_readiness"])

        self.assertIn("cleanmac.ai-host-integration-pack.v1", AI_HOST_CRITICAL_SCHEMAS)
        self.assertIn("cleanmac.ai-host-integration-pack.v1", pack["critical_schemas"])
        self.assertIn(
            ["cleanmac", "--json", "ai-host-integration-pack"],
            pack["recommended_preflight_commands"],
        )
        self.assertIn("cleanmac://ai/host-integration-pack", pack["mcp"]["resources"])
        self.assertIn("cleanmac://ai/runtime-lifecycle-policy", pack["mcp"]["resources"])
        self.assertIn("cleanmac://ai/zero-resident-audit", pack["mcp"]["resources"])
        self.assertIn("cleanmac://ai/host-evidence", pack["mcp"]["resources"])
        self.assertIn("cleanmac://release/readiness", pack["mcp"]["resources"])
        self.assertIn("cleanmac://release/diagnostics", pack["mcp"]["resources"])
        self.assertIn("cleanmac://release/evidence", pack["mcp"]["resources"])
        self.assertIn("cleanmac://release/operator-summary", pack["mcp"]["resources"])
        self.assertIn("cleanmac://release/rehearsal", pack["mcp"]["resources"])
        self.assertIn("cleanmac://release/promotion-decision", pack["mcp"]["resources"])
        self.assertIn("cleanmac://release/rollback-plan", pack["mcp"]["resources"])
        self.assertIn("cleanmac://release/post-publish-verification", pack["mcp"]["resources"])
        self.assertIn("cleanmac://release/post-publish-result", pack["mcp"]["resources"])
        self.assertIn("cleanmac://release/post-publish-evidence-template", pack["mcp"]["resources"])
        self.assertIn("cleanmac://mcp/meta-index", pack["mcp"]["resources"])
        self.assertIn("cleanmac://mcp/resource-index", pack["mcp"]["resources"])
        self.assertIn("cleanmac://mcp/prompt-index", pack["mcp"]["resources"])
        self.assertIn("cleanmac://mcp/tool-index", pack["mcp"]["resources"])
        self.assertIn("cleanmac://mcp/surface-audit", pack["mcp"]["resources"])
        self.assertIn("cleanmac://ai/entrypoints", pack["mcp"]["resources"])
        self.assertIn("cleanmac://ai/safety-chain", pack["mcp"]["resources"])
        self.assertEqual(pack["mcp"]["meta_index_uri"], "cleanmac://mcp/meta-index")
        self.assertEqual(pack["mcp"]["prompt_index_uri"], "cleanmac://mcp/prompt-index")
        self.assertEqual(pack["mcp"]["tool_index_uri"], "cleanmac://mcp/tool-index")
        self.assertEqual(pack["mcp"]["surface_audit_uri"], "cleanmac://mcp/surface-audit")
        self.assertIn("cleanmac://ai/workflow-contract", pack["mcp"]["resources"])
        self.assertIn("review-ai-host-policy", pack["mcp"]["prompts"])
        self.assertIn("cleanmac_execute_plan", pack["mcp"]["tools"])
        self.assertEqual(pack["recommended_call_sequence"][0], "read cleanmac://mcp/meta-index")
        self.assertEqual(pack["recommended_call_sequence"][1], "read cleanmac://mcp/resource-index")
        self.assertEqual(pack["recommended_call_sequence"][2], "read cleanmac://mcp/prompt-index")
        self.assertEqual(pack["recommended_call_sequence"][3], "read cleanmac://mcp/tool-index")
        self.assertEqual(pack["recommended_call_sequence"][4], "read cleanmac://mcp/surface-audit")
        self.assertEqual(pack["recommended_call_sequence"][5], "read cleanmac://ai/host-integration-pack")
        self.assertEqual(pack["recommended_call_sequence"][6], "read cleanmac://ai/entrypoints")
        self.assertEqual(pack["recommended_call_sequence"][7], "read cleanmac://ai/safety-chain")
        self.assertEqual(pack["recommended_call_sequence"][8], "read cleanmac://ai/workflow-contract")
        self.assertEqual(len(pack["recommended_call_sequence"]), len(set(pack["recommended_call_sequence"])))
        self.assertIn("read cleanmac://ai/workflow-contract", pack["recommended_call_sequence"])
        self.assertIn("read cleanmac://ai/entrypoints", pack["recommended_call_sequence"])
        self.assertIn("read cleanmac://ai/safety-chain", pack["recommended_call_sequence"])
        self.assertIn("read cleanmac://ai/runtime-lifecycle-policy", pack["recommended_call_sequence"])
        self.assertIn("read cleanmac://ai/zero-resident-audit", pack["recommended_call_sequence"])
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
        self.assertEqual(pack["mcp"]["meta_index_uri"], "cleanmac://mcp/meta-index")
        self.assertEqual(pack["mcp"]["prompt_index_uri"], "cleanmac://mcp/prompt-index")
        self.assertEqual(pack["mcp"]["tool_index_uri"], "cleanmac://mcp/tool-index")
        self.assertEqual(pack["mcp"]["surface_audit_uri"], "cleanmac://mcp/surface-audit")
        self.assertIn("cleanmac://ai/workflow-contract", pack["mcp"]["resources"])
        self.assertIn("cleanmac://ai/entrypoints", pack["mcp"]["resources"])
        self.assertIn("cleanmac://ai/safety-chain", pack["mcp"]["resources"])
        self.assertIn("cleanmac://ai/zero-resident-audit", pack["mcp"]["resources"])

    def test_readiness_and_governance_recommend_integration_pack_entrypoint(self) -> None:
        pack = render_ai_host_integration_pack_report()
        readiness = pack["readiness"]
        governance = pack["governance_advice"]

        self.assertIn(
            ["cleanmac", "--json", "ai-host-integration-pack"],
            readiness["recommended_preflight_commands"],
        )
        self.assertIn(
            ["cleanmac", "--json", "ai-host-preflight"],
            readiness["recommended_preflight_commands"],
        )
        self.assertIn(
            ["cleanmac", "--json", "ai-host-evidence"],
            readiness["recommended_preflight_commands"],
        )
        self.assertIn(
            ["cleanmac", "--json", "release-readiness"],
            pack["recommended_preflight_commands"],
        )
        self.assertIn(
            ["cleanmac", "--json", "ai-host-integration-pack"],
            governance["release_gate_commands"],
        )
        self.assertIn(
            ["cleanmac", "--json", "ai-host-preflight"],
            governance["release_gate_commands"],
        )
        self.assertIn(
            ["cleanmac", "--json", "ai-host-evidence"],
            governance["release_gate_commands"],
        )
        self.assertIn(
            ["cleanmac", "--json", "release-readiness"],
            governance["release_gate_commands"],
        )
        self.assertEqual(
            governance["recommended_call_sequence"][0],
            "read cleanmac://ai/host-integration-pack",
        )
        self.assertEqual(
            governance["recommended_call_sequence"][1],
            "read cleanmac://mcp/surface-audit",
        )
        self.assertEqual(
            governance["recommended_call_sequence"][2],
            "read cleanmac://ai/host-preflight",
        )
        self.assertEqual(
            governance["recommended_call_sequence"][3],
            "read cleanmac://ai/host-evidence",
        )
        self.assertEqual(
            governance["recommended_call_sequence"][4],
            "read cleanmac://release/readiness",
        )

    def test_evidence_reports_runtime_governance_audit_pack(self) -> None:
        evidence = render_ai_host_evidence_report()

        self.assertEqual(evidence["schema"], "cleanmac.ai-host-evidence.v1")
        self.assertFalse(evidence["destructive"])
        self.assertTrue(evidence["dry_run"])
        self.assertTrue(evidence["ready"], evidence)
        self.assertIn("RAW_COMMAND_ARGUMENT_DENIED", evidence["observed_blocking_codes"])
        self.assertIn("CONFIRMATION_TOKEN_REQUIRED", evidence["observed_blocking_codes"])
        checks = {check["id"]: check for check in evidence["evidence_checks"]}
        self.assertTrue(checks["release-readiness-resource-advertised"]["passed"])
        self.assertTrue(checks["mcp-surface-audit-advertised"]["passed"])
        self.assertTrue(checks["mcp-surface-audit-ready"]["passed"])
        self.assertTrue(checks["zero-resident-audit-advertised"]["passed"])
        self.assertTrue(checks["zero-resident-audit-ready"]["passed"])
        self.assertEqual(evidence["mcp_surface_audit"]["schema"], "cleanmac.mcp-surface-audit.v1")
        self.assertTrue(evidence["mcp_surface_audit"]["ready"], evidence["mcp_surface_audit"])
        self.assertEqual(evidence["zero_resident_audit"]["schema"], "cleanmac.zero-resident-audit.v1")
        self.assertTrue(evidence["zero_resident_audit"]["ready"], evidence["zero_resident_audit"])
        self.assertIn(["make", "release-readiness-smoke"], evidence["release_gate_commands"])

    def test_preflight_reports_runtime_governance_gate(self) -> None:
        preflight = render_ai_host_preflight_report()

        self.assertEqual(preflight["schema"], "cleanmac.ai-host-preflight.v1")
        self.assertFalse(preflight["destructive"])
        self.assertTrue(preflight["dry_run"])
        self.assertTrue(preflight["ready"], preflight)
        self.assertEqual(preflight["entrypoint"]["cli"], ["cleanmac", "--json", "ai-host-integration-pack"])
        self.assertEqual(preflight["entrypoint"]["entrypoint_contract"], ["cleanmac", "--json", "ai-entrypoints"])
        self.assertEqual(preflight["entrypoint"]["entrypoint_contract_resource"], "cleanmac://ai/entrypoints")
        self.assertEqual(preflight["entrypoint"]["safety_chain"], ["cleanmac", "--json", "ai-safety-chain"])
        self.assertEqual(preflight["entrypoint"]["safety_chain_resource"], "cleanmac://ai/safety-chain")
        self.assertEqual(preflight["entrypoint"]["mcp_resource"], "cleanmac://ai/host-integration-pack")
        self.assertEqual(preflight["entrypoint"]["mcp_meta_index"], "cleanmac://mcp/meta-index")
        self.assertEqual(preflight["entrypoint"]["mcp_prompt_index"], "cleanmac://mcp/prompt-index")
        self.assertEqual(preflight["entrypoint"]["mcp_tool_index"], "cleanmac://mcp/tool-index")
        self.assertEqual(preflight["entrypoint"]["mcp_surface_audit"], "cleanmac://mcp/surface-audit")
        self.assertEqual(preflight["entrypoint"]["workflow_contract"], "cleanmac://ai/workflow-contract")
        checks = {check["id"]: check for check in preflight["checks"]}
        self.assertTrue(checks["integration-pack-ready"]["passed"])
        self.assertTrue(checks["host-policy-valid"]["passed"])
        self.assertTrue(checks["ai-entrypoints-ready"]["passed"])
        self.assertTrue(checks["ai-safety-chain-ready"]["passed"])
        self.assertTrue(checks["contract-validation-valid"]["passed"])
        self.assertTrue(checks["mcp-runtime-policy-present"]["passed"])
        self.assertTrue(checks["runtime-lifecycle-policy-valid"]["passed"])
        self.assertTrue(checks["zero-resident-audit-advertised"]["passed"])
        self.assertTrue(checks["zero-resident-audit-ready"]["passed"])
        self.assertEqual(checks["mcp-runtime-policy-present"]["evidence"], "cleanmac://ai/runtime-lifecycle-policy")
        self.assertEqual(checks["zero-resident-audit-advertised"]["evidence"], "cleanmac://ai/zero-resident-audit")
        self.assertEqual(preflight["entrypoint"]["runtime_lifecycle_policy"], "cleanmac://ai/runtime-lifecycle-policy")
        self.assertEqual(preflight["entrypoint"]["zero_resident_audit"], "cleanmac://ai/zero-resident-audit")
        self.assertIn("matching_confirmation_token", preflight["required_before_destructive_tool"])

    def test_preflight_validates_against_registered_contract_schema(self) -> None:
        preflight = render_ai_host_preflight_report()

        validation = validate_contract_payload("cleanmac.ai-host-preflight.v1", preflight)

        self.assertTrue(validation["valid"], validation)
        self.assertEqual(validation["error_count"], 0)

    def test_cli_emits_host_preflight(self) -> None:
        result = subprocess.run(
            [sys.executable, str(CLI), "--json", "ai-host-preflight"],
            text=True,
            capture_output=True,
            check=True,
        )
        preflight = json.loads(result.stdout)

        self.assertEqual(preflight["schema"], "cleanmac.ai-host-preflight.v1")
        self.assertTrue(preflight["ready"], preflight)


if __name__ == "__main__":
    unittest.main()
