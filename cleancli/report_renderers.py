"""Human-readable report renderers for CLI-first cleanmac workflows."""

from __future__ import annotations

import html
import json
import shlex
from collections.abc import Mapping
from typing import Any


def _title(payload: Mapping[str, Any]) -> str:
    return str(payload.get("schema") or "cleanmac report")


def _summary_rows(payload: Mapping[str, Any]) -> list[tuple[str, Any]]:
    keys = (
        "schema",
        "destructive",
        "dry_run",
        "total_bytes",
        "estimated_bytes",
        "candidate_count",
        "result_count",
        "planned_count",
        "deleted_count",
        "skipped_count",
        "blocked_count",
        "failed_count",
        "safe_to_auto_execute",
    )
    return [(key, payload[key]) for key in keys if key in payload]


def _items(payload: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    for key in ("items", "candidates", "results", "entries", "categories"):
        value = payload.get(key)
        if isinstance(value, list) and all(isinstance(row, Mapping) for row in value):
            return [row for row in value if isinstance(row, Mapping)]
    pre_report = payload.get("pre_clean_report")
    if isinstance(pre_report, Mapping):
        value = pre_report.get("candidates")
        if isinstance(value, list) and all(isinstance(row, Mapping) for row in value):
            return [row for row in value if isinstance(row, Mapping)]
    uninstall_plan = payload.get("uninstall_plan")
    if isinstance(uninstall_plan, Mapping):
        value = uninstall_plan.get("candidates")
        if isinstance(value, list) and all(isinstance(row, Mapping) for row in value):
            return [row for row in value if isinstance(row, Mapping)]
    return []


def _row_bytes(row: Mapping[str, Any]) -> int:
    try:
        return int(row.get("bytes") or row.get("size_bytes") or 0)
    except (TypeError, ValueError):
        return 0


def _human_bytes(value: int) -> str:
    units = ("B", "KB", "MB", "GB", "TB")
    size = float(value)
    for unit in units:
        if size < 1024 or unit == units[-1]:
            return f"{size:.1f} {unit}" if unit != "B" else f"{int(size)} B"
        size /= 1024
    return f"{value} B"


def _row_path(row: Mapping[str, Any]) -> str:
    return str(row.get("path") or row.get("source_pattern") or row.get("key") or "")


def _path_link(path: Any) -> str:
    text = str(path or "")
    if not text.startswith("/"):
        return html.escape(text)
    href = "file://" + html.escape(text, quote=True)
    return f'<a href="{href}">{html.escape(text)}</a>'


def _finder_url(row: Mapping[str, Any], path: str) -> str | None:
    value = row.get("finder_url")
    if isinstance(value, str) and value:
        return value
    return f"file://{path}" if path.startswith("/") else None


def _finder_link(row: Mapping[str, Any], path: str) -> str:
    finder_url = _finder_url(row, path)
    if not finder_url:
        return ""
    return f'<a href="{html.escape(finder_url, quote=True)}">Finder URL</a>'


def _command_text(row: Mapping[str, Any], key: str, fallback: list[str]) -> str:
    value = row.get(f"{key}_text")
    if isinstance(value, str) and value:
        return value
    command = row.get(key)
    if isinstance(command, list) and all(isinstance(part, str) for part in command):
        return shlex.join(command)
    return shlex.join(fallback)


def _selected_ids(payload: Mapping[str, Any]) -> set[str]:
    selection = payload.get("selection") if isinstance(payload.get("selection"), Mapping) else None
    if selection:
        return {str(item) for item in selection.get("selected_item_ids", []) if item is not None}
    review_selection = payload.get("review_selection") if isinstance(payload.get("review_selection"), Mapping) else None
    if review_selection:
        return {str(item) for item in review_selection.get("selected_item_ids", []) if item is not None}
    return set()


def _selected_paths(payload: Mapping[str, Any]) -> set[str]:
    review_selection = payload.get("review_selection") if isinstance(payload.get("review_selection"), Mapping) else None
    if review_selection:
        return {str(item) for item in review_selection.get("selected_paths", []) if item is not None}
    return set()


def _is_selected(row: Mapping[str, Any], payload: Mapping[str, Any]) -> bool:
    selected_ids = _selected_ids(payload)
    if selected_ids:
        return str(row.get("id")) in selected_ids
    selected_paths = _selected_paths(payload)
    path = _row_path(row)
    if selected_paths:
        return path in selected_paths
    if "default_selected" in row:
        return bool(row.get("default_selected"))
    return str(row.get("status") or "") in {"planned", "deleted"}


def _category_cards(payload: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    pre_report = payload.get("pre_clean_report") if isinstance(payload.get("pre_clean_report"), Mapping) else None
    if pre_report and isinstance(pre_report.get("category_preview"), list):
        return [row for row in pre_report["category_preview"] if isinstance(row, Mapping)]
    value = payload.get("category_preview") or payload.get("categories")
    if isinstance(value, list):
        return [row for row in value if isinstance(row, Mapping)]
    by_category = payload.get("by_category")
    if isinstance(by_category, Mapping):
        return [dict(value, key=key) for key, value in by_category.items() if isinstance(value, Mapping)]
    rows = _items(payload)
    if rows:
        cards: dict[str, dict[str, Any]] = {}
        for row in rows:
            key = str(row.get("category") or row.get("kind") or "candidate")
            card = cards.setdefault(key, {"key": key, "bytes": 0, "candidate_count": 0, "risk": row.get("risk")})
            card["bytes"] = int(card["bytes"]) + _row_bytes(row)
            card["candidate_count"] = int(card["candidate_count"]) + 1
            if not card.get("risk") and row.get("risk"):
                card["risk"] = row.get("risk")
        return list(cards.values())
    return []


def _category_risks(payload: Mapping[str, Any]) -> dict[str, str]:
    risks: dict[str, str] = {}
    candidates: list[Any] = []
    pre_report = payload.get("pre_clean_report") if isinstance(payload.get("pre_clean_report"), Mapping) else None
    if pre_report and isinstance(pre_report.get("category_preview"), list):
        candidates.extend(pre_report["category_preview"])
    for key in ("selected_categories", "category_preview"):
        value = payload.get(key)
        if isinstance(value, list):
            candidates.extend(value)
    for row in candidates:
        if not isinstance(row, Mapping):
            continue
        key = str(row.get("key") or row.get("category") or "")
        risk = str(row.get("risk") or "")
        if key and risk:
            risks[key] = risk
    return risks


def _row_risk(row: Mapping[str, Any], risks: Mapping[str, str]) -> str:
    value = row.get("risk") or row.get("status")
    if value:
        return str(value)
    category = str(row.get("category") or row.get("kind") or "")
    return risks.get(category, "unknown")


def _skipped_summary(payload: Mapping[str, Any]) -> Mapping[str, Any]:
    value = payload.get("skipped_summary")
    return value if isinstance(value, Mapping) else {}


def _confirmation_summary(payload: Mapping[str, Any]) -> Mapping[str, Any]:
    value = payload.get("ai_confirmation_summary")
    return value if isinstance(value, Mapping) else {}


def _copyable_execution_command(audit_record: Mapping[str, Any], payload: Mapping[str, Any]) -> str | None:
    confirmation = _confirmation_summary(payload)
    token = str(confirmation.get("confirmation_token") or "{confirmation_token_from_matching_dry_run}")
    context_value = confirmation.get("confirmation_token_context")
    context: Mapping[str, Any] = context_value if isinstance(context_value, Mapping) else {}
    plan_file = str(payload.get("plan_file") or context.get("plan_file") or "{plan-file}")
    review_selection_value = payload.get("review_selection")
    review_selection: Mapping[str, Any] = review_selection_value if isinstance(review_selection_value, Mapping) else {}
    review_selection_file = str(review_selection.get("selection_file") or "{review-selection-file}")
    operation_log = str(confirmation.get("operation_log") or "~/.cleanmac/operations.jsonl")
    if not confirmation and payload.get("schema") not in {"cleanmac.plan.v1", "cleanmac.clean.v1"}:
        argv = audit_record.get("argv")
        return shlex.join(["python3", "cleanmac.py", *[str(part) for part in argv]]) if isinstance(argv, list) else None
    return shlex.join(
        [
            "python3",
            "cleanmac.py",
            "--json",
            "clean",
            "run",
            "--plan-file",
            plan_file,
            "--review-selection-file",
            review_selection_file,
            "--require-plan-context",
            "--delete-mode",
            "trash",
            "--execute",
            "--yes",
            "--operation-log",
            operation_log,
            "--require-confirmation-token",
            "--confirmation-token",
            token,
        ]
    )


def render_markdown_report(audit_record: Mapping[str, Any]) -> str:
    payload = audit_record.get("report") if isinstance(audit_record.get("report"), Mapping) else audit_record
    assert isinstance(payload, Mapping)
    lines = [f"# {_title(payload)}", ""]
    lines.append("## Summary")
    for key, value in _summary_rows(payload):
        lines.append(f"- **{key}**: `{value}`")
    rows = _items(payload)
    if rows:
        lines.extend(["", "## Items", "", "| Path | Kind | Status | Bytes |", "| --- | --- | --- | ---: |"])
        for row in rows[:200]:
            path = str(row.get("path") or row.get("source_pattern") or row.get("key") or "")
            link = f"[Open in Finder](file://{path})" if path.startswith("/") else path
            lines.append(
                "| "
                + " | ".join(
                    [
                        link,
                        str(row.get("kind") or row.get("category") or ""),
                        str(row.get("status") or row.get("risk") or ""),
                        str(row.get("bytes") or row.get("size_bytes") or 0),
                    ]
                )
                + " |"
            )
    lines.extend(["", "## Raw JSON", "", "```json", json.dumps(payload, indent=2, ensure_ascii=False), "```", ""])
    return "\n".join(lines)


def render_html_report(audit_record: Mapping[str, Any]) -> str:
    payload = audit_record.get("report") if isinstance(audit_record.get("report"), Mapping) else audit_record
    assert isinstance(payload, Mapping)
    rows = _items(payload)
    category_risks = _category_risks(payload)
    total_bytes = int(
        payload.get("total_bytes") or payload.get("estimated_reclaimable_bytes") or sum(_row_bytes(row) for row in rows)
    )
    selected_rows = [row for row in rows if _is_selected(row, payload)]
    skipped_value = payload.get("skipped")
    skipped: list[Any] = skipped_value if isinstance(skipped_value, list) else []
    confirmation = _confirmation_summary(payload)
    token = confirmation.get("confirmation_token")
    summary = "".join(
        f"<tr><th>{html.escape(key)}</th><td><code>{html.escape(str(value))}</code></td></tr>"
        for key, value in [
            ("schema", payload.get("schema")),
            ("dry_run", payload.get("dry_run")),
            ("destructive", payload.get("destructive")),
            ("candidate_count", payload.get("candidate_count") or payload.get("total_candidates") or len(rows)),
            ("selected_count", len(selected_rows)),
            ("skipped_count", payload.get("skipped_count") or len(skipped)),
            (
                "total_reclaimable",
                payload.get("total_human") or payload.get("estimated_reclaimable_human") or _human_bytes(total_bytes),
            ),
            ("risk_policy", payload.get("risk_policy")),
            ("confirmation_token", token or "not emitted for this report"),
        ]
        if value is not None
    )
    top_rows = "".join(
        "<tr>"
        f"<td>{html.escape(str(row.get('category') or row.get('kind') or row.get('key') or ''))}</td>"
        f"<td>{html.escape(row.get('human') and str(row.get('human')) or _human_bytes(_row_bytes(row)))}</td>"
        f"<td>{html.escape(_row_risk(row, category_risks))}</td>"
        f"<td>{_path_link(_row_path(row))}</td>"
        f"<td><code>{html.escape(_command_text(row, 'reveal_command', ['open', '-R', _row_path(row)]))}</code></td>"
        "</tr>"
        for row in sorted(rows, key=_row_bytes, reverse=True)[:10]
    )
    category_cards = "".join(
        "<article class='card'>"
        f"<h3>{html.escape(str(row.get('key') or row.get('category') or row.get('title') or 'category'))}</h3>"
        f"<p><strong>Size:</strong> {html.escape(str(row.get('human') or _human_bytes(_row_bytes(row))))}</p>"
        f"<p><strong>Risk:</strong> {html.escape(str(row.get('risk') or 'unknown'))}</p>"
        f"<p><strong>Candidates:</strong> {html.escape(str(row.get('candidate_count') or row.get('count') or 0))}</p>"
        "</article>"
        for row in _category_cards(payload)[:24]
    )
    skipped_reasons = (
        _skipped_summary(payload).get("by_reason") if isinstance(_skipped_summary(payload), Mapping) else None
    )
    skipped_rows = "".join(
        f"<tr><td>{html.escape(str(reason))}</td><td>{html.escape(str(count))}</td></tr>"
        for reason, count in (skipped_reasons.items() if isinstance(skipped_reasons, Mapping) else [])
    )
    item_rows = ""
    for row in rows[:200]:
        path = _row_path(row)
        selected = _is_selected(row, payload)
        reveal = _command_text(row, "reveal_command", ["open", "-R", path])
        item_rows += (
            "<tr>"
            f"<td><input type='checkbox' disabled {'checked' if selected else ''}></td>"
            f"<td>{_path_link(path)}</td>"
            f"<td><code>{html.escape(path)}</code></td>"
            f"<td>{html.escape(str(row.get('category') or row.get('kind') or ''))}</td>"
            f"<td>{html.escape(_row_risk(row, category_risks))}</td>"
            f"<td>{html.escape(row.get('human') and str(row.get('human')) or _human_bytes(_row_bytes(row)))}</td>"
            f"<td>{html.escape(str(row.get('reason') or row.get('match_reason') or row.get('why_not_default') or ''))}</td>"
            f"<td>{_finder_link(row, path)}<br><code>{html.escape(reveal)}</code></td>"
            "</tr>"
        )
    execution_command = _copyable_execution_command(audit_record, payload)
    execution_html = (
        "<h2>Copyable execution command</h2>"
        "<p>This command still uses the governed CLI plan / review-selection / delete_ops path.</p>"
        f"<pre><code>{html.escape(execution_command)}</code></pre>"
        if execution_command
        else ""
    )
    raw = html.escape(json.dumps(payload, indent=2, ensure_ascii=False))
    return f"""<!doctype html>
<html lang="en">
<head><meta charset="utf-8"><title>{html.escape(_title(payload))}</title>
<style>body{{font-family:-apple-system,BlinkMacSystemFont,sans-serif;margin:2rem;color:#24292f;}}table{{border-collapse:collapse;width:100%;margin:1rem 0;}}th,td{{border:1px solid #d0d7de;padding:.45rem;text-align:left;vertical-align:top;}}th{{background:#f6f8fa;}}code,pre{{background:#f6f8fa;border-radius:6px;padding:.15rem .25rem;}}pre{{padding:1rem;overflow:auto;}}.cards{{display:grid;grid-template-columns:repeat(auto-fit,minmax(14rem,1fr));gap:1rem;}}.card{{border:1px solid #d0d7de;border-radius:10px;padding:1rem;background:#fbfbfd;}}.hero{{padding:1rem;border:1px solid #d0d7de;border-radius:10px;background:#f6f8fa;}}</style></head>
<body><h1>cleanmac audit report</h1><section class="hero"><h2>Scan summary</h2><table>{summary}</table></section><h2>Top reclaimable</h2><table><tr><th>Category</th><th>Size</th><th>Risk</th><th>Path</th><th>Reveal command</th></tr>{top_rows}</table><h2>Category cards</h2><div class="cards">{category_cards}</div><h2>Skipped reasons</h2><table><tr><th>Reason</th><th>Count</th></tr>{skipped_rows}</table><h2>Selected-to-delete review</h2><table><tr><th>Select</th><th>Path link</th><th>Copy path</th><th>Category/Kind</th><th>Risk/Status</th><th>Size</th><th>Reason</th><th>Reveal</th></tr>{item_rows}</table>{execution_html}<h2>Raw JSON</h2><pre>{raw}</pre></body></html>"""
