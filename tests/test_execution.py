from __future__ import annotations

import pytest

from cleancli.execution import (
    ExecuteBudgetError,
    build_ai_confirmation_summary,
    build_ai_execution_ledger,
    build_operation_log_entry,
    build_operation_log_explainability_fields,
    build_safety_gate,
    enforce_execute_budgets,
    row_bytes,
)


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


def test_build_ai_confirmation_summary_reports_confirmation_context() -> None:
    summary = build_ai_confirmation_summary(
        execute=False,
        confirmation_token_context={"plan_file": "/tmp/plan.json"},
        confirmation_token_value="cleanmac-confirm-token",
        confirmation_token_validated=False,
        confirmation_phrase="Confirm cleanmac cleanup execution",
        delete_mode="trash",
        operation_log="~/.cleanmac/operations.jsonl",
        operation_log_path=None,
        total_bytes=2048,
        item_count=2,
        deleted_count=0,
        skipped_count=1,
        risk_level="high",
        risk_policy="default",
        category_keys=("trash", "downloads"),
        yes_required_category_keys=("downloads",),
        max_delete_mb=10,
        max_items=5,
        protected_bundle_policy_active=True,
        warnings=("High-risk categories selected: downloads",),
        human_size=_human_size,
    )

    assert summary["schema"] == "cleanmac.ai-confirmation-summary.v1"
    assert summary["requires_confirmation"] is True
    assert summary["recommended_confirmation_phrase"] == "Confirm cleanmac cleanup execution"
    assert summary["confirmation_token_embedded"] == "cleanmac-confirm-token"
    assert summary["operation_log"] == "~/.cleanmac/operations.jsonl"
    assert summary["estimated_reclaimable_human"] == "2048 B"
    assert summary["selected_categories"] == ["trash", "downloads"]
    assert summary["yes_required_categories"] == ["downloads"]
    assert summary["warnings"] == ["High-risk categories selected: downloads"]
    assert summary["safe_to_auto_execute"] is False


def test_build_ai_execution_ledger_marks_safe_chain_complete() -> None:
    ledger = build_ai_execution_ledger(
        execute=True,
        confirmation_token_context={"plan_file": "/tmp/plan.json", "plan_sha256": "abc"},
        confirmation_token_value="cleanmac-confirm-token",
        confirmation_token_required=True,
        confirmation_token_validated=True,
        operation_log="~/.cleanmac/operations.jsonl",
        operation_log_path="/tmp/operations.jsonl",
        operation_log_status={"status": "ready", "rotated": False, "error": None},
        operation_session_id="session-1",
        operation_log_entry_count=3,
        delete_mode="trash",
        require_plan_context=True,
        ai_originated_plan=True,
    )

    assert ledger["schema"] == "cleanmac.ai-execution-ledger.v1"
    assert ledger["phase"] == "clean-execute"
    assert ledger["safe_chain_complete"] is True
    assert ledger["plan"] == {
        "file": "/tmp/plan.json",
        "sha256": "abc",
        "ai_originated": True,
        "context_required": True,
    }
    assert ledger["confirmation"]["token_validated"] is True
    assert ledger["operation_log"]["path"] == "/tmp/operations.jsonl"
    assert ledger["operation_log"]["ready"] is True
    assert ledger["operation_log"]["entry_count"] == 3
    assert ledger["execution"]["trash_recoverable"] is True


def test_build_operation_log_explainability_fields() -> None:
    fields = build_operation_log_explainability_fields(
        command_text="cleanmac.py clean run",
        action="delete",
        category="downloads",
        path="/tmp/download.bin",
        bytes_value=10,
        human="10 B",
        bundle_id=None,
        delete_mode="trash",
        trash_path="/tmp/.Trash/download.bin",
        deleted=True,
        status="deleted",
        reason=None,
        error=None,
    )

    assert fields["tool"] == "cleanmac.clean.run"
    assert fields["parameters"]["category"] == "downloads"
    assert fields["parameters"]["delete_mode"] == "trash"
    assert fields["result"]["status"] == "deleted"
    assert fields["result"]["deleted"] is True
    assert fields["impact_scope"]["bytes"] == 10


def test_build_operation_log_entry_preserves_candidate_evidence() -> None:
    evidence = {"schema": "cleanmac.candidate-review-evidence.v1", "matched_rule": "clean.downloads.candidate"}
    entry = build_operation_log_entry(
        timestamp="2026-01-01T00:00:00+00:00",
        session_id="session-1",
        command_text="cleanmac.py clean run",
        action="delete",
        row={
            "category": "downloads",
            "path": "/tmp/download.bin",
            "bytes": 10,
            "human": "10 B",
            "bundle_id": None,
            "trash_path": "/tmp/.Trash/download.bin",
            "deleted": True,
            "status": "deleted",
            "review_evidence": evidence,
        },
        delete_mode="trash",
        root_text="/tmp/root",
        home_text="/Users/tester",
        ai_operation_audit={"schema": "cleanmac.operation-log-ai-audit.v1"},
    )

    assert entry["schema"] == "cleanmac.operation-log-entry.v1"
    assert entry["timestamp"] == "2026-01-01T00:00:00+00:00"
    assert entry["session_id"] == "session-1"
    assert entry["root"] == "/tmp/root"
    assert entry["home"] == "/Users/tester"
    assert entry["ai"]["candidate_review_evidence"] == evidence
    assert entry["result"]["action"] == "delete"


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
