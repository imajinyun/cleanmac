"""Filesystem scan helpers for cleanup candidate discovery."""

from __future__ import annotations

import os
import re
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Mapping, Protocol, Sequence

from . import protection


@dataclass(frozen=True)
class ScanTarget:
    category: str
    source_pattern: str
    path: Path
    matched: bool
    from_glob: bool
    delete_target: bool = False


class CategoryScanDefaults(Protocol):
    key: str
    description: str
    risk: str
    requires_privilege: bool
    full_disk_access: bool
    default_include_patterns: tuple[str, ...]
    default_exclude_patterns: tuple[str, ...]
    default_older_than_days: float | None
    default_min_size_mb: int


@dataclass(frozen=True)
class ScanBudget:
    max_delete_mb: float | None = None
    max_items: int | None = None
    applies_to_execute: bool = False
    message: str = "inspect is non-destructive; use plan or clean to enforce these budgets before deletion."

    def summary(self, *, candidate_count: int, candidate_bytes: int, human_size: Callable[[int | None], str]) -> dict[str, Any]:
        max_delete_bytes = None if self.max_delete_mb is None else int(self.max_delete_mb * 1024 * 1024)
        return {
            "candidate_count": candidate_count,
            "candidate_bytes": candidate_bytes,
            "candidate_human": human_size(candidate_bytes),
            "max_items": self.max_items,
            "within_max_items": self.max_items is None or candidate_count <= self.max_items,
            "max_delete_mb": self.max_delete_mb,
            "max_delete_bytes": max_delete_bytes,
            "within_max_delete_budget": max_delete_bytes is None or candidate_bytes <= max_delete_bytes,
            "applies_to_execute": self.applies_to_execute,
            "message": self.message,
        }


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


def child_entries(path: Path) -> list[Path]:
    if not path.exists() and not path.is_symlink():
        return []
    if path.is_symlink() or path.is_file():
        return [path]
    try:
        return [path / name for name in os.listdir(path)]
    except OSError:
        return []


def inspect_entries(path: Path, *, recursive: bool) -> list[tuple[Path, int]]:
    direct = [(entry, 1) for entry in child_entries(path)]
    if not recursive:
        return direct
    rows = list(direct)
    for entry, _ in direct:
        if not entry.is_dir() or entry.is_symlink():
            continue
        base_depth = len(entry.parts)
        for current_root, dirs, files in os.walk(entry, followlinks=False):
            current = Path(current_root)
            depth = len(current.parts) - base_depth + 1
            for name in list(dirs):
                child = current / name
                rows.append((child, depth + 1))
                if child.is_symlink():
                    dirs.remove(name)
            for name in files:
                rows.append((current / name, depth + 1))
    return rows


def candidate_entries(target: ScanTarget, *, recursive: bool) -> list[tuple[Path, int]]:
    if target.delete_target:
        return [(target.path, 0)] if target.matched else []
    return inspect_entries(target.path, recursive=recursive)


def clean_candidate_entries(target: ScanTarget) -> list[Path]:
    if target.delete_target:
        return [target.path] if target.matched else []
    return child_entries(target.path)


def matches_exclude(path: Path, patterns: Sequence[str]) -> bool:
    return protection.matches_pattern(path, patterns)


def matches_include(path: Path, patterns: Sequence[str]) -> bool:
    if not patterns:
        return True
    return protection.matches_pattern(path, patterns)


def effective_include_patterns(
    category: CategoryScanDefaults,
    include_patterns: Sequence[str],
) -> tuple[str, ...]:
    return tuple(include_patterns) if include_patterns else category.default_include_patterns


def effective_exclude_patterns(
    category: CategoryScanDefaults,
    exclude_patterns: Sequence[str],
) -> tuple[str, ...]:
    return tuple(exclude_patterns) + category.default_exclude_patterns


def effective_older_than_days(category: CategoryScanDefaults, older_than_days: float | None) -> float | None:
    return older_than_days if older_than_days is not None else category.default_older_than_days


def effective_min_size_mb(category: CategoryScanDefaults, min_size_mb: int) -> int:
    return min_size_mb if min_size_mb > 0 else category.default_min_size_mb


def matches_name_regex(path: Path, name_regex: str | None) -> bool:
    if not name_regex:
        return True
    try:
        return re.search(name_regex, path.name) is not None
    except re.error as exc:
        raise ValueError(f"Invalid --name-regex: {exc}") from exc


def is_old_enough(path: Path, older_than_days: float | None) -> bool:
    if older_than_days is None:
        return True
    try:
        age_seconds = time.time() - path.lstat().st_mtime
    except OSError:
        return False
    return age_seconds >= max(older_than_days, 0) * 24 * 60 * 60


def _row_bytes(row: Mapping[str, Any]) -> int:
    value = row.get("bytes", 0)
    return int(value) if isinstance(value, int | float) else 0


def rows_by_category(
    rows: Sequence[Mapping[str, Any]],
    *,
    human_size: Callable[[int | None], str],
) -> dict[str, dict[str, Any]]:
    output: dict[str, dict[str, Any]] = {}
    for row in rows:
        key = str(row["category"])
        current = output.setdefault(key, {"count": 0, "bytes": 0, "human": human_size(0)})
        current["count"] = int(current["count"]) + 1
        current["bytes"] = int(current["bytes"]) + int(row.get("bytes", 0))
        current["human"] = human_size(int(current["bytes"]))
    return output


def skipped_summary(
    skipped: Sequence[Mapping[str, Any]],
    *,
    human_size: Callable[[int | None], str],
) -> dict[str, Any]:
    by_reason: dict[str, int] = {}
    total_bytes = 0
    for row in skipped:
        reason = str(row["reason"])
        by_reason[reason] = by_reason.get(reason, 0) + 1
        total_bytes += int(row.get("bytes", 0))
    return {"count": len(skipped), "bytes": total_bytes, "human": human_size(total_bytes), "by_reason": by_reason}


def inspect_items(
    categories: Sequence[CategoryScanDefaults],
    *,
    targets: Sequence[ScanTarget],
    category_by_key: Mapping[str, CategoryScanDefaults],
    root: Path,
    limit: int,
    recursive: bool = False,
    min_size_mb: int = 0,
    sort: str = "size-desc",
    include_patterns: Sequence[str] = (),
    exclude_patterns: Sequence[str] = (),
    older_than_days: float | None = None,
    name_regex: str | None = None,
    max_delete_mb: float | None = None,
    max_items: int | None = None,
    bundle_allowlist: Sequence[str] = (),
    bundle_blocklist: Sequence[str] = (),
    display_path: Callable[[Path | str], str],
    human_size: Callable[[int | None], str],
    path_interaction_metadata: Callable[[Path], dict[str, Any]],
    skipped_row: Callable[[str, Path, Path, str], dict[str, Any]],
    filter_reason: Callable[..., str | None],
    render_ai_summary: Callable[..., dict[str, Any]],
) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    skipped: list[dict[str, Any]] = []
    for target in targets:
        category = category_by_key[target.category]
        min_size_bytes = max(effective_min_size_mb(category, min_size_mb), 0) * 1024 * 1024
        for entry, depth in candidate_entries(target, recursive=recursive):
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
                skipped.append(skipped_row(target.category, target.path, entry, reason))
                continue
            size = path_size_bytes(entry)
            if size < min_size_bytes:
                skipped.append(skipped_row(target.category, target.path, entry, "below-min-size"))
                continue
            default_selected = not category.requires_privilege
            rows.append(
                {
                    "category": target.category,
                    "parent": display_path(target.path),
                    "path": display_path(entry),
                    **path_interaction_metadata(entry),
                    "depth": depth,
                    "bytes": size,
                    "human": human_size(size),
                    "risk": category.risk,
                    "default_selected": default_selected,
                    "protected": False,
                    "delete_mode": "trash",
                    "review_evidence": {
                        "schema": "cleanmac.candidate-review-evidence.v1",
                        "matched_rule": f"clean.{target.category}.candidate",
                        "match_reason": target.category,
                        "confidence": "medium",
                        "risk": category.risk,
                        "risk_reason": category.description,
                        "risk_explanation": category.description,
                        "default_selected": default_selected,
                        "why_not_default": None
                        if default_selected
                        else "privileged category requires explicit review before execution",
                        "protected": False,
                        "delete_mode": "trash",
                        "recovery": "Execution is gated and Trash-first when this candidate is executable.",
                        "contains_user_data": category.full_disk_access or category.risk in {"high", "critical"},
                        "shared_container": target.category == "groupContainerCaches",
                        "recommended_next_action": "review-default-selection-before-trash-execution"
                        if default_selected
                        else "manual-review-required",
                    },
                }
            )
    if sort == "size-asc":
        rows.sort(key=lambda row: (_row_bytes(row), str(row["path"])))
    elif sort == "path":
        rows.sort(key=lambda row: str(row["path"]))
    else:
        rows.sort(key=lambda row: (_row_bytes(row), str(row["path"])), reverse=True)
    total_candidates = len(rows)
    total_bytes = sum(_row_bytes(row) for row in rows)
    budget_summary = ScanBudget(max_delete_mb=max_delete_mb, max_items=max_items).summary(
        candidate_count=total_candidates,
        candidate_bytes=total_bytes,
        human_size=human_size,
    )
    shown_rows = rows if limit < 0 else rows[:limit]
    return {
        "schema": "cleanmac.inspect.v1",
        "destructive": False,
        "dry_run": True,
        "ai_summary": render_ai_summary(
            list(categories),
            phase="inspect",
            total_bytes=total_bytes,
            item_count=total_candidates,
            skipped_count=len(skipped),
            recommended_next_action="generate_plan" if total_candidates else "no_action",
        ),
        "total_candidates": total_candidates,
        "shown_candidates": len(shown_rows),
        "total_bytes": total_bytes,
        "total_human": human_size(total_bytes),
        "recursive": recursive,
        "min_size_mb": min_size_mb,
        "effective_category_defaults": {
            category.key: {
                "older_than_days": effective_older_than_days(category, older_than_days),
                "min_size_mb": effective_min_size_mb(category, min_size_mb),
                "include_patterns": list(effective_include_patterns(category, include_patterns)),
                "exclude_patterns": list(effective_exclude_patterns(category, exclude_patterns)),
            }
            for category in categories
        },
        "sort": sort,
        "include_patterns": list(include_patterns),
        "exclude_patterns": list(exclude_patterns),
        "older_than_days": older_than_days,
        "name_regex": name_regex,
        "bundle_allowlist": list(bundle_allowlist),
        "bundle_blocklist": list(bundle_blocklist),
        "max_delete_mb": max_delete_mb,
        "max_items": max_items,
        "budget_summary": budget_summary,
        "by_category": rows_by_category(shown_rows, human_size=human_size),
        "skipped_by_category": rows_by_category(skipped, human_size=human_size),
        "skipped_count": len(skipped),
        "skipped_summary": skipped_summary(skipped, human_size=human_size),
        "skipped": skipped,
        "items": shown_rows,
    }


def clean_candidate_rows(
    *,
    targets: Sequence[ScanTarget],
    category_by_key: Mapping[str, CategoryScanDefaults],
    root: Path,
    include_patterns: Sequence[str],
    exclude_patterns: Sequence[str],
    older_than_days: float | None,
    min_size_mb: int,
    name_regex: str | None,
    bundle_allowlist: Sequence[str],
    bundle_blocklist: Sequence[str],
    review_selected_paths: set[str] | None,
    delete_mode: str,
    display_path: Callable[[Path | str], str],
    human_size: Callable[[int | None], str],
    path_interaction_metadata: Callable[[Path], dict[str, Any]],
    skipped_row: Callable[[str, Path, Path, str], dict[str, Any]],
    filter_reason: Callable[..., str | None],
    assert_safe_to_delete: Callable[[Path], None],
    bundle_id_for_path: Callable[[Path], str | None],
    progress_tick: Callable[[], None] | None = None,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    rows: list[dict[str, Any]] = []
    skipped: list[dict[str, Any]] = []
    for target in targets:
        category = category_by_key[target.category]
        min_size_bytes = max(effective_min_size_mb(category, min_size_mb), 0) * 1024 * 1024
        for entry in clean_candidate_entries(target):
            assert_safe_to_delete(entry)
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
                skipped.append(skipped_row(target.category, target.path, entry, reason))
                continue
            display_entry = display_path(entry)
            if review_selected_paths is not None and display_entry not in review_selected_paths:
                skipped_item = skipped_row(target.category, target.path, entry, "not-in-review-selection")
                default_selected = not category.requires_privilege
                skipped_item["review_evidence"] = {
                    "schema": "cleanmac.candidate-review-evidence.v1",
                    "matched_rule": f"clean.{target.category}.candidate",
                    "match_reason": target.category,
                    "confidence": "medium",
                    "risk": category.risk,
                    "risk_reason": category.description,
                    "risk_explanation": category.description,
                    "default_selected": default_selected,
                    "why_not_default": None
                    if default_selected
                    else "privileged category requires explicit review before execution",
                    "protected": False,
                    "delete_mode": delete_mode,
                    "recovery": "Execution is gated and Trash-first when this candidate is executable.",
                    "contains_user_data": category.full_disk_access or category.risk in {"high", "critical"},
                    "shared_container": target.category == "groupContainerCaches",
                    "recommended_next_action": "review-default-selection-before-trash-execution"
                    if default_selected
                    else "manual-review-required",
                }
                skipped.append(skipped_item)
                continue
            size = path_size_bytes(entry)
            if size < min_size_bytes:
                skipped.append(skipped_row(target.category, target.path, entry, "below-min-size"))
                continue
            default_selected = not category.requires_privilege
            rows.append(
                {
                    "category": target.category,
                    "parent": display_path(target.path),
                    "path": display_entry,
                    **path_interaction_metadata(entry),
                    "bytes": size,
                    "human": human_size(size),
                    "bundle_id": bundle_id_for_path(entry),
                    "delete_mode": delete_mode,
                    "trash_path": None,
                    "deleted": False,
                    "risk": category.risk,
                    "default_selected": default_selected,
                    "protected": False,
                    "review_evidence": {
                        "schema": "cleanmac.candidate-review-evidence.v1",
                        "matched_rule": f"clean.{target.category}.candidate",
                        "match_reason": target.category,
                        "confidence": "medium",
                        "risk": category.risk,
                        "risk_reason": category.description,
                        "risk_explanation": category.description,
                        "default_selected": default_selected,
                        "why_not_default": None
                        if default_selected
                        else "privileged category requires explicit review before execution",
                        "protected": False,
                        "delete_mode": delete_mode,
                        "recovery": "Execution is gated and Trash-first when this candidate is executable.",
                        "contains_user_data": category.full_disk_access or category.risk in {"high", "critical"},
                        "shared_container": target.category == "groupContainerCaches",
                        "recommended_next_action": "review-default-selection-before-trash-execution"
                        if default_selected
                        else "manual-review-required",
                    },
                }
            )
            if progress_tick is not None:
                progress_tick()
    return rows, skipped


__all__ = [
    "ScanTarget",
    "ScanBudget",
    "path_size_bytes",
    "child_entries",
    "inspect_entries",
    "candidate_entries",
    "clean_candidate_entries",
    "matches_exclude",
    "matches_include",
    "effective_include_patterns",
    "effective_exclude_patterns",
    "effective_older_than_days",
    "effective_min_size_mb",
    "matches_name_regex",
    "is_old_enough",
    "rows_by_category",
    "skipped_summary",
    "inspect_items",
    "clean_candidate_rows",
]
