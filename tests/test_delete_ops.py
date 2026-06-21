from __future__ import annotations

import unittest
from pathlib import Path
from unittest import mock

from cleancli import delete_ops
from tests.helpers import make_sandbox, policy_for


def test_validate_deletion_path_rejects_empty_relative_and_traversal_paths() -> None:
    tmp, root, home = make_sandbox()
    with tmp:
        policy = policy_for(root, home)
        rejected_paths = ("", Path(""), Path("relative/path"), Path("/tmp/foo/../../etc/passwd"))

        for path in rejected_paths:
            with unittest.TestCase().assertRaises(RuntimeError):
                delete_ops.validate_deletion_path(path, policy=policy)


def test_validate_deletion_path_rejects_control_characters() -> None:
    tmp, root, home = make_sandbox()
    with tmp:
        policy = policy_for(root, home)
        target = root / "Users/tester/Downloads/bad\nname.txt"

        with unittest.TestCase().assertRaisesRegex(RuntimeError, "control characters"):
            delete_ops.validate_deletion_path(target, policy=policy)


def test_validate_deletion_path_rejects_live_system_roots() -> None:
    policy = policy_for(Path("/"), Path("/Users/tester"))
    rejected_paths = (
        Path("/"),
        Path("/System"),
        Path("/bin"),
        Path("/sbin"),
        Path("/usr"),
        Path("/etc"),
        Path("/var"),
        Path("/private"),
        Path("/private/var/db/important.db"),
    )

    for path in rejected_paths:
        with unittest.TestCase().subTest(path=str(path)):
            with unittest.TestCase().assertRaises(RuntimeError):
                delete_ops.validate_deletion_path(path, policy=policy)


def test_validate_deletion_path_allows_explicit_private_allowlist() -> None:
    policy = policy_for(Path("/"), Path("/Users/tester"))
    allowed_paths = (
        Path("/private/tmp/cleanmac-cache.bin"),
        Path("/private/var/tmp/cleanmac-cache.bin"),
        Path("/private/var/log/cleanmac.log"),
    )

    for path in allowed_paths:
        with unittest.TestCase().subTest(path=str(path)):
            assert delete_ops.validate_deletion_path(path, policy=policy) == path


def test_safe_remove_honors_dry_run_and_then_deletes() -> None:
    tmp, root, home = make_sandbox()
    with tmp:
        policy = policy_for(root, home)
        target = root / "Users/tester/Downloads/removable.tmp"
        target.write_text("cache", encoding="utf-8")

        delete_ops.safe_remove(target, policy=policy, dry_run=True)
        assert target.exists()

        delete_ops.safe_remove(target, policy=policy, dry_run=False)
        assert not target.exists()


def test_safe_sudo_remove_blocks_no_auth_and_symlinks() -> None:
    tmp, root, home = make_sandbox()
    with tmp:
        policy = policy_for(root, home)
        target = root / "Users/tester/Downloads/needs-sudo.tmp"
        target.write_text("cache", encoding="utf-8")

        with mock.patch.dict("os.environ", {"CLEANMAC_TEST_NO_AUTH": "1"}, clear=False):
            with unittest.TestCase().assertRaisesRegex(RuntimeError, "sudo blocked"):
                delete_ops.safe_sudo_remove(target, policy=policy)

        link = root / "Users/tester/Downloads/sudo-link"
        link.symlink_to(target)
        with unittest.TestCase().assertRaisesRegex(RuntimeError, "sudo remove symlink"):
            delete_ops.safe_sudo_remove(link, policy=policy, dry_run=True)


def test_require_trash_first_delete_mode_blocks_permanent_without_explicit_gate() -> None:
    delete_ops.require_trash_first_delete_mode("trash", surface="privacy cleanup")

    with unittest.TestCase().assertRaisesRegex(RuntimeError, "requires --delete-mode trash"):
        delete_ops.require_trash_first_delete_mode("permanent", surface="privacy cleanup")

    delete_ops.require_trash_first_delete_mode(
        "permanent",
        surface="non-trashable cleanup",
        non_trashable=True,
        explicit_non_trash_gate=True,
    )
