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
    pre_clean_report = report.get("pre_clean_report") if isinstance(report.get("pre_clean_report"), dict) else None
    if pre_clean_report and isinstance(pre_clean_report.get("candidates"), list):
        return list(pre_clean_report["candidates"])
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


def _count_by(items: list[dict[str, Any]], field: str) -> dict[str, int]:
    counts: dict[str, int] = {}
    for item in items:
        value = item.get(field)
        if value is None:
            continue
        key = str(value)
        counts[key] = counts.get(key, 0) + 1
    return dict(sorted(counts.items()))


def _sum_bytes(items: list[dict[str, Any]]) -> int:
    total = 0
    for item in items:
        try:
            total += int(item.get("bytes") or 0)
        except (TypeError, ValueError):
            continue
    return total


def _item_bytes(item: dict[str, Any]) -> int:
    try:
        return int(item.get("bytes") or 0)
    except (TypeError, ValueError):
        return 0


def _risk_rank(item: dict[str, Any]) -> int:
    return {"critical": 4, "high": 3, "medium": 2, "low": 1}.get(str(item.get("risk") or "unknown"), 0)


def _selection_summary(
    items: list[dict[str, Any]], selected_ids: list[str], unknown_item_ids: list[str]
) -> dict[str, Any]:
    selected_id_set = set(selected_ids)
    selected_items = [item for item in items if str(item["id"]) in selected_id_set]
    excluded_items = [item for item in items if str(item["id"]) not in selected_id_set]
    selected_scopes = _count_by(selected_items, "scope")
    selected_risks = _count_by(selected_items, "risk")
    return {
        "schema": "cleanmac.review-selection-summary.v1",
        "destructive": False,
        "dry_run": True,
        "item_count": len(items),
        "selected_count": len(selected_items),
        "excluded_count": len(excluded_items),
        "protected_count": sum(1 for item in items if item["protected"]),
        "unknown_item_count": len(unknown_item_ids),
        "selected_bytes": _sum_bytes(selected_items),
        "excluded_bytes": _sum_bytes(excluded_items),
        "selected_risk_counts": selected_risks,
        "excluded_risk_counts": _count_by(excluded_items, "risk"),
        "selected_scope_counts": selected_scopes,
        "selected_application_counts": _count_by(selected_items, "application"),
        "selected_kind_counts": _count_by(selected_items, "kind"),
        "requires_sensitive_review": bool(
            selected_risks.get("high") or selected_risks.get("critical") or selected_scopes.get("credentials")
        ),
    }


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
    selected_set.update(
        item_id for item_id in explicit_selected if item_id in known_ids and item_id not in protected_ids
    )
    selected_set.difference_update(item_id for item_id in explicit_excluded if item_id in known_ids)
    selected = [
        str(item["id"]) for item in items if str(item["id"]) in selected_set and str(item["id"]) not in protected_ids
    ]
    unknown_item_ids = [item_id for item_id in [*explicit_selected, *explicit_excluded] if item_id not in known_ids]
    selection_summary = _selection_summary(items, selected, _string_list(unknown_item_ids))
    return {
        "schema": "cleanmac.review.v1",
        "destructive": False,
        "dry_run": True,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source_schema": payload.get("schema"),
        "source_fingerprint": source_fingerprint(payload),
        "item_count": len(items),
        "default_selected_count": len(selected),
        "item_view": {
            "scope": "all",
            "item_count": len(items),
            "source_item_count": len(items),
        },
        "selection_summary": selection_summary,
        "items": items,
        "selection": {
            "schema": "cleanmac.review-selection.v1",
            "source_fingerprint": source_fingerprint(payload),
            "selected_item_ids": selected,
            "excluded_item_ids": [item["id"] for item in items if item["id"] not in selected],
            "summary": selection_summary,
            "explicit_selected_item_ids": explicit_selected,
            "explicit_excluded_item_ids": explicit_excluded,
            "unknown_item_ids": _string_list(unknown_item_ids),
            "protected_item_ids": [item_id for item_id in explicit_selected if item_id in protected_ids],
        },
    }


def _sort_items(items: list[dict[str, Any]], selected_ids: set[str], sort: str) -> list[dict[str, Any]]:
    if sort == "risk-desc":
        return sorted(items, key=lambda item: (-_risk_rank(item), str(item.get("id") or "")))
    if sort == "bytes-desc":
        return sorted(items, key=lambda item: (-_item_bytes(item), str(item.get("id") or "")))
    if sort == "selected-first":
        return sorted(items, key=lambda item: (str(item.get("id")) not in selected_ids, str(item.get("id") or "")))
    if sort == "path":
        return sorted(items, key=lambda item: str(item.get("path") or item.get("id") or ""))
    return items


def apply_item_scope(review: dict[str, Any], scope: str, sort: str = "source") -> dict[str, Any]:
    normalized_scope = scope if scope in {"all", "selected", "excluded"} else "all"
    normalized_sort = sort if sort in {"source", "risk-desc", "bytes-desc", "selected-first", "path"} else "source"
    items = [item for item in review.get("items", []) if isinstance(item, dict)]
    selection = review.get("selection") if isinstance(review.get("selection"), dict) else {}
    selected_ids = {str(item) for item in selection.get("selected_item_ids", []) if item is not None}
    if normalized_scope == "selected":
        scoped_items = [item for item in items if str(item.get("id")) in selected_ids]
    elif normalized_scope == "excluded":
        scoped_items = [item for item in items if str(item.get("id")) not in selected_ids]
    else:
        scoped_items = items
    scoped_items = _sort_items(scoped_items, selected_ids, normalized_sort)
    scoped = dict(review)
    scoped["items"] = scoped_items
    scoped["item_count"] = len(scoped_items)
    scoped["item_view"] = {
        "scope": normalized_scope,
        "sort": normalized_sort,
        "item_count": len(scoped_items),
        "source_item_count": len(items),
    }
    return scoped


def render_review_with_selection(payload: dict[str, Any], selection: dict[str, Any] | None = None) -> dict[str, Any]:
    if selection is None:
        return render_review(payload)
    selected_ids = [str(item) for item in selection.get("selected_item_ids", [])]
    excluded_ids = [str(item) for item in selection.get("excluded_item_ids", [])]
    review = render_review(payload, selected_item_ids=selected_ids, excluded_item_ids=excluded_ids)
    review["selection_validation"] = validate_review_selection(payload, selection)
    return review


def render_review_html(review: dict[str, Any]) -> str:
    summary = review.get("selection_summary") if isinstance(review.get("selection_summary"), dict) else {}
    selection = review.get("selection") if isinstance(review.get("selection"), dict) else {}
    selected_ids = {str(item) for item in selection.get("selected_item_ids", []) if item is not None}
    summary_rows = [
        ("Selected", summary.get("selected_count", 0)),
        ("Excluded", summary.get("excluded_count", 0)),
        ("Protected", summary.get("protected_count", 0)),
        ("Unknown overrides", summary.get("unknown_item_count", 0)),
        ("Selected bytes", summary.get("selected_bytes", 0)),
        ("Requires sensitive review", summary.get("requires_sensitive_review", False)),
    ]
    rows = []
    for item in review.get("items", []):
        if not isinstance(item, dict):
            continue
        item_id = str(item.get("id", ""))
        selected = item_id in selected_ids
        status = "selected" if selected else "excluded"
        rows.append(
            f"<tr class='{html.escape(status)}'>"
            f"<td><input type='checkbox' disabled {'checked' if selected else ''}></td>"
            f"<td>{html.escape(item_id)}</td>"
            f"<td>{html.escape(status)}</td>"
            f"<td>{html.escape(str(item.get('risk', '')))}</td>"
            f"<td>{html.escape(str(item.get('scope') or item.get('application') or item.get('kind') or ''))}</td>"
            f"<td>{html.escape(str(item.get('path', item.get('kind', ''))))}</td>"
            "</tr>"
        )
    validation = review.get("selection_validation") if isinstance(review.get("selection_validation"), dict) else None
    validation_html = ""
    if validation is not None:
        validation_html = (
            "<h2>Selection validation</h2>"
            f"<p><strong>Valid:</strong> {html.escape(str(validation.get('valid')))}</p>"
            f"<pre>{html.escape(json.dumps(validation, indent=2, ensure_ascii=False))}</pre>"
        )
    return "\n".join(
        [
            "<!doctype html>",
            "<html><head><meta charset='utf-8'><title>cleanmac review</title>",
            "<style>body{font-family:-apple-system,BlinkMacSystemFont,sans-serif;margin:2rem;}"
            "code,td,pre{font-family:ui-monospace,monospace;}table{border-collapse:collapse;width:100%;margin:1rem 0;}"
            "td,th{border:1px solid #ddd;padding:.4rem;text-align:left;}th{background:#f6f8fa;}"
            ".selected{background:#f0fff4}.excluded{color:#57606a}.warning{color:#9a6700}</style></head><body>",
            "<h1>cleanmac review</h1>",
            f"<p><strong>Source schema:</strong> {html.escape(str(review.get('source_schema')))}</p>",
            f"<p><strong>Items:</strong> {html.escape(str(review.get('item_count')))}</p>",
            "<h2>Selection summary</h2>",
            "<table><thead><tr><th>Metric</th><th>Value</th></tr></thead><tbody>",
            *(
                f"<tr><td>{html.escape(label)}</td><td>{html.escape(str(value))}</td></tr>"
                for label, value in summary_rows
            ),
            "</tbody></table>",
            f"<pre>{html.escape(json.dumps(summary, indent=2, ensure_ascii=False))}</pre>",
            validation_html,
            "<h2>Review items</h2>",
            "<table><thead><tr><th>Select</th><th>ID</th><th>Status</th><th>Risk</th><th>Scope/App/Kind</th><th>Path/Kind</th></tr></thead><tbody>",
            *rows,
            "</tbody></table>",
            f"<pre>{html.escape(json.dumps(review.get('selection'), indent=2, ensure_ascii=False))}</pre>",
            "</body></html>",
        ]
    )
