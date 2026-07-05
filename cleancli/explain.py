"""Explain plan/report payloads without executing cleanup."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any, Callable


def payload_candidates(payload: Mapping[str, Any]) -> list[dict[str, Any]]:
    if isinstance(payload.get("pre_clean_report"), Mapping):
        candidates = payload["pre_clean_report"].get("candidates", [])  # type: ignore[index]
    else:
        candidates = payload.get("items", [])
    return [dict(row) for row in candidates if isinstance(row, Mapping)] if isinstance(candidates, list) else []


def payload_selected_categories(payload: Mapping[str, Any]) -> list[dict[str, Any]]:
    selected = payload.get("selected_categories", [])
    return [dict(row) for row in selected if isinstance(row, Mapping)] if isinstance(selected, list) else []


def render_explain_payload(
    payload: Mapping[str, Any],
    *,
    human_size: Callable[[int | None], str],
) -> dict[str, Any]:
    candidates = payload_candidates(payload)
    selected_categories = payload_selected_categories(payload)
    risk_by_category = {str(row.get("key")): str(row.get("risk", "unknown")) for row in selected_categories}
    bytes_by_category: dict[str, int] = {}
    count_by_category: dict[str, int] = {}
    for row in candidates:
        category = str(row.get("category", "unknown"))
        bytes_by_category[category] = bytes_by_category.get(category, 0) + int(row.get("bytes") or 0)
        count_by_category[category] = count_by_category.get(category, 0) + 1
    top_categories = [
        {
            "category": category,
            "bytes": total_bytes,
            "human": human_size(total_bytes),
            "item_count": count_by_category.get(category, 0),
            "risk": risk_by_category.get(category, "unknown"),
            "reason": "regenerable cleanup candidate"
            if risk_by_category.get(category) != "high"
            else "high-risk category needs explicit review",
        }
        for category, total_bytes in sorted(bytes_by_category.items(), key=lambda item: item[1], reverse=True)
    ]
    risk_summary: dict[str, int] = {}
    for row in top_categories:
        risk = str(row["risk"])
        risk_summary[risk] = risk_summary.get(risk, 0) + int(row["item_count"])
    estimated_bytes = int(
        payload.get("estimated_reclaimable_bytes") or payload.get("total_bytes") or sum(bytes_by_category.values())
    )
    source_schema = str(payload.get("schema", "unknown"))
    destructive = bool(payload.get("destructive", False))
    return {
        "schema": "cleanmac.explain.v1",
        "destructive": False,
        "dry_run": True,
        "source_schema": source_schema,
        "source_destructive": destructive,
        "source_dry_run": bool(payload.get("dry_run", True)),
        "summary": {
            "estimated_reclaimable_bytes": estimated_bytes,
            "estimated_reclaimable_human": human_size(estimated_bytes),
            "candidate_count": len(candidates),
            "category_count": len(top_categories),
            "requires_review_before_execute": True,
        },
        "top_categories": top_categories[:10],
        "risk_summary": risk_summary,
        "ai_guidance": {
            "safe_to_auto_call": True,
            "safe_to_execute": False,
            "preferred_next_actions": ["review", "validate-plan", "policy-simulate", "dry-run"],
            "execute_requires": [
                "review-selection-file",
                "trash delete mode",
                "plan context",
                "confirmation token",
                "operation log",
            ],
            "do_not": ["convert explanation into deletion", "bypass review", "use raw shell deletion"],
        },
        "user_summary": (
            f"{source_schema} describes {len(candidates)} candidate item(s) totaling "
            f"{human_size(estimated_bytes)}. Review and dry-run are required before any execution."
        ),
    }


__all__ = ["payload_candidates", "payload_selected_categories", "render_explain_payload"]
