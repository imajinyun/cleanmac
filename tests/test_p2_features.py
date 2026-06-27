"""P2 feature tests: hardlink mode, file-type/directory grouping, batch logging."""

from __future__ import annotations

import json
import os

from tests.helpers import make_sandbox, run_cli


class TestHardlinkMode:
    def test_hardlink_replaces_duplicate_with_same_inode(self):
        tmp, root, home = make_sandbox()
        with tmp:
            downloads = root / "Users" / "tester" / "Downloads"

            data = b"x" * (2 * 1024 * 1024)
            (downloads / "a.bin").write_bytes(data)
            (downloads / "b.bin").write_bytes(data)
            (downloads / "c.bin").write_bytes(data)

            result = run_cli(
                "--root",
                str(root),
                "--home",
                str(home),
                "--json",
                "clean",
                "run",
                "--categories",
                "duplicateFiles",
                "--execute",
                "--yes",
                "--delete-mode",
                "hardlink",
            )
            report = json.loads(result.stdout)
            dup_items = [item for item in report["items"] if item["category"] == "duplicateFiles"]
            assert len(dup_items) == 2
            assert all(item.get("hardlinked") for item in dup_items)

            dup_files = [p for p in downloads.iterdir() if p.name in {"a.bin", "b.bin", "c.bin"}]
            inodes = {p.stat().st_ino for p in dup_files}
            assert len(inodes) == 1

    def test_hardlink_skips_non_duplicate_categories(self):
        tmp, root, home = make_sandbox()
        with tmp:
            downloads = root / "Users" / "tester" / "Downloads"
            logs_dir = root / "Users" / "tester" / "Library" / "logs"
            logs_dir.mkdir(parents=True, exist_ok=True)
            (logs_dir / "app.log").write_bytes(b"log entry" * 1000)

            data = b"x" * (2 * 1024 * 1024)
            (downloads / "a.bin").write_bytes(data)
            (downloads / "b.bin").write_bytes(data)

            result = run_cli(
                "--root",
                str(root),
                "--home",
                str(home),
                "--json",
                "clean",
                "run",
                "--categories",
                "duplicateFiles,userLogs",
                "--execute",
                "--yes",
                "--delete-mode",
                "hardlink",
            )
            report = json.loads(result.stdout)
            log_items = [item for item in report["items"] if item["category"] == "userLogs"]
            assert all(item["status"] == "skipped" for item in log_items)
            assert all(item.get("reason") == "hardlink-mode-only-applies-to-duplicateFiles" for item in log_items)
            assert (logs_dir / "app.log").exists()

    def test_hardlink_already_linked_is_idempotent(self):
        tmp, root, home = make_sandbox()
        with tmp:
            downloads = root / "Users" / "tester" / "Downloads"

            data = b"z" * (2 * 1024 * 1024)
            (downloads / "a.bin").write_bytes(data)
            os.link(downloads / "a.bin", downloads / "b.bin")

            result = run_cli(
                "--root",
                str(root),
                "--home",
                str(home),
                "--json",
                "clean",
                "run",
                "--categories",
                "duplicateFiles",
                "--execute",
                "--yes",
                "--delete-mode",
                "hardlink",
            )
            json.loads(result.stdout)
            dup_files = [p for p in downloads.iterdir() if p.name in {"a.bin", "b.bin"}]
            inodes = {p.stat().st_ino for p in dup_files}
            assert len(inodes) == 1

    def test_hardlink_plan_does_not_modify_files(self):
        tmp, root, home = make_sandbox()
        with tmp:
            downloads = root / "Users" / "tester" / "Downloads"

            data = b"y" * (2 * 1024 * 1024)
            (downloads / "a.bin").write_bytes(data)
            (downloads / "b.bin").write_bytes(data)

            before = {p.name: p.stat().st_ino for p in downloads.iterdir() if p.name in {"a.bin", "b.bin"}}
            result = run_cli(
                "--root",
                str(root),
                "--home",
                str(home),
                "--json",
                "clean",
                "plan",
                "--categories",
                "duplicateFiles",
            )
            json.loads(result.stdout)
            after = {p.name: p.stat().st_ino for p in downloads.iterdir() if p.name in {"a.bin", "b.bin"}}
            assert before == after
            assert len(after) == 2


class TestGroupingFunctions:
    def test_by_file_type_groups_by_extension(self):
        tmp, root, home = make_sandbox()
        with tmp:
            downloads = root / "Users" / "tester" / "Downloads"

            (downloads / "video1.mp4").write_bytes(b"v" * (110 * 1024 * 1024))
            (downloads / "video2.mp4").write_bytes(b"w" * (120 * 1024 * 1024))
            (downloads / "data.zip").write_bytes(b"z" * (105 * 1024 * 1024))
            (downloads / "noext").write_bytes(b"n" * (102 * 1024 * 1024))

            result = run_cli(
                "--root",
                str(root),
                "--home",
                str(home),
                "--json",
                "clean",
                "plan",
                "--categories",
                "largeFiles",
            )
            report = json.loads(result.stdout)
            assert "by_file_type" in report
            ft = report["by_file_type"]
            assert "mp4" in ft
            assert ft["mp4"]["count"] == 2
            assert "zip" in ft
            assert ft["zip"]["count"] == 1
            assert "(no extension)" in ft

    def test_by_parent_directory_groups_by_parent(self):
        tmp, root, home = make_sandbox()
        with tmp:
            downloads = root / "Users" / "tester" / "Downloads"
            desktop = root / "Users" / "tester" / "Desktop"
            desktop.mkdir(parents=True, exist_ok=True)

            data = b"x" * (110 * 1024 * 1024)
            (downloads / "big1.iso").write_bytes(data)
            (downloads / "big2.dmg").write_bytes(data)
            (desktop / "big3.zip").write_bytes(data)

            result = run_cli(
                "--root",
                str(root),
                "--home",
                str(home),
                "--json",
                "clean",
                "plan",
                "--categories",
                "largeFiles",
            )
            report = json.loads(result.stdout)
            assert "by_parent_directory" in report
            by_dir = report["by_parent_directory"]
            dl_key = next(k for k in by_dir if "Downloads" in k)
            assert by_dir[dl_key]["count"] >= 2
            dt_key = next(k for k in by_dir if "Desktop" in k)
            assert by_dir[dt_key]["count"] == 1


class TestBatchDeletionLog:
    def test_batch_append_writes_multiple_entries_at_once(self):
        tmp, root, home = make_sandbox()
        with tmp:
            from cleancli.core import batch_append_deletion_log, deletion_log_path_for_context

            entries = [
                {
                    "mode": "trash",
                    "status": "deleted",
                    "path": "/tmp/a.txt",
                    "bytes_value": 100,
                    "detail": "trash:/tmp/.Trash/a.txt",
                },
                {
                    "mode": "trash",
                    "status": "deleted",
                    "path": "/tmp/b.txt",
                    "bytes_value": 200,
                    "detail": "trash:/tmp/.Trash/b.txt",
                },
                {
                    "mode": "permanent",
                    "status": "failed",
                    "path": "/tmp/c.txt",
                    "bytes_value": 300,
                    "detail": "permission denied",
                },
            ]

            result = batch_append_deletion_log(root=root, home=home, entries=entries)
            assert result

            log_path = deletion_log_path_for_context(root=root, home=home)
            lines = log_path.read_text().strip().split("\n")
            assert len(lines) == 3
            assert "a.txt" in lines[0]
            assert "b.txt" in lines[1]
            assert "c.txt" in lines[2]
            assert "failed" in lines[2]

    def test_batch_append_empty_entries_is_noop(self):
        tmp, root, home = make_sandbox()
        with tmp:
            from cleancli.core import batch_append_deletion_log, deletion_log_path_for_context

            result = batch_append_deletion_log(root=root, home=home, entries=[])
            assert result

            log_path = deletion_log_path_for_context(root=root, home=home)
            assert not log_path.exists()


class TestPreCleanReportEnhancement:
    def test_category_preview_includes_candidate_bytes(self):
        tmp, root, home = make_sandbox()
        with tmp:
            downloads = root / "Users" / "tester" / "Downloads"

            (downloads / "large1.bin").write_bytes(b"x" * (150 * 1024 * 1024))
            (downloads / "large2.bin").write_bytes(b"y" * (120 * 1024 * 1024))

            result = run_cli(
                "--root",
                str(root),
                "--home",
                str(home),
                "--json",
                "clean",
                "plan",
                "--categories",
                "largeFiles",
            )
            report = json.loads(result.stdout)
            pre = report["pre_clean_report"]
            preview = pre["category_preview"]
            lf = next(c for c in preview if c["key"] == "largeFiles")
            assert lf["candidate_count"] >= 2
            assert "candidate_bytes" in lf
            assert lf["candidate_bytes"] > 0
            assert "candidate_human" in lf


class TestNewAiTools:
    def test_analyze_duplicates_tool_exists(self):
        from cleancli.ai_schema import AI_TOOL_DEFINITIONS

        tools = {t["name"]: t for t in AI_TOOL_DEFINITIONS}
        assert "cleanmac_analyze_duplicates" in tools
        tool = tools["cleanmac_analyze_duplicates"]
        assert tool["risk"] == "readonly"
        assert tool["auto_call_allowed"] is True
        assert tool["requires_confirmation"] is False

    def test_analyze_large_files_tool_exists(self):
        from cleancli.ai_schema import AI_TOOL_DEFINITIONS

        tools = {t["name"]: t for t in AI_TOOL_DEFINITIONS}
        assert "cleanmac_analyze_large_files" in tools
        tool = tools["cleanmac_analyze_large_files"]
        assert tool["risk"] == "readonly"
        assert tool["auto_call_allowed"] is True

    def test_analyze_old_files_tool_exists(self):
        from cleancli.ai_schema import AI_TOOL_DEFINITIONS

        tools = {t["name"]: t for t in AI_TOOL_DEFINITIONS}
        assert "cleanmac_analyze_old_files" in tools
        tool = tools["cleanmac_analyze_old_files"]
        assert tool["risk"] == "readonly"
        assert tool["auto_call_allowed"] is True
