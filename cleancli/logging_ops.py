"""Log path, rotation, and append helpers for clean workflows."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Sequence


def log_path_for_context(
    path: str,
    *,
    root: Path,
    home: Path,
    remap_path: Callable[[str], str],
) -> Path:
    if path.startswith("~/") or path == "~":
        return Path(remap_path(path)).resolve(strict=False)
    return Path(path).expanduser().resolve(strict=False)


def operation_log_path_for_context(
    path: str,
    *,
    root: Path,
    home: Path,
    remap_path: Callable[[str], str],
) -> Path:
    if path.startswith("~/") or path == "~":
        return Path(remap_path(path)).expanduser()
    return Path(path).expanduser()


def rotate_log_once(path: Path, *, max_bytes: int, remove_path: Callable[[Path], None]) -> bool:
    if max_bytes <= 0 or not path.exists() or path.stat().st_size <= max_bytes:
        return False
    rotated = path.with_name(f"{path.name}.1")
    remove_path(rotated)
    path.rename(rotated)
    return True


def deletion_log_path_for_context(
    *,
    root: Path,
    home: Path,
    delete_log_file: str,
    remap_path: Callable[[str], str],
) -> Path:
    return log_path_for_context(delete_log_file, root=root, home=home, remap_path=remap_path)


def append_deletion_log(
    *,
    root: Path,
    home: Path,
    delete_log_file: str,
    remap_path: Callable[[str], str],
    display_path: Callable[[Path | str], str],
    mode: str,
    status: str,
    path: Path | str,
    bytes_value: int | str | None,
    detail: str = "",
) -> str:
    log_path = deletion_log_path_for_context(
        root=root,
        home=home,
        delete_log_file=delete_log_file,
        remap_path=remap_path,
    )
    log_path.parent.mkdir(parents=True, exist_ok=True)
    size_text = "unknown" if bytes_value is None else str(bytes_value)
    line = "\t".join(
        [datetime.now(timezone.utc).isoformat(), mode, size_text, status, str(path), detail.replace("\t", " ")]
    )
    with log_path.open("a", encoding="utf-8") as handle:
        handle.write(line + "\n")
    return display_path(log_path)


def batch_append_deletion_log(
    *,
    root: Path,
    home: Path,
    delete_log_file: str,
    remap_path: Callable[[str], str],
    display_path: Callable[[Path | str], str],
    entries: list[dict[str, Any]],
) -> str:
    log_path = deletion_log_path_for_context(
        root=root,
        home=home,
        delete_log_file=delete_log_file,
        remap_path=remap_path,
    )
    if not entries:
        return display_path(log_path)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    now = datetime.now(timezone.utc).isoformat()
    lines_out = []
    for entry in entries:
        size_text = "unknown" if entry.get("bytes_value") is None else str(entry["bytes_value"])
        detail = str(entry.get("detail", "")).replace("\t", " ")
        lines_out.append(
            "\t".join([now, str(entry["mode"]), size_text, str(entry["status"]), str(entry["path"]), detail])
        )
    with log_path.open("a", encoding="utf-8") as handle:
        handle.write("\n".join(lines_out) + "\n")
    return display_path(log_path)


def preflight_operation_log(
    path: str,
    *,
    root: Path,
    home: Path,
    remap_path: Callable[[str], str],
    display_path: Callable[[Path | str], str],
    rotate_bytes: int,
    remove_path: Callable[[Path], None],
) -> dict[str, Any]:
    log_path = operation_log_path_for_context(path, root=root, home=home, remap_path=remap_path)
    try:
        if log_path.parent.exists() and log_path.parent.is_symlink():
            raise RuntimeError(f"Refusing to use symlinked operation log directory: {log_path.parent}")
        log_path.parent.mkdir(parents=True, exist_ok=True)
        if log_path.parent.is_symlink():
            raise RuntimeError(f"Refusing to use symlinked operation log directory: {log_path.parent}")
        if log_path.exists() and log_path.is_symlink():
            raise RuntimeError(f"Refusing to use symlinked operation log file: {log_path}")
        if log_path.exists() and log_path.is_dir():
            raise RuntimeError(f"Refusing to use directory as operation log file: {log_path}")
        rotated = rotate_log_once(log_path, max_bytes=rotate_bytes, remove_path=remove_path)
        with log_path.open("a", encoding="utf-8"):
            pass
    except Exception as exc:
        return {
            "schema": "cleanmac.operation-log-status.v1",
            "status": "failed",
            "path": display_path(log_path),
            "rotated": False,
            "error": str(exc),
        }
    return {
        "schema": "cleanmac.operation-log-status.v1",
        "status": "ready",
        "path": display_path(log_path),
        "rotated": rotated,
        "error": None,
    }


def append_operation_log(
    path: str,
    entries: Sequence[dict[str, Any]],
    *,
    root: Path,
    home: Path,
    remap_path: Callable[[str], str],
    display_path: Callable[[Path | str], str],
    rotate_bytes: int,
    remove_path: Callable[[Path], None],
    ensure_entry: Callable[[dict[str, Any]], dict[str, Any]],
    rotate: bool = True,
) -> str:
    log_path = operation_log_path_for_context(path, root=root, home=home, remap_path=remap_path)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    if rotate:
        rotate_log_once(log_path, max_bytes=rotate_bytes, remove_path=remove_path)
    with log_path.open("a", encoding="utf-8") as handle:
        for entry in entries:
            handle.write(json.dumps(ensure_entry(entry), ensure_ascii=False, sort_keys=True) + "\n")
    return display_path(log_path)


__all__ = [
    "log_path_for_context",
    "operation_log_path_for_context",
    "rotate_log_once",
    "deletion_log_path_for_context",
    "append_deletion_log",
    "batch_append_deletion_log",
    "preflight_operation_log",
    "append_operation_log",
]
