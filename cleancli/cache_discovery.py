"""Bounded discovery of regenerable Chromium and Electron cache subtrees."""

from __future__ import annotations

from pathlib import Path

from .protection_data import (
    AMBIGUOUS_APP_CACHE_DIRECTORIES,
    APP_SUPPORT_CACHE_DIRECTORIES,
    KNOWN_ELECTRON_CACHE_APPS,
)

# Chromium/Electron per-profile layouts place caches under Default/ and
# Partitions/<partition>/ below the application data directory. Descent is
# restricted to recognized applications so a profile directory can never
# authorize deletion inside an unrecognized application data directory.
PROFILE_DEFAULT_DIRECTORY = "Default"
PARTITIONS_DIRECTORY = "Partitions"


def _physical_directory(path: Path, boundary: Path) -> bool:
    if not path.is_dir() or not path.is_relative_to(boundary):
        return False
    current = path
    while current != boundary.parent:
        if current.is_symlink():
            return False
        current = current.parent
    return True


def app_has_cache_markers(app: Path) -> bool:
    return any(_physical_directory(app / name, app.parent) for name in APP_SUPPORT_CACHE_DIRECTORIES)


def _partition_roots(partitions: Path, home_root: Path) -> list[Path]:
    if not _physical_directory(partitions, home_root):
        return []
    try:
        children = sorted(partitions.iterdir())
    except OSError:
        return []
    return [child for child in children if _physical_directory(child, home_root)]


def profile_roots(app: Path, home_root: Path) -> tuple[Path, ...]:
    """Application root plus bounded Chromium profile roots for known apps."""
    roots: list[Path] = [app]
    if app.name not in KNOWN_ELECTRON_CACHE_APPS:
        return tuple(roots)
    # Partitions can sit beside the profiles (App/Partitions/<name>) or inside
    # the active profile (App/Default/Partitions/<name>); both are Chromium
    # defaults for non-persistent and in-profile storage partitions.
    roots.extend(_partition_roots(app / PARTITIONS_DIRECTORY, home_root))
    default_profile = app / PROFILE_DEFAULT_DIRECTORY
    if _physical_directory(default_profile, home_root):
        roots.append(default_profile)
        roots.extend(_partition_roots(default_profile / PARTITIONS_DIRECTORY, home_root))
    return tuple(roots)


def app_support_cache_directories(home_root: Path) -> list[Path]:
    support = home_root / "Library/Application Support"
    if not _physical_directory(support, home_root):
        return []
    try:
        apps = sorted(support.iterdir())
    except OSError:
        return []
    paths: list[Path] = []
    for app in apps:
        if not _physical_directory(app, home_root):
            continue
        names: tuple[str, ...] = APP_SUPPORT_CACHE_DIRECTORIES
        if app.name in KNOWN_ELECTRON_CACHE_APPS or app_has_cache_markers(app):
            names = (*names, *AMBIGUOUS_APP_CACHE_DIRECTORIES)
        for root in profile_roots(app, home_root):
            paths.extend(root / name for name in names if _physical_directory(root / name, home_root))
    return paths


def _relative_cache_root(app: Path, relative: tuple[str, ...]) -> Path | None:
    marker_names = (*APP_SUPPORT_CACHE_DIRECTORIES, *AMBIGUOUS_APP_CACHE_DIRECTORIES)
    prefixes: list[tuple[str, ...]] = [()]
    if relative and relative[0] == PROFILE_DEFAULT_DIRECTORY:
        prefixes.append((PROFILE_DEFAULT_DIRECTORY,))
    if len(relative) >= 2 and relative[0] == PARTITIONS_DIRECTORY:
        prefixes.append((PARTITIONS_DIRECTORY, relative[1]))
    if len(relative) >= 3 and relative[:2] == (PROFILE_DEFAULT_DIRECTORY, PARTITIONS_DIRECTORY):
        prefixes.append((PROFILE_DEFAULT_DIRECTORY, PARTITIONS_DIRECTORY, relative[2]))
    for prefix in prefixes:
        tail = relative[len(prefix) :]
        for name in marker_names:
            cache_parts = Path(name).parts
            if tail[: len(cache_parts)] == cache_parts:
                return app.joinpath(*prefix, *cache_parts)
    return None


def app_cache_root(path: Path) -> Path | None:
    parts = path.parts
    for index in range(len(parts) - 3):
        if parts[index : index + 2] != ("Library", "Application Support"):
            continue
        app = Path(*parts[: index + 3])
        relative = parts[index + 3 :]
        cache_root = _relative_cache_root(app, relative)
        if cache_root is not None:
            return cache_root
    return None


def cache_application_root(path: Path) -> Path | None:
    app = app_cache_root(path)
    if app is None:
        return None
    while app.parent.name != "Application Support":
        app = app.parent
    return app


def valid_app_cache_path(path: Path) -> bool:
    cache = app_cache_root(path)
    if cache is None:
        return False
    app = cache
    while app.parent.name != "Application Support":
        app = app.parent
    if not _physical_directory(cache, app.parent.parent.parent):
        return False
    if cache.name in AMBIGUOUS_APP_CACHE_DIRECTORIES:
        return app.name in KNOWN_ELECTRON_CACHE_APPS or app_has_cache_markers(app)
    return True


def known_regenerable_app_cache(path: Path, protected_fragment: str | None = None) -> bool:
    """Lexical exception for known protected app roots, after path validation."""
    if path.is_relative_to(Path("/Library")):
        return False
    cache = app_cache_root(path)
    if cache is None:
        return False
    app = cache
    while app.parent.name != "Application Support":
        app = app.parent
    return app.name in KNOWN_ELECTRON_CACHE_APPS and (
        protected_fragment is None or protected_fragment == f"/library/application support/{app.name.lower()}"
    )
