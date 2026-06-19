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
                "risk": item.get("risk", "unknown"),
                "bytes": item.get("bytes"),
                "human": item.get("human"),
                "default_selected": bool(item.get("default_selected", item.get("status") != "failed")),
                "protected": bool(item.get("protected")),
                "reason": item.get("reason") or item.get("match_reason"),
            }
        )
    return rows


def render_review(payload: dict[str, Any]) -> dict[str, Any]:
    items = normalize_review_items(payload)
    selected = [item["id"] for item in items if item["default_selected"] and not item["protected"]]
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
        },
    }


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
