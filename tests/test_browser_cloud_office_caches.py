"""Browser, cloud-drive, and office cache alignment with Mole.

Pins three behaviors:

* Chromium shader/GPU/on-device-model leaves are reached by the curated
  browser categories while Service Worker ScriptCache is never a target
  (Mole #785, #964, #968);
* ``browserServiceWorkerCaches`` enumerates CacheStorage per origin and keeps
  protected offline web-editor origins;
* additional browser/cloud/office categories stay advanced opt-in caches and
  never touch profiles, mailboxes, documents, or synced folders.
"""

from __future__ import annotations

import json
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


def _rel(path: Path) -> str:
    return str(path).split("/Users/tester/", 1)[-1]


def test_chrome_completed_leaves_and_scriptcache_never_target() -> None:
    tmp, root, _home = make_sandbox()
    with tmp:
        expected = [
            _write(root, "Library/Application Support/Google/Chrome/Default/DawnCache/d"),
            _write(root, "Library/Application Support/Google/Chrome/Default/GrShaderCache/g"),
            _write(root, "Library/Application Support/Google/Chrome/GrShaderCache/g"),
            _write(root, "Library/Application Support/Google/Chrome/OptGuideOnDeviceModel/m"),
            _write(root, "Library/Application Support/Google/Chrome/optimization_guide_model_store/m"),
            _write(root, "Library/Application Support/Google/GoogleUpdater/crx_cache/c.crx"),
            _write(root, "Library/Application Support/Google/GoogleUpdater/old.old"),
            _write(root, "Library/Caches/Google/Chrome/Default/Media Cache/m"),
        ]
        scriptcache = _write(
            root, "Library/Application Support/Google/Chrome/Default/Service Worker/ScriptCache/ext/code"
        )
        cookies = _write(root, "Library/Application Support/Google/Chrome/Default/Cookies")

        rows, skipped = _inspect(root, "chrome")
        selected = _relpaths(root, rows)
        for path in expected:
            assert _rel(path) in selected
        assert not any("scriptcache" in path.lower() for path in selected)
        assert _rel(cookies) not in selected
        assert str(scriptcache) not in [str(row["path"]) for row in rows]
        # ScriptCache is not a candidate, so it is not merely policy-skipped.
        assert all("scriptcache" not in path.lower() for path in skipped)


def test_firefox_cache_tree_leaves() -> None:
    tmp, root, _home = make_sandbox()
    with tmp:
        # The Firefox rule targets the regenerable cache2/entries leaf directly
        # (cache.bin is an immediate child) plus shader/startup cache leaves.
        expected = [
            _write(root, "Library/Caches/Firefox/Profiles/dev.default/cache2/entries/e"),
            _write(root, "Library/Caches/Firefox/Profiles/dev.default/shader-cache/s"),
            _write(root, "Library/Caches/Firefox/Profiles/dev.default/startupCache/s"),
            _write(root, "Library/Application Support/Firefox/Profiles/dev.default/cache2/entries/e"),
            _write(root, "Library/Application Support/Firefox/Profiles/dev.default/startupCache/s"),
        ]
        profile = _write(root, "Library/Application Support/Firefox/Profiles/dev.default/logins.json")
        rows, _ = _inspect(root, "firefox")
        selected = _relpaths(root, rows)
        for path in expected:
            assert _rel(path) in selected
        assert _rel(profile) not in selected


def test_generic_browser_category_locks_service_worker_cachestorage() -> None:
    # The generic chrome category keeps Service Worker CacheStorage visible but
    # locked (app-protected-data); only browserServiceWorkerCaches removes it.
    tmp, root, _home = make_sandbox()
    with tmp:
        origin = _write(
            root,
            "Library/Application Support/Google/Chrome/Default/Service Worker/CacheStorage/abc/1/body",
        )
        rows, skipped = _inspect(root, "chrome")
        assert all("service worker" not in str(r["path"]).lower() for r in rows)
        assert skipped, "CacheStorage must remain visible as a locked skip"
        assert all(reason == "app-protected-data" for reason in skipped.values())
        # The origin cache is never deleted through the generic category.
        assert origin.exists()


def test_browser_service_worker_provider_enumerates_origins() -> None:
    tmp, root, _home = make_sandbox()
    with tmp:
        hashed = _write(
            root,
            "Library/Application Support/Google/Chrome/Default/Service Worker/CacheStorage/abc/1/body",
        )
        protected = _write(
            root,
            "Library/Application Support/Google/Chrome/Default/Service Worker/"
            "CacheStorage/https_docs.google.com_0/2/body",
        )
        arc = _write(
            root,
            "Library/Application Support/Arc/User Data/Profile 1/Service Worker/CacheStorage/xyz/9/body",
        )
        opera = _write(
            root,
            "Library/Application Support/com.operasoftware.Opera/Service Worker/CacheStorage/op/3/body",
        )
        # Unknown app with the same layout is outside the provider allowlist.
        stranger = _write(root, "Library/Application Support/SomeApp/Service Worker/CacheStorage/s/1/body")
        # A CacheStorage root or origin dir is never itself a depth-2 target.
        rows, skipped = _inspect(root, "browserServiceWorkerCaches")
        selected_paths = {str(row["path"]) for row in rows}
        for path in (hashed, arc, opera):
            assert str(path) in selected_paths
        assert str(protected) not in selected_paths
        assert str(stranger) not in selected_paths
        assert all("docs.google.com" not in path for path in selected_paths)
        assert protected.exists()
        assert not any(str(row["path"]).endswith("CacheStorage/abc") for row in rows)
        assert not skipped


def test_service_worker_provider_skips_symlinked_origin(tmp_path: Path) -> None:
    home = tmp_path / "Users/tester"
    outside = tmp_path / "outside-origin"
    outside.mkdir(parents=True)
    (outside / "body").write_text("secret")
    storage = home / "Library/Application Support/Google/Chrome/Default/Service Worker/CacheStorage"
    storage.mkdir(parents=True)
    try:
        (storage / "evil").symlink_to(outside, target_is_directory=True)
    except OSError:
        pytest.skip("symlinks unavailable")
    targets = core.browser_service_worker_cache_dirs(home)
    assert targets == []


def test_extra_browser_categories_select_curated_leaves() -> None:
    tmp, root, _home = make_sandbox()
    with tmp:
        expected = [
            _write(root, "Library/Caches/com.apple.Safari/Cache.db"),
            _write(root, "Library/Caches/Chromium/c"),
            _write(root, "Library/Caches/company.thebrowser.dia/c"),
            _write(root, "Library/Application Support/Dia/User Data/GPUPersistentCache/g"),
            _write(root, "Library/Application Support/Dia/User Data/Profile/GPUCache/g"),
            _write(root, "Library/Caches/net.imput.helium/c"),
            _write(root, "Library/Application Support/net.imput.helium/ShaderCache/s"),
            _write(root, "Library/Caches/Yandex/YandexBrowser/c"),
            _write(root, "Library/Application Support/Yandex/YandexBrowser/ShaderCache/s"),
            _write(root, "Library/Caches/com.vivaldi.Vivaldi/c"),
            _write(root, "Library/Application Support/Vivaldi/ShaderCache/s"),
            _write(root, "Library/Caches/Comet/c"),
            _write(root, "Library/Caches/com.kagi.kagimacOS/c"),
            _write(root, "Library/Caches/zen/c"),
            _write(root, "Library/Caches/com.tencent.QQBrowser3/c"),
            _write(root, "Library/Application Support/QQBrowser3/component_crx_cache/c"),
        ]
        # Safari profile/website data and browser cookies must stay untouched.
        protected_files = [
            _write(root, "Library/Safari/History.db"),
            _write(root, "Library/Containers/com.apple.Safari/Data/Library/Cookies/Cookies.binarycookies"),
            _write(root, "Library/WebKit/com.apple.Safari/WebsiteData/LocalStorage/site.localstorage"),
            _write(root, "Library/Application Support/Vivaldi/Default/Cookies"),
        ]
        rows, _ = _inspect(
            root,
            "safari,chromium,dia,helium,yandex,vivaldi,comet,orion,zen,qqBrowser3",
        )
        selected = _relpaths(root, rows)
        for path in expected:
            assert _rel(path) in selected
        selected_paths = {str(row["path"]) for row in rows}
        for path in protected_files:
            assert str(path) not in selected_paths


def test_cloud_storage_categories() -> None:
    tmp, root, _home = make_sandbox()
    with tmp:
        expected = [
            _write(root, "Library/Caches/com.getdropbox.dropbox/c"),
            _write(root, "Library/Caches/com.dropbox.Dropbox/c"),
            _write(root, "Library/Caches/com.baidu.netdisk/c"),
            _write(root, "Library/Caches/com.alibaba.teambitiondisk/c"),
            _write(root, "Library/Caches/com.box.desktop/c"),
            _write(root, "Library/Application Support/Dropbox/Cache/c"),
        ]
        config = _write(root, "Library/Application Support/Dropbox/info.json")
        rows, _ = _inspect(root, "dropbox,baiduNetdisk,teambitionDisk,box")
        selected = _relpaths(root, rows)
        for path in expected:
            assert _rel(path) in selected
        assert _rel(config) not in selected


def test_office_mail_categories_keep_documents_and_mailboxes() -> None:
    tmp, root, _home = make_sandbox()
    with tmp:
        expected = [
            _write(root, "Library/Caches/com.microsoft.Word/c"),
            _write(root, "Library/Caches/com.microsoft.Excel/c"),
            _write(root, "Library/Caches/com.microsoft.Powerpoint/c"),
            _write(root, "Library/Caches/com.microsoft.Outlook/c"),
            _write(root, "Library/Containers/com.microsoft.Word/Data/tmp/scratch"),
            _write(root, "Library/Containers/com.microsoft.Word/Data/Library/Logs/word.log"),
            _write(root, "Library/Containers/com.microsoft.Excel/Data/tmp/scratch"),
            _write(root, "Library/Containers/com.microsoft.Word/Data/Library/Caches/c"),
            _write(root, "Library/Caches/com.apple.iWork.Pages/c"),
            _write(root, "Library/Caches/com.apple.iWork.Keynote/c"),
            _write(root, "Library/Caches/com.kingsoft.wpsoffice.mac/c"),
            _write(root, "Library/Caches/org.mozilla.thunderbird/c"),
            _write(root, "Library/Caches/com.apple.mail/c"),
        ]
        protected_files = [
            _write(root, "Library/Containers/com.microsoft.Word/Data/Documents/draft.docx"),
            _write(root, "Library/Containers/com.microsoft.Word/Data/Library/Preferences/auto.recovery"),
            _write(root, "Library/Thunderbird/Profiles/ab/Mail/INBOX"),
            _write(root, "Library/Mail/metadata"),
            _write(root, "Library/Mail Downloads/attach.zip"),
        ]
        rows, _ = _inspect(root, "microsoftOffice,microsoftOutlook,iwork,wps,thunderbird,mailCache")
        selected_paths = {str(row["path"]) for row in rows}
        for path in expected:
            assert str(path) in selected_paths
        for path in protected_files:
            assert str(path) not in selected_paths
        assert all(path.exists() for path in protected_files)


def test_new_categories_are_advanced_opt_in() -> None:
    keys = (
        "browserServiceWorkerCaches",
        "safari",
        "chromium",
        "dia",
        "helium",
        "yandex",
        "vivaldi",
        "comet",
        "orion",
        "zen",
        "qqBrowser3",
        "baiduNetdisk",
        "teambitionDisk",
        "box",
        "iwork",
        "wps",
        "thunderbird",
        "mailCache",
    )
    for key in keys:
        category = core.CATEGORY_BY_KEY[key]
        assert category.advanced is True
        assert category.default is False
        assert category.recommended is False
    assert core.CATEGORY_BY_KEY["browserServiceWorkerCaches"].provider == "browser-service-worker-caches"


def test_service_worker_predicates_pin_shapes() -> None:
    good = Path("/Users/t/Library/Application Support/Google/Chrome/Default/Service Worker/CacheStorage/origin/cache")
    assert protection.is_browser_service_worker_cache(good)
    assert not protection.is_protected_service_worker_origin(good)
    editor = Path(
        "/Users/t/Library/Application Support/Google/Chrome/Default/"
        "Service Worker/CacheStorage/https_www.figma.com_0/cache"
    )
    assert protection.is_browser_service_worker_cache(editor)
    assert protection.is_protected_service_worker_origin(editor)
    # ScriptCache and CacheStorage root/origin dirs never match.
    assert not protection.is_browser_service_worker_cache(
        Path("/Users/t/Library/Application Support/Google/Chrome/Default/Service Worker/ScriptCache/a/b")
    )
    assert not protection.is_browser_service_worker_cache(
        Path("/Users/t/Library/Application Support/Google/Chrome/Default/Service Worker/CacheStorage/origin")
    )
    # Unknown application family.
    assert not protection.is_browser_service_worker_cache(
        Path("/Users/t/Library/Application Support/SomeApp/Service Worker/CacheStorage/o/c")
    )
