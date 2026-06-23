from __future__ import annotations

import unittest

from cleancli.ai_contract import (
    render_ai_entrypoint_contract,
    render_ai_intent_hints,
    render_ai_recommended_workflow,
    render_ai_safety_chain_contract,
    render_ai_tool_contract,
)
from cleancli.ai_versioning import validate_contract_payload
from cleancli.core import render_ai_entrypoint_contract as render_core_ai_entrypoint_contract
from cleancli.core import render_ai_intent_hints as render_core_ai_intent_hints
from cleancli.core import render_ai_recommended_workflow as render_core_ai_recommended_workflow
from cleancli.core import render_ai_safety_chain_contract as render_core_ai_safety_chain_contract
from cleancli.core import render_ai_tool_contract as render_core_ai_tool_contract


class AIContractTests(unittest.TestCase):
    def test_ai_tool_contract_is_owned_outside_core_and_reexported(self) -> None:
        contract = render_ai_tool_contract()

        self.assertEqual(contract, render_core_ai_tool_contract())
        self.assertEqual(contract["schema"], "cleanmac.ai-tool-contract.v1")
        self.assertIn("clean run --execute", contract["confirmation_required"])
        self.assertIn("background daemon", contract["forbidden"])
        self.assertEqual(contract["error_taxonomy_schema"], "cleanmac.ai-error.v1")

    def test_ai_recommended_workflow_preserves_governed_execute_chain(self) -> None:
        workflow = render_ai_recommended_workflow()
        execute = next(step for step in workflow if step["step"] == "execute")

        self.assertEqual(workflow, render_core_ai_recommended_workflow())
        self.assertFalse(execute["auto_call_allowed"])
        self.assertTrue(execute["requires_user_confirmation"])
        self.assertIn("--require-plan-context", execute["command_template"])
        self.assertIn("--delete-mode", execute["command_template"])
        self.assertIn("--require-confirmation-token", execute["command_template"])

    def test_ai_intent_hints_remain_readonly_for_analysis_and_uninstall_planning(self) -> None:
        hints = render_ai_intent_hints()
        by_intent = {row["intent"]: row for row in hints}

        self.assertEqual(hints, render_core_ai_intent_hints())
        self.assertEqual(by_intent["large_file_analysis"]["default_delete_mode"], "none")
        self.assertEqual(by_intent["software_uninstall_planning"]["recommended_risk_policy"], "readonly")

    def test_ai_entrypoint_contract_covers_canonical_cli_surfaces(self) -> None:
        contract = render_ai_entrypoint_contract()

        self.assertEqual(contract, render_core_ai_entrypoint_contract())
        self.assertEqual(contract["schema"], "cleanmac.ai-entrypoint-contract.v1")
        self.assertTrue(contract["ready"], contract)
        self.assertEqual(contract["entrypoint_count"], 6)
        self.assertEqual(contract["missing_registry_entries"], [])
        self.assertEqual(contract["missing_schema_fragments"], [])
        by_id = {row["id"]: row for row in contract["entrypoints"]}
        self.assertEqual(by_id["discover_capabilities"]["output_schema"], "cleanmac.capabilities.v1")
        self.assertEqual(by_id["workflow_guidance"]["output_schema"], "cleanmac.workflow.v1")
        self.assertEqual(by_id["explain_report"]["output_schema"], "cleanmac.explain.v1")
        self.assertEqual(by_id["generate_ai_origin_plan"]["output_schema"], "cleanmac.plan.v1")
        self.assertEqual(by_id["normalize_review_selection"]["output_schema"], "cleanmac.review.v1")
        self.assertEqual(by_id["validate_plan"]["output_schema"], "cleanmac.validate-plan.v1")
        self.assertTrue(all(row["uses_shell"] is False for row in contract["entrypoints"]))
        self.assertTrue(all(row["auto_call_allowed"] is True for row in contract["entrypoints"]))
        self.assertTrue(all(row["destructive"] is False for row in contract["entrypoints"]))
        self.assertTrue(all(row["version_compatibility"]["compatible_major_versions"] == [1] for row in contract["entrypoints"]))

        validation = validate_contract_payload("cleanmac.ai-entrypoint-contract.v1", contract)
        self.assertTrue(validation["valid"], validation)

    def test_ai_safety_chain_contract_covers_non_bypassable_execute_path(self) -> None:
        contract = render_ai_safety_chain_contract()

        self.assertEqual(contract, render_core_ai_safety_chain_contract())
        self.assertEqual(contract["schema"], "cleanmac.ai-safety-chain.v1")
        self.assertTrue(contract["ready"], contract)
        self.assertEqual(contract["chain_id"], "plan-review-dry-run-execute")
        self.assertEqual(contract["chain_step_count"], 6)
        self.assertEqual(contract["missing_registry_entries"], [])
        self.assertEqual(contract["missing_schema_fragments"], [])

        by_id = {row["id"]: row for row in contract["chain_steps"]}
        self.assertEqual(by_id["plan"]["output_schema"], "cleanmac.plan.v1")
        self.assertEqual(by_id["validate_plan"]["output_schema"], "cleanmac.validate-plan.v1")
        self.assertEqual(by_id["review"]["produces"], ["cleanmac.review.v1", "cleanmac.review-selection.v1"])
        self.assertEqual(by_id["policy_simulate"]["output_schema"], "cleanmac.ai-policy-simulation.v1")
        self.assertEqual(by_id["dry_run"]["required_output"], "ai_confirmation_summary.confirmation_token")
        self.assertFalse(by_id["execute"]["auto_call_allowed"])
        self.assertTrue(by_id["execute"]["destructive"])
        self.assertEqual(by_id["execute"]["requires_gate_schema"], "cleanmac.execute-gate.v1")

        gate = contract["execute_gate"]
        self.assertEqual(gate["schema"], "cleanmac.execute-gate.v1")
        self.assertFalse(gate["auto_call_allowed"])
        self.assertTrue(gate["requires_human_confirmation"])
        self.assertTrue(gate["requires_matching_dry_run_confirmation_token"])
        self.assertTrue(gate["requires_trash_delete_mode"])
        self.assertTrue(gate["requires_operation_log"])
        self.assertTrue(gate["requires_plan_context_match"])
        self.assertIn("--require-plan-context", gate["required_runtime_flags"])
        self.assertIn("--delete-mode trash", gate["required_runtime_flags"])
        self.assertIn("--operation-log", gate["required_runtime_flags"])
        self.assertIn("--confirmation-token", gate["required_runtime_flags"])
        self.assertIn(["dry_run", "execute"], contract["non_bypassable_edges"])
        self.assertIn(["human_confirmation", "execute"], contract["non_bypassable_edges"])
        self.assertIn("cleanmac.execute-gate.v1", contract["required_contract_schemas"])

        validation = validate_contract_payload("cleanmac.ai-safety-chain.v1", contract)
        self.assertTrue(validation["valid"], validation)
        gate_validation = validate_contract_payload("cleanmac.execute-gate.v1", gate)
        self.assertTrue(gate_validation["valid"], gate_validation)
