"""Bounded discovery of superseded on-disk AI CLI versions.

The tools keep every downloaded version side by side and expose the active
install through a marker symlink. Discovery lists every physical version
directory except the active one. Missing, dangling, symlinked, or escaping
markers fail closed and yield no candidates, so a broken install can never
turn the active version into a deletion candidate.
"""

from __future__ import annotations

from pathlib import Path

from .protection_data import AI_TOOL_VERSION_ROOTS


def _physical_directory(path: Path, boundary: Path) -> bool:
    if not path.is_dir() or path.is_symlink() or not path.is_relative_to(boundary):
        return False
    current = path
    while current != boundary.parent:
        if current.is_symlink():
            return False
        current = current.parent
    return True


def _active_version(marker: Path, versions_root: Path) -> Path | None:
    """Resolve the active version directory; None when the marker is unsafe."""
    try:
        if not marker.is_symlink():
            return None
        active = marker.resolve(strict=False)
        root = versions_root.resolve(strict=False)
        relative = active.relative_to(root)
    except (OSError, ValueError):
        return None
    # One part points at the version directory (codex current); two parts
    # point at the active binary inside it (cursor-agent shim). The resolved
    # target must exist so a dangling marker fails closed instead of pinning
    # the directory that merely happens to share its name.
    if not relative.parts or len(relative.parts) > 2 or not active.exists():
        return None
    version_dir = root / relative.parts[0]
    return version_dir if _physical_directory(version_dir, root) else None


def _prunable_versions(versions_root: Path, marker: Path) -> list[Path]:
    # Resolve the marker before touching the versions root: no marker means no
    # candidates, even if old-looking directories are present.
    active = _active_version(marker, versions_root)
    if active is None or not _physical_directory(versions_root, versions_root.parent.parent.parent):
        return []
    try:
        children = sorted(versions_root.iterdir())
    except OSError:
        return []
    active_resolved = active.resolve(strict=False)
    targets: list[Path] = []
    seen: set[Path] = set()
    for child in children:
        if child.name.startswith(".") or not _physical_directory(child, versions_root):
            continue
        resolved = child.resolve(strict=False)
        if resolved == active_resolved or active_resolved.is_relative_to(resolved):
            continue
        if resolved in seen:
            continue
        seen.add(resolved)
        targets.append(child)
    return targets


def old_version_targets(home_root: Path) -> list[Path]:
    """Return non-active AI CLI version directories under the given home."""
    targets: list[Path] = []
    seen: set[Path] = set()
    installations = (
        (home_root / ".codex/packages/standalone/releases", home_root / ".codex/packages/standalone/current"),
        (home_root / ".local/share/cursor-agent/versions", home_root / ".local/bin/cursor-agent"),
    )
    for versions_root, marker in installations:
        for target in _prunable_versions(versions_root, marker):
            resolved = target.resolve(strict=False)
            if resolved not in seen:
                seen.add(resolved)
                targets.append(target)
    return targets


_VERSION_ROOT_SUFFIXES = (
    (".codex", "packages", "standalone", "releases"),
    (".local", "share", "cursor-agent", "versions"),
)


def home_root_for_candidate(path: Path) -> Path | None:
    """Derive the sandbox home ancestor from a direct version-child path."""
    parts = path.parts
    if not path.is_absolute():
        return None
    for suffix in _VERSION_ROOT_SUFFIXES:
        depth = len(suffix) + 1
        if len(parts) > depth and tuple(part.lower() for part in parts[-depth:-1]) == suffix:
            return Path(*parts[:-depth])
    return None


def is_known_version_shape(path: Path) -> bool:
    """Lexical membership in a version root; the provider adds FS validation."""
    lowered = str(path).lower()
    return any(root in lowered for root in AI_TOOL_VERSION_ROOTS)


def is_prunable_version_dir(path: Path, home_root: Path) -> bool:
    """Re-validate a candidate during policy checks (plan replay safety)."""
    prunable = {target.resolve(strict=False) for target in old_version_targets(home_root)}
    try:
        return path.resolve(strict=False) in prunable
    except OSError:
        return False
