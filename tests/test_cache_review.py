from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from cleancli import core, review, scan


def make_cache(root: Path, relative: str, data: bytes = b"cache") -> Path:
    path = root / "Users/tester" / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    return path


def test_running_cache_is_visible_but_cannot_be_selected(tmp_path: Path) -> None:
    make_cache(tmp_path, "Library/Caches/Microsoft Edge/cache.bin")
    with (
        patch.object(core, "run_text_command", return_value="Microsoft Edge"),
        patch.object(core, "is_test_no_auth", return_value=False),
    ):
        inspected = core.inspect_items(
            [core.CATEGORY_BY_KEY["userCache"]], root=tmp_path, home=Path("/Users/tester"), limit=-1
        )
    report = review.render_review(inspected)
    assert report["item_count"] == 1
    item = report["items"][0]
    assert item["protected"] is True
    assert item["locked"] is True
    assert item["selectable"] is False
    assert item["default_selected"] is False
    assert item["reason"] == "app-running"
    assert item["application"] == "Microsoft Edge"
    assert report["selection_summary"]["selected_bytes"] == 0
    assert report["selection_summary"]["protected_bytes"] == 5
    assert report["selection_summary"]["discovered_bytes"] == 5
    selection = dict(report["selection"])
    selection["selected_item_ids"] = [item["id"]]
    selection["excluded_item_ids"] = []
    assert review.validate_review_selection(inspected, selection)["blocked_reasons"] == ["protected-item-selected"]


def test_review_enforces_locked_and_nonselectable_source_items() -> None:
    payload = {
        "schema": "cleanmac.inspect.v1",
        "items": [
            {"path": "/tmp/locked", "locked": True, "protected": False, "default_selected": True},
            {"path": "/tmp/nonselectable", "selectable": False, "protected": False, "default_selected": True},
        ],
    }
    report = review.render_review(payload)
    assert report["selection"]["selected_item_ids"] == []
    assert all(item["protected"] and item["locked"] and not item["selectable"] for item in report["items"])
    selection = dict(report["selection"])
    selection["selected_item_ids"] = [item["id"] for item in report["items"]]
    selection["excluded_item_ids"] = []
    assert review.validate_review_selection(payload, selection)["blocked_reasons"] == ["protected-item-selected"]


def test_plan_keeps_locked_cache_review_evidence(tmp_path: Path) -> None:
    make_cache(tmp_path, "Library/Caches/Microsoft Edge/cache.bin")
    with (
        patch.object(core, "run_text_command", return_value="Microsoft Edge"),
        patch.object(core, "is_test_no_auth", return_value=False),
    ):
        plan = core.render_clean_plan(
            [core.CATEGORY_BY_KEY["userCache"]],
            root=tmp_path,
            home=Path("/Users/tester"),
            risk_policy="default",
            max_delete_mb=None,
        )
    report = review.render_review(plan)
    assert report["item_count"] == 1
    assert report["items"][0]["locked"] is True
    assert report["items"][0]["review_evidence"]["why_not_default"] == "app-running"
    assert plan["estimated_reclaimable_bytes"] == 0


def test_merging_skips_preserves_existing_candidate_ids() -> None:
    payload = {"schema": "cleanmac.inspect.v1", "items": [{"path": "/tmp/cache", "bytes": 5, "risk": "low"}]}
    original_id = review.render_review(payload)["items"][0]["id"]
    payload["skipped"] = [{"path": "/tmp/active", "reason": "app-running", "bytes": 9}]
    report = review.render_review(payload)
    assert report["items"][0]["id"] == original_id
    assert report["item_count"] == 2
    assert report["selection_summary"]["selectable_bytes"] == 5
    assert report["selection_summary"]["protected_bytes"] == 9
    assert report["selection_summary"]["discovered_bytes"] == 14


def test_overlapping_categories_have_disjoint_candidates_and_exact_budgets(tmp_path: Path) -> None:
    cache = make_cache(tmp_path, "Library/Caches/Microsoft Edge/cache.bin")
    make_cache(tmp_path, "Library/Caches/Microsoft Edge/other/file.bin", b"abc")
    categories = [core.CATEGORY_BY_KEY[key] for key in ("userCache", "edge")]
    inspected = core.inspect_items(categories, root=tmp_path, home=Path("/Users/tester"), limit=-1)
    assert inspected["total_bytes"] == 8
    assert inspected["total_candidates"] == 2
    paths = [Path(row["path"]).resolve() for row in inspected["items"]]
    assert len(paths) == len(set(paths))
    assert not any(a in b.parents for a in paths for b in paths if a != b)
    result = core.clean(
        categories,
        root=tmp_path,
        home=Path("/Users/tester"),
        execute=True,
        delete_mode="trash",
        operation_log=None,
        max_items=2,
        max_delete_mb=8 / (1024 * 1024),
    )
    assert result["total_bytes"] == 8
    assert result["deleted_count"] == 2
    assert result["failed_count"] == 0
    assert not cache.exists()


def test_overlapping_category_accounting_is_independent_of_selection_order(tmp_path: Path) -> None:
    make_cache(tmp_path, "Library/Caches/Microsoft Edge/cache.bin")
    totals = []
    for keys in (("edge", "userCache"), ("userCache", "edge")):
        report = core.inspect_items(
            [core.CATEGORY_BY_KEY[key] for key in keys], root=tmp_path, home=Path("/Users/tester"), limit=-1
        )
        totals.append((report["total_bytes"], [(row["category"], row["path"]) for row in report["items"]]))
    assert totals[0] == totals[1]
    assert totals[0][0] == 5


def test_locked_items_are_not_duplicated_by_overlapping_categories(tmp_path: Path) -> None:
    make_cache(tmp_path, "Library/Caches/Microsoft Edge/cache.bin")
    with (
        patch.object(core, "run_text_command", return_value="Microsoft Edge"),
        patch.object(core, "is_test_no_auth", return_value=False),
    ):
        inspected = core.inspect_items(
            [core.CATEGORY_BY_KEY[key] for key in ("userCache", "edge")],
            root=tmp_path,
            home=Path("/Users/tester"),
            limit=-1,
        )
    report = review.render_review(inspected)
    assert report["item_count"] == 1
    assert report["selection_summary"]["protected_bytes"] == 5
    assert report["selection_summary"]["discovered_bytes"] == 5


def test_accounting_counts_a_late_activity_skip_once() -> None:
    row = {"path": "/tmp/cache", "bytes": 5, "protected": True, "default_selected": False}
    summary = scan.selection_accounting([row], [{**row, "reason": "app-running"}])
    assert summary["discovered_count"] == 1
    assert summary["discovered_bytes"] == 5
    assert summary["protected_count"] == 1
    assert summary["protected_bytes"] == 5
    assert summary["selectable_count"] == 0
    assert summary["selected_count"] == 0


def test_accounting_distinguishes_selection_exclusion_from_protection() -> None:
    selected = {"path": "/tmp/selected-cache", "bytes": 5, "default_selected": True, "protected": False}
    excluded = {
        "path": "/tmp/excluded-cache",
        "bytes": 3,
        "default_selected": False,
        "protected": False,
        "reason": "not-in-review-selection",
    }
    summary = scan.selection_accounting([selected], [excluded])
    assert summary["discovered_bytes"] == 8
    assert summary["protected_bytes"] == 0
    assert summary["selectable_bytes"] == 8
    assert summary["selected_bytes"] == 5


def test_analysis_counts_overlapping_cache_scopes_once(tmp_path: Path) -> None:
    make_cache(tmp_path, "Library/Caches/Microsoft Edge/cache.bin")
    report = core.analyze(
        [core.CATEGORY_BY_KEY[key] for key in ("userCache", "edge")], root=tmp_path, home=Path("/Users/tester")
    )
    assert report["total_bytes"] == 5
    assert sum(row["bytes"] for row in report["categories"]) == 5


def test_recursive_inspect_uses_consistent_unique_space_totals(tmp_path: Path) -> None:
    make_cache(tmp_path, "Library/Caches/Acme/nested/file.bin")
    inspected = core.inspect_items(
        [core.CATEGORY_BY_KEY["userCache"]], root=tmp_path, home=Path("/Users/tester"), limit=-1, recursive=True
    )
    assert len(inspected["items"]) == 3
    assert inspected["total_bytes"] == 5
    assert inspected["by_category"]["userCache"]["bytes"] == 5
    assert sum(row["bytes"] for row in scan.rows_by_file_type(inspected["items"], human_size=str).values()) == 5
    assert sum(row["bytes"] for row in scan.rows_by_parent_directory(inspected["items"], human_size=str).values()) == 5
    summary = review.render_review(inspected)["selection_summary"]
    assert summary["discovered_bytes"] == summary["selectable_bytes"] == summary["selected_bytes"] == 5


def test_separate_cache_symlinks_keep_separate_accounting_identities(tmp_path: Path) -> None:
    cache = tmp_path / "Users/tester/Library/Caches"
    cache.mkdir(parents=True)
    target = tmp_path / "safe-target"
    target.mkdir()
    (cache / "a").symlink_to(target, target_is_directory=True)
    (cache / "b").symlink_to(target, target_is_directory=True)
    inspected = core.inspect_items(
        [core.CATEGORY_BY_KEY["userCache"]], root=tmp_path, home=Path("/Users/tester"), limit=-1
    )
    summary = inspected["selection_accounting"]
    assert summary["selectable_count"] == inspected["total_candidates"] == 2
    assert summary["selected_bytes"] == summary["discovered_bytes"] == inspected["total_bytes"]
    assert review.render_review(inspected)["selection_summary"]["selected_bytes"] == inspected["total_bytes"]
