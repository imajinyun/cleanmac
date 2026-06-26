from __future__ import annotations

import json
import os
import time
from pathlib import Path

import pytest

import cleancli.core as cleancli
from tests.helpers import make_sandbox, run_cli
from tests.test_review_selection import run_cli_unchecked


def test_capabilities_grouped_command_alias_metadata_matches_cli_contract() -> None:
    report = json.loads(run_cli("--json", "capabilities").stdout)

    clean_group = report["command_groups"]["clean"]
    assert clean_group["commands"] == [
        "clean list",
        "clean inspect",
        "clean plan",
        "clean validate-plan",
        "clean run",
        "clean scripts",
        "clean open",
        "clean links",
    ]
    assert clean_group["flat_command_aliases"] == [
        "list",
        "inspect",
        "plan",
        "validate-plan",
        "clean",
        "scripts",
        "open",
        "links",
    ]
    assert report["command_groups"]["analyze"]["commands"] == [
        "analyze categories",
        "analyze scan",
        "analyze tree",
    ]
    assert report["command_groups"]["analyze"]["flat_command_aliases"] == ["analyze"]
    assert report["preferred_command_style"] == "grouped"
    assert report["flat_command_compatibility"] is True


def test_grouped_clean_commands_match_flat_alias_reports() -> None:
    tmp, root, home = make_sandbox()
    with tmp:
        flat_alias = run_cli("--root", str(root), "--home", str(home), "--json", "inspect", "--categories", "trash")
        grouped = run_cli(
            "--root", str(root), "--home", str(home), "--json", "clean", "inspect", "--categories", "trash"
        )
        flat_alias_report = json.loads(flat_alias.stdout)
        grouped_report = json.loads(grouped.stdout)

        assert grouped_report["total_candidates"] == flat_alias_report["total_candidates"]
        assert grouped_report["items"] == flat_alias_report["items"]


def test_grouped_clean_run_executes_dry_run_alias() -> None:
    tmp, root, home = make_sandbox()
    with tmp:
        result = run_cli("--root", str(root), "--home", str(home), "--json", "clean", "run", "--categories", "trash")
        report = json.loads(result.stdout)

        assert report["dry_run"] is True
        assert report["selected_categories"][0]["key"] == "trash"
        assert (root / "Users/tester/.Trash/old.tmp").exists()


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
        old_time = time.time() - 8 * 24 * 60 * 60
        log_file = root / "Users/tester/Library/logs/noisy.log"
        log_file.parent.mkdir(parents=True, exist_ok=True)
        log_file.write_text("log", encoding="utf-8")
        os.utime(log_file, (old_time, old_time))
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
        result = run_cli_unchecked(
            "--root",
            str(root),
            "--home",
            str(home),
            "inspect",
            "--categories",
            "trash",
            "--name-regex",
            "[",
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
        old_time = time.time() - 40 * 24 * 60 * 60
        old_mail = root / "Users/tester/Library/Mail Downloads/old-mail.pdf"
        old_mail.parent.mkdir(parents=True, exist_ok=True)
        old_mail.write_text("small", encoding="utf-8")
        os.utime(old_mail, (old_time, old_time))
        original_test_mode = os.environ.get("CLEANMAC_TEST_MODE")
        os.environ["CLEANMAC_TEST_MODE"] = "1"
        try:
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
        finally:
            if original_test_mode is None:
                os.environ.pop("CLEANMAC_TEST_MODE", None)
            else:
                os.environ["CLEANMAC_TEST_MODE"] = original_test_mode
        report = json.loads(result.stdout)

        assert report["total_candidates"] == 0
        assert "below-min-size" in report["skipped_summary"]["by_reason"]


def test_gpu_cache_provider_only_returns_stale_allowlisted_dirs() -> None:
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
        old_time = time.time() - 3 * 24 * 60 * 60
        os.utime(stale_file, (old_time, old_time))
        os.utime(stale, (old_time, old_time))

        result = run_cli(
            "--root",
            str(root),
            "--home",
            str(home),
            "--json",
            "inspect",
            "--categories",
            "gpuCaches",
        )
        report = json.loads(result.stdout)
        paths = [row["path"] for row in report["items"]]

        assert str(stale) in paths
        assert str(recent) not in paths
        assert "not-stale" in report["skipped_summary"]["by_reason"]


def test_deep_system_cleanup_categories_cover_xcode_firmware_apple_silicon_and_diagnostics() -> None:
    tmp, root, home = make_sandbox()
    with tmp:
        fixtures = (
            root / "Users/tester/Library/Developer/Xcode/Archives/App.xcarchive/info.plist",
            root / "Users/tester/Library/Developer/Xcode/iOS DeviceSupport/17.0/symbols.bin",
            root / "private/var/db/oah/runtime-cache/cache.bin",
            root / "private/var/db/DetachedSignatures/signature-cache/cache.bin",
            root / "Library/Logs/DiagnosticReports/crash.ips",
        )
        for path in fixtures:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("cache", encoding="utf-8")

        result = run_cli(
            "--root",
            str(root),
            "--home",
            str(home),
            "--json",
            "clean",
            "inspect",
            "--categories",
            "xcode,deviceFirmware,appleSiliconCaches,systemDiagnostics",
            "--older-than-days",
            "0",
            "--limit",
            "50",
        )
        report = json.loads(result.stdout)
        paths = [row["path"] for row in report["items"]]

        assert str(root / "Users/tester/Library/Developer/Xcode/Archives/App.xcarchive") in paths
        assert str(root / "Users/tester/Library/Developer/Xcode/iOS DeviceSupport/17.0") in paths
        assert str(root / "private/var/db/oah/runtime-cache") in paths
        assert str(root / "private/var/db/DetachedSignatures/signature-cache") in paths
        assert str(root / "Library/Logs/DiagnosticReports/crash.ips") in paths
        assert report["by_category"]["deviceFirmware"]["count"] == 1
        assert report["by_category"]["appleSiliconCaches"]["count"] == 2


def test_browser_code_sign_cache_provider_uses_x_shard_and_rejects_outside_root() -> None:
    tmp, root, home = make_sandbox()
    with tmp:
        cache = root / "private/var/folders/aa/bb/X/com.browser/foo.code_sign_clone"
        cache.mkdir(parents=True)

        result = run_cli(
            "--root",
            str(root),
            "--home",
            str(home),
            "--json",
            "inspect",
            "--categories",
            "browserCodeSignCache",
        )
        report = json.loads(result.stdout)

        assert report["total_candidates"] == 1
        assert report["items"][0]["path"] == str(cache)
        try:
            cleancli.assert_safe_to_delete(
                Path("/tmp/cleanmac-outside-candidate"),
                root=root,
                home=home,
            )
        except RuntimeError as exc:
            assert "outside sandbox root" in str(exc)
        else:
            raise AssertionError("outside-root candidate should be rejected")


def test_older_than_days_filters_new_candidates() -> None:
    tmp, root, home = make_sandbox()
    with tmp:
        old_file = root / "Users/tester/.Trash/ancient.tmp"
        new_file = root / "Users/tester/.Trash/fresh.tmp"
        old_file.write_text("old", encoding="utf-8")
        new_file.write_text("new", encoding="utf-8")
        old_time = time.time() - 10 * 24 * 60 * 60
        os.utime(old_file, (old_time, old_time))

        result = run_cli(
            "--root",
            str(root),
            "--home",
            str(home),
            "--json",
            "inspect",
            "--categories",
            "trash",
            "--older-than-days",
            "7",
            "--sort",
            "path",
        )
        report = json.loads(result.stdout)
        paths = [row["path"] for row in report["items"]]

        assert str(old_file) in paths
        assert str(new_file) not in paths
        assert "too-new" in report["skipped_summary"]["by_reason"]


def test_grouped_command_matrix_smoke_remains_non_destructive() -> None:
    tmp, root, home = make_sandbox()
    with tmp:
        plan_result = run_cli(
            "--root",
            str(root),
            "--home",
            str(home),
            "--json",
            "clean",
            "plan",
            "--categories",
            "trash",
        )
        plan_file = root / "plan.json"
        plan_file.write_text(plan_result.stdout, encoding="utf-8")

        cases: list[tuple[list[str], str, dict[str, object]]] = [
            (["clean", "list"], "cleanmac.category-list.v1", {"categories": list}),
            (["clean", "inspect", "--categories", "trash"], "cleanmac.inspect.v1", {"dry_run": True}),
            (["clean", "plan", "--categories", "trash"], "cleanmac.plan.v1", {}),
            (["clean", "validate-plan", "--plan-file", str(plan_file)], "cleanmac.validate-plan.v1", {"valid": True}),
            (["clean", "scripts", "--categories", "trash"], "cleanmac.scripts.v1", {}),
            (["clean", "open", "--categories", "trash"], "cleanmac.open.v1", {"dry_run": True}),
            (["clean", "links"], "cleanmac.links.v1", {"dry_run": True}),
            (["software", "list"], "cleanmac.software.v1", {"destructive": False}),
            (["software", "leftovers"], "cleanmac.software.v1", {"destructive": False}),
            (["software", "orphans"], "cleanmac.software-orphans.v1", {"dry_run": True}),
            (["software", "startup-items"], "cleanmac.software.v1", {"destructive": False}),
            (["startup", "audit"], "cleanmac.startup-audit.v1", {"dry_run": True}),
            (["startup", "plan"], "cleanmac.startup-plan.v1", {"dry_run": True}),
            (["privacy", "inspect", "--scope", "cache"], "cleanmac.privacy-inspect.v1", {"dry_run": True}),
            (["privacy", "plan", "--scope", "credentials"], "cleanmac.privacy-plan.v1", {"dry_run": True}),
            (["optimize", "list"], "cleanmac.optimize.v1", {"destructive": False}),
            (["optimize", "run", "--execute"], "cleanmac.optimize.v1", {"execution_supported": False}),
            (["analyze", "categories", "--categories", "trash"], "cleanmac.analyze.v1", {"dry_run": True}),
            (["analyze", "scan", "--path", "/Users/tester", "--depth", "1"], "cleanmac.analyze-tree.v1", {}),
            (["status", "snapshot"], "cleanmac.status.snapshot.v1", {"destructive": False}),
        ]

        for command_args, expected_schema, expected_fields in cases:
            result = run_cli("--root", str(root), "--home", str(home), "--json", *command_args)
            report = json.loads(result.stdout)

            assert report["schema"] == expected_schema, command_args
            for field, expected in expected_fields.items():
                if isinstance(expected, type):
                    assert isinstance(report[field], expected), command_args
                else:
                    assert report[field] == expected, command_args
            if command_args[:2] == ["clean", "scripts"]:
                assert report["script_inventory"]["schema"] == "cleanmac.script-groups.v1"

        assert (root / "Users/tester/.Trash/old.tmp").exists()
        assert (root / "Users/tester/Downloads/download.bin").exists()


def test_explain_summarizes_plan_without_execution() -> None:
    tmp, root, home = make_sandbox()
    with tmp:
        trash_file = root / "Users/tester/.Trash/old.tmp"
        trash_file.write_bytes(b"x" * 2048)
        plan_result = run_cli(
            "--root",
            str(root),
            "--home",
            str(home),
            "--json",
            "plan",
            "--categories",
            "trash",
        )
        plan_file = root / "plan.json"
        plan_file.write_text(plan_result.stdout, encoding="utf-8")

        explain_result = run_cli(
            "--root",
            str(root),
            "--home",
            str(home),
            "--json",
            "explain",
            "--input-file",
            str(plan_file),
        )
        report = json.loads(explain_result.stdout)

        assert report["schema"] == "cleanmac.explain.v1"
        assert report["destructive"] is False
        assert report["dry_run"] is True
        assert report["source_schema"] == "cleanmac.plan.v1"
        assert report["summary"]["candidate_count"] == 1
        assert report["summary"]["estimated_reclaimable_bytes"] == 2048
        assert report["ai_guidance"]["safe_to_execute"] is False
        assert "trash delete mode" in report["ai_guidance"]["execute_requires"]
        assert report["top_categories"][0]["category"] == "trash"
        assert trash_file.exists()


def test_diagnose_recommends_safe_categories_and_flags_logs() -> None:
    tmp, root, home = make_sandbox()
    with tmp:
        mail_file = root / "Users/tester/Library/Mail Downloads/old-mail.pdf"
        mail_file.parent.mkdir(parents=True)
        mail_file.write_bytes(b"m" * (5 * 1024 * 1024 + 1))
        old_timestamp = time.time() - (40 * 24 * 60 * 60)
        os.utime(mail_file, (old_timestamp, old_timestamp))

        xcode_cache = root / "Users/tester/Library/Developer/Xcode/DerivedData/App-a/cache.db"
        xcode_cache.parent.mkdir(parents=True)
        xcode_cache.write_text("derived", encoding="utf-8")

        log_file = root / "Users/tester/Library/logs/noisy.log"
        log_file.parent.mkdir(parents=True)
        log_file.write_text("log", encoding="utf-8")

        result = run_cli(
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
        )
        report = json.loads(result.stdout)
        issue_codes = {issue["code"] for issue in report["issues"]}

        assert report["recommended_clean_categories"] == ["trash", "mails", "xcode"]
        assert "userLogs" in report["advanced_options"]["selected_advanced_keys"]
        assert report["advanced_options"]["requires_extra_review"] is True
        assert "large-logs-may-indicate-problem" in issue_codes
        assert "downloads" in report["caution_clean_categories"]
        assert "trash,mails,xcode" in report["suggested_safe_command"]


def test_workflow_selected_dry_run_scope_includes_high_risk_without_execute() -> None:
    tmp, root, home = make_sandbox()
    with tmp:
        result = run_cli(
            "--root",
            str(root),
            "--home",
            str(home),
            "--json",
            "workflow",
            "--categories",
            "trash,downloads",
            "--dry-run-scope",
            "selected",
        )
        report = json.loads(result.stdout)

        assert [category["key"] for category in report["dry_run_categories"]] == ["trash", "downloads"]
        assert report["reports"]["dry_run"]["dry_run"] is True
        assert len(report["reports"]["dry_run"]["items"]) >= 2
        assert (root / "Users/tester/Downloads/download.bin").exists()


def test_grouped_analyze_tree_reports_largest_entries() -> None:
    tmp, root, home = make_sandbox()
    with tmp:
        result = run_cli(
            "--root",
            str(root),
            "--home",
            str(home),
            "--json",
            "analyze",
            "tree",
            "--path",
            "/Users/tester",
            "--depth",
            "1",
            "--top",
            "5",
        )
        report = json.loads(result.stdout)

        assert report["schema"] == "cleanmac.analyze-tree.v1"
        assert report["destructive"] is False
        assert report["exists"] is True
        assert report["shown_entries"] <= 5


def test_analyze_tree_writes_markdown_report_with_file_links() -> None:
    tmp, root, home = make_sandbox()
    with tmp:
        report_file = root / "tree-report.md"
        result = run_cli(
            "--root",
            str(root),
            "--home",
            str(home),
            "--json",
            "--report-file",
            str(report_file),
            "--report-format",
            "markdown",
            "analyze",
            "tree",
            "--path",
            "/Users/tester",
            "--depth",
            "1",
            "--top",
            "5",
        )
        report = json.loads(result.stdout)
        markdown = report_file.read_text(encoding="utf-8")

        assert report["report_format"] == "markdown"
        assert "# cleanmac.analyze-tree.v1" in markdown
        assert "Open in Finder" in markdown


def test_analyze_tree_markdown_report_preserves_sandbox_paths_and_schema_fields() -> None:
    tmp, root, home = make_sandbox()
    with tmp:
        report_file = root / "tree-report.md"
        result = run_cli(
            "--root",
            str(root),
            "--home",
            str(home),
            "--json",
            "--report-file",
            str(report_file),
            "--report-format",
            "markdown",
            "analyze",
            "tree",
            "--path",
            "/Users/tester",
            "--depth",
            "1",
            "--top",
            "5",
        )
        report = json.loads(result.stdout)
        markdown = report_file.read_text(encoding="utf-8")

        assert report["schema"] == "cleanmac.analyze-tree.v1"
        assert report["destructive"] is False
        assert report["path"] == str(root / "Users/tester")
        assert report["report_file"] == str(report_file)
        assert report["report_format"] == "markdown"
        assert 0 < report["shown_entries"] <= 5
        assert report["total_entries"] >= report["shown_entries"]
        assert report["entries"]
        assert all(entry["path"].startswith(str(root)) for entry in report["entries"])
        assert all({"path", "name", "type", "depth", "bytes", "human"}.issubset(entry) for entry in report["entries"])
        assert str(root / "Users/tester") in markdown
        assert "file://" in markdown
        assert "Raw JSON" in markdown


def test_unknown_category_cli_guidance_matches_grouped_compatibility() -> None:
    list_result = run_cli("list", "--categories", "doesNotExist", check=False)

    assert list_result.returncode != 0
    assert "unrecognized arguments" in list_result.stderr

    inspect_result = run_cli("inspect", "--categories", "doesNotExist", check=False)
    assert inspect_result.returncode != 0
    assert "Unknown category: doesNotExist" in inspect_result.stderr
    assert "trash" in inspect_result.stderr
    assert "imessage" in inspect_result.stderr


def test_analyze_group_rejects_non_cli_view_action() -> None:
    removed_action = "t" + "ui"
    result = run_cli("--json", "analyze", removed_action, "--path", ".", check=False)

    assert result.returncode != 0
    assert "unrecognized arguments" in result.stderr


def test_software_optimize_and_status_grouped_commands_are_safe() -> None:
    tmp, root, home = make_sandbox()
    with tmp:
        software = json.loads(
            run_cli(
                "--root", str(root), "--home", str(home), "--json", "software", "uninstall-plan", "--app", "Demo"
            ).stdout
        )
        optimize = json.loads(run_cli("--json", "optimize", "plan").stdout)
        status = json.loads(run_cli("--root", str(root), "--json", "status", "snapshot").stdout)

        assert software["schema"] == "cleanmac.software-uninstall-plan.v1"
        assert software["destructive"] is False
        assert software["uninstall_plan"]["app"] == "Demo"
        assert optimize["schema"] == "cleanmac.optimize.v1"
        assert optimize["execution_supported"] is False
        assert status["schema"] == "cleanmac.status.snapshot.v1"
        assert "disk" in status


def test_doctor_reports_environment_and_full_disk_access_guidance() -> None:
    result = run_cli("--json", "doctor")
    report = json.loads(result.stdout)

    assert report["schema"] == "cleanmac.doctor.v1"
    assert report["destructive"] is False
    assert "platform" in report
    assert "python" in report
    assert "full_disk_access" in report["checks"]
    assert "live_root_execution" in report["checks"]
    assert "private_path_policy" in report["checks"]
    assert "lsof_available" in report["checks"]
    assert "getconf_available" in report["checks"]


def test_open_reports_special_finder_targets() -> None:
    tmp, root, home = make_sandbox()
    with tmp:
        result = run_cli(
            "--root",
            str(root),
            "--home",
            str(home),
            "--json",
            "open",
            "--categories",
            "terminal,userAppLogs,userAppCache,trash",
        )
        report = json.loads(result.stdout)
        targets = {row["category"]: row for row in report["targets"]}

        assert report["schema"] == "cleanmac.open.v1"
        assert report["dry_run"] is True
        assert len(report["targets"]) == 4
        assert targets["terminal"]["special_case"] is True
        assert targets["terminal"]["path"].endswith("/private/var/log/asl")
        assert ".CleanMacAppLogLinks" in targets["userAppLogs"]["path"]
        assert ".CleanMacAppCacheLinks" in targets["userAppCache"]["path"]
        assert targets["trash"]["path"].endswith("/Users/tester/.Trash")
        assert "finder_url" in targets["trash"]
        assert "manual_command" in targets["trash"]
        assert targets["trash"]["open_command"][0] == "open"
        assert targets["trash"]["reveal_command"][:2] == ["open", "-R"]
        assert "open -R" in targets["trash"]["reveal_command_text"]
        assert targets["trash"]["open_supported"] is True


@pytest.mark.parametrize(
    ("profile", "expected_categories", "expected_risk_policy", "expected_max_delete_mb"),
    [
        ("safe", {"trash", "downloads", "userCache", "userLogs"}, "strict", 1024.0),
        (
            "developer",
            {"xcode", "nodePackageCaches", "pythonPackageCaches", "goBuildCaches"},
            "default",
            4096.0,
        ),
        ("browser", {"chrome", "firefox"}, "strict", 2048.0),
    ],
)
def test_profiles_expand_to_safe_category_and_budget_defaults(
    profile: str,
    expected_categories: set[str],
    expected_risk_policy: str,
    expected_max_delete_mb: float,
) -> None:
    tmp, root, home = make_sandbox()
    with tmp:
        profiles = json.loads(run_cli("--json", "profiles").stdout)
        report = json.loads(
            run_cli("--root", str(root), "--home", str(home), "--json", "clean", "plan", "--profile", profile).stdout
        )

        assert profiles["schema"] == "cleanmac.profiles.v1"
        profiles_by_name = {row["name"]: row for row in profiles["profiles"]}
        assert profile in profiles_by_name
        assert profiles_by_name[profile]["delete_mode"] == "trash"
        assert report["risk_policy"] == expected_risk_policy
        assert report["max_delete_mb"] == expected_max_delete_mb
        assert {row["key"] for row in report["selected_categories"]} == expected_categories


def test_profiles_and_links_expose_safe_metadata_contracts() -> None:
    tmp, root, home = make_sandbox()
    with tmp:
        profiles = json.loads(run_cli("--json", "profiles").stdout)
        links = json.loads(run_cli("--root", str(root), "--home", str(home), "--json", "links").stdout)

        by_name = {profile["name"]: profile for profile in profiles["profiles"]}
        assert profiles["schema"] == "cleanmac.profiles.v1"
        assert profiles["destructive"] is False
        assert profiles["dry_run"] is True
        assert profiles["profile_count"] == 3
        assert set(by_name) == {"safe", "developer", "browser"}
        assert by_name["safe"]["risk_policy"] == "strict"
        assert by_name["safe"]["delete_mode"] == "trash"
        assert by_name["safe"]["max_delete_mb"] == 1024
        assert by_name["developer"]["max_delete_mb"] == 4096
        assert by_name["browser"]["max_delete_mb"] == 2048
        assert by_name["safe"]["categories"] == ["trash", "downloads", "userCache", "userLogs"]
        assert by_name["developer"]["categories"] == [
            "xcode",
            "nodePackageCaches",
            "pythonPackageCaches",
            "goBuildCaches",
        ]
        assert by_name["browser"]["categories"] == ["chrome", "firefox"]
        assert by_name["developer"]["risk_policy"] == "default"
        assert by_name["browser"]["risk_policy"] == "strict"
        assert all(profile["delete_mode"] == "trash" for profile in profiles["profiles"])
        assert all(profile["safe_to_auto_execute"] is False for profile in profiles["profiles"])
        assert by_name["developer"]["example_plan_command"] == [
            "cleanmac",
            "--json",
            "clean",
            "plan",
            "--profile",
            "developer",
        ]

        assert links["schema"] == "cleanmac.links.v1"
        assert links["destructive"] is False
        assert links["dry_run"] is True
        assert links["mode"] == "create-update"
        assert links["kind"] == "all"
        assert links["model"]["create"] == "create app log/cache symlink directories"
        assert links["model"]["remove"] == "remove app log/cache symlink directories"
        resolved_root = str(root.resolve())
        assert links["container_root"] == str((root / "Users/tester/Library/Containers").resolve())
        assert links["mappings"]
        assert {mapping["kind"] for mapping in links["mappings"]} == {"logs", "cache"}
        assert any(mapping["container"] == "com.example" for mapping in links["mappings"])
        assert any(mapping["link_dir"].endswith(".CleanMacAppLogLinks") for mapping in links["mappings"])
        assert any(mapping["link_dir"].endswith(".CleanMacAppCacheLinks") for mapping in links["mappings"])
        for mapping in links["mappings"]:
            assert mapping["status"] == "planned"
            assert mapping["kind"] in {"logs", "cache"}
            assert mapping["source"].startswith(resolved_root)
            assert mapping["link_path"].startswith(str((root / "Users/tester").resolve()))
        assert links["removed"] == []


def test_links_reports_symbolic_link_mappings() -> None:
    tmp, root, home = make_sandbox()
    with tmp:
        result = run_cli(
            "--root",
            str(root),
            "--home",
            str(home),
            "--json",
            "links",
        )
        report = json.loads(result.stdout)

        assert report["dry_run"] is True
        assert report["mode"] == "create-update"
        mappings = {(row["kind"], row["container"]): row for row in report["mappings"]}
        expected = {
            "logs": (
                root / "Users/tester/Library/Containers/com.example/Data/Library/Logs",
                root / "Users/tester/.CleanMacAppLogLinks/com.example",
            ),
            "cache": (
                root / "Users/tester/Library/Containers/com.example/Data/Library/Caches",
                root / "Users/tester/.CleanMacAppCacheLinks/com.example",
            ),
        }

        assert {("logs", "com.example"), ("cache", "com.example")}.issubset(mappings)
        for kind, (source, link_path) in expected.items():
            mapping = mappings[(kind, "com.example")]
            assert mapping["source"] == str(source.resolve())
            assert mapping["link_dir"] == str(link_path.parent.resolve())
            assert mapping["link_path"] == str(link_path.parent.resolve() / link_path.name)
            assert mapping["status"] == "planned"
        assert not (root / "Users/tester/.CleanMacAppLogLinks").exists()


def test_links_execute_creates_and_removes_symlink_dirs() -> None:
    tmp, root, home = make_sandbox()
    with tmp:
        logs = root / "Users/tester/Library/Containers/com.example/Data/Library/Logs"
        create = run_cli(
            "--root",
            str(root),
            "--home",
            str(home),
            "--json",
            "links",
            "--kind",
            "logs",
            "--execute",
        )
        create_report = json.loads(create.stdout)
        link_path = root / "Users/tester/.CleanMacAppLogLinks/com.example"
        assert link_path.is_symlink()
        assert link_path.resolve() == logs.resolve()
        assert create_report["dry_run"] is False
        assert create_report["destructive"] is False
        created_mapping = create_report["mappings"][0]
        assert created_mapping["kind"] == "logs"
        assert created_mapping["container"] == "com.example"
        assert created_mapping["status"] == "created"
        assert created_mapping["source"] == str(logs.resolve())
        assert created_mapping["link_dir"] == str(link_path.parent.resolve())
        assert created_mapping["link_path"] == str(link_path.parent.resolve() / link_path.name)

        result = run_cli(
            "--root",
            str(root),
            "--home",
            str(home),
            "--json",
            "links",
            "--kind",
            "logs",
            "--remove",
            "--execute",
        )
        report = json.loads(result.stdout)
        assert report["mode"] == "remove"
        assert report["destructive"] is True
        assert report["dry_run"] is False
        removed = report["removed"][0]
        assert removed["kind"] == "logs"
        assert removed["link_dir"] == str(link_path.parent.resolve())
        assert removed["existed_before"] is True
        assert removed["removed"] is True
        assert not (root / "Users/tester/.CleanMacAppLogLinks").exists()


def test_links_remove_dry_run_preserves_existing_link_directory() -> None:
    tmp, root, home = make_sandbox()
    with tmp:
        link_dir = root / "Users/tester/.CleanMacAppLogLinks"
        link_dir.mkdir(parents=True)

        result = run_cli(
            "--root",
            str(root),
            "--home",
            str(home),
            "--json",
            "links",
            "--kind",
            "logs",
            "--remove",
        )
        report = json.loads(result.stdout)

        assert report["dry_run"] is True
        assert report["destructive"] is False
        assert report["mode"] == "remove"
        assert report["mappings"] == []
        removed = report["removed"][0]
        assert removed["kind"] == "logs"
        assert removed["link_dir"] == str(link_dir.resolve())
        assert removed["existed_before"] is True
        assert removed["removed"] is False
        assert link_dir.exists()


def test_links_execute_skips_existing_non_symlink_mapping() -> None:
    tmp, root, home = make_sandbox()
    with tmp:
        link_path = root / "Users/tester/.CleanMacAppLogLinks/com.example"
        link_path.parent.mkdir(parents=True)
        link_path.mkdir()

        result = run_cli(
            "--root",
            str(root),
            "--home",
            str(home),
            "--json",
            "links",
            "--kind",
            "logs",
            "--execute",
        )
        report = json.loads(result.stdout)
        mapping = report["mappings"][0]

        assert mapping["status"] == "skipped-existing-non-symlink"
        assert link_path.is_dir()
        assert not link_path.is_symlink()


def test_analyze_uses_sandbox_root() -> None:
    tmp, root, home = make_sandbox()
    with tmp:
        result = run_cli(
            "--root",
            str(root),
            "--home",
            str(home),
            "--json",
            "analyze",
            "--default",
        )
        report = json.loads(result.stdout)
        paths = "\n".join(target["path"] for target in report["targets"])

        assert report["total_bytes"] > 0
        assert "human" in report["categories"][0]
        assert str(root / "Users/tester/.Trash") in paths
