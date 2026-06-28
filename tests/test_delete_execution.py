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
