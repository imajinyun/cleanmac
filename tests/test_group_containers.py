from __future__ import annotations

from tests.helpers import make_sandbox, run_clean_json, skipped_by_path


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
