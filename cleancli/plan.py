"""Clean plan loading, schema negotiation, and freshness helpers."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable


def normalize_plan_category_keys(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    keys = []
    for item in value:
        if isinstance(item, str):
            keys.append(item)
        elif isinstance(item, dict) and isinstance(item.get("key"), str):
            keys.append(str(item["key"]))
    return keys


def normalize_risk_policy(value: object) -> str | None:
    if value in {"strict", "default", "permissive"}:
        return str(value)
    return None


def load_clean_plan(
    plan_file: str,
    *,
    display_path: Callable[[Path | str], str],
    negotiate_plan_schema: Callable[[dict[str, Any]], dict[str, Any]],
) -> dict[str, Any]:
    plan_path = Path(plan_file).expanduser().resolve(strict=False)
    payload = json.loads(plan_path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"Plan file must contain a JSON object: {plan_path}")
    plan = (
        payload.get("report")
        if payload.get("schema") == "cleanmac.audit.v1" and isinstance(payload.get("report"), dict)
        else payload
    )
    if not isinstance(plan, dict):
        raise ValueError(f"Plan file does not contain a usable report object: {plan_path}")
    schema_negotiation = negotiate_plan_schema(plan)

    category_keys = normalize_plan_category_keys(plan.get("selected_category_keys"))
    if not category_keys:
        category_keys = normalize_plan_category_keys(plan.get("categories"))
    if not category_keys:
        category_keys = normalize_plan_category_keys(plan.get("selected_categories"))

    safety_gate = plan.get("safety_gate")
    max_delete_mb = plan.get("max_delete_mb")
    if isinstance(safety_gate, dict) and max_delete_mb is None:
        max_delete_mb = safety_gate.get("max_delete_mb")

    return {
        "path": display_path(plan_path),
        "source_schema": str(plan.get("schema")) if isinstance(plan.get("schema"), str) else "",
        "schema_negotiation": schema_negotiation,
        "category_keys": category_keys,
        "risk_policy": normalize_risk_policy(plan.get("risk_policy")),
        "max_delete_mb": max_delete_mb if isinstance(max_delete_mb, (int, float)) else None,
        "exclude_patterns": normalize_plan_category_keys(plan.get("exclude_patterns")),
        "include_patterns": normalize_plan_category_keys(plan.get("include_patterns")),
        "older_than_days": plan.get("older_than_days")
        if isinstance(plan.get("older_than_days"), (int, float))
        else None,
        "min_size_mb": plan.get("min_size_mb") if isinstance(plan.get("min_size_mb"), int) else None,
        "name_regex": str(plan.get("name_regex")) if isinstance(plan.get("name_regex"), str) else None,
        "max_items": plan.get("max_items") if isinstance(plan.get("max_items"), int) else None,
        "root": str(plan.get("root")) if isinstance(plan.get("root"), str) else None,
        "home": str(plan.get("home")) if isinstance(plan.get("home"), str) else None,
        "ai_origin": plan.get("ai_origin") is True,
        "generated_at": str(plan.get("generated_at")) if isinstance(plan.get("generated_at"), str) else None,
        "expires_at": str(plan.get("expires_at")) if isinstance(plan.get("expires_at"), str) else None,
        "plan_max_age_seconds": plan.get("plan_max_age_seconds")
        if isinstance(plan.get("plan_max_age_seconds"), int)
        else None,
        "candidate_fingerprints": plan.get("candidate_fingerprints")
        if isinstance(plan.get("candidate_fingerprints"), list)
        else [],
    }


def ensure_supported_plan_schema(plan: dict[str, Any]) -> None:
    schema_negotiation = plan.get("schema_negotiation")
    if not isinstance(schema_negotiation, dict) or schema_negotiation.get("accepted") is not True:
        schema = "" if not isinstance(schema_negotiation, dict) else str(schema_negotiation.get("schema") or "")
        reason = (
            "missing-schema-negotiation"
            if not isinstance(schema_negotiation, dict)
            else str(schema_negotiation.get("reason") or "unknown")
        )
        raise ValueError(f"Unsupported plan schema {schema or '<missing>'}: {reason}")


def plan_schema_warnings(schema_negotiation: dict[str, Any]) -> list[dict[str, str]]:
    if schema_negotiation.get("accepted") is not True or schema_negotiation.get("legacy") is not True:
        return []
    schema = str(schema_negotiation.get("schema") or "")
    latest = str(schema_negotiation.get("latest_supported_schema") or "cleanmac.plan.v1")
    if schema:
        message = f"Plan schema {schema} is supported for compatibility; {latest} is preferred."
    else:
        message = f"Plan file has no schema field and is accepted as legacy; {latest} is preferred."
    return [{"code": "LEGACY_PLAN_SCHEMA", "schema": schema, "message": message}]


def render_plan_freshness_report(
    plan: dict[str, Any],
    *,
    compare_candidate_fingerprints: Callable[[list[dict[str, Any]]], list[dict[str, Any]]],
    parse_iso_datetime: Callable[[object], datetime | None],
    plan_max_age_seconds: int,
    now: datetime | None = None,
) -> dict[str, Any]:
    now = now or datetime.now(timezone.utc)
    generated_at = parse_iso_datetime(plan.get("generated_at"))
    expires_at = parse_iso_datetime(plan.get("expires_at"))
    max_age_seconds = plan.get("plan_max_age_seconds") or plan_max_age_seconds
    age_seconds = None if generated_at is None else max((now - generated_at).total_seconds(), 0)
    stale_reasons: list[str] = []
    if generated_at is None:
        stale_reasons.append("missing-generated-at")
    elif age_seconds is not None and age_seconds > float(max_age_seconds):
        stale_reasons.append("plan-age-exceeded")
    if expires_at is not None and now > expires_at:
        stale_reasons.append("plan-expired")
    fingerprints = [row for row in plan.get("candidate_fingerprints", []) if isinstance(row, dict)]
    drift = compare_candidate_fingerprints(fingerprints) if fingerprints else []
    return {
        "schema": "cleanmac.plan-freshness.v1",
        "fresh": not stale_reasons and not drift,
        "generated_at": plan.get("generated_at"),
        "expires_at": plan.get("expires_at"),
        "age_seconds": age_seconds,
        "max_age_seconds": max_age_seconds,
        "stale_reasons": stale_reasons,
        "drift_count": len(drift),
        "drift": drift,
        "fingerprint_count": len(fingerprints),
        "suggested_next_action": "continue"
        if not stale_reasons and not drift
        else "regenerate_plan_and_repeat_dry_run",
    }


__all__ = [
    "normalize_plan_category_keys",
    "normalize_risk_policy",
    "load_clean_plan",
    "ensure_supported_plan_schema",
    "plan_schema_warnings",
    "render_plan_freshness_report",
]
