"""Review report normalization and selection helpers."""

from __future__ import annotations

import hashlib
import html
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def load_json_file(path: str) -> dict[str, Any]:
    with Path(path).expanduser().open("r", encoding="utf-8") as handle:
        value = json.load(handle)
    if not isinstance(value, dict):
        raise ValueError("review input must be a JSON object")
    return value


def source_fingerprint(payload: dict[str, Any]) -> str:
    encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _item_source(payload: dict[str, Any]) -> list[Any]:
    report = payload.get("report") if isinstance(payload.get("report"), dict) else payload
    if isinstance(report.get("items"), list):
        return list(report["items"])
    if isinstance(report.get("candidates"), list):
        return list(report["candidates"])
    uninstall_plan = report.get("uninstall_plan") if isinstance(report.get("uninstall_plan"), dict) else None
    if uninstall_plan and isinstance(uninstall_plan.get("candidates"), list):
        return list(uninstall_plan["candidates"])
    disable_plan = report.get("disable_plan") if isinstance(report.get("disable_plan"), dict) else None
    if disable_plan and isinstance(disable_plan.get("candidates"), list):
        return list(disable_plan["candidates"])
    privacy_plan = report.get("privacy_plan") if isinstance(report.get("privacy_plan"), dict) else None
    if privacy_plan and isinstance(privacy_plan.get("candidates"), list):
        return list(privacy_plan["candidates"])
    return []


def normalize_review_items(payload: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for index, item in enumerate(_item_source(payload), start=1):
        if not isinstance(item, dict):
            continue
        path = str(item.get("path") or item.get("argv") or f"item-{index}")
        stable = hashlib.sha256(path.encode("utf-8")).hexdigest()[:16]
        rows.append(
            {
                "id": str(item.get("id") or f"item-{index}-{stable}"),
                "path": item.get("path"),
                "category": item.get("category"),
                "kind": item.get("kind"),
                "risk": item.get("risk") or item.get("privacy_risk", "unknown"),
                "privacy_risk": item.get("privacy_risk"),
                "data_loss_risk": item.get("data_loss_risk"),
                "recommendation": item.get("recommendation"),
                "application": item.get("application"),
                "profile": item.get("profile"),
                "scope": item.get("scope"),
                "bytes": item.get("bytes"),
                "human": item.get("human"),
                "default_selected": bool(item.get("default_selected", item.get("status") != "failed")),
                "protected": bool(item.get("protected")),
                "reason": item.get("reason") or item.get("match_reason") or item.get("preserve_reason"),
            }
        )
    return rows


def _string_list(values: list[str] | None) -> list[str]:
    if not values:
        return []
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        item = str(value)
        if item not in seen:
            seen.add(item)
            result.append(item)
    return result


def validate_review_selection(payload: dict[str, Any], selection: dict[str, Any]) -> dict[str, Any]:
    items = normalize_review_items(payload)
    known_ids = {str(item["id"]) for item in items}
    protected_ids = {str(item["id"]) for item in items if item["protected"]}
    selected = _string_list([str(item) for item in selection.get("selected_item_ids", [])])
    excluded = _string_list([str(item) for item in selection.get("excluded_item_ids", [])])
    unknown_selected = [item_id for item_id in selected if item_id not in known_ids]
    unknown_excluded = [item_id for item_id in excluded if item_id not in known_ids]
    protected_selected = [item_id for item_id in selected if item_id in protected_ids]
    overlap = [item_id for item_id in selected if item_id in set(excluded)]
    fingerprint_matches = selection.get("source_fingerprint") == source_fingerprint(payload)
    blocked_reasons = []
    if not fingerprint_matches:
        blocked_reasons.append("source-fingerprint-mismatch")
    if unknown_selected or unknown_excluded:
        blocked_reasons.append("unknown-item-id")
    if protected_selected:
        blocked_reasons.append("protected-item-selected")
    if overlap:
        blocked_reasons.append("item-both-selected-and-excluded")
    return {
        "schema": "cleanmac.review-selection-validation.v1",
        "destructive": False,
        "dry_run": True,
        "valid": not blocked_reasons,
        "source_fingerprint": source_fingerprint(payload),
        "selection_source_fingerprint": selection.get("source_fingerprint"),
        "fingerprint_matches": fingerprint_matches,
        "item_count": len(items),
        "selected_count": len(selected),
        "excluded_count": len(excluded),
        "unknown_selected_item_ids": unknown_selected,
        "unknown_excluded_item_ids": unknown_excluded,
        "protected_selected_item_ids": protected_selected,
        "overlap_item_ids": overlap,
        "blocked_reasons": blocked_reasons,
    }


def render_review(
    payload: dict[str, Any], *, selected_item_ids: list[str] | None = None, excluded_item_ids: list[str] | None = None
) -> dict[str, Any]:
    items = normalize_review_items(payload)
    known_ids = {str(item["id"]) for item in items}
    protected_ids = {str(item["id"]) for item in items if item["protected"]}
    explicit_selected = _string_list(selected_item_ids)
    explicit_excluded = _string_list(excluded_item_ids)
    selected_set = {str(item["id"]) for item in items if item["default_selected"] and not item["protected"]}
    selected_set.update(item_id for item_id in explicit_selected if item_id in known_ids and item_id not in protected_ids)
    selected_set.difference_update(item_id for item_id in explicit_excluded if item_id in known_ids)
    selected = [str(item["id"]) for item in items if str(item["id"]) in selected_set and str(item["id"]) not in protected_ids]
    unknown_item_ids = [item_id for item_id in [*explicit_selected, *explicit_excluded] if item_id not in known_ids]
    return {
        "schema": "cleanmac.review.v1",
        "destructive": False,
        "dry_run": True,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source_schema": payload.get("schema"),
        "source_fingerprint": source_fingerprint(payload),
        "item_count": len(items),
        "default_selected_count": len(selected),
        "items": items,
        "selection": {
            "schema": "cleanmac.review-selection.v1",
            "source_fingerprint": source_fingerprint(payload),
            "selected_item_ids": selected,
            "excluded_item_ids": [item["id"] for item in items if item["id"] not in selected],
            "explicit_selected_item_ids": explicit_selected,
            "explicit_excluded_item_ids": explicit_excluded,
            "unknown_item_ids": _string_list(unknown_item_ids),
            "protected_item_ids": [item_id for item_id in explicit_selected if item_id in protected_ids],
        },
    }


def render_review_with_selection(
    payload: dict[str, Any], selection: dict[str, Any] | None = None
) -> dict[str, Any]:
    if selection is None:
        return render_review(payload)
    selected_ids = [str(item) for item in selection.get("selected_item_ids", [])]
    excluded_ids = [str(item) for item in selection.get("excluded_item_ids", [])]
    review = render_review(payload, selected_item_ids=selected_ids, excluded_item_ids=excluded_ids)
    review["selection_validation"] = validate_review_selection(payload, selection)
    return review


def render_review_html(review: dict[str, Any]) -> str:
    rows = []
    for item in review.get("items", []):
        if not isinstance(item, dict):
            continue
        rows.append(
            "<tr>"
            f"<td>{html.escape(str(item.get('id', '')))}</td>"
            f"<td>{html.escape(str(item.get('risk', '')))}</td>"
            f"<td>{html.escape(str(item.get('default_selected', '')))}</td>"
            f"<td>{html.escape(str(item.get('path', item.get('kind', ''))))}</td>"
            "</tr>"
        )
    return "\n".join(
        [
            "<!doctype html>",
            "<html><head><meta charset='utf-8'><title>cleanmac review</title></head><body>",
            "<h1>cleanmac review</h1>",
            f"<p><strong>Source schema:</strong> {html.escape(str(review.get('source_schema')))}</p>",
            f"<p><strong>Items:</strong> {html.escape(str(review.get('item_count')))}</p>",
            "<table><thead><tr><th>ID</th><th>Risk</th><th>Selected</th><th>Path/Kind</th></tr></thead><tbody>",
            *rows,
            "</tbody></table>",
            f"<pre>{html.escape(json.dumps(review.get('selection'), indent=2, ensure_ascii=False))}</pre>",
            "</body></html>",
        ]
    )
