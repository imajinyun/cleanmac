"""One-shot automatic cleanup orchestration."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Callable, Sequence

DEFAULT_AUTO_CATEGORIES = ("darwinUserTemp", "nodePackageCaches", "pythonPackageCaches", "goBuildCaches")


def render_auto_clean(
    *,
    categories: Sequence[Any],
    root: Path,
    home: Path,
    execute: bool,
    older_than_days: float | None,
    max_delete_mb: float | None,
    max_items: int | None,
    inspect_items: Callable[..., dict[str, Any]],
    render_clean_plan: Callable[..., dict[str, Any]],
    validate_clean_plan_payload: Callable[[dict[str, Any], Path, Path], dict[str, Any]],
    clean: Callable[..., dict[str, Any]],
) -> dict[str, Any]:
    category_keys = [str(category.key) for category in categories]
    inspect_report = inspect_items(
        list(categories),
        root=root,
        home=home,
        limit=50,
        older_than_days=older_than_days,
        max_delete_mb=max_delete_mb,
        max_items=max_items,
    )
    plan_report = render_clean_plan(
        list(categories),
        root=root,
        home=home,
        risk_policy="default",
        max_delete_mb=max_delete_mb,
        older_than_days=older_than_days,
        max_items=max_items,
        ai_origin=True,
    )
    validation_report = validate_clean_plan_payload(plan_report, root, home)
    dry_run_report = clean(
        list(categories),
        root=root,
        home=home,
        execute=False,
        risk_policy="default",
        max_delete_mb=max_delete_mb,
        older_than_days=older_than_days,
        max_items=max_items,
        delete_mode="trash",
        operation_log=None,
        ai_originated_plan=True,
        command_argv=["auto", "--categories", ",".join(category_keys)],
    )
    execution_report = None
    if execute:
        execution_report = clean(
            list(categories),
            root=root,
            home=home,
            execute=True,
            risk_policy="default",
            max_delete_mb=max_delete_mb,
            older_than_days=older_than_days,
            max_items=max_items,
            delete_mode="trash",
            operation_log=None,
            ai_originated_plan=True,
            command_argv=["auto", "--categories", ",".join(category_keys), "--execute"],
        )
    final_report = execution_report or dry_run_report
    return {
        "schema": "cleanmac.auto.v1",
        "destructive": bool(execute),
        "dry_run": not execute,
        "phase": "execute" if execute else "dry-run",
        "selected_categories": category_keys,
        "delete_mode": "trash",
        "older_than_days": older_than_days,
        "max_delete_mb": max_delete_mb,
        "max_items": max_items,
        "inspect_summary": {
            "candidate_count": int(inspect_report.get("total_candidates", 0)),
            "shown_candidates": int(inspect_report.get("shown_candidates", 0)),
            "total_bytes": int(inspect_report.get("total_bytes", 0)),
            "total_human": inspect_report.get("total_human", "0 B"),
            "by_category": inspect_report.get("by_category", {}),
            "skipped_count": int(inspect_report.get("skipped_count", 0)),
        },
        "review": {
            "risk_level": final_report.get("ai_summary", {}).get("risk_level", "unknown"),
            "candidate_count": len(final_report.get("items", [])),
            "skipped_count": int(final_report.get("skipped_count", 0)),
            "requires_confirmation": bool(final_report.get("ai_confirmation_summary", {}).get("requires_confirmation", True)),
            "safe_to_auto_execute": False,
        },
        "plan": {
            "schema": plan_report.get("schema"),
            "valid": bool(validation_report.get("valid")),
            "candidate_fingerprint_count": len(plan_report.get("candidate_fingerprints", [])),
        },
        "dry_run_summary": {
            "item_count": len(dry_run_report.get("items", [])),
            "total_bytes": int(dry_run_report.get("total_bytes", 0)),
            "total_human": dry_run_report.get("total_human", "0 B"),
            "skipped_count": int(dry_run_report.get("skipped_count", 0)),
        },
        "execution": {
            "executed": bool(execute),
            "deleted_count": int(final_report.get("deleted_count", 0)),
            "failed_count": int(final_report.get("failed_count", 0)),
            "skipped_count": int(final_report.get("skipped_count", 0)),
            "operation_log": final_report.get("operation_log"),
        },
        "bytes_freed": int(final_report.get("total_bytes", 0)) if execute else 0,
        "bytes_freed_human": final_report.get("total_human", "0 B") if execute else "0 B",
        "reports": {
            "inspect": inspect_report,
            "plan": plan_report,
            "validate": validation_report,
            "dry_run": dry_run_report,
            "execute": execution_report,
        },
    }


__all__ = ["DEFAULT_AUTO_CATEGORIES", "render_auto_clean"]
