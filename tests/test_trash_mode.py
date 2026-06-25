from __future__ import annotations

import os
import shutil

import pytest

from tests.helpers import make_sandbox, run_cli


@pytest.mark.skipif(not hasattr(os, "symlink"), reason="symlink unsupported")
def test_trash_mode_failure_does_not_fallback_to_permanent_delete() -> None:
    tmp, root, home = make_sandbox()
    with tmp:
        trash = root / "Users/tester/.Trash"
        routed = root / "Users/tester/TrashTarget"
        shutil.rmtree(trash)
        routed.mkdir()
        os.symlink(routed, trash)

        result = run_cli(
            "--root",
            str(root),
            "--home",
            str(home),
            "clean",
            "--categories",
            "downloads",
            "--delete-mode",
            "trash",
            "--execute",
            "--yes",
            check=False,
        )

        assert result.returncode != 0
        assert (root / "Users/tester/Downloads/download.bin").exists()
        assert list(routed.iterdir()) == []


@pytest.mark.skipif(not hasattr(os, "symlink"), reason="symlink unsupported")
def test_trash_delete_mode_rejects_symlink_candidates() -> None:
    tmp, root, home = make_sandbox()
    with tmp:
        target = root / "Users/tester/Downloads/target.txt"
        link = root / "Users/tester/Downloads/link.txt"
        target.write_text("target", encoding="utf-8")
        os.symlink(target, link)

        result = run_cli(
            "--root",
            str(root),
            "--home",
            str(home),
            "--json",
            "clean",
            "--categories",
            "downloads",
            "--delete-mode",
            "trash",
            "--include",
            "link.txt",
            "--execute",
            "--yes",
            check=False,
        )

        assert result.returncode != 0
        assert link.is_symlink()
        deletion_log = root / "Users/tester/.cleanmac/deletions.log"
        assert "\tfailed\t" in deletion_log.read_text(encoding="utf-8")
