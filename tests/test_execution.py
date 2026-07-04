from __future__ import annotations

import pytest

from cleancli.execution import ExecuteBudgetError, build_safety_gate, enforce_execute_budgets, row_bytes


def _human_size(size: int | None) -> str:
    return f"{size} B"


def test_build_safety_gate_reports_budget_and_context() -> None:
    gate = build_safety_gate(
        risk_policy="default",
        plan_file="/tmp/plan.json",
        max_delete_mb=1,
        candidate_bytes=2 * 1024 * 1024,
        candidate_count=3,
        skipped_count=1,
        fail_on_skipped=True,
        fail_fast=True,
        max_items=2,
        delete_mode="trash",
        operation_log="~/.cleanmac/operations.jsonl",
        confirmation_token_required=True,
        review_selection_applied=True,
        bundle_allowlist=("com.example.safe",),
        bundle_blocklist=("com.example.blocked",),
        human_size=_human_size,
    )

    assert gate["risk_policy"] == "default"
    assert gate["max_delete_bytes"] == 1024 * 1024
    assert gate["candidate_bytes"] == 2 * 1024 * 1024
    assert gate["candidate_human"] == f"{2 * 1024 * 1024} B"
    assert gate["within_delete_budget"] is False
    assert gate["within_max_items"] is False
    assert gate["fail_fast"] is True
    assert gate["fail_on_skipped"] is True
    assert gate["review_selection_applied"] is True
    assert gate["bundle_allowlist"] == ["com.example.safe"]
    assert gate["bundle_blocklist"] == ["com.example.blocked"]


def test_enforce_execute_budgets_is_noop_for_dry_run() -> None:
    enforce_execute_budgets(
        execute=False,
        fail_on_skipped=True,
        skipped_count=2,
        candidate_count=3,
        candidate_bytes=10,
        max_items=1,
        max_delete_mb=0,
        human_size=_human_size,
    )


def test_enforce_execute_budgets_blocks_skipped_candidates() -> None:
    with pytest.raises(ExecuteBudgetError, match="2 candidate\\(s\\) were skipped"):
        enforce_execute_budgets(
            execute=True,
            fail_on_skipped=True,
            skipped_count=2,
            candidate_count=1,
            candidate_bytes=10,
            max_items=None,
            max_delete_mb=None,
            human_size=_human_size,
        )


def test_enforce_execute_budgets_blocks_max_items() -> None:
    with pytest.raises(ExecuteBudgetError, match="candidate count 3 exceeds --max-items budget 2"):
        enforce_execute_budgets(
            execute=True,
            fail_on_skipped=False,
            skipped_count=0,
            candidate_count=3,
            candidate_bytes=10,
            max_items=2,
            max_delete_mb=None,
            human_size=_human_size,
        )


def test_enforce_execute_budgets_blocks_max_delete_mb() -> None:
    with pytest.raises(ExecuteBudgetError, match="candidate bytes exceed --max-delete-mb budget"):
        enforce_execute_budgets(
            execute=True,
            fail_on_skipped=False,
            skipped_count=0,
            candidate_count=1,
            candidate_bytes=2 * 1024 * 1024,
            max_items=None,
            max_delete_mb=1,
            human_size=_human_size,
        )


def test_row_bytes_handles_missing_or_non_numeric_values() -> None:
    assert row_bytes({"bytes": 10}) == 10
    assert row_bytes({"bytes": 1.5}) == 1
    assert row_bytes({"bytes": "10"}) == 0
    assert row_bytes({}) == 0
