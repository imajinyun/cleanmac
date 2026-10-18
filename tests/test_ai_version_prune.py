from __future__ import annotations

from pathlib import Path

import pytest

from cleancli import app_activity, core, protection, version_prune

HOME = Path("/Users/tester")
CATEGORY = core.CATEGORY_BY_KEY["aiToolOldVersions"]

CODEX_BASE = ".codex/packages/standalone"
CURSOR_BASE = ".local/share/cursor-agent"


def _version(root: Path, tool: str, version: str, *, marker: str | None = None) -> Path:
    if tool == "codex":
        base = root / "Users/tester" / CODEX_BASE / "releases" / version
        marker_path = root / "Users/tester" / CODEX_BASE / "current"
        target = Path("releases") / version
    else:
        base = root / "Users/tester" / CURSOR_BASE / "versions" / version
        marker_path = root / "Users/tester/.local/bin/cursor-agent"
        target = Path("..") / "share" / "cursor-agent" / "versions" / version
    base.mkdir(parents=True, exist_ok=True)
    (base / "bin").mkdir(exist_ok=True)
    (base / "bin" / tool).write_bytes(b"exec")
    (base / "resource.json").write_bytes(b"{}")
    if marker is not None:
        marker_path.parent.mkdir(parents=True, exist_ok=True)
        if marker_path.exists() or marker_path.is_symlink():
            marker_path.unlink()
        if marker == "active":
            marker_path.symlink_to(target)
        elif marker == "outside":
            outside = root / "outside-version"
            outside.mkdir(exist_ok=True)
            marker_path.symlink_to(outside, target_is_directory=True)
        elif marker == "nested":
            marker_path.symlink_to(target / "bin" / "subdir")
        elif marker == "dangling":
            marker_path.symlink_to(target / "missing")
        elif marker == "file":
            marker_path.parent.mkdir(parents=True, exist_ok=True)
            marker_path.write_bytes(b"not a symlink")
    return base


@pytest.fixture
def installed_home(tmp_path: Path) -> Path:
    _version(tmp_path, "codex", "0.142.3-aarch64-apple-darwin")
    _version(tmp_path, "codex", "0.147.0-aarch64-apple-darwin")
    _version(tmp_path, "codex", "0.148.0-aarch64-apple-darwin", marker="active")
    _version(tmp_path, "cursor-agent", "2026.08.11-e8db854")
    _version(tmp_path, "cursor-agent", "2026.08.25-3e8eec8", marker="active")
    return tmp_path / "Users/tester"


def test_old_version_targets_skip_active_version_for_each_tool(installed_home: Path) -> None:
    targets = version_prune.old_version_targets(installed_home)
    names = {path.name for path in targets}
    assert names == {"0.142.3-aarch64-apple-darwin", "0.147.0-aarch64-apple-darwin", "2026.08.11-e8db854"}
    assert all(path.is_dir() for path in targets)


def test_active_marker_is_required_and_other_versions_are_not_listed_without_it(tmp_path: Path) -> None:
    _version(tmp_path, "codex", "0.142.3-aarch64-apple-darwin")
    _version(tmp_path, "codex", "0.148.0-aarch64-apple-darwin")
    assert version_prune.old_version_targets(tmp_path / "Users/tester") == []


@pytest.mark.parametrize("marker", ["dangling", "file", "outside", "nested"])
def test_anomalous_markers_fail_closed(tmp_path: Path, marker: str) -> None:
    _version(tmp_path, "codex", "0.142.3-aarch64-apple-darwin")
    _version(tmp_path, "codex", "0.148.0-aarch64-apple-darwin", marker=marker)
    assert version_prune.old_version_targets(tmp_path / "Users/tester") == []


def test_non_directory_and_dotfile_children_are_ignored(installed_home: Path) -> None:
    releases = installed_home / CODEX_BASE / "releases"
    (releases / "notes.txt").write_bytes(b"readme")
    (releases / ".tmp").mkdir()
    targets = version_prune.old_version_targets(installed_home)
    assert all(path.name not in {"notes.txt", ".tmp"} for path in targets)


def test_symlinked_version_directories_are_never_targets(tmp_path: Path) -> None:
    home_dir = tmp_path / "Users/tester"
    real_root = tmp_path / "elsewhere/releases"
    real_root.mkdir(parents=True)
    (real_root / "0.9.0").mkdir()
    _version(tmp_path, "codex", "0.148.0-aarch64-apple-darwin", marker="active")
    releases = home_dir / CODEX_BASE / "releases"
    (releases / "0.9.0").symlink_to(real_root / "0.9.0", target_is_directory=True)
    targets = version_prune.old_version_targets(home_dir)
    assert {path.name for path in targets} == set()
    assert (real_root / "0.9.0").is_dir()


def test_is_prunable_version_dir_revalidates_membership(installed_home: Path) -> None:
    old = installed_home / CODEX_BASE / "releases/0.147.0-aarch64-apple-darwin"
    active = installed_home / CODEX_BASE / "releases/0.148.0-aarch64-apple-darwin"
    assert version_prune.is_prunable_version_dir(old, installed_home) is True
    assert version_prune.is_prunable_version_dir(active, installed_home) is False
    child = old / "bin" / "codex"
    assert version_prune.is_prunable_version_dir(child, installed_home) is False


def test_home_root_for_candidate_derives_sandbox_home(installed_home: Path) -> None:
    old = installed_home / CODEX_BASE / "releases/0.147.0-aarch64-apple-darwin"
    cursor_old = installed_home / CURSOR_BASE / "versions/2026.08.11-e8db854"
    assert version_prune.home_root_for_candidate(old) == installed_home
    assert version_prune.home_root_for_candidate(cursor_old) == installed_home
    assert version_prune.home_root_for_candidate(old / "bin" / "codex") is None
    assert version_prune.home_root_for_candidate(Path("releases/0.1.0")) is None


def test_inspect_lists_whole_version_directories_not_their_children(installed_home: Path) -> None:
    root = installed_home.parent.parent
    report = core.inspect_items([CATEGORY], root=root, home=HOME, limit=-1)
    paths = {Path(row["path"]).resolve() for row in report["items"]}
    assert paths == {path.resolve() for path in version_prune.old_version_targets(installed_home)}
    assert all("bin" not in path.parts for path in paths)
    assert report["skipped"] == []


def test_policy_rejects_active_version_and_forged_descendants(installed_home: Path) -> None:
    root = installed_home.parent.parent
    active = installed_home / CODEX_BASE / "releases/0.148.0-aarch64-apple-darwin"
    forged_child = installed_home / CODEX_BASE / "releases/0.147.0-aarch64-apple-darwin/codex"
    lookalike = root / "other/.codex/packages/standalone/releases/9.9.9"
    lookalike.mkdir(parents=True)
    assert core.category_policy_reason(CATEGORY, active, root=root) == "outside-provider-allowlist"
    assert core.category_policy_reason(CATEGORY, forged_child, root=root) == "outside-provider-allowlist"
    assert core.category_policy_reason(CATEGORY, lookalike, root=root) == "outside-provider-allowlist"


def test_lexical_version_shape_does_not_authorize_unrelated_paths() -> None:
    assert protection.is_superseded_ai_tool_version(HOME / ".codex/packages/standalone/releases/0.1.0")
    assert not protection.is_superseded_ai_tool_version(HOME / ".codex/sessions/thread.jsonl")
    assert not protection.should_protect_data(HOME / ".codex/packages/standalone/releases/0.147.0-aarch64-apple-darwin")


def test_execution_trashes_old_versions_and_preserves_active_and_marker(installed_home: Path) -> None:
    root = installed_home.parent.parent
    active = installed_home / CODEX_BASE / "releases/0.148.0-aarch64-apple-darwin"
    cursor_active = installed_home / CURSOR_BASE / "versions/2026.08.25-3e8eec8"
    codex_marker = installed_home / CODEX_BASE / "current"
    cursor_marker = installed_home / ".local/bin/cursor-agent"
    report = core.clean(
        [CATEGORY],
        root=root,
        home=HOME,
        execute=True,
        delete_mode="trash",
        operation_log=None,
    )
    assert report["deleted_count"] == 3
    assert active.is_dir()
    assert cursor_active.is_dir()
    assert codex_marker.resolve(strict=True) == active.resolve(strict=False)
    assert cursor_marker.resolve(strict=True) == cursor_active.resolve(strict=False)
    assert not (installed_home / CODEX_BASE / "releases/0.147.0-aarch64-apple-darwin").exists()
    assert not (installed_home / CURSOR_BASE / "versions/2026.08.11-e8db854").exists()


def test_version_roots_bind_to_running_tool_activity_guards(installed_home: Path) -> None:
    activity = app_activity.ApplicationActivity(
        home_root=installed_home,
        category_guards=[],
        read_processes=lambda: "",
    )
    codex_old = installed_home / CODEX_BASE / "releases/0.147.0-aarch64-apple-darwin"
    cursor_old = installed_home / CURSOR_BASE / "versions/2026.08.11-e8db854"
    assert "Codex" in activity.applications(codex_old)
    assert "Cursor Agent" in activity.applications(cursor_old)


@pytest.mark.parametrize(
    "executable,target",
    [
        ("/Users/tester/.local/bin/codex", CODEX_BASE + "/releases/0.147.0-aarch64-apple-darwin"),
        ("/Users/tester/.local/bin/cursor-agent", CURSOR_BASE + "/versions/2026.08.11-e8db854"),
    ],
)
def test_running_tools_block_version_removal(installed_home: Path, executable: str, target: str) -> None:
    root = installed_home.parent.parent
    activity = app_activity.ApplicationActivity(
        home_root=installed_home,
        category_guards=[],
        read_processes=lambda: executable + "\n",
    )
    reason = core.category_policy_reason(CATEGORY, installed_home / target, root=root, activity=activity)
    assert reason == "app-running"


def test_unreadable_process_state_blocks_removal_fail_closed(installed_home: Path) -> None:
    root = installed_home.parent.parent
    activity = app_activity.ApplicationActivity(
        home_root=installed_home,
        category_guards=[],
        read_processes=lambda: None,
    )
    target = installed_home / CODEX_BASE / "releases/0.147.0-aarch64-apple-darwin"
    reason = core.category_policy_reason(CATEGORY, target, root=root, activity=activity)
    assert reason == "process-state-unknown"
