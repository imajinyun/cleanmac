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


__all__ = [
    "ExecuteBudgetError",
    "build_safety_gate",
    "enforce_execute_budgets",
    "row_bytes",
]
