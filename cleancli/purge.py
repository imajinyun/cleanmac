"""Project artifact purge — find build artifacts across project directories.

Scans configurable project roots for known build/dependency directories
(node_modules, target, venv, dist, build, etc.) and reports per-project
sizes. Defaults to skipping projects modified in the last 7 days.
"""

from __future__ import annotations

import os
import time
from collections.abc import Iterator
from pathlib import Path
from typing import Any

PROJECT_ARTIFACT_DIRS: tuple[str, ...] = (
    "node_modules",
    "target",
    "venv",
    ".venv",
    "dist",
    "build",
    ".build",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    ".gradle",
    ".next",
    ".nuxt",
    ".cache",
    "Pods",
    "DerivedData",
    ".dart_tool",
    "CMakeFiles",
    "bazel-out",
    "buck-out",
    "_build",
    "deps",
)

DEFAULT_SCAN_ROOTS: tuple[str, ...] = (
    "~/Projects",
    "~/GitHub",
    "~/dev",
    "~/code",
    "~/work",
)

DEFAULT_RECENT_DAYS = 7
MAX_SCAN_DEPTH = 4


def _human_size(size: int | None) -> str:
    if size is None:
        return "0 B"
    if size < 1024:
        return f"{size} B"
    if size < 1024 * 1024:
        return f"{size / 1024:.1f} KB"
    if size < 1024 * 1024 * 1024:
        return f"{size / (1024 * 1024):.1f} MB"
    if size < 1024 * 1024 * 1024 * 1024:
        return f"{size / (1024 * 1024 * 1024):.1f} GB"
    return f"{size / (1024 * 1024 * 1024 * 1024):.1f} TB"


def _display_path(path: Path | str) -> str:
    p = Path(path)
    home = Path.home()
    try:
        return "~" + str(p)[len(str(home)) :] if str(p).startswith(str(home)) else str(p)
    except Exception:
        return str(p)


def _resolve_roots(roots: tuple[str, ...], *, home: Path) -> list[Path]:
    resolved: list[Path] = []
    for root in roots:
        p = Path(root).expanduser()
        if not p.is_absolute():
            p = home / p
        if p.exists() and p.is_dir():
            resolved.append(p)
    return resolved


def _dir_size(path: Path) -> int:
    total = 0
    try:
        for entry in os.scandir(path):
            try:
                if entry.is_file(follow_symlinks=False):
                    total += entry.stat(follow_symlinks=False).st_size
                elif entry.is_dir(follow_symlinks=False):
                    total += _dir_size(Path(entry.path))
            except (OSError, PermissionError):
                continue
    except (OSError, PermissionError):
        pass
    return total


def _find_artifact_dirs(root: Path, *, max_depth: int = MAX_SCAN_DEPTH) -> Iterator[Path]:
    if max_depth <= 0:
        return
    try:
        entries = list(os.scandir(root))
    except (OSError, PermissionError):
        return
    for entry in entries:
        try:
            if entry.name.startswith(".") and entry.name not in {
                ".venv",
                ".build",
                ".pytest_cache",
                ".mypy_cache",
                ".ruff_cache",
                ".gradle",
                ".next",
                ".nuxt",
                ".cache",
                ".dart_tool",
            }:
                continue
            if entry.is_dir(follow_symlinks=False):
                if entry.name in PROJECT_ARTIFACT_DIRS:
                    yield Path(entry.path)
                else:
                    yield from _find_artifact_dirs(Path(entry.path), max_depth=max_depth - 1)
        except (OSError, PermissionError):
            continue


def find_project_artifacts(
    *,
    scan_roots: tuple[str, ...] | None = None,
    recent_days: int = DEFAULT_RECENT_DAYS,
    home: Path,
) -> dict[str, Any]:
    roots = _resolve_roots(scan_roots or DEFAULT_SCAN_ROOTS, home=home)
    cutoff = time.time() - recent_days * 86400

    projects: dict[str, dict[str, Any]] = {}

    for scan_root in roots:
        for artifact in _find_artifact_dirs(scan_root):
            try:
                project_dir = artifact.parent
                project_key = str(project_dir)
                artifact_name = artifact.name

                stat = artifact.stat()
                size_bytes = _dir_size(artifact)
                mtime = stat.st_mtime
                is_recent = mtime > cutoff

                if project_key not in projects:
                    project_mtime = 0.0
                    try:
                        project_stat = project_dir.stat()
                        project_mtime = project_stat.st_mtime
                    except (OSError, PermissionError):
                        pass
                    projects[project_key] = {
                        "project": _display_path(project_dir),
                        "project_path": str(project_dir),
                        "total_bytes": 0,
                        "artifact_count": 0,
                        "artifact_types": [],
                        "is_recent": project_mtime > cutoff,
                        "last_modified": project_mtime,
                        "artifacts": [],
                        "default_selected": not (project_mtime > cutoff),
                    }

                proj = projects[project_key]
                proj["total_bytes"] = int(proj["total_bytes"]) + size_bytes
                proj["artifact_count"] = int(proj["artifact_count"]) + 1
                if artifact_name not in proj["artifact_types"]:
                    proj["artifact_types"].append(artifact_name)
                proj["artifacts"].append(
                    {
                        "name": artifact_name,
                        "path": str(artifact),
                        "bytes": size_bytes,
                        "is_recent": is_recent,
                    }
                )
            except (OSError, PermissionError):
                continue

    project_list = sorted(projects.values(), key=lambda p: int(p["total_bytes"]), reverse=True)

    total_bytes = sum(int(p["total_bytes"]) for p in project_list)
    recent_count = sum(1 for p in project_list if p["is_recent"])
    selected_count = sum(1 for p in project_list if p["default_selected"])

    return {
        "schema": "cleanmac.project-purge.v1",
        "scan_roots": [str(r) for r in roots],
        "recent_days": recent_days,
        "total_projects": len(project_list),
        "total_bytes": total_bytes,
        "total_human": _human_size(total_bytes),
        "recent_projects": recent_count,
        "default_selected_count": selected_count,
        "projects": project_list,
    }


def render_purge_human(report: dict[str, Any]) -> str:
    lines: list[str] = []
    lines.append("Project Artifact Purge")
    lines.append("=" * 60)
    lines.append(f"Scan roots: {', '.join(str(r) for r in report['scan_roots'])}")
    lines.append(f"Recent threshold: {report['recent_days']} days")
    lines.append(
        f"Found {report['total_projects']} projects | "
        f"Total: {report['total_human']} | "
        f"Recent (skipped by default): {report['recent_projects']}"
    )
    lines.append("")

    projects = list(report["projects"]) if isinstance(report.get("projects"), list) else []

    if not projects:
        lines.append("No project artifacts found.")
        return "\n".join(lines)

    lines.append(f"{'':>3} {'Project':<40} {'Type':<15} {'Size':>10} {'Recent':<7}")
    lines.append("-" * 80)

    for i, proj in enumerate(projects[:30], 1):
        types = ", ".join(list(proj["artifact_types"])[:3])
        size = _human_size(int(proj["total_bytes"]))
        recent = "yes" if proj["is_recent"] else "no"
        marker = "●" if proj["default_selected"] else "○"
        lines.append(f"{marker}{i:>2} {str(proj['project'])[:39]:<40} {types[:14]:<15} {size:>10} {recent:<7}")

    if len(projects) > 30:
        lines.append(f"... and {len(projects) - 30} more projects")

    lines.append("")
    lines.append("Legend: ● = selected by default  ○ = recent (skipped by default)")
    return "\n".join(lines)
