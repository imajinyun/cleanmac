"""P3-06: Error classification and AI recovery strategy tests."""

from __future__ import annotations

from cleancli.ai_errors import (
    AI_ERROR_TAXONOMY_BY_CODE,
    classify_cli_error,
    render_ai_error_report,
    render_ai_error_taxonomy,
)


def test_taxonomy_has_expected_codes() -> None:
    taxonomy = render_ai_error_taxonomy()
    codes = [entry["code"] for entry in taxonomy]
    expected = [
        "CLI_ARGUMENT_ERROR",
        "UNKNOWN_CATEGORY",
        "PLAN_CONTEXT_REQUIRED",
        "PLAN_CONTEXT_MISMATCH",
        "PLAN_STALE_OR_DRIFTED",
        "AI_GUARD_REQUIRED",
        "CONFIRMATION_TOKEN_REQUIRED",
        "CONFIRMATION_TOKEN_MISMATCH",
        "OPERATION_LOG_UNAVAILABLE",
        "SAFETY_BUDGET_EXCEEDED",
        "SELECTION_VALIDATION_FAILED",
        "LIVE_ROOT_REFUSED",
        "USER_CONFIRMATION_REQUIRED",
        "EXECUTION_REFUSED",
        "TRASH_OPERATION_FAILED",
        "PROTECTED_PATH_REJECTED",
        "SYMLINK_DETECTED",
        "HARDLINK_REPLACEMENT_FAILED",
    ]
    for code in expected:
        assert code in codes, f"Missing error code: {code}"


def test_taxonomy_each_entry_has_required_fields() -> None:
    taxonomy = render_ai_error_taxonomy()
    required = [
        "code",
        "category",
        "retryable_after_fix",
        "suggested_next_action",
        "safe_to_auto_retry",
        "requires_user_visible_summary",
        "next_allowed_tools",
    ]
    for entry in taxonomy:
        for field in required:
            assert field in entry, f"Entry {entry['code']} missing field: {field}"


def test_taxonomy_codes_are_unique() -> None:
    taxonomy = render_ai_error_taxonomy()
    codes = [entry["code"] for entry in taxonomy]
    assert len(codes) == len(set(codes))


def test_by_code_dict_matches_taxonomy() -> None:
    taxonomy = render_ai_error_taxonomy()
    assert len(AI_ERROR_TAXONOMY_BY_CODE) == len(taxonomy)
    for entry in taxonomy:
        assert entry["code"] in AI_ERROR_TAXONOMY_BY_CODE


def test_classify_argument_error() -> None:
    result = classify_cli_error("unrecognized arguments", exit_code=2)
    assert result["code"] == "CLI_ARGUMENT_ERROR"
    assert result["safe_to_auto_retry"] is True


def test_classify_unknown_category() -> None:
    result = classify_cli_error("Unknown category: bogus", exit_code=1)
    assert result["code"] == "UNKNOWN_CATEGORY"


def test_classify_plan_context_mismatch() -> None:
    result = classify_cli_error("Plan root mismatch: /tmp != /", exit_code=1)
    assert result["code"] == "PLAN_CONTEXT_MISMATCH"
    assert result["safe_to_auto_retry"] is False


def test_classify_confirmation_token_required() -> None:
    result = classify_cli_error("confirmation token is required", exit_code=1)
    assert result["code"] == "CONFIRMATION_TOKEN_REQUIRED"
    assert result["safe_to_auto_retry"] is False


def test_classify_safety_budget_exceeded() -> None:
    result = classify_cli_error("exceeds --max-items budget", exit_code=1)
    assert result["code"] == "SAFETY_BUDGET_EXCEEDED"


def test_classify_selection_validation_failed() -> None:
    result = classify_cli_error("Review selection is invalid", exit_code=1)
    assert result["code"] == "SELECTION_VALIDATION_FAILED"
    assert result["safe_to_auto_retry"] is True


def test_classify_live_root_refused() -> None:
    result = classify_cli_error("live root '/' is not allowed", exit_code=1)
    assert result["code"] == "LIVE_ROOT_REFUSED"
    assert result["safe_to_auto_retry"] is False


def test_classify_user_confirmation_required() -> None:
    result = classify_cli_error("Cannot proceed without --yes", exit_code=1)
    assert result["code"] == "USER_CONFIRMATION_REQUIRED"


def test_classify_trash_operation_failed() -> None:
    result = classify_cli_error("Trash root is a symlink", exit_code=1)
    assert result["code"] == "TRASH_OPERATION_FAILED"
    assert result["retryable_after_fix"] is True


def test_classify_protected_path_rejected() -> None:
    result = classify_cli_error("Protected path rejected", exit_code=1)
    assert result["code"] == "PROTECTED_PATH_REJECTED"
    assert result["safe_to_auto_retry"] is False


def test_classify_symlink_detected() -> None:
    result = classify_cli_error("symlink unsafe rejected", exit_code=1)
    assert result["code"] == "SYMLINK_DETECTED"


def test_classify_hardlink_failed() -> None:
    result = classify_cli_error("hardlink replace fail", exit_code=1)
    assert result["code"] == "HARDLINK_REPLACEMENT_FAILED"
    assert result["retryable_after_fix"] is True


def test_classify_fallback_to_execution_refused() -> None:
    result = classify_cli_error("some random error", exit_code=1)
    assert result["code"] == "EXECUTION_REFUSED"


def test_error_report_has_schema() -> None:
    report = render_ai_error_report("test error", argv=["cleanmac", "clean"], exit_code=1)
    assert report["schema"] == "cleanmac.ai-error.v1"
    assert report["ok"] is False
    assert report["destructive_operation_started"] is False


def test_error_report_has_recovery_commands() -> None:
    report = render_ai_error_report("Plan root mismatch", argv=["cleanmac", "clean", "--execute"], exit_code=1)
    assert "error" in report
    assert "recovery_commands" in report["error"]
    assert len(report["error"]["recovery_commands"]) > 0


def test_error_report_next_allowed_tools() -> None:
    report = render_ai_error_report(
        "confirmation token is required",
        argv=["cleanmac", "clean", "--execute"],
        exit_code=1,
    )
    assert "next_allowed_tools" in report
    assert isinstance(report["next_allowed_tools"], list)


def test_category_values_are_consistent() -> None:
    taxonomy = render_ai_error_taxonomy()
    categories = {entry["category"] for entry in taxonomy}
    # Each category should have at least one code
    assert len(categories) >= 10
    # No empty categories
    assert "" not in categories


def test_retryable_flags_are_booleans() -> None:
    taxonomy = render_ai_error_taxonomy()
    for entry in taxonomy:
        assert isinstance(entry["retryable_after_fix"], bool), f"{entry['code']} retryable not bool"
        assert isinstance(entry["safe_to_auto_retry"], bool), f"{entry['code']} safe_to_auto_retry not bool"
        assert isinstance(entry["requires_user_visible_summary"], bool), (
            f"{entry['code']} requires_user_visible_summary not bool"
        )


def test_error_categories_have_descriptive_suggestions() -> None:
    taxonomy = render_ai_error_taxonomy()
    for entry in taxonomy:
        assert len(entry["suggested_next_action"]) > 10, (
            f"{entry['code']} has too short suggestion: {entry['suggested_next_action']}"
        )
