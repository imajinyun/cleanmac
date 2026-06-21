from __future__ import annotations

import json

from tests.helpers import make_sandbox, run_clean_json, run_cli, skipped_by_path


def test_com_apple_group_container_is_skipped_by_default() -> None:
    tmp, root, home = make_sandbox()
    with tmp:
        report = run_clean_json(root, home, "inspect", "--categories", "groupContainerCaches", "--older-than-days", "0")
        reasons = skipped_by_path(report)

        path = root / "Users/tester/Library/Group Containers/group.com.apple.notes/Library/Caches/cache.bin"
        assert reasons[str(path)] == "protected-group-container"


def test_safari_extension_group_container_is_skipped_by_default() -> None:
    tmp, root, home = make_sandbox()
    with tmp:
        report = run_clean_json(root, home, "inspect", "--categories", "groupContainerCaches", "--older-than-days", "0")
        reasons = skipped_by_path(report)

        path = root / "Users/tester/Library/Group Containers/group.com.apple.Safari.Extensions/Library/Caches/cache.bin"
        assert reasons[str(path)] == "protected-group-container"


def test_protected_app_allows_logs_only_and_skips_cache_data() -> None:
    tmp, root, home = make_sandbox()
    with tmp:
        cache_report = run_clean_json(root, home, "inspect", "--categories", "userAppCache")
        cache_reasons = skipped_by_path(cache_report)
        log_report = run_clean_json(root, home, "inspect", "--categories", "userAppLogs")
        items = log_report["items"]
        assert isinstance(items, list)
        log_items = {str(row["path"]) for row in items if isinstance(row, dict)}

        notes_cache = root / "Users/tester/Library/Containers/com.apple.Notes/Data/Library/Caches/cache.bin"
        example_log = root / "Users/tester/Library/Containers/com.example/Data/Library/Logs/app.log"
        assert cache_reasons[str(notes_cache)] == "protected-container-data"
        assert str(example_log) in log_items


def test_software_uninstall_group_container_candidates_explain_shared_risk() -> None:
    tmp, root, home = make_sandbox()
    with tmp:
        app_contents = root / "Applications/Example.app/Contents"
        app_contents.mkdir(parents=True)
        app_contents.joinpath("Info.plist").write_bytes(
            b'<?xml version="1.0" encoding="UTF-8"?><plist version="1.0"><dict>'
            b"<key>CFBundleIdentifier</key><string>com.example.app</string></dict></plist>"
        )

        result = run_cli(
            "--root", str(root), "--home", str(home), "--json", "software", "uninstall-plan", "--app", "Example"
        )
        plan = json.loads(result.stdout)
        uninstall_plan = plan["uninstall_plan"]
        assert isinstance(uninstall_plan, dict)
        group_candidate = next(
            candidate for candidate in uninstall_plan["candidates"] if candidate["kind"] == "group-container"
        )

        assert group_candidate["leftover_type"] == "containers"
        assert group_candidate["risk"] == "critical"
        assert group_candidate["default_selected"] is False
        assert group_candidate["shared_container"] is True
        assert "shared across apps" in group_candidate["risk_explanation"]
        assert group_candidate["why_not_default"] == "critical-risk candidate requires explicit review selection"
