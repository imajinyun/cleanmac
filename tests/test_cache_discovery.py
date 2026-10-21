from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from cleancli import core, protection


def cache_file(root: Path, relative: str) -> Path:
    path = root / "Users/tester" / relative / "cache.bin"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"rebuildable")
    return path


@pytest.mark.parametrize(
    "relative",
    [
        "Library/Application Support/Trae CN/CachedData",
        "Library/Application Support/TRAE SOLO CN/Cache",
        "Library/Application Support/mira/Code Cache",
        "Library/Application Support/mira/GPUCache",
        "Library/Application Support/Codex/GraphiteDawnCache",
        "Library/Application Support/Codex/Cache",
        "Library/Application Support/Claude/GPUCache",
        "Library/Application Support/Doubao/GraphiteDawnCache",
        "Library/Application Support/Qianwen/GrShaderCache",
        "Library/Application Support/LarkInternational/ShaderCache",
        "Library/Application Support/LarkShell-PRIVATE-BOE/ShaderCache",
        "Library/Application Support/Code/GPUCache",
        "Library/Application Support/DBW/Service Worker/CacheStorage",
        "Library/Application Support/Google/Chrome/component_crx_cache",
        "Library/Application Support/Google/Chrome/Crashpad/completed",
        ".cache/puppeteer",
    ],
)
def test_screenshot_cache_variants_are_discovered(tmp_path: Path, relative: str) -> None:
    cache = cache_file(tmp_path, relative)
    report = core.inspect_items(list(core.CATEGORIES), root=tmp_path, home=Path("/Users/tester"), limit=-1)
    assert any(Path(row["path"]).resolve() in (cache.resolve(), *cache.resolve().parents) for row in report["items"])


@pytest.mark.parametrize(
    "relative",
    [
        "Library/Application Support/Google/Chrome/Profile 1/Service Worker/ScriptCache",
        "Library/Application Support/Microsoft Edge/Default/Service Worker/ScriptCache",
        "Library/Application Support/Code/Service Worker/ScriptCache",
    ],
)
def test_service_worker_scriptcache_is_never_a_cache_target(tmp_path: Path, relative: str) -> None:
    # MV3 extension service-worker bytecode: removing it breaks registered
    # workers even while the browser is closed (Mole #785, #964, #968).
    cache = cache_file(tmp_path, relative)
    report = core.inspect_items(list(core.CATEGORIES), root=tmp_path, home=Path("/Users/tester"), limit=-1)
    paths = {Path(row["path"]).resolve() for row in report["items"]}
    assert cache.resolve() not in paths
    assert cache.resolve().parent not in paths


def test_generic_ambiguous_cache_requires_a_regenerable_marker(tmp_path: Path) -> None:
    unmarked = cache_file(tmp_path, "Library/Application Support/UnknownVault/Cache")
    marked = cache_file(tmp_path, "Library/Application Support/UnknownElectron/Cache")
    cache_file(tmp_path, "Library/Application Support/UnknownElectron/GPUCache")
    report = core.inspect_items(list(core.CATEGORIES), root=tmp_path, home=Path("/Users/tester"), limit=-1)
    paths = {Path(row["path"]).resolve() for row in report["items"]}
    assert unmarked.resolve() not in paths
    assert marked.resolve() in paths


@pytest.mark.parametrize(
    "relative",
    [
        "Library/Application Support/Codex/Default/GPUCache",
        "Library/Application Support/Codex/Default/DawnGraphiteCache",
        "Library/Application Support/Codex/Default/DawnWebGPUCache",
        "Library/Application Support/Codex/Default/Code Cache",
        "Library/Application Support/Codex/Default/Cache",
        "Library/Application Support/Codex/Default/Partitions/codex-browser-app/GPUCache",
        "Library/Application Support/Codex/Default/Partitions/codex-browser-app/Code Cache",
        "Library/Application Support/Claude/Partitions/cowork-file-preview/Code Cache",
        "Library/Application Support/Claude/Partitions/cowork-file-preview/Cache",
        "Library/Application Support/Claude/Partitions/launch-preview-static/Code Cache",
    ],
)
def test_known_ai_app_profile_and_partition_caches_are_discovered(tmp_path: Path, relative: str) -> None:
    cache = cache_file(tmp_path, relative)
    report = core.inspect_items(
        [core.CATEGORY_BY_KEY["appSupportCaches"]], root=tmp_path, home=Path("/Users/tester"), limit=-1
    )
    paths = {Path(row["path"]).resolve() for row in report["items"]}
    assert cache.resolve() in paths or cache.resolve().parent in paths


@pytest.mark.parametrize(
    "relative",
    [
        "Library/Application Support/Codex/Shared Dictionary/cache",
        "Library/Application Support/Claude/Shared Dictionary/cache",
        "Library/Application Support/Codex/Default/Shared Dictionary/cache",
        "Library/Application Support/Codex/Default/Partitions/codex-browser-app/Shared Dictionary/cache",
        "Library/Application Support/Claude/Partitions/cowork-file-preview/Shared Dictionary/cache",
        "Library/Application Support/Claude/Partitions/launch-preview-static/Shared Dictionary/cache",
    ],
)
def test_chromium_shared_dictionary_caches_are_discovered(tmp_path: Path, relative: str) -> None:
    cache = cache_file(tmp_path, relative)
    report = core.inspect_items(
        [core.CATEGORY_BY_KEY["appSupportCaches"]], root=tmp_path, home=Path("/Users/tester"), limit=-1
    )
    paths = {Path(row["path"]).resolve() for row in report["items"]}
    assert cache.resolve() in paths or cache.resolve().parent in paths


def test_profile_descent_is_restricted_to_recognized_applications(tmp_path: Path) -> None:
    # The unknown app has a regenerable marker at its root, so root markers are
    # discovered, but its Default/ profile must not authorize deeper descent.
    root_marker = cache_file(tmp_path, "Library/Application Support/UnknownElectron/GPUCache")
    profile_marker = cache_file(tmp_path, "Library/Application Support/UnknownElectron/Default/GPUCache")
    partition_marker = cache_file(tmp_path, "Library/Application Support/UnknownElectron/Partitions/guest/Code Cache")
    report = core.inspect_items(
        [core.CATEGORY_BY_KEY["appSupportCaches"]], root=tmp_path, home=Path("/Users/tester"), limit=-1
    )
    paths = {Path(row["path"]).resolve() for row in report["items"]}
    assert root_marker.resolve() in paths
    assert profile_marker.resolve() not in paths
    assert partition_marker.resolve() not in paths


def test_profile_descent_does_not_follow_symlinked_partitions(tmp_path: Path) -> None:
    home = tmp_path / "Users/tester"
    support = home / "Library/Application Support"
    app = support / "Claude"
    app.mkdir(parents=True)
    outside = tmp_path / "outside"
    (outside / "GPUCache").mkdir(parents=True)
    (outside / "GPUCache/cache.bin").write_bytes(b"private")
    partitions = app / "Partitions"
    partitions.mkdir()
    (partitions / "guest").symlink_to(outside, target_is_directory=True)
    report = core.inspect_items(
        [core.CATEGORY_BY_KEY["appSupportCaches"]], root=tmp_path, home=Path("/Users/tester"), limit=-1
    )
    assert report["items"] == []
    assert (outside / "GPUCache/cache.bin").read_bytes() == b"private"


def test_profile_partition_storage_siblings_remain_protected(tmp_path: Path) -> None:
    cache = cache_file(
        tmp_path,
        "Library/Application Support/Claude/Partitions/launch-preview-static/Code Cache",
    )
    storage = (
        tmp_path
        / "Users/tester/Library/Application Support/Claude/Partitions/launch-preview-static/Local Storage/leveldb/0001.log"
    )
    storage.parent.mkdir(parents=True, exist_ok=True)
    storage.write_bytes(b"session")
    report = core.inspect_items(
        [core.CATEGORY_BY_KEY["appSupportCaches"]], root=tmp_path, home=Path("/Users/tester"), limit=-1
    )
    paths = {Path(row["path"]).resolve() for row in report["items"]}
    assert cache.resolve() in paths or cache.resolve().parent in paths
    assert storage.resolve() not in paths
    assert all("Local Storage" not in row["path"] for row in report["items"])


@pytest.mark.parametrize("redirect", ["app", "cache", "marker"])
def test_generic_cache_discovery_does_not_follow_symlink_authority(tmp_path: Path, redirect: str) -> None:
    support = tmp_path / "Users/tester/Library/Application Support"
    app = support / "UnknownElectron"
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "cache.bin").write_bytes(b"private")
    app.mkdir(parents=True)
    if redirect == "app":
        linked = support / "LinkedApp"
        linked.symlink_to(outside, target_is_directory=True)
        (outside / "GPUCache").mkdir()
    elif redirect == "cache":
        (app / "GPUCache").symlink_to(outside, target_is_directory=True)
    else:
        (app / "GPUCache").symlink_to(outside, target_is_directory=True)
        cache_file(tmp_path, "Library/Application Support/UnknownElectron/Cache")
    report = core.inspect_items(list(core.CATEGORIES), root=tmp_path, home=Path("/Users/tester"), limit=-1)
    assert report["items"] == []
    assert (outside / "cache.bin").read_bytes() == b"private"


def test_generic_cache_discovery_refuses_a_symlinked_library_ancestor(tmp_path: Path) -> None:
    home = tmp_path / "Users/tester"
    home.mkdir(parents=True)
    outside = tmp_path / "outside"
    cache = outside / "Application Support/Codex/GPUCache/cache.bin"
    cache.parent.mkdir(parents=True)
    cache.write_bytes(b"private")
    (home / "Library").symlink_to(outside, target_is_directory=True)
    report = core.inspect_items(
        [core.CATEGORY_BY_KEY["appSupportCaches"]], root=tmp_path, home=Path("/Users/tester"), limit=-1
    )
    assert report["items"] == []
    assert cache.read_bytes() == b"private"


def test_known_ai_cache_execution_preserves_credentials_and_sessions(tmp_path: Path) -> None:
    cache = cache_file(tmp_path, "Library/Application Support/Codex/Cache")
    sessions = cache_file(tmp_path, "Library/Application Support/Codex/Local Storage")
    credentials = tmp_path / "Users/tester/.codex/auth.json"
    credentials.parent.mkdir(parents=True)
    credentials.write_text('{"token":"secret"}', encoding="utf-8")
    assert "appSupportCaches" in core.CATEGORY_BY_KEY
    report = core.clean(
        [core.CATEGORY_BY_KEY["appSupportCaches"]],
        root=tmp_path,
        home=Path("/Users/tester"),
        execute=True,
        delete_mode="trash",
        operation_log=None,
    )
    assert report["deleted_count"] == 1
    assert not cache.exists()
    assert sessions.exists()
    assert credentials.exists()


def test_generic_ai_cache_preserves_application_specific_storage(tmp_path: Path) -> None:
    session = tmp_path / "Users/tester/Library/Application Support/Claude/Cache/storage/sessions.json"
    session.parent.mkdir(parents=True)
    session.write_bytes(b"session state")
    category = core.CATEGORY_BY_KEY["appSupportCaches"]
    inspected = core.inspect_items([category], root=tmp_path, home=Path("/Users/tester"), limit=-1)
    assert inspected["items"] == []
    assert inspected["skipped_summary"]["by_reason"] == {"app-protected-data": 1}
    with patch.object(core, "delete_path") as deletion:
        report = core.clean(
            [category], root=tmp_path, home=Path("/Users/tester"), execute=True, delete_mode="trash", operation_log=None
        )
    deletion.assert_not_called()
    assert report["deleted_count"] == 0
    assert session.read_bytes() == b"session state"


def test_delete_exit_preserves_storage_descendants_in_an_ai_cache_root(tmp_path: Path) -> None:
    cache = tmp_path / "Users/tester/Library/Application Support/Claude/Cache"
    session = cache / "storage/sessions.json"
    session.parent.mkdir(parents=True)
    session.write_bytes(b"session state")
    with pytest.raises(RuntimeError, match="protected user data"):
        core.assert_safe_to_delete(cache, root=tmp_path, home=Path("/Users/tester"))


def test_generic_cache_preserves_sensitive_descendants(tmp_path: Path) -> None:
    cache = cache_file(tmp_path, "Library/Application Support/Codex/Cache")
    (cache.parent / "Cookies").write_bytes(b"login")
    assert "appSupportCaches" in core.CATEGORY_BY_KEY
    report = core.inspect_items(
        [core.CATEGORY_BY_KEY["appSupportCaches"]], root=tmp_path, home=Path("/Users/tester"), limit=-1
    )
    assert all(Path(row["path"]).name != "Cookies" for row in report["items"])
    assert any(row["reason"] == "app-protected-data" for row in report["skipped"])


def test_generic_user_cache_cannot_bypass_browser_credential_protection(tmp_path: Path) -> None:
    cache = cache_file(tmp_path, "Library/Caches/Google/Chrome")
    (cache.parent / "Cookies").write_bytes(b"login")
    report = core.inspect_items(
        [core.CATEGORY_BY_KEY["userCache"]], root=tmp_path, home=Path("/Users/tester"), limit=-1
    )
    assert report["items"] == []
    assert report["skipped_summary"]["by_reason"] == {"app-protected-data": 1}


def test_cache_exception_does_not_override_another_protected_root(tmp_path: Path) -> None:
    nested = cache_file(tmp_path, "Library/Application Support/Codex/Cache/Library/Application Support/CloudDocs")
    assert protection.should_protect_data(nested) is True
    cookie = nested.parents[4] / "Cookies"
    cookie.write_bytes(b"login")
    assert protection.should_protect_data(cookie) is True


def test_cache_exception_does_not_relax_system_application_support() -> None:
    assert protection.should_protect_data(Path("/Library/Application Support/Codex/Cache/cache.bin")) is True


def test_canonical_user_logs_are_discovered(tmp_path: Path) -> None:
    log = tmp_path / "Users/tester/Library/Logs/CorpLink/fe/fe-renderer.old.log"
    log.parent.mkdir(parents=True)
    log.write_bytes(b"old log")
    report = core.inspect_items([core.CATEGORY_BY_KEY["userLogs"]], root=tmp_path, home=Path("/Users/tester"), limit=-1)
    assert report["total_bytes"] == 7
    assert any(Path(row["path"]).resolve() in log.resolve().parents for row in report["items"])
