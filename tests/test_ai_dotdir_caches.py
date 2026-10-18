from __future__ import annotations

from pathlib import Path

import pytest

from cleancli import app_activity, core, protection

HOME = Path("/Users/tester")


def write(root: Path, relative: str, content: bytes = b"rebuildable") -> Path:
    path = root / "Users/tester" / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content)
    return path


@pytest.mark.parametrize(
    "relative",
    [
        ".codex/.tmp/plugins.tar.gz",
        ".codex/.tmp/plugins/catalog.json",
        ".codex/cache/codex_app_directory/info.json",
        ".codex/cache/remote_plugin_catalog/index.json",
        ".claude/cache/changelog.md",
        ".claude/Cache/my-closed-issues.json",
    ],
)
def test_exact_dotdir_cache_leaves_escape_sensitive_protection(relative: str) -> None:
    assert protection.should_protect_data(HOME / relative) is False
    assert protection.is_dotdir_regenerable_cache(HOME / relative) is True


@pytest.mark.parametrize(
    "relative",
    [
        ".codex",
        ".codex/sessions/2026/10/01/thread.jsonl",
        ".codex/auth.json",
        ".codex/config.toml",
        ".codex/projects/repo/session.jsonl",
        ".codex/history.jsonl",
        ".claude",
        ".claude/projects/repo.jsonl",
        ".claude/settings.json",
        ".claude/.credentials.json",
        ".claude.json",
        ".codex/cache2/secret",
        ".codex/cache-backup/x",
        ".codex/.tmpold/x",
    ],
)
def test_dotdir_parents_siblings_and_lookalikes_remain_protected(relative: str) -> None:
    assert protection.should_protect_data(HOME / relative) is True


def test_credential_descendant_re_blocks_the_dotdir_cache_leaf(tmp_path: Path) -> None:
    write(tmp_path, ".codex/cache/auth.json", b"{}")
    leaf = tmp_path / "Users/tester/.codex/cache"
    assert protection.should_protect_data(leaf) is True
    report = core.inspect_items([core.CATEGORY_BY_KEY["aiToolCaches"]], root=tmp_path, home=HOME, limit=-1)
    assert report["items"] == []
    assert any(row["reason"] == "app-protected-data" for row in report["skipped"])


def test_dotdir_caches_are_discovered_while_state_siblings_are_not(tmp_path: Path) -> None:
    tmp_file = write(tmp_path, ".codex/.tmp/plugins/version.json")
    cache_file = write(tmp_path, ".codex/cache/codex_apps_tools/tools.json")
    claude_file = write(tmp_path, ".claude/cache/changelog.md")
    write(tmp_path, ".codex/auth.json", b'{"token":"secret"}')
    write(tmp_path, ".codex/sessions/2026/thread.jsonl", b"conversation")
    write(tmp_path, ".claude/projects/repo/thread.jsonl", b"conversation")
    report = core.inspect_items([core.CATEGORY_BY_KEY["aiToolCaches"]], root=tmp_path, home=HOME, limit=-1)
    paths = {Path(row["path"]).resolve() for row in report["items"]}

    def covered(path: Path) -> bool:
        resolved = path.resolve()
        return resolved in paths or any(resolved.is_relative_to(row) for row in paths)

    assert covered(tmp_file)
    assert covered(cache_file)
    assert covered(claude_file)
    assert all(".codex/auth.json" not in str(path) for path in paths)
    assert all("sessions" not in str(path) for path in paths)
    assert all(".claude/projects" not in str(path) for path in paths)


def test_dotdir_cache_execution_preserves_credentials_and_conversations(tmp_path: Path) -> None:
    cache_file = write(tmp_path, ".codex/cache/codex_apps_tools/tools.json")
    tmp_file = write(tmp_path, ".codex/.tmp/plugins/catalog.json")
    credentials = write(tmp_path, ".codex/auth.json", b'{"token":"secret"}')
    sessions = write(tmp_path, ".codex/sessions/2026/thread.jsonl", b"conversation")
    report = core.clean(
        [core.CATEGORY_BY_KEY["aiToolCaches"]],
        root=tmp_path,
        home=HOME,
        execute=True,
        delete_mode="trash",
        operation_log=None,
    )
    assert report["deleted_count"] == 2
    assert not cache_file.exists()
    assert not tmp_file.exists()
    assert credentials.read_bytes() == b'{"token":"secret"}'
    assert sessions.read_bytes() == b"conversation"


def test_dotdir_cache_symlink_cannot_escape_home(tmp_path: Path) -> None:
    home_dir = tmp_path / "Users/tester"
    (home_dir / ".codex").mkdir(parents=True)
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "secret.bin").write_bytes(b"private")
    (home_dir / ".codex/cache").symlink_to(outside, target_is_directory=True)
    with pytest.raises(RuntimeError, match="Refusing to move symlink"):
        core.clean(
            [core.CATEGORY_BY_KEY["aiToolCaches"]],
            root=tmp_path,
            home=HOME,
            execute=True,
            delete_mode="trash",
            operation_log=None,
        )
    assert (outside / "secret.bin").read_bytes() == b"private"


def test_dotdir_caches_bind_to_codex_and_claude_activity_guards(tmp_path: Path) -> None:
    home_dir = tmp_path / "Users/tester"
    activity = app_activity.ApplicationActivity(
        home_root=home_dir,
        category_guards=[],
        read_processes=lambda: "",
    )
    assert "Codex" in activity.applications(home_dir / ".codex/cache/index")
    assert "Claude" in activity.applications(home_dir / ".claude/cache/changelog.md")
    assert activity.applications(home_dir / ".codex/sessions/thread.jsonl") == []


def test_running_codex_cli_blocks_dotdir_cache_removal(tmp_path: Path) -> None:
    write(tmp_path, ".codex/cache/codex_apps_tools/tools.json")
    activity = app_activity.ApplicationActivity(
        home_root=tmp_path / "Users/tester",
        category_guards=[],
        read_processes=lambda: "/Users/tester/.local/bin/codex\n",
    )
    category = core.CATEGORY_BY_KEY["aiToolCaches"]
    reason = core.category_policy_reason(
        category,
        tmp_path / "Users/tester/.codex/cache/codex_apps_tools/tools.json",
        root=tmp_path,
        activity=activity,
    )
    assert reason == "app-running"
