from __future__ import annotations

import json
from pathlib import Path

from cleancli import logging_ops


def test_log_path_for_context_remaps_home_paths(tmp_path: Path) -> None:
    root = tmp_path / "root"
    home = Path("/Users/tester")

    path = logging_ops.log_path_for_context(
        "~/.cleanmac/deletions.log",
        root=root,
        home=home,
        remap_path=lambda pattern: str(root / "Users/tester/.cleanmac/deletions.log"),
    )

    assert path == (root / "Users/tester/.cleanmac/deletions.log").resolve(strict=False)


def test_rotate_log_once_replaces_previous_rotation(tmp_path: Path) -> None:
    log_path = tmp_path / "operations.jsonl"
    rotated = tmp_path / "operations.jsonl.1"
    log_path.write_text("x" * 32, encoding="utf-8")
    rotated.write_text("old", encoding="utf-8")
    removed: list[Path] = []

    did_rotate = logging_ops.rotate_log_once(
        log_path,
        max_bytes=16,
        remove_path=lambda path: (removed.append(path), path.unlink(missing_ok=True)),
    )

    assert did_rotate is True
    assert removed == [rotated]
    assert not log_path.exists()
    assert rotated.read_text(encoding="utf-8") == "x" * 32


def test_append_deletion_log_writes_tab_separated_rows(tmp_path: Path) -> None:
    root = tmp_path / "root"
    home = Path("/Users/tester")

    log_path = logging_ops.append_deletion_log(
        root=root,
        home=home,
        delete_log_file="~/.cleanmac/deletions.log",
        remap_path=lambda pattern: str(root / "Users/tester/.cleanmac/deletions.log"),
        display_path=str,
        mode="trash",
        status="deleted",
        path="/tmp/file",
        bytes_value=12,
        detail="detail\twith-tab",
    )

    content = Path(log_path).read_text(encoding="utf-8")
    assert "\ttrash\t12\tdeleted\t/tmp/file\tdetail with-tab\n" in content


def test_preflight_operation_log_rejects_symlinked_directory(tmp_path: Path) -> None:
    root = tmp_path / "root"
    log_parent = tmp_path / "logs-link"
    target_parent = tmp_path / "logs-real"
    target_parent.mkdir()
    log_parent.symlink_to(target_parent, target_is_directory=True)

    report = logging_ops.preflight_operation_log(
        str(log_parent / "operations.jsonl"),
        root=root,
        home=Path("/Users/tester"),
        remap_path=lambda pattern: pattern,
        display_path=str,
        rotate_bytes=1024,
        remove_path=lambda path: path.unlink(missing_ok=True),
    )

    assert report["schema"] == "cleanmac.operation-log-status.v1"
    assert report["status"] == "failed"
    assert "symlinked operation log directory" in report["error"]


def test_append_operation_log_writes_jsonl_with_enrichment(tmp_path: Path) -> None:
    log_path = tmp_path / "operations.jsonl"

    result = logging_ops.append_operation_log(
        str(log_path),
        [{"schema": "example", "path": "/tmp/file"}],
        root=tmp_path,
        home=Path("/Users/tester"),
        remap_path=lambda pattern: pattern,
        display_path=str,
        rotate_bytes=1024,
        remove_path=lambda path: path.unlink(missing_ok=True),
        ensure_entry=lambda entry: {**entry, "enriched": True},
    )

    assert result == str(log_path)
    rows = [json.loads(line) for line in log_path.read_text(encoding="utf-8").splitlines()]
    assert rows == [{"schema": "example", "path": "/tmp/file", "enriched": True}]
