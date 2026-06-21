from __future__ import annotations

import unittest

from cleancli.ai_errors import classify_cli_error, render_ai_error_report, render_ai_error_taxonomy
from cleancli.core import render_ai_error_report as render_core_ai_error_report
from cleancli.core import render_ai_error_taxonomy as render_core_ai_error_taxonomy


class AIErrorTests(unittest.TestCase):
    def test_ai_error_taxonomy_is_owned_outside_core_and_reexported(self) -> None:
        taxonomy = render_ai_error_taxonomy()

        self.assertEqual(taxonomy, render_core_ai_error_taxonomy())
        self.assertGreaterEqual(
            {entry["code"] for entry in taxonomy},
            {
                "CLI_ARGUMENT_ERROR",
                "SELECTION_VALIDATION_FAILED",
                "OPERATION_LOG_UNAVAILABLE",
                "EXECUTION_REFUSED",
            },
        )

    def test_ai_error_report_classifies_review_selection_failures(self) -> None:
        report = render_ai_error_report(
            "software execute requires --review-selection-file",
            argv=["cleanmac", "software", "execute"],
            exit_code=1,
        )

        self.assertEqual(
            report,
            render_core_ai_error_report(
                "software execute requires --review-selection-file",
                argv=["cleanmac", "software", "execute"],
                exit_code=1,
            ),
        )
        self.assertEqual(report["schema"], "cleanmac.ai-error.v1")
        self.assertEqual(report["error"]["code"], "SELECTION_VALIDATION_FAILED")
        self.assertTrue(report["safe_to_auto_retry"])
        self.assertEqual(
            report["error"]["recovery_commands"],
            [["cleanmac", "--json", "review", "--input-file", "<plan.json>", "--selection-file", "<selection.json>"]],
        )

    def test_ai_error_classifier_keeps_argument_errors_machine_readable(self) -> None:
        classification = classify_cli_error("invalid choice: bad", exit_code=2)

        self.assertEqual(classification["code"], "CLI_ARGUMENT_ERROR")
        self.assertTrue(classification["safe_to_auto_retry"])
        self.assertEqual(classification["next_allowed_tools"], ["cleanmac_capabilities", "cleanmac_list_categories"])
