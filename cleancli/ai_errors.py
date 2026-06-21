"""Machine-readable AI/CLI error taxonomy and recovery reports."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any


def render_ai_error_taxonomy() -> list[dict[str, Any]]:
    entries = [
        {
            "code": "CLI_ARGUMENT_ERROR",
            "category": "invalid_arguments",
            "retryable_after_fix": True,
            "suggested_next_action": "correct_arguments_and_retry_readonly_first",
        },
        {
            "code": "UNKNOWN_CATEGORY",
            "category": "invalid_category",
            "retryable_after_fix": True,
            "suggested_next_action": "call_capabilities_or_clean_list_then_retry",
        },
        {
            "code": "PLAN_CONTEXT_REQUIRED",
            "category": "missing_guard",
            "retryable_after_fix": True,
            "suggested_next_action": "add_plan_file_or_remove_require_plan_context_for_readonly_dry_run",
        },
        {
            "code": "PLAN_CONTEXT_MISMATCH",
            "category": "context_mismatch",
            "retryable_after_fix": True,
            "suggested_next_action": "regenerate_plan_for_current_root_home_context",
        },
        {
            "code": "PLAN_STALE_OR_DRIFTED",
            "category": "plan_freshness_failed",
            "retryable_after_fix": True,
            "suggested_next_action": "regenerate_plan_and_repeat_matching_dry_run",
        },
        {
            "code": "AI_GUARD_REQUIRED",
            "category": "ai_guard_missing",
            "retryable_after_fix": True,
            "suggested_next_action": "rerun_with_trash_operation_log_confirmation_token_and_plan_context",
        },
        {
            "code": "CONFIRMATION_TOKEN_REQUIRED",
            "category": "confirmation_required",
            "retryable_after_fix": True,
            "suggested_next_action": "perform_matching_dry_run_and_pass_confirmation_token_after_user_confirmation",
        },
        {
            "code": "CONFIRMATION_TOKEN_MISMATCH",
            "category": "confirmation_mismatch",
            "retryable_after_fix": True,
            "suggested_next_action": "discard_token_and_repeat_dry_run_for_exact_current_context",
        },
        {
            "code": "OPERATION_LOG_UNAVAILABLE",
            "category": "audit_log_unavailable",
            "retryable_after_fix": True,
            "suggested_next_action": "choose_writable_non_symlink_operation_log_path_then_retry",
        },
        {
            "code": "SAFETY_BUDGET_EXCEEDED",
            "category": "safety_budget_exceeded",
            "retryable_after_fix": True,
            "suggested_next_action": "narrow_scope_or_raise_budget_only_after_user_review",
        },
        {
            "code": "SELECTION_VALIDATION_FAILED",
            "category": "review_selection_invalid",
            "retryable_after_fix": True,
            "suggested_next_action": "regenerate_review_selection_for_current_plan",
        },
        {
            "code": "LIVE_ROOT_REFUSED",
            "category": "live_root_guard",
            "retryable_after_fix": False,
            "suggested_next_action": "use_sandbox_root_or_explicit_user_authorized_live_root_flow",
        },
        {
            "code": "USER_CONFIRMATION_REQUIRED",
            "category": "user_confirmation_required",
            "retryable_after_fix": True,
            "suggested_next_action": "show_dry_run_summary_and_get_explicit_user_confirmation",
        },
        {
            "code": "EXECUTION_REFUSED",
            "category": "execution_refused",
            "retryable_after_fix": False,
            "suggested_next_action": "inspect_error_message_and_return_control_to_user",
        },
    ]
    retry_policy = {
        "CLI_ARGUMENT_ERROR": {
            "safe_to_auto_retry": True,
            "requires_user_visible_summary": False,
            "next_allowed_tools": ["cleanmac_capabilities", "cleanmac_list_categories"],
        },
        "UNKNOWN_CATEGORY": {
            "safe_to_auto_retry": True,
            "requires_user_visible_summary": False,
            "next_allowed_tools": ["cleanmac_capabilities", "cleanmac_list_categories"],
        },
        "PLAN_CONTEXT_REQUIRED": {
            "safe_to_auto_retry": True,
            "requires_user_visible_summary": False,
            "next_allowed_tools": ["cleanmac_validate_plan", "cleanmac_policy_simulate"],
        },
        "PLAN_CONTEXT_MISMATCH": {
            "safe_to_auto_retry": False,
            "requires_user_visible_summary": True,
            "next_allowed_tools": ["cleanmac_generate_plan", "cleanmac_validate_plan"],
        },
        "PLAN_STALE_OR_DRIFTED": {
            "safe_to_auto_retry": False,
            "requires_user_visible_summary": True,
            "next_allowed_tools": ["cleanmac_generate_plan", "cleanmac_dry_run_plan", "cleanmac_policy_simulate"],
        },
        "AI_GUARD_REQUIRED": {
            "safe_to_auto_retry": True,
            "requires_user_visible_summary": False,
            "next_allowed_tools": ["cleanmac_policy_simulate", "cleanmac_dry_run_plan"],
        },
        "CONFIRMATION_TOKEN_REQUIRED": {
            "safe_to_auto_retry": False,
            "requires_user_visible_summary": True,
            "next_allowed_tools": ["cleanmac_dry_run_plan", "cleanmac_policy_simulate"],
        },
        "CONFIRMATION_TOKEN_MISMATCH": {
            "safe_to_auto_retry": False,
            "requires_user_visible_summary": True,
            "next_allowed_tools": ["cleanmac_dry_run_plan", "cleanmac_policy_simulate"],
        },
        "OPERATION_LOG_UNAVAILABLE": {
            "safe_to_auto_retry": True,
            "requires_user_visible_summary": False,
            "next_allowed_tools": ["cleanmac_policy_simulate"],
        },
        "SAFETY_BUDGET_EXCEEDED": {
            "safe_to_auto_retry": False,
            "requires_user_visible_summary": True,
            "next_allowed_tools": ["cleanmac_inspect", "cleanmac_generate_plan"],
        },
        "SELECTION_VALIDATION_FAILED": {
            "safe_to_auto_retry": True,
            "requires_user_visible_summary": False,
            "next_allowed_tools": ["cleanmac_review", "cleanmac_dry_run_plan"],
        },
        "LIVE_ROOT_REFUSED": {
            "safe_to_auto_retry": False,
            "requires_user_visible_summary": True,
            "next_allowed_tools": ["cleanmac_dry_run_plan", "cleanmac_policy_simulate"],
        },
        "USER_CONFIRMATION_REQUIRED": {
            "safe_to_auto_retry": False,
            "requires_user_visible_summary": True,
            "next_allowed_tools": ["cleanmac_dry_run_plan", "cleanmac_policy_simulate"],
        },
        "EXECUTION_REFUSED": {
            "safe_to_auto_retry": False,
            "requires_user_visible_summary": True,
            "next_allowed_tools": ["cleanmac_capabilities", "cleanmac_policy_simulate"],
        },
    }
    for entry in entries:
        entry.update(retry_policy[str(entry["code"])])
    return entries


AI_ERROR_TAXONOMY_BY_CODE = {entry["code"]: entry for entry in render_ai_error_taxonomy()}


def classify_cli_error(message: str, *, exit_code: int) -> dict[str, Any]:
    if exit_code == 2:
        code = "CLI_ARGUMENT_ERROR"
    elif "Unknown category" in message:
        code = "UNKNOWN_CATEGORY"
    elif "--require-plan-context requires --plan-file" in message:
        code = "PLAN_CONTEXT_REQUIRED"
    elif "Plan root mismatch" in message or "Plan home mismatch" in message:
        code = "PLAN_CONTEXT_MISMATCH"
    elif "plan is stale or drifted" in message:
        code = "PLAN_STALE_OR_DRIFTED"
    elif "AI-originated plan requires" in message:
        code = "AI_GUARD_REQUIRED"
    elif "confirmation token is required" in message:
        code = "CONFIRMATION_TOKEN_REQUIRED"
    elif "confirmation token mismatch" in message:
        code = "CONFIRMATION_TOKEN_MISMATCH"
    elif "operation log preflight failed" in message:
        code = "OPERATION_LOG_UNAVAILABLE"
    elif "exceeds --max-items budget" in message or "exceed --max-delete-mb budget" in message:
        code = "SAFETY_BUDGET_EXCEEDED"
    elif (
        "Review selection is invalid" in message
        or "--review-selection-file requires --plan-file" in message
        or "startup disable requires --review-selection-file" in message
        or "software execute requires --plan-file" in message
        or "software execute requires --review-selection-file" in message
        or "privacy execute requires --plan-file" in message
        or "privacy execute requires --review-selection-file" in message
    ):
        code = "SELECTION_VALIDATION_FAILED"
    elif "live root '/'" in message:
        code = "LIVE_ROOT_REFUSED"
    elif "without --yes" in message:
        code = "USER_CONFIRMATION_REQUIRED"
    else:
        code = "EXECUTION_REFUSED"
    taxonomy = AI_ERROR_TAXONOMY_BY_CODE[code]
    return {
        "code": code,
        "category": taxonomy["category"],
        "retryable_after_fix": taxonomy["retryable_after_fix"],
        "suggested_next_action": taxonomy["suggested_next_action"],
        "safe_to_auto_retry": taxonomy["safe_to_auto_retry"],
        "requires_user_visible_summary": taxonomy["requires_user_visible_summary"],
        "next_allowed_tools": taxonomy["next_allowed_tools"],
    }


def render_ai_error_report(message: str, *, argv: Sequence[str], exit_code: int) -> dict[str, Any]:
    classification = classify_cli_error(message, exit_code=exit_code)
    recovery_commands = {
        "SELECTION_VALIDATION_FAILED": [
            ["cleanmac", "--json", "review", "--input-file", "<plan.json>", "--selection-file", "<selection.json>"]
        ],
        "PLAN_CONTEXT_MISMATCH": [["cleanmac", "--json", "clean", "plan", "--categories", "trash"]],
        "OPERATION_LOG_UNAVAILABLE": [["cleanmac", "--json", "clean", "policy-simulate", "--plan-file", "<plan.json>"]],
        "CONFIRMATION_TOKEN_REQUIRED": [["cleanmac", "--json", "clean", "run", "--plan-file", "<plan.json>"]],
        "CONFIRMATION_TOKEN_MISMATCH": [["cleanmac", "--json", "clean", "run", "--plan-file", "<plan.json>"]],
        "USER_CONFIRMATION_REQUIRED": [["cleanmac", "--json", "clean", "run", "--plan-file", "<plan.json>"]],
    }.get(str(classification["code"]), [["cleanmac", "--json", "capabilities"]])
    return {
        "schema": "cleanmac.ai-error.v1",
        "ok": False,
        "destructive_operation_started": False,
        "safe_to_auto_retry": classification["safe_to_auto_retry"],
        "argv": list(argv),
        "error": {
            **classification,
            "message": message,
            "exit_code": exit_code,
            "recovery_commands": recovery_commands,
            "docs_hint": "Run dry-run/review commands before any execute command; cleanmac stays dry-run by default.",
        },
    }


__all__ = ["classify_cli_error", "render_ai_error_report", "render_ai_error_taxonomy"]
