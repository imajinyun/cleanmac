"""Startup item audit, disable planning, and guarded disable execution."""

from __future__ import annotations

import hashlib
import plistlib
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from cleancli import protection


def _display_path(path: Path | str) -> str:
    return str(path)


def _home_root(root: Path, home: Path) -> Path:
    return root / str(home).lstrip("/") if root != Path("/") else home


def _system_path(root: Path, path: str) -> Path:
    return root / path.lstrip("/") if root != Path("/") else Path(path)


def _path_size(path: Path) -> int:
    try:
        if not path.exists() and not path.is_symlink():
            return 0
        if path.is_file() or path.is_symlink():
            return path.lstat().st_size
        return sum(child.lstat().st_size for child in path.rglob("*") if child.exists() or child.is_symlink())
    except OSError:
        return 0


def _startup_path_allowed(path: Path, *, root: Path, home: Path) -> bool:
    try:
        resolved = path.resolve(strict=False)
    except OSError:
        resolved = path
    for _, location, _ in _startup_locations(root, home):
        try:
            resolved_location = location.resolve(strict=False)
        except OSError:
            resolved_location = location
        if resolved == resolved_location or resolved_location in resolved.parents:
            return True
    return False


def _load_plist(path: Path) -> dict[str, Any]:
    try:
        with path.open("rb") as handle:
            payload = plistlib.load(handle)
        return payload if isinstance(payload, dict) else {}
    except (OSError, plistlib.InvalidFileException, ValueError):
        return {}


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _backup_plist(path: Path) -> dict[str, str]:
    backup = path.with_suffix(path.suffix + ".cleanmac.bak")
    index = 1
    while backup.exists():
        backup = path.with_suffix(path.suffix + f".cleanmac.{index}.bak")
        index += 1
    backup.write_bytes(path.read_bytes())
    return {"backup_path": str(backup), "backup_sha256": _sha256_file(backup)}


def _write_disabled_plist(path: Path) -> dict[str, Any]:
    plist = _load_plist(path)
    if not plist:
        return {"status": "invalid-plist", "backup_path": None, "backup_sha256": None}
    if plist.get("Disabled") is True:
        return {"status": "already-disabled", "backup_path": None, "backup_sha256": None}
    backup = _backup_plist(path)
    plist["Disabled"] = True
    with path.open("wb") as handle:
        plistlib.dump(plist, handle)
    return {"status": "disabled", **backup}


def _startup_locations(root: Path, home: Path) -> list[tuple[str, Path, bool]]:
    home_root = _home_root(root, home)
    return [
        ("user-launch-agent", home_root / "Library/LaunchAgents", False),
        ("system-launch-agent", _system_path(root, "/Library/LaunchAgents"), True),
        ("system-launch-daemon", _system_path(root, "/Library/LaunchDaemons"), True),
        ("user-startup-item", home_root / "Library/StartupItems", False),
        ("system-startup-item", _system_path(root, "/Library/StartupItems"), True),
    ]


def _count_by(items: list[dict[str, Any]], field: str) -> dict[str, int]:
    counts: dict[str, int] = {}
    for item in items:
        key = str(item.get(field) or "unknown")
        counts[key] = counts.get(key, 0) + 1
    return dict(sorted(counts.items()))


def _review_evidence(
    *,
    kind: str,
    recommendation: str,
    risk: str,
    default_selected: bool,
    protected: bool,
    requires_privilege: bool,
) -> dict[str, Any]:
    if protected:
        recommended_next_action = "excluded-protected"
    elif default_selected:
        recommended_next_action = "review-default-selection-before-trash-execution"
    else:
        recommended_next_action = "manual-review-required"
    if protected:
        why_not_default = "protected startup item is preserved by policy"
    elif requires_privilege and not default_selected:
        why_not_default = "privileged startup item requires explicit review selection"
    elif recommendation != "review-disable" and not default_selected:
        why_not_default = f"startup recommendation is {recommendation}"
    else:
        why_not_default = None
    return {
        "schema": "cleanmac.candidate-review-evidence.v1",
        "matched_rule": f"startup.{kind}.{recommendation}",
        "match_reason": recommendation,
        "confidence": "high",
        "risk": risk,
        "risk_reason": "Startup item can affect login, background services, or privileged launch behavior.",
        "risk_explanation": "Disabling startup items changes whether related software starts automatically.",
        "default_selected": default_selected,
        "why_not_default": why_not_default,
        "protected": protected,
        "delete_mode": "trash",
        "recovery": "Restore the plist or StartupItems entry from Trash, then reload it manually if needed.",
        "contains_user_data": False,
        "shared_container": False,
        "recommended_next_action": recommended_next_action,
    }


def _item_from_plist(path: Path, *, kind: str, requires_privilege: bool) -> dict[str, Any]:
    plist = _load_plist(path)
    label = str(plist.get("Label") or path.stem)
    disabled = bool(plist.get("Disabled") is True)
    run_at_load = bool(plist.get("RunAtLoad") is True)
    keep_alive = bool(plist.get("KeepAlive") not in (None, False))
    program = plist.get("Program") or plist.get("ProgramArguments") or []
    if isinstance(program, list):
        program_display = [str(part) for part in program]
    else:
        program_display = [str(program)] if program else []
    protected = label.startswith("com.apple.") or protection.should_protect_path(path)
    if protected:
        risk = "critical"
        recommendation = "preserve"
    elif disabled:
        risk = "low"
        recommendation = "already-disabled"
    elif kind == "system-launch-daemon" or requires_privilege:
        risk = "high"
        recommendation = "review-disable"
    elif run_at_load or keep_alive:
        risk = "medium"
        recommendation = "review-disable"
    else:
        risk = "low"
        recommendation = "leave-enabled"
    default_selected = recommendation == "review-disable" and not requires_privilege and not protected
    return {
        "id": f"startup:{kind}:{label}:{_display_path(path)}",
        "path": _display_path(path),
        "kind": kind,
        "label": label,
        "program": program_display,
        "run_at_load": run_at_load,
        "keep_alive": keep_alive,
        "disabled": disabled,
        "requires_privilege": requires_privilege,
        "bytes": _path_size(path),
        "risk": risk,
        "protected": protected,
        "recommendation": recommendation,
        "default_selected": default_selected,
        "disable_method": "launchctl bootout/disable or move plist after explicit governed execution",
        "delete_mode": "trash",
        "review_evidence": _review_evidence(
            kind=kind,
            recommendation=recommendation,
            risk=risk,
            default_selected=default_selected,
            protected=protected,
            requires_privilege=requires_privilege,
        ),
    }


def _item_from_directory(path: Path, *, kind: str, requires_privilege: bool) -> dict[str, Any]:
    protected = protection.should_protect_path(path)
    recommendation = "preserve" if protected else "review-disable"
    risk = "high" if requires_privilege else "medium"
    default_selected = recommendation == "review-disable" and not requires_privilege
    return {
        "id": f"startup:{kind}:{path.name}:{_display_path(path)}",
        "path": _display_path(path),
        "kind": kind,
        "label": path.name,
        "program": [],
        "run_at_load": True,
        "keep_alive": False,
        "disabled": False,
        "requires_privilege": requires_privilege,
        "bytes": _path_size(path),
        "risk": risk,
        "protected": protected,
        "recommendation": recommendation,
        "default_selected": default_selected,
        "disable_method": "move StartupItems entry after explicit governed execution",
        "delete_mode": "trash",
        "review_evidence": _review_evidence(
            kind=kind,
            recommendation=recommendation,
            risk=risk,
            default_selected=default_selected,
            protected=protected,
            requires_privilege=requires_privilege,
        ),
    }


def audit_startup(*, root: Path, home: Path) -> dict[str, Any]:
    items: list[dict[str, Any]] = []
    scanned_locations: list[str] = []
    for kind, location, requires_privilege in _startup_locations(root, home):
        scanned_locations.append(_display_path(location))
        if not location.exists():
            continue
        if "launch" in kind:
            entries = sorted(location.glob("*.plist"))
            items.extend(_item_from_plist(path, kind=kind, requires_privilege=requires_privilege) for path in entries)
        else:
            entries = sorted(path for path in location.iterdir() if path.exists() or path.is_symlink())
            items.extend(
                _item_from_directory(path, kind=kind, requires_privilege=requires_privilege) for path in entries
            )
    risk_counts = _count_by(items, "risk")
    recommendation_counts = _count_by(items, "recommendation")
    kind_counts = _count_by(items, "kind")
    return {
        "schema": "cleanmac.startup-audit.v1",
        "destructive": False,
        "dry_run": True,
        "root": _display_path(root),
        "home": _display_path(home),
        "scanned_locations": scanned_locations,
        "item_count": len(items),
        "items": items,
        "requires_privilege_count": sum(1 for item in items if item["requires_privilege"]),
        "review_disable_count": sum(1 for item in items if item["recommendation"] == "review-disable"),
        "risk_counts": risk_counts,
        "recommendation_counts": recommendation_counts,
        "kind_counts": kind_counts,
        "recommended_next_action": "review_disable_plan"
        if recommendation_counts.get("review-disable", 0)
        else "no_action_needed",
    }


def plan_startup(*, root: Path, home: Path) -> dict[str, Any]:
    audit = audit_startup(root=root, home=home)
    candidates = [item for item in audit["items"] if item["recommendation"] == "review-disable"]
    risk_counts = _count_by(candidates, "risk")
    kind_counts = _count_by(candidates, "kind")
    return {
        "schema": "cleanmac.startup-plan.v1",
        "destructive": False,
        "dry_run": True,
        "root": _display_path(root),
        "home": _display_path(home),
        "valid": True,
        "blocked_reasons": [],
        "source_audit_item_count": audit["item_count"],
        "disable_plan": {
            "requires_explicit_execute": True,
            "requires_explicit_future_execute": True,
            "safe_to_auto_execute": False,
            "candidate_count": len(candidates),
            "default_selected_count": sum(1 for item in candidates if item["default_selected"]),
            "requires_privilege_count": sum(1 for item in candidates if item["requires_privilege"]),
            "risk_counts": risk_counts,
            "kind_counts": kind_counts,
            "candidates": candidates,
            "preserve_recommendations": [
                item for item in audit["items"] if item["recommendation"] in {"preserve", "already-disabled"}
            ],
        },
    }


def disable_startup_items(
    plan: dict[str, Any],
    *,
    review_selection: dict[str, Any],
    execute: bool,
    yes: bool,
    root: Path,
    home: Path,
) -> dict[str, Any]:
    if plan.get("schema") != "cleanmac.startup-plan.v1":
        raise SystemExit("Startup disable requires a cleanmac.startup-plan.v1 plan file.")
    if str(plan.get("root")) != _display_path(root):
        raise SystemExit(f"Plan root mismatch: expected {plan.get('root')} actual {_display_path(root)}")
    if str(plan.get("home")) != _display_path(home):
        raise SystemExit(f"Plan home mismatch: expected {plan.get('home')} actual {_display_path(home)}")
    if execute and not yes:
        raise SystemExit("Refusing to disable startup items without --yes. Review startup plan and selection first.")

    selected_ids = {str(item) for item in review_selection.get("selected_item_ids", []) if item is not None}
    selected_paths = {str(path) for path in review_selection.get("selected_paths", []) if path is not None}
    disable_plan_value = plan.get("disable_plan")
    disable_plan: dict[str, Any] = disable_plan_value if isinstance(disable_plan_value, dict) else {}
    candidates = [item for item in disable_plan.get("candidates", []) if isinstance(item, dict)]
    results: list[dict[str, Any]] = []
    operation_log_entries: list[dict[str, Any]] = []

    for item in candidates:
        path = Path(str(item.get("path") or ""))
        item_id = str(item.get("id") or "")
        path_text = str(path)
        reason = None
        status = "planned"
        backup_path = None
        backup_sha256 = None
        if item_id not in selected_ids:
            status = "skipped"
            reason = "not-in-review-selection"
        elif selected_paths and path_text not in selected_paths:
            status = "blocked"
            reason = "selection-id-path-mismatch"
        elif item.get("protected") or protection.should_protect_path(path):
            status = "blocked"
            reason = "protected-startup-item"
        elif item.get("requires_privilege"):
            status = "blocked"
            reason = "requires-privilege"
        elif path.is_symlink():
            status = "blocked"
            reason = "symlink-startup-item"
        elif not _startup_path_allowed(path, root=root, home=home):
            status = "blocked"
            reason = "outside-startup-locations"
        elif not path.exists():
            status = "blocked"
            reason = "missing-startup-item"
        elif path.suffix != ".plist":
            status = "blocked"
            reason = "unsupported-disable-method"
        elif execute:
            write_result = _write_disabled_plist(path)
            status = str(write_result["status"])
            backup_path = write_result.get("backup_path")
            backup_sha256 = write_result.get("backup_sha256")
            if status == "invalid-plist":
                reason = "invalid-plist"

        result = {
            "id": item.get("id"),
            "path": str(path),
            "kind": item.get("kind"),
            "label": item.get("label"),
            "risk": item.get("risk"),
            "status": status,
            "reason": reason,
            "executed": bool(execute and status in {"disabled", "already-disabled"}),
            "backup_path": backup_path,
            "backup_sha256": backup_sha256,
        }
        results.append(result)
        operation_log_entries.append(
            {
                "schema": "cleanmac.operation-log-entry.v1",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "action": "startup-disable" if execute else "startup-disable-dry-run",
                "category": "startup",
                "path": str(path),
                "bytes": int(item.get("bytes") or 0),
                "human": str(item.get("human") or ""),
                "delete_mode": "startup-disable",
                "deleted": False,
                "status": status,
                "reason": reason,
                "backup_path": backup_path,
                "backup_sha256": backup_sha256,
                "root": _display_path(root),
                "home": _display_path(home),
                "ai": {
                    "schema": "cleanmac.operation-log-ai-audit.v1",
                    "review_selection": {
                        "schema": "cleanmac.operation-log-review-selection.v1",
                        "selection_file": review_selection.get("selection_file"),
                        "source_plan_file": review_selection.get("source_plan_file"),
                        "source_fingerprint": review_selection.get("source_fingerprint"),
                        "selected_count": review_selection.get("selected_count"),
                        "selected_item_ids": list(review_selection.get("selected_item_ids", [])),
                        "validation_valid": review_selection.get("validation", {}).get("valid")
                        if isinstance(review_selection.get("validation"), dict)
                        else None,
                    },
                },
            }
        )

    return {
        "schema": "cleanmac.startup-disable-result.v1",
        "destructive": bool(execute),
        "dry_run": not execute,
        "root": _display_path(root),
        "home": _display_path(home),
        "review_selection": review_selection,
        "result_count": len(results),
        "planned_count": sum(1 for item in results if item["status"] == "planned"),
        "disabled_count": sum(1 for item in results if item["status"] == "disabled"),
        "already_disabled_count": sum(1 for item in results if item["status"] == "already-disabled"),
        "skipped_count": sum(1 for item in results if item["status"] == "skipped"),
        "blocked_count": sum(1 for item in results if item["status"] == "blocked" or item["status"] == "invalid-plist"),
        "safe_to_auto_execute": False,
        "results": results,
        "operation_log_entries": operation_log_entries,
    }


def render_startup(action: str, *, root: Path, home: Path) -> dict[str, Any]:
    if action == "plan":
        return plan_startup(root=root, home=home)
    return audit_startup(root=root, home=home)
