"""Read-only software uninstall inspection and planning."""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from cleancli import protection


def _display_path(path: Path | str) -> str:
    return str(path)


def _review_selection_audit(review_selection: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema": "cleanmac.operation-log-review-selection.v1",
        "selection_file": review_selection.get("selection_file"),
        "source_plan_file": review_selection.get("source_plan_file"),
        "source_fingerprint": review_selection.get("source_fingerprint"),
        "selected_count": review_selection.get("selected_count"),
        "selected_item_ids": list(review_selection.get("selected_item_ids", [])),
        "validation_valid": review_selection.get("validation", {}).get("valid")
        if isinstance(review_selection.get("validation"), dict)
        else None,
    }


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


def _bundle_id_for_app(app_path: Path) -> str | None:
    return protection.bundle_id_for_app(app_path)


def _app_identity(app_path: Path) -> dict[str, Any]:
    bundle_id = _bundle_id_for_app(app_path)
    vendor = protection.official_uninstaller_vendor(bundle_id=bundle_id, name=app_path.stem, app_path=app_path)
    return {
        "name": app_path.name,
        "display_name": app_path.stem,
        "path": _display_path(app_path),
        "bundle": app_path.suffix == ".app",
        "bundle_id": bundle_id,
        "protected_from_uninstall": protection.should_protect_from_uninstall(bundle_id),
        "official_uninstaller_vendor": vendor,
    }


def list_apps(*, root: Path, home: Path) -> list[dict[str, Any]]:
    app_dirs = [_system_path(root, "/Applications"), _home_root(root, home) / "Applications"]
    apps: list[dict[str, Any]] = []
    for app_dir in app_dirs:
        if app_dir.exists():
            for path in sorted(app_dir.glob("*.app")):
                apps.append({**_app_identity(path), "source": "unknown"})
    return apps


def _find_app(app: str, *, root: Path, home: Path) -> dict[str, Any] | None:
    needle = app.lower().removesuffix(".app")
    for entry in list_apps(root=root, home=home):
        names = {
            str(entry.get("name") or "").lower(),
            str(entry.get("display_name") or "").lower(),
            str(entry.get("bundle_id") or "").lower(),
        }
        if app.lower() in names or needle in names:
            return entry
    return None


def _candidate(
    path: Path, *, kind: str, confidence: str, match_reason: str, risk: str, default_selected: bool
) -> dict[str, Any]:
    protected = protection.should_protect_path(path)
    return {
        "id": f"{kind}:{_display_path(path)}",
        "path": _display_path(path),
        "kind": kind,
        "bytes": _path_size(path),
        "confidence": confidence,
        "match_reason": match_reason,
        "risk": risk,
        "default_selected": bool(default_selected and not protected),
        "protected": protected,
        "delete_mode": "trash",
    }


def _candidate_paths(app_identity: dict[str, Any], *, root: Path, home: Path) -> list[dict[str, Any]]:
    app_path = Path(str(app_identity["path"]))
    app_name = str(app_identity["display_name"])
    bundle_id = app_identity.get("bundle_id")
    home_root = _home_root(root, home)
    candidates: list[dict[str, Any]] = []
    candidates.append(
        _candidate(
            app_path,
            kind="app-bundle",
            confidence="high",
            match_reason="selected-app",
            risk="high",
            default_selected=True,
        )
    )
    if bundle_id:
        patterns = [
            (home_root / "Library/Preferences" / f"{bundle_id}.plist", "preferences", "bundle-id", "medium"),
            (home_root / "Library/Caches" / str(bundle_id), "cache", "bundle-id", "low"),
            (home_root / "Library/Logs" / str(bundle_id), "logs", "bundle-id", "low"),
            (home_root / "Library/Containers" / str(bundle_id), "container", "bundle-id", "high"),
            (home_root / "Library/LaunchAgents" / f"{bundle_id}.plist", "launch-agent", "bundle-id", "high"),
            (_system_path(root, "/Library/LaunchAgents") / f"{bundle_id}.plist", "launch-agent", "bundle-id", "high"),
        ]
        for path, kind, reason, risk in patterns:
            if path.exists() or path.is_symlink():
                candidates.append(
                    _candidate(
                        path,
                        kind=kind,
                        confidence="high",
                        match_reason=reason,
                        risk=risk,
                        default_selected=kind in {"cache", "logs", "preferences"},
                    )
                )
    name_patterns = [
        (home_root / "Library/Application Support" / app_name, "application-support"),
        (home_root / "Library/Caches" / app_name, "cache"),
        (home_root / "Library/Logs" / app_name, "logs"),
    ]
    for path, kind in name_patterns:
        if path.exists() or path.is_symlink():
            candidates.append(
                _candidate(
                    path, kind=kind, confidence="medium", match_reason="app-name", risk="medium", default_selected=False
                )
            )
    return candidates


def inspect_software_uninstall(app: str, *, root: Path, home: Path) -> dict[str, Any]:
    identity = _find_app(app, root=root, home=home)
    candidates = _candidate_paths(identity, root=root, home=home) if identity else []
    return {
        "schema": "cleanmac.software-inspect.v1",
        "destructive": False,
        "dry_run": True,
        "root": _display_path(root),
        "home": _display_path(home),
        "app": app,
        "found": identity is not None,
        "app_identity": identity,
        "candidate_count": len(candidates),
        "candidates": candidates,
        "estimated_bytes": sum(int(item.get("bytes") or 0) for item in candidates),
    }


def plan_software_uninstall(app: str | None, *, root: Path, home: Path) -> dict[str, Any]:
    if not app:
        return {
            "schema": "cleanmac.software-uninstall-plan.v1",
            "destructive": False,
            "dry_run": True,
            "root": _display_path(root),
            "home": _display_path(home),
            "app": None,
            "valid": False,
            "blocked_reasons": ["app-required"],
            "uninstall_plan": None,
        }
    inspection = inspect_software_uninstall(app, root=root, home=home)
    identity = inspection.get("app_identity") if isinstance(inspection.get("app_identity"), dict) else None
    vendor = (
        identity.get("official_uninstaller_vendor") if identity else protection.official_uninstaller_vendor(name=app)
    )
    protected = bool(identity and identity.get("protected_from_uninstall"))
    blocked_reasons: list[str] = []
    if not inspection["found"]:
        blocked_reasons.append("app-not-found")
    if vendor:
        blocked_reasons.append("official-uninstaller-required")
    if protected:
        blocked_reasons.append("protected-from-uninstall")
    candidates = list(inspection["candidates"])
    for item in candidates:
        if blocked_reasons:
            item["default_selected"] = False
    return {
        "schema": "cleanmac.software-uninstall-plan.v1",
        "destructive": False,
        "dry_run": True,
        "root": _display_path(root),
        "home": _display_path(home),
        "app": app,
        "valid": not blocked_reasons,
        "blocked_reasons": blocked_reasons,
        "uninstall_plan": {
            "app": app,
            "requires_explicit_future_execute": True,
            "official_uninstaller_vendor": vendor,
            "official_uninstaller_required": vendor is not None,
            "official_uninstaller_message": (
                f"Use the official {vendor} uninstaller; generic deletion is intentionally not planned."
                if vendor
                else None
            ),
            "protected_data_policy": "preserve app data unless selected by explicit governed uninstall execution",
            "requires_explicit_execute": True,
            "candidate_count": len(candidates),
            "candidate_bytes": sum(int(item.get("bytes") or 0) for item in candidates),
            "safe_to_auto_execute": False,
            "candidates": candidates,
        },
    }


def execute_software_uninstall(
    plan: dict[str, Any],
    *,
    review_selection: dict[str, Any],
    execute: bool,
    yes: bool,
    root: Path,
    home: Path,
    delete_mode: str,
    delete_path_func: Callable[[Path], Path | None],
) -> dict[str, Any]:
    if plan.get("schema") != "cleanmac.software-uninstall-plan.v1":
        raise SystemExit("Software uninstall execute requires a cleanmac.software-uninstall-plan.v1 plan file.")
    if str(plan.get("root")) != _display_path(root):
        raise SystemExit(f"Plan root mismatch: expected {plan.get('root')} actual {_display_path(root)}")
    if str(plan.get("home")) != _display_path(home):
        raise SystemExit(f"Plan home mismatch: expected {plan.get('home')} actual {_display_path(home)}")
    if delete_mode != "trash":
        raise SystemExit("Software uninstall execute only supports --delete-mode trash.")
    if execute and not yes:
        raise SystemExit(
            "Refusing to execute software uninstall without --yes. Review uninstall plan and selection first."
        )
    if not plan.get("valid"):
        reasons = ", ".join(str(reason) for reason in plan.get("blocked_reasons", [])) or "invalid-plan"
        raise SystemExit(f"Refusing to execute software uninstall because plan is blocked: {reasons}")

    selected_ids = {str(item) for item in review_selection.get("selected_item_ids", []) if item is not None}
    selected_paths = {str(path) for path in review_selection.get("selected_paths", []) if path is not None}
    uninstall_plan_value = plan.get("uninstall_plan")
    uninstall_plan: dict[str, Any] = uninstall_plan_value if isinstance(uninstall_plan_value, dict) else {}
    candidates = [item for item in uninstall_plan.get("candidates", []) if isinstance(item, dict)]
    results: list[dict[str, Any]] = []
    operation_log_entries: list[dict[str, Any]] = []
    review_audit = _review_selection_audit(review_selection)

    for item in candidates:
        path = Path(str(item.get("path") or ""))
        item_id = str(item.get("id") or "")
        path_text = str(path)
        bytes_value = int(item.get("bytes") or 0)
        status = "planned"
        reason = None
        error = None
        executed = False
        trash_path = None

        if item_id not in selected_ids:
            status = "skipped"
            reason = "not-in-review-selection"
        elif selected_paths and path_text not in selected_paths:
            status = "blocked"
            reason = "selection-id-path-mismatch"
        elif item.get("protected") or protection.should_protect_path(path):
            status = "blocked"
            reason = "protected-software-candidate"
        elif path.is_symlink():
            status = "blocked"
            reason = "symlink-software-candidate"
        elif not path.exists():
            status = "blocked"
            reason = "missing-software-candidate"
        elif execute:
            try:
                moved_path = delete_path_func(path)
                status = "deleted"
                executed = True
                trash_path = _display_path(moved_path) if moved_path else None
            except Exception as exc:
                status = "failed"
                reason = "delete-failed"
                error = str(exc)

        result = {
            "id": item.get("id"),
            "path": str(path),
            "kind": item.get("kind"),
            "risk": item.get("risk"),
            "bytes": bytes_value,
            "delete_mode": "trash",
            "trash_path": trash_path,
            "status": status,
            "reason": reason,
            "error": error,
            "executed": executed,
        }
        results.append(result)
        operation_log_entries.append(
            {
                "schema": "cleanmac.operation-log-entry.v1",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "action": "software-uninstall" if execute else "software-uninstall-dry-run",
                "category": "software",
                "path": str(path),
                "bytes": bytes_value,
                "human": str(item.get("human") or ""),
                "delete_mode": "trash",
                "trash_path": trash_path,
                "deleted": executed,
                "status": status,
                "reason": reason,
                "root": _display_path(root),
                "home": _display_path(home),
                "ai": {
                    "schema": "cleanmac.operation-log-ai-audit.v1",
                    "review_selection": review_audit,
                },
            }
        )

    return {
        "schema": "cleanmac.software-uninstall-result.v1",
        "destructive": bool(execute),
        "dry_run": not execute,
        "root": _display_path(root),
        "home": _display_path(home),
        "app": plan.get("app"),
        "delete_mode": "trash",
        "review_selection": review_selection,
        "result_count": len(results),
        "planned_count": sum(1 for item in results if item["status"] == "planned"),
        "deleted_count": sum(1 for item in results if item["status"] == "deleted"),
        "skipped_count": sum(1 for item in results if item["status"] == "skipped"),
        "blocked_count": sum(1 for item in results if item["status"] == "blocked"),
        "failed_count": sum(1 for item in results if item["status"] == "failed"),
        "safe_to_auto_execute": False,
        "results": results,
        "operation_log_entries": operation_log_entries,
    }


def render_software(action: str, *, app: str | None, root: Path, home: Path) -> dict[str, Any]:
    startup_locations = [
        "~/Library/LaunchAgents/",
        "/Library/LaunchAgents/",
        "/Library/LaunchDaemons/",
        "~/Library/StartupItems/",
        "/Library/StartupItems/",
    ]
    leftover_roots = [
        "~/Library/Preferences/<bundle-id>.plist",
        "~/Library/Application Support/<app>",
        "~/Library/Caches/<bundle-id>",
        "~/Library/LaunchAgents/<bundle-id>.plist",
        "/Library/Receipts/<package-id>.*",
    ]
    if action == "inspect":
        return inspect_software_uninstall(app or "", root=root, home=home)
    if action == "uninstall-plan":
        return plan_software_uninstall(app, root=root, home=home)
    return {
        "schema": "cleanmac.software.v1",
        "action": action,
        "destructive": False,
        "status": "read-only-planning",
        "app": app,
        "apps": list_apps(root=root, home=home) if action == "list" else [],
        "startup_locations": startup_locations if action == "startup-items" else [],
        "leftover_scan_roots": leftover_roots if action == "leftovers" else [],
        "uninstall_plan": None,
    }
