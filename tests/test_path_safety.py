from __future__ import annotations

import os

import pytest

from cleancli import delete_ops
from tests.helpers import make_sandbox, policy_for


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
