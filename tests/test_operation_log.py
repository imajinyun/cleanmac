from __future__ import annotations

import json

from cleancli import core
from tests.helpers import make_sandbox, run_cli


def test_operation_log_records_delete_status_path_bytes_mode_and_trash_path() -> None:
    tmp, root, home = make_sandbox()
    with tmp:
        operation_log = root / "logs/operations.jsonl"
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
            "--operation-log",
            str(operation_log),
        )
        report = json.loads(result.stdout)
        records = [json.loads(line) for line in operation_log.read_text(encoding="utf-8").splitlines()]

        record = next(row for row in records if str(row["path"]).endswith("download.bin"))
        assert report["operation_log"] == str(operation_log)
        assert record["status"] == "deleted"
        assert str(record["path"]).endswith("download.bin")
        assert record["bytes"] > 0
        assert record["delete_mode"] == "trash"
        assert record["trash_path"]


def test_operation_log_preflight_blocks_execute_when_parent_is_symlink() -> None:
    tmp, root, home = make_sandbox()
    with tmp:
        real_logs = root / "real-logs"
        real_logs.mkdir()
        symlink_logs = root / "logs-link"
        symlink_logs.symlink_to(real_logs, target_is_directory=True)
        candidate = root / "Users/tester/Downloads/download.bin"

        result = run_cli(
            "--root",
            str(root),
            "--home",
            str(home),
            "--json",
            "clean",
            "run",
            "--categories",
            "downloads",
            "--execute",
            "--yes",
            "--operation-log",
            str(symlink_logs / "operations.jsonl"),
            check=False,
        )

        assert result.returncode != 0
        assert "operation log preflight failed" in result.stderr
        assert candidate.exists()


def test_operation_log_preflight_blocks_execute_when_log_path_is_directory() -> None:
    tmp, root, home = make_sandbox()
    with tmp:
        operation_log = root / "logs/operations.jsonl"
        operation_log.mkdir(parents=True)
        candidate = root / "Users/tester/Downloads/download.bin"

        result = run_cli(
            "--root",
            str(root),
            "--home",
            str(home),
            "--json",
            "clean",
            "run",
            "--categories",
            "downloads",
            "--execute",
            "--yes",
            "--operation-log",
            str(operation_log),
            check=False,
        )

        assert result.returncode != 0
        assert "operation log preflight failed" in result.stderr
        assert candidate.exists()


def test_operation_log_preflight_rotates_oversized_log_before_delete() -> None:
    tmp, root, home = make_sandbox()
    with tmp:
        operation_log = root / "logs/operations.jsonl"
        operation_log.parent.mkdir(parents=True)
        operation_log.write_text("x" * (core.OPERATIONS_LOG_ROTATE_BYTES + 1), encoding="utf-8")
        rotated_log = operation_log.with_name("operations.jsonl.1")
        rotated_log.write_text("old rotated content", encoding="utf-8")

        result = run_cli(
            "--root",
            str(root),
            "--home",
            str(home),
            "--json",
            "clean",
            "run",
            "--categories",
            "downloads",
            "--delete-mode",
            "trash",
            "--execute",
            "--yes",
            "--operation-log",
            str(operation_log),
        )
        report = json.loads(result.stdout)
        records = [json.loads(line) for line in operation_log.read_text(encoding="utf-8").splitlines()]

        assert report["operation_log"] == str(operation_log)
        assert report["operation_log_status"] == "ready"
        assert report["operation_log_error"] is None
        assert report["operation_log_rotated"] is True
        assert report["operation_log_preflight"]["rotated"] is True
        assert rotated_log.exists()
        assert rotated_log.read_text(encoding="utf-8").startswith("x")
        assert records
        assert all(record["schema"] == "cleanmac.operation-log-entry.v1" for record in records)
