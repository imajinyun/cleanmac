"""Bounded discovery of regenerable Chromium and Electron cache subtrees."""

from __future__ import annotations

from pathlib import Path

from .protection_data import (
    AMBIGUOUS_APP_CACHE_DIRECTORIES,
    APP_SUPPORT_CACHE_DIRECTORIES,
    KNOWN_ELECTRON_CACHE_APPS,
)


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
        paths.extend(app / name for name in names if _physical_directory(app / name, home_root))
    return paths


def app_cache_root(path: Path) -> Path | None:
    parts = path.parts
    for index in range(len(parts) - 3):
        if parts[index : index + 2] != ("Library", "Application Support"):
            continue
        app = Path(*parts[: index + 3])
        relative = parts[index + 3 :]
        for name in (*APP_SUPPORT_CACHE_DIRECTORIES, *AMBIGUOUS_APP_CACHE_DIRECTORIES):
            cache_parts = Path(name).parts
            if relative[: len(cache_parts)] == cache_parts:
                return app / name
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
