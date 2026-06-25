from __future__ import annotations

import os
from pathlib import Path

import pytest

from cleancli import delete_ops
from tests.helpers import PROJECT_ROOT, make_sandbox, policy_for


def test_direct_delete_safety_blocks_top_level_and_outside_sandbox_paths() -> None:
    tmp, root, home = make_sandbox()
    with tmp:
        with pytest.raises(RuntimeError, match="unsafe top-level path"):
            delete_ops.assert_safe_to_delete(root / "Users/tester", policy=policy_for(root, home))


def test_delete_safety_rejects_malformed_and_protected_paths() -> None:
    tmp, root, home = make_sandbox()
    with tmp:
        policy = policy_for(root, home)

        with pytest.raises(RuntimeError, match="non-absolute"):
            delete_ops.assert_safe_to_delete(Path("relative.tmp"), policy=policy)

        with pytest.raises(RuntimeError, match="traversal"):
            delete_ops.assert_safe_to_delete(root / "Users/tester/.Trash/../escape", policy=policy)

        with pytest.raises(RuntimeError, match="control characters"):
            delete_ops.assert_safe_to_delete(root / "Users/tester/.Trash/bad\nname", policy=policy)

        protected = root / "System/Library"
        protected.mkdir(parents=True)
        with pytest.raises(RuntimeError, match="protected system path"):
            delete_ops.assert_safe_to_delete(protected, policy=policy)


def test_path_safety_rejects_dangerous_path_data() -> None:
    tmp, root, home = make_sandbox()
    corpus = PROJECT_ROOT / "tests/data/dangerous_paths.txt"
    with tmp:
        dangerous_paths = [
            line.strip()
            for line in corpus.read_text(encoding="utf-8").splitlines()
            if line.strip() and not line.startswith("#")
        ]
        assert len(dangerous_paths) >= 50

        policy = policy_for(root, home)
        for value in dangerous_paths:
            candidate = Path(value)
            mapped = candidate if not candidate.is_absolute() else root / value.lstrip("/")
            with pytest.raises(RuntimeError):
                delete_ops.assert_safe_to_delete(mapped, policy=policy)


def test_delete_safety_allows_private_allowlist_and_rejects_private_db() -> None:
    tmp, root, home = make_sandbox()
    with tmp:
        policy = policy_for(root, home)
        log_file = root / "private/var/log/app.log"
        log_file.parent.mkdir(parents=True)
        log_file.write_text("log", encoding="utf-8")
        delete_ops.assert_safe_to_delete(log_file, policy=policy)

        db_file = root / "private/var/db/important.db"
        db_file.parent.mkdir(parents=True, exist_ok=True)
        db_file.write_text("db", encoding="utf-8")
        with pytest.raises(RuntimeError, match="protected system path"):
            delete_ops.assert_safe_to_delete(db_file, policy=policy)


@pytest.mark.skipif(not hasattr(os, "symlink"), reason="symlink unsupported")
def test_symlink_pointing_to_system_path_is_rejected() -> None:
    tmp, root, home = make_sandbox()
    with tmp:
        system_dir = root / "System"
        system_dir.mkdir()
        link = root / "Users/tester/Downloads/system-link"
        os.symlink(system_dir, link)

        with pytest.raises(RuntimeError, match="symlink pointing to protected path"):
            delete_ops.assert_safe_to_delete(link, policy=policy_for(root, home))


@pytest.mark.skipif(not hasattr(os, "symlink"), reason="symlink unsupported")
def test_delete_safety_rejects_symlink_to_protected_path() -> None:
    tmp, root, home = make_sandbox()
    with tmp:
        protected = root / "System/Library"
        protected.mkdir(parents=True)
        link = root / "Users/tester/.Trash/system-link"
        os.symlink(protected, link)

        with pytest.raises(RuntimeError, match="symlink pointing to protected path"):
            delete_ops.assert_safe_to_delete(link, policy=policy_for(root, home))
