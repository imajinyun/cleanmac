from __future__ import annotations

import os
import time
from pathlib import Path

import pytest

from cleancli.purge import (
    DEFAULT_RECENT_DAYS,
    PROJECT_ARTIFACT_DIRS,
    _dir_size,
    _display_path,
    _find_artifact_dirs,
    _human_size,
    _resolve_roots,
    find_project_artifacts,
    render_purge_human,
)


def test_human_size_bins():
    assert _human_size(0) == "0 B"
    assert _human_size(None) == "0 B"
    assert _human_size(512) == "512 B"
    assert _human_size(2048) == "2.0 KB"
    assert _human_size(2 * 1024 * 1024) == "2.0 MB"
    assert _human_size(3 * 1024 * 1024 * 1024) == "3.0 GB"
    assert _human_size(4 * 1024 * 1024 * 1024 * 1024) == "4.0 TB"


def test_display_path_replaces_home():
    home = Path("/Users/tester")
    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(Path, "home", lambda: home)
        assert _display_path("/Users/tester/code/foo") == "~/code/foo"
        assert _display_path("/tmp/other") == "/tmp/other"


def test_resolve_roots_filters_nonexistent(tmp_path: Path):
    home = tmp_path / "home"
    home.mkdir()
    existing = tmp_path / "projects"
    existing.mkdir()

    roots = _resolve_roots((str(existing), str(tmp_path / "nope")), home=home)
    assert len(roots) == 1
    assert roots[0] == existing


def test_resolve_roots_expands_user(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    home = tmp_path / "Users" / "tester"
    home.mkdir(parents=True)
    monkeypatch.setenv("HOME", str(home))

    project_dir = home / "Projects"
    project_dir.mkdir()

    roots = _resolve_roots(("~/Projects",), home=home)
    assert len(roots) == 1
    assert roots[0] == project_dir


def test_dir_size_counts_files(tmp_path: Path):
    d = tmp_path / "art"
    d.mkdir()
    (d / "a.txt").write_text("x" * 100)
    (d / "b.txt").write_text("y" * 200)
    sub = d / "sub"
    sub.mkdir()
    (sub / "c.txt").write_text("z" * 300)

    assert _dir_size(d) == 600


def test_dir_size_handles_permission_error(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    d = tmp_path / "art"
    d.mkdir()
    (d / "a.txt").write_text("x" * 100)

    def bad_scandir(path):
        raise PermissionError("denied")

    monkeypatch.setattr(os, "scandir", bad_scandir)
    assert _dir_size(d) == 0


def test_find_artifact_dirs_finds_known_types(tmp_path: Path):
    proj = tmp_path / "myproject"
    (proj / "node_modules").mkdir(parents=True)
    (proj / "src").mkdir(parents=True)
    (proj / "src" / "util.js").write_text("x")

    found = list(_find_artifact_dirs(tmp_path))
    names = [p.name for p in found]
    assert "node_modules" in names


def test_find_artifact_dirs_respects_depth(tmp_path: Path):
    deep = tmp_path / "a" / "b" / "c" / "d" / "node_modules"
    deep.mkdir(parents=True)

    found = list(_find_artifact_dirs(tmp_path, max_depth=3))
    assert len(found) == 0


def test_find_artifact_dirs_skips_dot_dirs(tmp_path: Path):
    hidden = tmp_path / ".hidden_dir" / "node_modules"
    hidden.mkdir(parents=True)

    found = list(_find_artifact_dirs(tmp_path))
    assert len(found) == 0


def test_find_artifact_dirs_includes_allowed_dot_dirs(tmp_path: Path):
    venv_dir = tmp_path / ".venv"
    venv_dir.mkdir()

    found = list(_find_artifact_dirs(tmp_path))
    assert len(found) == 1
    assert found[0].name == ".venv"


def test_find_project_artifacts_groups_by_project(tmp_path: Path):
    proj1 = tmp_path / "proj1"
    (proj1 / "node_modules").mkdir(parents=True)
    (proj1 / "node_modules" / "pkg").write_text("x" * 100)

    proj2 = tmp_path / "proj2"
    (proj2 / "target").mkdir(parents=True)
    (proj2 / "target" / "debug").write_text("y" * 200)

    home = tmp_path / "home"
    home.mkdir()

    result = find_project_artifacts(
        scan_roots=(str(tmp_path),),
        recent_days=0,
        home=home,
    )

    assert result["schema"] == "cleanmac.project-purge.v1"
    assert result["total_projects"] == 2
    assert result["total_bytes"] == 300


def test_find_project_artifacts_recent_skip(tmp_path: Path):
    proj = tmp_path / "myproj"
    (proj / "node_modules").mkdir(parents=True)
    (proj / "node_modules" / "pkg").write_text("x" * 100)

    now = time.time()
    os.utime(proj / "node_modules", (now, now))
    os.utime(proj, (now, now))

    home = tmp_path / "home"
    home.mkdir()

    result = find_project_artifacts(
        scan_roots=(str(tmp_path),),
        recent_days=DEFAULT_RECENT_DAYS,
        home=home,
    )

    assert result["recent_projects"] == 1
    assert result["default_selected_count"] == 0


def test_find_project_artifacts_old_project_selected(tmp_path: Path):
    proj = tmp_path / "oldproj"
    (proj / "node_modules").mkdir(parents=True)
    (proj / "node_modules" / "pkg").write_text("x" * 100)

    old_time = time.time() - 30 * 86400
    os.utime(proj, (old_time, old_time))
    os.utime(proj / "node_modules", (old_time, old_time))

    home = tmp_path / "home"
    home.mkdir()

    result = find_project_artifacts(
        scan_roots=(str(tmp_path),),
        recent_days=DEFAULT_RECENT_DAYS,
        home=home,
    )

    assert result["recent_projects"] == 0
    assert result["default_selected_count"] == 1


def test_find_project_artifacts_empty(tmp_path: Path):
    home = tmp_path / "home"
    home.mkdir()

    result = find_project_artifacts(
        scan_roots=(str(tmp_path),),
        recent_days=0,
        home=home,
    )

    assert result["total_projects"] == 0
    assert result["total_bytes"] == 0


def test_render_purge_human_empty():
    report = {
        "scan_roots": ["/tmp"],
        "recent_days": 7,
        "total_projects": 0,
        "total_bytes": 0,
        "total_human": "0 B",
        "recent_projects": 0,
        "default_selected_count": 0,
        "projects": [],
    }
    output = render_purge_human(report)
    assert "Project Artifact Purge" in output
    assert "No project artifacts found" in output


def test_render_purge_human_with_projects(tmp_path: Path):
    proj = tmp_path / "myproject"
    (proj / "node_modules").mkdir(parents=True)
    (proj / "node_modules" / "pkg").write_text("x" * 100)

    home = tmp_path / "home"
    home.mkdir()

    old_time = time.time() - 30 * 86400
    os.utime(proj, (old_time, old_time))

    result = find_project_artifacts(
        scan_roots=(str(tmp_path),),
        recent_days=7,
        home=home,
    )
    output = render_purge_human(result)
    assert "node_modules" in output
    assert "● 1" in output
    assert "Legend" in output


def test_render_purge_human_truncates_long_list(tmp_path: Path):
    for i in range(35):
        proj = tmp_path / f"proj_{i:03d}"
        (proj / "node_modules").mkdir(parents=True)
        (proj / "node_modules" / "f").write_text("x")

    home = tmp_path / "home"
    home.mkdir()

    old_time = time.time() - 30 * 86400
    for i in range(35):
        os.utime(tmp_path / f"proj_{i:03d}", (old_time, old_time))

    result = find_project_artifacts(
        scan_roots=(str(tmp_path),),
        recent_days=7,
        home=home,
    )
    output = render_purge_human(result)
    assert "and 5 more projects" in output


def test_project_artifact_dirs_count():
    assert len(PROJECT_ARTIFACT_DIRS) == 23


def test_find_project_artifacts_multiple_artifact_types(tmp_path: Path):
    proj = tmp_path / "multiproj"
    (proj / "node_modules").mkdir(parents=True)
    (proj / "node_modules" / "pkg").write_text("x" * 100)
    (proj / "dist").mkdir(parents=True)
    (proj / "dist" / "bundle.js").write_text("y" * 200)

    home = tmp_path / "home"
    home.mkdir()

    result = find_project_artifacts(
        scan_roots=(str(tmp_path),),
        recent_days=0,
        home=home,
    )

    assert result["total_projects"] == 1
    proj_data = result["projects"][0]
    assert proj_data["artifact_count"] == 2
    assert "node_modules" in proj_data["artifact_types"]
    assert "dist" in proj_data["artifact_types"]
    assert proj_data["total_bytes"] == 300


def test_find_artifact_dirs_handles_symlinks(tmp_path: Path):
    real = tmp_path / "real" / "node_modules"
    real.mkdir(parents=True)
    (real / "pkg").write_text("x")

    link = tmp_path / "link"
    link.mkdir()
    symlink_target = link / "node_modules"
    try:
        os.symlink(real, symlink_target)
    except (OSError, AttributeError):
        pytest.skip("symlinks not supported on this platform")

    found = list(_find_artifact_dirs(tmp_path))
    assert symlink_target not in found
