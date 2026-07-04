from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pytest

from cleancli import scan


@dataclass(frozen=True)
class ScanDefaults:
    key: str = "cache"
    description: str = "Cache files"
    risk: str = "low"
    requires_privilege: bool = False
    full_disk_access: bool = False
    default_include_patterns: tuple[str, ...] = ()
    default_exclude_patterns: tuple[str, ...] = ("*.keep",)
    default_older_than_days: float | None = 7
    default_min_size_mb: int = 2


def test_path_size_bytes_counts_directory_without_following_symlinks(tmp_path: Path) -> None:
    root = tmp_path / "cache"
    root.mkdir()
    (root / "a.bin").write_text("a" * 10, encoding="utf-8")
    outside = tmp_path / "outside.bin"
    outside.write_text("x" * 1000, encoding="utf-8")
    link = root / "outside-link"
    try:
        link.symlink_to(outside)
    except OSError:
        pytest.skip("symlinks are not available")

    size = scan.path_size_bytes(root)

    assert size >= 10
    assert size < 1000


def test_candidate_entries_respects_delete_target_semantics(tmp_path: Path) -> None:
    target_path = tmp_path / "node_modules"
    target_path.mkdir()
    (target_path / "package.json").write_text("{}", encoding="utf-8")
    target = scan.ScanTarget(
        category="projectArtifacts",
        source_pattern="node_modules",
        path=target_path,
        matched=True,
        from_glob=False,
        delete_target=True,
    )

    assert scan.candidate_entries(target, recursive=True) == [(target_path, 0)]
    assert scan.clean_candidate_entries(target) == [target_path]


def test_inspect_entries_reports_recursive_depth(tmp_path: Path) -> None:
    root = tmp_path / "cache"
    nested = root / "a" / "b"
    nested.mkdir(parents=True)
    (nested / "cache.bin").write_text("data", encoding="utf-8")

    entries = scan.inspect_entries(root, recursive=True)
    by_name = {path.name: depth for path, depth in entries}

    assert by_name["a"] == 1
    assert by_name["b"] == 2
    assert by_name["cache.bin"] == 3


def test_effective_scan_defaults_and_patterns() -> None:
    defaults = ScanDefaults(default_include_patterns=("*.log",))

    assert scan.effective_include_patterns(defaults, ()) == ("*.log",)
    assert scan.effective_include_patterns(defaults, ("*.tmp",)) == ("*.tmp",)
    assert scan.effective_exclude_patterns(defaults, ("*.bak",)) == ("*.bak", "*.keep")
    assert scan.effective_older_than_days(defaults, None) == 7
    assert scan.effective_older_than_days(defaults, 1) == 1
    assert scan.effective_min_size_mb(defaults, 0) == 2
    assert scan.effective_min_size_mb(defaults, 9) == 9


def test_invalid_name_regex_raises_value_error(tmp_path: Path) -> None:
    path = tmp_path / "cache.bin"
    path.write_text("data", encoding="utf-8")

    with pytest.raises(ValueError, match="Invalid --name-regex"):
        scan.matches_name_regex(path, "[")


def test_scan_budget_summary_reports_limits() -> None:
    summary = scan.ScanBudget(max_delete_mb=1, max_items=2).summary(
        candidate_count=3,
        candidate_bytes=2 * 1024 * 1024,
        human_size=lambda size: f"{size} B",
    )

    assert summary["candidate_count"] == 3
    assert summary["candidate_bytes"] == 2 * 1024 * 1024
    assert summary["max_delete_bytes"] == 1024 * 1024
    assert summary["within_max_items"] is False
    assert summary["within_max_delete_budget"] is False
    assert summary["applies_to_execute"] is False


def test_row_aggregation_groups_by_category_file_type_and_parent() -> None:
    rows = [
        {"category": "downloads", "path": "/tmp/a.log", "parent": "/tmp", "bytes": 10},
        {"category": "downloads", "path": "/tmp/b.LOG", "parent": "/tmp", "bytes": 20},
        {"category": "trash", "path": "/trash/noext", "parent": "/trash", "bytes": 5},
    ]
    human = lambda size: f"{size} B"

    by_category = scan.rows_by_category(rows, human_size=human)
    by_type = scan.rows_by_file_type(rows, human_size=human)
    by_parent = scan.rows_by_parent_directory(rows, human_size=human)

    assert by_category["downloads"] == {"count": 2, "bytes": 30, "human": "30 B"}
    assert by_category["trash"] == {"count": 1, "bytes": 5, "human": "5 B"}
    assert by_type["log"] == {"count": 2, "bytes": 30, "human": "30 B"}
    assert by_type["(no extension)"] == {"count": 1, "bytes": 5, "human": "5 B"}
    assert by_parent["/tmp"] == {"count": 2, "bytes": 30, "human": "30 B"}
    assert by_parent["/trash"] == {"count": 1, "bytes": 5, "human": "5 B"}


def test_path_interaction_metadata_builds_open_and_reveal_commands(tmp_path: Path) -> None:
    path = tmp_path / "cache file.log"
    path.write_text("data", encoding="utf-8")

    metadata = scan.path_interaction_metadata(
        path,
        display_path=str,
        shell_quote_command=lambda argv: " ".join(argv),
    )

    assert metadata["finder_url"].startswith("file://")
    assert metadata["open_command"] == ["open", str(path)]
    assert metadata["reveal_command"] == ["open", "-R", str(path)]
    assert metadata["open_command_text"] == f"open {path}"
    assert metadata["safe_to_open"] is True
    assert metadata["open_supported"] is True


def test_skipped_row_includes_interaction_metadata_and_size(tmp_path: Path) -> None:
    parent = tmp_path / "cache"
    parent.mkdir()
    entry = parent / "skip.tmp"
    entry.write_text("skip", encoding="utf-8")

    row = scan.skipped_row(
        "cache",
        parent,
        entry,
        "excluded",
        display_path=str,
        shell_quote_command=lambda argv: " ".join(argv),
        human_size=lambda size: f"{size} B",
    )

    assert row["category"] == "cache"
    assert row["parent"] == str(parent)
    assert row["path"] == str(entry)
    assert row["reason"] == "excluded"
    assert row["bytes"] == 4
    assert row["human"] == "4 B"
    assert row["reveal_command"] == ["open", "-R", str(entry)]


def test_scan_inspect_items_builds_read_only_report(tmp_path: Path) -> None:
    root = tmp_path / "cache"
    root.mkdir()
    (root / "keep.log").write_text("x" * 10, encoding="utf-8")
    (root / "skip.keep").write_text("x" * 10, encoding="utf-8")
    category = ScanDefaults(
        default_include_patterns=(),
        default_exclude_patterns=("*.keep",),
        default_older_than_days=None,
        default_min_size_mb=0,
    )
    target = scan.ScanTarget(
        category="cache",
        source_pattern=str(root),
        path=root,
        matched=True,
        from_glob=False,
    )

    report = scan.inspect_items(
        [category],
        targets=[target],
        category_by_key={"cache": category},
        root=tmp_path,
        limit=10,
        display_path=str,
        human_size=lambda size: f"{size} B",
        path_interaction_metadata=lambda path: {"safe_to_open": True},
        skipped_row=lambda cat, parent, entry, reason: {
            "category": cat,
            "parent": str(parent),
            "path": str(entry),
            "reason": reason,
            "bytes": scan.path_size_bytes(entry),
        },
        filter_reason=lambda category, path, **kwargs: "excluded"
        if scan.matches_exclude(path, category.default_exclude_patterns)
        else None,
        render_ai_summary=lambda categories, **kwargs: {"schema": "test.ai-summary", **kwargs},
    )

    assert report["schema"] == "cleanmac.inspect.v1"
    assert report["destructive"] is False
    assert report["dry_run"] is True
    assert report["total_candidates"] == 1
    assert report["items"][0]["path"].endswith("keep.log")
    assert report["items"][0]["review_evidence"]["schema"] == "cleanmac.candidate-review-evidence.v1"
    assert report["skipped_count"] == 1
    assert report["skipped"][0]["reason"] == "excluded"
    assert report["budget_summary"]["candidate_count"] == 1


def test_clean_candidate_rows_applies_filters_and_review_selection(tmp_path: Path) -> None:
    root = tmp_path / "cache"
    root.mkdir()
    selected = root / "selected.log"
    excluded = root / "excluded.keep"
    unselected = root / "unselected.log"
    selected.write_text("x" * 10, encoding="utf-8")
    excluded.write_text("x" * 10, encoding="utf-8")
    unselected.write_text("x" * 10, encoding="utf-8")
    category = ScanDefaults(
        default_include_patterns=(),
        default_exclude_patterns=("*.keep",),
        default_older_than_days=None,
        default_min_size_mb=0,
    )
    target = scan.ScanTarget(
        category="cache",
        source_pattern=str(root),
        path=root,
        matched=True,
        from_glob=False,
    )
    ticks = 0

    def tick() -> None:
        nonlocal ticks
        ticks += 1

    rows, skipped = scan.clean_candidate_rows(
        targets=[target],
        category_by_key={"cache": category},
        root=tmp_path,
        include_patterns=(),
        exclude_patterns=(),
        older_than_days=None,
        min_size_mb=0,
        name_regex=None,
        bundle_allowlist=(),
        bundle_blocklist=(),
        review_selected_paths={str(selected)},
        delete_mode="trash",
        display_path=str,
        human_size=lambda size: f"{size} B",
        path_interaction_metadata=lambda path: {"safe_to_open": True},
        skipped_row=lambda cat, parent, entry, reason: {
            "category": cat,
            "parent": str(parent),
            "path": str(entry),
            "reason": reason,
            "bytes": scan.path_size_bytes(entry),
            "human": f"{scan.path_size_bytes(entry)} B",
        },
        filter_reason=lambda category, path, **kwargs: "excluded"
        if scan.matches_exclude(path, category.default_exclude_patterns)
        else None,
        assert_safe_to_delete=lambda path: None,
        bundle_id_for_path=lambda path: "com.example.cache",
        progress_tick=tick,
    )

    assert [row["path"] for row in rows] == [str(selected)]
    assert rows[0]["delete_mode"] == "trash"
    assert rows[0]["bundle_id"] == "com.example.cache"
    assert rows[0]["review_evidence"]["delete_mode"] == "trash"
    assert {row["reason"] for row in skipped} == {"excluded", "not-in-review-selection"}
    review_skips = [row for row in skipped if row["reason"] == "not-in-review-selection"]
    assert review_skips[0]["review_evidence"]["schema"] == "cleanmac.candidate-review-evidence.v1"
    assert ticks == 1
