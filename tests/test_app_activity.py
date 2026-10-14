from __future__ import annotations

from dataclasses import replace
from pathlib import Path
from unittest.mock import patch

import pytest

from cleancli import core


def make_cache(root: Path, relative: str) -> Path:
    path = root / "Users/tester" / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"cache")
    return path


@pytest.mark.parametrize(
    ("relative", "category", "process"),
    [
        (
            "Library/Caches/Microsoft Edge/cache.bin",
            "userCache",
            "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge",
        ),
        ("Library/Caches/Google/Chrome/cache.bin", "userCache", "Google Chrome Helper (Renderer)"),
        ("Library/Caches/LarkShell/cache.bin", "userCache", "/Applications/Feishu.app/Contents/MacOS/Feishu"),
        ("Library/Caches/LarkInternational/cache.bin", "userCache", "Lark"),
        ("Library/Caches/com.cmuxterm.app/cache.bin", "userCache", "cmux"),
        ("Library/Caches/com.openai.chat/cache.bin", "userCache", "/Applications/ChatGPT.app/Contents/MacOS/ChatGPT"),
        (".cache/puppeteer/chrome/cache.bin", "automationBrowserCaches", "Google Chrome for Testing"),
        ("Library/Containers/com.tencent.xinWeChat/Data/Library/Caches/cache.bin", "userAppCache", "WeChat"),
    ],
)
def test_generic_cache_discovery_respects_application_activity(
    tmp_path: Path, relative: str, category: str, process: str
) -> None:
    make_cache(tmp_path, relative)
    with (
        patch.object(core, "run_text_command", return_value=process),
        patch.object(core, "is_test_no_auth", return_value=False),
    ):
        report = core.inspect_items(
            [core.CATEGORY_BY_KEY[category]], root=tmp_path, home=Path("/Users/tester"), limit=-1
        )
    assert report["items"] == []
    assert report["skipped_summary"]["by_reason"] == {"app-running": 1}
    assert report["skipped"][0]["application"]


def test_unknown_process_state_preserves_application_caches(tmp_path: Path) -> None:
    make_cache(tmp_path, "Library/Caches/Microsoft Edge/cache.bin")
    with (
        patch.object(core, "run_text_command", return_value=None),
        patch.object(core, "is_test_no_auth", return_value=False),
    ):
        report = core.inspect_items(
            [core.CATEGORY_BY_KEY["userCache"]], root=tmp_path, home=Path("/Users/tester"), limit=-1
        )
    assert report["items"] == []
    assert report["skipped_summary"]["by_reason"] == {"process-state-unknown": 1}


def test_duplicate_file_preview_uses_the_same_cache_activity_guard(tmp_path: Path) -> None:
    first = make_cache(tmp_path, "Library/Caches/Microsoft Edge/first.bin")
    second = make_cache(tmp_path, "Library/Caches/Microsoft Edge/second.bin")
    first.write_bytes(b"a" * (1024 * 1024))
    second.write_bytes(first.read_bytes())
    category = replace(core.CATEGORY_BY_KEY["duplicateFiles"], paths=("~/Library/Caches/Microsoft Edge",))
    with (
        patch.dict(core.CATEGORY_BY_KEY, {"duplicateFiles": category}),
        patch.object(core, "run_text_command", return_value="Microsoft Edge"),
        patch.object(core, "is_test_no_auth", return_value=False),
    ):
        report = core.clean(
            [category],
            root=tmp_path,
            home=Path("/Users/tester"),
            execute=False,
            delete_mode="trash",
            operation_log=None,
        )
    assert report["items"] == []
    assert report["skipped_summary"]["by_reason"] == {"app-running": 1}


def test_duplicate_file_preview_cannot_select_browser_credentials_in_a_cache(tmp_path: Path) -> None:
    cookie = make_cache(tmp_path, "Library/Caches/Microsoft Edge/Cookies")
    copy = make_cache(tmp_path, "Downloads/copy.bin")
    cookie.write_bytes(b"a" * (1024 * 1024))
    copy.write_bytes(cookie.read_bytes())
    category = replace(core.CATEGORY_BY_KEY["duplicateFiles"], paths=("~/Downloads", "~/Library/Caches/Microsoft Edge"))
    with patch.dict(core.CATEGORY_BY_KEY, {"duplicateFiles": category}):
        report = core.clean(
            [category],
            root=tmp_path,
            home=Path("/Users/tester"),
            execute=False,
            delete_mode="trash",
            operation_log=None,
        )
    assert report["items"] == []
    assert report["skipped_summary"]["by_reason"] == {"app-protected-data": 1}


def test_no_auth_scan_does_not_read_host_processes(tmp_path: Path) -> None:
    make_cache(tmp_path, "Library/Caches/Microsoft Edge/cache.bin")
    with patch.object(core, "run_text_command", side_effect=AssertionError("unexpected host process probe")):
        report = core.inspect_items(
            [core.CATEGORY_BY_KEY["userCache"]], root=tmp_path, home=Path("/Users/tester"), limit=-1
        )
    assert report["total_candidates"] == 1


def test_scan_uses_one_process_observation_for_multiple_cache_entries(tmp_path: Path) -> None:
    make_cache(tmp_path, "Library/Caches/Microsoft Edge/cache.bin")
    make_cache(tmp_path, "Library/Caches/LarkShell/cache.bin")
    with (
        patch.object(core, "run_text_command", return_value="") as probe,
        patch.object(core, "is_test_no_auth", return_value=False),
    ):
        report = core.inspect_items(
            [core.CATEGORY_BY_KEY["userCache"]], root=tmp_path, home=Path("/Users/tester"), limit=-1
        )
    assert report["total_candidates"] == 2
    probe.assert_called_once_with(["ps", "-axo", "comm="], timeout=2)


def test_execute_rechecks_application_activity_after_discovery(tmp_path: Path) -> None:
    cache = make_cache(tmp_path, "Library/Caches/Microsoft Edge/cache.bin")
    started = False

    def process_observation(*args: object, **kwargs: object) -> str:
        return "Microsoft Edge" if started else ""

    def start_after_scan(*args: object, **kwargs: object) -> dict[str, object]:
        nonlocal started
        started = True
        return {"status": "ready", "path": None, "rotated": False, "error": None}

    with (
        patch.object(core, "run_text_command", side_effect=process_observation),
        patch.object(core, "is_test_no_auth", return_value=False),
        patch.object(core, "preflight_operation_log", side_effect=start_after_scan),
    ):
        report = core.clean(
            [core.CATEGORY_BY_KEY["userCache"]],
            root=tmp_path,
            home=Path("/Users/tester"),
            execute=True,
            delete_mode="trash",
            operation_log="~/operations.jsonl",
        )
    assert cache.exists()
    assert report["deleted_count"] == 0
    assert report["skipped_summary"]["by_reason"]["app-running"] >= 1
    skipped = report["items"][0]
    assert skipped["review_evidence"]["protected"] is True
    assert skipped["review_evidence"]["default_selected"] is False
    assert skipped["review_evidence"]["why_not_default"] == "app-running"
