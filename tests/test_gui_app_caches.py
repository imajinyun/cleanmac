"""Long-tail GUI application cache alignment with Mole section 7.

Covers ``clean_user_gui_applications`` parity:

* communication, AI, creative, productivity, media/video player, download
  manager, gaming, translation, screenshot, mail, shell/system, notes,
  launcher, and remote-desktop cache categories are registered as advanced
  opt-in caches scoped to regenerable leaves;
* documents, accounts, databases, preferences, installed games, and
  downloaded media stay protected by rule ``protected_patterns``;
* the ``neatDownloads`` provider enumerates only numbered Neat Download
  Manager segment directories whose ``seg.x0`` marker is at least 30 days
  old, never ``NeatDB.db`` or resumable downloads.
"""

from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Any

import pytest

from cleancli import app_activity, core, neatdm, protection
from tests.helpers import make_sandbox, run_cli

NEW_CATEGORY_KEYS = (
    # communication
    "wecom",
    "tencentMeeting",
    "skype",
    "legcord",
    # AI assistants
    "chatgpt",
    "claudeDesktop",
    "lmStudio",
    # creative tools
    "premierePro",
    "cinema4d",
    "autodeskCaches",
    # productivity
    "miaoYan",
    "klee",
    "ora",
    "filo",
    "flomo",
    "quark",
    "netNewsWire",
    "mindNode",
    "kaku",
    "spacedrive",
    "folo",
    # music players
    "neteaseMusic",
    "qqMusic",
    "kugouMusic",
    "kuwoMusic",
    "appleTV",
    "plex",
    # video players
    "iina",
    "mpv",
    "iqiyi",
    "tencentVideo",
    "bilibili",
    "douyu",
    "huya",
    "senPlayer",
    "stremio",
    # download managers
    "aria2gui",
    "transmission",
    "qbittorrent",
    "downie",
    "pacifist",
    "neatDownloads",
    # gaming
    "steam",
    "epicGames",
    "battleNet",
    "eaApp",
    "gogGalaxy",
    "riotGames",
    "minecraft",
    "lunarClient",
    "pcsx2",
    "rpcs3",
    # translation
    "youdaoDict",
    "eudict",
    "bobTranslate",
    # screenshots / mail / tasks
    "camo",
    "xnip",
    "sparkMail",
    "airmail",
    "anydo",
    # shell and system utilities
    "ghostty",
    "inputSourcePro",
    "wakatime",
    "weType",
    "mihomoParty",
    "stash",
    # notes / launchers / remote desktop
    "logseq",
    "yinxiang",
    "theUnarchiver",
    "teamViewer",
    "anyDesk",
    "toDesk",
    "sunlogin",
)


@pytest.fixture(autouse=True)
def _test_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CLEANMAC_TEST_MODE", "1")
    monkeypatch.setenv("CLEANMAC_TEST_NO_AUTH", "1")


def _write(root: Path, relative: str, *, mtime_days: float | None = None) -> Path:
    path = root / "Users/tester" / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("x", encoding="utf-8")
    if mtime_days is not None:
        stamp = time.time() - mtime_days * 86400
        os.utime(path, (stamp, stamp))
    return path


def _mkdir(root: Path, relative: str) -> Path:
    path = root / "Users/tester" / relative
    path.mkdir(parents=True, exist_ok=True)
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


# --- registration ---------------------------------------------------------


def test_gui_app_categories_registered_as_advanced_opt_in() -> None:
    from cleancli.protection_data import APP_CLEANUP_RULES

    assert len(NEW_CATEGORY_KEYS) == 73
    for key in NEW_CATEGORY_KEYS:
        category = core.CATEGORY_BY_KEY[key]
        assert category.advanced is True
        assert category.default is False
        assert category.recommended is False
        assert category.risk == "medium"
        assert category.process_guard
        if key != "neatDownloads":
            assert category.paths == APP_CLEANUP_RULES[key]["paths"]
            assert category.title == APP_CLEANUP_RULES[key]["title"]
    neat = core.CATEGORY_BY_KEY["neatDownloads"]
    assert neat.provider == "neatdm-stale-segments"
    assert neat.delete_target is True
    assert neat.paths == ()


def test_process_aliases_cover_localized_and_helper_binaries() -> None:
    cases = {
        "WeCom": ("/Applications/企业微信.app/Contents/MacOS/企业微信", "WeCom Helper (GPU)"),
        "Tencent Meeting": ("/Applications/TencentMeeting.app/Contents/MacOS/TencentMeeting",),
        "Autodesk": ("/Applications/Autodesk/AcCoreConsole", "/Applications/Autodesk/ADPClientService"),
        "Premiere Pro": (
            "/Applications/Adobe Premiere Pro 2025/Adobe Premiere Pro 2025.app/Contents/MacOS/Adobe Premiere Pro 2025",
        ),
        "Steam": ("steam_osx",),
        "Riot Games": ("RiotClientServices",),
        "Downie": ("Downie 4",),
        "Sunlogin": ("SunloginClient_Desktop",),
        "Yinxiang Note": ("印象笔记",),
        "Bilibili": ("哔哩哔哩",),
    }
    for guard, executables in cases.items():
        for executable in executables:
            assert app_activity.executable_matches(executable, guard), (guard, executable)


# --- NeatDM provider ------------------------------------------------------


def _neatdm_root(home: Path) -> Path:
    return home / neatdm.NEATDM_ROOT


def _segment(root: Path, home: Path, name: str, *, age_days: float | None) -> Path:
    segment = _neatdm_root(home) / name
    segment.mkdir(parents=True, exist_ok=True)
    marker = segment / "seg.x0"
    marker.write_text("part", encoding="utf-8")
    if age_days is not None:
        stamp = time.time() - age_days * 86400
        os.utime(marker, (stamp, stamp))
    return segment


def test_neatdm_provider_only_lists_old_numbered_segments(tmp_path: Path) -> None:
    home = tmp_path / "tester"
    stale = _segment(tmp_path, home, "1001", age_days=45)
    _segment(tmp_path, home, "1002", age_days=2)
    # Numbered but without the seg.x0 marker is not a removable segment tree.
    other = _neatdm_root(home) / "2002"
    other.mkdir(parents=True)
    (other / "notes.txt").write_text("n", encoding="utf-8")
    # Non-numeric entries and the history database always stay.
    (_neatdm_root(home) / "NeatDB.db").write_text("history", encoding="utf-8")

    targets = neatdm.stale_segment_dirs(home)
    assert targets == [stale]
    assert neatdm.is_stale_segment_candidate(stale)
    assert not neatdm.is_stale_segment_candidate(_neatdm_root(home) / "1002")
    assert not neatdm.is_stale_segment_candidate(other)
    assert not neatdm.is_stale_segment_candidate(_neatdm_root(home) / "NeatDB.db")


def test_neatdm_symlinked_segment_fails_closed(tmp_path: Path) -> None:
    home = tmp_path / "tester"
    root = _neatdm_root(home)
    root.mkdir(parents=True)
    outside = tmp_path / "outside" / "3003"
    outside.mkdir(parents=True)
    (outside / "seg.x0").write_text("p", encoding="utf-8")
    old = time.time() - 60 * 86400
    os.utime(outside / "seg.x0", (old, old))
    try:
        (root / "3003").symlink_to(outside, target_is_directory=True)
    except OSError:
        pytest.skip("symlinks unavailable")
    assert neatdm.stale_segment_dirs(home) == []
    assert not neatdm.is_stale_segment_candidate(root / "3003")


def test_neatdm_home_root_derivation(tmp_path: Path) -> None:
    segment = tmp_path / "h" / neatdm.NEATDM_ROOT / "42"
    assert neatdm.home_root_for_candidate(segment) == tmp_path / "h"
    assert neatdm.home_root_for_candidate(tmp_path / "relative" / "42") is None


@pytest.mark.parametrize("ancestor", ("Library", "Library/Application Support", str(neatdm.NEATDM_ROOT)))
def test_neatdm_replay_rejects_symlinked_ancestors(tmp_path: Path, ancestor: str) -> None:
    home = tmp_path / "tester"
    segment = _segment(tmp_path, home, "42", age_days=45)
    linked = home / ancestor
    relocated = tmp_path / "relocated"
    linked.rename(relocated)
    linked.symlink_to(relocated, target_is_directory=True)

    assert neatdm.stale_segment_dirs(home) == []
    assert not neatdm.is_stale_segment_candidate(segment)
    assert core.category_policy_reason(core.CATEGORY_BY_KEY["neatDownloads"], segment, root=tmp_path) == (
        "outside-provider-allowlist"
    )


def test_neatdm_replay_rechecks_marker_age(tmp_path: Path) -> None:
    home = tmp_path / "tester"
    segment = _segment(tmp_path, home, "42", age_days=45)
    assert neatdm.is_stale_segment_candidate(segment)
    os.utime(segment / "seg.x0", None)
    assert not neatdm.is_stale_segment_candidate(segment)


def test_app_protection_rechecks_new_offline_data(tmp_path: Path) -> None:
    storage = tmp_path / "Library/Application Support/Spotify/Storage"
    storage.mkdir(parents=True)
    candidate = storage / "index.dat"
    candidate.write_text("cache", encoding="utf-8")
    assert protection.app_protected_data_reason("spotify", candidate) is None

    (storage / "offline.file").write_text("offline music", encoding="utf-8")
    assert protection.app_protected_data_reason("spotify", candidate) == "app-protected-data"


def test_generic_cache_protection_preserves_offline_siblings(tmp_path: Path) -> None:
    storage = tmp_path / "Library/Application Support/Spotify/Storage"
    storage.mkdir(parents=True)
    candidate = storage / "index.dat"
    candidate.write_text("cache", encoding="utf-8")
    (storage / "offline.file").write_text("offline music", encoding="utf-8")

    assert protection.cache_protected_data_reason(candidate, home_root=tmp_path) == "app-protected-data"


def test_cache_bundle_suffix_is_not_a_protected_document(tmp_path: Path) -> None:
    cache = tmp_path / "Library/Caches/com.danielhooper.principle"
    cache.mkdir(parents=True)
    candidate = cache / "cache.bin"
    candidate.write_text("cache", encoding="utf-8")
    assert protection.app_protected_data_reason("principle", candidate) is None
    assert protection.cache_protected_data_reason(candidate, home_root=tmp_path) is None

    (cache / "animation.principle").write_text("project", encoding="utf-8")
    assert protection.app_protected_data_reason("principle", candidate) == "app-protected-data"
    assert protection.cache_protected_data_reason(candidate, home_root=tmp_path) == "app-protected-data"


def test_cli_neatdm_inspect_lists_only_stale_segments() -> None:
    tmp, root, home = make_sandbox()
    with tmp:
        home_root = root / "Users" / "tester"
        stale = _segment(root, home_root, "1001", age_days=45)
        fresh = _segment(root, home_root, "1002", age_days=1)
        db = _neatdm_root(home_root) / "NeatDB.db"
        db.write_text("history", encoding="utf-8")

        items, _ = _inspect(root, "neatDownloads")
        listed = {str(row["path"]) for row in items}
        assert str(stale) in listed
        assert str(fresh) not in listed
        assert str(db) not in listed


# --- protected descendants ------------------------------------------------


def test_protected_patterns_keep_user_data_and_installed_games(tmp_path: Path) -> None:
    # A hypothetical Steam-root candidate containing installed games must be
    # refused even though it overlaps the cache rule paths.
    steam = tmp_path / "Library/Application Support/Steam"
    (steam / "steamapps/common/Counter-Strike").mkdir(parents=True)
    (steam / "htmlcache").mkdir(parents=True)
    assert protection.app_protected_data_reason("steam", steam) == "app-protected-data"

    minecraft = tmp_path / "Library/Application Support/minecraft"
    (minecraft / "saves/World").mkdir(parents=True)
    (minecraft / "webcache").mkdir(parents=True)
    assert protection.app_protected_data_reason("minecraft", minecraft) == "app-protected-data"

    qqmusic = tmp_path / "Library/Containers/com.tencent.QQMusicMac/Data/Library/Application Support/QQMusicMac"
    (qqmusic / "iDownloadProxy/album").mkdir(parents=True)
    (qqmusic / "iTemp").mkdir(parents=True)
    assert protection.app_protected_data_reason("qqMusic", qqmusic) == "app-protected-data"

    # Legacy LM Studio model home must never be treated as cache content.
    lm_cache = tmp_path / "Library/Caches/com.lmstudio.lmstudio"
    lm_cache.mkdir(parents=True)
    assert protection.app_protected_data_reason("lmStudio", lm_cache) is None
    legacy = tmp_path / ".cache/lm-studio"
    (legacy / "models").mkdir(parents=True)
    assert protection.app_protected_data_reason("lmStudio", legacy) == "app-protected-data"


# --- CLI leaf scoping -----------------------------------------------------


def test_steam_category_scopes_to_cache_leaves() -> None:
    tmp, root, _home = make_sandbox()
    with tmp:
        cache_files = [
            _write(root, "Library/Caches/com.valvesoftware.steam/a.tmp"),
            _write(root, "Library/Application Support/Steam/htmlcache/index"),
            _write(root, "Library/Application Support/Steam/appcache/appinfo.vdf"),
            _write(root, "Library/Application Support/Steam/depotcache/123.blob"),
            _write(root, "Library/Application Support/Steam/steamapps/shadercache/fxc.bin"),
            _write(root, "Library/Application Support/Steam/logs/bootstrap_log.txt"),
        ]
        game = _write(root, "Library/Application Support/Steam/steamapps/common/Counter-Strike/csgo/bin/x")
        manifest = _write(root, "Library/Application Support/Steam/steamapps/appmanifest_730.acf")
        userdata = _write(root, "Library/Application Support/Steam/userdata/123/localconfig.vdf")

        rows, _ = _inspect(root, "steam")
        listed = _relpaths(root, rows)
        for path in cache_files:
            assert _rel(path) in listed
        assert _rel(game) not in listed
        assert _rel(manifest) not in listed
        assert _rel(userdata) not in listed


def test_qqmusic_container_leaves_protect_offline_downloads() -> None:
    tmp, root, _home = make_sandbox()
    with tmp:
        caches = [
            _write(root, "Library/Caches/com.tencent.QQMusicMac/c"),
            _write(root, "Library/Containers/com.tencent.QQMusicMac/Data/Library/Caches/c"),
            _write(
                root,
                "Library/Containers/com.tencent.QQMusicMac/Data/Library/Application Support/QQMusicMac/iTemp/t",
            ),
            _write(
                root,
                "Library/Containers/com.tencent.QQMusicMac/Data/Library/Application Support/QQMusicMac/iLog/l",
            ),
        ]
        offline = _write(
            root,
            "Library/Containers/com.tencent.QQMusicMac/Data/Library/Application Support/QQMusicMac/iDownloadProxy/song.ogg",
        )
        rows, _ = _inspect(root, "qqMusic")
        listed = _relpaths(root, rows)
        for path in caches:
            assert _rel(path) in listed
        assert _rel(offline) not in listed


def test_podcasts_tmp_leaves_are_glob_scoped() -> None:
    tmp, root, _home = make_sandbox()
    with tmp:
        streamed = _write(root, "Library/Containers/com.apple.podcasts/Data/tmp/StreamedMedia/abc")
        artwork = _write(root, "Library/Containers/com.apple.podcasts/Data/tmp/cover.heic")
        image = _write(root, "Library/Containers/com.apple.podcasts/Data/tmp/art.img")
        download = _write(root, "Library/Containers/com.apple.podcasts/Data/tmp/xCFNetworkDownload123.tmp")
        unrelated = _write(root, "Library/Containers/com.apple.podcasts/Data/tmp/keep.txt")

        rows, _ = _inspect(root, "podcasts")
        listed = _relpaths(root, rows)
        for path in (streamed, artwork, image, download):
            assert _rel(path) in listed
        assert _rel(unrelated) not in listed


def test_extended_existing_rules_reach_mole_cache_ids() -> None:
    tmp, root, _home = make_sandbox()
    with tmp:
        warp_log = _write(root, "Library/Logs/warp.log")
        warp_crash = _write(root, "Library/Caches/SentryCrash/Warp/report.json")
        dingtalk_ids = [
            _write(root, "Library/Caches/dd.work.exclusive4aliding/c"),
            _write(root, "Library/Caches/com.alibaba.AliLang.osx/c"),
            _write(root, "Library/Application Support/iDingTalk/log/a.log"),
            _write(root, "Library/Application Support/iDingTalk/holmeslogs/b.log"),
        ]
        feishu_glob = _write(root, "Library/Caches/com.feishu.darwin/c")
        bear_legacy = _write(root, "Library/Caches/com.bear-writer.5/c")
        cleanshot_glob = _write(root, "Library/Caches/com.cleanshot.macos/c")
        blender_id = _write(root, "Library/Caches/org.blenderfoundation.blender/c")
        davinci_id = _write(root, "Library/Caches/com.blackmagic-design.DaVinciResolve/c")
        folx_id = _write(root, "Library/Caches/com.folx.Folx5/c")

        warp_rows, _ = _inspect(root, "warp")
        warp_listed = _relpaths(root, warp_rows)
        assert _rel(warp_log) in warp_listed
        assert _rel(warp_crash) in warp_listed

        for categories, paths in (
            ("dingTalk", dingtalk_ids),
            ("feishu", [feishu_glob]),
            ("bear", [bear_legacy]),
            ("cleanShot", [cleanshot_glob]),
            ("blender", [blender_id]),
            ("davinciResolve", [davinci_id]),
            ("folx", [folx_id]),
        ):
            rows, _ = _inspect(root, categories)
            listed = _relpaths(root, rows)
            for path in paths:
                assert _rel(path) in listed, (categories, _rel(path))


def test_spotify_cache_tree_protected_when_offline_blobs_present() -> None:
    tmp, root, _home = make_sandbox()
    with tmp:
        storage = _mkdir(root, "Library/Application Support/Spotify/Storage")
        (storage / "1234.file").write_text("offline", encoding="utf-8")
        (storage / "index.dat").write_text("index", encoding="utf-8")
        rows, skipped = _inspect(root, "spotify")
        # The whole Storage root is locked while offline tracks are present,
        # including non-encrypted siblings such as index.dat.
        assert any("app-protected-data" in reason for reason in skipped.values())
        listed = _relpaths(root, rows)
        assert not any("Application Support/Spotify/Storage" in path for path in listed)


def test_representative_long_tail_categories_emit_cache_files() -> None:
    tmp, root, _home = make_sandbox()
    with tmp:
        cases: list[tuple[str, list[Path], list[Path]]] = [
            ("wecom", [_write(root, "Library/Caches/com.tencent.WeWorkMac/c")], []),
            (
                "legcord",
                [_write(root, "Library/Application Support/legcord/Cache/c")],
                [
                    _write(root, "Library/Application Support/legcord/Local Storage/leveldb/0"),
                    _write(root, "Library/Application Support/legcord/Cookies"),
                ],
            ),
            (
                "chatgpt",
                [_write(root, "Library/Caches/com.openai.chat/c")],
                [_write(root, "Library/Application Support/com.openai.chat/account.json")],
            ),
            (
                "claudeDesktop",
                [
                    _write(root, "Library/Caches/com.anthropic.claudefordesktop/c"),
                    _write(root, "Library/Logs/Claude/mcp.log"),
                ],
                [_write(root, "Library/Application Support/Claude/settings.json")],
            ),
            (
                "premierePro",
                [
                    _write(root, "Library/Caches/com.adobe.PremierePro.25/c"),
                    _write(root, "Library/Application Support/Adobe/Common/Media Cache Files/clip.pek"),
                ],
                [_write(root, "Movies/project.prproj")],
            ),
            ("autodeskCaches", [_write(root, "Library/Caches/com.autodesk.fusion360/c")], []),
            ("miaoYan", [_write(root, "Library/Caches/com.tw93.MiaoYan/c")], []),
            (
                "folo",
                [
                    _write(
                        root,
                        "Library/Containers/is.follow/Data/Library/Application Support/Folo/Cache/Cache_Data/d",
                    )
                ],
                [],
            ),
            ("neteaseMusic", [_write(root, "Library/Caches/com.netease.163music/c")], []),
            (
                "tencentVideo",
                [
                    _write(root, "Library/Caches/com.tencent.tenvideo/c"),
                    _write(root, "Library/Containers/com.tencent.tenvideo/Data/Library/Application Support/Upgrade/u"),
                ],
                [_write(root, "Library/Containers/com.tencent.tenvideo/Data/Documents/history")],
            ),
            ("bilibili", [_write(root, "Library/Caches/tv.danmaku.bili/c")], []),
            (
                "stremio",
                [
                    _write(root, "Library/Caches/smart.stremio.desktop/c"),
                    _write(root, "Library/Application Support/stremio/stremio-server/stremio-cache/x"),
                ],
                [],
            ),
            (
                "transmission",
                [_write(root, "Library/Caches/org.m0k.transmission/c")],
                [_write(root, "Library/Application Support/Transmission/Resume/x.resume")],
            ),
            ("downie", [_write(root, "Library/Caches/com.downie.Downie-4/c")], []),
            (
                "minecraft",
                [
                    _write(root, "Library/Application Support/minecraft/logs/latest.log"),
                    _write(root, "Library/Application Support/minecraft/webcache2/c"),
                ],
                [
                    _write(root, "Library/Application Support/minecraft/saves/World/level.dat"),
                    _write(root, "Library/Application Support/minecraft/options.txt"),
                ],
            ),
            (
                "lunarClient",
                [
                    _write(root, ".lunarclient/game-cache/c"),
                    _write(root, ".lunarclient/offline/1.8/logs/l.log"),
                ],
                [],
            ),
            (
                "pcsx2",
                [
                    _write(root, "Library/Caches/net.pcsx2.PCSX2/c"),
                    _write(root, "Library/Logs/PCSX2/emulog.txt"),
                ],
                [_write(root, "Library/Application Support/PCSX2/memcards/Mcd001.ps2")],
            ),
            ("rpcs3", [_write(root, "Library/Caches/net.rpcs3.rpcs3/c")], []),
            ("youdaoDict", [_write(root, "Library/Caches/com.youdao.YoudaoDict/c")], []),
            ("eudict", [_write(root, "Library/Caches/com.eudic.eudic/c")], []),
            ("bobTranslate", [_write(root, "Library/Caches/com.bob-build.Bob/c")], []),
            ("camo", [_write(root, "Library/Caches/com.reincubate.camo/c")], []),
            ("xnip", [_write(root, "Library/Caches/com.xnipapp.xnip/c")], []),
            ("sparkMail", [_write(root, "Library/Caches/com.readdle.smartemail-Mac/c")], []),
            ("airmail", [_write(root, "Library/Caches/com.airmail.airmail3/c")], []),
            ("anydo", [_write(root, "Library/Caches/com.any.do.mac/c")], []),
            ("ghostty", [_write(root, "Library/Caches/com.mitchellh.ghostty/c")], []),
            ("inputSourcePro", [_write(root, "Library/Caches/com.runjuu.Input-Source-Pro/c")], []),
            ("wakatime", [_write(root, "Library/Caches/macos-wakatime.WakaTime/c")], []),
            (
                "weType",
                [
                    _write(root, "Library/Application Support/WeType/com.onevcat.Kingfisher.ImageCache.WeType/i"),
                    _write(root, "Library/Application Support/WeType/DictUpdate/d"),
                ],
                [_write(root, "Library/Application Support/WeType/UserDict/user.db")],
            ),
            (
                "mihomoParty",
                [
                    _write(root, "Library/Application Support/mihomo-party/Cache/c"),
                    _write(root, "Library/Application Support/mihomo-party/logs/l.log"),
                ],
                [_write(root, "Library/Application Support/mihomo-party/config/config.yaml")],
            ),
            ("stash", [_write(root, "Library/Caches/ws.stash.app.mac/c")], []),
            ("logseq", [_write(root, "Library/Caches/com.logseq.logseq/c")], []),
            ("yinxiang", [_write(root, "Library/Caches/com.yinxiang.Mac/c")], []),
            ("theUnarchiver", [_write(root, "Library/Caches/cx.c3.theunarchiver/c")], []),
            ("teamViewer", [_write(root, "Library/Caches/com.teamviewer.TeamViewer/c")], []),
            ("anyDesk", [_write(root, "Library/Caches/com.anydesk.anydesk/c")], []),
            ("toDesk", [_write(root, "Library/Caches/com.todesk.ToDesk/c")], []),
            ("sunlogin", [_write(root, "Library/Caches/com.sunlogin.SunloginClient/c")], []),
        ]
        for key, expected, protected_paths in cases:
            rows, _skipped = _inspect(root, key)
            listed = _relpaths(root, rows)
            for path in expected:
                assert _rel(path) in listed, (key, _rel(path))
            for path in protected_paths:
                assert _rel(path) not in listed, (key, _rel(path))
