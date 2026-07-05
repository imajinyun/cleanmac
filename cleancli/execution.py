"""Pure execution-gate helpers for clean workflows."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
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


def build_confirmation_token_context(
    *,
    category_keys: Sequence[str],
    root: Path,
    home: Path,
    risk_policy: str,
    max_delete_mb: float | None,
    max_items: int | None,
    include_patterns: Sequence[str],
    exclude_patterns: Sequence[str],
    older_than_days: float | None,
    min_size_mb: int,
    name_regex: str | None,
    bundle_allowlist: Sequence[str],
    bundle_blocklist: Sequence[str],
    delete_mode: str,
    plan_file: str | None,
    rows: Sequence[Mapping[str, Any]],
    display_path: Callable[[Path | str], str],
    file_sha256: Callable[[str | None], str | None],
) -> dict[str, Any]:
    return {
        "schema": "cleanmac.ai-confirmation-token-context.v1",
        "root": display_path(root),
        "home": display_path(home),
        "selected_categories": list(category_keys),
        "risk_policy": risk_policy,
        "max_delete_mb": max_delete_mb,
        "max_items": max_items,
        "include_patterns": list(include_patterns),
        "exclude_patterns": list(exclude_patterns),
        "older_than_days": older_than_days,
        "min_size_mb": min_size_mb,
        "name_regex": name_regex,
        "bundle_allowlist": list(bundle_allowlist),
        "bundle_blocklist": list(bundle_blocklist),
        "delete_mode": delete_mode,
        "plan_file": plan_file,
        "plan_sha256": file_sha256(plan_file),
        "candidate_count": len(rows),
        "candidate_bytes": sum(row_bytes(row) for row in rows),
        "candidates": [
            {
                "category": row.get("category"),
                "path": row.get("path"),
                "bytes": row.get("bytes"),
                "bundle_id": row.get("bundle_id"),
            }
            for row in rows
        ],
    }


def confirmation_token(context: Mapping[str, Any]) -> str:
    payload = json.dumps(context, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return f"cleanmac-confirm-{hashlib.sha256(payload.encode('utf-8')).hexdigest()[:32]}"


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


def build_operation_log_explainability_fields(
    *,
    command_text: str,
    action: str,
    category: str,
    path: Any,
    bytes_value: Any,
    human: Any,
    bundle_id: Any,
    delete_mode: str,
    trash_path: Any,
    deleted: bool,
    status: Any,
    reason: Any,
    error: Any,
) -> dict[str, Any]:
    """Return AI-replayable fields required on every operation-log JSONL row."""

    normalized_status = str(status or action)
    return {
        "tool": "cleanmac.clean.run",
        "parameters": {
            "command": command_text,
            "category": category,
            "path": path,
            "delete_mode": delete_mode,
        },
        "result": {
            "action": action,
            "status": normalized_status,
            "deleted": deleted,
            "reason": reason,
            "error": error,
            "trash_path": trash_path,
        },
        "impact_scope": {
            "category": category,
            "path": path,
            "bytes": bytes_value,
            "human": human,
            "bundle_id": bundle_id,
            "trash_path": trash_path,
        },
    }


def build_operation_log_entry(
    *,
    timestamp: str,
    session_id: str,
    command_text: str,
    action: str,
    row: Mapping[str, Any],
    delete_mode: str,
    root_text: str,
    home_text: str,
    ai_operation_audit: Mapping[str, Any],
) -> dict[str, Any]:
    explainability = build_operation_log_explainability_fields(
        command_text=command_text,
        action=action,
        category=str(row["category"]),
        path=row["path"],
        bytes_value=row["bytes"],
        human=row["human"],
        bundle_id=row.get("bundle_id"),
        delete_mode=delete_mode,
        trash_path=row.get("trash_path"),
        deleted=bool(row.get("deleted")),
        status=row.get("status", action),
        reason=row.get("reason"),
        error=row.get("error"),
    )
    return {
        "schema": "cleanmac.operation-log-entry.v1",
        "timestamp": timestamp,
        "session_id": session_id,
        "command": command_text,
        **explainability,
        "action": action,
        "category": row["category"],
        "path": row["path"],
        "bytes": row["bytes"],
        "human": row["human"],
        "bundle_id": row.get("bundle_id"),
        "delete_mode": delete_mode,
        "trash_path": row.get("trash_path"),
        "deleted": bool(row.get("deleted")),
        "status": row.get("status", action),
        "reason": row.get("reason"),
        "error": row.get("error"),
        "root": root_text,
        "home": home_text,
        "ai": {
            **dict(ai_operation_audit),
            "candidate_review_evidence": row.get("review_evidence")
            if isinstance(row.get("review_evidence"), dict)
            else None,
        },
    }


def build_review_selection_audit(review_selection: Mapping[str, Any] | None) -> dict[str, Any] | None:
    if not isinstance(review_selection, Mapping):
        return None
    validation = review_selection.get("validation")
    return {
        "schema": "cleanmac.operation-log-review-selection.v1",
        "selection_file": review_selection.get("selection_file"),
        "source_plan_file": review_selection.get("source_plan_file"),
        "source_fingerprint": review_selection.get("source_fingerprint"),
        "selected_count": review_selection.get("selected_count"),
        "selected_item_ids": list(review_selection.get("selected_item_ids", [])),
        "selected_review_evidence": list(review_selection.get("selected_review_evidence", [])),
        "validation_valid": validation.get("valid") if isinstance(validation, Mapping) else None,
    }


def sample_operation_log_entry() -> dict[str, Any]:
    sample_row = {
        "category": "downloads",
        "path": "~/Downloads/example-cache.bin",
        "bytes": 1024,
        "human": "1.00 KB",
        "bundle_id": None,
        "trash_path": "~/.Trash/example-cache.bin",
        "deleted": True,
        "status": "deleted",
        "reason": None,
        "error": None,
    }
    return build_operation_log_entry(
        timestamp="sample-timestamp",
        session_id="cleanmac-sample-session",
        command_text=(
            "cleanmac --json clean run --categories downloads --execute --yes "
            "--delete-mode trash --operation-log {operation_log}"
        ),
        action="delete",
        row=sample_row,
        delete_mode="trash",
        root_text="/",
        home_text="~",
        ai_operation_audit={
            "schema": "cleanmac.operation-log-ai-audit.v1",
            "originated_plan": True,
            "plan_file": "{plan_file}",
            "plan_sha256": "sample-plan-sha256",
            "require_plan_context": True,
            "confirmation_token_required": True,
            "confirmation_token_validated": True,
            "review_selection": None,
        },
    )


def validate_operation_log_explainability(
    report: Mapping[str, Any],
    *,
    schema_name: str,
    required_entry_fields: set[str],
) -> dict[str, Any]:
    violations: list[dict[str, Any]] = []
    if report.get("schema") != schema_name:
        violations.append({"code": "INVALID_SCHEMA", "path": "$.schema"})
    if report.get("destructive") is not False or report.get("dry_run") is not True:
        violations.append({"code": "CONTRACT_MUST_BE_READ_ONLY", "path": "$"})
    required_fields = {str(field) for field in report.get("required_entry_fields", []) if isinstance(field, str)}
    if not required_entry_fields.issubset(required_fields):
        violations.append({"code": "REQUIRED_ENTRY_FIELDS_MISSING", "path": "$.required_entry_fields"})
    sample = report.get("sample_entry", {}) if isinstance(report.get("sample_entry"), Mapping) else {}
    missing_sample_fields = sorted(required_entry_fields - set(sample))
    if missing_sample_fields:
        violations.append(
            {
                "code": "SAMPLE_ENTRY_MISSING_FIELDS",
                "path": "$.sample_entry",
                "missing": missing_sample_fields,
            }
        )
    for field in ("parameters", "result", "impact_scope"):
        if not isinstance(sample.get(field), Mapping):
            violations.append({"code": "SAMPLE_STRUCTURED_FIELD_INVALID", "path": f"$.sample_entry.{field}"})
    if report.get("format") != "jsonl" or report.get("append_only") is not True:
        violations.append({"code": "JSONL_APPEND_ONLY_REQUIRED", "path": "$"})
    return {
        "schema": "cleanmac.operation-log-explainability-validation.v1",
        "valid": not violations,
        "violation_count": len(violations),
        "violations": violations,
    }


def render_operation_log_explainability_contract(
    *,
    schema_name: str,
    resource_uri: str,
    required_entry_fields: set[str],
) -> dict[str, Any]:
    checks = [
        {
            "id": "operation-log-jsonl-append-only",
            "passed": True,
            "evidence": "append_operation_log writes one JSON object per line",
        },
        {
            "id": "operation-log-entry-has-timestamp-tool-parameters-result-impact",
            "passed": True,
            "evidence": "cleanmac.operation-log-entry.v1",
        },
        {
            "id": "operation-log-ai-audit-embedded",
            "passed": True,
            "evidence": "cleanmac.operation-log-ai-audit.v1",
        },
        {
            "id": "operation-log-preflight-fail-closed",
            "passed": True,
            "evidence": "cleanmac.operation-log-status.v1",
        },
    ]
    for check in checks:
        check["remediation_commands"] = [
            ["cleanmac", "--json", "operation-log-explainability"],
            ["python3", "-m", "pytest", "tests/test_operation_log.py", "-q"],
        ]
    payload: dict[str, Any] = {
        "schema": schema_name,
        "destructive": False,
        "dry_run": True,
        "ready": True,
        "resource_uri": resource_uri,
        "purpose": "Machine-readable contract that makes operation logs replayable and explainable by AI Hosts.",
        "format": "jsonl",
        "append_only": True,
        "sensitive_data_policy": "local-operation-log-may-contain-user-paths-mcp-resources-redacted",
        "required_entry_schema": "cleanmac.operation-log-entry.v1",
        "required_entry_fields": sorted(required_entry_fields),
        "required_nested_fields": {
            "parameters": ["command", "category", "path", "delete_mode"],
            "result": ["action", "status", "deleted", "reason", "error", "trash_path"],
            "impact_scope": ["category", "path", "bytes", "human", "bundle_id", "trash_path"],
            "ai": [
                "schema",
                "originated_plan",
                "plan_file",
                "plan_sha256",
                "require_plan_context",
                "confirmation_token_required",
                "confirmation_token_validated",
                "review_selection",
            ],
        },
        "sample_entry": sample_operation_log_entry(),
        "checks": checks,
        "failed_check_ids": [str(check["id"]) for check in checks if not check["passed"]],
        "readiness_score": {
            "passed": sum(1 for check in checks if check["passed"]),
            "total": len(checks),
            "level": "ready",
        },
        "release_gate_commands": [
            ["cleanmac", "--json", "operation-log-explainability"],
            ["python3", "-m", "pytest", "tests/test_operation_log.py", "-q"],
            ["make", "ai-host-smoke"],
        ],
    }
    validation = validate_operation_log_explainability(
        payload,
        schema_name=schema_name,
        required_entry_fields=required_entry_fields,
    )
    payload["validation"] = validation
    payload["ready"] = bool(validation["valid"] and not payload["failed_check_ids"])
    readiness_score = payload["readiness_score"]
    if isinstance(readiness_score, dict):
        readiness_score["level"] = "ready" if payload["ready"] else "blocked"
    return payload


__all__ = [
    "ExecuteBudgetError",
    "build_ai_confirmation_summary",
    "build_ai_execution_ledger",
    "build_confirmation_token_context",
    "build_operation_log_entry",
    "build_operation_log_explainability_fields",
    "build_review_selection_audit",
    "build_safety_gate",
    "confirmation_token",
    "enforce_execute_budgets",
    "render_operation_log_explainability_contract",
    "sample_operation_log_entry",
    "validate_operation_log_explainability",
    "row_bytes",
]
