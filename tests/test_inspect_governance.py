from __future__ import annotations

import json
import os
import time
from pathlib import Path

import cleancli.core as cleancli
from tests.helpers import make_sandbox, run_cli


def make_old(path: Path, *, days: int) -> None:
    old_time = time.time() - days * 24 * 60 * 60
    os.utime(path, (old_time, old_time))


def test_inspect_lists_direct_children_sorted_by_size() -> None:
    tmp, root, home = make_sandbox()
    with tmp:
        (root / "Users/tester/.Trash/big.tmp").write_text("x" * 100, encoding="utf-8")

        result = run_cli(
            "--root",
            str(root),
            "--home",
            str(home),
            "--json",
            "inspect",
            "--categories",
            "trash",
            "--limit",
            "1",
        )
        report = json.loads(result.stdout)

        assert report["shown_candidates"] == 1
        assert report["items"][0]["path"].endswith("big.tmp")
        assert report["ai_summary"]["schema"] == "cleanmac.ai-summary.v1"
        assert report["ai_summary"]["phase"] == "inspect"
        assert report["ai_summary"]["recommended_next_action"] == "generate_plan"
        assert report["ai_summary"]["safe_to_execute_after_confirmation"] is False
        assert "trash" in report["ai_summary"]["selected_categories"]
        assert report["ai_summary"]["headline"]


def test_inspect_supports_recursive_min_size_and_path_sort() -> None:
    tmp, root, home = make_sandbox()
    with tmp:
        nested = root / "Users/tester/.Trash/nested"
        nested.mkdir()
        (nested / "small.txt").write_text("tiny", encoding="utf-8")
        (nested / "large.bin").write_bytes(b"x" * (1024 * 1024 + 1))

        result = run_cli(
            "--root",
            str(root),
            "--home",
            str(home),
            "--json",
            "inspect",
            "--categories",
            "trash",
            "--recursive",
            "--min-size-mb",
            "1",
            "--sort",
            "path",
        )
        report = json.loads(result.stdout)
        paths = [row["path"] for row in report["items"]]

        assert report["recursive"] is True
        assert report["min_size_mb"] == 1
        assert paths == sorted(paths)
        assert any(path.endswith("nested/large.bin") for path in paths)
        large_row = next(row for row in report["items"] if row["path"].endswith("nested/large.bin"))
        assert large_row["depth"] == 2


def test_inspect_accepts_budget_flags_as_non_destructive_preview() -> None:
    tmp, root, home = make_sandbox()
    with tmp:
        log_file = root / "Users/tester/Library/logs/noisy.log"
        log_file.parent.mkdir(parents=True)
        log_file.write_text("log", encoding="utf-8")
        make_old(log_file, days=8)

        result = run_cli(
            "--root",
            str(root),
            "--home",
            str(home),
            "--json",
            "inspect",
            "--categories",
            "userLogs",
            "--older-than-days",
            "7",
            "--max-delete-mb",
            "1000",
            "--max-items",
            "500",
        )
        report = json.loads(result.stdout)

        assert report["max_delete_mb"] == 1000.0
        assert report["max_items"] == 500
        assert report["budget_summary"]["within_max_delete_budget"] is True
        assert report["budget_summary"]["within_max_items"] is True
        assert report["budget_summary"]["applies_to_execute"] is False
        assert log_file.exists()


def test_invalid_name_regex_is_rejected_before_deletion() -> None:
    tmp, root, home = make_sandbox()
    with tmp:
        result = run_cli(
            "--root",
            str(root),
            "--home",
            str(home),
            "inspect",
            "--categories",
            "trash",
            "--name-regex",
            "[",
            check=False,
        )

        assert result.returncode != 0
        assert "Invalid --name-regex" in result.stderr
        assert (root / "Users/tester/.Trash/old.tmp").exists()


def test_incomplete_downloads_skip_active_files() -> None:
    tmp, root, home = make_sandbox()
    with tmp:
        partial = root / "Users/tester/Downloads/partial.crdownload"
        partial.write_text("partial", encoding="utf-8")
        original = cleancli.is_file_open
        cleancli.is_file_open = lambda path: path.name == "partial.crdownload"  # type: ignore[assignment]
        try:
            report = cleancli.inspect_items(
                [cleancli.CATEGORY_BY_KEY["incompleteDownloads"]],
                root=root,
                home=home,
                limit=50,
            )
        finally:
            cleancli.is_file_open = original  # type: ignore[assignment]

        assert report["total_candidates"] == 0
        assert "active-file" in report["skipped_summary"]["by_reason"]


def test_mail_downloads_use_age_and_size_defaults() -> None:
    tmp, root, home = make_sandbox()
    with tmp:
        old_mail = root / "Users/tester/Library/Mail Downloads/old-mail.pdf"
        old_mail.parent.mkdir(parents=True)
        old_mail.write_text("mail-old", encoding="utf-8")
        make_old(old_mail, days=40)

        result = run_cli(
            "--root",
            str(root),
            "--home",
            str(home),
            "--json",
            "inspect",
            "--categories",
            "mails",
        )
        report = json.loads(result.stdout)

        assert report["total_candidates"] == 0
        assert "below-min-size" in report["skipped_summary"]["by_reason"]


def test_provider_specific_inspect_filters_are_auditable() -> None:
    tmp, root, home = make_sandbox()
    with tmp:
        stale = root / "private/var/folders/aa/bb/C/app/com.apple.metal"
        recent = root / "private/var/folders/aa/bb/C/app/com.apple.metalfe"
        stale.mkdir(parents=True)
        recent.mkdir(parents=True)
        stale_file = stale / "shader.cache"
        recent_file = recent / "shader.cache"
        stale_file.write_text("old", encoding="utf-8")
        recent_file.write_text("new", encoding="utf-8")
        make_old(stale_file, days=3)
        make_old(stale, days=3)

        gpu_report = json.loads(
            run_cli("--root", str(root), "--home", str(home), "--json", "inspect", "--categories", "gpuCaches").stdout
        )
        gpu_paths = [row["path"] for row in gpu_report["items"]]

        assert str(stale) in gpu_paths
        assert str(recent) not in gpu_paths
        assert "not-stale" in gpu_report["skipped_summary"]["by_reason"]

        cache = root / "private/var/folders/aa/bb/X/com.browser/foo.code_sign_clone"
        cache.mkdir(parents=True)
        code_sign_report = json.loads(
            run_cli(
                "--root",
                str(root),
                "--home",
                str(home),
                "--json",
                "inspect",
                "--categories",
                "browserCodeSignCache",
            ).stdout
        )

        assert code_sign_report["total_candidates"] == 1
        assert code_sign_report["items"][0]["path"] == str(cache)


def test_filters_apply_to_inspect_and_clean() -> None:
    tmp, root, home = make_sandbox()
    with tmp:
        keep = root / "Users/tester/.Trash/keep.tmp"
        remove = root / "Users/tester/.Trash/remove.log"
        keep.write_text("keep", encoding="utf-8")
        remove.write_text("remove", encoding="utf-8")

        inspect_report = json.loads(
            run_cli(
                "--root",
                str(root),
                "--home",
                str(home),
                "--json",
                "inspect",
                "--categories",
                "trash",
                "--name-regex",
                r"remove\.log$",
            ).stdout
        )
        inspect_paths = [row["path"] for row in inspect_report["items"]]

        assert str(remove) in inspect_paths
        assert str(keep) not in inspect_paths
        assert "name-regex-mismatch" in inspect_report["skipped_summary"]["by_reason"]

        clean_report = json.loads(
            run_cli(
                "--root",
                str(root),
                "--home",
                str(home),
                "--json",
                "clean",
                "--categories",
                "trash",
                "--exclude",
                "*keep.tmp",
                "--execute",
            ).stdout
        )

        assert clean_report["skipped_summary"]["by_reason"] == {"excluded": 1}
        assert keep.exists()
        assert not remove.exists()


def test_diagnose_recommends_safe_categories_and_flags_logs() -> None:
    tmp, root, home = make_sandbox()
    with tmp:
        mail_file = root / "Users/tester/Library/Mail Downloads/old-mail.pdf"
        mail_file.parent.mkdir(parents=True)
        mail_file.write_bytes(b"m" * (5 * 1024 * 1024 + 1))
        make_old(mail_file, days=40)
        xcode_cache = root / "Users/tester/Library/Developer/Xcode/DerivedData/App-a/cache.db"
        xcode_cache.parent.mkdir(parents=True)
        xcode_cache.write_text("derived", encoding="utf-8")
        log_file = root / "Users/tester/Library/logs/noisy.log"
        log_file.parent.mkdir(parents=True)
        log_file.write_text("log", encoding="utf-8")

        report = json.loads(
            run_cli(
                "--root",
                str(root),
                "--home",
                str(home),
                "--json",
                "diagnose",
                "--categories",
                "trash,mails,xcode,userLogs,downloads",
                "--log-threshold-mb",
                "0",
            ).stdout
        )
        issue_codes = {issue["code"] for issue in report["issues"]}

        assert report["recommended_clean_categories"] == ["trash", "mails", "xcode"]
        assert "userLogs" in report["advanced_options"]["selected_advanced_keys"]
        assert report["advanced_options"]["requires_extra_review"] is True
        assert "large-logs-may-indicate-problem" in issue_codes
        assert "downloads" in report["caution_clean_categories"]
        assert "trash,mails,xcode" in report["suggested_safe_command"]
