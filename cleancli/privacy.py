"""Read-only privacy data inspection and cleanup planning."""

from __future__ import annotations

from pathlib import Path
from typing import Any


PRIVACY_SCOPES = ("all", "cache", "cookies", "history", "local-storage", "credentials")


def _display_path(path: Path | str) -> str:
    return str(path)


def _home_root(root: Path, home: Path) -> Path:
    return root / str(home).lstrip("/") if root != Path("/") else home


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
                (profile_root / "Service Worker/CacheStorage", "service-worker-cache", "cache", "low", "low", True, None),
                (profile_root / "Cookies", "cookies", "cookies", "high", "medium", False, "cookies preserve signed-in sessions"),
                (profile_root / "History", "history", "history", "medium", "medium", False, "history is personal browsing data"),
                (profile_root / "Login Data", "login-data", "credentials", "critical", "high", False, "saved credentials are never selected by default"),
                (profile_root / "Bookmarks", "bookmarks", "history", "medium", "high", False, "bookmarks are user-authored data"),
                (profile_root / "Local Storage", "local-storage", "local-storage", "high", "medium", False, "local storage may include app state and sessions"),
                (profile_root / "IndexedDB", "indexeddb", "local-storage", "high", "medium", False, "indexeddb may include app state and sessions"),
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
                (profile_root / "cookies.sqlite", "cookies", "cookies", "high", "medium", False, "cookies preserve signed-in sessions"),
                (profile_root / "places.sqlite", "history", "history", "medium", "medium", False, "history is personal browsing data"),
                (profile_root / "logins.json", "logins", "credentials", "critical", "high", False, "saved credentials are never selected by default"),
                (profile_root / "key4.db", "credential-key", "credentials", "critical", "high", False, "credential keys are never selected by default"),
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
            (root / "Local Storage", "local-storage", "local-storage", "high", "medium", False, "local storage may include app state and sessions"),
            (root / "IndexedDB", "indexeddb", "local-storage", "high", "medium", False, "indexeddb may include app state and sessions"),
            (root / "User/globalStorage", "global-storage", "local-storage", "high", "medium", False, "global storage may include app state"),
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
    all_candidates = _chromium_candidates(home_root) + _firefox_candidates(home_root) + _electron_candidates(home_root)
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


def render_privacy(action: str, *, scope: str, root: Path, home: Path) -> dict[str, Any]:
    if action == "plan":
        return plan_privacy(scope, root=root, home=home)
    return inspect_privacy(scope, root=root, home=home)
