from __future__ import annotations

import json
from pathlib import Path

import pytest

from cleancli.core import (
    CATEGORY_BY_KEY,
    PROJECT_ARTIFACT_MAX_SCAN_DEPTH,
    discover_project_artifact_targets,
    normalize_project_roots,
    project_root_logical_path,
)
from tests.helpers import make_sandbox, run_clean_json, run_cli

PROJECT_ARTIFACTS = CATEGORY_BY_KEY["projectArtifacts"]


# ---------------------------------------------------------------------------
# normalize_project_roots
# ---------------------------------------------------------------------------


def test_normalize_project_roots_accepts_home_scoped_absolute_paths(tmp_path: Path) -> None:
    roots = normalize_project_roots(
        (str(tmp_path / "Codes/demo"), str(tmp_path / "Codes/other")),
        root=Path("/"),
        home=tmp_path,
    )

    assert roots == (tmp_path / "Codes/demo", tmp_path / "Codes/other")


def test_normalize_project_roots_rejects_relative_paths(tmp_path: Path) -> None:
    with pytest.raises(SystemExit, match="absolute paths"):
        normalize_project_roots(("Codes/demo",), root=Path("/"), home=tmp_path)


def test_normalize_project_roots_rejects_paths_outside_home(tmp_path: Path) -> None:
    with pytest.raises(SystemExit, match="outside the active home"):
        normalize_project_roots(("/etc",), root=Path("/"), home=tmp_path)


def test_normalize_project_roots_rejects_home_itself(tmp_path: Path) -> None:
    with pytest.raises(SystemExit, match="root/home itself"):
        normalize_project_roots((str(tmp_path),), root=Path("/"), home=tmp_path)


def test_normalize_project_roots_remaps_and_dedupes_in_sandbox(tmp_path: Path) -> None:
    root = tmp_path / "sandbox"
    home = Path("/Users/tester")

    roots = normalize_project_roots(
        ("/Users/tester/Codes", "/Users/tester/Codes/../Codes"),
        root=root,
        home=home,
    )

    assert roots == (root / "Users/tester/Codes",)
    # Absolute inputs are remapped under the sandbox root; only a traversal
    # escape can land outside it, and that must be rejected.
    with pytest.raises(SystemExit, match="outside the active root"):
        normalize_project_roots(("/../../../etc",), root=root, home=home)
    with pytest.raises(SystemExit, match="root/home itself"):
        normalize_project_roots(("/",), root=root, home=home)


def test_project_root_logical_path_inverts_sandbox_remap(tmp_path: Path) -> None:
    root = tmp_path / "sandbox"
    physical = root / "Users/tester/Codes/demo"

    assert project_root_logical_path(physical, root=root) == "/Users/tester/Codes/demo"
    assert project_root_logical_path(Path("/Users/tester/Codes/demo"), root=Path("/")) == ("/Users/tester/Codes/demo")


# ---------------------------------------------------------------------------
# bounded artifact discovery
# ---------------------------------------------------------------------------


def test_discover_project_artifact_targets_is_bounded_and_name_exact(tmp_path: Path) -> None:
    codes = tmp_path / "Codes"
    node_modules = codes / "me/demo/node_modules"
    nested_target = codes / "me/rust/fuzz/target"
    at_depth_limit = codes / "a/b/c/d/e/node_modules"
    too_deep = codes / "a/b/c/d/e/f/node_modules"
    git_ignored = codes / "me/demo/.git/objects"
    source_file = codes / "me/demo/main.py"
    for path in (node_modules, nested_target, at_depth_limit, too_deep, git_ignored):
        path.mkdir(parents=True)
    source_file.parent.mkdir(parents=True, exist_ok=True)
    source_file.write_text("print('hi')", encoding="utf-8")
    (node_modules / "pkg").mkdir()
    (node_modules / "pkg/index.js").write_text("x", encoding="utf-8")

    targets = discover_project_artifact_targets(PROJECT_ARTIFACTS, (codes,))
    target_paths = {target.path for target in targets}

    assert node_modules in target_paths
    assert nested_target in target_paths
    assert at_depth_limit in target_paths
    # Discovery never descends into a matched artifact directory.
    assert node_modules / "pkg" not in target_paths
    # Depth is bounded at six and dot directories (.git) are not traversed.
    assert too_deep not in target_paths
    assert git_ignored not in target_paths
    assert all(target.delete_target and target.matched for target in targets)


def test_filter_reason_enforces_vendor_bin_obj_context_guards(tmp_path: Path) -> None:
    from cleancli.core import filter_reason

    php = tmp_path / "php-app"
    (php / "vendor").mkdir(parents=True)
    (php / "composer.json").write_text("{}")

    rails = tmp_path / "rails-app"
    (rails / "vendor").mkdir(parents=True)

    dotnet = tmp_path / "dotnet-app"
    (dotnet / "bin" / "Debug").mkdir(parents=True)
    (dotnet / "obj").mkdir(parents=True)
    (dotnet / "App.csproj").write_text("<Project/>")

    plain = tmp_path / "plain"
    (plain / "bin").mkdir(parents=True)
    (plain / "vendor").mkdir(parents=True)

    def reason(path: Path) -> str | None:
        return filter_reason(
            PROJECT_ARTIFACTS,
            path,
            root=Path("/"),
            include_patterns=(),
            exclude_patterns=(),
            older_than_days=0,
            name_regex=None,
        )

    # Discovery is name-based: every ambiguous name is a candidate target.
    target_paths = {target.path for target in discover_project_artifact_targets(PROJECT_ARTIFACTS, (tmp_path,))}
    assert {php / "vendor", rails / "vendor", dotnet / "bin", dotnet / "obj", plain / "bin"} <= target_paths

    # Policy skips the ambiguous names unless project context proves rebuildability.
    assert reason(php / "vendor") is None
    assert reason(dotnet / "bin") is None
    assert reason(dotnet / "obj") is None
    assert reason(rails / "vendor") == "artifact-context-mismatch"
    assert reason(plain / "vendor") == "artifact-context-mismatch"
    assert reason(plain / "bin") == "artifact-context-mismatch"


def test_project_artifact_scan_depth_constant_matches_purge() -> None:
    from cleancli import purge

    assert PROJECT_ARTIFACT_MAX_SCAN_DEPTH == purge.MAX_SCAN_DEPTH


# ---------------------------------------------------------------------------
# CLI end-to-end
# ---------------------------------------------------------------------------


def _make_project_tree(root: Path) -> dict[str, Path]:
    codes = root / "Users/tester/Codes"
    node_modules = codes / "demo/node_modules/pkg"
    target = codes / "rustapp/fuzz/target/debug"
    git_objects = codes / "demo/.git/objects"
    built_in = root / "Users/tester/Projects/legacy/node_modules"
    for path in (node_modules, target, git_objects, built_in):
        path.mkdir(parents=True)
    (node_modules / "index.js").write_text("x", encoding="utf-8")
    (target / "bin").write_text("bin", encoding="utf-8")
    (git_objects / "abc").write_text("g", encoding="utf-8")
    (built_in / "old.js").write_text("old", encoding="utf-8")
    (codes / "demo/main.py").write_text("src", encoding="utf-8")
    return {
        "codes": codes,
        "node_modules": codes / "demo/node_modules",
        "target": codes / "rustapp/fuzz/target",
        "built_in": root / "Users/tester/Projects/legacy/node_modules",
    }


def test_inspect_with_project_roots_replaces_built_in_roots() -> None:
    tmp, root, home = make_sandbox()
    with tmp:
        paths = _make_project_tree(root)
        report = run_clean_json(
            root,
            home,
            "inspect",
            "--categories",
            "projectArtifacts",
            "--project-roots",
            "/Users/tester/Codes",
            "--older-than-days",
            "0",
            "--limit",
            "100",
        )

        items = report["items"]
        assert isinstance(items, list)
        item_paths = {str(row["path"]) for row in items}
        assert str(paths["node_modules"]) in item_paths
        assert str(paths["target"]) in item_paths
        # Custom roots replace rather than extend the built-in ~/Projects roots.
        assert str(paths["built_in"]) not in item_paths
        # Artifact internals and source files are never candidates.
        assert not any(path.endswith("/pkg/index.js") for path in item_paths)
        assert not any(path.endswith("/main.py") for path in item_paths)


def test_inspect_applies_vendor_bin_obj_context_guards() -> None:
    tmp, root, home = make_sandbox()
    with tmp:
        codes = root / "Users/tester/Codes"
        php_vendor = codes / "php-app/vendor"
        php_vendor.mkdir(parents=True)
        (codes / "php-app/composer.json").write_text("{}")
        (php_vendor / "pkg").mkdir()
        (php_vendor / "pkg/file.php").write_text("<?php")

        rails_vendor = codes / "rails-app/vendor"
        rails_vendor.mkdir(parents=True)
        (rails_vendor / "junk.js").write_text("x")

        dotnet_bin = codes / "dotnet-app/bin/Debug/net8.0"
        dotnet_bin.mkdir(parents=True)
        (dotnet_bin / "App.dll").write_text("x")
        dotnet_obj = codes / "dotnet-app/obj"
        dotnet_obj.mkdir(parents=True)
        (dotnet_obj / "build.cache").write_text("x")
        (codes / "dotnet-app/App.csproj").write_text("<Project/>")

        plain_bin = codes / "scripts/bin"
        plain_bin.mkdir(parents=True)
        (plain_bin / "tool").write_text("#!/bin/sh")

        report = run_clean_json(
            root,
            home,
            "inspect",
            "--categories",
            "projectArtifacts",
            "--project-roots",
            "/Users/tester/Codes",
            "--older-than-days",
            "0",
            "--limit",
            "100",
        )

        items = report["items"]
        skipped_rows = report["skipped"]
        assert isinstance(items, list)
        assert isinstance(skipped_rows, list)
        item_paths = {str(row["path"]) for row in items}
        skipped = {str(row["path"]): str(row["reason"]) for row in skipped_rows}

        assert str(php_vendor) in item_paths
        assert str(codes / "dotnet-app/bin") in item_paths
        assert str(dotnet_obj) in item_paths
        assert str(rails_vendor) not in item_paths
        assert str(plain_bin) not in item_paths
        assert skipped.get(str(rails_vendor)) == "artifact-context-mismatch"
        assert skipped.get(str(plain_bin)) == "artifact-context-mismatch"


def test_plan_carries_logical_project_roots_and_validates() -> None:
    tmp, root, home = make_sandbox()
    with tmp:
        paths = _make_project_tree(root)
        plan_file = root / "plan.json"
        result = run_cli(
            "--root",
            str(root),
            "--home",
            str(home),
            "--json",
            "plan",
            "--categories",
            "projectArtifacts",
            "--project-roots",
            "/Users/tester/Codes",
            "--older-than-days",
            "0",
        )
        plan_file.write_text(result.stdout, encoding="utf-8")
        plan = json.loads(result.stdout)

        assert plan["project_roots"] == ["/Users/tester/Codes"]
        assert "--project-roots /Users/tester/Codes" in plan["replay_command"]

        validation = json.loads(
            run_cli(
                "--root",
                str(root),
                "--home",
                str(home),
                "--json",
                "validate-plan",
                "--plan-file",
                str(plan_file),
            ).stdout
        )
        assert validation["valid"] is True
        preview_paths = {row["path"] for row in validation["preview"]["items"]}
        assert str(paths["node_modules"]) in preview_paths
        assert "--project-roots /Users/tester/Codes" in validation["replay_clean_command"]


def test_plan_replay_restores_project_roots_and_executes_trash() -> None:
    tmp, root, home = make_sandbox()
    with tmp:
        paths = _make_project_tree(root)
        plan_file = root / "plan.json"
        plan_file.write_text(
            run_cli(
                "--root",
                str(root),
                "--home",
                str(home),
                "--json",
                "plan",
                "--categories",
                "projectArtifacts",
                "--project-roots",
                "/Users/tester/Codes",
                "--older-than-days",
                "0",
            ).stdout,
            encoding="utf-8",
        )
        op_log = root / "op.jsonl"

        report = run_clean_json(
            root,
            home,
            "--plan-file",
            str(plan_file),
            "--require-plan-context",
            "--execute",
            "--delete-mode",
            "trash",
            "--operation-log",
            str(op_log),
        )

        assert report["dry_run"] is False
        assert report["deleted_count"] == 2
        assert not paths["node_modules"].exists()
        assert not paths["target"].exists()
        # Source and VCS data stay in place.
        assert (paths["codes"] / "demo/main.py").exists()
        assert (paths["codes"] / "demo/.git/objects/abc").exists()
        # The unrelated built-in root was never in scope.
        assert paths["built_in"].exists()


def test_project_root_equal_to_sandbox_root_is_rejected() -> None:
    tmp, root, home = make_sandbox()
    with tmp:
        result = run_cli(
            "--root",
            str(root),
            "--home",
            str(home),
            "--json",
            "clean",
            "inspect",
            "--categories",
            "projectArtifacts",
            "--project-roots",
            "/",
            check=False,
        )

        assert result.returncode != 0
        error = json.loads(result.stderr)["error"]
        assert "root/home itself" in error["message"]


def test_project_root_outside_home_is_rejected_on_live_root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    result = run_cli(
        "--json",
        "clean",
        "inspect",
        "--categories",
        "projectArtifacts",
        "--project-roots",
        "/etc",
        check=False,
    )

    assert result.returncode != 0
    error = json.loads(result.stderr)["error"]
    assert "outside the active home" in error["message"]
