"""Per-invocation application ownership and executable observations."""

from __future__ import annotations

import fnmatch
import glob
from collections.abc import Callable, Iterable
from pathlib import Path

from .protection_data import APP_CACHE_OWNER_PATHS, APP_PROCESS_ALIASES


def executable_matches(executable: str, application: str) -> bool:
    names = APP_PROCESS_ALIASES.get(application, (application,))
    basename = Path(executable).name
    for name in names:
        if basename == name or basename.startswith(name + " Helper"):
            return True
        if "Helper" in name and basename.startswith(name + " ("):
            return True
        if f"/{name}.app/Contents/" in executable:
            return True
    return False


def pattern_owns_path(pattern: str, path: Path) -> bool:
    if any(fnmatch.fnmatchcase(str(parent), pattern) for parent in (path, *path.parents)):
        return True
    prefix = pattern.split("*", 1)[0].split("?", 1)[0].split("[", 1)[0]
    if not prefix.startswith(str(path).rstrip("/") + "/"):
        return False
    # A broad candidate can contain another app's cache. Guard the parent too.
    if not path.is_dir() or path.is_symlink():
        return False
    return any(Path(match).is_relative_to(path) for match in glob.glob(pattern))


class ApplicationActivity:
    def __init__(
        self,
        *,
        home_root: Path,
        category_guards: Iterable[tuple[str, tuple[str, ...]]],
        read_processes: Callable[[], str | None],
    ) -> None:
        self.home_root = home_root.resolve(strict=False)
        self.read_processes = read_processes
        self.loaded = False
        self.executables: tuple[str, ...] | None = None
        self.bindings: list[tuple[str, str]] = []
        self.owners: dict[tuple[Path, str | None], list[str]] = {}
        for application, patterns in (*APP_CACHE_OWNER_PATHS.items(), *category_guards):
            for pattern in patterns:
                if pattern.startswith("~/"):
                    self.bindings.append((str(self.home_root / pattern[2:]).rstrip("/"), application))

    def applications(self, path: Path, category_guard: str | None = None) -> list[str]:
        path = path.resolve(strict=False)
        cache_key = (path, category_guard)
        if cache_key in self.owners:
            return self.owners[cache_key]
        names = {application for pattern, application in self.bindings if pattern_owns_path(pattern, path)}
        if category_guard:
            names.add(category_guard)
        try:
            parts = path.relative_to(self.home_root).parts
        except ValueError:
            parts = ()
        if (
            not names
            and len(parts) >= 3
            and parts[:2]
            in {
                ("Library", "Caches"),
                ("Library", "Application Support"),
                ("Library", "Logs"),
                ("Library", "logs"),
            }
        ):
            names.add(parts[2])
        if not names and len(parts) >= 3 and parts[:2] == ("Library", "Containers"):
            names.add(parts[2])
        result = sorted(names)
        self.owners[cache_key] = result
        return result

    def reason(self, path: Path, category_guard: str | None = None) -> str | None:
        applications = self.applications(path, category_guard)
        if not applications:
            return None
        if not self.loaded:
            output = self.read_processes()
            self.executables = (
                None if output is None else tuple(line.strip() for line in output.splitlines() if line.strip())
            )
            self.loaded = True
        if self.executables is None:
            return "process-state-unknown"
        if any(
            executable_matches(executable, application)
            for application in applications
            for executable in self.executables
        ):
            return "app-running"
        return None

    def metadata(self, path: Path, category_guard: str | None = None) -> dict[str, object]:
        applications = self.applications(path, category_guard)
        return {"application": applications[0] if applications else None, "applications": applications}
