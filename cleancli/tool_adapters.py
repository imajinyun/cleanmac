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

PACKAGE_MANAGER_ADAPTER_KEYS = ("npm", "pnpm", "yarn", "pip", "uv", "poetry", "cargo")
TOOL_ADAPTER_CHOICES = ("all", "docker", "homebrew", "xcode", "package-managers", *PACKAGE_MANAGER_ADAPTER_KEYS)


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
            "risk_explanation": (
                "Docker cache cleanup can reclaim build layers, stopped containers, and dangling images, but named "
                "volumes may contain databases or user data and are deliberately excluded."
            ),
            "cleanup_scope": [
                "disk-usage inspection via docker system df",
                "BuildKit cache sizing via docker builder du",
                "manual pruning recommendations for builders, dangling images, and stopped containers",
            ],
            "path_categories": ["docker"],
            "detect_commands": [["docker", "system", "df"], ["docker", "system", "df", "--verbose"], ["docker", "builder", "du"]],
            "dry_run_commands": [["docker", "system", "df"], ["docker", "system", "df", "--verbose"], ["docker", "builder", "du"]],
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
            "excluded_destructive_commands": [["docker", "volume", "prune"], ["docker", "system", "prune", "--volumes"]],
            "preserve": ["volumes", "contexts", "auth", "daemon configuration"],
            "notes": [
                "Volume pruning is intentionally excluded because volumes often contain persistent database or application state.",
                "Use docker system df --verbose output to identify the largest reclaimable image/build-cache groups before running manual prune commands.",
            ],
        },
        "homebrew": {
            "title": "Homebrew semantic cleanup plan",
            "risk": "medium",
            "risk_explanation": (
                "Homebrew cleanup removes old downloads and outdated keg/cask artifacts. It should preserve installed "
                "formulae and taps, but failed builds or pinned legacy versions should be reviewed before cleanup."
            ),
            "cleanup_scope": [
                "cleanup dry-run listing of removable downloads and stale artifacts",
                "cache directory discovery via brew --cache",
                "manual cleanup recommendation only; no prune command is auto-executed by plan output",
            ],
            "path_categories": ["homebrewCaches"],
            "detect_commands": [["brew", "cleanup", "--dry-run"], ["brew", "--cache"]],
            "dry_run_commands": [["brew", "cleanup", "--dry-run"], ["brew", "--cache"]],
            "execute_commands": [["brew", "cleanup"]],
            "manual_execute_commands": [["brew", "cleanup"]],
            "excluded_destructive_commands": [],
            "preserve": ["installed formulae", "installed casks", "taps", "brew configuration"],
            "notes": [
                "Review brew cleanup --dry-run output first; cleanmac will not run brew cleanup from a semantic plan.",
                "Use the homebrewCaches category for recoverable Trash-mode cache-path review when direct path cleanup is preferred.",
            ],
        },
        "xcode": {
            "title": "Xcode semantic cleanup plan",
            "risk": "medium",
            "risk_explanation": (
                "Xcode DerivedData and module caches are regenerable, simulator cache cleanup is usually safe, but Archives "
                "may be release evidence and device support may be needed for debugging older devices."
            ),
            "cleanup_scope": [
                "DerivedData: regenerable build products and indexes; projects may rebuild more slowly afterward",
                "Archives: exported/release build history; review individually and do not bulk-delete without explicit selection",
                "CoreSimulator caches: regenerable simulator cache data; unavailable devices can be listed before deletion",
                "DeviceSupport: symbols for connected devices; keep current devices and recent OS versions",
            ],
            "path_categories": ["xcode", "deviceFirmware"],
            "detect_commands": [["xcrun", "simctl", "list", "devices", "unavailable"]],
            "dry_run_commands": [["xcrun", "simctl", "list", "devices", "unavailable"]],
            "execute_commands": [["xcrun", "simctl", "delete", "unavailable"]],
            "manual_execute_commands": [["xcrun", "simctl", "delete", "unavailable"]],
            "excluded_destructive_commands": [],
            "preserve": ["active simulators", "current device support", "project archives unless explicitly selected"],
            "notes": [
                "Xcode Archives are listed as cleanup candidates for review, but should be treated as release artifacts until explicitly selected.",
                "Simulator unavailable-device deletion is separate from path-based cache cleanup and should be run only after reviewing the dry-run list.",
            ],
        },
        "npm": {
            "title": "npm cache semantic cleanup plan",
            "risk": "medium",
            "risk_explanation": "npm cache cleanup is usually recoverable by re-downloading packages, but can slow future installs and must preserve ~/.npmrc auth tokens.",
            "cleanup_scope": ["cache integrity verification", "cache directory discovery", "manual npm cache clean recommendation"],
            "path_categories": ["nodePackageCaches"],
            "detect_commands": [["npm", "cache", "verify"], ["npm", "config", "get", "cache"]],
            "dry_run_commands": [["npm", "cache", "verify"], ["npm", "config", "get", "cache"]],
            "execute_commands": [["npm", "cache", "clean", "--force"]],
            "manual_execute_commands": [["npm", "cache", "clean", "--force"]],
            "excluded_destructive_commands": [],
            "preserve": ["~/.npmrc registry auth", "publishing tokens", "lock files", "project node_modules"],
        },
        "pnpm": {
            "title": "pnpm store semantic cleanup plan",
            "risk": "medium",
            "risk_explanation": "pnpm store pruning removes unreferenced store packages and may require re-fetching packages for dormant projects.",
            "cleanup_scope": ["store integrity/status check", "global store path discovery", "manual pnpm store prune recommendation"],
            "path_categories": ["nodePackageCaches"],
            "detect_commands": [["pnpm", "store", "status"], ["pnpm", "store", "path"]],
            "dry_run_commands": [["pnpm", "store", "status"], ["pnpm", "store", "path"]],
            "execute_commands": [["pnpm", "store", "prune"]],
            "manual_execute_commands": [["pnpm", "store", "prune"]],
            "excluded_destructive_commands": [],
            "preserve": ["pnpm workspace files", "lock files", "registry auth", "project node_modules"],
        },
        "yarn": {
            "title": "Yarn cache semantic cleanup plan",
            "risk": "medium",
            "risk_explanation": "Yarn cache cleanup is re-downloadable but can remove offline mirrors or cached packages needed by older workspaces if not reviewed.",
            "cleanup_scope": ["cache directory discovery", "manual yarn cache clean recommendation"],
            "path_categories": ["nodePackageCaches"],
            "detect_commands": [["yarn", "cache", "dir"]],
            "dry_run_commands": [["yarn", "cache", "dir"]],
            "execute_commands": [["yarn", "cache", "clean"]],
            "manual_execute_commands": [["yarn", "cache", "clean"]],
            "excluded_destructive_commands": [["rm", "-rf", "~/.yarn"]],
            "preserve": ["~/.yarnrc.yml registry auth", "project .yarn/cache offline mirrors", "lock files", "project node_modules"],
            "notes": [
                "Yarn has multiple cache layouts across classic and Berry releases; review the reported cache directory before manual cleanup.",
            ],
        },
        "pip": {
            "title": "pip cache semantic cleanup plan",
            "risk": "medium",
            "risk_explanation": "pip cache purging removes downloaded wheels/sdists and is recoverable by re-downloading, but private index credentials must be preserved.",
            "cleanup_scope": ["cache size/type summary", "cache directory discovery", "manual pip cache purge recommendation"],
            "path_categories": ["pythonPackageCaches"],
            "detect_commands": [["pip", "cache", "info"], ["pip", "cache", "dir"]],
            "dry_run_commands": [["pip", "cache", "info"], ["pip", "cache", "dir"]],
            "execute_commands": [["pip", "cache", "purge"]],
            "manual_execute_commands": [["pip", "cache", "purge"]],
            "excluded_destructive_commands": [],
            "preserve": ["pip configuration", "index credentials", "virtual environments", "project dependencies"],
        },
        "uv": {
            "title": "uv cache semantic cleanup plan",
            "risk": "medium",
            "risk_explanation": "uv cache pruning removes unused cached packages while preserving environments; full cache clean is excluded because it is broader than a prune.",
            "cleanup_scope": ["cache directory discovery", "manual uv cache prune recommendation", "full uv cache clean excluded from semantic cleanup"],
            "path_categories": ["pythonPackageCaches"],
            "detect_commands": [["uv", "cache", "dir"]],
            "dry_run_commands": [["uv", "cache", "dir"]],
            "execute_commands": [["uv", "cache", "prune"]],
            "manual_execute_commands": [["uv", "cache", "prune"]],
            "excluded_destructive_commands": [["uv", "cache", "clean"]],
            "preserve": ["uv configuration", "Python installations", "virtual environments", "project lock files"],
        },
        "poetry": {
            "title": "Poetry cache semantic cleanup plan",
            "risk": "medium",
            "risk_explanation": "Poetry cache cleanup removes repository caches that are recoverable by re-downloading, but private repository credentials and virtualenvs must be preserved.",
            "cleanup_scope": ["cache repository listing", "manual Poetry cache clear recommendation"],
            "path_categories": ["pythonPackageCaches"],
            "detect_commands": [["poetry", "cache", "list"]],
            "dry_run_commands": [["poetry", "cache", "list"]],
            "execute_commands": [["poetry", "cache", "clear", "PyPI", "--all"]],
            "manual_execute_commands": [["poetry", "cache", "clear", "PyPI", "--all"]],
            "excluded_destructive_commands": [["rm", "-rf", "~/Library/Caches/pypoetry"], ["rm", "-rf", "~/.cache/pypoetry"]],
            "preserve": ["Poetry config", "private repository credentials", "virtualenvs", "poetry.lock"],
            "notes": ["Run poetry cache list first because Poetry cache names can differ for private repositories."],
        },
        "cargo": {
            "title": "Cargo cache discovery plan",
            "risk": "low",
            "risk_explanation": "Cargo does not provide a stable built-in cache dry-run; cleanmac limits Cargo tool execution to discovery and recommends path-based review.",
            "cleanup_scope": ["Cargo binary/version discovery", "path-based Cargo registry/git cache review through cargoCaches"],
            "path_categories": ["cargoCaches"],
            "detect_commands": [["cargo", "--version"]],
            "dry_run_commands": [["cargo", "--version"]],
            "execute_commands": [],
            "manual_execute_commands": [],
            "excluded_destructive_commands": [["rm", "-rf", "~/.cargo"], ["cargo", "cache", "--remove-dir", "all"]],
            "preserve": ["Cargo credentials", "Cargo config", "installed binaries", "project target directories"],
            "notes": [
                "Cargo has no built-in stable cache dry-run command; cleanmac reports path-based cargo cache candidates separately.",
                "Use the cargoCaches category for recoverable Trash-mode cleanup after reviewing candidate paths.",
            ],
        },
    }


def selected_adapters(tool: str) -> dict[str, dict[str, Any]]:
    adapters = tool_adapters()
    if tool == "all":
        return adapters
    if tool == "package-managers":
        return {key: adapters[key] for key in PACKAGE_MANAGER_ADAPTER_KEYS}
    return {tool: adapters[tool]}


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
                "cleanup_scope": list(adapter.get("cleanup_scope", [])),
                "path_categories": list(adapter.get("path_categories", [])),
                "risk_explanation": adapter.get("risk_explanation", "Review tool output before running any cleanup command."),
                "dry_run_explanation": "Only commands listed in dry_run_commands are run by tool-execute without --execute.",
                "execution_policy": {
                    "default_mode": "dry-run",
                    "auto_execute_allowed": False,
                    "requires_human_confirmation_for_execute": True,
                    "external_prune_commands_are_recommendations_only_in_plan": True,
                },
                "recommended_commands": [
                    *[
                        {"purpose": "dry-run-analysis", "argv": list(command), "auto_call_allowed": True}
                        for command in adapter["dry_run_commands"]
                    ],
                    *[
                        {"purpose": "manual-human-confirmed-cleanup", "argv": list(command), "auto_call_allowed": False}
                        for command in adapter["manual_execute_commands"]
                    ],
                ],
                "auto_execute_allowed": False,
                "notes": list(adapter.get("notes", []))
                + [
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
        "execution_policy": {
            "default_mode": "dry-run",
            "auto_execute_allowed": False,
            "requires_human_confirmation_for_execute": True,
            "external_prune_commands_are_recommendations_only_in_plan": True,
        },
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
