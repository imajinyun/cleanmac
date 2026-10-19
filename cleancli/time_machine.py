"""Read-only Time Machine local snapshot evidence.

Aligns with Mole's ``clean_local_snapshots``: enumerate local Time Machine
snapshots via ``tmutil listlocalsnapshots`` after the same pre-checks (tmutil
present, Time Machine configured, backup engine idle). This surface is
review-only by design — deleting local snapshots breaks Time Machine backup
continuity, and Mole deliberately removed its snapshot deletion path for that
reason; cleanmac never executes ``tmutil thinlocalsnapshots`` or equivalent.
"""

from __future__ import annotations

import os
import re
import shutil
import subprocess
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from typing import Any

TIME_MACHINE_SCHEMA = "cleanmac.time-machine.v1"

# com.apple.TimeMachine.YYYY-MM-DD-HHMMSS, with an optional trailing suffix
# (some macOS releases print ".local" or the volume name after the date).
SNAPSHOT_PATTERN = re.compile(r"com\.apple\.TimeMachine\.\d{4}-\d{2}-\d{2}-\d{6}(?:\.\S+)?")
SNAPSHOT_DATE_PATTERN = re.compile(r"(\d{4})-(\d{2})-(\d{2})-(\d{2})(\d{2})(\d{2})")
RUNNING_PATTERN = re.compile(r"^\s*Running\s*=\s*([01])\s*;", re.MULTILINE)

AUTOBACKUP_DOMAIN = "/Library/Preferences/com.apple.TimeMachine"
DEFAULT_MOUNT = "/"
HOST_COMMAND_TIMEOUT_SECONDS = 5.0


@dataclass(frozen=True)
class HostCommandResult:
    returncode: int
    stdout: str
    stderr: str = ""


CommandRunner = Callable[[Sequence[str], float], HostCommandResult | None]


def _host_command(argv: Sequence[str], timeout: float) -> HostCommandResult | None:
    """Default runner; never invokes host tools in test/no-auth mode."""
    if os.environ.get("CLEANMAC_TEST_MODE") == "1" or os.environ.get("CLEANMAC_TEST_NO_AUTH") == "1":
        return None
    try:
        completed = subprocess.run(
            list(argv),
            text=True,
            capture_output=True,
            check=False,
            timeout=timeout,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    return HostCommandResult(
        returncode=completed.returncode,
        stdout=completed.stdout,
        stderr=completed.stderr,
    )


def parse_auto_backup(text: str | None) -> bool | None:
    """Parse ``defaults read ... AutoBackup`` output into 1/0/absent."""
    if text is None:
        return None
    stripped = text.strip()
    if stripped == "1":
        return True
    if stripped == "0":
        return False
    return None


def parse_backup_state(status_text: str | None) -> str:
    """Parse ``tmutil status`` into running/idle/unknown."""
    if not status_text:
        return "unknown"
    match = RUNNING_PATTERN.search(status_text)
    if not match:
        return "unknown"
    return "running" if match.group(1) == "1" else "idle"


def parse_local_snapshots(text: str | None) -> list[dict[str, str | None]]:
    """Extract snapshot names from ``tmutil listlocalsnapshots`` output.

    Every printed occurrence is preserved (Mole counts the same grep matches),
    so snapshots listed under multiple volume sections are not deduplicated.
    """
    snapshots: list[dict[str, str | None]] = []
    if not text:
        return snapshots
    for name in SNAPSHOT_PATTERN.findall(text):
        date_token = ""
        iso_timestamp = None
        date_match = SNAPSHOT_DATE_PATTERN.search(name)
        if date_match:
            year, month, day, hour, minute, second = date_match.groups()
            date_token = f"{year}-{month}-{day}-{hour}{minute}{second}"
            iso_timestamp = f"{year}-{month}-{day}T{hour}:{minute}:{second}"
        snapshots.append(
            {
                "name": name,
                "date_token": date_token,
                "timestamp": iso_timestamp,
            }
        )
    return snapshots


def render_time_machine(
    *,
    mount: str = DEFAULT_MOUNT,
    host_tools_enabled: bool = True,
    runner: CommandRunner | None = None,
    timeout: float = HOST_COMMAND_TIMEOUT_SECONDS,
) -> dict[str, Any]:
    """Collect review-only local snapshot evidence for one mount point."""
    run = runner or _host_command
    tmutil_path = shutil.which("tmutil")
    invoked: list[str] = []

    def run_host(argv: Sequence[str]) -> HostCommandResult | None:
        invoked.append(argv[0])
        return run(argv, timeout)

    report: dict[str, Any] = {
        "schema": TIME_MACHINE_SCHEMA,
        "destructive": False,
        "dry_run": True,
        "read_only": True,
        "deletion_supported": False,
        "mount": mount,
        "host_tools": {
            "enabled": bool(host_tools_enabled),
            "tmutil_available": tmutil_path is not None,
            "tmutil_path": tmutil_path,
            "invoked_commands": invoked,
        },
        "configured": None,
        "auto_backup": None,
        "backup_state": "unknown",
        "enumeration_status": "unavailable",
        "snapshot_count": 0,
        "snapshots": [],
        "manual_review_command": ["tmutil", "listlocalsnapshots", mount],
        "deletion_policy": {
            "snapshot_deletion_supported": False,
            "reason": (
                "Local snapshots are Time Machine recovery points; deleting them breaks "
                "backup continuity. Enumeration is review-only and stays manual."
            ),
        },
        "recommended_next_action": "review-manually",
    }

    if not host_tools_enabled:
        report["enumeration_status"] = "skipped-host-tools-disabled"
        return report
    if runner is None and (
        os.environ.get("CLEANMAC_TEST_MODE") == "1" or os.environ.get("CLEANMAC_TEST_NO_AUTH") == "1"
    ):
        # The default host runner is blocked in test/no-auth mode; report the
        # conservative outcome without recording any command invocation.
        report["enumeration_status"] = "skipped-not-configured"
        return report
    if tmutil_path is None:
        report["enumeration_status"] = "skipped-tmutil-unavailable"
        return report

    defaults_result = run_host(["defaults", "read", AUTOBACKUP_DOMAIN, "AutoBackup"])
    auto_backup = parse_auto_backup(defaults_result.stdout if defaults_result else None)
    report["auto_backup"] = auto_backup
    report["configured"] = auto_backup is not None
    if auto_backup is None:
        # Mole skips the whole tmutil sequence when Time Machine is unconfigured.
        report["enumeration_status"] = "skipped-not-configured"
        return report

    status_result = run_host(["tmutil", "status"])
    backup_state = parse_backup_state(status_result.stdout if status_result else None)
    report["backup_state"] = backup_state
    if backup_state == "running":
        report["enumeration_status"] = "skipped-backup-in-progress"
        return report
    if backup_state == "unknown":
        # Unknown status is fail-closed: never enumerate while a backup may be active.
        report["enumeration_status"] = "skipped-status-unknown"
        return report

    listing_result = run_host(["tmutil", "listlocalsnapshots", mount])
    if listing_result is None or listing_result.returncode != 0:
        report["enumeration_status"] = "enumeration-failed"
        return report

    snapshots = parse_local_snapshots(listing_result.stdout)
    report["snapshots"] = snapshots
    report["snapshot_count"] = len(snapshots)
    report["enumeration_status"] = "enumerated"
    return report
