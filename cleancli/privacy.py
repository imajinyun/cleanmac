"""Read-only privacy data inspection and cleanup planning."""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from cleancli import delete_ops, protection

PRIVACY_SCOPES = ("all", "cache", "cookies", "history", "local-storage", "credentials")


def _display_path(path: Path | str) -> str:
    return str(path)


def _home_root(root: Path, home: Path) -> Path:
    return root / str(home).lstrip("/") if root != Path("/") else home


def _privacy_allowed_roots(root: Path, home: Path) -> list[Path]:
    home_root = _home_root(root, home)
    return [
        home_root / "Library/Caches",
        home_root / "Library/Application Support/Google/Chrome",
        home_root / "Library/Application Support/Microsoft Edge",
        home_root / "Library/Application Support/BraveSoftware/Brave-Browser",
        home_root / "Library/Application Support/Arc/User Data",
        home_root / "Library/Application Support/Firefox/Profiles",
        home_root / "Library/Caches/Firefox/Profiles",
        home_root / "Library/Safari",
        home_root / "Library/Cookies",
        home_root / "Library/Containers/com.apple.Safari/Data/Library/Caches",
        home_root / "Library/Containers/com.apple.Safari/Data/Library/Cookies",
        home_root / "Library/WebKit/com.apple.Safari/WebsiteData",
        home_root / "Library/Application Support/Slack",
        home_root / "Library/Application Support/discord",
        home_root / "Library/Application Support/Notion",
        home_root / "Library/Application Support/Windsurf",
    ]


def _path_within(candidate: Path, parent: Path) -> bool:
    try:
        resolved_candidate = candidate.resolve(strict=False)
        resolved_parent = parent.resolve(strict=False)
    except OSError:
        resolved_candidate = candidate
        resolved_parent = parent
    return resolved_candidate == resolved_parent or resolved_parent in resolved_candidate.parents


def _privacy_path_allowed(path: Path, *, root: Path, home: Path) -> bool:
    return any(_path_within(path, allowed_root) for allowed_root in _privacy_allowed_roots(root, home))


def _path_size(path: Path) -> int:
    try:
        if not path.exists() and not path.is_symlink():
            return 0
        if path.is_file() or path.is_symlink():
            return path.lstat().st_size
        return sum(child.lstat().st_size for child in path.rglob("*") if child.exists() or child.is_symlink())
    except OSError:
        return 0


def _count_by(items: list[dict[str, Any]], field: str) -> dict[str, int]:
    counts: dict[str, int] = {}
    for item in items:
        key = str(item.get(field) or "unknown")
        counts[key] = counts.get(key, 0) + 1
    return dict(sorted(counts.items()))


def _review_evidence(
    *,
    kind: str,
    scope: str,
    privacy_risk: str,
    data_loss_risk: str,
    default_selected: bool,
    preserve_reason: str | None,
) -> dict[str, Any]:
    contains_user_data = scope in {"credentials", "cookies", "history", "local-storage"}
    if default_selected:
        recommended_next_action = "review-default-selection-before-trash-execution"
    else:
        recommended_next_action = "manual-review-required"
    return {
        "schema": "cleanmac.candidate-review-evidence.v1",
        "matched_rule": f"privacy.{scope}.{kind}",
        "match_reason": preserve_reason or scope,
        "confidence": "high",
        "risk": privacy_risk,
        "risk_reason": preserve_reason or f"{scope} privacy cleanup candidate",
        "risk_explanation": preserve_reason or f"{scope} data may affect privacy, sessions, or browser state.",
        "default_selected": default_selected,
        "why_not_default": None if default_selected else preserve_reason or "privacy candidate requires explicit review",
        "protected": False,
        "delete_mode": "trash",
        "recovery": "Restore the candidate from Trash before reopening the application if needed.",
        "contains_user_data": contains_user_data,
        "shared_container": False,
        "recommended_next_action": recommended_next_action,
        "data_loss_risk": data_loss_risk,
    }


def _candidate(
    path: Path,
    *,
    application: str,
    profile: str,
    kind: str,
    scope: str,
    privacy_risk: str,
    data_loss_risk: str,
    default_selected: bool,
    preserve_reason: str | None = None,
) -> dict[str, Any] | None:
    if not path.exists() and not path.is_symlink():
        return None
    return {
        "id": f"privacy:{application}:{profile}:{kind}:{_display_path(path)}",
        "path": _display_path(path),
        "application": application,
        "profile": profile,
        "kind": kind,
        "scope": scope,
        "bytes": _path_size(path),
        "privacy_risk": privacy_risk,
        "data_loss_risk": data_loss_risk,
        "default_selected": default_selected,
        "preserve_reason": preserve_reason,
        "delete_mode": "trash",
        "protected": False,
        "review_evidence": _review_evidence(
            kind=kind,
            scope=scope,
            privacy_risk=privacy_risk,
            data_loss_risk=data_loss_risk,
            default_selected=default_selected,
            preserve_reason=preserve_reason,
        ),
    }


def _chromium_candidates(home_root: Path) -> list[dict[str, Any]]:
    apps = [
        ("Chrome", home_root / "Library/Application Support/Google/Chrome", home_root / "Library/Caches/Google/Chrome"),
        ("Microsoft Edge", home_root / "Library/Application Support/Microsoft Edge", None),
        ("Brave", home_root / "Library/Application Support/BraveSoftware/Brave-Browser", None),
        ("Arc", home_root / "Library/Application Support/Arc/User Data", None),
    ]
    candidates: list[dict[str, Any]] = []
    for application, support_root, cache_root in apps:
        profiles = sorted(path for path in support_root.glob("*") if path.is_dir()) if support_root.exists() else []
        if not profiles and cache_root and cache_root.exists():
            profiles = [support_root / path.name for path in sorted(cache_root.glob("*")) if path.is_dir()]
        for profile_root in profiles:
            profile = profile_root.name
            cache_path = (cache_root / profile / "Cache") if cache_root else (profile_root / "Cache")
            specs = [
                (cache_path, "cache", "cache", "low", "low", True, None),
                (profile_root / "Code Cache", "code-cache", "cache", "low", "low", True, None),
                (
                    profile_root / "Service Worker/CacheStorage",
                    "service-worker-cache",
                    "cache",
                    "low",
                    "low",
                    True,
                    None,
                ),
                (
                    profile_root / "Cookies",
                    "cookies",
                    "cookies",
                    "high",
                    "medium",
                    False,
                    "cookies preserve signed-in sessions",
                ),
                (
                    profile_root / "History",
                    "history",
                    "history",
                    "medium",
                    "medium",
                    False,
                    "history is personal browsing data",
                ),
                (
                    profile_root / "Login Data",
                    "login-data",
                    "credentials",
                    "critical",
                    "high",
                    False,
                    "saved credentials are never selected by default",
                ),
                (
                    profile_root / "Bookmarks",
                    "bookmarks",
                    "history",
                    "medium",
                    "high",
                    False,
                    "bookmarks are user-authored data",
                ),
                (
                    profile_root / "Local Storage",
                    "local-storage",
                    "local-storage",
                    "high",
                    "medium",
                    False,
                    "local storage may include app state and sessions",
                ),
                (
                    profile_root / "IndexedDB",
                    "indexeddb",
                    "local-storage",
                    "high",
                    "medium",
                    False,
                    "indexeddb may include app state and sessions",
                ),
            ]
            for path, kind, scope, privacy_risk, data_loss_risk, selected, reason in specs:
                item = _candidate(
                    path,
                    application=application,
                    profile=profile,
                    kind=kind,
                    scope=scope,
                    privacy_risk=privacy_risk,
                    data_loss_risk=data_loss_risk,
                    default_selected=selected,
                    preserve_reason=reason,
                )
                if item:
                    candidates.append(item)
    return candidates


def _firefox_candidates(home_root: Path) -> list[dict[str, Any]]:
    roots = [home_root / "Library/Application Support/Firefox/Profiles", home_root / "Library/Caches/Firefox/Profiles"]
    candidates: list[dict[str, Any]] = []
    seen: set[str] = set()
    for root in roots:
        if not root.exists():
            continue
        for profile_root in sorted(path for path in root.glob("*") if path.is_dir()):
            profile = profile_root.name
            specs = [
                (profile_root / "cache2/entries", "cache", "cache", "low", "low", True, None),
                (
                    profile_root / "cookies.sqlite",
                    "cookies",
                    "cookies",
                    "high",
                    "medium",
                    False,
                    "cookies preserve signed-in sessions",
                ),
                (
                    profile_root / "places.sqlite",
                    "history",
                    "history",
                    "medium",
                    "medium",
                    False,
                    "history is personal browsing data",
                ),
                (
                    profile_root / "logins.json",
                    "logins",
                    "credentials",
                    "critical",
                    "high",
                    False,
                    "saved credentials are never selected by default",
                ),
                (
                    profile_root / "key4.db",
                    "credential-key",
                    "credentials",
                    "critical",
                    "high",
                    False,
                    "credential keys are never selected by default",
                ),
            ]
            for path, kind, scope, privacy_risk, data_loss_risk, selected, reason in specs:
                item = _candidate(
                    path,
                    application="Firefox",
                    profile=profile,
                    kind=kind,
                    scope=scope,
                    privacy_risk=privacy_risk,
                    data_loss_risk=data_loss_risk,
                    default_selected=selected,
                    preserve_reason=reason,
                )
                if item and item["id"] not in seen:
                    seen.add(str(item["id"]))
                    candidates.append(item)
    return candidates


def _safari_candidates(home_root: Path) -> list[dict[str, Any]]:
    specs = [
        (home_root / "Library/Caches/com.apple.Safari", "cache", "cache", "low", "low", True, None),
        (
            home_root / "Library/Containers/com.apple.Safari/Data/Library/Caches/com.apple.Safari",
            "container-cache",
            "cache",
            "low",
            "low",
            True,
            None,
        ),
        (
            home_root / "Library/Safari/History.db",
            "history-db",
            "history",
            "medium",
            "medium",
            False,
            "history is personal browsing data",
        ),
        (
            home_root / "Library/Safari/Downloads.plist",
            "downloads-history",
            "history",
            "medium",
            "medium",
            False,
            "download history is personal browsing data",
        ),
        (
            home_root / "Library/Cookies/Cookies.binarycookies",
            "cookies",
            "cookies",
            "high",
            "medium",
            False,
            "cookies preserve signed-in sessions",
        ),
        (
            home_root / "Library/Containers/com.apple.Safari/Data/Library/Cookies/Cookies.binarycookies",
            "container-cookies",
            "cookies",
            "high",
            "medium",
            False,
            "cookies preserve signed-in sessions",
        ),
        (
            home_root / "Library/Safari/LocalStorage",
            "local-storage",
            "local-storage",
            "high",
            "medium",
            False,
            "local storage may include app state and sessions",
        ),
        (
            home_root / "Library/Safari/Databases",
            "web-sql-databases",
            "local-storage",
            "high",
            "medium",
            False,
            "website databases may include app state and sessions",
        ),
        (
            home_root / "Library/WebKit/com.apple.Safari/WebsiteData/LocalStorage",
            "webkit-local-storage",
            "local-storage",
            "high",
            "medium",
            False,
            "webkit local storage may include app state and sessions",
        ),
        (
            home_root / "Library/WebKit/com.apple.Safari/WebsiteData/IndexedDB",
            "webkit-indexeddb",
            "local-storage",
            "high",
            "medium",
            False,
            "indexeddb may include app state and sessions",
        ),
    ]
    candidates: list[dict[str, Any]] = []
    for path, kind, scope, privacy_risk, data_loss_risk, selected, reason in specs:
        item = _candidate(
            path,
            application="Safari",
            profile="default",
            kind=kind,
            scope=scope,
            privacy_risk=privacy_risk,
            data_loss_risk=data_loss_risk,
            default_selected=selected,
            preserve_reason=reason,
        )
        if item:
            candidates.append(item)
    return candidates


def _electron_candidates(home_root: Path) -> list[dict[str, Any]]:
    apps = [
        ("Slack", home_root / "Library/Application Support/Slack"),
        ("Discord", home_root / "Library/Application Support/discord"),
        ("Notion", home_root / "Library/Application Support/Notion"),
        ("Windsurf", home_root / "Library/Application Support/Windsurf"),
    ]
    candidates: list[dict[str, Any]] = []
    for application, root in apps:
        specs = [
            (root / "Cache", "cache", "cache", "low", "low", True, None),
            (root / "Service Worker/CacheStorage", "service-worker-cache", "cache", "low", "low", True, None),
            (root / "Cookies", "cookies", "cookies", "high", "medium", False, "cookies preserve signed-in sessions"),
            (
                root / "Local Storage",
                "local-storage",
                "local-storage",
                "high",
                "medium",
                False,
                "local storage may include app state and sessions",
            ),
            (
                root / "IndexedDB",
                "indexeddb",
                "local-storage",
                "high",
                "medium",
                False,
                "indexeddb may include app state and sessions",
            ),
            (
                root / "User/globalStorage",
                "global-storage",
                "local-storage",
                "high",
                "medium",
                False,
                "global storage may include app state",
            ),
        ]
        for path, kind, scope, privacy_risk, data_loss_risk, selected, reason in specs:
            item = _candidate(
                path,
                application=application,
                profile="default",
                kind=kind,
                scope=scope,
                privacy_risk=privacy_risk,
                data_loss_risk=data_loss_risk,
                default_selected=selected,
                preserve_reason=reason,
            )
            if item:
                candidates.append(item)
    return candidates


def inspect_privacy(scope: str, *, root: Path, home: Path) -> dict[str, Any]:
    normalized_scope = scope if scope in PRIVACY_SCOPES else "all"
    home_root = _home_root(root, home)
    all_candidates = (
        _chromium_candidates(home_root)
        + _firefox_candidates(home_root)
        + _safari_candidates(home_root)
        + _electron_candidates(home_root)
    )
    candidates = [item for item in all_candidates if normalized_scope == "all" or item["scope"] == normalized_scope]
    scope_counts = _count_by(candidates, "scope")
    application_counts = _count_by(candidates, "application")
    privacy_risk_counts = _count_by(candidates, "privacy_risk")
    default_selected_count = sum(1 for item in candidates if item["default_selected"])
    return {
        "schema": "cleanmac.privacy-inspect.v1",
        "destructive": False,
        "dry_run": True,
        "root": _display_path(root),
        "home": _display_path(home),
        "scope": normalized_scope,
        "candidate_count": len(candidates),
        "estimated_bytes": sum(int(item.get("bytes") or 0) for item in candidates),
        "candidates": candidates,
        "credential_candidate_count": sum(1 for item in candidates if item["scope"] == "credentials"),
        "default_selected_count": default_selected_count,
        "scope_counts": scope_counts,
        "application_counts": application_counts,
        "privacy_risk_counts": privacy_risk_counts,
        "recommended_next_action": "review_privacy_plan" if candidates else "no_action_needed",
    }


def plan_privacy(scope: str, *, root: Path, home: Path) -> dict[str, Any]:
    inspection = inspect_privacy(scope, root=root, home=home)
    candidates = list(inspection["candidates"])
    for item in candidates:
        if item["scope"] in {"credentials", "history", "cookies", "local-storage"}:
            item["default_selected"] = False
    scope_counts = _count_by(candidates, "scope")
    application_counts = _count_by(candidates, "application")
    privacy_risk_counts = _count_by(candidates, "privacy_risk")
    return {
        "schema": "cleanmac.privacy-plan.v1",
        "destructive": False,
        "dry_run": True,
        "root": _display_path(root),
        "home": _display_path(home),
        "scope": inspection["scope"],
        "valid": True,
        "blocked_reasons": [],
        "privacy_plan": {
            "requires_explicit_execute": True,
            "requires_explicit_future_execute": True,
            "safe_to_auto_execute": False,
            "candidate_count": len(candidates),
            "default_selected_count": sum(1 for item in candidates if item["default_selected"]),
            "candidate_bytes": sum(int(item.get("bytes") or 0) for item in candidates),
            "scope_counts": scope_counts,
            "application_counts": application_counts,
            "privacy_risk_counts": privacy_risk_counts,
            "candidates": candidates,
            "preserve_scopes": ["credentials", "cookies", "history", "local-storage"],
        },
    }


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


def execute_privacy_cleanup(
    plan: dict[str, Any],
    *,
    review_selection: dict[str, Any],
    execute: bool,
    yes: bool,
    root: Path,
    home: Path,
    delete_path_func: Callable[[Path], Path | None],
    delete_mode: str = "trash",
) -> dict[str, Any]:
    if plan.get("schema") != "cleanmac.privacy-plan.v1":
        raise SystemExit("Privacy cleanup requires a cleanmac.privacy-plan.v1 plan file.")
    try:
        delete_ops.require_trash_first_delete_mode(delete_mode, surface="privacy cleanup")
    except RuntimeError as exc:
        raise SystemExit(str(exc)) from exc
    if str(plan.get("root")) != _display_path(root):
        raise SystemExit(f"Plan root mismatch: expected {plan.get('root')} actual {_display_path(root)}")
    if str(plan.get("home")) != _display_path(home):
        raise SystemExit(f"Plan home mismatch: expected {plan.get('home')} actual {_display_path(home)}")
    if execute and not yes:
        raise SystemExit("Refusing to execute privacy cleanup without --yes. Review privacy plan and selection first.")

    selected_ids = {str(item) for item in review_selection.get("selected_item_ids", []) if item is not None}
    selected_paths = {str(path) for path in review_selection.get("selected_paths", []) if path is not None}
    privacy_plan_value = plan.get("privacy_plan")
    privacy_plan: dict[str, Any] = privacy_plan_value if isinstance(privacy_plan_value, dict) else {}
    candidates = [item for item in privacy_plan.get("candidates", []) if isinstance(item, dict)]
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
        elif path.is_symlink():
            status = "blocked"
            reason = "symlink-privacy-candidate"
        elif not _privacy_path_allowed(path, root=root, home=home):
            status = "blocked"
            reason = "outside-privacy-locations"
        elif item.get("scope") == "credentials":
            status = "blocked"
            reason = "sensitive-scope-blocked"
        elif protection.should_protect_path(path):
            status = "blocked"
            reason = "protected-privacy-candidate"
        elif not path.exists():
            status = "blocked"
            reason = "missing-privacy-candidate"
        elif execute:
            try:
                moved_path = delete_path_func(path)
                trash_path = _display_path(moved_path) if moved_path else None
                status = "deleted"
                executed = True
            except Exception as exc:
                status = "failed"
                reason = "delete-failed"
                error = str(exc)

        result = {
            "id": item.get("id"),
            "path": str(path),
            "application": item.get("application"),
            "profile": item.get("profile"),
            "kind": item.get("kind"),
            "scope": item.get("scope"),
            "privacy_risk": item.get("privacy_risk"),
            "data_loss_risk": item.get("data_loss_risk"),
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
                "action": "privacy-cleanup" if execute else "privacy-cleanup-dry-run",
                "category": "privacy",
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
        "schema": "cleanmac.privacy-execute-result.v1",
        "destructive": bool(execute),
        "dry_run": not execute,
        "root": _display_path(root),
        "home": _display_path(home),
        "scope": plan.get("scope"),
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


def render_privacy(action: str, *, scope: str, root: Path, home: Path) -> dict[str, Any]:
    if action == "plan":
        return plan_privacy(scope, root=root, home=home)
    return inspect_privacy(scope, root=root, home=home)
