from __future__ import annotations

import os
import unittest

from cleancli import delete_ops
from tests.helpers import make_sandbox, policy_for


@unittest.skipIf(not hasattr(os, "symlink"), "symlink unsupported")
def test_symlink_pointing_to_system_path_is_rejected() -> None:
    tmp, root, home = make_sandbox()
    with tmp:
        system_dir = root / "System"
        system_dir.mkdir()
        link = root / "Users/tester/Downloads/system-link"
        os.symlink(system_dir, link)

        with unittest.TestCase().assertRaisesRegex(RuntimeError, "symlink pointing to protected path"):
            delete_ops.assert_safe_to_delete(link, policy=policy_for(root, home))
