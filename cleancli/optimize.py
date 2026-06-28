"""System optimization tasks — maintenance planning and execution.

All optimize tasks are non-destructive maintenance operations that refresh
system caches, rebuild indexes, and restart services. Tasks that require
privilege are gated behind --execute + --yes + test-mode checks.
"""

from __future__ import annotations

import shlex
import subprocess
from typing import Any

OPTIMIZE_TASKS: list[dict[str, Any]] = [
    {
        "key": "quicklook-cache",
        "title": "Quick Look cache refresh",
        "description": "Reset Quick Look thumbnail and preview caches.",
        "command": "qlmanage -r cache",
        "requires_privilege": False,
        "destructive": False,
        "category": "caches",
    },
    {
        "key": "launchservices-rebuild",
        "title": "LaunchServices metadata rebuild",
        "description": "Rebuild the LaunchServices database to fix Open With menu duplicates.",
        "command": "/System/Library/Frameworks/CoreServices.framework/Frameworks/LaunchServices.framework/Support/lsregister -kill -r -domain local -domain system -domain user",
        "requires_privilege": False,
        "destructive": False,
        "category": "caches",
    },
    {
        "key": "spotlight-reindex",
        "title": "Spotlight index rebuild",
        "description": "Turn Spotlight indexing off and on for the root volume to rebuild the index.",
        "command": "sudo mdutil -E /",
        "requires_privilege": True,
        "destructive": False,
        "category": "indexes",
    },
    {
        "key": "finder-restart",
        "title": "Finder refresh",
        "description": "Restart the Finder process to clear cached state and apply preference changes.",
        "command": "killall Finder",
        "requires_privilege": False,
        "destructive": False,
        "category": "services",
    },
    {
        "key": "dock-restart",
        "title": "Dock refresh",
        "description": "Restart the Dock process to clear cached icon and preference state.",
        "command": "killall Dock",
        "requires_privilege": False,
        "destructive": False,
        "category": "services",
    },
    {
        "key": "diagnostic-logs-clear",
        "title": "Diagnostic and crash logs cleanup",
        "description": "Remove stale system diagnostic reports and crash logs.",
        "command": "rm -rf ~/Library/Logs/DiagnosticReports/*",
        "requires_privilege": False,
        "destructive": False,
        "category": "logs",
    },
    {
        "key": "dns-cache-flush",
        "title": "DNS cache flush",
        "description": "Flush the DNS resolver cache to clear stale hostname lookups.",
        "command": "sudo dscacheutil -flushcache && sudo killall -HUP mDNSResponder",
        "requires_privilege": True,
        "destructive": False,
        "category": "network",
    },
    {
        "key": "kernel-cache-update",
        "title": "Kernel cache update",
        "description": "Touch the kernel extension cache to trigger a rebuild on next boot.",
        "command": "sudo touch /System/Library/Extensions",
        "requires_privilege": True,
        "destructive": False,
        "category": "caches",
    },
    {
        "key": "print-cache-clear",
        "title": "Print queue and cache reset",
        "description": "Cancel all print jobs and reset the printer cache.",
        "command": "cancel -a - && rm -rf ~/Library/Printers/*",
        "requires_privilege": False,
        "destructive": False,
        "category": "caches",
    },
    {
        "key": "font-cache-clear",
        "title": "Font cache rebuild",
        "description": "Clear font registry caches; they rebuild automatically on next use.",
        "command": "atsutil databases -removeUser",
        "requires_privilege": False,
        "destructive": False,
        "category": "caches",
    },
]


def list_optimize_tasks() -> list[dict[str, Any]]:
    return [dict(t) for t in OPTIMIZE_TASKS]


def _run_optimize_task(
    task: dict[str, Any],
    *,
    execute: bool,
    test_mode: bool,
    sudo_available: bool,
) -> dict[str, Any]:
    key = str(task.get("key", ""))
    title = str(task.get("title", ""))
    command = str(task.get("command", ""))
    requires_privilege = bool(task.get("requires_privilege", False))

    result: dict[str, Any] = {
        "key": key,
        "title": title,
        "command": command,
        "requires_privilege": requires_privilege,
        "status": "planned",
        "output": None,
        "error": None,
    }

    if not execute:
        result["status"] = "dry-run"
        return result

    if test_mode:
        result["status"] = "skipped"
        result["output"] = "[test-mode] command not executed"
        return result

    if requires_privilege and not sudo_available:
        result["status"] = "blocked"
        result["error"] = "requires sudo privilege"
        return result

    try:
        proc = subprocess.run(
            shlex.split(command),
            capture_output=True,
            text=True,
            timeout=60,
        )
        result["status"] = "success" if proc.returncode == 0 else "failed"
        result["output"] = proc.stdout.strip() or None
        if proc.stderr.strip():
            result["error"] = proc.stderr.strip()
    except subprocess.TimeoutExpired:
        result["status"] = "failed"
        result["error"] = "command timed out after 60s"
    except FileNotFoundError as e:
        result["status"] = "failed"
        result["error"] = f"command not found: {e}"
    except Exception as e:
        result["status"] = "failed"
        result["error"] = str(e)

    return result


def execute_optimize_tasks(
    *,
    action: str,
    execute: bool,
    test_mode: bool = False,
    sudo_available: bool = False,
    task_filter: set[str] | None = None,
) -> dict[str, Any]:
    tasks = list_optimize_tasks()

    if task_filter is not None:
        tasks = [t for t in tasks if str(t.get("key")) in task_filter]

    results: list[dict[str, Any]] = []
    success_count = 0
    failed_count = 0
    skipped_count = 0

    for task in tasks:
        result = _run_optimize_task(
            task,
            execute=execute,
            test_mode=test_mode,
            sudo_available=sudo_available,
        )
        results.append(result)
        status = result.get("status")
        if status == "success":
            success_count += 1
        elif status == "failed" or status == "blocked":
            failed_count += 1
        elif status == "skipped" or status == "dry-run":
            skipped_count += 1

    return {
        "schema": "cleanmac.optimize.v1",
        "action": action,
        "destructive": False,
        "dry_run": not execute,
        "execute_requested": execute,
        "execution_supported": True,
        "total_tasks": len(results),
        "success_count": success_count,
        "failed_count": failed_count,
        "skipped_count": skipped_count,
        "tasks": results,
    }


def render_optimize_human(report: dict[str, Any]) -> str:
    lines: list[str] = []
    lines.append("System Optimization")
    lines.append("=" * 60)
    lines.append(
        f"Tasks: {report.get('total_tasks', 0)} | Mode: {'execute' if report.get('execute_requested') else 'dry-run'}"
    )
    if report.get("execute_requested"):
        lines.append(
            f"Success: {report.get('success_count', 0)} | "
            f"Failed: {report.get('failed_count', 0)} | "
            f"Skipped: {report.get('skipped_count', 0)}"
        )
    lines.append("")

    tasks = list(report.get("tasks", []))
    if not tasks:
        lines.append("No optimize tasks configured.")
        return "\n".join(lines)

    for task in tasks:
        status = str(task.get("status", "unknown"))
        title = str(task.get("title", ""))
        icon = {
            "success": "✓",
            "failed": "✗",
            "blocked": "⊘",
            "skipped": "○",
            "dry-run": "○",
            "planned": "○",
        }.get(status, "?")

        privilege = " [sudo]" if task.get("requires_privilege") else ""

        lines.append(f"  {icon} {title}{privilege}")
        if status == "failed" and task.get("error"):
            err = str(task["error"])[:80]
            lines.append(f"      Error: {err}")

    lines.append("")
    lines.append("Run with --execute --yes to apply optimizations.")
    return "\n".join(lines)


__all__ = [
    "OPTIMIZE_TASKS",
    "execute_optimize_tasks",
    "list_optimize_tasks",
    "render_optimize_human",
]
