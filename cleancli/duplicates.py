"""Duplicate file discovery and candidate row assembly."""

from __future__ import annotations

import hashlib
import os
from pathlib import Path
from typing import Any, Callable, Protocol, Sequence

from . import scan


class DuplicateCategory(Protocol):
    description: str
    risk: str


def find_duplicate_files(
    paths: Sequence[Path],
    *,
    root: Path,
    home: Path,
    min_size_mb: int = 1,
    recursive: bool = True,
    remap_path: Callable[[str], str],
    display_path: Callable[[Path | str], str],
    human_size: Callable[[int | None], str],
) -> dict[str, Any]:
    min_bytes = max(min_size_mb, 0) * 1024 * 1024
    size_groups: dict[int, list[Path]] = {}

    for base_path in paths:
        scan_path = Path(remap_path(str(base_path)))
        if not scan_path.exists():
            continue
        for current_root, _dirs, files in os.walk(scan_path, followlinks=False):
            current = Path(current_root)
            for name in files:
                child = current / name
                if child.is_symlink():
                    continue
                try:
                    size = child.lstat().st_size
                except OSError:
                    continue
                if size < min_bytes:
                    continue
                size_groups.setdefault(size, []).append(child)
            if not recursive:
                break

    hash_groups: dict[str, list[dict[str, Any]]] = {}
    total_duplicates = 0
    wasted_bytes = 0

    for size, file_list in size_groups.items():
        if len(file_list) < 2:
            continue
        for file_path in file_list:
            try:
                digest = _sha256_file(file_path)
            except OSError:
                continue
            hash_groups.setdefault(digest, []).append(
                {
                    "path": display_path(file_path),
                    "bytes": size,
                    "human": human_size(size),
                }
            )

    groups: list[dict[str, Any]] = []
    for digest, dup_file_list in hash_groups.items():
        if len(dup_file_list) < 2:
            continue
        group_size = dup_file_list[0]["bytes"]
        wasted = group_size * (len(dup_file_list) - 1)
        total_duplicates += len(dup_file_list) - 1
        wasted_bytes += wasted
        groups.append(
            {
                "hash": digest,
                "file_count": len(dup_file_list),
                "bytes_per_file": group_size,
                "wasted_bytes": wasted,
                "wasted_human": human_size(wasted),
                "files": dup_file_list,
            }
        )

    groups.sort(key=lambda g: (g["wasted_bytes"], g["hash"]), reverse=True)

    return {
        "schema": "cleanmac.duplicate-files.v1",
        "destructive": False,
        "min_size_mb": min_size_mb,
        "total_groups": len(groups),
        "total_duplicate_files": total_duplicates,
        "wasted_bytes": wasted_bytes,
        "wasted_human": human_size(wasted_bytes),
        "groups": groups,
    }


def duplicate_candidates_from_result(result: dict[str, Any]) -> dict[str, dict[str, Any]]:
    candidates: dict[str, dict[str, Any]] = {}
    for group in result.get("groups", []):
        files = group.get("files", []) if isinstance(group, dict) else []
        if not isinstance(files, list) or len(files) < 2:
            continue
        keep_path = files[0]["path"]
        for file_info in files[1:]:
            candidates[str(file_info["path"])] = {
                "duplicate_group_hash": group["hash"],
                "duplicate_group_size": group["bytes_per_file"],
                "duplicate_group_file_count": group["file_count"],
                "duplicate_keep_path": keep_path,
            }
    return candidates


def duplicate_candidate_rows(
    *,
    dup_candidates: dict[str, dict[str, Any]],
    category: DuplicateCategory,
    root: Path,
    include_patterns: Sequence[str],
    exclude_patterns: Sequence[str],
    older_than_days: float | None,
    name_regex: str | None,
    bundle_allowlist: Sequence[str],
    bundle_blocklist: Sequence[str],
    review_selected_paths: set[str] | None,
    delete_mode: str,
    display_path: Callable[[Path | str], str],
    human_size: Callable[[int | None], str],
    path_interaction_metadata: Callable[[Path], dict[str, Any]],
    filter_reason: Callable[..., str | None],
    assert_safe_to_delete: Callable[[Path], None],
    bundle_id_for_path: Callable[[Path], str | None],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for dup_path, dup_meta in dup_candidates.items():
        entry = Path(dup_path)
        try:
            assert_safe_to_delete(entry)
        except Exception:
            continue
        reason = filter_reason(
            category,
            entry,
            root=root,
            include_patterns=include_patterns,
            exclude_patterns=exclude_patterns,
            older_than_days=older_than_days,
            name_regex=name_regex,
            bundle_allowlist=bundle_allowlist,
            bundle_blocklist=bundle_blocklist,
        )
        if reason:
            continue
        display_entry = display_path(entry)
        if review_selected_paths is not None and display_entry not in review_selected_paths:
            continue
        size = scan.path_size_bytes(entry)
        rows.append(
            {
                "category": "duplicateFiles",
                "parent": display_path(entry.parent),
                "path": display_entry,
                **path_interaction_metadata(entry),
                "bytes": size,
                "human": human_size(size),
                "bundle_id": bundle_id_for_path(entry),
                "delete_mode": delete_mode,
                "trash_path": None,
                "deleted": False,
                "risk": category.risk,
                "default_selected": True,
                "protected": False,
                "duplicate_group_hash": dup_meta["duplicate_group_hash"],
                "duplicate_group_size": dup_meta["duplicate_group_size"],
                "duplicate_group_file_count": dup_meta["duplicate_group_file_count"],
                "duplicate_keep_path": dup_meta["duplicate_keep_path"],
                "review_evidence": {
                    "schema": "cleanmac.candidate-review-evidence.v1",
                    "matched_rule": "clean.duplicateFiles.candidate",
                    "match_reason": "duplicate-content-hash",
                    "confidence": "high",
                    "risk": category.risk,
                    "risk_reason": category.description,
                    "risk_explanation": (
                        f"SHA-256 hash matches {dup_meta['duplicate_group_file_count'] - 1} other file(s); "
                        f"one copy preserved at {dup_meta['duplicate_keep_path']}"
                    ),
                    "default_selected": True,
                    "why_not_default": None,
                    "protected": False,
                    "delete_mode": delete_mode,
                    "recovery": "Duplicate copies are safe to remove; one original copy is preserved per content group.",
                    "contains_user_data": True,
                    "shared_container": False,
                    "recommended_next_action": "review-duplicate-group-before-deletion",
                },
            }
        )
    return rows


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file:
        while True:
            chunk = file.read(65536)
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest()


__all__ = [
    "find_duplicate_files",
    "duplicate_candidates_from_result",
    "duplicate_candidate_rows",
]
