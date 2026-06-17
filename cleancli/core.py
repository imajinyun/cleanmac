#!/usr/bin/env python3
"""CleanMac is a lightweight macOS cleanup CLI.

The command intentionally defaults to dry-run mode. Destructive cleanup only
happens when the caller passes ``clean --execute``. For validation, ``--root``
and ``--home`` can remap macOS paths into a sandbox directory so no host paths
are touched.
"""

from __future__ import annotations

import argparse
import glob
import json
import os
import re
import shlex
import shutil
import subprocess
import sys
import time
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from cleancli import delete_ops, protection
from cleancli.protection_data import APP_CLEANUP_RULES, DEFAULT_PROTECTED_BUNDLE_IDS, OFFICIAL_UNINSTALLER_RULES

LOG_CATEGORY_KEYS = {"userLogs", "systemLogs", "userAppLogs", "terminal"}
CACHE_CATEGORY_KEYS = {"userCache", "userAppCache"}
LOG_LINK_DIR = "~/.CleanMacAppLogLinks/"
CACHE_LINK_DIR = "~/.CleanMacAppCacheLinks/"
LOG_FILE = "~/.cleanmac/cleanmac.log"
DEBUG_SESSION_LOG_FILE = "~/.cleanmac/cleanmac_debug_session.log"
DELETE_LOG_FILE = "~/.cleanmac/deletions.log"
OPERATIONS_LOG_FILE = "~/.cleanmac/operations.jsonl"
LOG_ROTATE_BYTES = 1 * 1024 * 1024
OPERATIONS_LOG_ROTATE_BYTES = 5 * 1024 * 1024


@dataclass(frozen=True)
class Category:
    key: str
    title: str
    paths: tuple[str, ...]
    description: str
    group: str = "clean"
    risk: str = "low"
    default: bool = False
    recommended: bool = False
    advanced: bool = False
    requires_privilege: bool = False
    full_disk_access: bool = False
    provider: str | None = None
    delete_target: bool = False
    default_older_than_days: float | None = None
    default_min_size_mb: int = 0
    default_include_patterns: tuple[str, ...] = ()
    default_exclude_patterns: tuple[str, ...] = ()
    process_guard: str | None = None
    active_file_check: bool = False
    stale_days: float | None = None


@dataclass(frozen=True)
class ResolvedTarget:
    category: str
    source_pattern: str
    path: Path
    matched: bool
    from_glob: bool
    delete_target: bool = False


CATEGORIES: tuple[Category, ...] = (
    Category(
        "trash",
        "Trash",
        ("~/.Trash/",),
        "Deletes all files and folders in the user's Trash.",
        default=True,
        recommended=True,
    ),
    Category(
        "mails",
        "Apple Mail downloads",
        (
            "~/Library/Mail Downloads/",
            "~/Library/Containers/com.apple.mail/Data/Library/Mail Downloads/",
        ),
        "Deletes old downloaded Apple Mail attachments when Mail is not running.",
        default=True,
        recommended=True,
        default_older_than_days=30,
        default_min_size_mb=5,
        process_guard="Mail",
    ),
    Category(
        "xcode",
        "Xcode caches, derived data, and device logs",
        (
            "~/Library/Developer/Xcode/iOS Device Logs/",
            "~/Library/Developer/Xcode/DerivedData/",
            "~/Library/Developer/Xcode/Archives/",
            "~/Library/Developer/Xcode/Products/",
            "~/Library/Developer/Xcode/ModuleCache.noindex/",
            "~/Library/Developer/CoreSimulator/Caches/",
        ),
        "Deletes Xcode device logs, derived data, archives, module caches, products, and simulator caches.",
        default=True,
        recommended=True,
    ),
    Category(
        "deviceFirmware",
        "Xcode device support and firmware caches",
        (
            "~/Library/Developer/Xcode/iOS DeviceSupport/",
            "~/Library/Developer/Xcode/watchOS DeviceSupport/",
            "~/Library/Developer/Xcode/tvOS DeviceSupport/",
        ),
        "Deletes old Xcode device support symbols and firmware support caches used for connected devices.",
        risk="high",
        advanced=True,
        default_older_than_days=30,
    ),
    Category(
        "bash",
        "Bash history and sessions",
        ("~/.bash_sessions/", "~/.bash_history"),
        "Deletes Bash history and Bash session files.",
        risk="medium",
        advanced=True,
    ),
    Category(
        "terminal",
        "Terminal ASL logs",
        ("/private/var/log/asl/*.asl",),
        "Deletes *.asl log files used by older Terminal/system logging.",
        risk="medium",
        advanced=True,
        requires_privilege=True,
    ),
    Category(
        "userAppLogs",
        "Sandboxed application logs",
        ("~/Library/Containers/*/Data/Library/Logs/",),
        "Deletes per-application logs under user Library containers.",
        risk="medium",
        advanced=True,
    ),
    Category(
        "userAppCache",
        "Sandboxed application caches",
        ("~/Library/Containers/*/Data/Library/Caches/", "~/Library/Containers/*/Data/tmp/"),
        "Deletes per-application caches and tmp files under user Library containers while preserving protected app data.",
        risk="medium",
        advanced=True,
    ),
    Category(
        "groupContainerCaches",
        "Group Container logs, caches, and tmp files",
        (
            "~/Library/Group Containers/*/Library/Logs/",
            "~/Library/Group Containers/*/Library/Caches/",
            "~/Library/Group Containers/*/tmp/",
            "~/Library/Group Containers/*/Caches/",
        ),
        "Deletes safe logs/caches/tmp entries from Group Containers while skipping Apple, Safari extension, and protected app data containers.",
        risk="medium",
        advanced=True,
        default_older_than_days=7,
    ),
    Category(
        "androidStudio",
        APP_CLEANUP_RULES["androidStudio"]["title"],
        APP_CLEANUP_RULES["androidStudio"]["paths"],
        "Deletes Android Studio regenerable caches/logs while preserving SDKs, AVDs, signing keys, and projects.",
        risk="medium",
        advanced=True,
        process_guard="Android Studio",
    ),
    Category(
        "jetbrains",
        APP_CLEANUP_RULES["jetbrains"]["title"],
        APP_CLEANUP_RULES["jetbrains"]["paths"],
        "Deletes JetBrains IDE regenerable caches/logs while preserving settings and licenses.",
        risk="medium",
        advanced=True,
        process_guard="idea",
    ),
    Category(
        "vscode",
        APP_CLEANUP_RULES["vscode"]["title"],
        APP_CLEANUP_RULES["vscode"]["paths"],
        "Deletes VS Code regenerable caches while preserving User settings and workspace state.",
        risk="medium",
        advanced=True,
        process_guard="Code",
    ),
    Category(
        "docker",
        APP_CLEANUP_RULES["docker"]["title"],
        APP_CLEANUP_RULES["docker"]["paths"],
        "Deletes Docker Desktop cache/build artifacts while preserving auth, contexts, and daemon configuration.",
        risk="medium",
        advanced=True,
        process_guard="Docker",
    ),
    Category(
        "raycast",
        APP_CLEANUP_RULES["raycast"]["title"],
        APP_CLEANUP_RULES["raycast"]["paths"],
        "Deletes Raycast regenerable caches.",
        risk="medium",
        advanced=True,
        process_guard="Raycast",
    ),
    Category(
        "unity",
        APP_CLEANUP_RULES["unity"]["title"],
        APP_CLEANUP_RULES["unity"]["paths"],
        "Deletes Unity editor caches.",
        risk="medium",
        advanced=True,
        process_guard="Unity",
    ),
    Category(
        "unreal",
        APP_CLEANUP_RULES["unreal"]["title"],
        APP_CLEANUP_RULES["unreal"]["paths"],
        "Deletes Unreal Engine derived data cache.",
        risk="medium",
        advanced=True,
    ),
    Category(
        "godot",
        APP_CLEANUP_RULES["godot"]["title"],
        APP_CLEANUP_RULES["godot"]["paths"],
        "Deletes Godot editor caches.",
        risk="medium",
        advanced=True,
        process_guard="Godot",
    ),
    Category(
        "deveco",
        APP_CLEANUP_RULES["deveco"]["title"],
        APP_CLEANUP_RULES["deveco"]["paths"],
        "Deletes DevEco Studio regenerable caches/logs.",
        risk="medium",
        advanced=True,
        process_guard="DevEco Studio",
    ),
    Category(
        "maestro",
        APP_CLEANUP_RULES["maestro"]["title"],
        APP_CLEANUP_RULES["maestro"]["paths"],
        "Deletes Maestro CLI/test caches.",
        risk="medium",
        advanced=True,
    ),
    Category(
        "chrome",
        APP_CLEANUP_RULES["chrome"]["title"],
        APP_CLEANUP_RULES["chrome"]["paths"],
        "Deletes Chrome regenerable browser caches while preserving profile data, cookies, history, bookmarks, passwords, and extensions.",
        risk="medium",
        advanced=True,
        process_guard="Google Chrome",
    ),
    Category(
        "firefox",
        APP_CLEANUP_RULES["firefox"]["title"],
        APP_CLEANUP_RULES["firefox"]["paths"],
        "Deletes Firefox regenerable browser caches while preserving profile data, cookies, history, passwords, certificates, preferences, and extensions.",
        risk="medium",
        advanced=True,
        process_guard="Firefox",
    ),
    Category(
        "slack",
        APP_CLEANUP_RULES["slack"]["title"],
        APP_CLEANUP_RULES["slack"]["paths"],
        "Deletes Slack regenerable caches while preserving local workspace storage and account state.",
        risk="medium",
        advanced=True,
        process_guard="Slack",
    ),
    Category(
        "zoom",
        APP_CLEANUP_RULES["zoom"]["title"],
        APP_CLEANUP_RULES["zoom"]["paths"],
        "Deletes Zoom regenerable caches while preserving account databases and cookies.",
        risk="medium",
        advanced=True,
        process_guard="zoom.us",
    ),
    Category(
        "teams",
        APP_CLEANUP_RULES["teams"]["title"],
        APP_CLEANUP_RULES["teams"]["paths"],
        "Deletes Microsoft Teams regenerable caches while preserving local workspace storage and account state.",
        risk="medium",
        advanced=True,
        process_guard="Microsoft Teams",
    ),
    Category(
        "nodePackageCaches",
        APP_CLEANUP_RULES["nodePackageCaches"]["title"],
        APP_CLEANUP_RULES["nodePackageCaches"]["paths"],
        "Deletes npm, pnpm, and Yarn package download caches while preserving auth and registry configuration.",
        risk="medium",
        advanced=True,
    ),
    Category(
        "pythonPackageCaches",
        APP_CLEANUP_RULES["pythonPackageCaches"]["title"],
        APP_CLEANUP_RULES["pythonPackageCaches"]["paths"],
        "Deletes pip, Poetry, and PDM package download caches while preserving publishing credentials.",
        risk="medium",
        advanced=True,
    ),
    Category(
        "goBuildCaches",
        APP_CLEANUP_RULES["goBuildCaches"]["title"],
        APP_CLEANUP_RULES["goBuildCaches"]["paths"],
        "Deletes Go build cache and module download cache while preserving Go environment and credential files.",
        risk="medium",
        advanced=True,
    ),
    Category(
        "postman",
        APP_CLEANUP_RULES["postman"]["title"],
        APP_CLEANUP_RULES["postman"]["paths"],
        "Deletes Postman regenerable caches while preserving workspaces, collections, cookies, and local storage.",
        risk="medium",
        advanced=True,
        process_guard="Postman",
    ),
    Category(
        "insomnia",
        APP_CLEANUP_RULES["insomnia"]["title"],
        APP_CLEANUP_RULES["insomnia"]["paths"],
        "Deletes Insomnia regenerable caches while preserving workspace databases, cookies, and local storage.",
        risk="medium",
        advanced=True,
        process_guard="Insomnia",
    ),
    Category(
        "aiToolCaches",
        APP_CLEANUP_RULES["aiToolCaches"]["title"],
        APP_CLEANUP_RULES["aiToolCaches"]["paths"],
        "Deletes regenerable Claude, Cursor, ChatGPT, and Ollama caches while preserving AI tool runtime state and credentials.",
        risk="medium",
        advanced=True,
    ),
    Category(
        "userCache",
        "User caches",
        ("~/Library/Caches/",),
        "Deletes user-level application caches.",
        risk="medium",
        advanced=True,
    ),
    Category(
        "userLogs",
        "User logs",
        ("~/Library/logs/",),
        "Deletes user-level logs.",
        risk="medium",
        advanced=True,
    ),
    Category(
        "systemLogs",
        "System logs",
        ("/Library/logs/", "/var/log/"),
        "Deletes system logs.",
        risk="high",
        advanced=True,
        requires_privilege=True,
    ),
    Category(
        "globalTemp",
        "Global temporary files",
        ("/tmp/",),
        "Deletes global temporary files.",
        risk="high",
        advanced=True,
        requires_privilege=True,
    ),
    Category(
        "userPrefs",
        "User preferences",
        ("~/Library/Preferences/",),
        "Deletes user preference files. This is risky and not recommended.",
        risk="critical",
        advanced=True,
    ),
    Category(
        "downloads",
        "Downloads",
        ("~/Downloads/",),
        "Deletes everything in the user's Downloads folder.",
        risk="high",
        advanced=True,
    ),
    Category(
        "incompleteDownloads",
        "Incomplete browser downloads",
        (
            "~/Downloads/*.download",
            "~/Downloads/*.crdownload",
            "~/Downloads/*.part",
        ),
        "Deletes incomplete browser download fragments that are not currently open.",
        default=True,
        recommended=True,
        active_file_check=True,
    ),
    Category(
        "spotlight",
        "Spotlight index",
        ("/.Spotlight-V100/",),
        "Deletes Spotlight index data so macOS can rebuild it.",
        risk="high",
        advanced=True,
        requires_privilege=True,
    ),
    Category(
        "docRev",
        "Document revisions",
        ("/.DocumentRevisions-V100/",),
        "Deletes macOS document revision data. This removes autosave/version history.",
        risk="critical",
        advanced=True,
        requires_privilege=True,
    ),
    Category(
        "imessage",
        "iMessage attachments",
        ("~/Library/Messages/Attachments/",),
        "Deletes received iMessage attachments.",
        risk="high",
        advanced=True,
        requires_privilege=True,
        full_disk_access=True,
    ),
    Category(
        "systemCaches",
        "System cache files",
        (
            "/Library/Caches/**/*.cache",
            "/Library/Caches/**/*.tmp",
            "/Library/Caches/**/*.log",
        ),
        "Deletes old rebuildable system cache, temp, and log files under /Library/Caches.",
        risk="high",
        advanced=True,
        requires_privilege=True,
        delete_target=True,
        default_older_than_days=7,
    ),
    Category(
        "systemDiagnostics",
        "System diagnostic reports",
        (
            "/Library/Logs/DiagnosticReports/",
            "/private/var/db/diagnostics/",
            "/private/var/db/DiagnosticPipeline/",
            "/private/var/db/powerlog/",
            "/private/var/db/reportmemoryexception/",
        ),
        "Deletes old system diagnostic logs and diagnostic pipeline artifacts.",
        risk="high",
        advanced=True,
        requires_privilege=True,
        default_older_than_days=14,
    ),
    Category(
        "appleSiliconCaches",
        "Apple Silicon and Rosetta runtime caches",
        (
            "/private/var/db/oah/",
            "/private/var/db/DetachedSignatures/",
        ),
        "Deletes old rebuildable Apple Silicon/Rosetta runtime caches and detached signature cache artifacts.",
        risk="high",
        advanced=True,
        requires_privilege=True,
        default_older_than_days=14,
    ),
    Category(
        "thirdPartySystemLogs",
        "Third-party system logs",
        (
            "/Library/Logs/Adobe/",
            "/Library/Logs/CreativeCloud/",
            "/Library/Logs/adobegc.log",
        ),
        "Deletes old Adobe and Creative Cloud system logs.",
        risk="medium",
        advanced=True,
        requires_privilege=True,
        default_older_than_days=14,
    ),
    Category(
        "macosInstallers",
        "macOS installer remnants",
        (
            "/macOS Install Data/",
            "/Applications/Install macOS*.app",
        ),
        "Deletes old macOS installer data and installer apps after safety checks.",
        risk="high",
        advanced=True,
        requires_privilege=True,
        delete_target=True,
        default_older_than_days=14,
    ),
    Category(
        "systemUpdates",
        "System update remnants",
        ("/Library/Updates/",),
        "Deletes removable system update remnants while skipping restricted items.",
        risk="high",
        advanced=True,
        requires_privilege=True,
        default_older_than_days=14,
    ),
    Category(
        "browserCodeSignCache",
        "Browser code signature caches",
        (),
        "Deletes rebuildable browser code signature clone caches under Darwin user cache shards.",
        risk="medium",
        advanced=True,
        requires_privilege=True,
        provider="browser-code-sign-cache",
        delete_target=True,
    ),
    Category(
        "gpuCaches",
        "Rebuildable GPU and Metal caches",
        (),
        "Deletes stale rebuildable GPU and Metal caches under Darwin cache shards.",
        risk="medium",
        advanced=True,
        requires_privilege=True,
        provider="gpu-cache",
        delete_target=True,
        stale_days=1,
    ),
    Category(
        "darwinUserTemp",
        "Darwin user temporary files",
        (),
        "Deletes old files from the current user's DARWIN_USER_TEMP_DIR after ownership and path checks.",
        risk="medium",
        advanced=True,
        provider="darwin-user-temp",
        default_older_than_days=7,
        default_exclude_patterns=("*.sqlite", "*.sqlite-shm", "*.sqlite-wal", "*.db", "*.plist"),
    ),
    Category(
        "darwinUserCache",
        "Darwin user runtime caches",
        (),
        "Deletes old files from the current user's DARWIN_USER_CACHE_DIR after ownership and path checks.",
        risk="medium",
        advanced=True,
        provider="darwin-user-cache",
        default_older_than_days=7,
        default_exclude_patterns=("*.sqlite", "*.sqlite-shm", "*.sqlite-wal", "*.db", "*.plist"),
    ),
)

CATEGORY_BY_KEY = {category.key: category for category in CATEGORIES}

COMMAND_GROUPS: dict[str, dict[str, Any]] = {
    "clean": {
        "title": "清理 / Cleanup",
        "description": "Inspect, plan, validate, preview, and run file cleanup tasks.",
        "commands": [
            "clean list",
            "clean inspect",
            "clean plan",
            "clean validate-plan",
            "clean run",
            "clean scripts",
            "clean open",
            "clean links",
        ],
        "flat_command_aliases": ["list", "inspect", "plan", "validate-plan", "clean", "scripts", "open", "links"],
    },
    "software": {
        "title": "软件 / Software",
        "description": "Read-only app inventory, startup-item review, and uninstall-plan placeholders for app cleanup governance.",
        "commands": ["software list", "software leftovers", "software startup-items", "software uninstall-plan"],
        "flat_command_aliases": [],
    },
    "optimize": {
        "title": "优化 / Optimize",
        "description": "System maintenance task inventory and dry-run execution planning.",
        "commands": ["optimize list", "optimize plan", "optimize run"],
        "flat_command_aliases": ["doctor", "workflow"],
    },
    "analyze": {
        "title": "分析 / Analyze",
        "description": "Category reclaim analysis and directory tree scans for CLI workflows.",
        "commands": ["analyze categories", "analyze scan", "analyze tree"],
        "flat_command_aliases": ["analyze"],
    },
    "status": {
        "title": "状态 / Status",
        "description": "Read-only system health snapshots.",
        "commands": ["status snapshot"],
        "flat_command_aliases": [],
    },
}

GROUPED_COMMAND_ALIASES: dict[tuple[str, str], str] = {
    ("clean", "list"): "list",
    ("clean", "inspect"): "inspect",
    ("clean", "plan"): "plan",
    ("clean", "validate-plan"): "validate-plan",
    ("clean", "run"): "clean",
    ("clean", "scripts"): "scripts",
    ("clean", "open"): "open",
    ("clean", "links"): "links",
    ("analyze", "categories"): "analyze",
    ("analyze", "scan"): "analyze-tree",
    ("analyze", "tree"): "analyze-tree",
}


def parse_args(argv: Sequence[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="cleanmac",
        description="macOS cleanup CLI. Defaults to dry-run for destructive commands.",
    )
    parser.add_argument(
        "--root",
        default="/",
        help="Remap absolute macOS paths under this root. Use a sandbox path for tests.",
    )
    parser.add_argument(
        "--home",
        default=str(Path.home()),
        help="Home path used for ~ expansion before --root remapping.",
    )
    parser.add_argument("--json", action="store_true", help="Emit machine-readable JSON.")
    parser.add_argument(
        "--report-file",
        help="Write the command report to a JSON audit file while still printing the normal output.",
    )

    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("list", help="List available cleanup categories.")
    subparsers.add_parser("capabilities", help="Describe commands and safety guardrails.")
    subparsers.add_parser("doctor", help="Run non-destructive environment and permission diagnostics.")

    scripts = subparsers.add_parser("scripts", help="Print cleanup command templates for selected categories.")
    add_category_flags(scripts, default_scope="all")
    scripts.add_argument(
        "--group", choices=("all", "clean", "software", "optimize", "analyze", "status"), default="all"
    )

    inspect_cmd = subparsers.add_parser(
        "inspect",
        help="List direct child items that would be removed, with sizes. Does not delete files.",
    )
    add_category_flags(inspect_cmd, default_scope="default")
    inspect_cmd.add_argument("--limit", type=int, default=50)
    inspect_cmd.add_argument("--recursive", action="store_true")
    inspect_cmd.add_argument("--min-size-mb", type=int, default=0)
    inspect_cmd.add_argument("--sort", choices=("size-desc", "size-asc", "path"), default="size-desc")
    inspect_cmd.add_argument("--exclude")
    inspect_cmd.add_argument("--include")
    inspect_cmd.add_argument("--name-regex")
    inspect_cmd.add_argument("--older-than-days", type=float)
    inspect_cmd.add_argument("--max-delete-mb", type=float)
    inspect_cmd.add_argument("--max-items", type=int)

    analyze_cmd = subparsers.add_parser("analyze", help="Calculate reclaimable space without deleting files.")
    add_category_flags(analyze_cmd, default_scope="all")

    plan_cmd = subparsers.add_parser("plan", help="Generate a reusable JSON cleanup plan without deleting files.")
    add_category_flags(plan_cmd, default_scope="default")
    plan_cmd.add_argument(
        "--risk-policy",
        choices=("strict", "default", "permissive"),
        default="default",
        help="Risk policy to store in the generated plan.",
    )
    plan_cmd.add_argument("--max-delete-mb", type=float)
    plan_cmd.add_argument("--exclude")
    plan_cmd.add_argument("--include")
    plan_cmd.add_argument("--min-size-mb", type=int, default=0)
    plan_cmd.add_argument("--name-regex")
    plan_cmd.add_argument("--max-items", type=int)
    plan_cmd.add_argument("--older-than-days", type=float)

    validate_plan = subparsers.add_parser("validate-plan", help="Validate a cleanup plan/audit JSON file.")
    validate_plan.add_argument("--plan-file", required=True)

    analyze_tree = subparsers.add_parser("analyze-tree", help=argparse.SUPPRESS)
    analyze_tree.add_argument("--path", default="~", help="Directory to scan.")
    analyze_tree.add_argument("--depth", type=int, default=2)
    analyze_tree.add_argument("--top", type=int, default=20)
    analyze_tree.add_argument("--min-size-mb", type=int, default=0)

    diagnose_cmd = subparsers.add_parser("diagnose", help="Analyze cleanup categories and emit recommendations.")
    add_category_flags(diagnose_cmd, default_scope="all")
    diagnose_cmd.add_argument("--log-threshold-mb", type=int, default=100)
    diagnose_cmd.add_argument("--large-threshold-mb", type=int, default=1024)

    workflow_cmd = subparsers.add_parser("workflow", help="Run the fixed safe workflow without destructive cleanup.")
    add_category_flags(workflow_cmd, default_scope="all")
    workflow_cmd.add_argument("--inspect-limit", type=int, default=25)
    workflow_cmd.add_argument("--log-threshold-mb", type=int, default=100)
    workflow_cmd.add_argument("--large-threshold-mb", type=int, default=1024)
    workflow_cmd.add_argument("--dry-run-scope", choices=("recommended", "selected"), default="recommended")

    open_cmd = subparsers.add_parser("open", help="Preview or execute Finder targets.")
    add_category_flags(open_cmd, default_scope="default")
    open_cmd.add_argument("--execute", action="store_true")

    links_cmd = subparsers.add_parser("links", help="Preview, create, or remove app log/cache symlink folders.")
    links_cmd.add_argument("--kind", choices=("all", "logs", "cache"), default="all")
    links_cmd.add_argument("--execute", action="store_true")
    links_cmd.add_argument("--remove", action="store_true")

    clean_cmd = subparsers.add_parser("clean", help="Clean selected categories. Dry-run unless --execute is passed.")
    add_category_flags(clean_cmd, default_scope="default")
    clean_cmd.add_argument("--execute", action="store_true")
    clean_cmd.add_argument("--yes", action="store_true")
    clean_cmd.add_argument(
        "--risk-policy",
        choices=("strict", "default", "permissive"),
        default="default",
        help="Controls which selected risks require --yes.",
    )
    clean_cmd.add_argument("--plan-file")
    clean_cmd.add_argument("--max-delete-mb", type=float)
    clean_cmd.add_argument("--exclude")
    clean_cmd.add_argument("--include")
    clean_cmd.add_argument("--min-size-mb", type=int, default=0)
    clean_cmd.add_argument("--name-regex")
    clean_cmd.add_argument("--max-items", type=int)
    clean_cmd.add_argument("--older-than-days", type=float)
    clean_cmd.add_argument("--allow-live-root", action="store_true")
    clean_cmd.add_argument("--require-plan-context", action="store_true")
    clean_cmd.add_argument("--fail-on-skipped", action="store_true")
    clean_cmd.add_argument(
        "--bundle-allowlist",
        help="Comma-separated bundle IDs that may be cleaned; other bundle-owned candidates are skipped.",
    )
    clean_cmd.add_argument(
        "--bundle-blocklist",
        default=",".join(DEFAULT_PROTECTED_BUNDLE_IDS),
        help="Comma-separated bundle IDs protected from cleanup. Defaults protect selected Apple app containers.",
    )
    clean_cmd.add_argument(
        "--delete-mode",
        choices=("permanent", "trash"),
        default="permanent",
        help="Delete permanently or move candidates to the user's Trash for recovery.",
    )
    clean_cmd.add_argument(
        "--operation-log",
        default=OPERATIONS_LOG_FILE,
        help="Append JSONL deletion audit records to this file when executing.",
    )

    software_cmd = subparsers.add_parser("software", help="Software inventory and app cleanup planning.")
    software_cmd.add_argument(
        "action", nargs="?", choices=("list", "leftovers", "startup-items", "uninstall-plan"), default="list"
    )
    software_cmd.add_argument("--app", help="Application name or bundle id for uninstall planning.")

    optimize_cmd = subparsers.add_parser("optimize", help="System maintenance planning.")
    optimize_cmd.add_argument("action", nargs="?", choices=("list", "plan", "run"), default="list")
    optimize_cmd.add_argument(
        "--execute",
        action="store_true",
        help="Reserved for future maintenance execution; current tasks remain dry-run.",
    )

    status_cmd = subparsers.add_parser("status", help="Read-only system health snapshots.")
    status_cmd.add_argument("action", nargs="?", choices=("snapshot",), default="snapshot")

    return parser.parse_args(argv)


def normalize_grouped_argv(argv: Sequence[str]) -> tuple[list[str], dict[str, str] | None]:
    normalized = list(argv)
    known_commands = {
        "list",
        "capabilities",
        "doctor",
        "scripts",
        "inspect",
        "analyze",
        "plan",
        "validate-plan",
        "analyze-tree",
        "diagnose",
        "workflow",
        "open",
        "links",
        "clean",
        "software",
        "optimize",
        "status",
    }
    first_command_index = next((index for index, item in enumerate(normalized) if item in known_commands), None)
    if first_command_index is None or first_command_index + 1 >= len(normalized):
        return normalized, None
    group = normalized[first_command_index]
    action = normalized[first_command_index + 1]
    mapped = GROUPED_COMMAND_ALIASES.get((group, action))
    if mapped is None:
        return normalized, None
    normalized[first_command_index : first_command_index + 2] = [mapped]
    return normalized, {"group": group, "action": action, "mapped_command": mapped}


def add_category_flags(parser: argparse.ArgumentParser, default_scope: str) -> None:
    parser.set_defaults(default_scope=default_scope)
    parser.add_argument(
        "--categories",
        help="Comma-separated category keys. Use 'cleanmac list' to see valid keys.",
    )
    parser.add_argument("--default", action="store_true", help="Use default categories.")
    parser.add_argument("--all", action="store_true", help="Include all categories, including advanced/risky ones.")


def parse_csv(value: str | None) -> tuple[str, ...]:
    if not value:
        return ()
    return tuple(item.strip() for item in value.split(",") if item.strip())


def display_path(path: Path | str) -> str:
    text = str(path)
    if sys.platform == "darwin" and text.startswith("/private/var/"):
        return "/var/" + text[len("/private/var/") :]
    return text


def same_context_path(expected: str | None, actual: Path | str) -> bool:
    if expected is None:
        return True
    if display_path(expected) == display_path(actual):
        return True
    try:
        return Path(expected).expanduser().resolve(strict=False) == Path(actual).expanduser().resolve(strict=False)
    except OSError:
        return False


def select_categories(args: argparse.Namespace) -> list[Category]:
    if args.categories:
        requested = list(parse_csv(args.categories))
        unknown = [key for key in requested if key not in CATEGORY_BY_KEY]
        if unknown:
            valid = ", ".join(category.key for category in CATEGORIES)
            raise SystemExit(f"Unknown category: {', '.join(unknown)}. Valid categories: {valid}")
        return [CATEGORY_BY_KEY[key] for key in requested]
    if args.all or (not args.default and args.default_scope == "all"):
        return list(CATEGORIES)
    return [category for category in CATEGORIES if category.default]


def selected_high_risk_categories(categories: Iterable[Category]) -> list[Category]:
    return [category for category in categories if category.risk in {"high", "critical"}]


def categories_requiring_yes(categories: Iterable[Category], risk_policy: str) -> list[Category]:
    if risk_policy == "strict":
        return [category for category in categories if category.risk in {"medium", "high", "critical"}]
    if risk_policy == "permissive":
        return []
    return selected_high_risk_categories(categories)


def normalize_plan_category_keys(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    keys = []
    for item in value:
        if isinstance(item, str):
            keys.append(item)
        elif isinstance(item, dict) and isinstance(item.get("key"), str):
            keys.append(str(item["key"]))
    return keys


def normalize_risk_policy(value: object) -> str | None:
    if value in {"strict", "default", "permissive"}:
        return str(value)
    return None


def load_clean_plan(plan_file: str) -> dict[str, Any]:
    plan_path = Path(plan_file).expanduser().resolve(strict=False)
    payload = json.loads(plan_path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise SystemExit(f"Plan file must contain a JSON object: {plan_path}")
    plan = (
        payload.get("report")
        if payload.get("schema") == "cleanmac.audit.v1" and isinstance(payload.get("report"), dict)
        else payload
    )
    if not isinstance(plan, dict):
        raise SystemExit(f"Plan file does not contain a usable report object: {plan_path}")

    category_keys = normalize_plan_category_keys(plan.get("selected_category_keys"))
    if not category_keys:
        category_keys = normalize_plan_category_keys(plan.get("categories"))
    if not category_keys:
        category_keys = normalize_plan_category_keys(plan.get("selected_categories"))

    safety_gate = plan.get("safety_gate")
    max_delete_mb = plan.get("max_delete_mb")
    if isinstance(safety_gate, dict) and max_delete_mb is None:
        max_delete_mb = safety_gate.get("max_delete_mb")

    return {
        "path": display_path(plan_path),
        "category_keys": category_keys,
        "risk_policy": normalize_risk_policy(plan.get("risk_policy")),
        "max_delete_mb": max_delete_mb if isinstance(max_delete_mb, (int, float)) else None,
        "exclude_patterns": normalize_plan_category_keys(plan.get("exclude_patterns")),
        "include_patterns": normalize_plan_category_keys(plan.get("include_patterns")),
        "older_than_days": plan.get("older_than_days")
        if isinstance(plan.get("older_than_days"), (int, float))
        else None,
        "min_size_mb": plan.get("min_size_mb") if isinstance(plan.get("min_size_mb"), int) else None,
        "name_regex": str(plan.get("name_regex")) if isinstance(plan.get("name_regex"), str) else None,
        "max_items": plan.get("max_items") if isinstance(plan.get("max_items"), int) else None,
        "root": str(plan.get("root")) if isinstance(plan.get("root"), str) else None,
        "home": str(plan.get("home")) if isinstance(plan.get("home"), str) else None,
    }


def apply_clean_plan_defaults(args: argparse.Namespace) -> dict[str, Any] | None:
    if getattr(args, "command", None) != "clean" or not getattr(args, "plan_file", None):
        return None
    plan = load_clean_plan(args.plan_file)
    if not args.categories and plan["category_keys"]:
        args.categories = ",".join(str(key) for key in plan["category_keys"])
    if args.risk_policy == "default" and plan["risk_policy"]:
        args.risk_policy = str(plan["risk_policy"])
    if args.max_delete_mb is None and plan["max_delete_mb"] is not None:
        args.max_delete_mb = float(plan["max_delete_mb"])
    if not getattr(args, "exclude", None) and plan["exclude_patterns"]:
        args.exclude = ",".join(str(pattern) for pattern in plan["exclude_patterns"])
    if not getattr(args, "include", None) and plan["include_patterns"]:
        args.include = ",".join(str(pattern) for pattern in plan["include_patterns"])
    if getattr(args, "older_than_days", None) is None and plan["older_than_days"] is not None:
        args.older_than_days = float(plan["older_than_days"])
    if getattr(args, "min_size_mb", 0) == 0 and plan["min_size_mb"] is not None:
        args.min_size_mb = int(plan["min_size_mb"])
    if not getattr(args, "name_regex", None) and plan["name_regex"]:
        args.name_regex = str(plan["name_regex"])
    if getattr(args, "max_items", None) is None and plan["max_items"] is not None:
        args.max_items = int(plan["max_items"])
    return plan


def remap_path(pattern: str, *, root: Path, home: Path) -> str:
    expanded = str(home / pattern[2:]) if pattern.startswith("~/") else (str(home) if pattern == "~" else pattern)
    expanded_path = Path(expanded)
    if root == Path("/"):
        return str(expanded_path)
    if expanded_path.is_absolute():
        return str(root / str(expanded_path).lstrip("/"))
    return str(root / expanded_path)


def provider_base(root: Path, absolute_path: str) -> Path:
    return Path(absolute_path) if root == Path("/") else root / absolute_path.lstrip("/")


def run_text_command(argv: Sequence[str], *, timeout: float = 2) -> str | None:
    return delete_ops.run_text_command(argv, timeout=timeout)


def is_test_mode() -> bool:
    return delete_ops.is_test_mode()


def is_test_no_auth() -> bool:
    return delete_ops.is_test_no_auth()


def current_uid() -> int | None:
    try:
        return os.getuid()
    except AttributeError:
        return None


def path_owner_uid(path: Path) -> int | None:
    try:
        return path.stat().st_uid
    except OSError:
        return None


def darwin_runtime_dir_from_getconf(kind: str) -> Path | None:
    variable = "DARWIN_USER_TEMP_DIR" if kind == "temp" else "DARWIN_USER_CACHE_DIR"
    output = run_text_command(["getconf", variable])
    if not output:
        return None
    return Path(output)


def is_safe_darwin_runtime_dir(path: Path, *, kind: str, root: Path) -> bool:
    if not path.exists() or not path.is_dir() or path.is_symlink():
        return False
    try:
        resolved = path.resolve(strict=False)
    except OSError:
        return False
    base = provider_base(root, "/private/var/folders").resolve(strict=False)
    marker = "T" if kind == "temp" else "C"
    if not is_relative_to(resolved, base):
        return False
    relative = resolved.relative_to(base)
    if len(relative.parts) < 3 or relative.parts[2] != marker:
        return False
    uid = current_uid()
    owner = path_owner_uid(resolved)
    return uid is None or owner is None or owner == uid


def provider_targets(category: Category, *, root: Path, home: Path) -> list[ResolvedTarget]:
    provider = category.provider
    if provider is None:
        return []

    paths: list[Path] = []
    if provider in {"darwin-user-temp", "darwin-user-cache"}:
        kind = "temp" if provider == "darwin-user-temp" else "cache"
        if root == Path("/"):
            runtime_dir = darwin_runtime_dir_from_getconf(kind)
            if runtime_dir is not None:
                paths.append(runtime_dir)
        else:
            marker = "T" if kind == "temp" else "C"
            base = provider_base(root, "/private/var/folders")
            paths.extend(Path(item) for item in glob.glob(str(base / "*" / "*" / marker)))
        paths = [path for path in paths if is_safe_darwin_runtime_dir(path, kind=kind, root=root)]
    elif provider == "browser-code-sign-cache":
        base = provider_base(root, "/private/var/folders")
        paths.extend(
            Path(item) for item in glob.glob(str(base / "*" / "*" / "X" / "**" / "*.code_sign_clone"), recursive=True)
        )
    elif provider == "gpu-cache":
        base = provider_base(root, "/private/var/folders")
        for name in ("com.apple.gpuarchiver", "com.apple.metal", "com.apple.metalfe"):
            paths.extend(Path(item) for item in glob.glob(str(base / "*" / "*" / "C" / "**" / name), recursive=True))

    return [
        ResolvedTarget(category.key, f"provider:{provider}", path, path.exists(), True, category.delete_target)
        for path in paths
    ]


def resolve_targets(categories: Iterable[Category], *, root: Path, home: Path) -> list[ResolvedTarget]:
    targets: list[ResolvedTarget] = []
    for category in categories:
        if category.provider:
            targets.extend(provider_targets(category, root=root, home=home))
            continue
        for source_pattern in category.paths:
            remapped = remap_path(source_pattern, root=root, home=home)
            has_glob = any(char in remapped for char in "*?[")
            matches = [Path(item) for item in glob.glob(remapped, recursive="**" in remapped)] if has_glob else []
            if has_glob and matches:
                targets.extend(
                    ResolvedTarget(category.key, source_pattern, match, True, True, category.delete_target)
                    for match in matches
                )
            elif has_glob:
                targets.append(
                    ResolvedTarget(category.key, source_pattern, Path(remapped), False, True, category.delete_target)
                )
            else:
                path = Path(remapped)
                targets.append(
                    ResolvedTarget(category.key, source_pattern, path, path.exists(), False, category.delete_target)
                )
    return targets


def category_metadata(category: Category) -> dict[str, Any]:
    return {
        "key": category.key,
        "title": category.title,
        "risk": category.risk,
        "default": category.default,
        "recommended": category.recommended,
        "advanced": category.advanced,
        "requires_privilege": category.requires_privilege,
        "full_disk_access": category.full_disk_access,
        "group": category.group,
        "provider": category.provider,
        "delete_target": category.delete_target,
        "default_older_than_days": category.default_older_than_days,
        "default_min_size_mb": category.default_min_size_mb,
        "default_include_patterns": list(category.default_include_patterns),
        "default_exclude_patterns": list(category.default_exclude_patterns),
        "process_guard": category.process_guard,
        "active_file_check": category.active_file_check,
        "stale_days": category.stale_days,
        "description": category.description,
        "paths": list(category.paths),
    }


def render_boundary_governance() -> dict[str, Any]:
    return {
        "schema": "cleanmac.boundary-governance.v1",
        "purpose": "Define safe automation boundaries for cleanup operations.",
        "automated_safe_behaviors": [
            "list",
            "capabilities",
            "doctor",
            "analyze",
            "diagnose",
            "inspect",
            "plan",
            "validate-plan",
            "workflow",
            "scripts",
        ],
        "manual_only_behaviors": [
            {
                "id": "destructive-clean-execution",
                "required_flags": ["clean --execute", "--yes for high/critical categories"],
            },
            {"id": "live-root-clean-execution", "required_flags": ["--allow-live-root", "--execute"]},
            {
                "id": "full-disk-access-grant",
                "policy": "Granting macOS Full Disk Access remains a manual System Settings action.",
            },
        ],
        "forbidden_automation": ["clean --execute", "--allow-live-root", "sudo rm", "rm -rf /"],
        "script_template_policy": {
            "parse_and_preview_allowed": True,
            "auto_execute_allowed": False,
            "destructive_templates_require_manual_review": True,
            "global_flags_before_command": True,
            "recommended_delete_templates_use_cleanmac_cli": True,
            "raw_rm_rf_requires_deprecation_metadata": True,
        },
        "privileged_command_ownership": {
            "boundary_modules": ["cleancli/delete_ops.py"],
            "blocked_commands": ["sudo", "osascript", "launchctl"],
            "scan_command": "python3 scripts/security_scan.py",
        },
        "verification": {
            "python_test_environment": {
                "requires_virtualenv": True,
                "workflow_python_env": "PYTHON=.venv/bin/python",
                "ci_policy": "GitHub Actions must create a venv before running Python test or smoke commands.",
            },
            "required_commands": [
                "make quality-check",
                "make local-test",
                "make build-check",
                "make package-smoke",
                "make script-smoke",
                "make bundle-audit-smoke",
                "make macos-smoke",
                "make security-smoke",
                "make dependency-audit-smoke",
                "make docs-smoke",
                "make governance-smoke",
                "make open-source-smoke",
                "make distribution-smoke",
                "make docker-test",
                "make release-check",
            ],
        },
    }


def render_capabilities() -> dict[str, Any]:
    return {
        "schema": "cleanmac.capabilities.v1",
        "name": "cleanmac",
        "destructive": False,
        "model": "Dry-run-first CLI with sandbox remapping, reusable plans, filters, and execution budgets.",
        "category_count": len(CATEGORIES),
        "active_path_count": sum(len(category.paths) for category in CATEGORIES),
        "commands": [
            "list",
            "capabilities",
            "doctor",
            "scripts",
            "analyze",
            "diagnose",
            "inspect",
            "plan",
            "validate-plan",
            "workflow",
            "open",
            "links",
            "clean",
            "software",
            "optimize",
            "status",
        ],
        "command_groups": COMMAND_GROUPS,
        "preferred_command_style": "grouped",
        "flat_command_compatibility": True,
        "safety_guardrails": {
            "dry_run_default": True,
            "delete_requires_execute": True,
            "risk_policy": ["strict", "default", "permissive"],
            "high_or_critical_requires_yes_by_default": True,
            "sandbox_remap_flags": ["--root", "--home"],
            "deletion_budget_flag": "clean --max-delete-mb",
            "plan_replay_flag": "clean --plan-file",
            "include_filter_flag": "clean/inspect --include",
            "exclude_filter_flag": "clean/inspect --exclude",
            "age_filter_flag": "clean/inspect --older-than-days",
            "min_size_filter_flag": "clean/inspect --min-size-mb",
            "name_regex_filter_flag": "clean/inspect --name-regex",
            "max_items_budget_flag": "clean --max-items",
            "fail_on_skipped_flag": "clean --fail-on-skipped",
            "live_root_execute_flag": "clean --allow-live-root",
            "bundle_allowlist_flag": "clean --bundle-allowlist",
            "bundle_blocklist_flag": "clean --bundle-blocklist",
            "trash_routing_flag": "clean --delete-mode trash",
            "operation_log_flag": "clean --operation-log",
            "default_operation_log_file": OPERATIONS_LOG_FILE,
            "bundle_drift_audit": {
                "schema": "cleanmac.bundle-drift-audit.v1",
                "command": "python3 scripts/audit_bundle_drift.py --json --fail-on-drift",
                "system_roots": [
                    "/System/Applications",
                    "/System/Library/CoreServices",
                    "/System/Library/CoreServices/Applications",
                    "/System/Library/PreferencePanes",
                    "/Library/Apple/System/Library/CoreServices",
                    "/System/iOSSupport/System/Library/CoreServices",
                ],
                "informational_roots": ["/Applications"],
                "bundle_suffixes": [".app", ".appex", ".bundle", ".plugin", ".prefPane"],
                "scheduled_workflow": ".github/workflows/bundle_audit.yml",
            },
            "distribution_governance": {
                "schema": "cleanmac.distribution-governance.v1",
                "supported_artifacts": ["wheel", "sdist", "standalone-zipapp"],
                "release_manifest": "release-assets/ARTIFACT-MANIFEST.json",
                "homebrew_formula_policy": {
                    "status": "preflight-only",
                    "publish_automatically": False,
                    "recommended_install_method": "pipx or Homebrew formula generated from release checksums",
                    "formula_checks": ["class_name", "url", "sha256", "license", "test do"],
                },
                "standalone_smoke_command": "python cleanmac.pyz --json capabilities",
            },
            "privileged_command_ownership": render_boundary_governance()["privileged_command_ownership"],
            "log_rotation": {
                "log_file": LOG_FILE,
                "debug_session_log_file": DEBUG_SESSION_LOG_FILE,
                "delete_log_file": DELETE_LOG_FILE,
                "log_rotate_bytes": LOG_ROTATE_BYTES,
                "operations_log_file": OPERATIONS_LOG_FILE,
                "operations_log_rotate_bytes": OPERATIONS_LOG_ROTATE_BYTES,
                "rotation_function": "rotate_log_once",
            },
            "audit_file_flag": "--report-file",
            "default_protected_bundle_ids": list(DEFAULT_PROTECTED_BUNDLE_IDS),
            "default_protected_bundle_count": len(DEFAULT_PROTECTED_BUNDLE_IDS),
            "app_specific_cleanup_categories": sorted(APP_CLEANUP_RULES),
            "group_container_policy": {
                "category": "groupContainerCaches",
                "skip_apple_group_containers": True,
                "skip_safari_extension_containers": True,
                "protected_apps_logs_only": True,
            },
            "official_uninstaller_vendors": [str(rule["vendor"]) for rule in OFFICIAL_UNINSTALLER_RULES],
            "test_mode_environment": {
                "test_mode": ["CLEANMAC_TEST_MODE"],
                "no_auth": ["CLEANMAC_TEST_NO_AUTH"],
                "trash_dir": ["CLEANMAC_TEST_TRASH_DIR"],
            },
            "deep_system_cleanup_categories": [
                "xcode",
                "deviceFirmware",
                "androidStudio",
                "jetbrains",
                "vscode",
                "docker",
                "unity",
                "unreal",
                "godot",
                "appleSiliconCaches",
                "systemCaches",
                "systemDiagnostics",
                "macosInstallers",
                "systemUpdates",
                "browserCodeSignCache",
                "gpuCaches",
            ],
            "dynamic_provider_categories": [category.key for category in CATEGORIES if category.provider],
            "system_deep_clean_categories": [
                category.key for category in CATEGORIES if category.requires_privilege and category.advanced
            ],
            "active_process_skip_categories": [category.key for category in CATEGORIES if category.process_guard],
            "active_file_skip_categories": [category.key for category in CATEGORIES if category.active_file_check],
            "private_path_allowlist_enabled": True,
            "symlink_target_validation_enabled": True,
        },
        "boundary_governance": render_boundary_governance(),
    }


def render_doctor(*, root: Path, home: Path) -> dict[str, Any]:
    imessage_path = Path(remap_path("~/Library/Messages/Attachments/", root=root, home=home))
    live_root = root == Path("/")
    return {
        "schema": "cleanmac.doctor.v1",
        "destructive": False,
        "platform": sys.platform,
        "python": sys.version.split()[0],
        "executable": display_path(sys.executable),
        "root": display_path(root),
        "home": display_path(home),
        "checks": {
            "full_disk_access": {
                "status": "check-manually" if sys.platform == "darwin" else "not-darwin",
                "path": display_path(imessage_path),
                "message": "iMessage attachments may require Full Disk Access on macOS.",
            },
            "live_root_execution": {
                "status": "blocked-by-default" if live_root else "sandbox-root-configured",
                "message": "clean --execute refuses --root / unless --allow-live-root is explicitly passed.",
            },
            "path_alias_normalization": {
                "status": "enabled" if sys.platform == "darwin" else "not-needed",
                "message": "macOS /private/var paths are displayed as /var and accepted as equivalent plan context paths.",
            },
            "dry_run_default": {
                "status": "enabled",
                "message": "clean defaults to dry-run; deletion requires clean --execute.",
            },
            "private_path_policy": {
                "status": "enabled",
                "message": "Deletion under /private is limited to explicit temporary, log, cache, and diagnostic allowlists.",
            },
            "lsof_available": {
                "status": "available" if shutil.which("lsof") else "missing",
                "message": "lsof is used to skip active incomplete downloads when available.",
            },
            "getconf_available": {
                "status": "available" if shutil.which("getconf") else "missing",
                "message": "getconf is used to locate DARWIN_USER_TEMP_DIR and DARWIN_USER_CACHE_DIR on live macOS.",
            },
            "sudo_noninteractive": {
                "status": "available"
                if run_text_command(["sudo", "-n", "true"], timeout=1) is not None
                else "not-available-or-needs-auth",
                "message": "System categories may require sudo; doctor only checks sudo -n and never prompts for a password.",
            },
        },
    }


def path_size_bytes(path: Path) -> int:
    try:
        if not path.exists() and not path.is_symlink():
            return 0
        if path.is_symlink() or path.is_file():
            return path.lstat().st_size
        total = 0
        for current_root, dirs, files in os.walk(path, followlinks=False):
            current = Path(current_root)
            for name in list(dirs):
                child = current / name
                try:
                    total += child.lstat().st_size
                    if child.is_symlink():
                        dirs.remove(name)
                except OSError:
                    continue
            for name in files:
                try:
                    total += (current / name).lstat().st_size
                except OSError:
                    continue
        return total
    except OSError:
        return 0


def child_entries(path: Path) -> list[Path]:
    if not path.exists() and not path.is_symlink():
        return []
    if path.is_symlink() or path.is_file():
        return [path]
    try:
        return [path / name for name in os.listdir(path)]
    except OSError:
        return []


def inspect_entries(path: Path, *, recursive: bool) -> list[tuple[Path, int]]:
    direct = [(entry, 1) for entry in child_entries(path)]
    if not recursive:
        return direct
    rows = list(direct)
    for entry, _ in direct:
        if not entry.is_dir() or entry.is_symlink():
            continue
        base_depth = len(entry.parts)
        for current_root, dirs, files in os.walk(entry, followlinks=False):
            current = Path(current_root)
            depth = len(current.parts) - base_depth + 1
            for name in list(dirs):
                child = current / name
                rows.append((child, depth + 1))
                if child.is_symlink():
                    dirs.remove(name)
            for name in files:
                rows.append((current / name, depth + 1))
    return rows


def candidate_entries(target: ResolvedTarget, *, recursive: bool) -> list[tuple[Path, int]]:
    if target.delete_target:
        return [(target.path, 0)] if target.matched else []
    return inspect_entries(target.path, recursive=recursive)


def clean_candidate_entries(target: ResolvedTarget) -> list[Path]:
    if target.delete_target:
        return [target.path] if target.matched else []
    return child_entries(target.path)


def matches_exclude(path: Path, patterns: Sequence[str]) -> bool:
    return protection.matches_pattern(path, patterns)


def contains_protected_descendant(path: Path, patterns: Sequence[str]) -> bool:
    return protection.contains_protected_descendant(path, patterns)


def bundle_id_for_path(path: Path) -> str | None:
    return protection.bundle_id_for_path(path)


def bundle_id_for_app(app_path: Path) -> str | None:
    return protection.bundle_id_for_app(app_path)


def normalize_group_container_id(identifier: str) -> str | None:
    return protection.normalize_group_container_id(identifier)


def group_container_name_for_path(path: Path) -> str | None:
    return protection.group_container_name_for_path(path)


def is_group_container_cache_or_tmp_path(path: Path) -> bool:
    return protection.is_group_container_cache_or_tmp_path(path)


def is_protected_group_container_path(path: Path) -> bool:
    return protection.is_protected_group_container_path(path)


def official_uninstaller_vendor(
    *, bundle_id: str | None = None, name: str | None = None, app_path: Path | None = None
) -> str | None:
    return protection.official_uninstaller_vendor(bundle_id=bundle_id, name=name, app_path=app_path)


def should_protect_from_uninstall(bundle_id: str | None) -> bool:
    return protection.should_protect_from_uninstall(bundle_id)


def bundle_policy_reason(
    path: Path, *, bundle_allowlist: Sequence[str] = (), bundle_blocklist: Sequence[str] = ()
) -> str | None:
    return protection.bundle_policy_reason(
        bundle_id_for_path(path), bundle_allowlist=bundle_allowlist, bundle_blocklist=bundle_blocklist
    )


def matches_include(path: Path, patterns: Sequence[str]) -> bool:
    if not patterns:
        return True
    return protection.matches_pattern(path, patterns)


def effective_include_patterns(category: Category, include_patterns: Sequence[str]) -> tuple[str, ...]:
    return tuple(include_patterns) if include_patterns else category.default_include_patterns


def effective_exclude_patterns(category: Category, exclude_patterns: Sequence[str]) -> tuple[str, ...]:
    return tuple(exclude_patterns) + category.default_exclude_patterns


def effective_older_than_days(category: Category, older_than_days: float | None) -> float | None:
    return older_than_days if older_than_days is not None else category.default_older_than_days


def effective_min_size_mb(category: Category, min_size_mb: int) -> int:
    return min_size_mb if min_size_mb > 0 else category.default_min_size_mb


def matches_name_regex(path: Path, name_regex: str | None) -> bool:
    if not name_regex:
        return True
    try:
        return re.search(name_regex, path.name) is not None
    except re.error as exc:
        raise SystemExit(f"Invalid --name-regex: {exc}") from exc


def is_old_enough(path: Path, older_than_days: float | None) -> bool:
    if older_than_days is None:
        return True
    try:
        age_seconds = time.time() - path.lstat().st_mtime
    except OSError:
        return False
    return age_seconds >= max(older_than_days, 0) * 24 * 60 * 60


def is_process_running_exact(name: str) -> bool:
    if is_test_mode():
        return False
    return run_text_command(["pgrep", "-x", name]) is not None


def is_file_open(path: Path) -> bool:
    return run_text_command(["lsof", "-F", "n", "--", str(path)], timeout=2) is not None


def has_recent_file(path: Path, days: float) -> bool:
    cutoff = time.time() - max(days, 0) * 24 * 60 * 60
    if path.is_file():
        try:
            return path.lstat().st_mtime >= cutoff
        except OSError:
            return False
    if not path.is_dir() or path.is_symlink():
        return False
    for current_root, dirs, files in os.walk(path, followlinks=False):
        current = Path(current_root)
        for name in list(dirs):
            if (current / name).is_symlink():
                dirs.remove(name)
        for name in files:
            try:
                if (current / name).lstat().st_mtime >= cutoff:
                    return True
            except OSError:
                continue
    return False


def is_rebuildable_gpu_cache_path(path: Path, *, root: Path) -> bool:
    resolved = path.resolve(strict=False)
    base = provider_base(root, "/private/var/folders").resolve(strict=False)
    if path.name not in {"com.apple.gpuarchiver", "com.apple.metal", "com.apple.metalfe"}:
        return False
    if not is_relative_to(resolved, base):
        return False
    relative = resolved.relative_to(base)
    return len(relative.parts) >= 4 and relative.parts[2] == "C"


def is_browser_code_sign_cache_path(path: Path, *, root: Path) -> bool:
    resolved = path.resolve(strict=False)
    base = provider_base(root, "/private/var/folders").resolve(strict=False)
    if path.name.endswith(".code_sign_clone") is False:
        return False
    if not is_relative_to(resolved, base):
        return False
    relative = resolved.relative_to(base)
    return len(relative.parts) >= 4 and relative.parts[2] == "X"


def stat_flags(path: Path) -> str:
    try:
        return str(getattr(path.stat(), "st_flags", ""))
    except OSError:
        return ""


def macos_major_version() -> str | None:
    output = run_text_command(["sw_vers", "-productVersion"])
    if not output:
        return None
    return output.split(".", 1)[0]


def plist_platform_version_major(plist_path: Path) -> str | None:
    output = run_text_command(["/usr/libexec/PlistBuddy", "-c", "Print :DTPlatformVersion", str(plist_path)])
    if not output:
        return None
    return output.split(".", 1)[0]


def category_policy_reason(category: Category, path: Path, *, root: Path) -> str | None:
    if category.process_guard and is_process_running_exact(category.process_guard):
        return "app-running"
    if category.active_file_check and path.is_file() and is_file_open(path):
        return "active-file"
    if category.key in APP_CLEANUP_RULES:
        reason = protection.app_protected_data_reason(category.key, path)
        if reason:
            return reason
    container_reason = protection.container_policy_reason(category.key, path)
    if container_reason:
        return container_reason
    if category.key in {"darwinUserTemp", "darwinUserCache"}:
        kind = "temp" if category.key == "darwinUserTemp" else "cache"
        runtime_dir = path if path.is_dir() else path.parent
        if not is_safe_darwin_runtime_dir(runtime_dir, kind=kind, root=root):
            return "unsafe-runtime-dir"
        if path.is_symlink():
            return "symlink"
        owner = path_owner_uid(path)
        uid = current_uid()
        if uid is not None and owner is not None and owner != uid:
            return "owner-mismatch"
    if category.key == "gpuCaches":
        if not is_rebuildable_gpu_cache_path(path, root=root):
            return "outside-provider-allowlist"
        stale_days = category.stale_days if category.stale_days is not None else 1
        if has_recent_file(path, stale_days):
            return "not-stale"
    if category.key == "browserCodeSignCache" and not is_browser_code_sign_cache_path(path, root=root):
        return "outside-provider-allowlist"
    if category.key == "systemUpdates" and "restricted" in stat_flags(path):
        return "restricted"
    if category.key == "macosInstallers":
        if path.name.startswith("Install macOS") and path.suffix == ".app":
            if is_process_running_exact(path.name):
                return "app-running"
            current_major = macos_major_version()
            installer_major = plist_platform_version_major(path / "Contents/Info.plist")
            if current_major and installer_major and current_major == installer_major:
                return "current-macos-installer"
    return None


def filter_reason(
    category: Category,
    path: Path,
    *,
    root: Path,
    include_patterns: Sequence[str],
    exclude_patterns: Sequence[str],
    older_than_days: float | None,
    name_regex: str | None,
    bundle_allowlist: Sequence[str] = (),
    bundle_blocklist: Sequence[str] = (),
) -> str | None:
    app_policy_reason = bundle_policy_reason(path, bundle_allowlist=bundle_allowlist, bundle_blocklist=bundle_blocklist)
    if app_policy_reason:
        return app_policy_reason
    policy_reason = category_policy_reason(category, path, root=root)
    if policy_reason:
        return policy_reason
    effective_include = effective_include_patterns(category, include_patterns)
    effective_exclude = effective_exclude_patterns(category, exclude_patterns)
    effective_age = effective_older_than_days(category, older_than_days)
    if effective_include and not matches_include(path, effective_include):
        return "not-included"
    if not matches_name_regex(path, name_regex):
        return "name-regex-mismatch"
    if effective_exclude and matches_exclude(path, effective_exclude):
        return "excluded"
    if not is_old_enough(path, effective_age):
        return "too-new"
    return None


def skipped_row(category: str, parent: Path, entry: Path, reason: str) -> dict[str, Any]:
    size = path_size_bytes(entry)
    return {
        "category": category,
        "parent": display_path(parent),
        "path": display_path(entry),
        "reason": reason,
        "bytes": size,
        "human": human_size(size),
    }


def skipped_summary(skipped: Sequence[dict[str, Any]]) -> dict[str, Any]:
    by_reason: dict[str, int] = {}
    total_bytes = 0
    for row in skipped:
        reason = str(row["reason"])
        by_reason[reason] = by_reason.get(reason, 0) + 1
        total_bytes += int(row.get("bytes", 0))
    return {"count": len(skipped), "bytes": total_bytes, "human": human_size(total_bytes), "by_reason": by_reason}


def rows_by_category(rows: Sequence[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    output: dict[str, dict[str, Any]] = {}
    for row in rows:
        key = str(row["category"])
        current = output.setdefault(key, {"count": 0, "bytes": 0, "human": human_size(0)})
        current["count"] = int(current["count"]) + 1
        current["bytes"] = int(current["bytes"]) + int(row.get("bytes", 0))
        current["human"] = human_size(int(current["bytes"]))
    return output


def inspect_items(
    categories: list[Category],
    *,
    root: Path,
    home: Path,
    limit: int,
    recursive: bool = False,
    min_size_mb: int = 0,
    sort: str = "size-desc",
    include_patterns: Sequence[str] = (),
    exclude_patterns: Sequence[str] = (),
    older_than_days: float | None = None,
    name_regex: str | None = None,
    max_delete_mb: float | None = None,
    max_items: int | None = None,
    bundle_allowlist: Sequence[str] = (),
    bundle_blocklist: Sequence[str] = (),
) -> dict[str, Any]:
    rows = []
    skipped = []
    for target in resolve_targets(categories, root=root, home=home):
        category = CATEGORY_BY_KEY[target.category]
        min_size_bytes = max(effective_min_size_mb(category, min_size_mb), 0) * 1024 * 1024
        for entry, depth in candidate_entries(target, recursive=recursive):
            reason = filter_reason(
                category,
                entry,
                root=root,
                include_patterns=include_patterns,
                exclude_patterns=exclude_patterns,
                older_than_days=older_than_days,
                name_regex=name_regex,
                bundle_allowlist=bundle_allowlist,
                bundle_blocklist=bundle_blocklist,
            )
            if reason:
                skipped.append(skipped_row(target.category, target.path, entry, reason))
                continue
            size = path_size_bytes(entry)
            if size < min_size_bytes:
                skipped.append(skipped_row(target.category, target.path, entry, "below-min-size"))
                continue
            rows.append(
                {
                    "category": target.category,
                    "parent": display_path(target.path),
                    "path": display_path(entry),
                    "depth": depth,
                    "bytes": size,
                    "human": human_size(size),
                }
            )
    if sort == "size-asc":
        rows.sort(key=lambda row: (row_bytes(row), str(row["path"])))
    elif sort == "path":
        rows.sort(key=lambda row: str(row["path"]))
    else:
        rows.sort(key=lambda row: (row_bytes(row), str(row["path"])), reverse=True)
    total_candidates = len(rows)
    total_bytes = sum(row_bytes(row) for row in rows)
    max_delete_bytes = None if max_delete_mb is None else int(max_delete_mb * 1024 * 1024)
    budget_summary = {
        "candidate_count": total_candidates,
        "candidate_bytes": total_bytes,
        "candidate_human": human_size(total_bytes),
        "max_items": max_items,
        "within_max_items": max_items is None or total_candidates <= max_items,
        "max_delete_mb": max_delete_mb,
        "max_delete_bytes": max_delete_bytes,
        "within_max_delete_budget": max_delete_bytes is None or total_bytes <= max_delete_bytes,
        "applies_to_execute": False,
        "message": "inspect is non-destructive; use plan or clean to enforce these budgets before deletion.",
    }
    shown_rows = rows if limit < 0 else rows[:limit]
    return {
        "schema": "cleanmac.inspect.v1",
        "destructive": False,
        "dry_run": True,
        "total_candidates": total_candidates,
        "shown_candidates": len(shown_rows),
        "total_bytes": total_bytes,
        "total_human": human_size(total_bytes),
        "recursive": recursive,
        "min_size_mb": min_size_mb,
        "effective_category_defaults": {
            category.key: {
                "older_than_days": effective_older_than_days(category, older_than_days),
                "min_size_mb": effective_min_size_mb(category, min_size_mb),
                "include_patterns": list(effective_include_patterns(category, include_patterns)),
                "exclude_patterns": list(effective_exclude_patterns(category, exclude_patterns)),
            }
            for category in categories
        },
        "sort": sort,
        "include_patterns": list(include_patterns),
        "exclude_patterns": list(exclude_patterns),
        "older_than_days": older_than_days,
        "name_regex": name_regex,
        "bundle_allowlist": list(bundle_allowlist),
        "bundle_blocklist": list(bundle_blocklist),
        "max_delete_mb": max_delete_mb,
        "max_items": max_items,
        "budget_summary": budget_summary,
        "by_category": rows_by_category(shown_rows),
        "skipped_by_category": rows_by_category(skipped),
        "skipped_count": len(skipped),
        "skipped_summary": skipped_summary(skipped),
        "skipped": skipped,
        "items": shown_rows,
    }


def remap_home(*, root: Path, home: Path) -> Path:
    return home if root == Path("/") else root / str(home).lstrip("/")


def is_relative_to(path: Path, base: Path) -> bool:
    try:
        path.relative_to(base)
        return True
    except ValueError:
        return False


def normalize_policy_path(path: Path) -> str:
    text = str(path).replace("//", "/")
    while "//" in text:
        text = text.replace("//", "/")
    return text.rstrip("/") or text


def has_path_traversal(path: Path) -> bool:
    return any(part == ".." for part in path.parts)


def has_control_characters(path: Path) -> bool:
    return any(ord(char) < 32 or ord(char) == 127 for char in str(path))


def is_critical_deletion_path(path: Path) -> bool:
    return protection.is_critical_system_component(Path(normalize_policy_path(path)))


def is_private_allowlisted_path(path: Path) -> bool:
    text = normalize_policy_path(path)
    allow_exact = {
        "/private/tmp",
        "/private/var/tmp",
        "/private/var/log",
        "/private/var/folders",
        "/private/var/db/diagnostics",
        "/private/var/db/DiagnosticPipeline",
        "/private/var/db/powerlog",
        "/private/var/db/reportmemoryexception",
        "/private/var/db/oah",
        "/private/var/db/DetachedSignatures",
    }
    allow_prefixes = tuple(item + "/" for item in allow_exact)
    return text in allow_exact or text.startswith(allow_prefixes)


def is_protected_user_data_path(path: Path) -> bool:
    parts = path.parts
    if len(parts) < 3 or parts[1] != "Users":
        return False
    return protection.is_protected_user_data_path(Path(normalize_policy_path(path)))


def delete_policy_for_context(*, root: Path, home: Path) -> delete_ops.DeletePolicy:
    return delete_ops.DeletePolicy(
        root=root,
        home_root=remap_home(root=root, home=home),
        critical_path=is_critical_deletion_path,
        private_allowlist=is_private_allowlisted_path,
        protected_user_data=is_protected_user_data_path,
        normalize_policy_path=normalize_policy_path,
    )


def assert_safe_to_delete(target: Path, *, root: Path, home: Path) -> None:
    delete_ops.assert_safe_to_delete(target, policy=delete_policy_for_context(root=root, home=home))


def delete_path(path: Path, *, root: Path, home: Path, delete_mode: str) -> Path | None:
    trash_root = trash_root_for_context(root=root, home=home) if delete_mode == "trash" else None
    return delete_ops.delete_path(
        path,
        policy=delete_policy_for_context(root=root, home=home),
        delete_mode=delete_mode,
        trash_root=trash_root,
    )


def remove_path(path: Path, *, root: Path, home: Path) -> None:
    delete_path(path, root=root, home=home, delete_mode="permanent")


def trash_root_for_context(*, root: Path, home: Path) -> Path:
    test_trash = os.environ.get("CLEANMAC_TEST_TRASH_DIR")
    if test_trash:
        return Path(test_trash)
    return Path(remap_path("~/.Trash/", root=root, home=home))


def unique_trash_path(path: Path, *, root: Path, home: Path) -> Path:
    return delete_ops.unique_trash_path(path, trash_root=trash_root_for_context(root=root, home=home))


def route_path_to_trash(path: Path, *, root: Path, home: Path) -> Path:
    trash_path = delete_path(path, root=root, home=home, delete_mode="trash")
    if trash_path is None:
        raise RuntimeError(f"Trash routing did not return a destination for: {path}")
    return trash_path


def deletion_log_path_for_context(*, root: Path, home: Path) -> Path:
    return log_path_for_context(DELETE_LOG_FILE, root=root, home=home)


def append_deletion_log(
    *,
    root: Path,
    home: Path,
    mode: str,
    status: str,
    path: Path | str,
    bytes_value: int | str | None,
    detail: str = "",
) -> str:
    log_path = deletion_log_path_for_context(root=root, home=home)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    size_text = "unknown" if bytes_value is None else str(bytes_value)
    line = "\t".join(
        [datetime.now(timezone.utc).isoformat(), mode, size_text, status, str(path), detail.replace("\t", " ")]
    )
    with log_path.open("a", encoding="utf-8") as handle:
        handle.write(line + "\n")
    return display_path(log_path)


def log_path_for_context(path: str, *, root: Path, home: Path) -> Path:
    if path.startswith("~/") or path == "~":
        return Path(remap_path(path, root=root, home=home)).resolve(strict=False)
    return Path(path).expanduser().resolve(strict=False)


def operation_log_path_for_context(path: str, *, root: Path, home: Path) -> Path:
    if path.startswith("~/") or path == "~":
        return Path(remap_path(path, root=root, home=home)).expanduser()
    return Path(path).expanduser()


def rotate_log_once(path: Path, *, max_bytes: int) -> bool:
    if max_bytes <= 0 or not path.exists() or path.stat().st_size <= max_bytes:
        return False
    rotated = path.with_name(f"{path.name}.1")
    delete_ops.remove_path_permanently(rotated)
    path.rename(rotated)
    return True


def preflight_operation_log(path: str, *, root: Path, home: Path) -> dict[str, Any]:
    log_path = operation_log_path_for_context(path, root=root, home=home)
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
        rotated = rotate_log_once(log_path, max_bytes=OPERATIONS_LOG_ROTATE_BYTES)
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
    path: str, entries: Sequence[dict[str, Any]], *, root: Path, home: Path, rotate: bool = True
) -> str:
    log_path = operation_log_path_for_context(path, root=root, home=home)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    if rotate:
        rotate_log_once(log_path, max_bytes=OPERATIONS_LOG_ROTATE_BYTES)
    with log_path.open("a", encoding="utf-8") as handle:
        for entry in entries:
            handle.write(json.dumps(entry, ensure_ascii=False, sort_keys=True) + "\n")
    return display_path(log_path)


def debug_enabled() -> bool:
    return os.environ.get("CLEANMAC_DEBUG") == "1"


def append_debug_log(message: str, *, root: Path, home: Path) -> str | None:
    if not debug_enabled():
        return None
    log_path = log_path_for_context(DEBUG_SESSION_LOG_FILE, root=root, home=home)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    rotate_log_once(log_path, max_bytes=LOG_ROTATE_BYTES)
    with log_path.open("a", encoding="utf-8") as handle:
        handle.write(f"{datetime.now(timezone.utc).isoformat()}\t{message}\n")
    return display_path(log_path)


def debug_timer_start(label: str, *, root: Path, home: Path) -> float:
    start = time.perf_counter()
    append_debug_log(f"START\t{label}", root=root, home=home)
    return start


def debug_timer_end(label: str, start: float, *, root: Path, home: Path) -> float:
    elapsed_ms = (time.perf_counter() - start) * 1000
    append_debug_log(f"PERF\t{label}\t{elapsed_ms:.3f}ms", root=root, home=home)
    return elapsed_ms


def analyze(categories: list[Category], *, root: Path, home: Path) -> dict[str, Any]:
    targets = resolve_targets(categories, root=root, home=home)
    category_sizes = {category.key: 0 for category in categories}
    target_rows = []
    for target in targets:
        size = path_size_bytes(target.path)
        category_sizes[target.category] += size
        target_rows.append(
            {
                "category": target.category,
                "source_pattern": target.source_pattern,
                "path": display_path(target.path),
                "exists": target.matched,
                "bytes": size,
                "human": human_size(size),
            }
        )
    total = sum(category_sizes.values())
    return {
        "schema": "cleanmac.analyze.v1",
        "destructive": False,
        "dry_run": True,
        "total_bytes": total,
        "total_human": human_size(total),
        "categories": [
            {
                **category_metadata(category),
                "bytes": category_sizes[category.key],
                "human": human_size(category_sizes[category.key]),
            }
            for category in categories
        ],
        "targets": target_rows,
    }


def analyze_tree(path: Path, *, root: Path, home: Path, depth: int, top: int, min_size_mb: int) -> dict[str, Any]:
    scan_root = (
        Path(remap_path(str(path), root=root, home=home))
        if not path.is_absolute()
        else (path if root == Path("/") else root / str(path).lstrip("/"))
    )
    scan_root = scan_root.expanduser().resolve(strict=False)
    max_depth = max(depth, 0)
    min_bytes = max(min_size_mb, 0) * 1024 * 1024
    rows = []
    if scan_root.exists():
        base_depth = len(scan_root.parts)
        for current_root, dirs, files in os.walk(scan_root, followlinks=False):
            current = Path(current_root)
            current_depth = len(current.parts) - base_depth
            if current_depth > max_depth:
                dirs[:] = []
                continue
            for name in list(dirs):
                child = current / name
                if child.is_symlink():
                    dirs.remove(name)
                    continue
                size = path_size_bytes(child)
                if size >= min_bytes:
                    rows.append(
                        {
                            "path": display_path(child),
                            "name": child.name,
                            "type": "directory",
                            "depth": current_depth + 1,
                            "bytes": size,
                            "human": human_size(size),
                        }
                    )
            for name in files:
                child = current / name
                size = path_size_bytes(child)
                if size >= min_bytes:
                    rows.append(
                        {
                            "path": display_path(child),
                            "name": child.name,
                            "type": "file",
                            "depth": current_depth + 1,
                            "bytes": size,
                            "human": human_size(size),
                        }
                    )
    rows.sort(key=lambda row: (row_bytes(row), str(row["path"])), reverse=True)
    shown = rows[: max(top, 0)]
    other_bytes = sum(row_bytes(row) for row in rows[max(top, 0) :])
    return {
        "schema": "cleanmac.analyze-tree.v1",
        "destructive": False,
        "path": display_path(scan_root),
        "exists": scan_root.exists(),
        "depth": max_depth,
        "top": top,
        "min_size_mb": min_size_mb,
        "total_entries": len(rows),
        "shown_entries": len(shown),
        "other_bytes": other_bytes,
        "other_human": human_size(other_bytes),
        "entries": shown,
    }


def render_software(action: str, *, app: str | None, root: Path, home: Path) -> dict[str, Any]:
    app_dirs = [provider_base(root, "/Applications"), remap_home(root=root, home=home) / "Applications"]
    apps: list[dict[str, Any]] = []
    for app_dir in app_dirs:
        if app_dir.exists():
            for path in sorted(app_dir.glob("*.app")):
                bundle_id = bundle_id_for_app(path)
                apps.append(
                    {
                        "name": path.name,
                        "path": display_path(path),
                        "source": "unknown",
                        "bundle": path.suffix == ".app",
                        "bundle_id": bundle_id,
                        "protected_from_uninstall": should_protect_from_uninstall(bundle_id),
                        "official_uninstaller_vendor": official_uninstaller_vendor(
                            bundle_id=bundle_id, name=path.stem, app_path=path
                        ),
                    }
                )
    startup_locations = [
        "~/Library/LaunchAgents/",
        "/Library/LaunchAgents/",
        "/Library/LaunchDaemons/",
        "~/Library/StartupItems/",
        "/Library/StartupItems/",
    ]
    uninstall_targets = [
        "~/Library/Preferences/<bundle-id>.plist",
        "~/Library/Application Support/<app>",
        "~/Library/Caches/<bundle-id>",
        "~/Library/LaunchAgents/<bundle-id>.plist",
        "/Library/Receipts/<package-id>.*",
    ]
    return {
        "schema": "cleanmac.software.v1",
        "action": action,
        "destructive": False,
        "status": "read-only-planning",
        "app": app,
        "apps": apps if action == "list" else [],
        "startup_locations": startup_locations if action == "startup-items" else [],
        "leftover_scan_roots": uninstall_targets if action in {"leftovers", "uninstall-plan"} else [],
        "uninstall_plan": {
            "app": app,
            "requires_explicit_future_execute": True,
            "official_uninstaller_vendor": official_uninstaller_vendor(name=app) if app else None,
            "official_uninstaller_required": official_uninstaller_vendor(name=app) is not None if app else False,
            "official_uninstaller_message": (
                f"Use the official {official_uninstaller_vendor(name=app)} uninstaller; generic deletion is intentionally not planned."
                if app and official_uninstaller_vendor(name=app)
                else None
            ),
            "candidate_patterns": uninstall_targets,
            "protected_data_policy": "preserve app data unless user explicitly chooses a future destructive uninstall flow",
        }
        if action == "uninstall-plan"
        else None,
    }


def optimize_tasks() -> list[dict[str, Any]]:
    return [
        {
            "key": "quicklook-cache",
            "title": "Quick Look cache refresh",
            "command": "qlmanage -r cache",
            "requires_privilege": False,
            "destructive": False,
        },
        {
            "key": "launchservices-metadata",
            "title": "LaunchServices metadata rebuild",
            "command": "lsregister rebuild",
            "requires_privilege": False,
            "destructive": False,
        },
        {
            "key": "spotlight-review",
            "title": "Spotlight index status review",
            "command": "mdutil -s /",
            "requires_privilege": False,
            "destructive": False,
        },
    ]


def render_optimize(action: str, *, execute: bool) -> dict[str, Any]:
    tasks = optimize_tasks()
    return {
        "schema": "cleanmac.optimize.v1",
        "action": action,
        "destructive": False,
        "dry_run": True,
        "execute_requested": execute,
        "execution_supported": False,
        "message": "Optimize commands are currently exposed as a dry-run task plan only.",
        "tasks": tasks,
    }


def render_status_snapshot(*, root: Path) -> dict[str, Any]:
    disk = shutil.disk_usage(root if root.exists() else Path("/"))
    loadavg = os.getloadavg() if hasattr(os, "getloadavg") else (None, None, None)
    return {
        "schema": "cleanmac.status.snapshot.v1",
        "destructive": False,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "load_average": {"1m": loadavg[0], "5m": loadavg[1], "15m": loadavg[2]},
        "disk": {
            "path": display_path(root),
            "total_bytes": disk.total,
            "used_bytes": disk.used,
            "free_bytes": disk.free,
            "total_human": human_size(disk.total),
            "used_human": human_size(disk.used),
            "free_human": human_size(disk.free),
        },
        "metrics_available": ["load_average", "disk"],
        "metrics_deferred": ["gpu", "network", "battery", "temperature", "fan", "processes"],
    }


def advanced_options_report(categories: Sequence[Category]) -> dict[str, Any]:
    advanced = [category for category in categories if category.advanced]
    return {
        "selected_advanced_keys": [category.key for category in advanced],
        "selected_advanced_count": len(advanced),
        "requires_extra_review": bool(advanced),
    }


def diagnose(
    categories: list[Category], *, root: Path, home: Path, log_threshold_mb: int, large_threshold_mb: int
) -> dict[str, Any]:
    analysis = analyze(categories, root=root, home=home)
    category_rows = analysis["categories"]
    issues = []
    recommended_clean = []
    caution_clean = []
    skipped_or_empty = []
    log_threshold = log_threshold_mb * 1024 * 1024
    large_threshold = large_threshold_mb * 1024 * 1024
    for row in category_rows:  # type: ignore[assignment]
        key = str(row["key"])
        size = int(row["bytes"])
        if size <= 0:
            skipped_or_empty.append(key)
        if key in LOG_CATEGORY_KEYS and size > 0 and size >= log_threshold:
            issues.append(
                {
                    "severity": "warning",
                    "code": "large-logs-may-indicate-problem",
                    "category": key,
                    "message": f"{key} is {human_size(size)}. Inspect unusually large logs before deleting them.",
                }
            )
            caution_clean.append(key)
        elif key in CACHE_CATEGORY_KEYS and size > 0 and size >= large_threshold:
            issues.append(
                {
                    "severity": "info",
                    "code": "large-cache-will-regenerate",
                    "category": key,
                    "message": f"{key} is {human_size(size)}. Caches are usually regenerated after deletion.",
                }
            )
            caution_clean.append(key)
        elif row["recommended"] and size > 0:
            recommended_clean.append(key)
        elif row["risk"] in {"high", "critical"} and size > 0:
            caution_clean.append(key)
        if row["full_disk_access"]:
            issues.append(
                {
                    "severity": "info",
                    "code": "full-disk-access-needed",
                    "category": key,
                    "message": "This category may require Full Disk Access on macOS.",
                }
            )
        if row["requires_privilege"]:
            issues.append(
                {
                    "severity": "info",
                    "code": "may-require-privilege",
                    "category": key,
                    "message": "This category may require elevated permissions depending on filesystem ownership.",
                }
            )
    return {
        "schema": "cleanmac.diagnose.v1",
        "destructive": False,
        "dry_run": True,
        "total_bytes": analysis["total_bytes"],
        "total_human": analysis["total_human"],
        "categories": category_rows,
        "issues": issues,
        "advanced_options": advanced_options_report(categories),
        "recommended_clean_categories": recommended_clean,
        "caution_clean_categories": sorted(set(caution_clean)),
        "empty_or_missing_categories": skipped_or_empty,
        "suggested_safe_command": build_clean_command(recommended_clean, execute=False),
        "suggested_safe_execute_command": build_clean_command(recommended_clean, execute=True),
    }


def disk_free_bytes(path: Path) -> int | None:
    try:
        usage_path = path if path.exists() else path.parent
        while not usage_path.exists() and usage_path != usage_path.parent:
            usage_path = usage_path.parent
        return shutil.disk_usage(usage_path).free
    except OSError:
        return None


def summarize_risks(categories: Sequence[Category]) -> dict[str, int]:
    summary = {"low": 0, "medium": 0, "high": 0, "critical": 0}
    for category in categories:
        summary[category.risk] = summary.get(category.risk, 0) + 1
    return summary


def category_bytes_by_key(category_rows: Sequence[dict[str, Any]]) -> dict[str, int]:
    return {str(row["key"]): int(row["bytes"]) for row in category_rows}


def candidate_counts_by_category(candidate_rows: Sequence[dict[str, Any]]) -> dict[str, int]:
    counts = {category.key: 0 for category in CATEGORIES}
    for row in candidate_rows:
        key = str(row["category"])
        counts[key] = counts.get(key, 0) + 1
    return counts


def command_group_inventory() -> dict[str, Any]:
    return {key: {**value, "key": key} for key, value in COMMAND_GROUPS.items()}


def command_template(
    template_id: str,
    argv: Sequence[str],
    *,
    destructive: bool,
    safe_to_auto_execute: bool,
    manual_review_required: bool = False,
    placeholders: Sequence[str] = (),
) -> dict[str, Any]:
    placeholder_list = list(placeholders)
    return {
        "id": template_id,
        "kind": "argv",
        "command": shell_quote_command(argv),
        "argv": list(argv),
        "placeholders": placeholder_list,
        "uses_shell": False,
        "destructive": destructive,
        "safe_to_auto_execute": safe_to_auto_execute,
        "manual_review_required": manual_review_required,
        "execution_policy": {
            "uses_shell": False,
            "destructive": destructive,
            "safe_to_auto_execute": safe_to_auto_execute,
            "manual_review_required": manual_review_required,
            "requires_placeholder_substitution": bool(placeholder_list),
        },
    }


def shell_template(
    template_id: str,
    command: str,
    *,
    destructive: bool,
    safe_to_auto_execute: bool,
    manual_review_required: bool = False,
    placeholders: Sequence[str] = (),
) -> dict[str, Any]:
    placeholder_list = list(placeholders)
    return {
        "id": template_id,
        "kind": "shell",
        "command": command,
        "argv": ["/bin/sh", "-c", command],
        "placeholders": placeholder_list,
        "uses_shell": True,
        "destructive": destructive,
        "safe_to_auto_execute": safe_to_auto_execute,
        "manual_review_required": manual_review_required,
        "execution_policy": {
            "uses_shell": True,
            "destructive": destructive,
            "safe_to_auto_execute": safe_to_auto_execute,
            "manual_review_required": manual_review_required,
            "requires_placeholder_substitution": bool(placeholder_list),
        },
    }


def non_clean_script_groups() -> dict[str, Any]:
    software_templates = [
        command_template(
            "software-list",
            ["python3", "cleanmac.py", "--json", "software", "list"],
            destructive=False,
            safe_to_auto_execute=True,
        ),
        command_template(
            "software-startup-items",
            ["python3", "cleanmac.py", "--json", "software", "startup-items"],
            destructive=False,
            safe_to_auto_execute=True,
        ),
        command_template(
            "software-uninstall-plan",
            ["python3", "cleanmac.py", "--json", "software", "uninstall-plan", "--app", "<AppName>"],
            destructive=False,
            safe_to_auto_execute=True,
            placeholders=["AppName"],
        ),
    ]
    optimize_templates = [
        command_template(
            "optimize-list",
            ["python3", "cleanmac.py", "--json", "optimize", "list"],
            destructive=False,
            safe_to_auto_execute=True,
        ),
        command_template(
            "optimize-plan",
            ["python3", "cleanmac.py", "--json", "optimize", "plan"],
            destructive=False,
            safe_to_auto_execute=True,
        ),
        command_template(
            "optimize-run",
            ["python3", "cleanmac.py", "--json", "optimize", "run"],
            destructive=False,
            safe_to_auto_execute=True,
        ),
    ]
    analyze_templates = [
        command_template(
            "analyze-categories-all",
            ["python3", "cleanmac.py", "--json", "analyze", "categories", "--all"],
            destructive=False,
            safe_to_auto_execute=True,
        ),
        command_template(
            "analyze-scan-home",
            ["python3", "cleanmac.py", "--json", "analyze", "scan", "--path", "~", "--depth", "2", "--top", "20"],
            destructive=False,
            safe_to_auto_execute=True,
        ),
        command_template(
            "analyze-tree-library",
            [
                "python3",
                "cleanmac.py",
                "--json",
                "analyze",
                "tree",
                "--path",
                "~/Library",
                "--depth",
                "2",
                "--top",
                "20",
            ],
            destructive=False,
            safe_to_auto_execute=True,
        ),
    ]
    status_templates = [
        command_template(
            "status-snapshot",
            ["python3", "cleanmac.py", "--json", "status", "snapshot"],
            destructive=False,
            safe_to_auto_execute=True,
        )
    ]
    return {
        "software": {
            "safe_to_execute": True,
            "safe_to_auto_execute": True,
            "contains_destructive_templates": False,
            "destructive": False,
            "commands": [str(template["command"]) for template in software_templates],
            "command_templates": software_templates,
        },
        "optimize": {
            "safe_to_execute": True,
            "safe_to_auto_execute": True,
            "contains_destructive_templates": False,
            "destructive": False,
            "commands": [str(template["command"]) for template in optimize_templates],
            "command_templates": optimize_templates,
        },
        "analyze": {
            "safe_to_execute": True,
            "safe_to_auto_execute": True,
            "contains_destructive_templates": False,
            "destructive": False,
            "commands": [str(template["command"]) for template in analyze_templates],
            "command_templates": analyze_templates,
        },
        "status": {
            "safe_to_execute": True,
            "safe_to_auto_execute": True,
            "contains_destructive_templates": False,
            "destructive": False,
            "commands": [str(template["command"]) for template in status_templates],
            "command_templates": status_templates,
        },
    }


COMMAND_TEMPLATE_REQUIRED_FIELDS = [
    "id",
    "kind",
    "command",
    "argv",
    "placeholders",
    "uses_shell",
    "destructive",
    "safe_to_auto_execute",
    "manual_review_required",
    "execution_policy",
]


def command_template_contract() -> dict[str, Any]:
    return {
        "required_fields": COMMAND_TEMPLATE_REQUIRED_FIELDS,
        "kind_values": ["argv", "shell"],
        "destructive_rule": "destructive templates must set safe_to_auto_execute=false and manual_review_required=true",
        "destructive_delete_rule": "destructive cleanup/delete templates must be argv-only cleanmac CLI invocations using clean run, --delete-mode trash, --execute, and --yes",
        "placeholder_rule": "templates with placeholders must be substituted before execution",
    }


def is_cleanmac_clean_run_argv(argv: object) -> bool:
    if not isinstance(argv, list):
        return False
    parts = [str(part) for part in argv]
    try:
        clean_index = parts.index("clean")
    except ValueError:
        return False
    return clean_index > 0 and clean_index + 1 < len(parts) and parts[clean_index + 1] == "run"


def validate_destructive_cleanmac_template(location: str, template: dict[str, Any], add_violation: Any) -> None:
    argv = template["argv"]
    kind = template["kind"]
    uses_shell = bool(template["uses_shell"])
    if kind != "argv" or uses_shell:
        add_violation(
            location,
            template,
            "destructive-shell-template",
            "destructive cleanup templates must be argv-only and must not invoke a shell",
        )
    if not is_cleanmac_clean_run_argv(argv):
        add_violation(
            location,
            template,
            "destructive-not-cleanmac-cli",
            "destructive cleanup templates must invoke cleanmac clean run",
        )
        return
    parts = [str(part) for part in argv]
    if "--delete-mode" not in parts or parts[parts.index("--delete-mode") + 1 : parts.index("--delete-mode") + 2] != [
        "trash"
    ]:
        add_violation(
            location,
            template,
            "destructive-without-trash-mode",
            "destructive cleanup templates must route deletes through --delete-mode trash",
        )
    if "--execute" not in parts:
        add_violation(
            location, template, "destructive-without-execute", "destructive cleanup templates must be explicit"
        )
    if "--yes" not in parts:
        add_violation(
            location,
            template,
            "destructive-without-review-ack",
            "destructive cleanup templates must include --yes after manual review",
        )
    if "--categories" not in parts and "--plan-file" not in parts:
        add_violation(
            location,
            template,
            "destructive-without-scope",
            "destructive cleanup templates must be scoped by --categories or --plan-file",
        )


def validate_command_templates(groups: dict[str, Any], categories: Sequence[dict[str, Any]]) -> dict[str, Any]:
    required = set(COMMAND_TEMPLATE_REQUIRED_FIELDS)
    violations: list[dict[str, Any]] = []
    template_count = 0
    destructive_count = 0
    safe_to_auto_execute_count = 0
    seen_ids: set[str] = set()

    def add_violation(location: str, template: object, code: str, message: str) -> None:
        template_id = template.get("id") if isinstance(template, dict) else None
        violations.append({"location": location, "template_id": template_id, "code": code, "message": message})

    def validate_one(location: str, template: object) -> None:
        nonlocal template_count, destructive_count, safe_to_auto_execute_count
        template_count += 1
        if not isinstance(template, dict):
            add_violation(location, template, "template-not-object", "command template must be an object")
            return

        missing = sorted(required - set(template))
        if missing:
            add_violation(location, template, "missing-required-fields", ",".join(missing))
            return

        template_id = str(template["id"])
        if not template_id:
            add_violation(location, template, "empty-id", "template id must be non-empty")
        elif template_id in seen_ids:
            add_violation(location, template, "duplicate-id", f"duplicate template id {template_id}")
        seen_ids.add(template_id)

        kind = template["kind"]
        uses_shell = bool(template["uses_shell"])
        destructive = bool(template["destructive"])
        safe_to_auto_execute = bool(template["safe_to_auto_execute"])
        manual_review_required = bool(template["manual_review_required"])
        placeholders = template["placeholders"]
        policy = template["execution_policy"]
        argv = template["argv"]
        command = template["command"]

        if kind not in {"argv", "shell"}:
            add_violation(location, template, "invalid-kind", "kind must be argv or shell")
        if uses_shell != (kind == "shell"):
            add_violation(location, template, "kind-shell-mismatch", "uses_shell must match kind")
        if not isinstance(argv, list) or not argv:
            add_violation(location, template, "invalid-argv", "argv must be a non-empty list")
        if not isinstance(command, str) or not command:
            add_violation(location, template, "invalid-command", "command must be a non-empty string")
        if not isinstance(placeholders, list):
            add_violation(location, template, "invalid-placeholders", "placeholders must be a list")
        if not isinstance(policy, dict):
            add_violation(location, template, "invalid-execution-policy", "execution_policy must be an object")
            return

        for key in ("uses_shell", "destructive", "safe_to_auto_execute", "manual_review_required"):
            if policy.get(key) != template[key]:
                add_violation(
                    location, template, "policy-mismatch", f"execution_policy.{key} must mirror top-level {key}"
                )
        if policy.get("requires_placeholder_substitution") != bool(placeholders):
            add_violation(
                location,
                template,
                "placeholder-policy-mismatch",
                "requires_placeholder_substitution must match placeholders",
            )

        if destructive:
            destructive_count += 1
            if safe_to_auto_execute:
                add_violation(
                    location,
                    template,
                    "destructive-auto-execute",
                    "destructive templates cannot be safe_to_auto_execute",
                )
            if not manual_review_required:
                add_violation(
                    location, template, "destructive-without-review", "destructive templates must require manual review"
                )
            validate_destructive_cleanmac_template(location, template, add_violation)
        if isinstance(command, str) and "rm -rf" in command:
            deprecated = bool(template.get("deprecated"))
            replacement = template.get("replacement_template_id")
            if not (deprecated and manual_review_required and not safe_to_auto_execute and replacement):
                add_violation(
                    location,
                    template,
                    "raw-rm-forbidden",
                    "raw rm -rf templates must be deprecated and point to a cleanmac CLI replacement",
                )
        if safe_to_auto_execute:
            safe_to_auto_execute_count += 1

    for group_name, group in groups.items():
        if not isinstance(group, dict):
            continue
        for index, template in enumerate(group.get("command_templates", [])):
            validate_one(f"groups.{group_name}.command_templates[{index}]", template)

    for category_index, category in enumerate(categories):
        templates = category.get("command_templates", {})
        if not isinstance(templates, dict):
            add_violation(
                f"categories[{category_index}]",
                category,
                "missing-category-command-templates",
                "category must include command_templates",
            )
            continue
        for bucket in ("analyze", "delete"):
            for index, template in enumerate(templates.get(bucket, [])):
                validate_one(f"categories[{category_index}].command_templates.{bucket}[{index}]", template)

    return {
        "schema": "cleanmac.command-template-validation.v1",
        "valid": not violations,
        "template_count": template_count,
        "destructive_template_count": destructive_count,
        "safe_to_auto_execute_template_count": safe_to_auto_execute_count,
        "violation_count": len(violations),
        "violations": violations,
    }


def command_template_migration_report(groups: dict[str, Any], categories: Sequence[dict[str, Any]]) -> dict[str, Any]:
    templates: list[dict[str, Any]] = []

    for group in groups.values():
        if isinstance(group, dict):
            templates.extend(template for template in group.get("command_templates", []) if isinstance(template, dict))
    for category in categories:
        category_templates = category.get("command_templates", {})
        if isinstance(category_templates, dict):
            for bucket in ("analyze", "delete"):
                templates.extend(
                    template for template in category_templates.get(bucket, []) if isinstance(template, dict)
                )

    raw_remove_pattern = "rm " + "-rf"
    raw_rm_rf_templates = [template for template in templates if raw_remove_pattern in str(template.get("command", ""))]
    deprecated_templates = [template for template in templates if template.get("deprecated")]
    replacement_templates = [template for template in templates if template.get("replacement_template_id")]
    recommended_delete_templates = [
        template
        for category in categories
        for template in category.get("command_templates", {}).get("delete", [])
        if isinstance(template, dict)
    ]
    return {
        "schema": "cleanmac.command-template-migration.v1",
        "raw_rm_rf_template_count": len(raw_rm_rf_templates),
        "deprecated_template_count": len(deprecated_templates),
        "replacement_template_count": len(replacement_templates),
        "recommended_delete_template_count": len(recommended_delete_templates),
        "all_recommended_delete_templates_use_cleanmac_cli": all(
            is_cleanmac_clean_run_argv(template.get("argv"))
            and not template.get("uses_shell")
            and "--delete-mode" in [str(part) for part in template.get("argv", [])]
            and "trash" in [str(part) for part in template.get("argv", [])]
            for template in recommended_delete_templates
        ),
    }


def render_scripts(categories: list[Category], *, root: Path, home: Path, group: str = "all") -> dict[str, Any]:
    rows = []
    for category in categories:
        analyze_commands = [
            shell_quote_command(["du", "-smc", remap_path(path, root=root, home=home)])
            + " 2>/dev/null | sed -n '$s/\\t.*//p'"
            for path in category.paths
        ]
        delete_argv = [
            "python3",
            "cleanmac.py",
            "--root",
            str(root),
            "--home",
            str(home),
            "--json",
            "clean",
            "run",
            "--categories",
            category.key,
            "--delete-mode",
            "trash",
            "--execute",
            "--yes",
        ]
        delete_commands = [shell_quote_command(delete_argv)]
        analyze_templates = [
            shell_template(f"{category.key}-analyze-{index + 1}", command, destructive=False, safe_to_auto_execute=True)
            for index, command in enumerate(analyze_commands)
        ]
        delete_templates = [
            command_template(
                f"{category.key}-delete-reviewed-cli",
                delete_argv,
                destructive=True,
                safe_to_auto_execute=False,
                manual_review_required=True,
            )
        ]
        rows.append(
            {
                **category_metadata(category),
                "commands": {
                    "analyze": analyze_commands,
                    "delete": delete_commands,
                    "requires_privilege": category.requires_privilege,
                },
                "command_templates": {"analyze": analyze_templates, "delete": delete_templates},
            }
        )
    clean_templates = [
        command_template(
            "clean-inspect-selected",
            ["python3", "cleanmac.py", "--json", "clean", "inspect", "--categories", "<keys>"],
            destructive=False,
            safe_to_auto_execute=True,
            placeholders=["keys"],
        ),
        command_template(
            "clean-plan-selected",
            ["python3", "cleanmac.py", "--json", "clean", "plan", "--categories", "<keys>"],
            destructive=False,
            safe_to_auto_execute=True,
            placeholders=["keys"],
        ),
        command_template(
            "clean-run-reviewed-plan",
            [
                "python3",
                "cleanmac.py",
                "--json",
                "clean",
                "run",
                "--plan-file",
                "<plan.json>",
                "--require-plan-context",
                "--delete-mode",
                "trash",
                "--execute",
                "--yes",
            ],
            destructive=True,
            safe_to_auto_execute=False,
            manual_review_required=True,
            placeholders=["plan.json"],
        ),
    ]
    script_groups = {
        "clean": {
            "safe_to_execute": False,
            "safe_to_auto_execute": False,
            "contains_destructive_templates": True,
            "destructive": True,
            "manual_review_required": True,
            "categories": rows,
            "commands": [str(template["command"]) for template in clean_templates],
            "command_templates": clean_templates,
        },
        **non_clean_script_groups(),
    }
    selected_groups = script_groups if group == "all" else {group: script_groups[group]}
    template_validation = validate_command_templates(selected_groups, rows)
    template_migration = command_template_migration_report(selected_groups, rows)
    return {
        "schema": "cleanmac.scripts.v1",
        "destructive": False,
        "dry_run": True,
        "script_inventory": {
            "schema": "cleanmac.script-groups.v1",
            "selected_group": group,
            "command_template_contract": command_template_contract(),
            "shell_execution": {"launch_path": "/bin/sh", "arguments": ["-c", "<combined command>"]},
            "disk_free_before_after": {
                "model": "shutil.disk_usage(<root-or-existing-parent>).free before/after --execute"
            },
            "calculate_sizes": "du -smc <path> 2>/dev/null | sed -n '$s/\\t.*//p'",
            "delete_candidates": "python3 cleanmac.py --json clean run --categories <keys> --delete-mode trash --execute --yes",
            "deprecated_delete_examples": {
                "raw_rm_rf": "not recommended; raw rm -rf templates must be deprecated and require replacement_template_id"
            },
            "symbolic_links": {"logs_link_dir": LOG_LINK_DIR, "cache_link_dir": CACHE_LINK_DIR},
            "open_in_finder": {"command": "python3 cleanmac.py clean open --categories <keys>"},
            "boundary_governance": render_boundary_governance(),
        },
        "command_groups": command_group_inventory(),
        "groups": selected_groups,
        "categories": rows,
        "template_validation": template_validation,
        "template_migration": template_migration,
    }


def render_pre_clean_report(
    categories: list[Category],
    *,
    root: Path,
    home: Path,
    risk_policy: str = "default",
    include_patterns: Sequence[str] = (),
    exclude_patterns: Sequence[str] = (),
    older_than_days: float | None = None,
    min_size_mb: int = 0,
    name_regex: str | None = None,
    bundle_allowlist: Sequence[str] = (),
    bundle_blocklist: Sequence[str] = (),
) -> dict[str, Any]:
    analysis_report = analyze(categories, root=root, home=home)
    inspect_report = inspect_items(
        categories,
        root=root,
        home=home,
        limit=-1,
        min_size_mb=min_size_mb,
        include_patterns=include_patterns,
        exclude_patterns=exclude_patterns,
        older_than_days=older_than_days,
        name_regex=name_regex,
        bundle_allowlist=bundle_allowlist,
        bundle_blocklist=bundle_blocklist,
    )
    high_risk = selected_high_risk_categories(categories)
    yes_required = categories_requiring_yes(categories, risk_policy)
    candidate_counts = candidate_counts_by_category(inspect_report["items"])  # type: ignore[arg-type]
    return {
        "phase": "pre-clean",
        "summary": {
            "selected_category_count": len(categories),
            "candidate_count": inspect_report["total_candidates"],
            "estimated_reclaimable_bytes": analysis_report["total_bytes"],
            "estimated_reclaimable_human": analysis_report["total_human"],
            "risk_summary": summarize_risks(categories),
            "high_risk_categories": [category.key for category in high_risk],
            "risk_policy": risk_policy,
            "yes_required_categories": [category.key for category in yes_required],
            "requires_yes_for_execute": bool(yes_required),
            "include_patterns": list(include_patterns),
            "exclude_patterns": list(exclude_patterns),
            "older_than_days": older_than_days,
            "min_size_mb": min_size_mb,
            "name_regex": name_regex,
            "bundle_allowlist": list(bundle_allowlist),
            "bundle_blocklist": list(bundle_blocklist),
            "delete_semantics": "delete target contents; preserve parent directories",
        },
        "cleanup_flow": {
            "progress_messages": ["Cleaning...", "Finishing!", "Success!"],
            "symbolic_link_refresh": {
                "enabled_when_selected": any(
                    category.key in {"userAppLogs", "userAppCache"} for category in categories
                ),
                "logs_link_dir": LOG_LINK_DIR,
                "cache_link_dir": CACHE_LINK_DIR,
            },
            "advanced_options": advanced_options_report(categories),
        },
        "categories": analysis_report["categories"],
        "category_preview": [
            {
                "key": row["key"],
                "title": row["title"],
                "bytes": row["bytes"],
                "human": row["human"],
                "candidate_count": candidate_counts.get(str(row["key"]), 0),
                "risk": row["risk"],
            }
            for row in analysis_report["categories"]
        ],  # type: ignore[index]
        "targets": analysis_report["targets"],
        "candidates": inspect_report["items"],
        "candidate_total_bytes": inspect_report["total_bytes"],
        "candidate_total_human": inspect_report["total_human"],
        "action_scripts": render_scripts(categories, root=root, home=home),
    }


def render_post_clean_report(
    categories: list[Category],
    *,
    root: Path,
    home: Path,
    pre_report: dict[str, Any],
    deleted_items: list[dict[str, Any]],
    disk_free_before: int | None,
    disk_free_after: int | None,
) -> dict[str, Any]:
    after_analysis = analyze(categories, root=root, home=home)
    remaining_candidates = inspect_items(categories, root=root, home=home, limit=-1)
    pre_estimated = int(pre_report["summary"]["estimated_reclaimable_bytes"])  # type: ignore[index]
    remaining_estimated = int(after_analysis["total_bytes"])
    before_by_category = category_bytes_by_key(pre_report["categories"])  # type: ignore[arg-type]
    after_by_category = category_bytes_by_key(after_analysis["categories"])  # type: ignore[arg-type]
    deleted_bytes = sum(int(item["bytes"]) for item in deleted_items if item.get("deleted"))
    disk_delta = (
        None if disk_free_before is None or disk_free_after is None else max(disk_free_after - disk_free_before, 0)
    )
    return {
        "phase": "post-clean",
        "summary": {
            "deleted_item_count": sum(1 for item in deleted_items if item.get("deleted")),
            "deleted_bytes_from_candidates": deleted_bytes,
            "deleted_human_from_candidates": human_size(deleted_bytes),
            "estimated_reclaimed_bytes": max(pre_estimated - remaining_estimated, 0),
            "estimated_reclaimed_human": human_size(max(pre_estimated - remaining_estimated, 0)),
            "remaining_reclaimable_bytes": remaining_estimated,
            "remaining_reclaimable_human": after_analysis["total_human"],
            "disk_free_delta_bytes": disk_delta,
            "disk_free_delta_human": human_size(disk_delta) if disk_delta is not None else None,
        },
        "category_deltas": [
            {
                "key": category.key,
                "before_bytes": before_by_category.get(category.key, 0),
                "before_human": human_size(before_by_category.get(category.key, 0)),
                "after_bytes": after_by_category.get(category.key, 0),
                "after_human": human_size(after_by_category.get(category.key, 0)),
                "reclaimed_bytes": max(
                    before_by_category.get(category.key, 0) - after_by_category.get(category.key, 0), 0
                ),
                "reclaimed_human": human_size(
                    max(before_by_category.get(category.key, 0) - after_by_category.get(category.key, 0), 0)
                ),
            }
            for category in categories
        ],
        "target_preservation": [
            {
                "category": row["category"],
                "path": row["path"],
                "exists_after_clean": Path(str(row["path"])).exists(),
                "expected": "parent target is preserved; only contents are removed",
            }
            for row in pre_report["targets"]
        ],  # type: ignore[index]
        "categories": after_analysis["categories"],
        "targets": after_analysis["targets"],
        "remaining_candidates": remaining_candidates["items"],
    }


def clean(
    categories: list[Category],
    *,
    root: Path,
    home: Path,
    execute: bool,
    risk_policy: str = "default",
    max_delete_mb: float | None = None,
    plan_file: str | None = None,
    include_patterns: Sequence[str] = (),
    exclude_patterns: Sequence[str] = (),
    older_than_days: float | None = None,
    min_size_mb: int = 0,
    name_regex: str | None = None,
    max_items: int | None = None,
    fail_on_skipped: bool = False,
    bundle_allowlist: Sequence[str] = (),
    bundle_blocklist: Sequence[str] = (),
    delete_mode: str = "permanent",
    operation_log: str | None = OPERATIONS_LOG_FILE,
    command_argv: Sequence[str] = (),
) -> dict[str, Any]:
    timer_start = debug_timer_start("clean", root=root, home=home)
    session_id = datetime.now(timezone.utc).strftime("cleanmac-%Y%m%dT%H%M%S%fZ")
    pre_report = render_pre_clean_report(
        categories,
        root=root,
        home=home,
        risk_policy=risk_policy,
        include_patterns=include_patterns,
        exclude_patterns=exclude_patterns,
        older_than_days=older_than_days,
        min_size_mb=min_size_mb,
        name_regex=name_regex,
        bundle_allowlist=bundle_allowlist,
        bundle_blocklist=bundle_blocklist,
    )
    disk_free_before = disk_free_bytes(root)
    rows = []
    skipped = []
    for target in resolve_targets(categories, root=root, home=home):
        category = CATEGORY_BY_KEY[target.category]
        min_size_bytes = max(effective_min_size_mb(category, min_size_mb), 0) * 1024 * 1024
        for entry in clean_candidate_entries(target):
            assert_safe_to_delete(entry, root=root, home=home)
            reason = filter_reason(
                category,
                entry,
                root=root,
                include_patterns=include_patterns,
                exclude_patterns=exclude_patterns,
                older_than_days=older_than_days,
                name_regex=name_regex,
                bundle_allowlist=bundle_allowlist,
                bundle_blocklist=bundle_blocklist,
            )
            if reason:
                skipped_item = skipped_row(target.category, target.path, entry, reason)
                skipped.append(skipped_item)
                continue
            size = path_size_bytes(entry)
            if size < min_size_bytes:
                skipped_item = skipped_row(target.category, target.path, entry, "below-min-size")
                skipped.append(skipped_item)
                continue
            rows.append(
                {
                    "category": target.category,
                    "parent": display_path(target.path),
                    "path": display_path(entry),
                    "bytes": size,
                    "human": human_size(size),
                    "bundle_id": bundle_id_for_path(entry),
                    "delete_mode": delete_mode,
                    "trash_path": None,
                    "deleted": False,
                }
            )
    candidate_bytes = sum(row_bytes(row) for row in rows)
    max_delete_bytes = None if max_delete_mb is None else int(max_delete_mb * 1024 * 1024)
    safety_gate = {
        "risk_policy": risk_policy,
        "plan_file": plan_file,
        "max_delete_mb": max_delete_mb,
        "max_delete_bytes": max_delete_bytes,
        "candidate_bytes": candidate_bytes,
        "candidate_human": human_size(candidate_bytes),
        "within_delete_budget": max_delete_bytes is None or candidate_bytes <= max_delete_bytes,
        "fail_on_skipped": fail_on_skipped,
        "skipped_count": len(skipped),
        "max_items": max_items,
        "within_max_items": max_items is None or len(rows) <= max_items,
        "delete_mode": delete_mode,
        "operation_log": operation_log,
        "bundle_allowlist": list(bundle_allowlist),
        "bundle_blocklist": list(bundle_blocklist),
    }
    operation_log_entries: list[dict[str, Any]] = []
    command_text = shlex.join(["cleanmac.py", *command_argv]) if command_argv else "cleanmac.py clean run"
    if execute:
        for item in skipped:
            operation_log_entries.append(
                {
                    "schema": "cleanmac.operation-log-entry.v1",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "session_id": session_id,
                    "command": command_text,
                    "action": "skip",
                    "category": item["category"],
                    "path": item["path"],
                    "bytes": item["bytes"],
                    "human": item["human"],
                    "bundle_id": bundle_id_for_path(Path(str(item["path"]))),
                    "delete_mode": delete_mode,
                    "trash_path": None,
                    "deleted": False,
                    "status": "skipped",
                    "reason": item["reason"],
                    "root": display_path(root),
                    "home": display_path(home),
                }
            )
    if execute and fail_on_skipped and skipped:
        raise SystemExit(f"Refusing to execute cleanup because {len(skipped)} candidate(s) were skipped by filters.")
    if execute and max_items is not None and len(rows) > max_items:
        raise SystemExit(
            f"Refusing to execute cleanup because candidate count {len(rows)} exceeds --max-items budget {max_items}."
        )
    if execute and max_delete_bytes is not None and candidate_bytes > max_delete_bytes:
        raise SystemExit(
            f"Refusing to execute cleanup because candidate bytes exceed --max-delete-mb budget. Candidates: {human_size(candidate_bytes)}; budget: {human_size(max_delete_bytes)}"
        )
    operation_log_status = {
        "schema": "cleanmac.operation-log-status.v1",
        "status": "disabled" if not operation_log else "not-needed",
        "path": None,
        "rotated": False,
        "error": None,
    }
    if execute and operation_log and (operation_log_entries or rows):
        operation_log_status = preflight_operation_log(operation_log, root=root, home=home)
        if operation_log_status["status"] != "ready":
            raise SystemExit(
                f"Refusing to execute cleanup because operation log preflight failed: {operation_log_status['error']}"
            )
    if execute:
        for row in rows:
            path = Path(str(row["path"]))
            try:
                if delete_mode == "trash":
                    trash_path = delete_path(path, root=root, home=home, delete_mode="trash")
                    if trash_path is None:
                        raise RuntimeError(f"Trash routing did not return a destination for: {path}")
                    row["trash_path"] = display_path(trash_path)
                else:
                    delete_path(path, root=root, home=home, delete_mode="permanent")
                row["deleted"] = True
                row["status"] = "deleted"
                append_deletion_log(
                    root=root,
                    home=home,
                    mode=delete_mode,
                    status="deleted",
                    path=path,
                    bytes_value=int(str(row["bytes"])),
                    detail=str(row.get("trash_path") or ""),
                )
            except Exception as exc:
                row["deleted"] = False
                row["status"] = "failed"
                row["error"] = str(exc)
                append_deletion_log(
                    root=root,
                    home=home,
                    mode=delete_mode,
                    status="failed",
                    path=path,
                    bytes_value=int(str(row["bytes"])),
                    detail=str(exc),
                )
                raise
            operation_log_entries.append(
                {
                    "schema": "cleanmac.operation-log-entry.v1",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "session_id": session_id,
                    "command": command_text,
                    "action": "delete",
                    "category": row["category"],
                    "path": row["path"],
                    "bytes": row["bytes"],
                    "human": row["human"],
                    "bundle_id": row.get("bundle_id"),
                    "delete_mode": delete_mode,
                    "trash_path": row.get("trash_path"),
                    "deleted": True,
                    "status": row.get("status", "deleted"),
                    "root": display_path(root),
                    "home": display_path(home),
                }
            )
    elapsed_ms = debug_timer_end("clean", timer_start, root=root, home=home)
    operation_log_path = (
        append_operation_log(operation_log, operation_log_entries, root=root, home=home, rotate=False)
        if operation_log_entries and operation_log
        else None
    )
    disk_free_after = disk_free_bytes(root) if execute else None
    post_report = (
        render_post_clean_report(
            categories,
            root=root,
            home=home,
            pre_report=pre_report,
            deleted_items=rows,
            disk_free_before=disk_free_before,
            disk_free_after=disk_free_after,
        )
        if execute
        else None
    )
    return {
        "schema": "cleanmac.clean.v1",
        "destructive": execute,
        "dry_run": not execute,
        "risk_policy": risk_policy,
        "plan_file": plan_file,
        "max_delete_mb": max_delete_mb,
        "include_patterns": list(include_patterns),
        "exclude_patterns": list(exclude_patterns),
        "older_than_days": older_than_days,
        "min_size_mb": min_size_mb,
        "name_regex": name_regex,
        "max_items": max_items,
        "fail_on_skipped": fail_on_skipped,
        "bundle_allowlist": list(bundle_allowlist),
        "bundle_blocklist": list(bundle_blocklist),
        "delete_mode": delete_mode,
        "operation_log": operation_log_path,
        "operation_log_status": operation_log_status["status"],
        "operation_log_error": operation_log_status["error"],
        "operation_log_rotated": operation_log_status["rotated"],
        "operation_log_preflight": operation_log_status,
        "operation_log_entry_count": len(operation_log_entries),
        "operation_session_id": session_id,
        "debug_elapsed_ms": elapsed_ms,
        "deletion_log": display_path(deletion_log_path_for_context(root=root, home=home)) if execute else None,
        "safety_gate": safety_gate,
        "selected_categories": [category_metadata(category) for category in categories],
        "pre_clean_report": pre_report,
        "post_clean_report": post_report,
        "total_bytes": candidate_bytes,
        "total_human": human_size(candidate_bytes),
        "by_category": rows_by_category(rows),
        "skipped_by_category": rows_by_category(skipped),
        "skipped_count": len(skipped),
        "skipped_summary": skipped_summary(skipped),
        "skipped": skipped,
        "items": rows,
    }


def render_clean_plan(
    categories: list[Category],
    *,
    root: Path,
    home: Path,
    risk_policy: str,
    max_delete_mb: float | None,
    include_patterns: Sequence[str] = (),
    exclude_patterns: Sequence[str] = (),
    older_than_days: float | None = None,
    min_size_mb: int = 0,
    name_regex: str | None = None,
    max_items: int | None = None,
) -> dict[str, Any]:
    category_keys = [category.key for category in categories]
    pre_report = render_pre_clean_report(
        categories,
        root=root,
        home=home,
        risk_policy=risk_policy,
        include_patterns=include_patterns,
        exclude_patterns=exclude_patterns,
        older_than_days=older_than_days,
        min_size_mb=min_size_mb,
        name_regex=name_regex,
    )
    return {
        "schema": "cleanmac.plan.v1",
        "destructive": False,
        "dry_run": True,
        "categories": category_keys,
        "selected_category_keys": category_keys,
        "selected_categories": [category_metadata(category) for category in categories],
        "risk_policy": risk_policy,
        "max_delete_mb": max_delete_mb,
        "include_patterns": list(include_patterns),
        "exclude_patterns": list(exclude_patterns),
        "older_than_days": older_than_days,
        "min_size_mb": min_size_mb,
        "name_regex": name_regex,
        "max_items": max_items,
        "root": display_path(root),
        "home": display_path(home),
        "estimated_reclaimable_bytes": pre_report["summary"]["estimated_reclaimable_bytes"],
        "estimated_reclaimable_human": pre_report["summary"]["estimated_reclaimable_human"],
        "requires_yes_for_execute": pre_report["summary"]["requires_yes_for_execute"],
        "yes_required_categories": pre_report["summary"]["yes_required_categories"],
        "pre_clean_report": pre_report,
        "replay_command": build_clean_command(category_keys, execute=False),
    }


def symlink_specs(kind: str) -> list[dict[str, str]]:
    specs = []
    if kind in {"all", "logs"}:
        specs.append({"kind": "logs", "container_subdir": "Data/Library/Logs", "link_dir": LOG_LINK_DIR})
    if kind in {"all", "cache"}:
        specs.append({"kind": "cache", "container_subdir": "Data/Library/Caches", "link_dir": CACHE_LINK_DIR})
    return specs


def render_symbolic_links(*, kind: str, root: Path, home: Path, execute: bool, remove: bool) -> dict[str, Any]:
    container_root = Path(remap_path("~/Library/Containers/", root=root, home=home))
    rows = []
    removed = []
    for spec in symlink_specs(kind):
        link_dir = Path(remap_path(spec["link_dir"], root=root, home=home))
        if remove:
            existed_before = link_dir.exists() or link_dir.is_symlink()
            if execute and existed_before:
                delete_path(link_dir, root=root, home=home, delete_mode="permanent")
            removed.append(
                {
                    "kind": spec["kind"],
                    "link_dir": str(link_dir),
                    "existed_before": existed_before,
                    "removed": execute and existed_before,
                }
            )
            continue
        containers = (
            sorted(path for path in container_root.iterdir() if path.is_dir()) if container_root.exists() else []
        )
        for container in containers:
            source = container / spec["container_subdir"]
            if not source.is_dir():
                continue
            link_path = link_dir / container.name
            status = "planned"
            if execute:
                link_dir.mkdir(parents=True, exist_ok=True)
                if link_path.is_symlink() or link_path.is_file():
                    delete_path(link_path, root=root, home=home, delete_mode="permanent")
                elif link_path.exists():
                    status = "skipped-existing-non-symlink"
                if status != "skipped-existing-non-symlink":
                    link_path.symlink_to(source)
                    status = "created"
            rows.append(
                {
                    "kind": spec["kind"],
                    "container": container.name,
                    "source": str(source),
                    "link_dir": str(link_dir),
                    "link_path": str(link_path),
                    "status": status,
                }
            )
    return {
        "schema": "cleanmac.links.v1",
        "destructive": remove and execute,
        "dry_run": not execute,
        "mode": "remove" if remove else "create-update",
        "kind": kind,
        "container_root": str(container_root),
        "model": {
            "create": "create app log/cache symlink directories",
            "remove": "remove app log/cache symlink directories",
        },
        "mappings": rows,
        "removed": removed,
    }


def open_patterns(category: Category) -> tuple[str, ...]:
    if category.key == "terminal":
        return ("/private/var/log/asl/",)
    if category.key == "userAppLogs":
        return (LOG_LINK_DIR,)
    if category.key == "userAppCache":
        return (CACHE_LINK_DIR,)
    return category.paths


def render_open_targets(categories: list[Category], *, root: Path, home: Path, execute: bool) -> dict[str, Any]:
    rows = []
    for category in categories:
        for pattern in open_patterns(category):
            path = Path(remap_path(pattern, root=root, home=home))
            command = ["open", str(path)]
            status = "planned"
            error = None
            if execute:
                if sys.platform != "darwin":
                    status = "unsupported-platform"
                    error = "macOS 'open' command is only supported on darwin."
                else:
                    try:
                        subprocess.run(command, check=True)
                        status = "opened"
                    except (OSError, subprocess.CalledProcessError) as exc:
                        status = "failed"
                        error = str(exc)
            rows.append(
                {
                    "category": category.key,
                    "source_pattern": pattern,
                    "path": display_path(path),
                    "exists": path.exists(),
                    "command": shell_quote_command(command),
                    "status": status,
                    "error": error,
                    "special_case": category.key in {"terminal", "userAppLogs", "userAppCache"},
                }
            )
    return {
        "schema": "cleanmac.open.v1",
        "destructive": False,
        "dry_run": not execute,
        "targets": rows,
        "model": {
            "default": "open target path",
            "terminal": "open /private/var/log/asl/",
            "userAppLogs": f"open {LOG_LINK_DIR}",
            "userAppCache": f"open {CACHE_LINK_DIR}",
        },
    }


def cleanmac_delete_expr(pattern: str, *, root: Path, home: Path) -> str:
    remapped = remap_path(pattern, root=root, home=home)
    if any(char in remapped for char in "*?["):
        return remapped if not remapped.endswith("/") else f"{remapped}*"
    path = Path(remapped)
    if pattern.endswith("/"):
        return f"{str(path).rstrip('/')}/*"
    return str(path)


def shell_quote_command(parts: Sequence[str]) -> str:
    return " ".join(shlex.quote(part) for part in parts)


def build_clean_command(category_keys: Sequence[str], *, execute: bool) -> str | None:
    if not category_keys:
        return None
    parts = ["python3", "cleanmac.py", "clean", "--categories", ",".join(category_keys)]
    if execute:
        parts.append("--execute")
    return shell_quote_command(parts)


def build_cli_command(command: str, category_keys: Sequence[str], extra_args: Sequence[str] = ()) -> str:
    parts = ["python3", "cleanmac.py", command]
    if category_keys:
        parts.extend(["--categories", ",".join(category_keys)])
    parts.extend(extra_args)
    return shell_quote_command(parts)


def build_global_cli_command(
    command: str,
    category_keys: Sequence[str],
    *,
    root: Path,
    home: Path,
    json_output: bool = True,
    extra_args: Sequence[str] = (),
) -> str:
    parts = ["python3", "cleanmac.py", "--root", str(root), "--home", str(home)]
    if json_output:
        parts.append("--json")
    parts.append(command)
    if category_keys:
        parts.extend(["--categories", ",".join(category_keys)])
    parts.extend(extra_args)
    return shell_quote_command(parts)


def validate_clean_plan(plan_file: str, *, root: Path | None = None, home: Path | None = None) -> dict[str, Any]:
    plan = load_clean_plan(plan_file)
    unknown = [key for key in plan["category_keys"] if str(key) not in CATEGORY_BY_KEY]
    context_warnings = []
    if root is not None and plan.get("root") and not same_context_path(str(plan["root"]), root):
        context_warnings.append({"field": "root", "expected": plan["root"], "actual": display_path(root)})
    if home is not None and plan.get("home") and not same_context_path(str(plan["home"]), home):
        context_warnings.append({"field": "home", "expected": plan["home"], "actual": display_path(home)})
    preview = None
    if not unknown and root is not None and home is not None:
        categories = [CATEGORY_BY_KEY[str(key)] for key in plan["category_keys"]]
        preview = inspect_items(
            categories,
            root=root,
            home=home,
            limit=-1,
            min_size_mb=int(plan["min_size_mb"] or 0),
            include_patterns=tuple(str(pattern) for pattern in plan["include_patterns"]),
            exclude_patterns=tuple(str(pattern) for pattern in plan["exclude_patterns"]),
            older_than_days=float(plan["older_than_days"]) if plan["older_than_days"] is not None else None,
            name_regex=str(plan["name_regex"]) if plan["name_regex"] else None,
        )
    budget_summary = None
    if preview is not None:
        candidate_count = int(preview["total_candidates"])
        candidate_bytes = int(preview["total_bytes"])
        max_delete_bytes = None if plan["max_delete_mb"] is None else int(float(plan["max_delete_mb"]) * 1024 * 1024)
        budget_summary = {
            "candidate_count": candidate_count,
            "candidate_bytes": candidate_bytes,
            "candidate_human": human_size(candidate_bytes),
            "max_items": plan["max_items"],
            "within_max_items": plan["max_items"] is None or candidate_count <= int(plan["max_items"]),
            "max_delete_mb": plan["max_delete_mb"],
            "max_delete_bytes": max_delete_bytes,
            "within_max_delete_budget": max_delete_bytes is None or candidate_bytes <= max_delete_bytes,
        }
    return {
        "schema": "cleanmac.validate-plan.v1",
        "destructive": False,
        "dry_run": True,
        "valid": not unknown,
        "plan": plan,
        "unknown_categories": unknown,
        "context_warnings": context_warnings,
        "preview": preview,
        "budget_summary": budget_summary,
        "replay_clean_command": build_clean_command(
            [str(key) for key in plan["category_keys"] if str(key) in CATEGORY_BY_KEY], execute=False
        ),
        "execute_command_requires_review": True,
    }


def workflow_steps(selected_keys: Sequence[str], dry_run_keys: Sequence[str]) -> list[dict[str, Any]]:
    return [
        {
            "number": 1,
            "name": "script-audit",
            "purpose": "Show command templates and safety boundaries.",
            "command": build_cli_command("scripts", selected_keys),
            "destructive": False,
        },
        {
            "number": 2,
            "name": "analyze-space",
            "purpose": "Estimate per-category reclaimable space.",
            "command": build_cli_command("analyze", selected_keys),
            "destructive": False,
        },
        {
            "number": 3,
            "name": "diagnose-problems",
            "purpose": "Review log/cache/risk recommendations.",
            "command": build_cli_command("diagnose", selected_keys),
            "destructive": False,
        },
        {
            "number": 4,
            "name": "inspect-candidates",
            "purpose": "List direct children that would be deleted.",
            "command": build_cli_command("inspect", selected_keys),
            "destructive": False,
        },
        {
            "number": 5,
            "name": "dry-run-clean",
            "purpose": "Preview exact cleanup candidates without --execute.",
            "command": build_clean_command(dry_run_keys, execute=False),
            "destructive": False,
        },
        {
            "number": 6,
            "name": "manual-execute-gate",
            "purpose": "Only after review should a human run --execute, adding --yes for high/critical categories.",
            "command": build_clean_command(dry_run_keys, execute=True),
            "destructive": True,
            "automatic": False,
        },
    ]


def workflow_iteration_status(*, script_report: dict[str, Any], dry_run_report: dict[str, Any]) -> dict[str, Any]:
    inventory = script_report.get("script_inventory")
    gaps = []
    if not isinstance(inventory, dict):
        gaps.append({"id": "missing-script-inventory", "severity": "high"})
    elif "boundary_governance" not in inventory:
        gaps.append({"id": "missing-boundary-governance", "severity": "high"})
    preview_ready = (
        isinstance(dry_run_report.get("pre_clean_report"), dict) or dry_run_report.get("selected_categories") == []
    )
    pending = [] if preview_ready and not gaps else ["script-or-preview-gaps"]
    return {
        "schema": "cleanmac.workflow-iteration-status.v1",
        "safe_to_auto_continue": True,
        "destructive_cleanup_allowed": False,
        "summary": {"script_capability_gaps": len(gaps), "pending_blockers": len(pending)},
        "next_checkpoint": "test-acceptance" if not pending else "script-capability-gap-analysis",
        "script_capability_gaps": gaps,
        "implementation_tasks": [],
        "test_tasks": [],
        "acceptance_gate": {
            "ready_for_docker_validation": not pending,
            "required_command": "make release-check",
            "prerequisite_commands": [
                "make quality-check",
                "make local-test",
                "make build-check",
                "make package-smoke",
                "make script-smoke",
                "make bundle-audit-smoke",
                "make macos-smoke",
                "make security-smoke",
                "make dependency-audit-smoke",
                "make docs-smoke",
                "make governance-smoke",
                "make open-source-smoke",
                "make distribution-smoke",
                "make docker-test",
            ],
            "pending_blockers": pending,
            "must_not_run": ["clean --execute", "--allow-live-root", "sudo rm"],
        },
    }


def workflow_automation_playbook(
    selected_keys: Sequence[str], dry_run_keys: Sequence[str], *, root: Path, home: Path, dry_run_scope: str
) -> dict[str, Any]:
    return {
        "schema": "cleanmac.workflow-automation.v1",
        "version": 1,
        "purpose": "Run non-destructive cleanup review, planning, and validation tasks safely.",
        "safe_to_auto_execute": True,
        "destructive_cleanup_allowed": False,
        "agent_contract": {
            "must_not_execute_cleanup": True,
            "forbidden_command_patterns": ["clean --execute", "--allow-live-root", "rm -rf /", "sudo rm"],
        },
        "required_inputs": {
            "root": display_path(root),
            "home": display_path(home),
            "selected_category_keys": list(selected_keys),
            "dry_run_category_keys": list(dry_run_keys),
            "dry_run_scope": dry_run_scope,
        },
        "load_context": {
            "command": build_global_cli_command(
                "workflow", selected_keys, root=root, home=home, extra_args=["--dry-run-scope", dry_run_scope]
            )
        },
        "test_acceptance": {
            "environment": {
                "requires_virtualenv": True,
                "workflow_python_env": "PYTHON=.venv/bin/python",
            },
            "required_commands": [
                "make quality-check",
                "make local-test",
                "make build-check",
                "make package-smoke",
                "make script-smoke",
                "make bundle-audit-smoke",
                "make macos-smoke",
                "make security-smoke",
                "make dependency-audit-smoke",
                "make docs-smoke",
                "make governance-smoke",
                "make open-source-smoke",
                "make distribution-smoke",
                "make docker-test",
                "make release-check",
            ],
        },
    }


def render_workflow(
    categories: list[Category],
    *,
    root: Path,
    home: Path,
    inspect_limit: int,
    log_threshold_mb: int,
    large_threshold_mb: int,
    dry_run_scope: str,
) -> dict[str, Any]:
    selected_keys = [category.key for category in categories]
    script_report = render_scripts(categories, root=root, home=home)
    analysis_report = analyze(categories, root=root, home=home)
    diagnose_report = diagnose(
        categories, root=root, home=home, log_threshold_mb=log_threshold_mb, large_threshold_mb=large_threshold_mb
    )
    inspect_report = inspect_items(categories, root=root, home=home, limit=inspect_limit)
    if dry_run_scope == "selected":
        dry_run_categories = categories
    else:
        recommended_keys = set(diagnose_report["recommended_clean_categories"])  # type: ignore[arg-type]
        dry_run_categories = [category for category in categories if category.key in recommended_keys]
    dry_run_keys = [category.key for category in dry_run_categories]
    dry_run_report = (
        clean(dry_run_categories, root=root, home=home, execute=False)
        if dry_run_categories
        else {
            "schema": "cleanmac.clean.v1",
            "destructive": False,
            "dry_run": True,
            "selected_categories": [],
            "pre_clean_report": None,
            "post_clean_report": None,
            "total_bytes": 0,
            "total_human": human_size(0),
            "items": [],
        }
    )
    iteration_status = workflow_iteration_status(script_report=script_report, dry_run_report=dry_run_report)
    return {
        "schema": "cleanmac.workflow.v1",
        "destructive": False,
        "dry_run": True,
        "workflow_name": "safe-cleaning-workflow",
        "principles": [
            "Never execute destructive cleanup during workflow; final execute commands are for manual review only.",
            "Inspect large logs before deleting them.",
            "Preserve target directories and delete only their contents.",
        ],
        "selected_categories": [category_metadata(category) for category in categories],
        "dry_run_scope": dry_run_scope,
        "dry_run_categories": [category_metadata(category) for category in dry_run_categories],
        "steps": workflow_steps(selected_keys, dry_run_keys),
        "automation_playbook": workflow_automation_playbook(
            selected_keys, dry_run_keys, root=root, home=home, dry_run_scope=dry_run_scope
        ),
        "reports": {
            "scripts": script_report,
            "analyze": analysis_report,
            "diagnose": diagnose_report,
            "inspect": inspect_report,
            "dry_run": dry_run_report,
            "iteration_status": iteration_status,
        },
    }


def human_size(size: int | None) -> str:
    if size is None:
        return "unknown"
    value = float(size)
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if value < 1024 or unit == "TB":
            return f"{int(value)} B" if unit == "B" else f"{value:.2f} {unit}"
        value /= 1024
    return f"{size} B"


def row_bytes(row: dict[str, Any]) -> int:
    return int(row["bytes"])


def print_categories(categories: Sequence[Category], *, as_json: bool) -> None:
    if as_json:
        print(json.dumps([category_metadata(category) for category in categories], indent=2, ensure_ascii=False))
        return
    print("Available cleanup categories:")
    for category in categories:
        flags = []
        if category.default:
            flags.append("default")
        if category.recommended:
            flags.append("recommended")
        if category.advanced:
            flags.append("advanced")
        flags.append(f"risk={category.risk}")
        if category.requires_privilege:
            flags.append("may require privilege/full disk access")
        print(f"  {category.key:14} {category.title} ({', '.join(flags)})")
        for pattern in category.paths:
            print(f"    - {pattern}")


def print_report(report: dict[str, Any], *, as_json: bool, command: str) -> None:
    if as_json:
        print(json.dumps(report, indent=2, ensure_ascii=False))
        return
    if command == "analyze":
        print(f"Total reclaimable estimate: {report['total_human']}")
        for row in report["categories"]:  # type: ignore[index]
            print(f"  {row['key']:14} {row['human']:>10}  risk={row['risk']}")
        return
    if command == "diagnose":
        print(f"Total reclaimable estimate: {report['total_human']}")
        print("Recommended categories:", ",".join(report["recommended_clean_categories"]) or "<none>")
        print("Caution categories:", ",".join(report["caution_clean_categories"]) or "<none>")
        return
    if command == "capabilities":
        print(f"{report['name']}: {report['model']}")
        print(f"Categories: {report['category_count']} ({report['active_path_count']} active path entries)")
        print("Commands:", ",".join(report["commands"]))
        return
    if command == "doctor":
        print("cleanmac doctor: non-destructive environment and permission diagnostics")
        print(f"Platform: {report['platform']}")
        for name, check in report["checks"].items():  # type: ignore[union-attr]
            print(f"  [{check['status']}] {name}: {check['message']}")
        return
    if command == "plan":
        print(f"Cleanup plan: {','.join(report['categories']) or '<none>'}")
        print(f"Risk policy: {report['risk_policy']}")
        print(f"Replay dry-run: {report['replay_command']}")
        return
    if command == "validate-plan":
        print(f"Plan valid: {report['valid']}")
        print(f"Replay dry-run: {report['replay_clean_command']}")
        return
    if command == "workflow":
        print(f"Workflow: {report['workflow_name']}")
        print(f"Dry-run scope: {report['dry_run_scope']}")
        return
    if command == "inspect":
        print(
            f"Inspectable cleanup candidates: showing {report['shown_candidates']} of {report['total_candidates']} item(s), {report['total_human']}"
        )
        for row in report["items"]:  # type: ignore[index]
            print(f"  [{row['category']}] {row['path']} ({row['human']})")
        return
    if command == "scripts":
        print("Script groups and cleanup command templates:")
        for group_key, group_info in report.get("groups", {}).items():  # type: ignore[union-attr]
            print(f"\n[{group_key}] destructive={group_info.get('destructive')}")
            for command_line in group_info.get("commands", []):
                print(f"  command: {command_line}")
        for row in report["categories"]:  # type: ignore[index]
            print(f"\n[{row['key']}] {row['title']} risk={row['risk']}")
            for command_line in row["commands"]["analyze"]:
                print(f"  analyze: {command_line}")
            for command_line in row["commands"]["delete"]:
                print(f"  delete : {command_line}")
        return
    if command == "software":
        print(f"Software {report['action']}: {report['status']}")
        return
    if command == "optimize":
        print(f"Optimize {report['action']}: {len(report['tasks'])} task(s), dry-run only")
        return
    if command == "analyze-tree":
        print(f"Analyze tree: {report['path']} showing {report['shown_entries']} of {report['total_entries']} entries")
        return
    if command == "status":
        print(f"Status snapshot: disk free {report['disk']['free_human']}")
        return
    if command == "links":
        mode = "DRY-RUN" if report["dry_run"] else "EXECUTE"
        print(f"{mode}: symlink mode={report['mode']} kind={report['kind']}")
        return
    if command == "open":
        mode = "DRY-RUN" if report["dry_run"] else "EXECUTE"
        print(f"{mode}: Finder targets")
        for row in report["targets"]:  # type: ignore[index]
            special = " special" if row["special_case"] else ""
            print(f"  [{row['category']}]{special} {row['status']}: {row['command']} exists={row['exists']}")
        return
    mode = "DRY-RUN" if report["dry_run"] else "EXECUTE"
    pre_report = report.get("pre_clean_report")
    if pre_report:
        pre_summary = pre_report["summary"]  # type: ignore[index]
        print("Pre-clean report:")
        print(f"  selected categories : {pre_summary['selected_category_count']}")
        print(f"  candidates          : {pre_summary['candidate_count']}")
        print(f"  estimated reclaim   : {pre_summary['estimated_reclaimable_human']}")
        print(f"  high-risk categories: {','.join(pre_summary['high_risk_categories']) or '<none>'}")
        print(f"  semantics           : {pre_summary['delete_semantics']}")
    print(f"{mode}: {report['total_human']} across {len(report['items'])} item(s)")
    for row in report["items"]:  # type: ignore[index]
        action = "deleted" if row["deleted"] else "would delete"
        print(f"  [{row['category']}] {action}: {row['path']} ({row['human']})")
    post_report = report.get("post_clean_report")
    if post_report:
        post_summary = post_report["summary"]  # type: ignore[index]
        print("Post-clean report:")
        print(f"  deleted items       : {post_summary['deleted_item_count']}")
        print(f"  estimated reclaimed : {post_summary['estimated_reclaimed_human']}")


def write_report_file(
    report_file: str, *, command: str, root: Path, home: Path, argv: Sequence[str], report: dict[str, Any]
) -> dict[str, Any]:
    path = Path(report_file).expanduser().resolve(strict=False)
    selected_categories = report.get("selected_categories")
    selected_category_keys = (
        [str(row.get("key")) if isinstance(row, dict) and "key" in row else str(row) for row in selected_categories]
        if isinstance(selected_categories, list)
        else None
    )
    audit_record = {
        "schema": "cleanmac.audit.v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "command": command,
        "argv": list(argv),
        "root": display_path(root),
        "home": display_path(home),
        "report_file": display_path(path),
        "dry_run": report.get("dry_run"),
        "safety_gate": report.get("safety_gate"),
        "selected_category_keys": selected_category_keys,
        "selected_categories": selected_categories,
        "report": report,
    }
    path.write_text(json.dumps(audit_record, indent=2, ensure_ascii=False), encoding="utf-8")
    return audit_record


def emit_report(
    report: dict[str, Any], *, args: argparse.Namespace, command: str, root: Path, home: Path, argv: Sequence[str]
) -> None:
    if args.report_file:
        audit_record = write_report_file(
            args.report_file, command=command, root=root, home=home, argv=argv, report=report
        )
        report["report_file"] = audit_record["report_file"]
    print_report(report, as_json=args.json, command=command)


def main(argv: Sequence[str] | None = None) -> int:
    original_argv = list(sys.argv[1:] if argv is None else argv)
    actual_argv, grouped_command = normalize_grouped_argv(original_argv)
    args = parse_args(actual_argv)
    if grouped_command:
        args.grouped_command = grouped_command
    root = Path(args.root).expanduser().resolve(strict=False)
    home = Path(args.home).expanduser()
    plan_metadata = apply_clean_plan_defaults(args)

    if args.command == "list":
        print_categories(CATEGORIES, as_json=args.json)
        return 0
    if args.command == "capabilities":
        emit_report(render_capabilities(), args=args, command="capabilities", root=root, home=home, argv=actual_argv)
        return 0
    if args.command == "doctor":
        emit_report(
            render_doctor(root=root, home=home), args=args, command="doctor", root=root, home=home, argv=actual_argv
        )
        return 0
    if args.command == "validate-plan":
        emit_report(
            validate_clean_plan(args.plan_file, root=root, home=home),
            args=args,
            command="validate-plan",
            root=root,
            home=home,
            argv=actual_argv,
        )
        return 0
    if args.command == "analyze-tree":
        emit_report(
            analyze_tree(
                Path(args.path), root=root, home=home, depth=args.depth, top=args.top, min_size_mb=args.min_size_mb
            ),
            args=args,
            command="analyze-tree",
            root=root,
            home=home,
            argv=actual_argv,
        )
        return 0
    if args.command == "links":
        emit_report(
            render_symbolic_links(kind=args.kind, root=root, home=home, execute=args.execute, remove=args.remove),
            args=args,
            command="links",
            root=root,
            home=home,
            argv=actual_argv,
        )
        return 0
    if args.command == "software":
        emit_report(
            render_software(args.action, app=args.app, root=root, home=home),
            args=args,
            command="software",
            root=root,
            home=home,
            argv=actual_argv,
        )
        return 0
    if args.command == "optimize":
        emit_report(
            render_optimize(args.action, execute=args.execute),
            args=args,
            command="optimize",
            root=root,
            home=home,
            argv=actual_argv,
        )
        return 0
    if args.command == "status":
        emit_report(
            render_status_snapshot(root=root), args=args, command="status", root=root, home=home, argv=actual_argv
        )
        return 0

    categories = select_categories(args)
    if args.command == "open":
        emit_report(
            render_open_targets(categories, root=root, home=home, execute=args.execute),
            args=args,
            command="open",
            root=root,
            home=home,
            argv=actual_argv,
        )
        return 0
    if args.command == "scripts":
        emit_report(
            render_scripts(categories, root=root, home=home, group=args.group),
            args=args,
            command="scripts",
            root=root,
            home=home,
            argv=actual_argv,
        )
        return 0
    if args.command == "analyze":
        emit_report(
            analyze(categories, root=root, home=home),
            args=args,
            command="analyze",
            root=root,
            home=home,
            argv=actual_argv,
        )
        return 0
    if args.command == "plan":
        report = render_clean_plan(
            categories,
            root=root,
            home=home,
            risk_policy=args.risk_policy,
            max_delete_mb=args.max_delete_mb,
            include_patterns=parse_csv(args.include),
            exclude_patterns=parse_csv(args.exclude),
            older_than_days=args.older_than_days,
            min_size_mb=args.min_size_mb,
            name_regex=args.name_regex,
            max_items=args.max_items,
        )
        emit_report(report, args=args, command="plan", root=root, home=home, argv=actual_argv)
        return 0
    if args.command == "diagnose":
        emit_report(
            diagnose(
                categories,
                root=root,
                home=home,
                log_threshold_mb=args.log_threshold_mb,
                large_threshold_mb=args.large_threshold_mb,
            ),
            args=args,
            command="diagnose",
            root=root,
            home=home,
            argv=actual_argv,
        )
        return 0
    if args.command == "workflow":
        report = render_workflow(
            categories,
            root=root,
            home=home,
            inspect_limit=args.inspect_limit,
            log_threshold_mb=args.log_threshold_mb,
            large_threshold_mb=args.large_threshold_mb,
            dry_run_scope=args.dry_run_scope,
        )
        emit_report(report, args=args, command="workflow", root=root, home=home, argv=actual_argv)
        return 0
    if args.command == "inspect":
        report = inspect_items(
            categories,
            root=root,
            home=home,
            limit=args.limit,
            recursive=args.recursive,
            min_size_mb=args.min_size_mb,
            sort=args.sort,
            include_patterns=parse_csv(args.include),
            exclude_patterns=parse_csv(args.exclude),
            older_than_days=args.older_than_days,
            name_regex=args.name_regex,
            max_delete_mb=args.max_delete_mb,
            max_items=args.max_items,
        )
        emit_report(report, args=args, command="inspect", root=root, home=home, argv=actual_argv)
        return 0
    if args.command == "clean":
        if args.require_plan_context and not plan_metadata:
            raise SystemExit("--require-plan-context requires --plan-file.")
        if args.require_plan_context and plan_metadata:
            if plan_metadata.get("root") and not same_context_path(str(plan_metadata["root"]), root):
                raise SystemExit(f"Plan root mismatch: expected {plan_metadata['root']} actual {display_path(root)}")
            if plan_metadata.get("home") and not same_context_path(str(plan_metadata["home"]), home):
                raise SystemExit(f"Plan home mismatch: expected {plan_metadata['home']} actual {display_path(home)}")
        if args.execute and root == Path("/") and not args.allow_live_root:
            raise SystemExit(
                "Refusing to execute cleanup against live root '/'. Use --root with a sandbox, or pass --allow-live-root after reviewing dry-run output."
            )
        yes_required = categories_requiring_yes(categories, args.risk_policy)
        if args.execute and yes_required and not args.yes:
            names = ", ".join(f"{category.key}({category.risk})" for category in yes_required)
            raise SystemExit(
                f"Refusing to execute cleanup without --yes under risk policy '{args.risk_policy}'. Review dry-run/inspect output first. Categories: {names}"
            )
        report = clean(
            categories,
            root=root,
            home=home,
            execute=args.execute,
            risk_policy=args.risk_policy,
            max_delete_mb=args.max_delete_mb,
            plan_file=str(plan_metadata["path"]) if plan_metadata else None,
            include_patterns=parse_csv(args.include),
            exclude_patterns=parse_csv(args.exclude),
            older_than_days=args.older_than_days,
            min_size_mb=args.min_size_mb,
            name_regex=args.name_regex,
            max_items=args.max_items,
            fail_on_skipped=args.fail_on_skipped,
            bundle_allowlist=parse_csv(args.bundle_allowlist),
            bundle_blocklist=parse_csv(args.bundle_blocklist),
            delete_mode=args.delete_mode,
            operation_log=args.operation_log,
            command_argv=original_argv,
        )
        if plan_metadata:
            report["plan_metadata"] = plan_metadata
        emit_report(report, args=args, command="clean", root=root, home=home, argv=actual_argv)
        return 0
    raise SystemExit(f"Unsupported command: {args.command}")


if __name__ == "__main__":
    raise SystemExit(main())
