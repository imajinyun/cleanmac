from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

from cleancli import core
from cleancli.delete_ops import DeletePolicy

PROJECT_ROOT = Path(__file__).resolve().parents[1]
CLI = PROJECT_ROOT / "cleanmac.py"


def make_sandbox() -> tuple[tempfile.TemporaryDirectory[str], Path, Path]:
    tmp = tempfile.TemporaryDirectory()
    root = Path(tmp.name)
    home = Path("/Users/tester")

    (root / "Users/tester/.Trash").mkdir(parents=True)
    (root / "Users/tester/Downloads").mkdir(parents=True)
    (root / "Users/tester/Library/Containers/com.example/Data/Library/Caches").mkdir(parents=True)
    (root / "Users/tester/Library/Containers/com.example/Data/Library/Logs").mkdir(parents=True)
    (root / "Users/tester/Library/Containers/com.apple.Notes/Data/Library/Caches").mkdir(parents=True)
    (root / "Users/tester/Library/Group Containers/group.com.apple.notes/Library/Caches").mkdir(parents=True)
    (root / "Users/tester/Library/Group Containers/group.com.apple.Safari.Extensions/Library/Caches").mkdir(
        parents=True
    )
    (root / "Users/tester/Library/Group Containers/group.com.example.app/Library/Caches").mkdir(parents=True)

    (root / "Users/tester/.Trash/old.tmp").write_text("trash", encoding="utf-8")
    (root / "Users/tester/Downloads/download.bin").write_text("download", encoding="utf-8")
    (root / "Users/tester/Library/Containers/com.example/Data/Library/Caches/cache.bin").write_text(
        "cache", encoding="utf-8"
    )
    (root / "Users/tester/Library/Containers/com.example/Data/Library/Logs/app.log").write_text("log", encoding="utf-8")
    (root / "Users/tester/Library/Containers/com.apple.Notes/Data/Library/Caches/cache.bin").write_text(
        "notes", encoding="utf-8"
    )
    (root / "Users/tester/Library/Group Containers/group.com.apple.notes/Library/Caches/cache.bin").write_text(
        "notes", encoding="utf-8"
    )
    (
        root / "Users/tester/Library/Group Containers/group.com.apple.Safari.Extensions/Library/Caches/cache.bin"
    ).write_text("safari", encoding="utf-8")
    (root / "Users/tester/Library/Group Containers/group.com.example.app/Library/Caches/cache.bin").write_text(
        "group", encoding="utf-8"
    )
    return tmp, root, home


def run_cli(*args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(CLI), *args],
        cwd=PROJECT_ROOT,
        text=True,
        capture_output=True,
        check=check,
    )


def run_clean_json(root: Path, home: Path, *args: str) -> dict[str, object]:
    result = run_cli("--root", str(root), "--home", str(home), "--json", "clean", *args)
    return json.loads(result.stdout)


def policy_for(root: Path, home: Path = Path("/Users/tester")) -> DeletePolicy:
    return core.delete_policy_for_context(root=root, home=home)


@contextmanager
def cleanmac_test_env() -> Iterator[None]:
    original = os.environ.copy()
    os.environ["CLEANMAC_TEST_NO_AUTH"] = "1"
    os.environ["CLEANMAC_TEST_MODE"] = "1"
    try:
        yield
    finally:
        os.environ.clear()
        os.environ.update(original)


def skipped_by_path(report: dict[str, object]) -> dict[str, str]:
    skipped = report["skipped"]
    assert isinstance(skipped, list)
    return {str(row["path"]): str(row["reason"]) for row in skipped}
