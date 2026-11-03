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

    def remove_rotated(path: Path) -> None:
        removed.append(path)
        path.unlink(missing_ok=True)

    did_rotate = logging_ops.rotate_log_once(
        log_path,
        max_bytes=16,
        remove_path=remove_rotated,
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


def _preflight(log_file: Path, tmp_path: Path) -> dict[str, object]:
    from cleancli import protection

    return logging_ops.preflight_operation_log(
        str(log_file),
        root=tmp_path / "root",
        home=Path("/Users/tester"),
        remap_path=lambda pattern: pattern,
        display_path=str,
        rotate_bytes=1024,
        remove_path=lambda path: path.unlink(missing_ok=True),
        protected_path=protection.should_protect_path,
    )


def test_preflight_operation_log_allows_benign_symlinked_directory(tmp_path: Path) -> None:
    # Mirrors macOS convenience links such as /tmp -> /private/tmp.
    log_parent = tmp_path / "logs-link"
    target_parent = tmp_path / "logs-real"
    target_parent.mkdir()
    log_parent.symlink_to(target_parent, target_is_directory=True)
    log_file = log_parent / "operations.jsonl"

    report = _preflight(log_file, tmp_path)

    assert report["schema"] == "cleanmac.operation-log-status.v1"
    assert report["status"] == "ready"
    assert report["error"] is None
    assert log_file.is_file()


def test_preflight_operation_log_rejects_symlinked_directory_to_protected_target(
    tmp_path: Path,
) -> None:
    # /etc exists on both Linux and macOS (where it resolves to /private/etc).
    log_parent = tmp_path / "logs-link"
    log_parent.symlink_to(Path("/etc"), target_is_directory=True)

    report = _preflight(log_parent / "operations.jsonl", tmp_path)

    assert report["status"] == "failed"
    assert "protected path" in str(report["error"])
    assert not (Path("/etc") / "operations.jsonl").exists()


def test_preflight_operation_log_rejects_protected_directory(tmp_path: Path) -> None:
    report = _preflight(Path("/etc") / "cleanmac-operations.jsonl", tmp_path)

    assert report["status"] == "failed"
    assert "protected path" in str(report["error"])
    assert not (Path("/etc") / "cleanmac-operations.jsonl").exists()


def test_preflight_operation_log_rejects_dangling_symlinked_directory(tmp_path: Path) -> None:
    log_parent = tmp_path / "logs-link"
    log_parent.symlink_to(tmp_path / "missing", target_is_directory=True)

    report = _preflight(log_parent / "operations.jsonl", tmp_path)

    assert report["status"] == "failed"
    assert "existing directory target" in str(report["error"])


def test_preflight_operation_log_allows_benign_symlinked_file(tmp_path: Path) -> None:
    real_log = tmp_path / "real" / "operations.jsonl"
    real_log.parent.mkdir()
    real_log.write_text("seed\n", encoding="utf-8")
    log_file = tmp_path / "operations-link.jsonl"
    log_file.symlink_to(real_log)

    report = _preflight(log_file, tmp_path)

    assert report["status"] == "ready"
    assert real_log.read_text(encoding="utf-8") == "seed\n"


def test_preflight_operation_log_rejects_symlinked_file_to_protected_target(
    tmp_path: Path,
) -> None:
    log_file = tmp_path / "operations-link.jsonl"
    log_file.symlink_to(Path("/etc") / "cleanmac-operation-log-target.jsonl")

    report = _preflight(log_file, tmp_path)

    assert report["status"] == "failed"
    assert "protected path" in str(report["error"])


def test_preflight_operation_log_rejects_symlinked_file_pointing_at_directory(
    tmp_path: Path,
) -> None:
    target_dir = tmp_path / "a-directory"
    target_dir.mkdir()
    log_file = tmp_path / "operations-link.jsonl"
    log_file.symlink_to(target_dir, target_is_directory=True)

    report = _preflight(log_file, tmp_path)

    assert report["status"] == "failed"
    assert "directory as operation log file" in str(report["error"])


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
