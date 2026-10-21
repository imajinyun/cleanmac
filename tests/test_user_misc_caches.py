"""User-misc cache categories (Mole User essentials / App caches parity).

Covers recent-items lists, saved application state, identity/Siri caches,
age-gated CrashReporter reports, Messages preview/sticker caches (never
attachments), the bounded Finder ``.DS_Store`` provider, and the curated
Apple daemon sandboxed-container cache allowlist. The allowlist must not
loosen the generic ``com.apple`` container protection used by userAppCache.
"""

from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Any

import pytest

from cleancli import core, protection
from tests.helpers import make_sandbox, run_cli


@pytest.fixture(autouse=True)
def _test_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CLEANMAC_TEST_MODE", "1")
    monkeypatch.setenv("CLEANMAC_TEST_NO_AUTH", "1")


def _write(root: Path, relative: str) -> Path:
    path = root / "Users/tester" / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("x", encoding="utf-8")
    return path


def _inspect(root: Path, categories: str) -> tuple[list[dict[str, Any]], dict[str, str]]:
    result = run_cli(
        "--root",
        str(root),
        "--home",
        "/Users/tester",
        "--json",
        "clean",
        "inspect",
        "--categories",
        categories,
    )
    report = json.loads(result.stdout)
    items = [row for row in report["items"] if isinstance(row, dict)]
    skipped = {str(row["path"]): str(row["reason"]) for row in report.get("skipped", [])}
    return items, skipped


def _relpaths(root: Path, rows: list[dict[str, Any]]) -> set[str]:
    base = str(root / "Users/tester") + "/"
    return {str(row["path"]).split(base, 1)[-1] for row in rows}


RECENT_LIST_FILES = (
    "Library/Application Support/com.apple.sharedfilelist/com.apple.LSSharedFileList.RecentApplications.sfl2",
    "Library/Application Support/com.apple.sharedfilelist/com.apple.LSSharedFileList.RecentDocuments.sfl2",
    "Library/Application Support/com.apple.sharedfilelist/com.apple.LSSharedFileList.RecentServers.sfl2",
    "Library/Application Support/com.apple.sharedfilelist/com.apple.LSSharedFileList.RecentHosts.sfl2",
    "Library/Application Support/com.apple.sharedfilelist/com.apple.LSSharedFileList.RecentApplications.sfl",
    "Library/Application Support/com.apple.sharedfilelist/com.apple.LSSharedFileList.RecentDocuments.sfl",
    "Library/Application Support/com.apple.sharedfilelist/com.apple.LSSharedFileList.RecentServers.sfl",
    "Library/Application Support/com.apple.sharedfilelist/com.apple.LSSharedFileList.RecentHosts.sfl",
    "Library/Preferences/com.apple.recentitems.plist",
)

DAEMON_CACHE_FILES = (
    "Library/Containers/com.apple.wallpaper.agent/Data/Library/Caches/c",
    "Library/Containers/com.apple.mediaanalysisd/Data/Library/Caches/c",
    "Library/Containers/com.apple.mediaanalysisd/Data/tmp/t",
    "Library/Containers/com.apple.AppStore/Data/Library/Caches/c",
    "Library/Containers/com.apple.configurator.xpc.InternetService/Data/tmp/t",
    "Library/Containers/com.apple.wallpaper.extension.aerials/Data/tmp/t",
    "Library/Containers/com.apple.geod/Data/tmp/t",
    "Library/Containers/com.apple.stocks/Data/Library/Caches/c",
    "Library/Containers/com.apple.AvatarUI.AvatarPickerMemojiPicker/Data/Library/Caches/c",
    "Library/Containers/com.apple.AMPArtworkAgent/Data/Library/Caches/c",
    "Library/Containers/com.apple.CoreDevice.CoreDeviceService/Data/Library/Caches/c",
    "Library/Containers/com.apple.NeptuneOneExtension/Data/Library/Caches/c",
    "Library/Containers/com.apple.AppleMediaServicesUI.UtilityExtension/Data/tmp/t",
)


def test_recent_items_selects_only_exact_recent_lists() -> None:
    tmp, root, _home = make_sandbox()
    with tmp:
        for relative in RECENT_LIST_FILES:
            _write(root, relative)
        decoy = _write(
            root,
            "Library/Application Support/com.apple.sharedfilelist/com.apple.LSSharedFileList.ApplicationRecentDocuments-x.plist",
        )
        rows, skipped = _inspect(root, "recentItems")
        selected = _relpaths(root, rows)
        assert selected == set(RECENT_LIST_FILES)
        assert str(decoy) not in selected
        assert all(reason == "outside-provider-allowlist" for reason in skipped.values()) or not skipped


def test_saved_state_identity_suggestions_and_diagnostics() -> None:
    tmp, root, _home = make_sandbox()
    with tmp:
        state = _write(root, "Library/Saved Application State/com.example.app.savedState/window.plist")
        identity = _write(root, "Library/IdentityCaches/cache")
        suggestions = _write(root, "Library/Suggestions/learned")
        _write(root, "Library/DiagnosticReports/report.ips")

        rows, _ = _inspect(root, "savedAppState,identityCaches,siriSuggestions")
        selected = _relpaths(root, rows)
        assert str(state).split("/Users/tester/", 1)[-1] in selected
        assert str(identity).split("/Users/tester/", 1)[-1] in selected
        assert str(suggestions).split("/Users/tester/", 1)[-1] in selected

        logs, _ = _inspect(root, "userLogs")
        assert "Library/DiagnosticReports/report.ips" in _relpaths(root, logs)


def test_crash_reporter_only_old_files() -> None:
    tmp, root, _home = make_sandbox()
    with tmp:
        old = _write(root, "Library/Application Support/CrashReporter/old.crash")
        new = _write(root, "Library/Application Support/CrashReporter/new.crash")
        old_ts = time.time() - 40 * 86400
        os.utime(old, (old_ts, old_ts))
        rows, skipped = _inspect(root, "crashReporter")
        selected = _relpaths(root, rows)
        assert selected == {"Library/Application Support/CrashReporter/old.crash"}
        assert skipped[str(new)] == "too-new"


def test_message_caches_never_include_attachments() -> None:
    tmp, root, _home = make_sandbox()
    with tmp:
        leaves = [
            _write(root, "Library/Messages/StickerCache/sticker.bin"),
            _write(root, "Library/Messages/Caches/Previews/Attachments/a"),
            _write(root, "Library/Messages/Caches/Previews/StickerCache/s"),
        ]
        attachment = _write(root, "Library/Messages/Attachments/chat/photo.jpg")
        rows, _ = _inspect(root, "messageCaches")
        selected = _relpaths(root, rows)
        assert selected == {str(p).split("/Users/tester/", 1)[-1] for p in leaves}
        assert "Library/Messages/Attachments/chat/photo.jpg" not in selected
        assert attachment.exists()


def test_finder_metadata_is_bounded_and_pruned() -> None:
    tmp, root, _home = make_sandbox()
    with tmp:
        expected = [
            _write(root, "Documents/.DS_Store"),
            _write(root, "Documents/Work/.DS_Store"),
            _write(root, "a/b/c/d/.DS_Store"),
        ]
        # Depth 6 (file six levels below home) is out of bounds.
        _write(root, "a/b/c/d/e/.DS_Store")
        # Pruned trees.
        _write(root, "Library/Caches/.DS_Store")
        _write(root, "Library/Developer/Xcode/.DS_Store")
        _write(root, "Library/Application Support/MobileSync/Backup/uuid/.DS_Store")
        _write(root, ".Trash/.DS_Store")
        _write(root, "project/node_modules/pkg/.DS_Store")
        _write(root, "project/.git/objects/.DS_Store")
        # Protected data locations are filtered at discovery.
        _write(root, "Library/Messages/.DS_Store")
        # Symlinked directory must never be traversed.
        secret = root / "Users/other/secret"
        secret.mkdir(parents=True, exist_ok=True)
        (secret / ".DS_Store").write_text("x", encoding="utf-8")
        link = root / "Users/tester/linkdir"
        try:
            os.symlink(secret, link)
        except OSError:
            pass

        rows, skipped = _inspect(root, "finderMetadata")
        selected = _relpaths(root, rows)
        assert selected == {str(p).split("/Users/tester/", 1)[-1] for p in expected}
        assert not skipped
        assert (secret / ".DS_Store").exists()


def test_apple_daemon_container_caches_curated_allowlist() -> None:
    tmp, root, _home = make_sandbox()
    with tmp:
        for relative in DAEMON_CACHE_FILES:
            _write(root, relative)
        mail_cache = _write(root, "Library/Containers/com.apple.mail/Data/Library/Caches/m")
        mail_docs = _write(root, "Library/Containers/com.apple.mail/Data/Documents/secret")

        rows, skipped = _inspect(root, "appleDaemonContainerCaches")
        selected = _relpaths(root, rows)
        assert selected == set(DAEMON_CACHE_FILES)
        assert str(mail_cache) not in [str(r["path"]) for r in rows]
        assert str(mail_docs) not in [str(r["path"]) for r in rows]
        assert not skipped
        assert mail_cache.exists() and mail_docs.exists()


def test_generic_user_app_cache_still_skips_apple_daemon_containers() -> None:
    tmp, root, _home = make_sandbox()
    with tmp:
        daemon_file = _write(root, "Library/Containers/com.apple.AppStore/Data/Library/Caches/c")
        third_party = _write(root, "Library/Containers/com.example.vendor/Data/Library/Caches/c")
        rows, skipped = _inspect(root, "userAppCache")
        selected_paths = {str(r["path"]) for r in rows}
        assert str(third_party) in selected_paths
        assert str(daemon_file) not in selected_paths
        assert skipped[str(daemon_file)] == "protected-container-data"


def test_new_categories_are_opt_in_with_expected_providers() -> None:
    by_key = core.CATEGORY_BY_KEY
    for key in (
        "recentItems",
        "savedAppState",
        "identityCaches",
        "siriSuggestions",
        "crashReporter",
        "messageCaches",
        "finderMetadata",
        "appleDaemonContainerCaches",
    ):
        category = by_key[key]
        assert category.advanced is True
        assert category.default is False
        assert category.recommended is False
    assert by_key["finderMetadata"].provider == "finder-metadata"
    assert by_key["appleDaemonContainerCaches"].provider == "apple-daemon-container-caches"
    assert by_key["crashReporter"].default_older_than_days == 30
    assert any("DiagnosticReports" in path for path in by_key["userLogs"].paths)


def test_protection_predicates_pin_exact_leaves() -> None:
    def home(relative: str) -> Path:
        return Path("/Users/tester") / relative

    assert protection.is_recent_items_file(home(RECENT_LIST_FILES[0]))
    assert not protection.is_recent_items_file(home("Library/Application Support/com.apple.sharedfilelist/other.plist"))

    assert protection.is_messages_regenerable_cache(home("Library/Messages/StickerCache/x"))
    assert protection.is_messages_regenerable_cache(home("Library/Messages/Caches/Previews/Attachments/x"))
    assert not protection.is_messages_regenerable_cache(home("Library/Messages/Attachments/chat/x"))

    assert protection.is_allowed_apple_daemon_container_cache(
        home("Library/Containers/com.apple.geod/Data/tmp/scratch")
    )
    assert protection.is_allowed_apple_daemon_container_cache(
        home("Library/Containers/com.apple.AppStore/Data/Library/Caches/cache")
    )
    assert not protection.is_allowed_apple_daemon_container_cache(
        home("Library/Containers/com.apple.mail/Data/Library/Caches/cache")
    )
    assert not protection.is_allowed_apple_daemon_container_cache(
        home("Library/Containers/com.apple.geod/Data/Documents/route")
    )
