"""macOS unified log inspection and governed permanent erasure.

The unified log keeps live tracev3 data under ``/private/var/db/diagnostics``
and ``/private/var/db/uuidtext``. The files are managed by logd and protected
by SIP; deleting them directly reclaims nothing and is unsafe. The only
supported reclamation path is ``sudo log erase --all``, which permanently
clears both stores together and cannot route through Trash.

This module orchestrates only. The privileged primitive lives in
``delete_ops.py`` so the single-deletion-exit ownership stays intact.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from cleancli import delete_ops

INSPECT_SCHEMA = "cleanmac.unified-logs-inspect.v1"
ERASE_PLAN_SCHEMA = "cleanmac.unified-logs-erase-plan.v1"
ERASE_RESULT_SCHEMA = "cleanmac.unified-logs-erase-result.v1"

DIAGNOSTICS_REL = "/private/var/db/diagnostics"
UUIDTEXT_REL = "/private/var/db/uuidtext"

STORE_SPECS: tuple[tuple[str, str, str], ...] = (
    ("diagnostics", DIAGNOSTICS_REL, "Unified log tracev3 data and timesync tracking."),
    ("uuidtext", UUIDTEXT_REL, "Short decimal/UUID reference text used with the tracev3 store."),
)

# Bounds the rglob walk so a huge or pathological store cannot stall the CLI.
DEFAULT_MAX_ENTRIES = 20_000

ERASE_COMMAND: tuple[str, ...] = delete_ops.SUDO_LOG_ERASE_COMMAND
REQUIRED_EXECUTE_FLAGS: tuple[str, ...] = ("--execute", "--yes", "--confirm-permanent-erase")

PERMANENT_ERASE_DISCLOSURE = (
    "`sudo log erase --all` permanently clears the entire macOS unified log "
    "(diagnostics and uuidtext). It is irreversible, is not routed through "
    "Trash, and cannot be undone."
)
REQUIRES_LIVE_ROOT_DISCLOSURE = (
    "Unified log erasure is only supported on the live root (/). Sandbox "
    "roots are rejected because `log erase` always targets the running OS."
)


@dataclass(frozen=True)
class StoreSize:
    name: str
    path: Path
    exists: bool
    bytes: int
    entries_scanned: int
    truncated: bool
    note: str


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


def _display_path(path: Path, *, home: Path | None) -> str:
    text = str(path)
    if home is not None and text.startswith(str(home)):
        return "~" + text[len(str(home)) :]
    return text


def store_path(absolute_path: str, *, root: Path) -> Path:
    """Map an absolute system store path under root, mirroring core.provider_base."""
    if root == Path("/"):
        return Path(absolute_path)
    return root / absolute_path.lstrip("/")


def bounded_store_size(name: str, absolute_path: str, note: str, *, root: Path, max_entries: int) -> StoreSize:
    path = store_path(absolute_path, root=root)
    if not path.exists() and not path.is_symlink():
        return StoreSize(name=name, path=path, exists=False, bytes=0, entries_scanned=0, truncated=False, note=note)
    total = 0
    scanned = 0
    truncated = False
    try:
        if path.is_file() or path.is_symlink():
            return StoreSize(
                name=name,
                path=path,
                exists=True,
                bytes=path.lstat().st_size,
                entries_scanned=1,
                truncated=False,
                note=note,
            )
        for index, child in enumerate(path.rglob("*")):
            if index >= max_entries:
                truncated = True
                break
            try:
                if child.exists() or child.is_symlink():
                    total += child.lstat().st_size
                    scanned += 1
            except OSError:
                continue
    except OSError:
        # Unreadable stores (permissions) report what was gathered so far and
        # stay visibly incomplete rather than failing the read-only inspect.
        truncated = True
    return StoreSize(
        name=name,
        path=path,
        exists=True,
        bytes=total,
        entries_scanned=scanned,
        truncated=truncated,
        note=note,
    )


def _store_row(size: StoreSize, *, home: Path | None = None) -> dict[str, Any]:
    return {
        "name": size.name,
        "path": _display_path(size.path, home=home),
        "exists": size.exists,
        "bytes": size.bytes,
        "human": _human_size(size.bytes),
        "entries_scanned": size.entries_scanned,
        "size_truncated": size.truncated,
        "note": size.note,
    }


def measure_stores(*, root: Path, max_entries: int = DEFAULT_MAX_ENTRIES) -> list[StoreSize]:
    return [
        bounded_store_size(name, absolute_path, note, root=root, max_entries=max_entries)
        for name, absolute_path, note in STORE_SPECS
    ]


def inspect_unified_logs(
    *, root: Path, home: Path | None = None, max_entries: int = DEFAULT_MAX_ENTRIES
) -> dict[str, Any]:
    """Read-only size accounting for the two unified-log stores."""
    sizes = measure_stores(root=root, max_entries=max_entries)
    rows = [_store_row(size, home=home) for size in sizes]
    total = sum(size.bytes for size in sizes)
    live_root = root == Path("/")
    return {
        "schema": INSPECT_SCHEMA,
        "phase": "inspect",
        "destructive": False,
        "dry_run": True,
        "root": _display_path(root, home=home),
        "home": _display_path(home, home=home) if home is not None else None,
        "status": "read-only-inspect",
        "live_root": live_root,
        "stores": rows,
        "total_bytes": total,
        "total_human": _human_size(total),
        "erased_together": True,
        "erase_command": list(ERASE_COMMAND),
        "erase_method": "permanent",
        "trash_routing": False,
        "notes": [
            "diagnostics and uuidtext are cleared together by `sudo log erase --all`.",
            "Direct file deletion of the live tracev3 store is unsupported and reclaims no space.",
        ],
        "warnings": [] if live_root else [REQUIRES_LIVE_ROOT_DISCLOSURE],
    }


def _erase_gate_disclosures(*, live_root: bool, confirmed: bool, permanent_confirmed: bool) -> list[str]:
    return [
        PERMANENT_ERASE_DISCLOSURE,
        REQUIRES_LIVE_ROOT_DISCLOSURE if not live_root else "Erasure targets the running OS on the live root (/).",
        f"Required flags for real execution: {' '.join(REQUIRED_EXECUTE_FLAGS)}.",
        (
            "All three confirmations (--execute, --yes, --confirm-permanent-erase) are required."
            if not (confirmed and permanent_confirmed)
            else "All explicit permanent-erase confirmations were supplied."
        ),
    ]


def plan_erase(
    *, root: Path, home: Path | None = None, max_entries: int = DEFAULT_MAX_ENTRIES
) -> dict[str, Any]:
    """Dry-run plan: sizes plus the permanent-erase gates and disclosures."""
    inspection = inspect_unified_logs(root=root, home=home, max_entries=max_entries)
    live_root = bool(inspection["live_root"])
    return {
        "schema": ERASE_PLAN_SCHEMA,
        "phase": "erase-dry-run",
        "destructive": True,
        "dry_run": True,
        "root": inspection["root"],
        "home": inspection["home"],
        "status": "dry-run",
        "live_root": live_root,
        "stores": inspection["stores"],
        "total_bytes": inspection["total_bytes"],
        "total_human": inspection["total_human"],
        "estimated_reclaimable_bytes": inspection["total_bytes"] if live_root else 0,
        "estimated_reclaimable_human": _human_size(inspection["total_bytes"]) if live_root else "0 B",
        "erase_command": list(ERASE_COMMAND),
        "erase_method": "permanent",
        "trash_routing": False,
        "required_flags": list(REQUIRED_EXECUTE_FLAGS),
        "safe_to_execute_after_confirmation": False,
        "disclosures": _erase_gate_disclosures(live_root=live_root, confirmed=False, permanent_confirmed=False),
        "warnings": list(inspection["warnings"]),
    }


def _result_refused(
    *, root: Path, home: Path | None, error_code: str, error: str, sizes: list[StoreSize]
) -> dict[str, Any]:
    total = sum(size.bytes for size in sizes)
    return {
        "schema": ERASE_RESULT_SCHEMA,
        "phase": "erase",
        "destructive": True,
        "dry_run": False,
        "root": _display_path(root, home=home),
        "home": _display_path(home, home=home) if home is not None else None,
        "status": "refused",
        "executed": False,
        "live_root": root == Path("/"),
        "error_code": error_code,
        "error": error,
        "stores": [_store_row(size, home=home) for size in sizes],
        "total_bytes": total,
        "total_human": _human_size(total),
        "reclaimed_bytes": 0,
        "reclaimed_human": "0 B",
        "erase_command": list(ERASE_COMMAND),
        "erase_method": "permanent",
        "trash_routing": False,
        "required_flags": list(REQUIRED_EXECUTE_FLAGS),
        "disclosures": [PERMANENT_ERASE_DISCLOSURE],
    }


def run_erase(
    *,
    root: Path,
    home: Path | None = None,
    execute: bool = False,
    confirmed: bool = False,
    permanent_confirmed: bool = False,
    sudo_available: bool | None = None,
    max_entries: int = DEFAULT_MAX_ENTRIES,
    operation_log: Callable[[str, Path, str], Any] | None = None,
    erase_runner: Callable[..., Any] = delete_ops.erase_unified_logs,
) -> dict[str, Any]:
    """Orchestrate the permanent unified-log erase with fail-closed gates.

    Gate order: dry-run default -> live-root validation -> explicit
    confirmations -> non-interactive sudo preflight -> primitive (which
    re-checks test/no-auth mode) -> structured result. Nothing destructive
    runs unless every gate passes.
    """
    if not execute:
        return plan_erase(root=root, home=home, max_entries=max_entries)

    sizes = measure_stores(root=root, max_entries=max_entries)
    total_before = sum(size.bytes for size in sizes)

    if root != Path("/"):
        return _result_refused(
            root=root,
            home=home,
            error_code="SANDBOX_ROOT_UNSUPPORTED",
            error="Refusing to erase unified logs outside the live root (/); `log erase` targets the running OS.",
            sizes=sizes,
        )
    if not confirmed or not permanent_confirmed:
        missing = []
        if not confirmed:
            missing.append("--yes")
        if not permanent_confirmed:
            missing.append("--confirm-permanent-erase")
        return _result_refused(
            root=root,
            home=home,
            error_code="CONFIRMATION_REQUIRED",
            error=(
                "Refusing to permanently erase unified logs without explicit confirmation; "
                f"missing: {', '.join(missing) or '--execute'}."
            ),
            sizes=sizes,
        )
    if sudo_available is False:
        return _result_refused(
            root=root,
            home=home,
            error_code="SUDO_PREFLIGHT_FAILED",
            error="Refusing to erase unified logs: non-interactive sudo preflight (`sudo -n true`) failed.",
            sizes=sizes,
        )

    try:
        outcome = erase_runner(dry_run=False, operation_log=operation_log)
    except RuntimeError as exc:
        return {
            "schema": ERASE_RESULT_SCHEMA,
            "phase": "erase",
            "destructive": True,
            "dry_run": False,
            "root": _display_path(root, home=home),
            "home": _display_path(home, home=home) if home is not None else None,
            "status": "failed",
            "executed": False,
            "live_root": True,
            "error_code": "ERASE_FAILED",
            "error": str(exc),
            "stores": [_store_row(size, home=home) for size in sizes],
            "total_bytes": total_before,
            "total_human": _human_size(total_before),
            "reclaimed_bytes": 0,
            "reclaimed_human": "0 B",
            "erase_command": list(ERASE_COMMAND),
            "erase_method": "permanent",
            "trash_routing": False,
            "required_flags": list(REQUIRED_EXECUTE_FLAGS),
            "disclosures": [PERMANENT_ERASE_DISCLOSURE],
        }

    after = measure_stores(root=root, max_entries=max_entries)
    total_after = sum(size.bytes for size in after)
    reclaimed = max(0, total_before - total_after)
    return {
        "schema": ERASE_RESULT_SCHEMA,
        "phase": "erase",
        "destructive": True,
        "dry_run": False,
        "root": _display_path(root, home=home),
        "home": _display_path(home, home=home) if home is not None else None,
        "status": "executed",
        "executed": True,
        "live_root": True,
        "error_code": None,
        "error": None,
        "command": list(getattr(outcome, "command", ERASE_COMMAND)),
        "returncode": getattr(outcome, "returncode", 0),
        "stdout": getattr(outcome, "stdout", ""),
        "stderr": getattr(outcome, "stderr", ""),
        "stores_before": [_store_row(size, home=home) for size in sizes],
        "stores_after": [_store_row(size, home=home) for size in after],
        "total_bytes": total_after,
        "total_human": _human_size(total_after),
        "reclaimed_bytes": reclaimed,
        "reclaimed_human": _human_size(reclaimed),
        "erase_command": list(ERASE_COMMAND),
        "erase_method": "permanent",
        "trash_routing": False,
        "required_flags": list(REQUIRED_EXECUTE_FLAGS),
        "disclosures": [PERMANENT_ERASE_DISCLOSURE],
    }


def render_human(report: dict[str, Any]) -> str:
    lines: list[str] = ["Unified Logs", "=" * 60]
    status = str(report.get("status") or ("dry-run" if report.get("dry_run") else "inspect"))
    lines.append(f"Phase: {report.get('phase', 'inspect')} ({status})")
    lines.append(f"Live root: {'yes' if report.get('live_root') else 'no'}")
    lines.append("")
    stores = report.get("stores") or report.get("stores_before") or []
    for store in stores:
        lines.append(
            f"- {store['name']}: {store['human']} ({store['path']})"
            + (" [size estimate truncated]" if store.get("size_truncated") else "")
        )
    if "total_human" in report:
        lines.append(f"Total: {report['total_human']}")
    if report.get("reclaimed_bytes"):
        lines.append(f"Reclaimed: {report['reclaimed_human']}")
    lines.append("")
    for disclosure in report.get("disclosures", []):
        lines.append(f"NOTE: {disclosure}")
    for warning in report.get("warnings", []):
        lines.append(f"WARNING: {warning}")
    if report.get("error"):
        lines.append(f"ERROR ({report.get('error_code')}): {report['error']}")
    return "\n".join(lines)
