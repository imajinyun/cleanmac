from __future__ import annotations

import json

from cleancli.ai_errors import classify_cli_error, render_ai_error_report, render_ai_error_taxonomy
from cleancli.core import render_ai_error_report as render_core_ai_error_report
from cleancli.core import render_ai_error_taxonomy as render_core_ai_error_taxonomy
from tests.helpers import make_sandbox, run_cli


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


def test_json_cli_argument_errors_emit_ai_safe_stderr_contract() -> None:
    result = run_cli("--json", "clean", "run", "--definitely-unknown", check=False)

    assert result.returncode == 2
    assert result.stdout == ""
    report = json.loads(result.stderr)
    assert report["schema"] == "cleanmac.ai-error.v1"
    assert report["ok"] is False
    assert report["destructive_operation_started"] is False
    assert report["error"]["code"] == "CLI_ARGUMENT_ERROR"
    assert report["error"]["exit_code"] == 2
    assert "unrecognized arguments" in report["error"]["message"]
    assert report["safe_to_auto_retry"] is True
    assert report["next_allowed_tools"] == report["error"]["next_allowed_tools"]
    assert "cleanmac_capabilities" in report["next_allowed_tools"]


def test_json_cli_safety_errors_emit_non_retryable_confirmation_contract() -> None:
    tmp, root, home = make_sandbox()
    with tmp:
        result = run_cli(
            "--root",
            str(root),
            "--home",
            str(home),
            "--json",
            "clean",
            "run",
            "--categories",
            "downloads",
            "--delete-mode",
            "trash",
            "--execute",
            "--yes",
            "--require-confirmation-token",
            check=False,
        )

        assert result.returncode != 0
        assert result.stdout == ""
        report = json.loads(result.stderr)
        assert report["schema"] == "cleanmac.ai-error.v1"
        assert report["destructive_operation_started"] is False
        assert report["error"]["code"] == "CONFIRMATION_TOKEN_REQUIRED"
        assert report["error"]["category"] == "confirmation_required"
        assert report["safe_to_auto_retry"] is False
        assert report["error"]["requires_user_visible_summary"] is True
        assert report["error"]["recovery_commands"] == [
            ["cleanmac", "--json", "clean", "run", "--plan-file", "<plan.json>"]
        ]
        assert (root / "Users/tester/Downloads/download.bin").exists()
