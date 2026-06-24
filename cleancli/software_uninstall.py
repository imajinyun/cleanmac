"""Read-only software uninstall inspection and planning."""

from __future__ import annotations

import shlex
from collections.abc import Callable
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import quote

from cleancli import protection


def _display_path(path: Path | str) -> str:
    return str(path)


def _shell_quote_command(parts: list[str]) -> str:
    return " ".join(shlex.quote(part) for part in parts)


def _path_interaction_metadata(path: Path) -> dict[str, Any]:
    path_text = _display_path(path)
    open_command = ["open", path_text]
    reveal_command = ["open", "-R", path_text]
    return {
        "finder_url": f"file://{quote(path_text, safe='/')}" if path_text.startswith("/") else None,
        "open_command": open_command,
        "open_command_text": _shell_quote_command(open_command),
        "reveal_command": reveal_command,
        "reveal_command_text": _shell_quote_command(reveal_command),
        "safe_to_open": not path.is_symlink(),
        "open_supported": True,
    }


def _review_selection_audit(review_selection: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema": "cleanmac.operation-log-review-selection.v1",
        "selection_file": review_selection.get("selection_file"),
        "source_plan_file": review_selection.get("source_plan_file"),
        "source_fingerprint": review_selection.get("source_fingerprint"),
        "selected_count": review_selection.get("selected_count"),
        "selected_item_ids": list(review_selection.get("selected_item_ids", [])),
        "selected_review_evidence": list(review_selection.get("selected_review_evidence", [])),
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


def _path_size_limited(path: Path, *, max_entries: int = 2000) -> int:
    try:
        if not path.exists() and not path.is_symlink():
            return 0
        if path.is_file() or path.is_symlink():
            return path.lstat().st_size
        total = 0
        for index, child in enumerate(path.rglob("*")):
            if index >= max_entries:
                break
            if child.exists() or child.is_symlink():
                total += child.lstat().st_size
        return total
    except OSError:
        return 0


def _bundle_id_for_app(app_path: Path) -> str | None:
    return protection.bundle_id_for_app(app_path)


def _app_owner(*, bundle_id: str | None, vendor: str | None) -> str:
    if vendor:
        return vendor
    if not bundle_id:
        return "unknown"
    parts = bundle_id.split(".")
    if len(parts) >= 2 and parts[0] == "com":
        return parts[1]
    if len(parts) >= 2 and parts[0] == "org":
        return parts[1]
    return parts[0]


def _app_identity(app_path: Path) -> dict[str, Any]:
    bundle_id = _bundle_id_for_app(app_path)
    vendor = protection.official_uninstaller_vendor(bundle_id=bundle_id, name=app_path.stem, app_path=app_path)
    return {
        "name": app_path.name,
        "display_name": app_path.stem,
        "path": _display_path(app_path),
        "bundle": app_path.suffix == ".app",
        "bundle_id": bundle_id,
        "app_owner": _app_owner(bundle_id=bundle_id, vendor=vendor),
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
    normalized_needle = needle.replace("-", "").replace("_", "").replace(" ", "")
    for entry in list_apps(root=root, home=home):
        bundle_id = str(entry.get("bundle_id") or "").lower()
        bundle_tail = bundle_id.rsplit(".", 1)[-1] if bundle_id else ""
        names = {
            str(entry.get("name") or "").lower(),
            str(entry.get("display_name") or "").lower(),
            bundle_id,
            bundle_tail,
        }
        normalized_names = {name.replace("-", "").replace("_", "").replace(" ", "") for name in names}
        if app.lower() in names or needle in names or normalized_needle in normalized_names:
            return entry
    return None


RISK_REASONS = {
    "low": "rebuildable or cosmetic app data such as caches, logs, or saved UI state",
    "medium": "app-scoped support data that may include preferences or offline state",
    "high": "application bundle, launch item, or app container that can change installed software behavior",
    "critical": "privileged helper or group container that may affect shared services, credentials, or system extensions",
}


LEFTOVER_TYPE_BY_KIND = {
    "app-bundle": "app_bundle",
    "preferences": "preferences",
    "cache": "cache",
    "logs": "logs",
    "container": "containers",
    "group-container": "containers",
    "saved-state": "saved_state",
    "http-storage": "containers",
    "webkit-data": "containers",
    "launch-agent": "launch_items",
    "launch-daemon": "launch_items",
    "privileged-helper": "privileged_helpers",
    "application-support": "support_data",
    "system-application-support": "support_data",
    "credentials": "credentials",
    "user-documents": "user_documents",
}


LEFTOVER_TYPE_RISK_EXPLANATIONS = {
    "app_bundle": "The application bundle is the installed app package itself; removing it changes installed software state.",
    "cache": "Caches are normally rebuildable and are safe default selections when matched by exact bundle id.",
    "logs": "Logs are diagnostic records and are normally safe to remove after review.",
    "preferences": "Preferences can reset app settings; they are reviewable and Trash-first recoverable.",
    "saved_state": "Saved state stores previous windows/session UI and is usually rebuildable by macOS.",
    "containers": "Container data may include sandboxed app state, databases, cookies, web storage, or files shared across apps.",
    "credentials": "Credentials, auth tokens, keys, and secrets are protected user data and are skipped by default.",
    "user_documents": "User documents may be authored project/work files and are never default-selected for uninstall cleanup.",
    "launch_items": "Launch agents/daemons can affect background services and should be selected only after explicit review.",
    "privileged_helpers": "Privileged helpers can affect system-level services; prefer vendor uninstallers or explicit human review.",
    "support_data": "Application support data may include app state or offline data; it is not selected by conservative defaults.",
}


RECOVERY_GUIDANCE = {
    "app-bundle": "Restore the app bundle from Trash or reinstall the app if execution was confirmed.",
    "preferences": "Restore the plist from Trash to recover app preferences.",
    "cache": "Usually rebuilt by the app; restore from Trash if the app needs the previous cache state.",
    "logs": "Restore from Trash only if logs are needed for troubleshooting.",
    "container": "Restore from Trash before reopening the app if container data was selected.",
    "saved-state": "Usually rebuilt by macOS; restore from Trash to recover previous window/session state.",
    "http-storage": "Restore from Trash if the app needs previous HTTP cache or web storage state.",
    "webkit-data": "Restore from Trash if embedded web views need previous local web data.",
    "launch-agent": "Restore from Trash and reload manually only after reviewing the launch item.",
    "launch-daemon": "Restore from Trash and reload manually only after reviewing the daemon and privileges.",
    "privileged-helper": "Do not remove casually; use vendor uninstall instructions or restore from Trash immediately.",
    "group-container": "Do not remove casually; may be shared across apps from the same vendor.",
    "application-support": "Restore from Trash if user state or app support files are still needed.",
    "system-application-support": "Restore from Trash or reinstall the app/vendor package if support files were selected.",
    "credentials": "Credentials are protected and skipped by default; restore from Trash immediately if explicitly selected by mistake.",
    "user-documents": "User documents are not default-selected; restore from Trash if explicitly selected and still needed.",
}


def _looks_like_credential_path(path: Path) -> bool:
    lowered_parts = {part.lower() for part in path.parts}
    lowered_name = path.name.lower()
    credential_terms = {
        "credential",
        "credentials",
        "secret",
        "secrets",
        "token",
        "tokens",
        "auth",
        "keychain",
        "keystore",
    }
    return bool(lowered_parts & credential_terms) or any(term in lowered_name for term in credential_terms)


def _is_user_document_path(path: Path, *, home_root: Path) -> bool:
    document_roots = (home_root / "Documents", home_root / "Desktop")
    return any(path == root or root in path.parents for root in document_roots)


def _leftover_type_for_path(path: Path, *, kind: str, home_root: Path) -> str:
    if _looks_like_credential_path(path):
        return "credentials"
    if _is_user_document_path(path, home_root=home_root):
        return "user_documents"
    return LEFTOVER_TYPE_BY_KIND.get(kind, kind.replace("-", "_"))


def _why_not_default(*, default_selected: bool, protected: bool, risk: str, confidence: str) -> str | None:
    if protected:
        return "protected by bundle/path safety policy"
    if default_selected:
        return None
    if risk == "critical":
        return "critical-risk candidate requires explicit review selection"
    if risk == "high":
        return "high-risk candidate requires explicit review selection unless it is the selected app bundle"
    if confidence != "high":
        return "medium-confidence or name-only match requires explicit review selection"
    return "not selected by conservative default policy"


def _candidate_review_evidence(candidate: dict[str, Any]) -> dict[str, Any]:
    protected = bool(candidate.get("protected"))
    default_selected = bool(candidate.get("default_selected"))
    if protected:
        recommended_next_action = "excluded-protected"
    elif default_selected:
        recommended_next_action = "review-default-selection-before-trash-execution"
    else:
        recommended_next_action = "manual-review-required"
    return {
        "schema": "cleanmac.candidate-review-evidence.v1",
        "matched_rule": candidate.get("matched_rule"),
        "match_reason": candidate.get("match_reason"),
        "confidence": candidate.get("confidence"),
        "risk": candidate.get("risk"),
        "risk_reason": candidate.get("risk_reason"),
        "risk_explanation": candidate.get("risk_explanation"),
        "default_selected": default_selected,
        "why_not_default": candidate.get("why_not_default"),
        "protected": protected,
        "delete_mode": candidate.get("delete_mode"),
        "recovery": candidate.get("recovery"),
        "contains_user_data": bool(candidate.get("contains_user_data")),
        "shared_container": bool(candidate.get("shared_container")),
        "recommended_next_action": recommended_next_action,
    }


def _attach_review_evidence(candidate: dict[str, Any]) -> dict[str, Any]:
    candidate["review_evidence"] = _candidate_review_evidence(candidate)
    return candidate


def _candidate(
    path: Path,
    *,
    kind: str,
    confidence: str,
    match_reason: str,
    risk: str,
    default_selected: bool,
    app_owner: str,
    home_root: Path,
    protected_override: bool = False,
    bytes_value: int | None = None,
) -> dict[str, Any]:
    leftover_type = _leftover_type_for_path(path, kind=kind, home_root=home_root)
    contains_user_data = leftover_type in {"credentials", "user_documents", "containers", "support_data"}
    shared_container = kind == "group-container"
    protected = bool(protected_override or leftover_type == "credentials" or protection.should_protect_path(path))
    effective_default = bool(default_selected and not protected)
    matched_rule = f"software-uninstall.{kind}.{match_reason}"
    risk_reason = RISK_REASONS.get(risk, "risk level assigned by software uninstall policy")
    risk_explanation = LEFTOVER_TYPE_RISK_EXPLANATIONS.get(leftover_type, risk_reason)
    recovery = RECOVERY_GUIDANCE.get(kind, "Execution routes to Trash; restore from Trash if needed.")
    why_not_default = _why_not_default(
        default_selected=effective_default, protected=protected, risk=risk, confidence=confidence
    )
    return _attach_review_evidence(
        {
            "id": f"{kind}:{_display_path(path)}",
            "path": _display_path(path),
            **_path_interaction_metadata(path),
            "kind": kind,
            "leftover_type": leftover_type,
            "bytes": _path_size(path) if bytes_value is None else bytes_value,
            "confidence": confidence,
            "match_reason": match_reason,
            "matched_rule": matched_rule,
            "reason": f"Matched {kind} by {match_reason} for the selected app.",
            "risk": risk,
            "risk_reason": risk_reason,
            "risk_explanation": risk_explanation,
            "recovery": recovery,
            "app_owner": app_owner,
            "contains_user_data": contains_user_data,
            "shared_container": shared_container,
            "default_selected": effective_default,
            "protected": protected,
            "why_not_default": why_not_default,
            "delete_mode": "trash",
        }
    )


def _candidate_paths(app_identity: dict[str, Any], *, root: Path, home: Path) -> list[dict[str, Any]]:
    app_path = Path(str(app_identity["path"]))
    app_name = str(app_identity["display_name"])
    bundle_id = app_identity.get("bundle_id")
    app_owner = str(app_identity.get("app_owner") or "unknown")
    app_protected = bool(app_identity.get("protected_from_uninstall"))
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
            app_owner=app_owner,
            home_root=home_root,
            protected_override=app_protected,
        )
    )
    if bundle_id:
        patterns = [
            (home_root / "Library/Preferences" / f"{bundle_id}.plist", "preferences", "bundle-id", "medium"),
            (home_root / "Library/Caches" / str(bundle_id), "cache", "bundle-id", "low"),
            (home_root / "Library/Logs" / str(bundle_id), "logs", "bundle-id", "low"),
            (home_root / "Library/Containers" / str(bundle_id), "container", "bundle-id", "high"),
            (
                home_root / "Library/Saved Application State" / f"{bundle_id}.savedState",
                "saved-state",
                "bundle-id",
                "low",
            ),
            (home_root / "Library/HTTPStorages" / str(bundle_id), "http-storage", "bundle-id", "medium"),
            (home_root / "Library/WebKit" / str(bundle_id), "webkit-data", "bundle-id", "medium"),
            (home_root / "Library/LaunchAgents" / f"{bundle_id}.plist", "launch-agent", "bundle-id", "high"),
            (_system_path(root, "/Library/LaunchAgents") / f"{bundle_id}.plist", "launch-agent", "bundle-id", "high"),
            (_system_path(root, "/Library/LaunchDaemons") / f"{bundle_id}.plist", "launch-daemon", "bundle-id", "high"),
            (
                _system_path(root, "/Library/PrivilegedHelperTools") / str(bundle_id),
                "privileged-helper",
                "bundle-id",
                "critical",
            ),
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
                        default_selected=kind in {"cache", "logs", "preferences", "saved-state"},
                        app_owner=app_owner,
                        home_root=home_root,
                    )
                )
        group_root = home_root / "Library/Group Containers"
        if group_root.exists():
            for path in sorted(group_root.iterdir()):
                group_bundle_id = protection.bundle_id_for_path(path)
                if group_bundle_id != bundle_id:
                    continue
                candidates.append(
                    _candidate(
                        path,
                        kind="group-container",
                        confidence="medium",
                        match_reason="bundle-id",
                        risk="critical",
                        default_selected=False,
                        app_owner=app_owner,
                        home_root=home_root,
                    )
                )
        support_root = home_root / "Library/Application Support" / app_name
        if support_root.exists():
            for path in sorted(support_root.rglob("*")):
                if not (path.exists() or path.is_symlink()) or path.is_dir():
                    continue
                if _leftover_type_for_path(path, kind="application-support", home_root=home_root) != "credentials":
                    continue
                candidates.append(
                    _candidate(
                        path,
                        kind="credentials",
                        confidence="high",
                        match_reason="credential-path",
                        risk="critical",
                        default_selected=False,
                        app_owner=app_owner,
                        home_root=home_root,
                    )
                )
        documents_root = home_root / "Documents" / app_name
        if documents_root.exists():
            candidates.append(
                _candidate(
                    documents_root,
                    kind="user-documents",
                    confidence="medium",
                    match_reason="app-name-documents",
                    risk="critical",
                    default_selected=False,
                    app_owner=app_owner,
                    home_root=home_root,
                )
            )
    name_patterns = [
        (home_root / "Library/Application Support" / app_name, "application-support"),
        (home_root / "Library/Caches" / app_name, "cache"),
        (home_root / "Library/Logs" / app_name, "logs"),
        (_system_path(root, "/Library/Application Support") / app_name, "system-application-support"),
    ]
    for path, kind in name_patterns:
        if path.exists() or path.is_symlink():
            candidates.append(
                _candidate(
                    path,
                    kind=kind,
                    confidence="medium",
                    match_reason="app-name",
                    risk="medium",
                    default_selected=False,
                    app_owner=app_owner,
                    home_root=home_root,
                )
            )
    deduped: dict[str, dict[str, Any]] = {}
    for candidate in candidates:
        deduped.setdefault(str(candidate["path"]), candidate)
    return list(deduped.values())


def _installed_bundle_ids(*, root: Path, home: Path) -> set[str]:
    return {str(app.get("bundle_id")) for app in list_apps(root=root, home=home) if app.get("bundle_id")}


def _orphan_candidate(
    path: Path,
    *,
    kind: str,
    bundle_id: str | None,
    app_name_hint: str,
    match_reason: str,
    risk: str,
    default_selected: bool,
    home_root: Path,
) -> dict[str, Any]:
    app_owner = _app_owner(bundle_id=bundle_id, vendor=None)
    candidate = _candidate(
        path,
        kind=kind,
        confidence="medium",
        match_reason=match_reason,
        risk=risk,
        default_selected=default_selected,
        app_owner=app_owner,
        home_root=home_root,
        bytes_value=_path_size_limited(path),
    )
    candidate["id"] = f"orphan:{candidate['id']}"
    candidate["reason"] = f"Matched {kind} as a likely orphan for an app that is not currently installed."
    candidate["matched_rule"] = f"software-orphan.{kind}.{match_reason}"
    candidate["bundle_id"] = bundle_id
    candidate["app_name_hint"] = app_name_hint
    candidate["installed_app_present"] = False
    candidate["recommended_next_action"] = (
        "review-orphan-before-trash-execution" if candidate["default_selected"] else "manual-review-required"
    )
    candidate = _attach_review_evidence(candidate)
    candidate["review_evidence"]["recommended_next_action"] = candidate["recommended_next_action"]
    return candidate


def _bundle_id_from_saved_state(path: Path) -> str:
    suffix = ".savedState"
    name = path.name
    return name[: -len(suffix)] if name.endswith(suffix) else path.stem


def _bundle_id_from_plist(path: Path) -> str:
    suffix = ".plist"
    name = path.name
    return name[: -len(suffix)] if name.endswith(suffix) else path.stem


def _looks_like_bundle_id(value: str | None) -> bool:
    if not value or "." not in value:
        return False
    lowered = value.lower()
    return lowered.startswith(("com.", "org.", "net.", "io."))


def find_software_orphans(*, root: Path, home: Path) -> dict[str, Any]:
    home_root = _home_root(root, home)
    installed_bundle_ids = _installed_bundle_ids(root=root, home=home)
    scan_roots = [
        _display_path(home_root / "Library/Preferences"),
        _display_path(home_root / "Library/Caches"),
        _display_path(home_root / "Library/Logs"),
        _display_path(home_root / "Library/Application Support"),
        _display_path(home_root / "Library/Containers"),
        _display_path(home_root / "Library/Group Containers"),
        _display_path(home_root / "Library/Saved Application State"),
        _display_path(home_root / "Library/HTTPStorages"),
        _display_path(home_root / "Library/WebKit"),
        _display_path(home_root / "Library/LaunchAgents"),
        _display_path(_system_path(root, "/Library/LaunchAgents")),
        _display_path(_system_path(root, "/Library/LaunchDaemons")),
        _display_path(_system_path(root, "/Library/PrivilegedHelperTools")),
    ]
    candidates: list[dict[str, Any]] = []

    bundle_scans = [
        (home_root / "Library/Preferences", "*.plist", "preferences", "medium", True, _bundle_id_from_plist),
        (home_root / "Library/Caches", "*", "cache", "low", True, lambda path: path.name),
        (home_root / "Library/Logs", "*", "logs", "low", True, lambda path: path.name),
        (home_root / "Library/Containers", "*", "container", "high", False, lambda path: path.name),
        (
            home_root / "Library/Saved Application State",
            "*.savedState",
            "saved-state",
            "low",
            True,
            _bundle_id_from_saved_state,
        ),
        (home_root / "Library/HTTPStorages", "*", "http-storage", "medium", False, lambda path: path.name),
        (home_root / "Library/WebKit", "*", "webkit-data", "medium", False, lambda path: path.name),
        (home_root / "Library/LaunchAgents", "*.plist", "launch-agent", "high", False, _bundle_id_from_plist),
        (_system_path(root, "/Library/LaunchAgents"), "*.plist", "launch-agent", "high", False, _bundle_id_from_plist),
        (
            _system_path(root, "/Library/LaunchDaemons"),
            "*.plist",
            "launch-daemon",
            "high",
            False,
            _bundle_id_from_plist,
        ),
        (
            _system_path(root, "/Library/PrivilegedHelperTools"),
            "*",
            "privileged-helper",
            "critical",
            False,
            lambda path: path.name,
        ),
    ]
    for base, pattern, kind, risk, default_selected, bundle_id_func in bundle_scans:
        if not base.exists():
            continue
        for path in sorted(base.glob(pattern)):
            if not (path.exists() or path.is_symlink()):
                continue
            bundle_id = bundle_id_func(path)
            if (
                not _looks_like_bundle_id(bundle_id)
                or bundle_id.startswith("com.apple.")
                or bundle_id in installed_bundle_ids
            ):
                continue
            candidates.append(
                _orphan_candidate(
                    path,
                    kind=kind,
                    bundle_id=bundle_id,
                    app_name_hint=bundle_id.rsplit(".", 1)[-1],
                    match_reason="missing-installed-bundle-id",
                    risk=risk,
                    default_selected=default_selected,
                    home_root=home_root,
                )
            )

    support_root = home_root / "Library/Application Support"
    app_dirs = {Path(str(app["path"])).stem.lower() for app in list_apps(root=root, home=home)}
    if support_root.exists():
        for path in sorted(child for child in support_root.iterdir() if child.exists() or child.is_symlink()):
            app_name_hint = path.name
            if app_name_hint.lower() in app_dirs:
                continue
            if protection.should_protect_path(path):
                continue
            candidates.append(
                _orphan_candidate(
                    path,
                    kind="application-support",
                    bundle_id=None,
                    app_name_hint=app_name_hint,
                    match_reason="missing-installed-app-name",
                    risk="medium",
                    default_selected=False,
                    home_root=home_root,
                )
            )

    group_root = home_root / "Library/Group Containers"
    if group_root.exists():
        for path in sorted(child for child in group_root.iterdir() if child.exists() or child.is_symlink()):
            bundle_id = protection.bundle_id_for_path(path)
            if not bundle_id or bundle_id.startswith("com.apple.") or bundle_id in installed_bundle_ids:
                continue
            candidates.append(
                _orphan_candidate(
                    path,
                    kind="group-container",
                    bundle_id=bundle_id,
                    app_name_hint=bundle_id.rsplit(".", 1)[-1],
                    match_reason="missing-installed-bundle-id",
                    risk="critical",
                    default_selected=False,
                    home_root=home_root,
                )
            )

    deduped: dict[str, dict[str, Any]] = {}
    for candidate in candidates:
        deduped.setdefault(str(candidate["path"]), candidate)
    candidates = list(deduped.values())
    type_counts: dict[str, int] = {}
    risk_counts: dict[str, int] = {}
    for candidate in candidates:
        leftover_type = str(candidate.get("leftover_type") or "unknown")
        risk = str(candidate.get("risk") or "unknown")
        type_counts[leftover_type] = type_counts.get(leftover_type, 0) + 1
        risk_counts[risk] = risk_counts.get(risk, 0) + 1
    return {
        "schema": "cleanmac.software-orphans.v1",
        "destructive": False,
        "dry_run": True,
        "root": _display_path(root),
        "home": _display_path(home),
        "status": "read-only-orphan-scan",
        "scan_roots": scan_roots,
        "installed_bundle_count": len(installed_bundle_ids),
        "candidate_count": len(candidates),
        "default_selected_count": sum(1 for item in candidates if item.get("default_selected")),
        "estimated_bytes": sum(int(item.get("bytes") or 0) for item in candidates),
        "leftover_type_counts": dict(sorted(type_counts.items())),
        "risk_counts": dict(sorted(risk_counts.items())),
        "safe_to_auto_execute": False,
        "recommended_next_action": "review-orphans-before-any-trash-execution" if candidates else "no_orphans_found",
        "candidates": candidates,
    }


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
    vendor = identity.get("official_uninstaller_vendor") if identity else None
    if not vendor:
        vendor = protection.official_uninstaller_vendor(
            bundle_id=str(identity.get("bundle_id") or "") if identity else None,
            name=str(identity.get("display_name") or app) if identity else app,
            app_path=Path(str(identity.get("path"))) if identity and identity.get("path") else None,
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
            item["why_not_default"] = f"plan blocked: {', '.join(blocked_reasons)}"
    leftover_type_counts: dict[str, int] = {}
    default_selected_count = 0
    protected_count = 0
    for item in candidates:
        leftover_type = str(item.get("leftover_type") or "unknown")
        leftover_type_counts[leftover_type] = leftover_type_counts.get(leftover_type, 0) + 1
        if item.get("default_selected"):
            default_selected_count += 1
        if item.get("protected"):
            protected_count += 1
    recommended_action = "use-official-uninstaller-first" if vendor else "review-leftovers-then-trash-first-execute"
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
            "official_uninstaller_priority": "highest" if vendor else "not-required",
            "recommended_action": recommended_action,
            "protected_data_policy": "skip credentials and user documents by default; route any selected leftovers to Trash only after review-selection confirmation",
            "requires_explicit_execute": True,
            "candidate_count": len(candidates),
            "default_selected_count": default_selected_count,
            "protected_candidate_count": protected_count,
            "candidate_bytes": sum(int(item.get("bytes") or 0) for item in candidates),
            "leftover_type_counts": leftover_type_counts,
            "leftover_types": [
                "cache",
                "logs",
                "preferences",
                "saved_state",
                "containers",
                "credentials",
                "user_documents",
            ],
            "candidate_explainability_fields": [
                "reason",
                "risk_reason",
                "risk_explanation",
                "recovery",
                "matched_rule",
                "app_owner",
                "confidence",
                "leftover_type",
                "contains_user_data",
                "why_not_default",
            ],
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
            **_path_interaction_metadata(path),
            "kind": item.get("kind"),
            "risk": item.get("risk"),
            "bytes": bytes_value,
            "delete_mode": "trash",
            "trash_path": trash_path,
            "status": status,
            "reason": reason,
            "error": error,
            "executed": executed,
            "review_evidence": item.get("review_evidence") if isinstance(item.get("review_evidence"), dict) else None,
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
                    "candidate_review_evidence": item.get("review_evidence")
                    if isinstance(item.get("review_evidence"), dict)
                    else None,
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
    if action == "orphans":
        return find_software_orphans(root=root, home=home)
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
