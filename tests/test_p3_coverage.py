"""P3 coverage improvement tests - low-level utility function tests."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pytest

from cleancli import delete_ops, protection
from cleancli.core import (
    CATEGORY_BY_KEY,
    Category,
    batch_append_deletion_log,
    delete_policy_for_context,
    deletion_log_path_for_context,
    rows_by_file_type,
    rows_by_parent_directory,
)
from cleancli.delete_ops import DeletePolicy


@dataclass
class _P3Sandbox:
    root: Path
    home: Path
    policy: DeletePolicy
    trash_root: Path


@pytest.fixture
def p3_sandbox(tmp_path: Path) -> _P3Sandbox:
    root = tmp_path
    home = root / "Users" / "tester"
    home.mkdir(parents=True)
    (home / ".Trash").mkdir()
    policy = delete_policy_for_context(root=root, home=home)
    return _P3Sandbox(root=root, home=home, policy=policy, trash_root=home / ".Trash")


class TestDeleteOpsUtility:
    def test_safe_trash_move_dry_run_returns_path(self, p3_sandbox: _P3Sandbox) -> None:
        target = p3_sandbox.root / "dry_run.txt"
        target.write_text("do not move")

        result = delete_ops.safe_trash_move(
            target, policy=p3_sandbox.policy, trash_root=p3_sandbox.trash_root, dry_run=True
        )
        assert result is not None
        assert target.exists()

    def test_safe_trash_move_real(self, p3_sandbox: _P3Sandbox) -> None:
        target = p3_sandbox.root / "trash_real.txt"
        target.write_text("go away")
        result = delete_ops.safe_trash_move(
            target, policy=p3_sandbox.policy, trash_root=p3_sandbox.trash_root, dry_run=False
        )
        assert result is not None
        assert result.exists()
        assert not target.exists()

    def test_safe_trash_move_rejects_symlink(self, p3_sandbox: _P3Sandbox) -> None:
        target = p3_sandbox.root / "real.txt"
        target.write_text("x")
        link = p3_sandbox.root / "link.txt"
        link.symlink_to(target)

        with pytest.raises(RuntimeError):
            delete_ops.safe_trash_move(link, policy=p3_sandbox.policy, trash_root=p3_sandbox.trash_root, dry_run=False)

    def test_delete_path_trash_mode(self, p3_sandbox: _P3Sandbox) -> None:
        target = p3_sandbox.root / "del_trash.txt"
        target.write_text("bye")
        result = delete_ops.delete_path(
            target, policy=p3_sandbox.policy, delete_mode="trash", trash_root=p3_sandbox.trash_root
        )
        assert result is not None
        assert not target.exists()

    def test_delete_path_dry_run_noop(self, p3_sandbox: _P3Sandbox) -> None:
        target = p3_sandbox.root / "noop.txt"
        target.write_text("stay")
        # delete_path doesn't have dry_run param; it always deletes
        # so we test with dry-run wrapping via safe_trash_move
        result = delete_ops.safe_trash_move(
            target, policy=p3_sandbox.policy, trash_root=p3_sandbox.trash_root, dry_run=True
        )
        assert result is not None
        assert target.exists()

    def test_delete_path_rejects_symlink(self, p3_sandbox: _P3Sandbox) -> None:
        target = p3_sandbox.root / "real.txt"
        target.write_text("x")
        link = p3_sandbox.root / "link.txt"
        link.symlink_to(target)

        with pytest.raises(RuntimeError):
            delete_ops.delete_path(
                link, policy=p3_sandbox.policy, delete_mode="trash", trash_root=p3_sandbox.trash_root
            )

    def test_delete_policy_for_context_returns_policy(self, p3_sandbox: _P3Sandbox) -> None:
        policy = delete_policy_for_context(root=p3_sandbox.root, home=p3_sandbox.home)
        assert isinstance(policy, DeletePolicy)
        assert policy.root == p3_sandbox.root
        assert p3_sandbox.home.name in str(policy.home_root)

    def test_delete_policy_has_callable_checks(self, p3_sandbox: _P3Sandbox) -> None:
        policy = delete_policy_for_context(root=p3_sandbox.root, home=p3_sandbox.home)
        assert callable(policy.critical_path)
        assert callable(policy.protected_user_data)
        assert callable(policy.private_allowlist)
        assert callable(policy.normalize_policy_path)

    def test_rows_by_file_type_empty(self) -> None:
        result = rows_by_file_type([])
        assert result == {}

    def test_rows_by_file_type_mixed(self, tmp_path: Path) -> None:
        (tmp_path / "a.txt").write_text("x")
        (tmp_path / "b.log").write_text("x")
        (tmp_path / "c.txt").write_text("x")
        rows = [
            {"path": str(tmp_path / "a.txt"), "bytes": 10},
            {"path": str(tmp_path / "b.log"), "bytes": 20},
            {"path": str(tmp_path / "c.txt"), "bytes": 30},
        ]
        result = rows_by_file_type(rows)
        assert "txt" in result
        assert "log" in result
        assert result["txt"]["count"] == 2
        assert result["txt"]["bytes"] == 40
        assert result["log"]["count"] == 1

    def test_rows_by_file_type_no_extension(self, tmp_path: Path) -> None:
        (tmp_path / "noext").write_text("x")
        rows = [{"path": str(tmp_path / "noext"), "bytes": 100}]
        result = rows_by_file_type(rows)
        assert "(no extension)" in result

    def test_rows_by_parent_directory_empty(self) -> None:
        result = rows_by_parent_directory([])
        assert result == {}

    def test_rows_by_parent_directory_groups(self, tmp_path: Path) -> None:
        d1 = str(tmp_path / "dir1")
        d2 = str(tmp_path / "dir2")
        rows = [
            {"parent": d1, "bytes": 10},
            {"parent": d1, "bytes": 20},
            {"parent": d2, "bytes": 30},
        ]
        result = rows_by_parent_directory(rows)
        assert d1 in result
        assert d2 in result
        assert result[d1]["count"] == 2
        assert result[d1]["bytes"] == 30
        assert result[d2]["count"] == 1

    def test_batch_append_deletion_log_writes_entries(self, p3_sandbox: _P3Sandbox) -> None:
        entries: list[dict[str, Any]] = [
            {"mode": "trash", "bytes_value": 1024, "status": "deleted", "path": "/tmp/a.txt", "detail": "ok"},
            {"mode": "permanent", "bytes_value": None, "status": "failed", "path": "/tmp/b.log", "detail": "error"},
        ]
        log_path = batch_append_deletion_log(root=p3_sandbox.root, home=p3_sandbox.home, entries=entries)
        assert Path(log_path).exists()
        content = Path(log_path).read_text()
        assert "trash" in content
        assert "permanent" in content
        assert "/tmp/a.txt" in content


class TestProtectionUtility:
    def test_should_protect_bundle_apple(self) -> None:
        assert protection.should_protect_bundle("com.apple.mail") is True
        assert protection.should_protect_bundle("com.apple.Safari") is True

    def test_should_protect_bundle_non_apple(self) -> None:
        assert protection.should_protect_bundle("com.google.Chrome") is False
        assert protection.should_protect_bundle(None) is False

    def test_should_protect_path_system(self) -> None:
        assert protection.should_protect_path(Path("/System")) is True
        assert protection.should_protect_path(Path("/Library")) is True

    def test_should_protect_path_tmp_allowed(self) -> None:
        assert protection.should_protect_path(Path("/tmp/test.txt")) is False

    def test_should_protect_data_keychain(self) -> None:
        keychain = Path("/Users/test/Library/Keychains/login.keychain-db")
        assert protection.should_protect_data(keychain) is True

    def test_should_protect_data_normal_file(self, tmp_path: Path) -> None:
        normal = tmp_path / "notes.txt"
        normal.write_text("hello")
        assert protection.should_protect_data(normal) is False

    def test_is_critical_system_component(self) -> None:
        assert protection.is_critical_system_component(Path("/System")) is True
        assert protection.is_critical_system_component(Path("/tmp")) is False

    def test_is_protected_group_container_apple(self, tmp_path: Path) -> None:
        group = tmp_path / "Group Containers" / "group.com.apple.something"
        group.parent.mkdir(parents=True)
        group.mkdir()
        assert protection.is_protected_group_container_path(group) is True

    def test_is_protected_user_data_messages(self) -> None:
        messages = Path("/Users/test/Library/Messages/chat.db")
        assert protection.is_protected_user_data_path(messages) is True

    def test_bundle_matches_pattern_wildcard(self) -> None:
        assert protection.bundle_matches_pattern("com.apple.mail", "com.apple.*") is True
        assert protection.bundle_matches_pattern("com.google.Chrome", "com.apple.*") is False

    def test_bundle_matches_any(self) -> None:
        patterns = ("com.apple.*", "com.microsoft.*")
        assert protection.bundle_matches_any("com.apple.mail", patterns) is True
        assert protection.bundle_matches_any("com.google.Chrome", patterns) is False
        assert protection.bundle_matches_any(None, patterns) is False

    def test_official_uninstaller_vendor_eset(self) -> None:
        result = protection.official_uninstaller_vendor(bundle_id="com.eset.ESETEndpointSecurity")
        assert result is not None
        assert "ESET" in result

    def test_official_uninstaller_vendor_none(self) -> None:
        result = protection.official_uninstaller_vendor(bundle_id="com.random.app")
        assert result is None

    def test_matches_pattern_basic(self) -> None:
        assert protection.matches_pattern(Path("/tmp/a/b/c.txt"), ["*/b/*"]) is True
        assert protection.matches_pattern(Path("/tmp/x/y.txt"), ["*/b/*"]) is False

    def test_contains_protected_descendant(self, tmp_path: Path) -> None:
        parent = tmp_path / "parent"
        parent.mkdir()
        (parent / "child" / "secret.keychain").parent.mkdir()
        (parent / "child" / "secret.keychain").write_text("x")
        assert protection.contains_protected_descendant(parent, ["*.keychain"]) is True

    def test_app_protected_data_reason(self) -> None:
        result = protection.app_protected_data_reason("trash", Path("/tmp/test.txt"))
        assert result is None

    def test_should_protect_from_uninstall_apple(self) -> None:
        assert protection.should_protect_from_uninstall("com.apple.mail") is True
        assert protection.should_protect_from_uninstall("com.google.Chrome") is False


class TestDeletePolicy:
    def test_policy_is_delete_policy_instance(self, p3_sandbox: _P3Sandbox) -> None:
        assert isinstance(p3_sandbox.policy, DeletePolicy)

    def test_policy_has_root(self, p3_sandbox: _P3Sandbox) -> None:
        assert p3_sandbox.policy.root == p3_sandbox.root

    def test_policy_has_home_root(self, p3_sandbox: _P3Sandbox) -> None:
        assert p3_sandbox.policy.home_root is not None
        assert isinstance(p3_sandbox.policy.home_root, Path)

    def test_policy_critical_path_is_callable(self, p3_sandbox: _P3Sandbox) -> None:
        assert callable(p3_sandbox.policy.critical_path)

    def test_policy_protected_user_data_is_callable(self, p3_sandbox: _P3Sandbox) -> None:
        assert callable(p3_sandbox.policy.protected_user_data)

    def test_policy_normalize_policy_path(self, p3_sandbox: _P3Sandbox) -> None:
        result = p3_sandbox.policy.normalize_policy_path(p3_sandbox.home / "test.txt")
        assert isinstance(result, str)

    def test_policy_private_allowlist(self, p3_sandbox: _P3Sandbox) -> None:
        assert callable(p3_sandbox.policy.private_allowlist)


class TestOperationLog:
    def test_deletion_log_path_returns_path(self, p3_sandbox: _P3Sandbox) -> None:
        path = deletion_log_path_for_context(root=p3_sandbox.root, home=p3_sandbox.home)
        assert isinstance(path, Path)
        assert path.name == "deletions.log"
        assert ".cleanmac" in path.parts

    def test_batch_append_creates_file(self, p3_sandbox: _P3Sandbox) -> None:
        entries: list[dict[str, Any]] = [
            {"mode": "trash", "bytes_value": 100, "status": "deleted", "path": "/tmp/x", "detail": ""},
        ]
        log_path = batch_append_deletion_log(root=p3_sandbox.root, home=p3_sandbox.home, entries=entries)
        assert Path(log_path).exists()
        assert Path(log_path).stat().st_size > 0

    def test_batch_append_appends_multiple(self, p3_sandbox: _P3Sandbox) -> None:
        entries: list[dict[str, Any]] = [
            {"mode": "trash", "bytes_value": 10, "status": "deleted", "path": "/a", "detail": ""},
            {"mode": "trash", "bytes_value": 20, "status": "deleted", "path": "/b", "detail": ""},
            {"mode": "trash", "bytes_value": 30, "status": "deleted", "path": "/c", "detail": ""},
        ]
        log_path_str = batch_append_deletion_log(root=p3_sandbox.root, home=p3_sandbox.home, entries=entries)
        log_path = Path(log_path_str)
        lines = [line for line in log_path.read_text().strip().split("\n") if line.strip()]
        assert len(lines) == 3

    def test_deletion_log_path_is_consistent(self, p3_sandbox: _P3Sandbox) -> None:
        path1 = deletion_log_path_for_context(root=p3_sandbox.root, home=p3_sandbox.home)
        path2 = deletion_log_path_for_context(root=p3_sandbox.root, home=p3_sandbox.home)
        assert path1 == path2

    def test_batch_append_returns_string_path(self, p3_sandbox: _P3Sandbox) -> None:
        entries: list[dict[str, Any]] = [
            {"mode": "trash", "bytes_value": 10, "status": "deleted", "path": "/a", "detail": ""},
        ]
        result = batch_append_deletion_log(root=p3_sandbox.root, home=p3_sandbox.home, entries=entries)
        assert isinstance(result, str)


class TestCategoryCoverage:
    def test_category_keys_are_unique(self) -> None:
        keys = list(CATEGORY_BY_KEY.keys())
        assert len(keys) == len(set(keys))

    def test_all_categories_have_title(self) -> None:
        for key, cat in CATEGORY_BY_KEY.items():
            assert isinstance(cat, Category)
            assert cat.title, f"Category {key} has empty title"

    def test_all_categories_have_key(self) -> None:
        for key, cat in CATEGORY_BY_KEY.items():
            assert cat.key == key

    def test_category_groups_are_defined(self) -> None:
        for key, cat in CATEGORY_BY_KEY.items():
            assert cat.group is not None, f"Category {key} has no group"

    def test_default_categories_exist(self) -> None:
        default_cats = [k for k, c in CATEGORY_BY_KEY.items() if c.default]
        assert len(default_cats) > 0

    def test_trash_category_exists(self) -> None:
        assert "trash" in CATEGORY_BY_KEY
        cat = CATEGORY_BY_KEY["trash"]
        assert "Trash" in cat.title or "trash" in cat.key

    def test_category_paths_is_tuple(self) -> None:
        cat = CATEGORY_BY_KEY.get("trash")
        assert cat is not None
        assert isinstance(cat.paths, tuple)

    def test_no_duplicate_category_keys(self) -> None:
        seen: set[str] = set()
        for key in CATEGORY_BY_KEY:
            assert key not in seen, f"Duplicate category key: {key}"
            seen.add(key)

    def test_recommended_categories_are_valid(self) -> None:
        recommended = [k for k, c in CATEGORY_BY_KEY.items() if c.recommended]
        for k in recommended:
            assert k in CATEGORY_BY_KEY

    def test_category_risk_levels(self) -> None:
        for key, cat in CATEGORY_BY_KEY.items():
            assert cat.risk in ("safe", "low", "medium", "high", "critical"), (
                f"Category {key} has invalid risk: {cat.risk}"
            )
