from __future__ import annotations

from pathlib import Path

import pytest

from cleancli.core import enumerate_ios_backups


def test_enumerate_ios_backups_no_backup_dir(tmp_path: Path):
    home = tmp_path / "home"
    home.mkdir()
    backups = enumerate_ios_backups(home=home)
    assert backups == []


def test_enumerate_ios_backups_empty_dir(tmp_path: Path):
    backup_dir = tmp_path / "home" / "Library" / "Application Support" / "MobileSync" / "Backup"
    backup_dir.mkdir(parents=True)
    backups = enumerate_ios_backups(home=tmp_path / "home")
    assert backups == []


def test_enumerate_ios_backups_single_backup(tmp_path: Path):
    udid = "00008101-000A12345678901E"
    backup_dir = tmp_path / "home" / "Library" / "Application Support" / "MobileSync" / "Backup" / udid
    backup_dir.mkdir(parents=True)

    (backup_dir / "Manifest.db").write_text("fake manifest")

    backups = enumerate_ios_backups(home=tmp_path / "home")
    assert len(backups) == 1
    assert backups[0]["udid"] == udid
    assert backups[0]["size_bytes"] == len("fake manifest")
    assert backups[0]["encrypted"] is False
    assert backups[0]["device_name"] is None
    assert backups[0]["product_type"] is None


def test_enumerate_ios_backups_multiple_sorted_by_size(tmp_path: Path):
    backup_root = tmp_path / "home" / "Library" / "Application Support" / "MobileSync" / "Backup"

    small = backup_root / "small-udid"
    small.mkdir(parents=True)
    (small / "a.txt").write_text("x" * 100)

    large = backup_root / "large-udid"
    large.mkdir(parents=True)
    (large / "b.txt").write_text("y" * 500)

    backups = enumerate_ios_backups(home=tmp_path / "home")
    assert len(backups) == 2
    assert backups[0]["size_bytes"] == 500
    assert backups[1]["size_bytes"] == 100


def test_enumerate_ios_backups_skips_files(tmp_path: Path):
    backup_root = tmp_path / "home" / "Library" / "Application Support" / "MobileSync" / "Backup"
    backup_root.mkdir(parents=True)

    (backup_root / "not-a-backup.txt").write_text("file, not dir")
    (backup_root / "valid-udid").mkdir()

    backups = enumerate_ios_backups(home=tmp_path / "home")
    assert len(backups) == 1
    assert backups[0]["udid"] == "valid-udid"


def test_enumerate_ios_backups_permission_error(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    backup_root = tmp_path / "home" / "Library" / "Application Support" / "MobileSync" / "Backup"
    backup_root.mkdir(parents=True)
    (backup_root / "backup1").mkdir()

    def bad_iterdir(self):
        raise PermissionError("denied")

    monkeypatch.setattr(Path, "iterdir", bad_iterdir)

    backups = enumerate_ios_backups(home=tmp_path / "home")
    assert backups == []


def test_enumerate_ios_backups_size_handles_symlinks(tmp_path: Path):
    udid = "test-udid"
    backup_dir = tmp_path / "home" / "Library" / "Application Support" / "MobileSync" / "Backup" / udid
    backup_dir.mkdir(parents=True)

    real_file = tmp_path / "real_file.txt"
    real_file.write_text("x" * 1000)

    import os

    try:
        os.symlink(real_file, backup_dir / "link.txt")
    except (OSError, AttributeError):
        pytest.skip("symlinks not supported")

    (backup_dir / "real.txt").write_text("y" * 100)

    backups = enumerate_ios_backups(home=tmp_path / "home")
    assert len(backups) == 1
    assert backups[0]["size_bytes"] == 100


def test_enumerate_ios_backups_size_handles_permission_error(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    udid = "test-udid"
    backup_dir = tmp_path / "home" / "Library" / "Application Support" / "MobileSync" / "Backup" / udid
    backup_dir.mkdir(parents=True)
    (backup_dir / "file.txt").write_text("content")

    def bad_rglob(self, pattern):
        raise PermissionError("denied")

    monkeypatch.setattr(Path, "rglob", bad_rglob)

    backups = enumerate_ios_backups(home=tmp_path / "home")
    assert len(backups) == 1
    assert backups[0]["size_bytes"] == 0


def test_enumerate_ios_backups_has_human_size(tmp_path: Path):
    backup_dir = tmp_path / "home" / "Library" / "Application Support" / "MobileSync" / "Backup" / "test-udid"
    backup_dir.mkdir(parents=True)
    (backup_dir / "data.bin").write_text("x" * 2048)

    backups = enumerate_ios_backups(home=tmp_path / "home")
    assert len(backups) == 1
    assert backups[0]["size_human"] is not None
    assert "KB" in backups[0]["size_human"]
