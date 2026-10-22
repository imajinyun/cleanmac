"""Bounded discovery of superseded on-disk Chromium and updater versions.

Chromium-family browsers (Chrome, Edge, Brave) keep every shipped framework
version side by side under
``<App>.app/Contents/Frameworks/<Framework>.framework/Versions`` and expose
the active one through a ``Current`` symlink. Microsoft EdgeUpdater likewise
stages full update payloads under ``msedge-stable/<version>``.

Discovery mirrors Mole's old-version cleanup:

* framework versions keep the ``Current`` symlink target plus any newer
  directory whose mtime is greater (a freshly staged auto-update);
* EdgeUpdater payloads keep every payload not strictly older than the
  installed Edge, falling back to keep-the-newest only when the installed
  version cannot be read.

A missing, broken, or symlink-escaping ``Current`` marker fails closed and
yields no candidates, so a damaged install can never turn the active browser
version into a deletion target.
"""

from __future__ import annotations

import os
import plistlib
import re
from pathlib import Path

# (application bundle name, framework directory name) for the Chromium-family
# browsers that use the versioned framework layout.
FRAMEWORK_BROWSERS: dict[str, tuple[str, str]] = {
    "chrome": ("Google Chrome.app", "Google Chrome Framework.framework"),
    "edge": ("Microsoft Edge.app", "Microsoft Edge Framework.framework"),
    "brave": ("Brave Browser.app", "Brave Browser Framework.framework"),
}

# cleanmac category key -> FRAMEWORK_BROWSERS key.
FRAMEWORK_CATEGORY_BROWSERS = {
    "chromeOldVersions": "chrome",
    "edgeOldVersions": "edge",
    "braveOldVersions": "brave",
}

EDGE_UPDATER_PAYLOADS = Path("Library/Application Support/Microsoft/EdgeUpdater/apps/msedge-stable")


def _version_key(name: str) -> tuple[int, ...] | None:
    """Leading dotted-numeric version, e.g. ``138.0.3351.85`` -> (138, 0, …)."""
    match = re.match(r"^\s*(\d+(?:\.\d+)*)\s*$", name)
    if match is None:
        return None
    return tuple(int(part) for part in match.group(1).split("."))


def _is_older(candidate: str, reference: str) -> bool | None:
    """True only when ``candidate`` parses and sorts strictly below reference."""
    candidate_key = _version_key(candidate)
    reference_key = _version_key(reference)
    if candidate_key is None or reference_key is None:
        return None
    return candidate_key < reference_key


def _physical_directory(path: Path, boundary: Path) -> bool:
    """Directory with no symlink at or above it, contained inside boundary."""
    if not path.is_dir() or path.is_symlink():
        return False
    resolved_path = path.resolve(strict=False)
    resolved_boundary = boundary.resolve(strict=False)
    try:
        resolved_path.relative_to(resolved_boundary)
    except ValueError:
        return False
    current = path
    while current != boundary and current != boundary.parent:
        if current.is_symlink():
            return False
        current = current.parent
    return True


def _current_version_name(versions_dir: Path) -> str | None:
    """Basename of the Current symlink target, None when missing/unreadable."""
    current_link = versions_dir / "Current"
    if not current_link.is_symlink():
        return None
    try:
        target = os.readlink(current_link)
    except OSError:
        return None
    name = os.path.basename(target.rstrip("/"))
    return name or None


def _prunable_framework_versions(versions_dir: Path) -> list[Path]:
    """Framework version directories removable under the keep-Current rules."""
    if versions_dir.is_symlink() or not versions_dir.is_dir():
        return []
    current_name = _current_version_name(versions_dir)
    if current_name is None:
        return []
    current_dir = versions_dir / current_name
    # A broken Current target fails closed: never prune an unverifiable layout.
    if not _physical_directory(current_dir, versions_dir):
        return []
    try:
        current_mtime = current_dir.stat().st_mtime
        children = [child for child in versions_dir.iterdir() if _physical_directory(child, versions_dir)]
    except OSError:
        return []

    # Keep a directory newer than Current: a staged auto-update that Current
    # flips to on the next launch.
    newest_name = ""
    newest_mtime = 0.0
    for child in children:
        mtime = child.stat().st_mtime
        if mtime > newest_mtime:
            newest_mtime = mtime
            newest_name = child.name
    if newest_mtime <= current_mtime:
        newest_name = ""

    candidates: list[Path] = []
    seen: set[Path] = set()
    for child in children:
        if child.name == current_name or child.name == newest_name:
            continue
        identity = child.resolve(strict=False)
        if identity in seen:
            continue
        seen.add(identity)
        candidates.append(child)
    return candidates


def old_framework_version_dirs(root: Path, home: Path, app_name: str, framework_name: str) -> list[Path]:
    """List prunable framework versions for one browser.

    Looks in both the system ``/Applications`` tree and the user
    ``~/Applications`` tree; duplicate physical installs resolve to one set.
    """
    app_dirs = (
        root / "Applications" / app_name,
        home / "Applications" / app_name,
    )
    targets: list[Path] = []
    seen: set[Path] = set()
    for app_dir in app_dirs:
        versions_dir = app_dir / "Contents" / "Frameworks" / framework_name / "Versions"
        for candidate in _prunable_framework_versions(versions_dir):
            identity = candidate.resolve(strict=False)
            if identity in seen:
                continue
            seen.add(identity)
            targets.append(candidate)
    return targets


def _installed_edge_version(root: Path, home: Path) -> str | None:
    for app_dir in (
        root / "Applications" / "Microsoft Edge.app",
        home / "Applications" / "Microsoft Edge.app",
    ):
        plist_path = app_dir / "Contents" / "Info.plist"
        try:
            if plist_path.is_symlink() or not plist_path.is_file():
                continue
            with plist_path.open("rb") as handle:
                value = plistlib.load(handle).get("CFBundleShortVersionString")
        except (OSError, plistlib.InvalidFileException, ValueError):
            continue
        if isinstance(value, str) and _version_key(value) is not None:
            return value
    return None


def old_edge_updater_payloads(root: Path, home: Path) -> list[Path]:
    """Stale staged EdgeUpdater payloads for the stable Edge channel."""
    payload_root = home / EDGE_UPDATER_PAYLOADS
    if not _physical_directory(payload_root, home):
        return []
    try:
        version_dirs = [child for child in payload_root.iterdir() if _physical_directory(child, payload_root)]
    except OSError:
        return []

    keep: set[str] = set()
    installed_version = _installed_edge_version(root, home)
    if installed_version is None:
        # Without a known installed version the conservative rule keeps the
        # newest payload and requires at least two directories before pruning.
        if len(version_dirs) < 2:
            return []
        parseable: list[tuple[Path, tuple[int, ...]]] = []
        for child in version_dirs:
            key = _version_key(child.name)
            if key is not None:
                parseable.append((child, key))
        if not parseable:
            return []
        keep.add(max(parseable, key=lambda item: item[1])[0].name)

    targets: list[Path] = []
    seen: set[Path] = set()
    for child in version_dirs:
        if child.name in keep:
            continue
        if installed_version is not None:
            # Equal or newer payloads are pending updates, not leftovers;
            # unparseable names fail closed and stay on disk.
            older = _is_older(child.name, installed_version)
            if older is not True:
                continue
        identity = child.resolve(strict=False)
        if identity in seen:
            continue
        seen.add(identity)
        targets.append(child)
    return targets


def is_prunable_framework_version(path: Path, framework_name: str) -> bool:
    """Re-validate a single framework version path during policy checks."""
    if path.is_symlink() or not path.is_dir():
        return False
    versions_dir = path.parent
    parts = versions_dir.parts
    if len(parts) < 7:
        return False
    if (
        versions_dir.name != "Versions"
        or parts[-2] != framework_name
        or parts[-3] != "Frameworks"
        or parts[-4] != "Contents"
        or not parts[-5].endswith(".app")
        or parts[-6] != "Applications"
    ):
        return False
    prunable = {target.resolve(strict=False) for target in _prunable_framework_versions(versions_dir)}
    try:
        return path.resolve(strict=False) in prunable
    except OSError:
        return False


def home_root_for_updater_candidate(path: Path) -> Path | None:
    """Derive the home ancestor from an EdgeUpdater version-child path."""
    parts = path.parts
    suffix = EDGE_UPDATER_PAYLOADS.parts
    depth = len(suffix) + 1
    if not path.is_absolute() or len(parts) <= depth:
        return None
    if tuple(part for part in parts[-depth:-1]) != suffix:
        return None
    return Path(*parts[:-depth])


def is_prunable_updater_payload(path: Path, root: Path | None = None) -> bool:
    """Re-validate an EdgeUpdater payload during policy checks (plan replay)."""
    if path.is_symlink() or not path.is_dir():
        return False
    home = home_root_for_updater_candidate(path)
    if home is None:
        return False
    effective_root = root if root is not None else Path("/")
    prunable = {target.resolve(strict=False) for target in old_edge_updater_payloads(effective_root, home)}
    try:
        return path.resolve(strict=False) in prunable
    except OSError:
        return False
