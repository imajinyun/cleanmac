from __future__ import annotations

from cleancli.ai_errors import classify_cli_error, render_ai_error_report, render_ai_error_taxonomy
from cleancli.core import render_ai_error_report as render_core_ai_error_report
from cleancli.core import render_ai_error_taxonomy as render_core_ai_error_taxonomy


def test_ai_error_taxonomy_is_owned_outside_core_and_reexported() -> None:
    taxonomy = render_ai_error_taxonomy()

    assert taxonomy == render_core_ai_error_taxonomy()
    assert {entry["code"] for entry in taxonomy} >= {
        "CLI_ARGUMENT_ERROR",
        "SELECTION_VALIDATION_FAILED",
        "OPERATION_LOG_UNAVAILABLE",
        "EXECUTION_REFUSED",
    }


def test_ai_error_report_classifies_review_selection_failures() -> None:
    report = render_ai_error_report(
        "software execute requires --review-selection-file",
        argv=["cleanmac", "software", "execute"],
        exit_code=1,
    )

    assert report == render_core_ai_error_report(
        "software execute requires --review-selection-file",
        argv=["cleanmac", "software", "execute"],
        exit_code=1,
    )
    assert report["schema"] == "cleanmac.ai-error.v1"
    assert report["error"]["code"] == "SELECTION_VALIDATION_FAILED"
    assert report["safe_to_auto_retry"] is True
    assert report["next_allowed_tools"] == report["error"]["next_allowed_tools"]
    assert report["error"]["next_allowed_tools"][:2] == ["cleanmac_validate_plan", "cleanmac_policy_simulate"]
    assert "cleanmac_review" in report["error"]["next_allowed_tools"]
    assert report["error"]["recovery_commands"] == [
        ["cleanmac", "--json", "review", "--input-file", "<plan.json>", "--selection-file", "<selection.json>"]
    ]


def test_ai_error_classifier_keeps_argument_errors_machine_readable() -> None:
    classification = classify_cli_error("invalid choice: bad", exit_code=2)

    assert classification["code"] == "CLI_ARGUMENT_ERROR"
    assert classification["safe_to_auto_retry"] is True
    assert classification["next_allowed_tools"][:2] == ["cleanmac_validate_plan", "cleanmac_policy_simulate"]
    assert "cleanmac_capabilities" in classification["next_allowed_tools"]
    assert "cleanmac_list_categories" in classification["next_allowed_tools"]
