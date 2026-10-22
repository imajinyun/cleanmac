"""Old Chromium framework version and EdgeUpdater payload pruning.

Aligns with Mole's clean_chrome/edge/brave_old_versions and
clean_edge_updater_old_versions: the ``Current`` symlink target and any newer
staged update always survive, a broken marker fails closed, and updater
payloads are compared against the installed Edge build.
"""

from __future__ import annotations

import json
import os
import plistlib
from pathlib import Path

import pytest

from cleancli import browser_versions, core
from tests.helpers import make_sandbox, run_cli

CHROME = ("Google Chrome.app", "Google Chrome Framework.framework")
EDGE = ("Microsoft Edge.app", "Microsoft Edge Framework.framework")
BRAVE = ("Brave Browser.app", "Brave Browser Framework.framework")


@pytest.fixture(autouse=True)
def _test_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CLEANMAC_TEST_MODE", "1")
    monkeypatch.setenv("CLEANMAC_TEST_NO_AUTH", "1")


def _versions(root: Path, app: str, framework: str) -> Path:
    return root / "Applications" / app / "Contents" / "Frameworks" / framework / "Versions"


def _make_version(versions_dir: Path, name: str, mtime: float) -> Path:
    version_dir = versions_dir / name
    version_dir.mkdir(parents=True)
    (version_dir / "binary").write_text("payload", encoding="utf-8")
    os.utime(version_dir, (mtime, mtime))
    return version_dir


def _framework_layout(root: Path, browser: tuple[str, str], spec: dict[str, float], current: str) -> Path:
    versions_dir = _versions(root, browser[0], browser[1])
    versions_dir.mkdir(parents=True)
    for name, mtime in spec.items():
        _make_version(versions_dir, name, mtime)
    (versions_dir / "Current").symlink_to(current)
    return versions_dir


def test_framework_pruning_keeps_current_and_staged_update(tmp_path: Path) -> None:
    versions_dir = _framework_layout(
        tmp_path,
        CHROME,
        {"136.0.1": 1000.0, "138.0.2": 2000.0, "139.0.9": 3000.0},
        "138.0.2",
    )
    targets = browser_versions.old_framework_version_dirs(tmp_path, tmp_path / "home", *CHROME)
    assert {path.name for path in targets} == {"136.0.1"}
    prunable = versions_dir / "136.0.1"
    assert browser_versions.is_prunable_framework_version(prunable, CHROME[1])
    assert not browser_versions.is_prunable_framework_version(versions_dir / "138.0.2", CHROME[1])
    assert not browser_versions.is_prunable_framework_version(versions_dir / "139.0.9", CHROME[1])


def test_framework_pruning_without_newer_staged_version(tmp_path: Path) -> None:
    home = tmp_path / "tester"
    _framework_layout(
        home,
        BRAVE,
        {"1.0.100": 1000.0, "1.0.200": 2000.0},
        "1.0.200",
    )
    # User-installed app lives under ~/Applications.
    targets = browser_versions.old_framework_version_dirs(tmp_path, home, *BRAVE)
    assert {path.name for path in targets} == {"1.0.100"}


def test_missing_or_broken_current_fails_closed(tmp_path: Path) -> None:
    # No Current symlink at all.
    versions_dir = _versions(tmp_path, *EDGE)
    versions_dir.mkdir(parents=True)
    _make_version(versions_dir, "1.0", 1000.0)
    assert browser_versions.old_framework_version_dirs(tmp_path, tmp_path / "home", *EDGE) == []

    # Broken Current target.
    (versions_dir / "Current").symlink_to("9.9")
    assert browser_versions.old_framework_version_dirs(tmp_path, tmp_path / "home", *EDGE) == []
    assert not browser_versions.is_prunable_framework_version(versions_dir / "1.0", EDGE[1])


def test_symlinked_version_directory_is_not_prunable(tmp_path: Path) -> None:
    outside = tmp_path / "outside-version"
    outside.mkdir()
    versions_dir = _framework_layout(tmp_path, CHROME, {"138.0.2": 2000.0}, "138.0.2")
    try:
        (versions_dir / "137.0.1").symlink_to(outside, target_is_directory=True)
    except OSError:
        pytest.skip("symlinks unavailable")
    targets = browser_versions.old_framework_version_dirs(tmp_path, tmp_path / "home", *CHROME)
    assert targets == []


def test_framework_predicate_rejects_wrong_browser_and_shape(tmp_path: Path) -> None:
    versions_dir = _framework_layout(
        tmp_path,
        CHROME,
        {"1.0": 1000.0, "2.0": 2000.0},
        "2.0",
    )
    old_chrome = versions_dir / "1.0"
    # Chrome path validated against the Edge framework name must not match.
    assert not browser_versions.is_prunable_framework_version(old_chrome, EDGE[1])
    # Random directory with no framework layout never matches.
    stranger = tmp_path / "Downloads" / "1.0"
    stranger.parent.mkdir()
    stranger.mkdir()
    assert not browser_versions.is_prunable_framework_version(stranger, CHROME[1])


def _updater_root(home: Path, versions: list[str]) -> Path:
    root = home / browser_versions.EDGE_UPDATER_PAYLOADS
    root.mkdir(parents=True)
    for name in versions:
        (root / name).mkdir()
    return root


def _install_edge(root: Path, version: str) -> None:
    contents = root / "Applications" / "Microsoft Edge.app" / "Contents"
    contents.mkdir(parents=True)
    with (contents / "Info.plist").open("wb") as handle:
        plistlib.dump({"CFBundleShortVersionString": version}, handle)


def test_updater_payloads_compared_to_installed_edge(tmp_path: Path) -> None:
    home = tmp_path / "home"
    root = _updater_root(home, ["136.0.1", "137.0.5", "138.0.2", "139.0.9", "garbage"])
    _install_edge(tmp_path, "138.0.2")
    targets = browser_versions.old_edge_updater_payloads(tmp_path, home)
    assert {path.name for path in targets} == {"136.0.1", "137.0.5"}
    assert browser_versions.is_prunable_updater_payload(root / "136.0.1", root=tmp_path)
    assert not browser_versions.is_prunable_updater_payload(root / "138.0.2", root=tmp_path)
    assert not browser_versions.is_prunable_updater_payload(root / "139.0.9", root=tmp_path)
    # Unparseable payload names fail closed.
    assert not browser_versions.is_prunable_updater_payload(root / "garbage", root=tmp_path)


def test_updater_fallback_keeps_newest_without_installed_edge(tmp_path: Path) -> None:
    home = tmp_path / "home"
    root = _updater_root(home, ["1.0", "2.0", "3.0"])
    assert {path.name for path in browser_versions.old_edge_updater_payloads(tmp_path, home)} == {"1.0", "2.0"}
    # A single payload with no installed version proves nothing, so prune nothing.
    for name in ("1.0", "2.0"):
        (root / name).rmdir()
    assert browser_versions.old_edge_updater_payloads(tmp_path, home) == []


def test_cli_inspect_lists_only_old_framework_versions() -> None:
    tmp, root, _logical_home = make_sandbox()
    with tmp:
        versions_dir = _framework_layout(
            root,
            CHROME,
            {"136.0.1": 1000.0, "138.0.2": 2000.0, "139.0.9": 3000.0},
            "138.0.2",
        )
        result = run_cli(
            "--root",
            str(root),
            "--home",
            "/Users/tester",
            "--json",
            "clean",
            "inspect",
            "--categories",
            "chromeOldVersions",
        )
        report = json.loads(result.stdout)
        paths = {str(row["path"]) for row in report["items"]}
        assert paths == {str(versions_dir / "136.0.1")}

        # The same Edge version directory is outside the Chrome category gate.
        edge_dir = _framework_layout(root, EDGE, {"1.0": 1000.0, "2.0": 2000.0}, "2.0")
        result = run_cli(
            "--root",
            str(root),
            "--home",
            "/Users/tester",
            "--json",
            "clean",
            "inspect",
            "--categories",
            "edgeOldVersions,braveOldVersions",
        )
        report = json.loads(result.stdout)
        paths = {str(row["path"]) for row in report["items"]}
        assert paths == {str(edge_dir / "1.0")}


def test_cli_inspect_lists_stale_updater_payloads() -> None:
    tmp, root, _logical_home = make_sandbox()
    with tmp:
        home_root = root / "Users" / "tester"
        payload_root = _updater_root(home_root, ["1.0", "2.0", "3.0"])
        _install_edge(root, "2.0")
        result = run_cli(
            "--root",
            str(root),
            "--home",
            "/Users/tester",
            "--json",
            "clean",
            "inspect",
            "--categories",
            "edgeUpdaterPayloads",
        )
        report = json.loads(result.stdout)
        paths = {str(row["path"]) for row in report["items"]}
        assert paths == {str(payload_root / "1.0")}


def test_old_version_categories_are_advanced_opt_in() -> None:
    expected = {
        "chromeOldVersions": ("chrome-old-versions", "Google Chrome"),
        "edgeOldVersions": ("edge-old-versions", "Microsoft Edge"),
        "braveOldVersions": ("brave-old-versions", "Brave Browser"),
        "edgeUpdaterPayloads": ("edge-updater-payloads", "Microsoft Edge"),
    }
    for key, (provider, guard) in expected.items():
        category = core.CATEGORY_BY_KEY[key]
        assert category.advanced is True
        assert category.default is False
        assert category.recommended is False
        assert category.provider == provider
        assert category.process_guard == guard


def test_home_root_for_updater_candidate(tmp_path: Path) -> None:
    payload = tmp_path / "u" / "Library/Application Support/Microsoft/EdgeUpdater/apps/msedge-stable/1.0"
    assert browser_versions.home_root_for_updater_candidate(payload) == tmp_path / "u"
    assert browser_versions.home_root_for_updater_candidate(tmp_path / "relative/1.0") is None
