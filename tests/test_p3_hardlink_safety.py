"""P3-02: duplicateFiles hardlink deletion safety validation tests."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pytest

from cleancli.core import CATEGORY_BY_KEY, clean, delete_policy_for_context
from cleancli.delete_ops import DeletePolicy, hardlink_replace


@dataclass
class _P3Sandbox:
    root: Path
    home: Path
    policy: DeletePolicy


@pytest.fixture
def p3_sandbox(tmp_path: Path) -> _P3Sandbox:
    root = tmp_path
    home = root / "Users" / "tester"
    home.mkdir(parents=True)
    (home / ".Trash").mkdir()
    policy = delete_policy_for_context(root=root, home=home)
    return _P3Sandbox(root=root, home=home, policy=policy)


def _make_dup_files(base_dir: Path, size_kb: int = 2048, count: int = 3) -> list[Path]:
    base_dir.mkdir(parents=True, exist_ok=True)
    content = b"x" * (size_kb * 1024)
    paths = []
    for i in range(count):
        p = base_dir / f"dup_{i}.bin"
        p.write_bytes(content)
        paths.append(p)
    return paths


def test_hardlink_replace_preserves_content(p3_sandbox: _P3Sandbox) -> None:
    src = p3_sandbox.root / "src.txt"
    dst = p3_sandbox.root / "dst.txt"
    src.write_text("preserved content")
    dst.write_text("old content")

    result = hardlink_replace(dst, policy=p3_sandbox.policy, target=src, dry_run=False)
    assert result is not None
    assert dst.read_text() == "preserved content"
    assert src.stat().st_ino == dst.stat().st_ino


def test_hardlink_replace_dry_run_preserves_original(p3_sandbox: _P3Sandbox) -> None:
    src = p3_sandbox.root / "src.txt"
    dst = p3_sandbox.root / "dst.txt"
    src.write_text("source content")
    dst.write_text("original content")
    original_ino = dst.stat().st_ino

    result = hardlink_replace(dst, policy=p3_sandbox.policy, target=src, dry_run=True)
    assert result is None
    assert dst.read_text() == "original content"
    assert dst.stat().st_ino == original_ino
    assert src.stat().st_ino != dst.stat().st_ino


def test_hardlink_replace_rejects_directory_target(p3_sandbox: _P3Sandbox) -> None:
    src = p3_sandbox.root / "src_dir"
    src.mkdir()
    dst = p3_sandbox.root / "dst.txt"
    dst.write_text("x")

    with pytest.raises(RuntimeError):
        hardlink_replace(dst, policy=p3_sandbox.policy, target=src, dry_run=False)


def test_hardlink_replace_rejects_directory_source(p3_sandbox: _P3Sandbox) -> None:
    src = p3_sandbox.root / "src.txt"
    src.write_text("x")
    dst = p3_sandbox.root / "dst_dir"
    dst.mkdir()

    with pytest.raises(RuntimeError):
        hardlink_replace(dst, policy=p3_sandbox.policy, target=src, dry_run=False)


def test_hardlink_replace_rejects_symlink_source(p3_sandbox: _P3Sandbox) -> None:
    src = p3_sandbox.root / "src.txt"
    src.write_text("x")
    dst_link = p3_sandbox.root / "dst_link"
    dst_link.symlink_to(src)

    with pytest.raises(RuntimeError):
        hardlink_replace(dst_link, policy=p3_sandbox.policy, target=src, dry_run=False)


def test_hardlink_replace_rejects_symlink_target(p3_sandbox: _P3Sandbox) -> None:
    src = p3_sandbox.root / "real.txt"
    src.write_text("x")
    target_link = p3_sandbox.root / "target_link"
    target_link.symlink_to(src)
    dst = p3_sandbox.root / "dst.txt"
    dst.write_text("x")

    with pytest.raises(RuntimeError):
        hardlink_replace(dst, policy=p3_sandbox.policy, target=target_link, dry_run=False)


def test_hardlink_replace_protected_path_rejected(p3_sandbox: _P3Sandbox) -> None:
    protected = p3_sandbox.root / "System" / "Library" / "CoreServices" / "file.txt"
    protected.parent.mkdir(parents=True)
    protected.write_text("system file")
    other = p3_sandbox.root / "other.txt"
    other.write_text("system file")

    with pytest.raises(RuntimeError):
        hardlink_replace(protected, policy=p3_sandbox.policy, target=other, dry_run=False)


def test_hardlink_replace_protected_target_rejected(p3_sandbox: _P3Sandbox) -> None:
    protected = p3_sandbox.root / "System" / "Library" / "file.txt"
    protected.parent.mkdir(parents=True)
    protected.write_text("system file")
    other = p3_sandbox.root / "other.txt"
    other.write_text("system file")

    with pytest.raises(RuntimeError):
        hardlink_replace(other, policy=p3_sandbox.policy, target=protected, dry_run=False)


def test_hardlink_replace_already_same_inode_is_skipped(p3_sandbox: _P3Sandbox) -> None:
    src = p3_sandbox.root / "src.txt"
    src.write_text("same inode")
    dst = p3_sandbox.root / "dst.txt"
    os.link(src, dst)
    assert src.stat().st_ino == dst.stat().st_ino

    log_entries: list[tuple[str, str, str]] = []

    def hook(status: str, path: Any, detail: str = "") -> None:
        log_entries.append((status, str(path), detail))

    result = hardlink_replace(dst, policy=p3_sandbox.policy, target=src, dry_run=False, operation_log=hook)
    assert result is not None
    assert src.stat().st_ino == dst.stat().st_ino
    assert any(e[0] == "skipped" for e in log_entries)


def test_hardlink_replace_empty_content_files(p3_sandbox: _P3Sandbox) -> None:
    src = p3_sandbox.root / "src_empty.txt"
    dst = p3_sandbox.root / "dst_empty.txt"
    src.write_text("")
    dst.write_text("")

    result = hardlink_replace(dst, policy=p3_sandbox.policy, target=src, dry_run=False)
    assert result is not None
    assert src.stat().st_ino == dst.stat().st_ino


def test_hardlink_replace_large_files(p3_sandbox: _P3Sandbox) -> None:
    src = p3_sandbox.root / "src_large.txt"
    dst = p3_sandbox.root / "dst_large.txt"
    content = "x" * 10240
    src.write_text(content)
    dst.write_text(content)

    result = hardlink_replace(dst, policy=p3_sandbox.policy, target=src, dry_run=False)
    assert result is not None
    assert src.stat().st_ino == dst.stat().st_ino
    assert dst.read_text() == content


def test_hardlink_replace_logs_operation(p3_sandbox: _P3Sandbox) -> None:
    src = p3_sandbox.root / "src.txt"
    dst = p3_sandbox.root / "dst.txt"
    src.write_text("hello")
    dst.write_text("hello")

    log_entries: list[tuple[str, str, str]] = []

    def hook(status: str, path: Any, detail: str = "") -> None:
        log_entries.append((status, str(path), detail))

    hardlink_replace(dst, policy=p3_sandbox.policy, target=src, dry_run=False, operation_log=hook)
    assert len(log_entries) == 1
    status, path, detail = log_entries[0]
    assert status == "hardlinked"
    assert str(dst) in path
    assert "target:" in detail


def test_hardlink_replace_dry_run_logs_operation(p3_sandbox: _P3Sandbox) -> None:
    src = p3_sandbox.root / "src.txt"
    dst = p3_sandbox.root / "dst.txt"
    src.write_text("hello")
    dst.write_text("hello")

    log_entries: list[tuple[str, str, str]] = []

    def hook(status: str, path: Any, detail: str = "") -> None:
        log_entries.append((status, str(path), detail))

    hardlink_replace(dst, policy=p3_sandbox.policy, target=src, dry_run=True, operation_log=hook)
    assert len(log_entries) == 1
    status, _path, detail = log_entries[0]
    assert status == "dry-run"
    assert "hardlink:" in detail


def test_cli_hardlink_mode_uses_trash_as_delete_mode(p3_sandbox: _P3Sandbox) -> None:
    logical_home = Path("/Users/tester")
    downloads = p3_sandbox.home / "Downloads" / "dup_test"
    _make_dup_files(downloads)

    report = clean(
        [CATEGORY_BY_KEY["duplicateFiles"]],
        root=p3_sandbox.root,
        home=logical_home,
        execute=True,
        risk_policy="default",
        delete_mode="hardlink",
        operation_log=str(p3_sandbox.root / "ops.jsonl"),
        command_argv=["clean", "--categories", "duplicateFiles", "--execute", "--delete-mode", "hardlink"],
    )
    dup_items = [item for item in report["items"] if item["category"] == "duplicateFiles"]
    hardlinked = [item for item in dup_items if item.get("status") == "hardlinked"]
    assert len(hardlinked) > 0


def test_cli_hardlink_mode_dry_run_no_changes(p3_sandbox: _P3Sandbox) -> None:
    logical_home = Path("/Users/tester")
    dup_dir = p3_sandbox.home / "Downloads" / "dup_test"
    files = _make_dup_files(dup_dir)
    inodes_before = [f.stat().st_ino for f in files]

    report = clean(
        [CATEGORY_BY_KEY["duplicateFiles"]],
        root=p3_sandbox.root,
        home=logical_home,
        execute=False,
        risk_policy="default",
        delete_mode="hardlink",
        operation_log=str(p3_sandbox.root / "ops.jsonl"),
        command_argv=["clean", "--categories", "duplicateFiles", "--delete-mode", "hardlink"],
    )
    dup_items = [item for item in report["items"] if item["category"] == "duplicateFiles"]
    assert len(dup_items) > 0

    inodes_after = [f.stat().st_ino for f in files]
    assert inodes_before == inodes_after


def test_hardlink_single_file_no_duplicate(p3_sandbox: _P3Sandbox) -> None:
    logical_home = Path("/Users/tester")
    dup_dir = p3_sandbox.home / "Downloads" / "single"
    dup_dir.mkdir(parents=True)
    (dup_dir / "only.bin").write_bytes(b"y" * (2 * 1024 * 1024))

    report = clean(
        [CATEGORY_BY_KEY["duplicateFiles"]],
        root=p3_sandbox.root,
        home=logical_home,
        execute=False,
        risk_policy="default",
        delete_mode="hardlink",
        operation_log=str(p3_sandbox.root / "ops.jsonl"),
        command_argv=["clean", "--categories", "duplicateFiles", "--delete-mode", "hardlink"],
    )
    dup_items = [item for item in report["items"] if item["category"] == "duplicateFiles"]
    assert len(dup_items) == 0
