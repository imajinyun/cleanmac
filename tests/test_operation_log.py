from __future__ import annotations

import json

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
