"""Pure execution-gate helpers for clean workflows."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Mapping, Sequence


@dataclass(frozen=True)
class ExecuteBudgetError(RuntimeError):
    message: str

    def __str__(self) -> str:
        return self.message


def row_bytes(row: Mapping[str, Any]) -> int:
    value = row.get("bytes", 0)
    return int(value) if isinstance(value, int | float) else 0


def build_safety_gate(
    *,
    risk_policy: str,
    plan_file: str | None,
    max_delete_mb: float | None,
    candidate_bytes: int,
    candidate_count: int,
    skipped_count: int,
    fail_on_skipped: bool,
    fail_fast: bool,
    max_items: int | None,
    delete_mode: str,
    operation_log: str | None,
    confirmation_token_required: bool,
    review_selection_applied: bool,
    bundle_allowlist: Sequence[str],
    bundle_blocklist: Sequence[str],
    human_size: Callable[[int | None], str],
) -> dict[str, Any]:
    max_delete_bytes = None if max_delete_mb is None else int(max_delete_mb * 1024 * 1024)
    return {
        "risk_policy": risk_policy,
        "plan_file": plan_file,
        "max_delete_mb": max_delete_mb,
        "max_delete_bytes": max_delete_bytes,
        "candidate_bytes": candidate_bytes,
        "candidate_human": human_size(candidate_bytes),
        "within_delete_budget": max_delete_bytes is None or candidate_bytes <= max_delete_bytes,
        "fail_on_skipped": fail_on_skipped,
        "fail_fast": fail_fast,
        "skipped_count": skipped_count,
        "max_items": max_items,
        "within_max_items": max_items is None or candidate_count <= max_items,
        "delete_mode": delete_mode,
        "operation_log": operation_log,
        "confirmation_token_required": confirmation_token_required,
        "review_selection_applied": review_selection_applied,
        "bundle_allowlist": list(bundle_allowlist),
        "bundle_blocklist": list(bundle_blocklist),
    }


def enforce_execute_budgets(
    *,
    execute: bool,
    fail_on_skipped: bool,
    skipped_count: int,
    candidate_count: int,
    candidate_bytes: int,
    max_items: int | None,
    max_delete_mb: float | None,
    human_size: Callable[[int | None], str],
) -> None:
    if not execute:
        return
    if fail_on_skipped and skipped_count:
        raise ExecuteBudgetError(
            f"Refusing to execute cleanup because {skipped_count} candidate(s) were skipped by filters."
        )
    if max_items is not None and candidate_count > max_items:
        raise ExecuteBudgetError(
            f"Refusing to execute cleanup because candidate count {candidate_count} exceeds --max-items budget {max_items}."
        )
    max_delete_bytes = None if max_delete_mb is None else int(max_delete_mb * 1024 * 1024)
    if max_delete_bytes is not None and candidate_bytes > max_delete_bytes:
        raise ExecuteBudgetError(
            "Refusing to execute cleanup because candidate bytes exceed --max-delete-mb budget. "
            f"Candidates: {human_size(candidate_bytes)}; budget: {human_size(max_delete_bytes)}"
        )


def build_ai_confirmation_summary(
    *,
    execute: bool,
    confirmation_token_context: dict[str, Any],
    confirmation_token_value: str,
    confirmation_token_validated: bool,
    confirmation_phrase: str,
    delete_mode: str,
    operation_log: str | None,
    operation_log_path: str | None,
    total_bytes: int,
    item_count: int,
    deleted_count: int,
    skipped_count: int,
    risk_level: str,
    risk_policy: str,
    category_keys: Sequence[str],
    yes_required_category_keys: Sequence[str],
    max_delete_mb: float | None,
    max_items: int | None,
    protected_bundle_policy_active: bool,
    warnings: Sequence[str],
    human_size: Callable[[int | None], str],
) -> dict[str, Any]:
    effective_operation_log = operation_log_path or operation_log
    return {
        "schema": "cleanmac.ai-confirmation-summary.v1",
        "requires_confirmation": not execute,
        "recommended_confirmation_phrase": confirmation_phrase,
        "confirmation_token": confirmation_token_value,
        "confirmation_token_embedded": confirmation_token_value,
        "confirmation_token_context": confirmation_token_context,
        "confirmation_token_validated": confirmation_token_validated,
        "recommended_next_action": "review_operation_log" if execute else "ask_user_confirmation",
        "safe_to_auto_execute": False,
        "delete_mode": delete_mode,
        "operation_log": effective_operation_log,
        "estimated_reclaimable_bytes": total_bytes,
        "estimated_reclaimable_human": human_size(total_bytes),
        "risk_level": risk_level,
        "risk_policy": risk_policy,
        "category_count": len(category_keys),
        "selected_categories": list(category_keys),
        "item_count": item_count,
        "deleted_count": deleted_count,
        "skipped_count": skipped_count,
        "yes_required_categories": list(yes_required_category_keys),
        "max_delete_mb": max_delete_mb,
        "max_items": max_items,
        "trash_recoverable": delete_mode == "trash",
        "protected_bundle_policy_active": protected_bundle_policy_active,
        "warnings": list(warnings),
    }


def build_ai_execution_ledger(
    *,
    execute: bool,
    confirmation_token_context: dict[str, Any],
    confirmation_token_value: str,
    confirmation_token_required: bool,
    confirmation_token_validated: bool,
    operation_log: str | None,
    operation_log_path: str | None,
    operation_log_status: Mapping[str, Any],
    operation_session_id: str,
    operation_log_entry_count: int,
    delete_mode: str,
    require_plan_context: bool,
    ai_originated_plan: bool,
) -> dict[str, Any]:
    effective_operation_log = operation_log_path or operation_log
    operation_log_ready = operation_log_status.get("status") in {"ready", "not-needed"}
    plan_file = confirmation_token_context.get("plan_file")
    plan_sha256 = confirmation_token_context.get("plan_sha256")
    safe_chain_complete = bool(
        execute
        and delete_mode == "trash"
        and effective_operation_log
        and operation_log_status.get("status") == "ready"
        and confirmation_token_required
        and confirmation_token_validated
        and (not plan_file or require_plan_context)
    )
    return {
        "schema": "cleanmac.ai-execution-ledger.v1",
        "phase": "clean-execute" if execute else "clean-dry-run",
        "safe_chain_complete": safe_chain_complete,
        "plan": {
            "file": plan_file,
            "sha256": plan_sha256,
            "ai_originated": ai_originated_plan,
            "context_required": require_plan_context,
        },
        "confirmation": {
            "token_required": confirmation_token_required,
            "token_validated": confirmation_token_validated,
            "token": confirmation_token_value,
        },
        "operation_log": {
            "path": effective_operation_log,
            "status": operation_log_status.get("status"),
            "ready": operation_log_ready,
            "error": operation_log_status.get("error"),
            "rotated": operation_log_status.get("rotated", False),
            "entry_count": operation_log_entry_count,
            "session_id": operation_session_id,
        },
        "execution": {
            "delete_mode": delete_mode,
            "destructive": execute,
            "trash_recoverable": delete_mode == "trash",
        },
    }


__all__ = [
    "ExecuteBudgetError",
    "build_ai_confirmation_summary",
    "build_ai_execution_ledger",
    "build_safety_gate",
    "enforce_execute_budgets",
    "row_bytes",
]
