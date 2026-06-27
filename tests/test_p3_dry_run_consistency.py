"""P3-07: Dry-run vs execute result consistency tests."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pytest

from cleancli.core import CATEGORY_BY_KEY, clean, delete_policy_for_context
from cleancli.delete_ops import DeletePolicy


@dataclass
class _P3Sandbox:
    root: Path
    home: Path
    policy: DeletePolicy
    trash_root: Path


LOGICAL_HOME = Path("/Users/tester")


@pytest.fixture
def p3_sandbox(tmp_path: Path) -> _P3Sandbox:
    root = tmp_path
    home = LOGICAL_HOME
    trash_root = root / "Users/tester/.Trash"
    trash_root.mkdir(parents=True)
    (root / "Users/tester/Library/Caches").mkdir(parents=True)
    policy = delete_policy_for_context(root=root, home=home)
    return _P3Sandbox(root=root, home=home, policy=policy, trash_root=trash_root)


def _make_trash_files(root: Path, count: int = 5) -> list[Path]:
    user_trash = root / "Users/tester/.Trash"
    user_trash.mkdir(parents=True, exist_ok=True)
    paths = []
    for i in range(count):
        p = user_trash / f"file_{i}.tmp"
        p.write_text(f"trash content {i}")
        paths.append(p)
    return paths


def _make_cache_files(root: Path, count: int = 5) -> list[Path]:
    cache_dir = root / "Users/tester/Library/Caches/com.example.test"
    cache_dir.mkdir(parents=True, exist_ok=True)
    paths = []
    for i in range(count):
        p = cache_dir / f"cache_{i}.dat"
        p.write_text(f"cache data {i}" * 100)
        paths.append(p)
    return paths


class TestDryRunVsExecuteConsistency:
    def test_trash_category_same_item_count(self, p3_sandbox: _P3Sandbox) -> None:
        _make_trash_files(p3_sandbox.root, 5)

        dry_report = clean(
            [CATEGORY_BY_KEY["trash"]],
            root=p3_sandbox.root,
            home=p3_sandbox.home,
            execute=False,
            operation_log=str(p3_sandbox.root / "dry_ops.jsonl"),
            command_argv=["clean", "--categories", "trash"],
        )
        dry_trash_items = [i for i in dry_report["items"] if i["category"] == "trash"]

        exec_report = clean(
            [CATEGORY_BY_KEY["trash"]],
            root=p3_sandbox.root,
            home=p3_sandbox.home,
            execute=True,
            operation_log=str(p3_sandbox.root / "exec_ops.jsonl"),
            command_argv=["clean", "--categories", "trash", "--execute"],
        )
        exec_trash_items = [i for i in exec_report["items"] if i["category"] == "trash"]

        assert len(dry_trash_items) == len(exec_trash_items)

    def test_trash_category_same_paths(self, p3_sandbox: _P3Sandbox) -> None:
        _make_trash_files(p3_sandbox.root, 3)

        dry_report = clean(
            [CATEGORY_BY_KEY["trash"]],
            root=p3_sandbox.root,
            home=p3_sandbox.home,
            execute=False,
            operation_log=str(p3_sandbox.root / "dry_ops.jsonl"),
            command_argv=["clean", "--categories", "trash"],
        )
        dry_paths = sorted(i["path"] for i in dry_report["items"] if i["category"] == "trash")

        exec_report = clean(
            [CATEGORY_BY_KEY["trash"]],
            root=p3_sandbox.root,
            home=p3_sandbox.home,
            execute=True,
            operation_log=str(p3_sandbox.root / "exec_ops.jsonl"),
            command_argv=["clean", "--categories", "trash", "--execute"],
        )
        exec_paths = sorted(i["path"] for i in exec_report["items"] if i["category"] == "trash")

        assert dry_paths == exec_paths

    def test_dry_run_preserves_files(self, p3_sandbox: _P3Sandbox) -> None:
        paths = _make_trash_files(p3_sandbox.root, 4)
        before = [p.exists() for p in paths]

        clean(
            [CATEGORY_BY_KEY["trash"]],
            root=p3_sandbox.root,
            home=p3_sandbox.home,
            execute=False,
            operation_log=str(p3_sandbox.root / "ops.jsonl"),
            command_argv=["clean", "--categories", "trash"],
        )

        after = [p.exists() for p in paths]
        assert before == after
        assert all(after)

    def test_execute_removes_files(self, p3_sandbox: _P3Sandbox) -> None:
        paths = _make_trash_files(p3_sandbox.root, 4)
        before = [p.exists() for p in paths]
        assert all(before)

        clean(
            [CATEGORY_BY_KEY["trash"]],
            root=p3_sandbox.root,
            home=p3_sandbox.home,
            execute=True,
            operation_log=str(p3_sandbox.root / "ops.jsonl"),
            command_argv=["clean", "--categories", "trash", "--execute"],
        )

        after = [p.exists() for p in paths]
        assert not any(after)

    def test_dry_run_bytes_matches_execute_bytes(self, p3_sandbox: _P3Sandbox) -> None:
        _make_trash_files(p3_sandbox.root, 3)

        dry_report = clean(
            [CATEGORY_BY_KEY["trash"]],
            root=p3_sandbox.root,
            home=p3_sandbox.home,
            execute=False,
            operation_log=str(p3_sandbox.root / "dry_ops.jsonl"),
            command_argv=["clean", "--categories", "trash"],
        )
        dry_bytes = sum(i.get("bytes", 0) for i in dry_report["items"] if i["category"] == "trash")

        exec_report = clean(
            [CATEGORY_BY_KEY["trash"]],
            root=p3_sandbox.root,
            home=p3_sandbox.home,
            execute=True,
            operation_log=str(p3_sandbox.root / "exec_ops.jsonl"),
            command_argv=["clean", "--categories", "trash", "--execute"],
        )
        exec_bytes = sum(i.get("bytes", 0) for i in exec_report["items"] if i["category"] == "trash")

        assert dry_bytes == exec_bytes
        assert dry_bytes > 0

    def test_usercache_category_same_count(self, p3_sandbox: _P3Sandbox) -> None:
        _make_cache_files(p3_sandbox.root, 5)

        dry_report = clean(
            [CATEGORY_BY_KEY["userCache"]],
            root=p3_sandbox.root,
            home=p3_sandbox.home,
            execute=False,
            operation_log=str(p3_sandbox.root / "dry_ops.jsonl"),
            command_argv=["clean", "--categories", "userCache"],
        )
        dry_cache = [i for i in dry_report["items"] if i["category"] == "userCache"]

        exec_report = clean(
            [CATEGORY_BY_KEY["userCache"]],
            root=p3_sandbox.root,
            home=p3_sandbox.home,
            execute=True,
            operation_log=str(p3_sandbox.root / "exec_ops.jsonl"),
            command_argv=["clean", "--categories", "userCache", "--execute"],
        )
        exec_cache = [i for i in exec_report["items"] if i["category"] == "userCache"]

        assert len(dry_cache) >= len(exec_cache)

    def test_both_reports_have_schema(self, p3_sandbox: _P3Sandbox) -> None:
        _make_trash_files(p3_sandbox.root, 1)

        dry_report = clean(
            [CATEGORY_BY_KEY["trash"]],
            root=p3_sandbox.root,
            home=p3_sandbox.home,
            execute=False,
            operation_log=str(p3_sandbox.root / "dry_ops.jsonl"),
            command_argv=["clean", "--categories", "trash"],
        )
        exec_report = clean(
            [CATEGORY_BY_KEY["trash"]],
            root=p3_sandbox.root,
            home=p3_sandbox.home,
            execute=True,
            operation_log=str(p3_sandbox.root / "exec_ops.jsonl"),
            command_argv=["clean", "--categories", "trash", "--execute"],
        )

        assert "schema" in dry_report
        assert "schema" in exec_report
        assert dry_report["schema"] == exec_report["schema"]

    def test_max_items_blocks_execute(self, p3_sandbox: _P3Sandbox) -> None:
        _make_trash_files(p3_sandbox.root, 10)

        with pytest.raises(SystemExit):
            clean(
                [CATEGORY_BY_KEY["trash"]],
                root=p3_sandbox.root,
                home=p3_sandbox.home,
                execute=True,
                max_items=3,
                operation_log=str(p3_sandbox.root / "exec_ops.jsonl"),
                command_argv=["clean", "--categories", "trash", "--max-items", "3", "--execute"],
            )

        # Files are preserved because execution was blocked
        remaining = list((p3_sandbox.root / "Users/tester/.Trash").glob("*.tmp"))
        assert len(remaining) == 10

    def test_empty_category_produces_zero_items(self, p3_sandbox: _P3Sandbox) -> None:
        dry_report = clean(
            [CATEGORY_BY_KEY["trash"]],
            root=p3_sandbox.root,
            home=p3_sandbox.home,
            execute=False,
            operation_log=str(p3_sandbox.root / "dry_ops.jsonl"),
            command_argv=["clean", "--categories", "trash"],
        )
        exec_report = clean(
            [CATEGORY_BY_KEY["trash"]],
            root=p3_sandbox.root,
            home=p3_sandbox.home,
            execute=True,
            operation_log=str(p3_sandbox.root / "exec_ops.jsonl"),
            command_argv=["clean", "--categories", "trash", "--execute"],
        )

        dry_trash = [i for i in dry_report["items"] if i["category"] == "trash"]
        exec_trash = [i for i in exec_report["items"] if i["category"] == "trash"]

        assert len(dry_trash) == 0
        assert len(exec_trash) == 0

    def test_total_bytes_consistency(self, p3_sandbox: _P3Sandbox) -> None:
        _make_trash_files(p3_sandbox.root, 4)

        dry_report = clean(
            [CATEGORY_BY_KEY["trash"]],
            root=p3_sandbox.root,
            home=p3_sandbox.home,
            execute=False,
            operation_log=str(p3_sandbox.root / "dry_ops.jsonl"),
            command_argv=["clean", "--categories", "trash"],
        )

        exec_report = clean(
            [CATEGORY_BY_KEY["trash"]],
            root=p3_sandbox.root,
            home=p3_sandbox.home,
            execute=True,
            operation_log=str(p3_sandbox.root / "exec_ops.jsonl"),
            command_argv=["clean", "--categories", "trash", "--execute"],
        )

        assert dry_report.get("total_bytes", 0) == exec_report.get("total_bytes", 0)
