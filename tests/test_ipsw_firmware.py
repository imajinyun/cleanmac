"""Cached device firmware (*.ipsw) category: discovery, protection, and gates."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

import cleancli.core as cleancli
from cleancli import protection
from cleancli.auto_clean import DEFAULT_AUTO_CATEGORIES
from cleancli.delete_ops import ProtectedUserDataError
from tests.helpers import make_sandbox, run_cli

CATEGORY = cleancli.CATEGORY_BY_KEY["ipswFirmware"]


def _touch(root: Path, relative: str, payload: bytes = b"firmware") -> Path:
    path = root / "Users/tester" / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(payload)
    return path


def test_category_metadata_is_high_risk_review_first() -> None:
    assert CATEGORY.risk == "high"
    assert CATEGORY.advanced is True
    assert CATEGORY.delete_target is True
    assert CATEGORY.requires_privilege is False
    assert CATEGORY.default_older_than_days is None
    assert "ipswFirmware" not in DEFAULT_AUTO_CATEGORIES


@pytest.mark.parametrize(
    "relative",
    [
        "Library/iTunes/iPhone Software Updates/iPhone16,2_18.0.ipsw",
        "Library/iTunes/iPad Software Updates/iPad13,1_17.4.ipsw",
        "Library/iTunes/iPod Software Updates/iPod_9.3.ipsw",
        "Library/Group Containers/group.com.apple.configurator/top-level.ipsw",
        "Library/Group Containers/group.com.apple.configurator/Data/Documents/Firmware/iphone.ipsw",
        "Library/Group Containers/AB1234DE.group.com.apple.configurator/Firmware/nested/ipad.ipsw",
    ],
)
def test_ipsw_files_are_discovered(tmp_path: Path, relative: str) -> None:
    firmware = _touch(tmp_path, relative)
    report = cleancli.inspect_items([CATEGORY], root=tmp_path, home=Path("/Users/tester"), limit=-1)
    paths = {Path(row["path"]).resolve() for row in report["items"]}
    assert firmware.resolve() in paths
    assert report["by_category"]["ipswFirmware"]["count"] == 1


def test_itunes_scan_is_shallow_and_ipsw_only(tmp_path: Path) -> None:
    shallow_ipsw = _touch(tmp_path, "Library/iTunes/iPhone Software Updates/iphone.ipsw")
    sibling_text = _touch(tmp_path, "Library/iTunes/iPhone Software Updates/readme.txt", b"notes")
    nested_ipsw = _touch(tmp_path, "Library/iTunes/iPhone Software Updates/sub/extra.ipsw")

    report = cleancli.inspect_items([CATEGORY], root=tmp_path, home=Path("/Users/tester"), limit=-1)
    paths = {Path(row["path"]).resolve() for row in report["items"]}

    assert paths == {shallow_ipsw.resolve()}
    assert sibling_text.exists()
    assert nested_ipsw.exists()


def test_configurator_scan_is_recursive_but_ipsw_only(tmp_path: Path) -> None:
    nested_ipsw = _touch(
        tmp_path,
        "Library/Group Containers/group.com.apple.configurator/Data/Firmware/deep/iphone.ipsw",
    )
    team_ipsw = _touch(
        tmp_path,
        "Library/Group Containers/AB1234DE.group.com.apple.configurator/Firmware/ipad.ipsw",
    )
    device_db = _touch(
        tmp_path,
        "Library/Group Containers/group.com.apple.configurator/Data/Devices/device.db",
        b"db",
    )

    report = cleancli.inspect_items([CATEGORY], root=tmp_path, home=Path("/Users/tester"), limit=-1)
    paths = {Path(row["path"]).resolve() for row in report["items"]}

    assert paths == {nested_ipsw.resolve(), team_ipsw.resolve()}
    assert device_db.exists()


def test_other_apple_group_containers_never_enumerated(tmp_path: Path) -> None:
    notes_ipsw = _touch(tmp_path, "Library/Group Containers/group.com.apple.notes/iphone.ipsw")
    spoof_ipsw = _touch(tmp_path, "Library/Group Containers/group.com.apple.configurator.evil/iphone.ipsw")

    report = cleancli.inspect_items([CATEGORY], root=tmp_path, home=Path("/Users/tester"), limit=-1)

    assert report["total_candidates"] == 0
    assert notes_ipsw.exists()
    assert spoof_ipsw.exists()


def test_missing_roots_report_zero_candidates(tmp_path: Path) -> None:
    report = cleancli.inspect_items([CATEGORY], root=tmp_path, home=Path("/Users/tester"), limit=-1)
    assert report["total_candidates"] == 0
    assert report["items"] == []


def test_predicate_matches_only_ipsw_leaves_inside_configurator_containers() -> None:
    assert protection.is_configurator_firmware_installer(
        Path("/Users/x/Library/Group Containers/group.com.apple.configurator/Data/iphone.ipsw")
    )
    assert protection.is_configurator_firmware_installer(
        Path("/Users/x/Library/Group Containers/AB1234DE.group.com.apple.configurator/ipad.IPSW")
    )
    assert not protection.is_configurator_firmware_installer(
        Path("/Users/x/Library/Group Containers/group.com.apple.configurator/Data/device.db")
    )
    assert not protection.is_configurator_firmware_installer(
        Path("/Users/x/Library/Group Containers/group.com.apple.notes/iphone.ipsw")
    )
    assert not protection.is_configurator_firmware_installer(
        Path("/Users/x/Library/Group Containers/group.com.apple.configurator.evil/iphone.ipsw")
    )
    assert not protection.is_configurator_firmware_installer(
        Path("/Users/x/Library/iTunes/iPhone Software Updates/iphone.ipsw")
    )


def test_group_container_blanket_protection_has_firmware_only_exception() -> None:
    # Exact *.ipsw leaves inside Configurator containers are regenerable downloads.
    assert not protection.should_protect_data(
        Path("/Users/x/Library/Group Containers/group.com.apple.configurator/Data/iphone.ipsw")
    )
    assert not protection.should_protect_data(
        Path("/Users/x/Library/Group Containers/AB1234DE.group.com.apple.configurator/ipad.ipsw")
    )
    # Everything else inside Apple group containers stays blanket-protected.
    assert protection.should_protect_data(
        Path("/Users/x/Library/Group Containers/group.com.apple.configurator/Data/device.db")
    )
    assert protection.should_protect_data(
        Path("/Users/x/Library/Group Containers/group.com.apple.notes/iphone.ipsw")
    )
    assert protection.should_protect_data(
        Path("/Users/x/Library/Group Containers/group.com.apple.configurator.evil/iphone.ipsw")
    )


def test_execution_gate_allows_ipsw_but_preserves_container_siblings(tmp_path: Path) -> None:
    home = Path("/Users/tester")
    firmware = _touch(
        tmp_path,
        "Library/Group Containers/group.com.apple.configurator/Data/Firmware/iphone.ipsw",
    )
    sibling = _touch(
        tmp_path,
        "Library/Group Containers/group.com.apple.configurator/Data/Devices/device.db",
        b"db",
    )

    cleancli.assert_safe_to_delete(firmware, root=tmp_path, home=home)
    with pytest.raises(ProtectedUserDataError):
        cleancli.assert_safe_to_delete(sibling, root=tmp_path, home=home)


def test_cli_inspect_lists_firmware_with_shallow_and_recursive_roots() -> None:
    tmp, root, home = make_sandbox()
    with tmp:
        itunes = _touch(root, "Library/iTunes/iPhone Software Updates/iphone.ipsw")
        bare = _touch(root, "Library/Group Containers/group.com.apple.configurator/Data/iphone.ipsw")
        team = _touch(root, "Library/Group Containers/X9Y8Z7.group.com.apple.configurator/deep/ipad.ipsw")
        _touch(root, "Library/iTunes/iPhone Software Updates/notes.txt", b"keep")
        _touch(root, "Library/Group Containers/group.com.apple.configurator/Data/device.db", b"keep")

        result = run_cli(
            "--root", str(root), "--home", str(home), "--json", "inspect", "--categories", "ipswFirmware"
        )
        report = json.loads(result.stdout)
        paths = {row["path"] for row in report["items"]}

        assert report["total_candidates"] == 3
        assert report["by_category"]["ipswFirmware"]["count"] == 3
        assert str(itunes) in paths
        assert str(bare) in paths
        assert str(team) in paths
        assert all(row["delete_mode"] == "trash" for row in report["items"])


def test_cli_dry_run_is_default_and_preserves_firmware() -> None:
    tmp, root, home = make_sandbox()
    with tmp:
        firmware = _touch(root, "Library/iTunes/iPhone Software Updates/iphone.ipsw")

        result = run_cli(
            "--root", str(root), "--home", str(home), "--json", "clean", "--categories", "ipswFirmware"
        )
        report = json.loads(result.stdout)

        assert report["dry_run"] is True
        assert firmware.exists()


def test_cli_execute_moves_only_ipsw_to_trash() -> None:
    tmp, root, home = make_sandbox()
    with tmp:
        itunes = _touch(root, "Library/iTunes/iPhone Software Updates/iphone.ipsw")
        bare = _touch(root, "Library/Group Containers/group.com.apple.configurator/Data/iphone.ipsw")
        team = _touch(root, "Library/Group Containers/X9Y8Z7.group.com.apple.configurator/deep/ipad.ipsw")
        sibling = _touch(
            root, "Library/Group Containers/group.com.apple.configurator/Data/device.db", b"keep"
        )
        notes_cache = root / "Users/tester/Library/Group Containers/group.com.apple.notes/Library/Caches/cache.bin"

        result = run_cli(
            "--root",
            str(root),
            "--home",
            str(home),
            "--json",
            "clean",
            "--categories",
            "ipswFirmware",
            "--delete-mode",
            "trash",
            "--execute",
            "--yes",
        )
        report = json.loads(result.stdout)
        post = report["post_clean_report"]

        assert report["dry_run"] is False
        assert post["summary"]["deleted_item_count"] == 3
        assert not itunes.exists()
        assert not bare.exists()
        assert not team.exists()
        assert sibling.exists()
        assert notes_cache.exists()
        trash_files = [
            path for path in (root / "Users/tester/.Trash").glob("*") if not path.name.endswith(".tmp")
        ]
        assert len(trash_files) == 3
        assert all(".ipsw" in path.name for path in trash_files)
