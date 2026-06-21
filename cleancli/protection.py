"""Protection policy helpers for app/container/bundle data."""

from __future__ import annotations

import fnmatch
import os
import plistlib
from collections.abc import Sequence
from pathlib import Path

from cleancli.protection_data import (
    APP_CLEANUP_RULES,
    APPLE_CONTAINER_CACHE_EXCEPTIONS,
    APPLE_UNINSTALLABLE_BUNDLE_PATTERNS,
    CRITICAL_SYSTEM_PATH_PREFIXES,
    CRITICAL_SYSTEM_PATHS_EXACT,
    DATA_PROTECTED_BUNDLE_PATTERNS,
    DEFAULT_PROTECTED_BUNDLE_IDS,
    OFFICIAL_UNINSTALLER_RULES,
    PROTECTED_BUNDLE_PREFIXES,
    SENSITIVE_USER_DATA_FRAGMENTS,
    SYSTEM_CRITICAL_BUNDLE_PATTERNS,
)


def matches_pattern(path: Path, patterns: Sequence[str]) -> bool:
    path_text = str(path)
    return any(fnmatch.fnmatch(path_text, pattern) or fnmatch.fnmatch(path.name, pattern) for pattern in patterns)


def contains_protected_descendant(path: Path, patterns: Sequence[str]) -> bool:
    if matches_pattern(path, patterns):
        return True
    if not path.is_dir() or path.is_symlink():
        return False
    for current_root, dirnames, filenames in os.walk(path, followlinks=False):
        current = Path(current_root)
        for name in (*dirnames, *filenames):
            if matches_pattern(current / name, patterns):
                return True
    return False


def bundle_matches_pattern(bundle_id: str | None, pattern: str) -> bool:
    if not bundle_id:
        return False
    return fnmatch.fnmatchcase(bundle_id.lower(), pattern.lower())


def bundle_matches_any(bundle_id: str | None, patterns: Sequence[str]) -> bool:
    return any(bundle_matches_pattern(bundle_id, pattern) for pattern in patterns)


def app_protected_data_reason(category_key: str, path: Path) -> str | None:
    protected_patterns = APP_CLEANUP_RULES.get(category_key, {}).get("protected_patterns", ())
    if protected_patterns and contains_protected_descendant(path, protected_patterns):
        return "app-protected-data"
    return None


def should_protect_bundle(bundle_id: str | None) -> bool:
    if not bundle_id:
        return False
    return (
        bundle_id in DEFAULT_PROTECTED_BUNDLE_IDS
        or bundle_id.startswith(PROTECTED_BUNDLE_PREFIXES)
        or bundle_matches_any(bundle_id, DATA_PROTECTED_BUNDLE_PATTERNS)
    )


def should_protect_from_uninstall(bundle_id: str | None) -> bool:
    if not bundle_id:
        return False
    if official_uninstaller_vendor(bundle_id=bundle_id):
        return True
    if bundle_matches_any(bundle_id, APPLE_UNINSTALLABLE_BUNDLE_PATTERNS):
        return False
    return bundle_id in DEFAULT_PROTECTED_BUNDLE_IDS or bundle_matches_any(bundle_id, SYSTEM_CRITICAL_BUNDLE_PATTERNS)


def _contains_sensitive_fragment(path_text: str, fragment: str) -> bool:
    normalized_fragment = fragment.rstrip("/")
    if any(char in normalized_fragment for char in "*?["):
        return fnmatch.fnmatchcase(path_text, f"*{normalized_fragment}*") or fnmatch.fnmatchcase(
            path_text, f"*{normalized_fragment}/*"
        )
    return path_text.endswith(normalized_fragment) or fragment in path_text or f"{normalized_fragment}/" in path_text


def should_protect_data(path: Path) -> bool:
    text = str(path)
    lowered = text.lower()
    if any(_contains_sensitive_fragment(lowered, fragment) for fragment in SENSITIVE_USER_DATA_FRAGMENTS):
        return True
    lowered_exceptions = tuple(item.lower() for item in APPLE_CONTAINER_CACHE_EXCEPTIONS)
    if "/library/containers/com.apple." in lowered and not any(item.lower() in lowered for item in lowered_exceptions):
        return True
    if "/library/group containers/group.com.apple." in lowered:
        return True
    if "/library/group containers/systemgroup.com.apple." in lowered:
        return True
    return False


def is_critical_system_component(path: Path) -> bool:
    text = str(path)
    return text in CRITICAL_SYSTEM_PATHS_EXACT or text.startswith(CRITICAL_SYSTEM_PATH_PREFIXES)


def should_protect_path(path: Path) -> bool:
    return is_critical_system_component(path) or should_protect_data(path)


def bundle_id_for_app(app_path: Path) -> str | None:
    plist_path = app_path / "Contents" / "Info.plist"
    if not plist_path.exists():
        return None
    try:
        with plist_path.open("rb") as handle:
            value = plistlib.load(handle).get("CFBundleIdentifier")
    except (OSError, plistlib.InvalidFileException, ValueError):
        return None
    return value if isinstance(value, str) and "." in value else None


def normalize_group_container_id(identifier: str) -> str | None:
    if identifier.startswith(("group.", "systemgroup.")):
        stripped = identifier.split(".", 1)[1]
        return stripped if stripped.startswith("com.") else identifier
    if "." in identifier:
        parts = identifier.split(".")
        for index, part in enumerate(parts):
            if part == "com" and index + 1 < len(parts):
                return ".".join(parts[index:])
        return identifier
    return None


def bundle_id_for_path(path: Path) -> str | None:
    parts = path.parts
    for index, part in enumerate(parts):
        if part == "Containers" and index + 1 < len(parts):
            candidate = parts[index + 1]
            if candidate.startswith("com."):
                return candidate
        if part == "Group Containers" and index + 1 < len(parts):
            return normalize_group_container_id(parts[index + 1])
    if path.suffix == ".app":
        bundle_id = bundle_id_for_app(path)
        if bundle_id:
            return bundle_id
    for part in reversed(parts):
        if part.startswith("com.") and "." in part:
            return part
    return None


def group_container_name_for_path(path: Path) -> str | None:
    parts = path.parts
    for index, part in enumerate(parts):
        if part == "Group Containers" and index + 1 < len(parts):
            return parts[index + 1]
    return None


def is_group_container_cache_or_tmp_path(path: Path) -> bool:
    parts = set(path.parts)
    return bool({"Caches", "tmp", "Logs"} & parts)


def is_protected_group_container_path(path: Path) -> bool:
    name = group_container_name_for_path(path)
    if not name:
        return False
    lowered = name.lower()
    if lowered.startswith(("group.com.apple", "systemgroup.com.apple")):
        return True
    if "safari" in lowered and "extension" in lowered:
        return True
    bundle_id = normalize_group_container_id(name)
    if should_protect_bundle(bundle_id):
        return not ("Logs" in path.parts and "Caches" not in path.parts and "tmp" not in path.parts)
    return False


def is_protected_user_data_path(path: Path) -> bool:
    return should_protect_data(path)


def container_policy_reason(category_key: str, path: Path) -> str | None:
    if category_key in {"userAppCache", "userAppLogs"}:
        bundle_id = bundle_id_for_path(path)
        if should_protect_bundle(bundle_id) and category_key != "userAppLogs":
            return "protected-container-data"
    if category_key == "groupContainerCaches":
        if is_protected_group_container_path(path):
            return "protected-group-container"
        if not is_group_container_cache_or_tmp_path(path):
            return "outside-group-container-cache"
    return None


def official_uninstaller_vendor(
    *, bundle_id: str | None = None, name: str | None = None, app_path: Path | None = None
) -> str | None:
    normalized_bundle = (bundle_id or "").lower()
    haystack = " ".join(item for item in (name, str(app_path) if app_path else None) if item).lower()
    for rule in OFFICIAL_UNINSTALLER_RULES:
        vendor = str(rule["vendor"])
        bundle_prefixes = tuple(str(prefix) for prefix in rule.get("bundle_prefixes", ()))
        name_fragments = tuple(str(fragment) for fragment in rule.get("name_fragments", ()))
        if normalized_bundle and any(normalized_bundle.startswith(prefix.lower()) for prefix in bundle_prefixes):
            return vendor
        if haystack and any(fragment.lower() in haystack for fragment in name_fragments):
            return vendor
    return None


def bundle_policy_reason(
    bundle_id: str | None, *, bundle_allowlist: Sequence[str] = (), bundle_blocklist: Sequence[str] = ()
) -> str | None:
    if bundle_id is None:
        return None
    allow = set(bundle_allowlist)
    block = set(bundle_blocklist)
    if allow and bundle_id not in allow:
        return "bundle-not-allowlisted"
    if bundle_id in block:
        return "bundle-blocklisted"
    return None
