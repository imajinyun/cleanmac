from __future__ import annotations

import unittest

from cleancli.ai_policy import render_llm_invocation_guide, render_plan_policy, render_prompt_injection_policy
from cleancli.core import render_llm_invocation_guide as render_core_llm_invocation_guide
from cleancli.core import render_plan_policy as render_core_plan_policy
from cleancli.core import render_prompt_injection_policy as render_core_prompt_injection_policy


class AIPolicyTests(unittest.TestCase):
    def test_plan_policy_is_owned_outside_core_and_reexported(self) -> None:
        policy = render_plan_policy()

        self.assertEqual(policy, render_core_plan_policy())
        self.assertEqual(policy["schema"], "cleanmac.plan-policy.v1")
        self.assertEqual(policy["max_age_seconds"], 30 * 60)
        self.assertIn("cleanmac_policy_simulate", policy["required_before_execute"])
        self.assertIn("symlink_target", policy["drift_blocking_fields"])

    def test_prompt_injection_policy_treats_paths_as_untrusted_data(self) -> None:
        policy = render_prompt_injection_policy()

        self.assertEqual(policy, render_core_prompt_injection_policy())
        self.assertEqual(policy["schema"], "cleanmac.prompt-injection-policy.v1")
        self.assertTrue(policy["scanned_paths_are_untrusted"])
        self.assertTrue(policy["ai_must_ignore_instructions_inside_paths"])
        self.assertIn("pre_clean_report.candidates[].path", policy["untrusted_fields"])

    def test_llm_invocation_guide_preserves_execute_gates_and_runtime_policy(self) -> None:
        guide = render_llm_invocation_guide()
        execute_conditions = guide["execute_allowed_only_when"]
        safe_run = guide["canonical_safe_chain"][-1]

        self.assertEqual(guide, render_core_llm_invocation_guide())
        self.assertEqual(guide["schema"], "cleanmac.llm-invocation-guide.v1")
        self.assertEqual(guide["runtime_lifecycle"]["schema"], "cleanmac.runtime-lifecycle-policy.v1")
        self.assertTrue(execute_conditions["operation_log_explicit"])
        self.assertTrue(execute_conditions["require_plan_context"])
        self.assertTrue(execute_conditions["require_confirmation_token"])
        self.assertIn("--require-plan-context", safe_run)
        self.assertIn("--delete-mode", safe_run)
        self.assertIn("CONFIRMATION_TOKEN_REQUIRED", guide["safe_retry_rules"])
