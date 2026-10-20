from __future__ import annotations

import os
import time
from pathlib import Path

import pytest

from cleancli.purge import (
    DEFAULT_RECENT_DAYS,
    DEFAULT_SCAN_ROOTS,
    MAX_SCAN_DEPTH,
    PROJECT_ARTIFACT_DIRS,
    _dir_size,
    _display_path,
    _find_artifact_dirs,
    _human_size,
    _resolve_roots,
    artifact_context_allows,
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
    # Mole-aligned catalog (MOLE_PURGE_TARGETS) plus cleanmac extras
    # (.cache, CMakeFiles, bazel-out, buck-out, _build, deps, bin, obj).
    assert len(PROJECT_ARTIFACT_DIRS) == 40
    assert len(set(PROJECT_ARTIFACT_DIRS)) == len(PROJECT_ARTIFACT_DIRS)


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


# ---------------------------------------------------------------------------
# Mole-aligned catalog: default roots, depth, and context guards
# ---------------------------------------------------------------------------


def test_default_scan_roots_match_mole_aligned_set():
    assert DEFAULT_SCAN_ROOTS == (
        "~/Projects",
        "~/GitHub",
        "~/dev",
        "~/code",
        "~/work",
        "~/www",
        "~/Code",
        "~/Workspace",
        "~/Repos",
        "~/Development",
    )
    assert not any("CloudStorage" in root for root in DEFAULT_SCAN_ROOTS)
    assert not any(".codex" in root or ".claude" in root for root in DEFAULT_SCAN_ROOTS)


def test_max_scan_depth_is_six():
    assert MAX_SCAN_DEPTH == 6


def test_find_artifact_dirs_reaches_depth_six(tmp_path: Path):
    reachable = tmp_path / "a" / "b" / "c" / "d" / "e" / "node_modules"
    too_deep = tmp_path / "a" / "b" / "c" / "d" / "e" / "f" / "node_modules"
    reachable.mkdir(parents=True)
    too_deep.mkdir(parents=True)

    found = set(_find_artifact_dirs(tmp_path))
    assert reachable in found
    assert too_deep not in found


def test_find_artifact_dirs_recognizes_new_dotted_artifacts(tmp_path: Path):
    for name in (".tox", ".nox", ".terragrunt-cache", ".turbo", ".zig-cache", ".angular"):
        (tmp_path / f"proj-{name.lstrip('.')}" / name).mkdir(parents=True)

    found = {p.name for p in _find_artifact_dirs(tmp_path)}
    assert {".tox", ".nox", ".terragrunt-cache", ".turbo", ".zig-cache", ".angular"} <= found


def test_vendor_requires_composer_context(tmp_path: Path):
    php = tmp_path / "php-app"
    (php / "vendor").mkdir(parents=True)
    (php / "composer.json").write_text("{}")

    rails = tmp_path / "rails-app"
    (rails / "vendor").mkdir(parents=True)
    (rails / "Gemfile").write_text("")
    (rails / "config").mkdir()
    (rails / "config" / "application.rb").write_text("")

    go_app = tmp_path / "go-app"
    (go_app / "vendor").mkdir(parents=True)
    (go_app / "go.mod").write_text("module x")

    plain = tmp_path / "plain"
    (plain / "vendor").mkdir(parents=True)

    found = set(_find_artifact_dirs(tmp_path))
    assert php / "vendor" in found
    assert rails / "vendor" not in found
    assert go_app / "vendor" not in found
    assert plain / "vendor" not in found


def test_protected_vendor_is_pruned(tmp_path: Path):
    # A nested rebuildable artifact inside a protected vendor tree must not
    # surface: matched artifact names prune the walk whether or not the
    # context guard accepts them.
    go_app = tmp_path / "go-app"
    nested = go_app / "vendor" / "example.com" / "pkg" / "node_modules"
    nested.mkdir(parents=True)
    (go_app / "go.mod").write_text("module x")

    found = set(_find_artifact_dirs(tmp_path))
    assert not any(path.name == "node_modules" for path in found)


def test_bin_and_obj_require_dotnet_context(tmp_path: Path):
    dotnet = tmp_path / "dotnet-app"
    (dotnet / "bin" / "Debug" / "net8.0").mkdir(parents=True)
    (dotnet / "obj").mkdir(parents=True)
    (dotnet / "App.csproj").write_text("<Project/>")

    dotnet_release = tmp_path / "dotnet-rel"
    (dotnet_release / "bin" / "Release").mkdir(parents=True)
    (dotnet_release / "Lib.fsproj").write_text("<Project/>")

    bin_without_config = tmp_path / "half-dotnet"
    (bin_without_config / "bin" / "stuff").mkdir(parents=True)
    (bin_without_config / "Half.vbproj").write_text("<Project/>")

    plain = tmp_path / "plain"
    (plain / "bin").mkdir(parents=True)
    (plain / "obj").mkdir(parents=True)

    found = set(_find_artifact_dirs(tmp_path))
    assert dotnet / "bin" in found
    assert dotnet / "obj" in found
    assert dotnet_release / "bin" in found
    assert bin_without_config / "bin" not in found
    assert plain / "bin" not in found
    assert plain / "obj" not in found


def test_derived_data_guard(tmp_path: Path):
    project_local = tmp_path / "MyApp" / "DerivedData"
    project_local.mkdir(parents=True)
    global_dd = tmp_path / "Library" / "Developer" / "Xcode" / "DerivedData"
    global_dd.mkdir(parents=True)

    assert artifact_context_allows("DerivedData", project_local) is True
    assert artifact_context_allows("DerivedData", global_dd) is False

    found = set(_find_artifact_dirs(tmp_path))
    assert project_local in found
    assert global_dd not in found


def test_unguarded_names_still_match_without_context(tmp_path: Path):
    plain = tmp_path / "plain" / "node_modules"
    plain.mkdir(parents=True)
    assert artifact_context_allows("node_modules", plain) is True
    assert artifact_context_allows("vendor", plain) is False
