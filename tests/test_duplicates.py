from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from cleancli import duplicates


@dataclass(frozen=True)
class DuplicateCategory:
    description: str = "Duplicate files"
    risk: str = "high"


def _human_size(size: int | None) -> str:
    return f"{size} B"


def test_find_duplicate_files_groups_by_content_hash(tmp_path: Path) -> None:
    root = tmp_path / "Downloads"
    root.mkdir()
    (root / "a.bin").write_bytes(b"x" * 1024)
    (root / "b.bin").write_bytes(b"x" * 1024)
    (root / "c.bin").write_bytes(b"y" * 1024)

    report = duplicates.find_duplicate_files(
        [root],
        root=tmp_path,
        home=tmp_path,
        min_size_mb=0,
        remap_path=lambda pattern: pattern,
        display_path=str,
        human_size=_human_size,
    )

    assert report["schema"] == "cleanmac.duplicate-files.v1"
    assert report["total_groups"] == 1
    assert report["total_duplicate_files"] == 1
    assert report["groups"][0]["file_count"] == 2
    assert {Path(row["path"]).name for row in report["groups"][0]["files"]} == {"a.bin", "b.bin"}


def test_duplicate_candidate_rows_preserve_review_evidence(tmp_path: Path) -> None:
    root = tmp_path / "Downloads"
    root.mkdir()
    duplicate = root / "b.bin"
    duplicate.write_bytes(b"x" * 1024)
    dup_candidates = {
        str(duplicate): {
            "duplicate_group_hash": "hash",
            "duplicate_group_size": 1024,
            "duplicate_group_file_count": 2,
            "duplicate_keep_path": str(root / "a.bin"),
        }
    }

    rows = duplicates.duplicate_candidate_rows(
        dup_candidates=dup_candidates,
        category=DuplicateCategory(),
        root=tmp_path,
        include_patterns=(),
        exclude_patterns=(),
        older_than_days=None,
        name_regex=None,
        bundle_allowlist=(),
        bundle_blocklist=(),
        review_selected_paths={str(duplicate)},
        delete_mode="hardlink",
        display_path=str,
        human_size=_human_size,
        path_interaction_metadata=lambda path: {"safe_to_open": True},
        filter_reason=lambda category, path, **kwargs: None,
        assert_safe_to_delete=lambda path: None,
        bundle_id_for_path=lambda path: None,
    )

    assert len(rows) == 1
    row = rows[0]
    assert row["category"] == "duplicateFiles"
    assert row["delete_mode"] == "hardlink"
    assert row["duplicate_group_hash"] == "hash"
    assert row["duplicate_keep_path"].endswith("a.bin")
    assert row["review_evidence"]["schema"] == "cleanmac.candidate-review-evidence.v1"
    assert row["review_evidence"]["match_reason"] == "duplicate-content-hash"
    assert row["review_evidence"]["delete_mode"] == "hardlink"


def test_duplicate_candidate_rows_respect_review_selection(tmp_path: Path) -> None:
    duplicate = tmp_path / "b.bin"
    duplicate.write_bytes(b"x" * 1024)
    dup_candidates = {
        str(duplicate): {
            "duplicate_group_hash": "hash",
            "duplicate_group_size": 1024,
            "duplicate_group_file_count": 2,
            "duplicate_keep_path": str(tmp_path / "a.bin"),
        }
    }

    rows = duplicates.duplicate_candidate_rows(
        dup_candidates=dup_candidates,
        category=DuplicateCategory(),
        root=tmp_path,
        include_patterns=(),
        exclude_patterns=(),
        older_than_days=None,
        name_regex=None,
        bundle_allowlist=(),
        bundle_blocklist=(),
        review_selected_paths={str(tmp_path / "other.bin")},
        delete_mode="trash",
        display_path=str,
        human_size=_human_size,
        path_interaction_metadata=lambda path: {},
        filter_reason=lambda category, path, **kwargs: None,
        assert_safe_to_delete=lambda path: None,
        bundle_id_for_path=lambda path: None,
    )

    assert rows == []
