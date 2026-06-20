"""Controlled external-tool cleanup adapters.

Adapters in this module describe allowlisted argv vectors for tools such as
Docker and Homebrew.  They never use a shell and keep destructive execution
behind explicit caller gates in ``cleancli.core``.
"""

from __future__ import annotations

import shutil
import subprocess
from collections.abc import Callable, Sequence
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

Runner = Callable[[Sequence[str], float], subprocess.CompletedProcess[str]]


def _run_command(argv: Sequence[str], timeout: float) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        list(argv),
        text=True,
        capture_output=True,
        check=False,
        timeout=timeout,
    )


def tool_adapters() -> dict[str, dict[str, Any]]:
    return {
        "docker": {
            "title": "Docker semantic cleanup plan",
            "risk": "medium",
            "detect_commands": [["docker", "system", "df"], ["docker", "builder", "du"]],
            "dry_run_commands": [["docker", "system", "df"], ["docker", "builder", "du"]],
            "execute_commands": [
                ["docker", "builder", "prune", "--force"],
                ["docker", "image", "prune", "--force"],
                ["docker", "container", "prune", "--force"],
            ],
            "manual_execute_commands": [
                ["docker", "builder", "prune"],
                ["docker", "image", "prune"],
                ["docker", "container", "prune"],
            ],
            "excluded_destructive_commands": [["docker", "volume", "prune"]],
            "preserve": ["volumes", "contexts", "auth", "daemon configuration"],
        },
        "homebrew": {
            "title": "Homebrew semantic cleanup plan",
            "risk": "medium",
            "detect_commands": [["brew", "cleanup", "--dry-run"], ["brew", "--cache"]],
            "dry_run_commands": [["brew", "cleanup", "--dry-run"]],
            "execute_commands": [["brew", "cleanup"]],
            "manual_execute_commands": [["brew", "cleanup"]],
            "excluded_destructive_commands": [],
            "preserve": ["installed formulae", "installed casks", "taps", "brew configuration"],
        },
        "xcode": {
            "title": "Xcode semantic cleanup plan",
            "risk": "medium",
            "detect_commands": [["xcrun", "simctl", "list", "devices", "unavailable"]],
            "dry_run_commands": [["xcrun", "simctl", "list", "devices", "unavailable"]],
            "execute_commands": [["xcrun", "simctl", "delete", "unavailable"]],
            "manual_execute_commands": [["xcrun", "simctl", "delete", "unavailable"]],
            "excluded_destructive_commands": [],
            "preserve": ["active simulators", "current device support", "project archives unless explicitly selected"],
        },
        "package-managers": {
            "title": "Package manager cache semantic cleanup plan",
            "risk": "medium",
            "detect_commands": [["npm", "cache", "verify"], ["yarn", "cache", "dir"], ["pip", "cache", "info"]],
            "dry_run_commands": [["npm", "cache", "verify"], ["pip", "cache", "info"]],
            "execute_commands": [["npm", "cache", "clean", "--force"], ["pip", "cache", "purge"]],
            "manual_execute_commands": [["npm", "cache", "clean", "--force"], ["pip", "cache", "purge"]],
            "excluded_destructive_commands": [],
            "preserve": ["registry auth", "publishing tokens", "lock files", "project dependencies"],
        },
    }


def selected_adapters(tool: str) -> dict[str, dict[str, Any]]:
    adapters = tool_adapters()
    return adapters if tool == "all" else {tool: adapters[tool]}


def render_tool_plan(tool: str, *, root: Path, home: Path) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    for key, adapter in selected_adapters(tool).items():
        commands = adapter["detect_commands"]
        binaries = sorted({command[0] for command in commands})
        rows.append(
            {
                "key": key,
                "title": adapter["title"],
                "risk": adapter["risk"],
                "available": all(shutil.which(binary) is not None for binary in binaries),
                "required_binaries": binaries,
                "missing_binaries": [binary for binary in binaries if shutil.which(binary) is None],
                "dry_run_commands": adapter["dry_run_commands"],
                "manual_execute_commands": adapter["manual_execute_commands"],
                "excluded_destructive_commands": adapter["excluded_destructive_commands"],
                "preserve": adapter["preserve"],
                "auto_execute_allowed": False,
                "notes": [
                    "This adapter is read-only unless tool-execute is invoked with explicit execution gates.",
                    "Use cleanmac path-based categories for recoverable Trash-mode cleanup; use tool commands only after manual review.",
                ],
            }
        )
    return {
        "schema": "cleanmac.tool-plan.v1",
        "destructive": False,
        "dry_run": True,
        "root": str(root),
        "home": str(home),
        "selected_tool": tool,
        "adapter_count": len(rows),
        "safe_to_auto_execute": False,
        "adapters": rows,
    }


def _command_allowed(argv: Sequence[str], allowlist: Sequence[Sequence[str]]) -> bool:
    return list(argv) in [list(command) for command in allowlist]


def _summarize_text(text: str, *, limit: int = 2000) -> str:
    text = text.strip()
    return text if len(text) <= limit else text[:limit] + "…"


def _command_result(
    *,
    tool: str,
    argv: Sequence[str],
    status: str,
    returncode: int | None = None,
    stdout: str = "",
    stderr: str = "",
    error: str | None = None,
) -> dict[str, Any]:
    return {
        "tool": tool,
        "argv": list(argv),
        "status": status,
        "returncode": returncode,
        "stdout": _summarize_text(stdout),
        "stderr": _summarize_text(stderr),
        "error": error,
    }


def execute_tool(
    tool: str,
    *,
    execute: bool,
    yes: bool,
    root: Path,
    home: Path,
    timeout: float = 30,
    runner: Runner | None = None,
) -> dict[str, Any]:
    adapters = selected_adapters(tool)
    runner = runner or _run_command
    results: list[dict[str, Any]] = []
    operation_log_entries: list[dict[str, Any]] = []
    blocked_reasons: list[str] = []
    if execute and not yes:
        blocked_reasons.append("explicit-yes-required")
    for key, adapter in adapters.items():
        commands = adapter["execute_commands"] if execute else adapter["dry_run_commands"]
        allowlist = adapter["execute_commands"] if execute else adapter["dry_run_commands"]
        for argv in commands:
            if not _command_allowed(argv, allowlist):
                result = _command_result(tool=key, argv=argv, status="blocked", error="argv-not-allowlisted")
            elif execute and not yes:
                result = _command_result(tool=key, argv=argv, status="blocked", error="explicit --yes required")
            elif shutil.which(argv[0]) is None:
                result = _command_result(
                    tool=key, argv=argv, status="missing-binary", error=f"Missing binary: {argv[0]}"
                )
            else:
                try:
                    completed = runner(argv, timeout)
                except Exception as exc:  # pragma: no cover - exercised via integration behavior
                    result = _command_result(tool=key, argv=argv, status="failed", error=str(exc))
                else:
                    result = _command_result(
                        tool=key,
                        argv=argv,
                        status="succeeded" if completed.returncode == 0 else "failed",
                        returncode=completed.returncode,
                        stdout=completed.stdout,
                        stderr=completed.stderr,
                    )
            results.append(result)
            operation_log_entries.append(
                {
                    "schema": "cleanmac.operation-log-entry.v1",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "action": "tool-execute" if execute else "tool-dry-run",
                    "tool": key,
                    "command": " ".join(argv),
                    "argv": list(argv),
                    "status": result["status"],
                    "returncode": result.get("returncode"),
                    "error": result.get("error"),
                    "root": str(root),
                    "home": str(home),
                }
            )
    return {
        "schema": "cleanmac.tool-execution-result.v1",
        "destructive": bool(execute),
        "dry_run": not execute,
        "root": str(root),
        "home": str(home),
        "selected_tool": tool,
        "safe_to_auto_execute": False,
        "blocked_reasons": blocked_reasons,
        "results": results,
        "operation_log_entries": operation_log_entries,
        "succeeded_count": sum(1 for result in results if result["status"] == "succeeded"),
        "failed_count": sum(1 for result in results if result["status"] in {"failed", "missing-binary", "blocked"}),
    }
