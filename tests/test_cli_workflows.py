from __future__ import annotations

import json
import os
import time

from tests.helpers import make_sandbox, run_cli


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

        assert report["dry_run"] is True
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


def test_profiles_expand_to_safe_category_and_budget_defaults() -> None:
    tmp, root, home = make_sandbox()
    with tmp:
        profiles = json.loads(run_cli("--json", "profiles").stdout)
        report = json.loads(
            run_cli("--root", str(root), "--home", str(home), "--json", "clean", "plan", "--profile", "safe").stdout
        )

        assert profiles["schema"] == "cleanmac.profiles.v1"
        assert "safe" in {profile["name"] for profile in profiles["profiles"]}
        assert report["risk_policy"] == "strict"
        assert report["max_delete_mb"] == 1024.0
        assert {row["key"] for row in report["selected_categories"]} == {
            "trash",
            "downloads",
            "userCache",
            "userLogs",
        }


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
        assert {row["kind"] for row in report["mappings"]} == {"logs", "cache"}
        assert not (root / "Users/tester/.CleanMacAppLogLinks").exists()


def test_links_execute_creates_and_removes_symlink_dirs() -> None:
    tmp, root, home = make_sandbox()
    with tmp:
        logs = root / "Users/tester/Library/Containers/com.example/Data/Library/Logs"
        run_cli(
            "--root",
            str(root),
            "--home",
            str(home),
            "links",
            "--kind",
            "logs",
            "--execute",
        )
        link_path = root / "Users/tester/.CleanMacAppLogLinks/com.example"
        assert link_path.is_symlink()
        assert link_path.resolve() == logs.resolve()

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
        assert report["removed"][0]["removed"] is True
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
        assert report["mode"] == "remove"
        assert report["removed"][0]["existed_before"] is True
        assert report["removed"][0]["removed"] is False
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
