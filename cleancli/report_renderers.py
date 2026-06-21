"""Human-readable report renderers for CLI-first cleanmac workflows."""

from __future__ import annotations

import html
import json
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
    uninstall_plan = payload.get("uninstall_plan")
    if isinstance(uninstall_plan, Mapping):
        value = uninstall_plan.get("candidates")
        if isinstance(value, list) and all(isinstance(row, Mapping) for row in value):
            return [row for row in value if isinstance(row, Mapping)]
    return []


def _path_link(path: Any) -> str:
    text = str(path or "")
    if not text.startswith("/"):
        return html.escape(text)
    href = "file://" + html.escape(text, quote=True)
    return f'<a href="{href}">{html.escape(text)}</a>'


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
    summary = "".join(
        f"<tr><th>{html.escape(key)}</th><td><code>{html.escape(str(value))}</code></td></tr>"
        for key, value in _summary_rows(payload)
    )
    item_rows = ""
    for row in _items(payload)[:200]:
        path = row.get("path") or row.get("source_pattern") or row.get("key") or ""
        item_rows += (
            "<tr>"
            f"<td>{_path_link(path)}</td>"
            f"<td>{html.escape(str(row.get('kind') or row.get('category') or ''))}</td>"
            f"<td>{html.escape(str(row.get('status') or row.get('risk') or ''))}</td>"
            f"<td>{html.escape(str(row.get('bytes') or row.get('size_bytes') or 0))}</td>"
            "</tr>"
        )
    items_table = (
        "<h2>Items</h2><table><tr><th>Path</th><th>Kind</th><th>Status</th><th>Bytes</th></tr>" + item_rows + "</table>"
        if item_rows
        else ""
    )
    raw = html.escape(json.dumps(payload, indent=2, ensure_ascii=False))
    return f"""<!doctype html>
<html lang="en">
<head><meta charset="utf-8"><title>{html.escape(_title(payload))}</title>
<style>body{{font-family:-apple-system,BlinkMacSystemFont,sans-serif;margin:2rem;}}table{{border-collapse:collapse;width:100%;}}th,td{{border:1px solid #ddd;padding:.4rem;text-align:left;}}code,pre{{background:#f6f8fa;}}</style></head>
<body><h1>cleanmac audit report</h1><h2>{html.escape(_title(payload))}</h2><h2>Summary</h2><table>{summary}</table>{items_table}<h2>Raw JSON</h2><pre>{raw}</pre></body></html>"""
