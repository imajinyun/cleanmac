from __future__ import annotations

import unittest

from cleancli.ai_contract import render_ai_intent_hints, render_ai_recommended_workflow, render_ai_tool_contract
from cleancli.core import render_ai_intent_hints as render_core_ai_intent_hints
from cleancli.core import render_ai_recommended_workflow as render_core_ai_recommended_workflow
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
