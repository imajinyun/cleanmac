"""Bounded discovery of stale Neat Download Manager segment directories.

Neat Download Manager stores each in-progress download as a numbered
directory under ``~/Library/Application Support/com.NeatDownloadManager``
whose parts are written to ``seg.x0``, ``seg.x1``, … . The resume history
database (``NeatDB.db``) and every other file belong to the application and
must be preserved.

The age of ``seg.x0`` is a conservative stale-download heuristic, not proof
that a download cannot be resumed. This opt-in provider mirrors Mole's
``clean_neatdm_stale_segments`` routine:

* only direct children whose names are entirely numeric are considered;
* the child must be a physical directory containing ``seg.x0``;
* the ``seg.x0`` mtime must be at least ``STALE_SEGMENT_DAYS`` days old;
* symlinks at any point in the chain fail closed.
"""

from __future__ import annotations

import re
import time
from pathlib import Path

NEATDM_ROOT = Path("Library/Application Support/com.NeatDownloadManager")

# Keep segment directories younger than this threshold.
STALE_SEGMENT_DAYS = 30

_NUMBERED_DIR = re.compile(r"^[0-9]+$")


def _physical_inside(path: Path, boundary: Path) -> bool:
    """Directory with no symlink at or above it, contained inside boundary."""
    if not path.is_dir() or path.is_symlink() or boundary.is_symlink():
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


def _is_numbered_segment_dir(candidate: Path, root: Path) -> bool:
    if candidate.parent != root or not _NUMBERED_DIR.fullmatch(candidate.name):
        return False
    return _physical_inside(candidate, root)


def _segment_age_days(segment_dir: Path, *, now: float | None = None) -> float | None:
    marker = segment_dir / "seg.x0"
    if marker.is_symlink() or not marker.is_file():
        return None
    try:
        mtime = marker.stat().st_mtime
    except OSError:
        return None
    reference = time.time() if now is None else now
    return (reference - mtime) / 86400.0


def stale_segment_dirs(home: Path, *, min_age_days: float = STALE_SEGMENT_DAYS) -> list[Path]:
    """List removable numbered segment directories older than ``min_age_days``."""
    root = home / NEATDM_ROOT
    if not _physical_inside(root, home):
        return []
    try:
        children = list(root.iterdir())
    except OSError:
        return []
    targets: list[Path] = []
    for child in sorted(children):
        if not _is_numbered_segment_dir(child, root):
            continue
        age = _segment_age_days(child)
        if age is not None and age >= min_age_days:
            targets.append(child)
    return targets


def home_root_for_candidate(path: Path) -> Path | None:
    """Derive the home ancestor from a numbered segment-dir path."""
    suffix = NEATDM_ROOT.parts
    depth = len(suffix) + 1
    parts = path.parts
    if not path.is_absolute() or len(parts) <= depth:
        return None
    if tuple(part for part in parts[-depth:-1]) != suffix:
        return None
    return Path(*parts[:-depth])


def is_stale_segment(path: Path, home: Path, *, min_age_days: float = STALE_SEGMENT_DAYS) -> bool:
    """Re-validate a single segment path during policy checks (plan replay)."""
    root = home / NEATDM_ROOT
    if not _physical_inside(root, home):
        return False
    if not _is_numbered_segment_dir(path, root):
        return False
    age = _segment_age_days(path)
    return age is not None and age >= min_age_days


def is_stale_segment_candidate(path: Path, *, min_age_days: float = STALE_SEGMENT_DAYS) -> bool:
    """Policy-check variant that resolves the home root from the path itself."""
    home = home_root_for_candidate(path)
    if home is None:
        return False
    return is_stale_segment(path, home, min_age_days=min_age_days)
