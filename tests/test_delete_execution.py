from __future__ import annotations

import json
from collections.abc import Iterator
from pathlib import Path
from unittest import mock

import pytest

from cleancli import core as cleancli
from cleancli import delete_ops
from tests.helpers import cleanmac_test_env, make_sandbox, run_cli


def run_cli_unchecked(*args: str):
    return run_cli(*args, check=False)


@pytest.fixture(autouse=True)
def _test_env() -> Iterator[None]:
    with cleanmac_test_env():
        yield


class TestDeleteFailureReason:
    def test_maps_permission_error(self) -> None:
        assert cleancli.delete_failure_reason(PermissionError("Operation not permitted")) == "permission-denied"

    def test_maps_symlink_protected(self) -> None:
        assert cleancli.delete_failure_reason(RuntimeError("symlink target is protected")) == "symlink-protected"

    def test_maps_protected_symlink_target_message(self) -> None:
        exc = RuntimeError("Refusing to delete symlink pointing to protected path: /x/link -> /System/x")
        assert cleancli.delete_failure_reason(exc) == "symlink-protected"

    @pytest.mark.parametrize(
        "message",
        [
            "Refusing to move symlink to Trash: /Users/t/Library/Caches/launcher.lck",
            "Refusing to sudo remove symlink: /Users/t/Downloads/link",
            "Refusing to delete unreadable symlink: /Users/t/Caches/broken.lnk",
        ],
    )
    def test_maps_benign_symlink_refusal_as_item_level_reason(self, message: str) -> None:
        assert cleancli.delete_failure_reason(RuntimeError(message)) == "symlink-not-removable"

    def test_maps_symlinked_trash_root_as_batch_aborting_reason(self) -> None:
        exc = RuntimeError("Refusing to use symlinked Trash directory: /Users/t/.Trash")
        assert cleancli.delete_failure_reason(exc) == "trash-root-symlink"

    def test_maps_protected_path(self) -> None:
        assert cleancli.delete_failure_reason(RuntimeError("Refusing to delete /System")) == "protected-path"

    def test_maps_trash_routing_failed(self) -> None:
        assert cleancli.delete_failure_reason(RuntimeError("Trash routing failed")) == "trash-routing-failed"

    def test_maps_unexpected_error(self) -> None:
        assert cleancli.delete_failure_reason(RuntimeError("unexpected")) == "delete-failed"


class TestDeleteBudgetGates:
    def test_max_delete_mb_blocks_execute_before_deleting(self) -> None:
        tmp, root, home = make_sandbox()
        with tmp:
            result = run_cli_unchecked(
                "--root",
                str(root),
                "--home",
                str(home),
                "clean",
                "--categories",
                "trash",
                "--execute",
                "--max-delete-mb",
                "0",
            )

            assert result.returncode != 0
            assert "exceed --max-delete-mb budget" in result.stderr
            assert (root / "Users/tester/.Trash/old.tmp").exists()

    def test_max_items_blocks_execute_before_deleting(self) -> None:
        tmp, root, home = make_sandbox()
        with tmp:
            (root / "Users/tester/.Trash/extra.tmp").write_text("extra")
            result = run_cli_unchecked(
                "--root",
                str(root),
                "--home",
                str(home),
                "clean",
                "--categories",
                "trash",
                "--execute",
                "--max-items",
                "1",
            )

            assert result.returncode != 0
            assert "exceeds --max-items budget" in result.stderr
            assert (root / "Users/tester/.Trash/old.tmp").exists()
            assert (root / "Users/tester/.Trash/extra.tmp").exists()

    def test_fail_on_skipped_blocks_execute_before_deleting(self) -> None:
        tmp, root, home = make_sandbox()
        with tmp:
            remove = root / "Users/tester/.Trash/remove.tmp"
            keep = root / "Users/tester/.Trash/keep.tmp"
            remove.write_text("remove")
            keep.write_text("keep")
            result = run_cli_unchecked(
                "--root",
                str(root),
                "--home",
                str(home),
                "clean",
                "--categories",
                "trash",
                "--exclude",
                "*keep.tmp",
                "--fail-on-skipped",
                "--execute",
            )

            assert result.returncode != 0
            assert "skipped by filters" in result.stderr
            assert remove.exists()
            assert keep.exists()


class TestDeleteExecutionBehavior:
    def test_trash_delete_mode_routes_candidates_to_recoverable_trash(self) -> None:
        tmp, root, home = make_sandbox()
        with tmp:
            result = run_cli(
                "--root",
                str(root),
                "--home",
                str(home),
                "--json",
                "clean",
                "--categories",
                "downloads",
                "--delete-mode",
                "trash",
                "--execute",
                "--yes",
            )
            report = json.loads(result.stdout)
            trash_entries = list((root / "Users/tester/.Trash").glob("cleanmac-*download.bin*"))

            assert report["delete_mode"] == "trash"
            assert not (root / "Users/tester/Downloads/download.bin").exists()
            assert trash_entries
            assert any(row["trash_path"] for row in report["items"] if row["path"].endswith("download.bin"))
            deletion_log = root / "Users/tester/.cleanmac/deletions.log"
            assert "\ttrash\t" in deletion_log.read_text(encoding="utf-8")

    def test_execute_records_item_failures_and_continues_by_default(self) -> None:
        tmp, root, home = make_sandbox()
        with tmp:
            (root / "Users/tester/.Trash/keep.tmp").write_text("keep")
            (root / "Users/tester/.Trash/remove.tmp").write_text("remove")
            operation_log = root / "logs" / "operations.jsonl"
            original_delete_path = delete_ops.delete_path

            def flaky_delete(path: Path, **kwargs):
                if path.name == "old.tmp":
                    raise PermissionError("Operation not permitted")
                return original_delete_path(path, **kwargs)

            with mock.patch.object(delete_ops, "delete_path", side_effect=flaky_delete):
                report = cleancli.clean(
                    [cleancli.CATEGORY_BY_KEY["trash"]],
                    root=root,
                    home=home,
                    execute=True,
                    risk_policy="default",
                    delete_mode="trash",
                    operation_log=str(operation_log),
                    command_argv=["clean", "--categories", "trash", "--execute"],
                )

            records = [json.loads(line) for line in operation_log.read_text(encoding="utf-8").splitlines()]
            failed = [row for row in report["items"] if row.get("status") == "failed"]
            [row for row in report["items"] if row.get("status") == "deleted"]

            assert report["failed_count"] == 1
            assert report["deleted_count"] >= 2
            assert failed[0]["reason"] == "permission-denied"
            assert (root / "Users/tester/.Trash/old.tmp").exists()
            assert {record["status"] for record in records} & {"failed", "deleted"}

    def test_trash_mode_skips_symlinked_cache_lock_and_completes_batch(self) -> None:
        tmp, root, home = make_sandbox()
        with tmp:
            cache_dir = root / "Users/tester/Library/Containers/com.tencent.meeting/Data/Library/Caches"
            cache_dir.mkdir(parents=True)
            lock_target = root / "Users/tester/runtime/launcher.lock"
            lock_target.parent.mkdir(parents=True)
            lock_target.write_text("lock", encoding="utf-8")
            lock_link = cache_dir / "launcher.lck"
            lock_link.symlink_to(lock_target)
            cache_file = cache_dir / "Cache.db"
            cache_file.write_text("cache", encoding="utf-8")

            dry_run = cleancli.clean(
                [cleancli.CATEGORY_BY_KEY["userAppCache"]],
                root=root,
                home=home,
                execute=False,
                delete_mode="trash",
            )
            link_skips = [row for row in dry_run["skipped"] if str(row["path"]).endswith("launcher.lck")]
            assert len(link_skips) == 1
            assert link_skips[0]["reason"] == "symlink"
            assert not link_skips[0]["selectable"]
            assert all(not str(row["path"]).endswith("launcher.lck") for row in dry_run["items"])

            report = cleancli.clean(
                [cleancli.CATEGORY_BY_KEY["userAppCache"]],
                root=root,
                home=home,
                execute=True,
                delete_mode="trash",
                operation_log=None,
            )

            assert report["failed_count"] == 0
            assert lock_link.is_symlink(), "symlink lock must be preserved, not trashed"
            assert lock_target.read_text(encoding="utf-8") == "lock"
            assert not cache_file.exists(), "regular cache siblings must still be cleaned"
            assert report["deleted_count"] >= 1
            assert any(str(row["path"]).endswith("Cache.db") for row in report["items"])
            assert all(
                str(row["path"]).endswith("launcher.lck") and row["status"] == "skipped"
                for row in report["skipped"]
                if str(row["path"]).endswith("launcher.lck")
            )

    def test_permanent_mode_still_unlinks_benign_symlink_candidates(self) -> None:
        tmp, root, home = make_sandbox()
        with tmp:
            cache_dir = root / "Users/tester/Library/Containers/com.example/Data/Library/Caches"
            link_target = root / "Users/tester/runtime/target.bin"
            link_target.parent.mkdir(parents=True)
            link_target.write_text("cache", encoding="utf-8")
            link = cache_dir / "link.lck"
            link.symlink_to(link_target)

            report = cleancli.clean(
                [cleancli.CATEGORY_BY_KEY["userAppCache"]],
                root=root,
                home=home,
                execute=True,
                delete_mode="permanent",
                operation_log=None,
            )

            assert report["failed_count"] == 0
            assert not link.exists(), "permanent mode unlinks the symlink itself"
            assert link_target.exists(), "permanent mode must never unlink through the symlink"

    def test_low_level_symlink_refusal_fails_item_without_aborting_batch(self) -> None:
        tmp, root, home = make_sandbox()
        with tmp:
            original_delete_path = delete_ops.delete_path

            def symlink_refusing_delete(path: Path, **kwargs):
                if path.name == "old.tmp":
                    raise RuntimeError(f"Refusing to move symlink to Trash: {path}")
                return original_delete_path(path, **kwargs)

            with mock.patch.object(delete_ops, "delete_path", side_effect=symlink_refusing_delete):
                report = cleancli.clean(
                    [cleancli.CATEGORY_BY_KEY["trash"]],
                    root=root,
                    home=home,
                    execute=True,
                    risk_policy="default",
                    delete_mode="trash",
                    operation_log=None,
                    command_argv=["clean", "--categories", "trash", "--execute"],
                )

            failed = [row for row in report["items"] if row.get("status") == "failed"]
            assert failed and failed[0]["reason"] == "symlink-not-removable"
            assert report["failed_count"] == 1
            assert (root / "Users/tester/.Trash/old.tmp").exists()

    def test_execute_fail_fast_stops_on_item_failure(self) -> None:
        tmp, root, home = make_sandbox()
        with tmp:
            original_delete_path = delete_ops.delete_path

            def flaky_delete(path: Path, **kwargs):
                if path.name == "download.bin":
                    raise PermissionError("Operation not permitted")
                return original_delete_path(path, **kwargs)

            with mock.patch.object(delete_ops, "delete_path", side_effect=flaky_delete):
                with pytest.raises(PermissionError):
                    cleancli.clean(
                        [cleancli.CATEGORY_BY_KEY["downloads"]],
                        root=root,
                        home=home,
                        execute=True,
                        risk_policy="default",
                        delete_mode="trash",
                        fail_fast=True,
                        command_argv=["clean", "--categories", "downloads", "--execute"],
                    )

            assert (root / "Users/tester/Downloads/download.bin").exists()
