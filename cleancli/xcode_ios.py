"""Read-only Xcode and iOS candidate evidence emitters."""

from __future__ import annotations

import os
import subprocess
import time
from pathlib import Path
from typing import Any


XCODE_IOS_EVIDENCE_FIELDS: tuple[str, ...] = (
    "path_role",
    "tool_domain",
    "regenerable",
    "contains_user_data",
    "release_artifact_risk",
    "active_runtime_hint",
    "retention_reason",
    "default_selected",
    "why_not_default",
    "recommended_next_action",
)

XCODE_IOS_PATH_POLICIES: tuple[dict[str, Any], ...] = (
    {
        "path_role": "xcode_derived_data",
        "category": "xcode",
        "tool_domain": "xcode",
        "regenerable": True,
        "contains_user_data": False,
        "release_artifact_risk": "low",
        "active_runtime_hint": "xcode_build_activity_possible",
        "retention_reason": "Build products are reproducible, but active Xcode builds should be avoided.",
        "default_selected": True,
        "why_not_default": None,
        "recommended_next_action": "Allow only through dry-run, review-selection, Trash routing, and delete budget gates.",
    },
    {
        "path_role": "xcode_module_cache",
        "category": "xcode",
        "tool_domain": "xcode",
        "regenerable": True,
        "contains_user_data": False,
        "release_artifact_risk": "low",
        "active_runtime_hint": "xcode_build_activity_possible",
        "retention_reason": "Compiler module cache is reproducible after rebuild.",
        "default_selected": True,
        "why_not_default": None,
        "recommended_next_action": "Allow only through dry-run, review-selection, Trash routing, and delete budget gates.",
    },
    {
        "path_role": "core_simulator_cache",
        "category": "xcode",
        "tool_domain": "simulator",
        "regenerable": True,
        "contains_user_data": False,
        "release_artifact_risk": "low",
        "active_runtime_hint": "booted_simulator_possible",
        "retention_reason": "Simulator caches are reproducible, but unavailable devices/runtimes must be inspected first.",
        "default_selected": True,
        "why_not_default": None,
        "recommended_next_action": "Inspect unavailable simulator devices read-only before any future deletion workflow.",
    },
    {
        "path_role": "xcode_products",
        "category": "xcode",
        "tool_domain": "xcode",
        "regenerable": "unknown",
        "contains_user_data": False,
        "release_artifact_risk": "medium",
        "active_runtime_hint": "xcode_build_activity_possible",
        "retention_reason": "Products may include outputs the user expects to keep outside a reproducible build.",
        "default_selected": False,
        "why_not_default": "Not selected until the report can prove the product is reproducible.",
        "recommended_next_action": "Show for review only; require explicit selection and Trash execution if implemented later.",
    },
    {
        "path_role": "xcode_archives",
        "category": "xcode",
        "tool_domain": "xcode",
        "regenerable": False,
        "contains_user_data": False,
        "release_artifact_risk": "high",
        "active_runtime_hint": "release_evidence_possible",
        "retention_reason": "Archives may be App Store, notarization, dSYM, or release evidence artifacts.",
        "default_selected": False,
        "why_not_default": "Archives are never default selected.",
        "recommended_next_action": "Review individually; do not auto-select in cleanmac governed plans.",
    },
    {
        "path_role": "device_support",
        "category": "deviceFirmware",
        "tool_domain": "xcode",
        "regenerable": "partial",
        "contains_user_data": False,
        "release_artifact_risk": "medium",
        "active_runtime_hint": "connected_device_os_possible",
        "retention_reason": "Keep current devices and recent OS versions until retention rules are available.",
        "default_selected": False,
        "why_not_default": "Current/recent device support retention is not implemented yet.",
        "recommended_next_action": "Report only; add current/recent OS retention before offering cleanup.",
    },
    {
        "path_role": "ios_backup",
        "category": "iosBackups",
        "tool_domain": "ios",
        "regenerable": False,
        "contains_user_data": True,
        "release_artifact_risk": "high",
        "active_runtime_hint": "mobile_device_backup_possible",
        "retention_reason": "MobileSync backups can contain user data and device recovery state.",
        "default_selected": False,
        "why_not_default": "iOS backups are never default selected.",
        "recommended_next_action": "Enumerate backups read-only and require explicit user review outside this governance phase.",
    },
    {
        "path_role": "unavailable_simulator_device",
        "category": "xcode",
        "tool_domain": "simulator",
        "regenerable": "unknown",
        "contains_user_data": "unknown",
        "release_artifact_risk": "medium",
        "active_runtime_hint": "simctl_unavailable_state",
        "retention_reason": "Unavailable simulator devices require read-only simctl evidence before cleanup eligibility.",
        "default_selected": False,
        "why_not_default": "Unavailable simulator deletion is read-only governance only in this phase.",
        "recommended_next_action": "Use xcrun simctl list devices unavailable as evidence; do not execute delete commands.",
    },
)

_POLICY_BY_ROLE = {str(policy["path_role"]): dict(policy) for policy in XCODE_IOS_PATH_POLICIES}

_ROLE_ROOTS: tuple[tuple[str, str], ...] = (
    ("xcode_derived_data", "~/Library/Developer/Xcode/DerivedData"),
    ("xcode_module_cache", "~/Library/Developer/Xcode/ModuleCache.noindex"),
    ("core_simulator_cache", "~/Library/Developer/CoreSimulator/Caches"),
    ("xcode_products", "~/Library/Developer/Xcode/Products"),
    ("xcode_archives", "~/Library/Developer/Xcode/Archives"),
    ("device_support", "~/Library/Developer/Xcode/iOS DeviceSupport"),
    ("device_support", "~/Library/Developer/Xcode/watchOS DeviceSupport"),
    ("device_support", "~/Library/Developer/Xcode/tvOS DeviceSupport"),
    ("ios_backup", "~/Library/Application Support/MobileSync/Backup"),
)


def display_path(path: Path | str) -> str:
    text = str(path)
    if text.startswith("/private/var/"):
        return "/var/" + text[len("/private/var/") :]
    return text


def human_size(size: int | None) -> str:
    if size is None:
        return "unknown"
    value = float(size)
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if value < 1024 or unit == "TB":
            return f"{int(value)} B" if unit == "B" else f"{value:.2f} {unit}"
        value /= 1024
    return f"{size} B"


def remap_path(pattern: str, *, root: Path, home: Path) -> Path:
    expanded = home / pattern[2:] if pattern.startswith("~/") else Path(pattern)
    if root == Path("/"):
        return expanded
    if expanded.is_absolute():
        return root / str(expanded).lstrip("/")
    return root / expanded


def path_size_bytes(path: Path) -> int:
    try:
        if not path.exists() and not path.is_symlink():
            return 0
        if path.is_symlink() or path.is_file():
            return path.lstat().st_size
        total = 0
        for current_root, dirs, files in os.walk(path, followlinks=False):
            current = Path(current_root)
            for name in list(dirs):
                child = current / name
                try:
                    total += child.lstat().st_size
                    if child.is_symlink():
                        dirs.remove(name)
                except OSError:
                    continue
            for name in files:
                try:
                    total += (current / name).lstat().st_size
                except OSError:
                    continue
        return total
    except OSError:
        return 0


def _iter_role_entries(root_path: Path) -> list[Path]:
    if not root_path.exists():
        return []
    if not root_path.is_dir():
        return [root_path]
    try:
        return sorted(root_path.iterdir(), key=lambda path: path.name)
    except OSError:
        return []


def _device_support_retention(entry: Path) -> str:
    version_text = entry.name
    if any(fragment in version_text.lower() for fragment in ("current", "latest")):
        return "keep-current-device-support"
    return "report-only-until-current-and-recent-os-retention-is-available"


def _candidate_id(path_role: str, path: Path) -> str:
    import hashlib

    digest = hashlib.sha256(f"{path_role}:{display_path(path)}".encode("utf-8")).hexdigest()[:16]
    return f"xcode-ios-{path_role}-{digest}"


def _candidate_from_path(path_role: str, path: Path, *, source: str) -> dict[str, Any]:
    policy = dict(_POLICY_BY_ROLE[path_role])
    size = path_size_bytes(path)
    review_evidence = {
        "schema": "cleanmac.candidate-review-evidence.v1",
        "matched_rule": f"xcode-ios.{path_role}",
        "match_reason": policy["retention_reason"],
        "confidence": "high" if policy["regenerable"] is True else "medium",
        "risk": policy["release_artifact_risk"],
        "risk_reason": policy["retention_reason"],
        "risk_explanation": policy["retention_reason"],
        "default_selected": policy["default_selected"],
        "why_not_default": policy["why_not_default"],
        "protected": False,
        "delete_mode": "trash",
        "recovery": "This source is read-only in cleanmac.xcode-ios-candidates.v1; future execution must pass review-selection, Trash, budget, and confirmation gates.",
        "contains_user_data": policy["contains_user_data"] is True,
        "shared_container": False,
        "recommended_next_action": policy["recommended_next_action"],
    }
    candidate = {
        "id": _candidate_id(path_role, path),
        "schema": "cleanmac.xcode-ios-candidate.v1",
        "kind": "xcode-ios-candidate",
        "path": display_path(path),
        "name": path.name,
        "bytes": size,
        "human": human_size(size),
        "size_bytes": size,
        "size_human": human_size(size),
        "source": source,
        "risk": policy["release_artifact_risk"],
        "confidence": review_evidence["confidence"],
        "review_evidence": review_evidence,
        **policy,
    }
    if path_role == "device_support":
        candidate["suppression_reason"] = _device_support_retention(path)
    if path_role in {"xcode_archives", "ios_backup", "unavailable_simulator_device"}:
        candidate["suppression_reason"] = policy["why_not_default"]
    return candidate


def _parse_unavailable_simulator_lines(text: str) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    current_runtime = ""
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if line.startswith("--") and line.endswith("--"):
            current_runtime = line.strip("-").strip()
            continue
        if "(unavailable" not in line.lower():
            continue
        rows.append({"name": line, "runtime": current_runtime})
    return rows


def _unavailable_simulator_candidates(*, max_scan_entries: int | None) -> list[dict[str, Any]]:
    command = ["xcrun", "simctl", "list", "devices", "unavailable"]
    try:
        result = subprocess.run(command, capture_output=True, text=True, timeout=5)
    except (OSError, subprocess.SubprocessError):
        return []
    if result.returncode != 0:
        return []
    rows = _parse_unavailable_simulator_lines(result.stdout)
    if max_scan_entries is not None:
        rows = rows[: max(max_scan_entries, 0)]
    policy = dict(_POLICY_BY_ROLE["unavailable_simulator_device"])
    candidates: list[dict[str, Any]] = []
    for row in rows:
        name = row["name"]
        runtime = row["runtime"]
        synthetic_path = f"simctl://unavailable/{runtime}/{name}"
        candidate = _candidate_from_path(
            "unavailable_simulator_device",
            Path(synthetic_path),
            source="xcrun simctl list devices unavailable",
        )
        candidate.update(
            {
                "path": synthetic_path,
                "name": name,
                "runtime": runtime,
                "bytes": 0,
                "human": human_size(0),
                "size_bytes": 0,
                "size_human": human_size(0),
                **policy,
            }
        )
        candidates.append(candidate)
    return candidates


def _scan_path_candidates(*, root: Path, home: Path, max_scan_entries: int | None) -> tuple[list[dict[str, Any]], bool]:
    candidates: list[dict[str, Any]] = []
    scanned_entries = 0
    truncated = False
    for path_role, pattern in _ROLE_ROOTS:
        root_path = remap_path(pattern, root=root, home=home)
        for entry in _iter_role_entries(root_path):
            if max_scan_entries is not None and scanned_entries >= max(max_scan_entries, 0):
                truncated = True
                return candidates, truncated
            scanned_entries += 1
            candidates.append(_candidate_from_path(path_role, entry, source=pattern))
    sim_candidates = _unavailable_simulator_candidates(max_scan_entries=max_scan_entries)
    if max_scan_entries is not None:
        remaining = max(max_scan_entries, 0) - scanned_entries
        if remaining < len(sim_candidates):
            sim_candidates = sim_candidates[: max(remaining, 0)]
            truncated = True
    candidates.extend(sim_candidates)
    return candidates, truncated


def _count_by(candidates: list[dict[str, Any]], field: str) -> dict[str, int]:
    counts: dict[str, int] = {}
    for candidate in candidates:
        key = str(candidate.get(field) if candidate.get(field) is not None else "unknown")
        counts[key] = counts.get(key, 0) + 1
    return dict(sorted(counts.items()))


def _bytes_by_role(candidates: list[dict[str, Any]]) -> dict[str, int]:
    totals: dict[str, int] = {}
    for candidate in candidates:
        role = str(candidate.get("path_role") or "unknown")
        totals[role] = totals.get(role, 0) + int(candidate.get("bytes") or 0)
    return dict(sorted(totals.items()))


def _default_policy_key(candidate: dict[str, Any]) -> str:
    return "default_selected" if candidate.get("default_selected") is True else "manual_review"


def render_xcode_ios_candidates(
    *,
    root: Path,
    home: Path,
    limit: int | None = 100,
    max_scan_entries: int | None = 1000,
    summary_only: bool = False,
) -> dict[str, Any]:
    started = time.monotonic()
    candidates, scan_truncated = _scan_path_candidates(root=root, home=home, max_scan_entries=max_scan_entries)
    candidates.sort(key=lambda row: (-int(row.get("bytes") or 0), str(row.get("path") or "")))
    shown_limit = None if limit is None else max(limit, 0)
    shown_candidates = [] if summary_only else candidates[:shown_limit]
    output_truncated = False if summary_only else shown_limit is not None and len(candidates) > shown_limit
    estimated_bytes_by_role = _bytes_by_role(candidates)
    total_bytes = sum(estimated_bytes_by_role.values())
    return {
        "schema": "cleanmac.xcode-ios-candidates.v1",
        "destructive": False,
        "dry_run": True,
        "root": display_path(root),
        "home": display_path(home),
        "summary_only": summary_only,
        "limit": limit,
        "max_scan_entries": max_scan_entries,
        "scan_duration_ms": int((time.monotonic() - started) * 1000),
        "candidate_count": len(candidates),
        "shown_candidate_count": len(shown_candidates),
        "truncated": scan_truncated or output_truncated,
        "scan_truncated": scan_truncated,
        "output_truncated": output_truncated,
        "total_bytes": total_bytes,
        "total_human": human_size(total_bytes),
        "candidate_count_by_path_role": _count_by(candidates, "path_role"),
        "candidate_count_by_default_policy": _count_by(
            [{**candidate, "default_policy": _default_policy_key(candidate)} for candidate in candidates],
            "default_policy",
        ),
        "estimated_bytes_by_path_role": estimated_bytes_by_role,
        "estimated_human_by_path_role": {
            role: human_size(size) for role, size in estimated_bytes_by_role.items()
        },
        "evidence_fields": list(XCODE_IOS_EVIDENCE_FIELDS),
        "never_default_selected_path_roles": [
            "xcode_archives",
            "device_support",
            "ios_backup",
            "unavailable_simulator_device",
        ],
        "read_only": True,
        "destructive_paths_absent": True,
        "next_review_command": [
            "cleanmac",
            "--json",
            "review",
            "--input-file",
            "<xcode-ios-candidates.json>",
        ],
        "candidates": shown_candidates,
    }

