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
import hashlib
import html
import json
import os
import re
import shlex
import shutil
import subprocess
import sys
import time
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, NoReturn
from urllib.parse import quote

from cleancli import ai_schema, delete_ops, protection
from cleancli.ai_contract import render_ai_intent_hints as render_ai_intent_hints
from cleancli.ai_contract import render_ai_recommended_workflow as render_ai_recommended_workflow
from cleancli.ai_contract import render_ai_tool_contract as render_ai_tool_contract
from cleancli.ai_decision import render_ai_tool_decision_matrix
from cleancli.ai_errors import classify_cli_error as classify_cli_error
from cleancli.ai_errors import render_ai_error_report as render_ai_error_report
from cleancli.ai_errors import render_ai_error_taxonomy as render_ai_error_taxonomy
from cleancli.ai_eval import render_ai_eval_pack, render_ai_eval_run
from cleancli.ai_governance import render_ai_governance_advice
from cleancli.ai_host_evidence import render_ai_host_evidence
from cleancli.ai_host_integration import render_ai_host_integration_pack, render_ai_host_preflight
from cleancli.ai_host_policy import evaluate_ai_host_tool_call, render_ai_host_policy
from cleancli.ai_policy import render_llm_invocation_guide as render_llm_invocation_guide
from cleancli.ai_policy import render_plan_policy as render_plan_policy
from cleancli.ai_policy import render_prompt_injection_policy as render_prompt_injection_policy
from cleancli.ai_readiness import render_ai_readiness
from cleancli.ai_runbook import render_ai_runbook
from cleancli.ai_self_test import render_ai_self_test as render_ai_self_test
from cleancli.ai_versioning import (
    AI_HOST_CRITICAL_SCHEMAS,
    negotiate_plan_schema,
    render_ai_contract_samples,
    render_ai_contract_validation_summary,
    render_ai_schema_registry,
    validate_contract_payload,
)
from cleancli.governance import render_boundary_governance, render_runtime_lifecycle_policy
from cleancli.mcp_resources import render_mcp_surface_audit
from cleancli.privacy import PRIVACY_SCOPES, execute_privacy_cleanup, render_privacy
from cleancli.profiles import PROFILES, profile_names, render_profiles
from cleancli.protection_data import APP_CLEANUP_RULES, DEFAULT_PROTECTED_BUNDLE_IDS, OFFICIAL_UNINSTALLER_RULES
from cleancli.release_artifacts import (
    HOMEBREW_TAP,
    REQUIRED_RELEASE_ASSET_NAMES,
    build_release_evidence_bundle,
    verify_release_artifact_manifest,
)
from cleancli.release_orchestration import (
    render_release_post_publish_evidence_template,
    render_release_post_publish_result,
    render_release_post_publish_verification,
    render_release_promotion_decision,
    render_release_rehearsal,
    render_release_rollback_plan,
)
from cleancli.release_readiness import render_release_readiness
from cleancli.report_renderers import render_html_report, render_markdown_report
from cleancli.review import (
    apply_item_scope,
    load_json_file,
    normalize_review_items,
    render_review,
    render_review_html,
    validate_review_selection,
)
from cleancli.software_uninstall import execute_software_uninstall
from cleancli.software_uninstall import render_software as render_software_report
from cleancli.startup import disable_startup_items, render_startup
from cleancli.tool_adapters import TOOL_ADAPTER_CHOICES, execute_tool
from cleancli.tool_adapters import render_tool_plan as render_tool_adapter_plan

VERSION = "0.1.0"

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
PLAN_MAX_AGE_SECONDS = 30 * 60


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
        "edge",
        APP_CLEANUP_RULES["edge"]["title"],
        APP_CLEANUP_RULES["edge"]["paths"],
        "Deletes Microsoft Edge regenerable browser caches while preserving profile data, cookies, history, passwords, and extensions.",
        risk="medium",
        advanced=True,
        process_guard="Microsoft Edge",
    ),
    Category(
        "brave",
        APP_CLEANUP_RULES["brave"]["title"],
        APP_CLEANUP_RULES["brave"]["paths"],
        "Deletes Brave regenerable browser caches while preserving profile data, cookies, history, passwords, and extensions.",
        risk="medium",
        advanced=True,
        process_guard="Brave Browser",
    ),
    Category(
        "arc",
        APP_CLEANUP_RULES["arc"]["title"],
        APP_CLEANUP_RULES["arc"]["paths"],
        "Deletes Arc regenerable browser caches while preserving profile data, cookies, history, passwords, and extensions.",
        risk="medium",
        advanced=True,
        process_guard="Arc",
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
        "discord",
        APP_CLEANUP_RULES["discord"]["title"],
        APP_CLEANUP_RULES["discord"]["paths"],
        "Deletes Discord regenerable caches while preserving account state, cookies, local storage, and IndexedDB.",
        risk="medium",
        advanced=True,
        process_guard="Discord",
    ),
    Category(
        "notion",
        APP_CLEANUP_RULES["notion"]["title"],
        APP_CLEANUP_RULES["notion"]["paths"],
        "Deletes Notion regenerable caches while preserving workspace databases, cookies, local storage, and IndexedDB.",
        risk="medium",
        advanced=True,
        process_guard="Notion",
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
        "homebrewCaches",
        APP_CLEANUP_RULES["homebrewCaches"]["title"],
        APP_CLEANUP_RULES["homebrewCaches"]["paths"],
        "Deletes Homebrew download caches while preserving Homebrew installations and taps.",
        risk="medium",
        advanced=True,
    ),
    Category(
        "gradleCaches",
        APP_CLEANUP_RULES["gradleCaches"]["title"],
        APP_CLEANUP_RULES["gradleCaches"]["paths"],
        "Deletes Gradle dependency and wrapper caches while preserving Gradle credentials and init configuration.",
        risk="medium",
        advanced=True,
    ),
    Category(
        "cargoCaches",
        APP_CLEANUP_RULES["cargoCaches"]["title"],
        APP_CLEANUP_RULES["cargoCaches"]["paths"],
        "Deletes Cargo registry and git caches while preserving Cargo credentials and configuration.",
        risk="medium",
        advanced=True,
    ),
    Category(
        "cocoaPodsCaches",
        APP_CLEANUP_RULES["cocoaPodsCaches"]["title"],
        APP_CLEANUP_RULES["cocoaPodsCaches"]["paths"],
        "Deletes CocoaPods caches and spec repos while preserving publishing and registry credentials.",
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
        "windsurf",
        APP_CLEANUP_RULES["windsurf"]["title"],
        APP_CLEANUP_RULES["windsurf"]["paths"],
        "Deletes Windsurf regenerable caches while preserving user settings, workspace state, local storage, and IndexedDB.",
        risk="medium",
        advanced=True,
        process_guard="Windsurf",
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
        "description": "App inventory, uninstall inspection/planning, and governed review-selection Trash execution.",
        "commands": [
            "software list",
            "software leftovers",
            "software startup-items",
            "software inspect",
            "software uninstall-plan",
            "software execute",
        ],
        "flat_command_aliases": [],
    },
    "startup": {
        "title": "启动项 / Startup",
        "description": "Read-only startup item audit and disable planning for LaunchAgents, LaunchDaemons, and StartupItems.",
        "commands": ["startup audit", "startup plan"],
        "flat_command_aliases": [],
    },
    "privacy": {
        "title": "隐私 / Privacy",
        "description": "Read-only privacy data inspection and cleanup planning for browser and Electron app data.",
        "commands": ["privacy inspect", "privacy plan"],
        "flat_command_aliases": [],
    },
    "permissions": {
        "title": "权限 / Permissions",
        "description": "Read-only preflight for category privileges, Full Disk Access hints, sudo availability, and live-root execution gates.",
        "commands": ["permissions"],
        "flat_command_aliases": [],
    },
    "tools": {
        "title": "工具语义计划 / Tool semantic plans",
        "description": "Read-only semantic cleanup plans for external tools; never executes tool prune commands.",
        "commands": ["tool-plan", "tool-execute"],
        "flat_command_aliases": [],
    },
    "review": {
        "title": "审查 / Review",
        "description": "Normalize reports and plans into reviewable item selections.",
        "commands": ["review"],
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
    ("clean", "policy-simulate"): "policy-simulate",
    ("clean", "run"): "clean",
    ("clean", "scripts"): "scripts",
    ("clean", "open"): "open",
    ("clean", "links"): "links",
    ("analyze", "categories"): "analyze",
    ("analyze", "scan"): "analyze-tree",
    ("analyze", "tree"): "analyze-tree",
}


class CleanMacCLIError(Exception):
    def __init__(self, message: str, *, exit_code: int = 1) -> None:
        super().__init__(message)
        self.message = message.strip()
        self.exit_code = exit_code


class CleanMacArgumentParser(argparse.ArgumentParser):
    def error(self, message: str) -> NoReturn:
        raise CleanMacCLIError(message, exit_code=2)

    def exit(self, status: int = 0, message: str | None = None) -> NoReturn:
        if message:
            print(message, end="", file=sys.stderr if status else sys.stdout)
        if status:
            raise CleanMacCLIError(message or "argument parsing failed", exit_code=status)
        raise SystemExit(status)


def emit_cli_error(message: str, *, argv: Sequence[str], exit_code: int, as_json: bool) -> int:
    if as_json:
        print(json.dumps(render_ai_error_report(message, argv=argv, exit_code=exit_code), indent=2), file=sys.stderr)
    else:
        print(message, file=sys.stderr)
    return exit_code


def parse_args(argv: Sequence[str]) -> argparse.Namespace:
    parser = CleanMacArgumentParser(
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
    parser.add_argument("--version", action="version", version=f"cleanmac {VERSION}", help="Show version and exit.")
    parser.add_argument(
        "-v",
        "--verbose",
        action="count",
        default=0,
        help="Increase output verbosity. Can be repeated.",
    )
    parser.add_argument(
        "-q",
        "--quiet",
        action="store_true",
        help="Suppress all non-error output to stdout.",
    )
    parser.add_argument(
        "--report-file",
        help="Write the command report to a JSON audit file while still printing the normal output.",
    )
    parser.add_argument(
        "--report-format",
        choices=("json", "html", "markdown"),
        default="json",
        help="Format used with --report-file. JSON is machine-readable; HTML/Markdown are human audit reports.",
    )

    subparsers = parser.add_subparsers(dest="command", required=True, parser_class=CleanMacArgumentParser)

    subparsers.add_parser("list", help="List available cleanup categories.")
    subparsers.add_parser("capabilities", help="Describe commands and safety guardrails.")
    subparsers.add_parser("profiles", help="List built-in safe cleanup profiles.")
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
    plan_cmd.add_argument(
        "--ai-origin",
        action="store_true",
        help="Mark the generated plan as AI-originated so later execution requires conservative safeguards.",
    )

    validate_plan = subparsers.add_parser("validate-plan", help="Validate a cleanup plan/audit JSON file.")
    validate_plan.add_argument("--plan-file", required=True)

    policy_simulate = subparsers.add_parser(
        "policy-simulate", help="Simulate AI cleanup policy without deleting files."
    )
    policy_simulate.add_argument("--plan-file", required=True)
    policy_simulate.add_argument("--execute", action="store_true", help="Simulate destructive execution intent.")
    policy_simulate.add_argument("--delete-mode", choices=("permanent", "trash"), default="permanent")
    policy_simulate.add_argument("--operation-log")
    policy_simulate.add_argument(
        "--review-selection-file",
        help="Validate and include a cleanmac.review-selection.v1 constraint in the recommended safe argv.",
    )
    policy_simulate.add_argument("--require-plan-context", action="store_true")
    policy_simulate.add_argument("--require-confirmation-token", action="store_true")
    policy_simulate.add_argument("--confirmation-token")

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

    ai_workflow_cmd = subparsers.add_parser(
        "ai-workflow",
        help="Emit a one-shot governed AI host workflow without scanning or deleting files.",
    )
    ai_workflow_cmd.add_argument("--goal", choices=("safe-cleanup",), default="safe-cleanup")
    add_category_flags(ai_workflow_cmd, default_scope="default")

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
    clean_cmd.add_argument(
        "--review-selection-file",
        help="Apply a cleanmac.review-selection.v1 file to plan replay so only reviewed selected items are eligible.",
    )
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
        "--fail-fast",
        action="store_true",
        help="Stop execution on the first item-level delete failure. By default, failures are recorded and cleanup continues.",
    )
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
    clean_cmd.add_argument(
        "--confirmation-token",
        help="AI confirmation token generated by a matching dry-run report.",
    )
    clean_cmd.add_argument(
        "--require-confirmation-token",
        action="store_true",
        help="Refuse execution unless --confirmation-token matches the current plan/context/budget/delete-mode.",
    )

    software_cmd = subparsers.add_parser("software", help="Software inventory and app cleanup planning.")
    software_cmd.add_argument(
        "action",
        nargs="?",
        choices=("list", "leftovers", "startup-items", "inspect", "uninstall-plan", "execute"),
        default="list",
    )
    software_cmd.add_argument("--app", help="Application name or bundle id for uninstall planning.")
    software_cmd.add_argument("--plan-file", help="cleanmac.software-uninstall-plan.v1 file to dry-run or execute.")
    software_cmd.add_argument(
        "--review-selection-file",
        help="cleanmac.review-selection.v1 file that selects software uninstall candidates from the plan.",
    )
    software_cmd.add_argument(
        "--execute", action="store_true", help="Move selected software uninstall candidates to Trash."
    )
    software_cmd.add_argument("--yes", action="store_true", help="Confirm governed software uninstall Trash execution.")
    software_cmd.add_argument(
        "--delete-mode",
        choices=("trash",),
        default="trash",
        help="Software uninstall execute only supports Trash routing for recovery.",
    )
    software_cmd.add_argument(
        "--operation-log",
        default=OPERATIONS_LOG_FILE,
        help="Append JSONL audit records when software uninstall candidates are evaluated.",
    )

    startup_cmd = subparsers.add_parser("startup", help="Startup item audit, disable planning, and governed disable.")
    startup_cmd.add_argument("action", nargs="?", choices=("audit", "plan", "disable"), default="audit")
    startup_cmd.add_argument("--plan-file", help="cleanmac.startup-plan.v1 file to execute or dry-run disable against.")
    startup_cmd.add_argument(
        "--review-selection-file",
        help="cleanmac.review-selection.v1 file that selects startup items from the plan.",
    )
    startup_cmd.add_argument(
        "--execute", action="store_true", help="Disable selected startup items by editing user plists."
    )
    startup_cmd.add_argument("--yes", action="store_true", help="Confirm governed startup disable execution.")
    startup_cmd.add_argument(
        "--operation-log",
        default=OPERATIONS_LOG_FILE,
        help="Append JSONL audit records when startup disable is evaluated.",
    )

    privacy_cmd = subparsers.add_parser(
        "privacy", help="Privacy data inspection, cleanup planning, and governed cleanup."
    )
    privacy_cmd.add_argument("action", nargs="?", choices=("inspect", "plan", "execute"), default="inspect")
    privacy_cmd.add_argument(
        "--scope",
        choices=PRIVACY_SCOPES,
        default="all",
        help="Privacy data scope to inspect or plan: all, cache, cookies, history, local-storage, credentials.",
    )
    privacy_cmd.add_argument("--plan-file", help="cleanmac.privacy-plan.v1 file to execute or dry-run cleanup against.")
    privacy_cmd.add_argument(
        "--review-selection-file",
        help="cleanmac.review-selection.v1 file that selects privacy cleanup items from the plan.",
    )
    privacy_cmd.add_argument(
        "--execute", action="store_true", help="Move selected privacy cleanup candidates to Trash."
    )
    privacy_cmd.add_argument("--yes", action="store_true", help="Confirm governed privacy cleanup execution.")
    privacy_cmd.add_argument(
        "--delete-mode",
        choices=("trash",),
        default="trash",
        help="Privacy cleanup execute only supports Trash routing for recovery.",
    )
    privacy_cmd.add_argument(
        "--operation-log",
        default=OPERATIONS_LOG_FILE,
        help="Append JSONL audit records when privacy cleanup is evaluated.",
    )

    permissions_cmd = subparsers.add_parser(
        "permissions",
        help="Preflight category permissions, Full Disk Access hints, and live-root execution requirements.",
    )
    add_category_flags(permissions_cmd, default_scope="all")

    tool_plan_cmd = subparsers.add_parser(
        "tool-plan",
        help="Render read-only semantic cleanup plans for external tools such as Docker, Homebrew, and Xcode.",
    )
    tool_plan_cmd.add_argument(
        "--tool",
        choices=TOOL_ADAPTER_CHOICES,
        default="all",
        help="Tool adapter to describe. Plans are read-only and never execute external cleanup commands.",
    )

    tool_execute_cmd = subparsers.add_parser(
        "tool-execute",
        help="Run allowlisted external tool dry-run or cleanup commands with explicit execution gates.",
    )
    tool_execute_cmd.add_argument(
        "--tool",
        choices=TOOL_ADAPTER_CHOICES,
        default="all",
    )
    tool_execute_cmd.add_argument("--execute", action="store_true", help="Run destructive adapter commands.")
    tool_execute_cmd.add_argument("--yes", action="store_true", help="Confirm destructive adapter execution.")
    tool_execute_cmd.add_argument(
        "--operation-log",
        default=OPERATIONS_LOG_FILE,
        help="Append JSONL audit records when adapter commands are evaluated.",
    )
    tool_execute_cmd.add_argument("--timeout", type=float, default=30.0, help="Per-command timeout in seconds.")

    review_cmd = subparsers.add_parser("review", help="Normalize a JSON report or plan into reviewable selections.")
    review_cmd.add_argument("--input-file", required=True, help="JSON plan/report to review.")
    review_cmd.add_argument("--selection-input-file", help="Existing review selection JSON to validate and replay.")
    review_cmd.add_argument("--format", choices=("json", "html"), default="json")
    review_cmd.add_argument("--selection-file", help="Write the generated review selection JSON to this path.")
    review_cmd.add_argument(
        "--item-scope",
        choices=("all", "selected", "excluded"),
        default="all",
        help="Filter review output items while preserving full selection metadata.",
    )
    review_cmd.add_argument(
        "--item-sort",
        choices=("source", "risk-desc", "bytes-desc", "selected-first", "path"),
        default="source",
        help="Sort review output items without changing selection metadata.",
    )
    review_cmd.add_argument(
        "--require-valid-selection",
        action="store_true",
        help="Exit non-zero when --selection-input-file does not match the reviewed source or contains invalid IDs.",
    )
    review_cmd.add_argument(
        "--select-item",
        action="append",
        default=[],
        help="Explicitly include a review item ID in the generated selection. May be repeated.",
    )
    review_cmd.add_argument(
        "--exclude-item",
        action="append",
        default=[],
        help="Explicitly exclude a review item ID from the generated selection. May be repeated.",
    )

    optimize_cmd = subparsers.add_parser("optimize", help="System maintenance planning.")
    optimize_cmd.add_argument("action", nargs="?", choices=("list", "plan", "run"), default="list")
    optimize_cmd.add_argument(
        "--execute",
        action="store_true",
        help="Reserved for future maintenance execution; current tasks remain dry-run.",
    )

    status_cmd = subparsers.add_parser("status", help="Read-only system health snapshots.")
    status_cmd.add_argument("action", nargs="?", choices=("snapshot",), default="snapshot")

    completion_cmd = subparsers.add_parser(
        "completion",
        help='Generate shell completion script. Usage: eval "$(cleanmac completion bash)"',
    )
    completion_cmd.add_argument(
        "shell",
        nargs="?",
        choices=("bash", "zsh", "fish"),
        default="bash",
        help="Target shell type (bash|zsh|fish). Default: bash",
    )

    ai_tools_cmd = subparsers.add_parser(
        "ai-tools",
        help="Emit AI tool definitions in OpenAI, Anthropic, or MCP format.",
    )
    ai_tools_cmd.add_argument(
        "--format",
        choices=("openai", "anthropic", "mcp", "all"),
        default="all",
        help="Output format. all = both OpenAI functions and Anthropic tools. (default: all)",
    )
    subparsers.add_parser(
        "ai-readiness",
        help="Emit AI host readiness, provider export parity, and MCP integration status.",
    )
    subparsers.add_parser(
        "ai-runbook",
        help="Emit AI host workflow phases, safe tool order, and execution gate requirements.",
    )
    subparsers.add_parser(
        "ai-self-test",
        help="Run AI host integration self-checks without deleting files.",
    )
    subparsers.add_parser(
        "ai-decision-matrix",
        help="Emit per-tool AI host decision metadata and MCP annotations.",
    )
    subparsers.add_parser(
        "ai-governance-advice",
        help="Emit governance advice for safe large-model cleanmac tool calling.",
    )
    subparsers.add_parser(
        "ai-host-policy",
        help="Emit machine-readable allow/deny policy for AI Host cleanmac tool calling.",
    )
    subparsers.add_parser(
        "ai-host-integration-pack",
        help="Emit one-stop AI Host integration metadata, policy, schemas, eval, and samples.",
    )
    subparsers.add_parser(
        "ai-host-preflight",
        help="Emit runtime AI Host preflight gate status before tool orchestration.",
    )
    subparsers.add_parser(
        "ai-host-evidence",
        help="Emit auditable AI Host runtime governance evidence pack.",
    )
    subparsers.add_parser(
        "mcp-surface-audit",
        help="Emit read-only MCP surface readiness and safety audit.",
    )
    release_readiness_parser = subparsers.add_parser(
        "release-readiness",
        help="Emit AI Host release readiness gates, evidence status, and review checklist.",
    )
    release_readiness_parser.add_argument(
        "--dist-dir",
        type=Path,
        default=None,
        help="Override the distribution directory used for release artifact verification.",
    )
    release_readiness_parser.add_argument(
        "--assets-dir",
        type=Path,
        default=None,
        help="Override the release assets directory used for manifest verification.",
    )
    release_diagnostics_parser = subparsers.add_parser(
        "release-diagnostics",
        help="Emit release readiness diagnostics and recommended recovery commands.",
    )
    release_diagnostics_parser.add_argument(
        "--dist-dir",
        type=Path,
        default=None,
        help="Override the distribution directory used for release diagnostics.",
    )
    release_diagnostics_parser.add_argument(
        "--assets-dir",
        type=Path,
        default=None,
        help="Override the release assets directory used for diagnostics.",
    )
    release_evidence_parser = subparsers.add_parser(
        "release-evidence",
        help="Emit release evidence bundle tying artifacts, readiness, contracts, and AI Host evidence together.",
    )
    release_evidence_parser.add_argument(
        "--dist-dir",
        type=Path,
        default=None,
        help="Override the distribution directory used for release evidence.",
    )
    release_evidence_parser.add_argument(
        "--assets-dir",
        type=Path,
        default=None,
        help="Override the release assets directory used for evidence.",
    )
    release_operator_summary_parser = subparsers.add_parser(
        "release-operator-summary",
        help="Emit a compact release operator summary with first-fix commands.",
    )
    release_operator_summary_parser.add_argument(
        "--dist-dir",
        type=Path,
        default=None,
        help="Override the distribution directory used for the operator summary.",
    )
    release_operator_summary_parser.add_argument(
        "--assets-dir",
        type=Path,
        default=None,
        help="Override the release assets directory used for the operator summary.",
    )
    release_rehearsal_parser = subparsers.add_parser(
        "release-rehearsal",
        help="Emit a dry-run release rehearsal report for promotion evidence review.",
    )
    release_rehearsal_parser.add_argument(
        "--dist-dir",
        type=Path,
        default=None,
        help="Override the distribution directory used for release rehearsal.",
    )
    release_rehearsal_parser.add_argument(
        "--assets-dir",
        type=Path,
        default=None,
        help="Override the release assets directory used for release rehearsal.",
    )
    release_promotion_parser = subparsers.add_parser(
        "release-promotion-decision",
        help="Emit a fail-closed release promotion decision from rehearsal evidence.",
    )
    release_promotion_parser.add_argument(
        "--dist-dir",
        type=Path,
        default=None,
        help="Override the distribution directory used for promotion decision.",
    )
    release_promotion_parser.add_argument(
        "--assets-dir",
        type=Path,
        default=None,
        help="Override the release assets directory used for promotion decision.",
    )
    release_rollback_parser = subparsers.add_parser(
        "release-rollback-plan",
        help="Emit a manual-only release rollback plan for distribution surfaces.",
    )
    release_rollback_parser.add_argument(
        "--dist-dir",
        type=Path,
        default=None,
        help="Override the distribution directory used for rollback plan context.",
    )
    release_rollback_parser.add_argument(
        "--assets-dir",
        type=Path,
        default=None,
        help="Override the release assets directory used for rollback plan context.",
    )
    release_post_publish_parser = subparsers.add_parser(
        "release-post-publish-verification",
        help="Emit a manual-only post-publish verification plan for distribution surfaces.",
    )
    release_post_publish_parser.add_argument(
        "--dist-dir",
        type=Path,
        default=None,
        help="Override the distribution directory used for post-publish verification context.",
    )
    release_post_publish_parser.add_argument(
        "--assets-dir",
        type=Path,
        default=None,
        help="Override the release assets directory used for post-publish verification context.",
    )
    release_post_publish_result_parser = subparsers.add_parser(
        "release-post-publish-result",
        help="Emit manual-only post-publish verification closure evidence.",
    )
    release_post_publish_result_parser.add_argument(
        "--dist-dir",
        type=Path,
        default=None,
        help="Override the distribution directory used for post-publish result context.",
    )
    release_post_publish_result_parser.add_argument(
        "--assets-dir",
        type=Path,
        default=None,
        help="Override the release assets directory used for post-publish result context.",
    )
    release_post_publish_result_parser.add_argument(
        "--evidence-file",
        type=Path,
        default=None,
        help="Optional manual post-publish evidence JSON file used to mark surfaces verified or failed.",
    )
    release_post_publish_template_parser = subparsers.add_parser(
        "release-post-publish-evidence-template",
        help="Emit a manual-only post-publish evidence input template.",
    )
    release_post_publish_template_parser.add_argument(
        "--dist-dir",
        type=Path,
        default=None,
        help="Override the distribution directory used for post-publish evidence template context.",
    )
    release_post_publish_template_parser.add_argument(
        "--assets-dir",
        type=Path,
        default=None,
        help="Override the release assets directory used for post-publish evidence template context.",
    )
    subparsers.add_parser(
        "ai-schema-registry",
        help="Emit cleanmac AI schema inventory and compatibility policy.",
    )
    subparsers.add_parser(
        "ai-contract-samples",
        help="Emit sample payloads for critical cleanmac AI contract schemas.",
    )
    ai_validate_contract_cmd = subparsers.add_parser(
        "ai-validate-contract",
        help="Validate a JSON payload against a registered cleanmac AI contract schema.",
    )
    ai_validate_contract_cmd.add_argument(
        "--schema",
        dest="schema_name",
        required=True,
        help="Schema name to validate, for example cleanmac.plan.v1.",
    )
    ai_validate_contract_cmd.add_argument(
        "--payload-file",
        required=True,
        help="Path to a JSON payload file to validate.",
    )
    subparsers.add_parser(
        "ai-eval-pack",
        help="Emit AI Host integration scenario definitions without running them.",
    )
    ai_eval_run_cmd = subparsers.add_parser(
        "ai-eval-run",
        help="Run safe sandbox AI Host integration scenarios and emit a trace summary.",
    )
    ai_eval_run_cmd.add_argument(
        "--scenario",
        default="smoke",
        help="AI eval scenario set to run. Default: smoke",
    )
    ai_eval_run_cmd.add_argument(
        "--trace-file",
        default=None,
        help="Optional path to persist a redacted AI eval trace as JSONL.",
    )

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
        "policy-simulate",
        "analyze-tree",
        "diagnose",
        "workflow",
        "ai-workflow",
        "open",
        "links",
        "clean",
        "software",
        "startup",
        "privacy",
        "optimize",
        "status",
        "completion",
        "ai-tools",
        "ai-readiness",
        "ai-runbook",
        "ai-self-test",
        "ai-decision-matrix",
        "ai-governance-advice",
        "ai-host-policy",
        "ai-host-integration-pack",
        "ai-host-preflight",
        "ai-host-evidence",
        "mcp-surface-audit",
        "release-readiness",
        "release-diagnostics",
        "release-evidence",
        "release-operator-summary",
        "release-rehearsal",
        "release-promotion-decision",
        "release-rollback-plan",
        "release-post-publish-verification",
        "release-post-publish-result",
        "release-post-publish-evidence-template",
        "ai-schema-registry",
        "ai-contract-samples",
        "ai-validate-contract",
        "ai-eval-pack",
        "ai-eval-run",
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
    parser.add_argument(
        "--profile",
        choices=profile_names(),
        help="Use a built-in cleanup profile to select categories and conservative defaults.",
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


def parse_iso_datetime(value: object) -> datetime | None:
    if not isinstance(value, str) or not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def path_fingerprint(path: Path | str) -> dict[str, Any]:
    candidate = Path(path).expanduser()
    base: dict[str, Any] = {"path": display_path(candidate), "exists": False}
    try:
        stat = candidate.lstat()
    except OSError as exc:
        base["error"] = str(exc)
        return base
    base.update(
        {
            "exists": True,
            "is_dir": candidate.is_dir(),
            "is_file": candidate.is_file(),
            "is_symlink": candidate.is_symlink(),
            "size_bytes": path_size_bytes(candidate) if candidate.exists() else 0,
            "mtime_ns": stat.st_mtime_ns,
        }
    )
    if candidate.is_symlink():
        try:
            base["symlink_target"] = os.readlink(candidate)
        except OSError as exc:
            base["symlink_target_error"] = str(exc)
    return base


def candidate_fingerprints(rows: Sequence[dict[str, Any]]) -> list[dict[str, Any]]:
    return [path_fingerprint(str(row["path"])) for row in rows if row.get("path")]


def compare_candidate_fingerprints(expected: Sequence[dict[str, Any]]) -> list[dict[str, Any]]:
    drift: list[dict[str, Any]] = []
    for row in expected:
        path = str(row.get("path") or "")
        if not path:
            continue
        current = path_fingerprint(path)
        changed_fields = [
            field
            for field in ("exists", "is_dir", "is_file", "is_symlink", "size_bytes", "mtime_ns", "symlink_target")
            if row.get(field) != current.get(field)
        ]
        if changed_fields:
            drift.append(
                {
                    "path": path,
                    "changed_fields": changed_fields,
                    "expected": {field: row.get(field) for field in changed_fields},
                    "actual": {field: current.get(field) for field in changed_fields},
                }
            )
    return drift


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
    if getattr(args, "profile", None):
        requested = [str(key) for key in PROFILES[str(args.profile)]["categories"]]
        unknown = [key for key in requested if key not in CATEGORY_BY_KEY]
        if unknown:
            valid = ", ".join(category.key for category in CATEGORIES)
            raise SystemExit(
                f"Profile {args.profile} references unknown category: {', '.join(unknown)}. Valid categories: {valid}"
            )
        return [CATEGORY_BY_KEY[key] for key in requested]
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
    schema_negotiation = negotiate_plan_schema(plan, allow_legacy_missing=True)

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
        "source_schema": str(plan.get("schema")) if isinstance(plan.get("schema"), str) else "",
        "schema_negotiation": schema_negotiation,
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
        "ai_origin": plan.get("ai_origin") is True,
        "generated_at": str(plan.get("generated_at")) if isinstance(plan.get("generated_at"), str) else None,
        "expires_at": str(plan.get("expires_at")) if isinstance(plan.get("expires_at"), str) else None,
        "plan_max_age_seconds": plan.get("plan_max_age_seconds")
        if isinstance(plan.get("plan_max_age_seconds"), int)
        else None,
        "candidate_fingerprints": plan.get("candidate_fingerprints")
        if isinstance(plan.get("candidate_fingerprints"), list)
        else [],
    }


def ensure_supported_plan_schema(plan: dict[str, Any]) -> None:
    schema_negotiation = plan.get("schema_negotiation")
    if not isinstance(schema_negotiation, dict) or schema_negotiation.get("accepted") is not True:
        schema = "" if not isinstance(schema_negotiation, dict) else str(schema_negotiation.get("schema") or "")
        reason = (
            "missing-schema-negotiation"
            if not isinstance(schema_negotiation, dict)
            else str(schema_negotiation.get("reason") or "unknown")
        )
        raise SystemExit(f"Unsupported plan schema {schema or '<missing>'}: {reason}")


def plan_schema_warnings(schema_negotiation: dict[str, Any]) -> list[dict[str, str]]:
    if schema_negotiation.get("accepted") is not True or schema_negotiation.get("legacy") is not True:
        return []
    schema = str(schema_negotiation.get("schema") or "")
    latest = str(schema_negotiation.get("latest_supported_schema") or "cleanmac.plan.v1")
    if schema:
        message = f"Plan schema {schema} is supported for compatibility; {latest} is preferred."
    else:
        message = f"Plan file has no schema field and is accepted as legacy; {latest} is preferred."
    return [{"code": "LEGACY_PLAN_SCHEMA", "schema": schema, "message": message}]


def apply_clean_plan_defaults(args: argparse.Namespace) -> dict[str, Any] | None:
    if getattr(args, "command", None) != "clean" or not getattr(args, "plan_file", None):
        return None
    plan = load_clean_plan(args.plan_file)
    ensure_supported_plan_schema(plan)
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


def review_selection_constraints(plan_file: str | None, selection_file: str | None) -> dict[str, Any] | None:
    if not selection_file:
        return None
    if not plan_file:
        raise SystemExit("--review-selection-file requires --plan-file.")
    source_payload = load_json_file(plan_file)
    selection_payload = load_json_file(selection_file)
    validation = validate_review_selection(source_payload, selection_payload)
    if not validation["valid"]:
        reasons = ", ".join(str(reason) for reason in validation["blocked_reasons"])
        raise SystemExit(f"Review selection is invalid for this plan: {reasons}")
    selected_ids = {str(item) for item in selection_payload.get("selected_item_ids", []) if item is not None}
    selected_paths = [
        str(item["path"])
        for item in normalize_review_items(source_payload)
        if str(item.get("id")) in selected_ids and item.get("path")
    ]
    return {
        "schema": "cleanmac.review-selection-constraint.v1",
        "selection_file": display_path(Path(selection_file).expanduser().resolve(strict=False)),
        "source_plan_file": display_path(Path(plan_file).expanduser().resolve(strict=False)),
        "source_fingerprint": validation["source_fingerprint"],
        "selected_item_ids": [str(item) for item in selection_payload.get("selected_item_ids", []) if item is not None],
        "selected_paths": selected_paths,
        "selected_count": len(selected_paths),
        "validation": validation,
    }


def render_plan_freshness_report(plan: dict[str, Any], *, now: datetime | None = None) -> dict[str, Any]:
    now = now or datetime.now(timezone.utc)
    generated_at = parse_iso_datetime(plan.get("generated_at"))
    expires_at = parse_iso_datetime(plan.get("expires_at"))
    max_age_seconds = plan.get("plan_max_age_seconds") or PLAN_MAX_AGE_SECONDS
    age_seconds = None if generated_at is None else max((now - generated_at).total_seconds(), 0)
    stale_reasons: list[str] = []
    if generated_at is None:
        stale_reasons.append("missing-generated-at")
    elif age_seconds is not None and age_seconds > float(max_age_seconds):
        stale_reasons.append("plan-age-exceeded")
    if expires_at is not None and now > expires_at:
        stale_reasons.append("plan-expired")
    fingerprints = [row for row in plan.get("candidate_fingerprints", []) if isinstance(row, dict)]
    drift = compare_candidate_fingerprints(fingerprints) if fingerprints else []
    return {
        "schema": "cleanmac.plan-freshness.v1",
        "fresh": not stale_reasons and not drift,
        "generated_at": plan.get("generated_at"),
        "expires_at": plan.get("expires_at"),
        "age_seconds": age_seconds,
        "max_age_seconds": max_age_seconds,
        "stale_reasons": stale_reasons,
        "drift_count": len(drift),
        "drift": drift,
        "fingerprint_count": len(fingerprints),
        "suggested_next_action": "continue"
        if not stale_reasons and not drift
        else "regenerate_plan_and_repeat_dry_run",
    }


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


def render_capabilities() -> dict[str, Any]:
    ai_tool_contract = render_ai_tool_contract()
    runtime_lifecycle = render_runtime_lifecycle_policy()
    return {
        "schema": "cleanmac.capabilities.v1",
        "name": "cleanmac",
        "destructive": False,
        "model": "AI-first ephemeral CLI with dry-run defaults, sandbox remapping, reusable plans, filters, and execution budgets.",
        "runtime_lifecycle": runtime_lifecycle,
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
            "startup",
            "privacy",
            "permissions",
            "tool-plan",
            "tool-execute",
            "review",
            "optimize",
            "status",
            "completion",
            "ai-tools",
            "ai-readiness",
            "ai-runbook",
            "ai-self-test",
            "ai-decision-matrix",
            "ai-governance-advice",
            "ai-host-policy",
            "ai-host-integration-pack",
            "ai-host-preflight",
            "ai-host-evidence",
            "release-readiness",
            "ai-schema-registry",
            "ai-eval-pack",
            "ai-eval-run",
        ],
        "command_groups": COMMAND_GROUPS,
        "preferred_command_style": "grouped",
        "flat_command_compatibility": True,
        "safety_guardrails": {
            "dry_run_default": True,
            "zero_resident_footprint": runtime_lifecycle,
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
            "html_audit_report_flag": "--report-file <path> --report-format html",
            "permissions_preflight_command": "permissions",
            "tool_semantic_plan_command": "tool-plan",
            "tool_controlled_execution_command": "tool-execute",
            "review_selection_command": "review",
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
                "supported_artifacts": ["wheel", "sdist", "standalone-zipapp", "homebrew-formula"],
                "release_manifest": "release-assets/ARTIFACT-MANIFEST.json",
                "homebrew_formula_policy": {
                    "status": "tap-publishable",
                    "tap": "cleanmac/tap",
                    "formula_path": "Formula/cleanmac.rb",
                    "formula_asset": "release-assets/cleanmac.rb",
                    "publish_automatically": False,
                    "recommended_install_method": "brew tap cleanmac/tap && brew install cleanmac",
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
        "ai_tool_contract": ai_tool_contract,
        "ai_error_taxonomy": render_ai_error_taxonomy(),
        "llm_invocation_guide": render_llm_invocation_guide(),
        "prompt_injection_policy": render_prompt_injection_policy(),
        "plan_policy": render_plan_policy(),
        "ai_recommended_workflow": render_ai_recommended_workflow(),
        "ai_intent_hints": render_ai_intent_hints(),
        "ai_function_schemas": ai_schema.render_function_schemas(),
        "ai_openai_functions": ai_schema.render_openai_functions(),
        "ai_anthropic_tools": ai_schema.render_anthropic_tools(),
        "mcp_tool_catalog": ai_schema.render_mcp_tool_catalog(),
        "ai_provider_export_parity": ai_schema.render_provider_export_parity(),
        "ai_schema_validation": ai_schema.validate_ai_tool_definitions(),
        "ai_contract_compatibility": ai_schema.render_contract_compatibility(ai_tool_contract),
        "ai_runbook": render_ai_runbook(),
        "ai_decision_matrix": render_ai_decision_matrix(),
        "ai_governance_advice": render_ai_governance_advice_report(),
        "ai_host_policy": render_ai_host_policy_report(),
        "ai_host_integration_pack": render_ai_host_integration_pack_report(),
        "ai_host_preflight": render_ai_host_preflight_report(),
        "ai_host_evidence": render_ai_host_evidence_report(),
        "release_readiness": render_release_readiness_report(),
        "ai_schema_registry": render_ai_schema_registry(),
        "ai_eval_pack": render_ai_eval_pack(),
        "ai_self_test": render_ai_self_test(),
        "ai_readiness": render_ai_readiness(
            ai_tool_contract,
            release_readiness=render_runtime_release_readiness_summary(),
        ),
    }


def render_ai_decision_matrix() -> dict[str, Any]:
    return render_ai_tool_decision_matrix(ai_schema.AI_TOOL_DEFINITIONS, render_ai_runbook())


def render_release_readiness_summary(report: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "schema": report.get("schema"),
        "ready": bool(report.get("ready")),
        "failed_gate_ids": list(report.get("failed_gate_ids", [])),
        "readiness_score": dict(report.get("readiness_score", {})),
        "required_for": "release-review",
        "not_required_for": "runtime-readonly-ai-host-discovery",
    }


def render_runtime_release_readiness_summary() -> dict[str, Any]:
    contract_validation = render_ai_contract_validation_summary()
    contract_validation["ready"] = bool(contract_validation.get("valid"))
    return render_release_readiness_summary(
        render_release_readiness(
            ai_host_integration_pack={"schema": "cleanmac.ai-host-integration-pack.v1", "ready": True},
            ai_host_preflight={"schema": "cleanmac.ai-host-preflight.v1", "ready": True},
            ai_host_evidence={"schema": "cleanmac.ai-host-evidence.v1", "ready": True},
            mcp_surface_audit=render_mcp_surface_audit(),
            contract_validation=contract_validation,
            eval_smoke=render_ai_eval_smoke_evidence(),
            release_manifest=render_release_manifest_evidence(),
            required_make_targets=[
                "quality-check",
                "governed-execution-smoke",
                "ai-contract-smoke",
                "mcp-smoke",
                "mcp-surface-audit-smoke",
                "ai-host-smoke",
                "release-artifacts-smoke",
            ],
        )
    )


def render_ai_governance_advice_report() -> dict[str, Any]:
    runbook = render_ai_runbook()
    decision_matrix = render_ai_decision_matrix()
    eval_pack = render_ai_eval_pack()
    return render_ai_governance_advice(
        readiness=render_ai_readiness(
            render_ai_tool_contract(),
            release_readiness=render_runtime_release_readiness_summary(),
        ),
        runbook=runbook,
        decision_matrix=decision_matrix,
        eval_pack=eval_pack,
    )


def render_ai_host_policy_report() -> dict[str, Any]:
    decision_matrix = render_ai_decision_matrix()
    governance_advice = render_ai_governance_advice_report()
    return render_ai_host_policy(
        decision_matrix=decision_matrix,
        governance_advice=governance_advice,
        runtime_lifecycle=render_runtime_lifecycle_policy(),
    )


def render_ai_host_integration_pack_report() -> dict[str, Any]:
    release_readiness = render_runtime_release_readiness_summary()
    readiness = render_ai_readiness(render_ai_tool_contract(), release_readiness=release_readiness)
    runbook = render_ai_runbook()
    decision_matrix = render_ai_decision_matrix()
    governance_advice = render_ai_governance_advice_report()
    runtime_lifecycle = render_runtime_lifecycle_policy()
    host_policy = render_ai_host_policy(
        decision_matrix=decision_matrix,
        governance_advice=governance_advice,
        runtime_lifecycle=runtime_lifecycle,
    )
    return render_ai_host_integration_pack(
        readiness=readiness,
        release_readiness=release_readiness,
        runbook=runbook,
        decision_matrix=decision_matrix,
        governance_advice=governance_advice,
        host_policy=host_policy,
        runtime_lifecycle=runtime_lifecycle,
        schema_registry=render_ai_schema_registry(),
        eval_pack=render_ai_eval_pack(),
        contract_validation=render_ai_contract_validation_summary(),
        contract_samples=render_ai_contract_samples(),
        critical_schemas=AI_HOST_CRITICAL_SCHEMAS,
    )


def render_ai_host_preflight_report() -> dict[str, Any]:
    return render_ai_host_preflight(
        integration_pack=render_ai_host_integration_pack_report(),
        runtime_policy_schema_registered="cleanmac.runtime-lifecycle-policy.v1" in AI_HOST_CRITICAL_SCHEMAS,
    )


def render_ai_host_evidence_report() -> dict[str, Any]:
    raw_denial = evaluate_ai_host_tool_call(
        tool={"name": "cleanmac_capabilities", "risk": "readonly", "auto_call_allowed": True},
        arguments={"raw_command": "rm -rf /"},
        source="ai-host-evidence.raw-command-sample",
    )
    destructive_denial = evaluate_ai_host_tool_call(
        tool={
            "name": "cleanmac_execute_plan",
            "risk": "destructive",
            "auto_call_allowed": False,
            "requires_confirmation": True,
        },
        arguments={"plan_file": "/tmp/cleanmac-plan.json"},
        source="ai-host-evidence.destructive-sample",
    )
    return render_ai_host_evidence(
        integration_pack=render_ai_host_integration_pack_report(),
        preflight=render_ai_host_preflight_report(),
        contract_validation=render_ai_contract_validation_summary(),
        release_readiness=render_runtime_release_readiness_summary(),
        runtime_lifecycle=render_runtime_lifecycle_policy(),
        runtime_policy_evidence=[
            {"id": "raw-command-argument-denied", "decision": raw_denial},
            {"id": "destructive-missing-confirmation-denied", "decision": destructive_denial},
        ],
        critical_schemas=AI_HOST_CRITICAL_SCHEMAS,
    )


def render_release_manifest_evidence(*, dist_dir: Path | None = None, assets_dir: Path | None = None) -> dict[str, Any]:
    project_root = Path(__file__).resolve().parent.parent
    resolved_dist_dir = dist_dir or project_root / "dist"
    resolved_assets_dir = assets_dir or project_root / "release-assets"
    manifest_path = resolved_assets_dir / "ARTIFACT-MANIFEST.json"
    if not manifest_path.is_file():
        return {
            "schema": "cleanmac.release-artifact-manifest.v1",
            "valid": False,
            "path": str(manifest_path),
            "dist_dir": str(resolved_dist_dir),
            "assets_dir": str(resolved_assets_dir),
            "error_code": "RELEASE_ARTIFACT_MANIFEST_MISSING",
            "error": "release artifact manifest is missing; run make release-artifacts-smoke before release review",
            "expected_assets": [str(resolved_assets_dir / name) for name in REQUIRED_RELEASE_ASSET_NAMES],
            "downloadable_asset_manifest": {
                "manifest": str(manifest_path),
                "sha256sums": str(resolved_assets_dir / "SHA256SUMS"),
                "sbom": str(resolved_assets_dir / "SBOM.json"),
                "homebrew_formula": str(resolved_assets_dir / "cleanmac.rb"),
                "dist_dir": str(resolved_dist_dir),
                "assets_dir": str(resolved_assets_dir),
            },
            "verification_commands": [
                ["make", "release-artifacts-smoke"],
                ["make", "release-readiness-smoke"],
                ["python3", "cleanmac.py", "--json", "release-evidence"],
            ],
            "publish_channels": [
                {"name": "GitHub Releases", "requires": ["ARTIFACT-MANIFEST.json", "SHA256SUMS", "SBOM.json"]},
                {"name": "Homebrew", "tap": HOMEBREW_TAP, "requires": ["cleanmac.rb", "SHA256SUMS"]},
                {"name": "PyPI", "requires": ["wheel", "sdist", "trusted-publishing"]},
            ],
        }
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        verify_release_artifact_manifest(
            manifest,
            dist_dir=resolved_dist_dir,
            assets_dir=resolved_assets_dir,
        )
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        return {
            "schema": "cleanmac.release-artifact-manifest.v1",
            "valid": False,
            "path": str(manifest_path),
            "dist_dir": str(resolved_dist_dir),
            "assets_dir": str(resolved_assets_dir),
            "error_code": "RELEASE_ARTIFACT_MANIFEST_INVALID",
            "error": str(exc),
        }
    manifest["valid"] = True
    manifest["path"] = str(manifest_path)
    manifest["dist_dir"] = str(resolved_dist_dir)
    manifest["assets_dir"] = str(resolved_assets_dir)
    return manifest


def render_ai_eval_smoke_evidence() -> dict[str, Any]:
    eval_pack = render_ai_eval_pack()
    return {
        "schema": "cleanmac.ai-eval-run.v1",
        "scenario": "smoke",
        "passed": bool(
            eval_pack.get("schema") == "cleanmac.ai-eval-pack.v1"
            and not eval_pack.get("uses_shell")
            and not eval_pack.get("allows_destructive_execution")
            and int(eval_pack.get("scenario_count") or 0) > 0
        ),
        "passed_count": int(eval_pack.get("scenario_count") or 0),
        "failed_count": 0,
        "evidence_source": "ai-eval-pack-static-smoke-readiness",
        "recommended_runner_command": eval_pack.get("recommended_runner_command"),
    }


def render_release_readiness_report(
    *,
    dist_dir: Path | None = None,
    assets_dir: Path | None = None,
) -> dict[str, Any]:
    contract_validation = render_ai_contract_validation_summary()
    contract_validation["ready"] = bool(contract_validation.get("valid"))
    required_make_targets = [
        "quality-check",
        "governed-execution-smoke",
        "ai-contract-smoke",
        "mcp-smoke",
        "mcp-surface-audit-smoke",
        "ai-host-smoke",
        "release-artifacts-smoke",
    ]
    return render_release_readiness(
        ai_host_integration_pack=render_ai_host_integration_pack_report(),
        ai_host_preflight=render_ai_host_preflight_report(),
        ai_host_evidence=render_ai_host_evidence_report(),
        mcp_surface_audit=render_mcp_surface_audit(),
        contract_validation=contract_validation,
        eval_smoke=render_ai_eval_smoke_evidence(),
        release_manifest=render_release_manifest_evidence(dist_dir=dist_dir, assets_dir=assets_dir),
        required_make_targets=required_make_targets,
    )


def _release_dirs(dist_dir: Path | None = None, assets_dir: Path | None = None) -> tuple[Path, Path]:
    project_root = Path(__file__).resolve().parent.parent
    return dist_dir or project_root / "dist", assets_dir or project_root / "release-assets"


def render_release_evidence_report(
    *,
    dist_dir: Path | None = None,
    assets_dir: Path | None = None,
) -> dict[str, Any]:
    resolved_dist_dir, resolved_assets_dir = _release_dirs(dist_dir=dist_dir, assets_dir=assets_dir)
    contract_validation = render_ai_contract_validation_summary()
    contract_validation["ready"] = bool(contract_validation.get("valid"))
    release_readiness = render_release_readiness_report(dist_dir=resolved_dist_dir, assets_dir=resolved_assets_dir)
    release_diagnostics = render_release_diagnostics_report(dist_dir=resolved_dist_dir, assets_dir=resolved_assets_dir)
    return build_release_evidence_bundle(
        dist_dir=resolved_dist_dir,
        assets_dir=resolved_assets_dir,
        release_readiness=release_readiness,
        release_diagnostics=release_diagnostics,
        contract_validation=contract_validation,
        ai_host_evidence=render_ai_host_evidence_report(),
        eval_smoke=render_ai_eval_smoke_evidence(),
        release_rehearsal=render_release_rehearsal_report(dist_dir=resolved_dist_dir, assets_dir=resolved_assets_dir),
        promotion_decision=render_release_promotion_decision_report(
            dist_dir=resolved_dist_dir, assets_dir=resolved_assets_dir
        ),
        rollback_plan=render_release_rollback_plan_report(dist_dir=resolved_dist_dir, assets_dir=resolved_assets_dir),
        post_publish_verification=render_release_post_publish_verification_report(
            dist_dir=resolved_dist_dir, assets_dir=resolved_assets_dir
        ),
        post_publish_result=render_release_post_publish_result_report(
            dist_dir=resolved_dist_dir, assets_dir=resolved_assets_dir
        ),
        post_publish_evidence_template=render_release_post_publish_evidence_template_report(
            dist_dir=resolved_dist_dir, assets_dir=resolved_assets_dir
        ),
    )


def render_release_diagnostics_report(
    *,
    dist_dir: Path | None = None,
    assets_dir: Path | None = None,
) -> dict[str, Any]:
    resolved_dist_dir, resolved_assets_dir = _release_dirs(dist_dir=dist_dir, assets_dir=assets_dir)
    readiness = render_release_readiness_report(dist_dir=resolved_dist_dir, assets_dir=resolved_assets_dir)
    manifest = render_release_manifest_evidence(dist_dir=resolved_dist_dir, assets_dir=resolved_assets_dir)
    failed_gates = [gate for gate in readiness.get("gates", []) if not gate.get("passed")]
    recommended_commands = [["make", "release-artifacts-smoke"], ["make", "release-readiness-smoke"]]
    recommended_commands.extend(
        list(action) for gate in failed_gates for action in gate.get("next_actions", []) if isinstance(action, list)
    )
    recommended_commands = [
        list(command) for command in dict.fromkeys(tuple(command) for command in recommended_commands)
    ]
    return {
        "schema": "cleanmac.release-diagnostics.v1",
        "destructive": False,
        "dry_run": True,
        "ready": bool(readiness.get("ready")),
        "failed_gate_ids": list(readiness.get("failed_gate_ids", [])),
        "environment": {
            "python_version": sys.version.split()[0],
            "platform": sys.platform,
            "test_mode": is_test_mode(),
        },
        "artifacts": {
            "dist_dir": str(resolved_dist_dir),
            "assets_dir": str(resolved_assets_dir),
            "manifest_present": Path(
                str(manifest.get("path", resolved_assets_dir / "ARTIFACT-MANIFEST.json"))
            ).is_file(),
            "manifest_valid": bool(manifest.get("valid")),
            "error_code": manifest.get("error_code"),
            "error": manifest.get("error"),
            "missing_files": ["ARTIFACT-MANIFEST.json"]
            if manifest.get("error_code") == "RELEASE_ARTIFACT_MANIFEST_MISSING"
            else [],
        },
        "readiness_summary": render_release_readiness_summary(readiness),
        "failed_gates": failed_gates,
        "recommended_commands": recommended_commands,
    }


def render_release_operator_summary(
    *,
    dist_dir: Path | None = None,
    assets_dir: Path | None = None,
) -> dict[str, Any]:
    readiness = render_release_readiness_report(dist_dir=dist_dir, assets_dir=assets_dir)
    failed_gates = [gate for gate in readiness.get("gates", []) if not gate.get("passed")]
    first_gate = failed_gates[0] if failed_gates else None
    return {
        "schema": "cleanmac.release-operator-summary.v1",
        "destructive": False,
        "dry_run": True,
        "status": "ready" if readiness.get("ready") else "blocked",
        "headline": "Release ready for governed publish"
        if readiness.get("ready")
        else f"Release blocked by {first_gate['id'] if first_gate else 'unknown gate'}",
        "failed_gate_count": len(failed_gates),
        "must_fix_first": []
        if first_gate is None
        else [
            {
                "gate_id": first_gate["id"],
                "blocking_code": first_gate.get("blocking_code"),
                "command": (first_gate.get("next_actions") or [["make", "release-readiness-smoke"]])[0],
            }
        ],
        "safe_copy_paste_commands": [["make", "release-readiness-smoke"], ["make", "release-check"]],
        "release_asset_checklist": [
            "SBOM.json",
            "SHA256SUMS",
            "ARTIFACT-MANIFEST.json",
            "RELEASE-READINESS.json",
            "RELEASE-EVIDENCE.json",
            "cleanmac.rb",
        ],
        "readiness_summary": render_release_readiness_summary(readiness),
    }


def render_release_rehearsal_report(
    *,
    dist_dir: Path | None = None,
    assets_dir: Path | None = None,
) -> dict[str, Any]:
    resolved_dist_dir, resolved_assets_dir = _release_dirs(dist_dir=dist_dir, assets_dir=assets_dir)
    return render_release_rehearsal(dist_dir=resolved_dist_dir, assets_dir=resolved_assets_dir)


def render_release_promotion_decision_report(
    *,
    dist_dir: Path | None = None,
    assets_dir: Path | None = None,
) -> dict[str, Any]:
    resolved_dist_dir, resolved_assets_dir = _release_dirs(dist_dir=dist_dir, assets_dir=assets_dir)
    return render_release_promotion_decision(dist_dir=resolved_dist_dir, assets_dir=resolved_assets_dir)


def render_release_rollback_plan_report(
    *,
    dist_dir: Path | None = None,
    assets_dir: Path | None = None,
) -> dict[str, Any]:
    resolved_dist_dir, resolved_assets_dir = _release_dirs(dist_dir=dist_dir, assets_dir=assets_dir)
    return render_release_rollback_plan(dist_dir=resolved_dist_dir, assets_dir=resolved_assets_dir)


def render_release_post_publish_verification_report(
    *,
    dist_dir: Path | None = None,
    assets_dir: Path | None = None,
) -> dict[str, Any]:
    resolved_dist_dir, resolved_assets_dir = _release_dirs(dist_dir=dist_dir, assets_dir=assets_dir)
    return render_release_post_publish_verification(dist_dir=resolved_dist_dir, assets_dir=resolved_assets_dir)


def render_release_post_publish_result_report(
    *,
    dist_dir: Path | None = None,
    assets_dir: Path | None = None,
    evidence_file: Path | None = None,
) -> dict[str, Any]:
    resolved_dist_dir, resolved_assets_dir = _release_dirs(dist_dir=dist_dir, assets_dir=assets_dir)
    return render_release_post_publish_result(
        dist_dir=resolved_dist_dir,
        assets_dir=resolved_assets_dir,
        evidence_file=evidence_file,
    )


def render_release_post_publish_evidence_template_report(
    *,
    dist_dir: Path | None = None,
    assets_dir: Path | None = None,
) -> dict[str, Any]:
    resolved_dist_dir, resolved_assets_dir = _release_dirs(dist_dir=dist_dir, assets_dir=assets_dir)
    return render_release_post_publish_evidence_template(dist_dir=resolved_dist_dir, assets_dir=resolved_assets_dir)


def render_ai_eval_unknown_scenario_error(message: str, argv: Sequence[str]) -> dict[str, Any]:
    return {
        "schema": "cleanmac.ai-error.v1",
        "ok": False,
        "destructive_operation_started": False,
        "safe_to_auto_retry": True,
        "argv": list(argv),
        "error": {
            "code": "AI_EVAL_UNKNOWN_SCENARIO",
            "category": "invalid_ai_eval_scenario",
            "retryable_after_fix": True,
            "safe_to_auto_retry": True,
            "message": message,
            "next_allowed_commands": ["ai-eval-pack", "ai-eval-run --scenario smoke"],
            "exit_code": 1,
        },
    }


def render_ai_contract_validation(schema_name: str, payload_file: str) -> dict[str, Any]:
    payload_path = Path(payload_file)
    try:
        payload = json.loads(payload_path.read_text(encoding="utf-8"))
    except OSError as exc:
        return {
            "schema": "cleanmac.ai-contract-validation.v1",
            "destructive": False,
            "dry_run": True,
            "valid": False,
            "target_schema": schema_name,
            "error_count": 1,
            "errors": [
                {
                    "code": "PAYLOAD_FILE_READ_FAILED",
                    "path": display_path(payload_path),
                    "message": str(exc),
                }
            ],
        }
    except json.JSONDecodeError as exc:
        return {
            "schema": "cleanmac.ai-contract-validation.v1",
            "destructive": False,
            "dry_run": True,
            "valid": False,
            "target_schema": schema_name,
            "error_count": 1,
            "errors": [
                {
                    "code": "PAYLOAD_INVALID_JSON",
                    "path": display_path(payload_path),
                    "message": str(exc),
                }
            ],
        }
    return validate_contract_payload(schema_name, payload)


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


def render_permissions_preflight(categories: list[Category], *, root: Path, home: Path) -> dict[str, Any]:
    live_root = root == Path("/")
    sudo_available = run_text_command(["sudo", "-n", "true"], timeout=1) is not None
    rows: list[dict[str, Any]] = []
    for category in categories:
        blockers: list[str] = []
        hints: list[str] = []
        if category.requires_privilege and not sudo_available and live_root:
            blockers.append("sudo-noninteractive-unavailable")
            hints.append(
                "Run a dry-run first, then rerun from a terminal with appropriate administrator privileges if required."
            )
        if category.full_disk_access and sys.platform == "darwin" and live_root:
            blockers.append("full-disk-access-may-be-required")
            hints.append("Grant Full Disk Access to the terminal or wrapper app before scanning protected user data.")
        if live_root:
            blockers.append("live-root-execute-requires-allow-live-root")
            hints.append("Destructive cleanup against '/' requires --allow-live-root after reviewing dry-run output.")
        resolved_paths = [remap_path(pattern, root=root, home=home) for pattern in category.paths]
        rows.append(
            {
                "key": category.key,
                "title": category.title,
                "risk": category.risk,
                "requires_privilege": category.requires_privilege,
                "full_disk_access": category.full_disk_access,
                "process_guard": category.process_guard,
                "provider": category.provider,
                "execute_ready": not any(reason != "live-root-execute-requires-allow-live-root" for reason in blockers),
                "blockers": blockers,
                "hints": hints,
                "paths": resolved_paths,
            }
        )
    blocked = [row for row in rows if row["blockers"]]
    return {
        "schema": "cleanmac.permissions-preflight.v1",
        "destructive": False,
        "dry_run": True,
        "root": display_path(root),
        "home": display_path(home),
        "platform": sys.platform,
        "live_root": live_root,
        "sudo_noninteractive": "available" if sudo_available else "not-available-or-needs-auth",
        "full_disk_access_probe": "manual" if sys.platform == "darwin" else "not-darwin",
        "category_count": len(rows),
        "blocked_or_needs_attention_count": len(blocked),
        "categories": rows,
        "recommended_next_action": "review_blockers_before_execute"
        if blocked
        else "safe_to_dry_run_selected_categories",
    }


def tool_plan_adapters() -> dict[str, dict[str, Any]]:
    from cleancli.tool_adapters import tool_adapters

    return tool_adapters()


def render_tool_plan(tool: str, *, root: Path, home: Path) -> dict[str, Any]:
    report = render_tool_adapter_plan(tool, root=root, home=home)
    report["root"] = display_path(root)
    report["home"] = display_path(home)
    return report


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


def path_interaction_metadata(path: Path) -> dict[str, Any]:
    path_text = display_path(path)
    absolute = path_text.startswith("/")
    open_command = ["open", path_text]
    reveal_command = ["open", "-R", path_text]
    return {
        "finder_url": f"file://{quote(path_text, safe='/')}" if absolute else None,
        "open_command": open_command,
        "open_command_text": shell_quote_command(open_command),
        "reveal_command": reveal_command,
        "reveal_command_text": shell_quote_command(reveal_command),
        "safe_to_open": not path.is_symlink(),
        "open_supported": sys.platform == "darwin",
    }


def skipped_row(category: str, parent: Path, entry: Path, reason: str) -> dict[str, Any]:
    size = path_size_bytes(entry)
    return {
        "category": category,
        "parent": display_path(parent),
        "path": display_path(entry),
        **path_interaction_metadata(entry),
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
                    **path_interaction_metadata(entry),
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
        "ai_summary": render_ai_summary(
            categories,
            phase="inspect",
            total_bytes=total_bytes,
            item_count=total_candidates,
            skipped_count=len(skipped),
            recommended_next_action="generate_plan" if total_candidates else "no_action",
        ),
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
        command_template(
            "software-uninstall-execute-reviewed-trash",
            [
                "python3",
                "cleanmac.py",
                "--json",
                "software",
                "execute",
                "--plan-file",
                "<PlanFile>",
                "--review-selection-file",
                "<SelectionFile>",
                "--delete-mode",
                "trash",
                "--execute",
                "--yes",
            ],
            destructive=True,
            safe_to_auto_execute=False,
            manual_review_required=True,
            placeholders=["PlanFile", "SelectionFile"],
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
            "safe_to_execute": False,
            "safe_to_auto_execute": False,
            "contains_destructive_templates": True,
            "destructive": True,
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
        "destructive_delete_rule": "destructive cleanup/delete templates must be argv-only governed cleanmac CLI invocations using clean run or software execute with --delete-mode trash, --execute, and --yes",
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


def is_cleanmac_software_execute_argv(argv: object) -> bool:
    if not isinstance(argv, list):
        return False
    parts = [str(part) for part in argv]
    try:
        software_index = parts.index("software")
    except ValueError:
        return False
    return software_index > 0 and software_index + 1 < len(parts) and parts[software_index + 1] == "execute"


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
    if not is_cleanmac_clean_run_argv(argv) and not is_cleanmac_software_execute_argv(argv):
        add_violation(
            location,
            template,
            "destructive-not-cleanmac-cli",
            "destructive cleanup templates must invoke a governed cleanmac destructive command",
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


def risk_rank(risk: str) -> int:
    return {"low": 1, "medium": 2, "high": 3, "critical": 4}.get(risk, 0)


def highest_risk(categories: Iterable[Category]) -> str:
    selected = list(categories)
    if not selected:
        return "low"
    return max((category.risk for category in selected), key=risk_rank)


def render_ai_summary(
    categories: list[Category],
    *,
    phase: str,
    total_bytes: int,
    item_count: int,
    skipped_count: int,
    recommended_next_action: str,
    delete_mode: str | None = None,
    operation_log: str | None = None,
    risk_policy: str = "default",
    max_delete_mb: float | None = None,
    max_items: int | None = None,
) -> dict[str, Any]:
    yes_required = categories_requiring_yes(categories, risk_policy)
    warnings = ai_confirmation_warnings(
        categories,
        yes_required=yes_required,
        delete_mode=delete_mode or "trash",
        max_delete_mb=max_delete_mb,
        max_items=max_items,
    )
    if delete_mode is None:
        warnings = [warning for warning in warnings if "Trash routing" not in warning]
    safe_after_confirmation = (
        phase == "clean-dry-run" and delete_mode == "trash" and max_delete_mb is not None and max_items is not None
    )
    reasons = [
        "cleanmac JSON reports are machine-readable for AI callers.",
        "Current phase does not grant automatic destructive execution.",
    ]
    if delete_mode == "trash":
        reasons.append("Trash mode is selected for recoverable cleanup after confirmation.")
    if operation_log:
        reasons.append("Operation log is configured for post-run auditability.")
    if skipped_count:
        reasons.append("Some candidates were skipped by filters or protection rules.")
    return {
        "schema": "cleanmac.ai-summary.v1",
        "phase": phase,
        "headline": f"{len(categories)} category/categories selected; {item_count} candidate item(s), {human_size(total_bytes)} estimated.",
        "recommended_next_action": recommended_next_action,
        "risk_level": highest_risk(categories),
        "safe_to_execute_after_confirmation": safe_after_confirmation,
        "selected_categories": [category.key for category in categories],
        "estimated_reclaimable_bytes": total_bytes,
        "estimated_reclaimable_human": human_size(total_bytes),
        "item_count": item_count,
        "skipped_count": skipped_count,
        "delete_mode": delete_mode,
        "operation_log": operation_log,
        "reasons": reasons,
        "warnings": warnings,
    }


def _append_flag_if_missing(argv: list[str], flag: str) -> None:
    if flag not in argv:
        argv.append(flag)


def _ensure_json_flag(argv: list[str]) -> None:
    if "--json" not in argv:
        argv.insert(1, "--json")


def _append_option_if_missing(argv: list[str], option: str, value: str) -> None:
    if option not in argv:
        argv.extend([option, value])


def _clean_execute_next_command(
    categories: list[Category],
    *,
    command_argv: Sequence[str],
    delete_mode: str,
    operation_log: str | None,
    confirmation_token_value: str,
    plan_file: str | None,
) -> list[str]:
    if command_argv:
        argv = ["cleanmac", *command_argv]
    else:
        argv = [
            "cleanmac",
            "--json",
            "clean",
            "run",
            "--categories",
            ",".join(category.key for category in categories),
            "--delete-mode",
            delete_mode,
        ]
    _ensure_json_flag(argv)
    _append_flag_if_missing(argv, "--execute")
    _append_flag_if_missing(argv, "--yes")
    if operation_log:
        _append_option_if_missing(argv, "--operation-log", operation_log)
    if plan_file:
        _append_flag_if_missing(argv, "--require-plan-context")
    _append_flag_if_missing(argv, "--require-confirmation-token")
    _append_option_if_missing(argv, "--confirmation-token", confirmation_token_value)
    return argv


def render_clean_human_summary(
    categories: list[Category],
    *,
    execute: bool,
    total_bytes: int,
    item_count: int,
    skipped_count: int,
    delete_mode: str,
    operation_log: str | None,
    confirmation_token_value: str,
    plan_file: str | None,
    command_argv: Sequence[str],
    warnings: Sequence[str],
) -> dict[str, Any]:
    category_keys = [category.key for category in categories]
    headline_phase = "Executed" if execute else "Dry-run found"
    reasons: list[str] = []
    if not execute:
        reasons.append("Dry-run only; destructive cleanup still requires human confirmation and --execute --yes.")
    if any(category.risk in {"high", "critical"} for category in categories):
        risky = ", ".join(category.key for category in categories if category.risk in {"high", "critical"})
        reasons.append(f"High-risk categories need review: {risky}.")
    if delete_mode == "trash":
        reasons.append("Trash routing is selected, so execute can remain recoverable if the user approves.")
    else:
        reasons.append("Trash routing is not selected; review delete mode before any execution.")
    if skipped_count:
        reasons.append(f"{skipped_count} item(s) were skipped by filters or protection rules.")
    reasons.extend(str(warning) for warning in warnings if warning)
    if item_count == 0:
        reasons.append("No candidate items were found.")
    next_command = []
    if not execute:
        next_command = _clean_execute_next_command(
            categories,
            command_argv=command_argv,
            delete_mode=delete_mode,
            operation_log=operation_log,
            confirmation_token_value=confirmation_token_value,
            plan_file=plan_file,
        )
    return {
        "schema": "cleanmac.human-summary.v1",
        "headline": (
            f"{headline_phase} {item_count} item(s) across {len(category_keys)} category/categories "
            f"for {human_size(total_bytes)}."
        ),
        "safe_to_execute": False,
        "top_reasons_to_review": reasons[:5],
        "next_command": next_command,
    }


def file_sha256(path: str | None) -> str | None:
    if not path:
        return None
    try:
        candidate = Path(path).expanduser().resolve(strict=False)
        if not candidate.is_file():
            return None
        return hashlib.sha256(candidate.read_bytes()).hexdigest()
    except OSError:
        return None


def ai_confirmation_token_context(
    categories: list[Category],
    *,
    root: Path,
    home: Path,
    risk_policy: str,
    max_delete_mb: float | None,
    max_items: int | None,
    include_patterns: Sequence[str],
    exclude_patterns: Sequence[str],
    older_than_days: float | None,
    min_size_mb: int,
    name_regex: str | None,
    bundle_allowlist: Sequence[str],
    bundle_blocklist: Sequence[str],
    delete_mode: str,
    plan_file: str | None,
    rows: Sequence[dict[str, Any]],
) -> dict[str, Any]:
    return {
        "schema": "cleanmac.ai-confirmation-token-context.v1",
        "root": display_path(root),
        "home": display_path(home),
        "selected_categories": [category.key for category in categories],
        "risk_policy": risk_policy,
        "max_delete_mb": max_delete_mb,
        "max_items": max_items,
        "include_patterns": list(include_patterns),
        "exclude_patterns": list(exclude_patterns),
        "older_than_days": older_than_days,
        "min_size_mb": min_size_mb,
        "name_regex": name_regex,
        "bundle_allowlist": list(bundle_allowlist),
        "bundle_blocklist": list(bundle_blocklist),
        "delete_mode": delete_mode,
        "plan_file": plan_file,
        "plan_sha256": file_sha256(plan_file),
        "candidate_count": len(rows),
        "candidate_bytes": sum(row_bytes(row) for row in rows),
        "candidates": [
            {
                "category": row.get("category"),
                "path": row.get("path"),
                "bytes": row.get("bytes"),
                "bundle_id": row.get("bundle_id"),
            }
            for row in rows
        ],
    }


def ai_confirmation_token(context: dict[str, Any]) -> str:
    payload = json.dumps(context, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return f"cleanmac-confirm-{hashlib.sha256(payload.encode('utf-8')).hexdigest()[:32]}"


def ai_confirmation_warnings(
    categories: Iterable[Category],
    *,
    yes_required: Sequence[Category],
    delete_mode: str,
    max_delete_mb: float | None,
    max_items: int | None,
) -> list[str]:
    warnings: list[str] = []
    yes_required_keys = [category.key for category in yes_required]
    if yes_required_keys:
        warnings.append(f"Categories requiring --yes before execution: {', '.join(yes_required_keys)}")
    high_risk_keys = [category.key for category in categories if category.risk in {"high", "critical"}]
    if high_risk_keys:
        warnings.append(f"High-risk categories selected: {', '.join(high_risk_keys)}")
    if delete_mode != "trash":
        warnings.append("Execution is not configured for Trash routing; AI callers should prefer --delete-mode trash.")
    if max_delete_mb is None:
        warnings.append("No --max-delete-mb budget is set.")
    if max_items is None:
        warnings.append("No --max-items budget is set.")
    return warnings


def render_ai_confirmation_summary(
    categories: list[Category],
    *,
    execute: bool,
    confirmation_token_context: dict[str, Any],
    confirmation_token_value: str,
    confirmation_token_validated: bool,
    delete_mode: str,
    operation_log: str | None,
    operation_log_path: str | None,
    total_bytes: int,
    rows: Sequence[dict[str, Any]],
    skipped: Sequence[dict[str, Any]],
    risk_policy: str,
    max_delete_mb: float | None,
    max_items: int | None,
    pre_report: dict[str, Any],
) -> dict[str, Any]:
    yes_required = categories_requiring_yes(categories, risk_policy)
    deleted_count = sum(1 for row in rows if row.get("deleted"))
    effective_operation_log = operation_log_path or operation_log
    return {
        "schema": "cleanmac.ai-confirmation-summary.v1",
        "requires_confirmation": not execute,
        "recommended_confirmation_phrase": ai_schema.CONFIRMATION_PHRASE,
        "confirmation_token": confirmation_token_value,
        "confirmation_token_embedded": confirmation_token_value,
        "confirmation_token_context": confirmation_token_context,
        "confirmation_token_validated": confirmation_token_validated,
        "recommended_next_action": "review_operation_log" if execute else "ask_user_confirmation",
        "safe_to_auto_execute": False,
        "delete_mode": delete_mode,
        "operation_log": effective_operation_log,
        "estimated_reclaimable_bytes": total_bytes,
        "estimated_reclaimable_human": human_size(total_bytes),
        "risk_level": highest_risk(categories),
        "risk_policy": risk_policy,
        "category_count": len(categories),
        "selected_categories": [category.key for category in categories],
        "item_count": len(rows),
        "deleted_count": deleted_count,
        "skipped_count": len(skipped),
        "yes_required_categories": [category.key for category in yes_required],
        "max_delete_mb": max_delete_mb,
        "max_items": max_items,
        "trash_recoverable": delete_mode == "trash",
        "protected_bundle_policy_active": bool(pre_report["summary"].get("bundle_blocklist")),
        "warnings": ai_confirmation_warnings(
            categories,
            yes_required=yes_required,
            delete_mode=delete_mode,
            max_delete_mb=max_delete_mb,
            max_items=max_items,
        ),
    }


def render_ai_execution_ledger(
    *,
    execute: bool,
    confirmation_token_context: dict[str, Any],
    confirmation_token_value: str,
    confirmation_token_required: bool,
    confirmation_token_validated: bool,
    operation_log: str | None,
    operation_log_path: str | None,
    operation_log_status: dict[str, Any],
    operation_session_id: str,
    operation_log_entry_count: int,
    delete_mode: str,
    require_plan_context: bool,
    ai_originated_plan: bool,
) -> dict[str, Any]:
    effective_operation_log = operation_log_path or operation_log
    operation_log_ready = operation_log_status.get("status") in {"ready", "not-needed"}
    plan_file = confirmation_token_context.get("plan_file")
    plan_sha256 = confirmation_token_context.get("plan_sha256")
    safe_chain_complete = bool(
        execute
        and delete_mode == "trash"
        and effective_operation_log
        and operation_log_status.get("status") == "ready"
        and confirmation_token_required
        and confirmation_token_validated
        and (not plan_file or require_plan_context)
    )
    return {
        "schema": "cleanmac.ai-execution-ledger.v1",
        "phase": "clean-execute" if execute else "clean-dry-run",
        "safe_chain_complete": safe_chain_complete,
        "plan": {
            "file": plan_file,
            "sha256": plan_sha256,
            "ai_originated": ai_originated_plan,
            "context_required": require_plan_context,
        },
        "confirmation": {
            "token_required": confirmation_token_required,
            "token_validated": confirmation_token_validated,
            "token": confirmation_token_value,
        },
        "operation_log": {
            "path": effective_operation_log,
            "status": operation_log_status.get("status"),
            "ready": operation_log_ready,
            "error": operation_log_status.get("error"),
            "rotated": operation_log_status.get("rotated", False),
            "entry_count": operation_log_entry_count,
            "session_id": operation_session_id,
        },
        "execution": {
            "delete_mode": delete_mode,
            "destructive": execute,
            "trash_recoverable": delete_mode == "trash",
        },
    }


def delete_failure_reason(exc: Exception) -> str:
    text = str(exc)
    if isinstance(exc, PermissionError) or "Operation not permitted" in text or "Lacking write permission" in text:
        return "permission-denied"
    if "symlink" in text.lower():
        return "symlink-protected"
    if "protected" in text.lower() or "Refusing to delete" in text:
        return "protected-path"
    if "Trash" in text or "trash" in text:
        return "trash-routing-failed"
    return "delete-failed"


def operation_log_entry(
    *,
    session_id: str,
    command_text: str,
    action: str,
    row: dict[str, Any],
    delete_mode: str,
    root: Path,
    home: Path,
    ai_operation_audit: dict[str, Any],
) -> dict[str, Any]:
    return {
        "schema": "cleanmac.operation-log-entry.v1",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "session_id": session_id,
        "command": command_text,
        "action": action,
        "category": row["category"],
        "path": row["path"],
        "bytes": row["bytes"],
        "human": row["human"],
        "bundle_id": row.get("bundle_id"),
        "delete_mode": delete_mode,
        "trash_path": row.get("trash_path"),
        "deleted": bool(row.get("deleted")),
        "status": row.get("status", action),
        "reason": row.get("reason"),
        "error": row.get("error"),
        "root": display_path(root),
        "home": display_path(home),
        "ai": dict(ai_operation_audit),
    }


def review_selection_audit(review_selection: dict[str, Any] | None) -> dict[str, Any] | None:
    if not isinstance(review_selection, dict):
        return None
    return {
        "schema": "cleanmac.operation-log-review-selection.v1",
        "selection_file": review_selection.get("selection_file"),
        "source_plan_file": review_selection.get("source_plan_file"),
        "source_fingerprint": review_selection.get("source_fingerprint"),
        "selected_count": review_selection.get("selected_count"),
        "selected_item_ids": list(review_selection.get("selected_item_ids", [])),
        "validation_valid": review_selection.get("validation", {}).get("valid")
        if isinstance(review_selection.get("validation"), dict)
        else None,
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
    fail_fast: bool = False,
    bundle_allowlist: Sequence[str] = (),
    bundle_blocklist: Sequence[str] = (),
    delete_mode: str = "permanent",
    operation_log: str | None = OPERATIONS_LOG_FILE,
    confirmation_token: str | None = None,
    require_confirmation_token: bool = False,
    require_plan_context: bool = False,
    ai_originated_plan: bool = False,
    review_selection: dict[str, Any] | None = None,
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
    review_selected_paths = (
        {str(path) for path in review_selection.get("selected_paths", [])}
        if isinstance(review_selection, dict)
        else None
    )
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
            display_entry = display_path(entry)
            if review_selected_paths is not None and display_entry not in review_selected_paths:
                skipped_item = skipped_row(target.category, target.path, entry, "not-in-review-selection")
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
                    "path": display_entry,
                    **path_interaction_metadata(entry),
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
        "fail_fast": fail_fast,
        "skipped_count": len(skipped),
        "max_items": max_items,
        "within_max_items": max_items is None or len(rows) <= max_items,
        "delete_mode": delete_mode,
        "operation_log": operation_log,
        "confirmation_token_required": require_confirmation_token,
        "review_selection_applied": review_selection is not None,
        "bundle_allowlist": list(bundle_allowlist),
        "bundle_blocklist": list(bundle_blocklist),
    }
    confirmation_context = ai_confirmation_token_context(
        categories,
        root=root,
        home=home,
        risk_policy=risk_policy,
        max_delete_mb=max_delete_mb,
        max_items=max_items,
        include_patterns=include_patterns,
        exclude_patterns=exclude_patterns,
        older_than_days=older_than_days,
        min_size_mb=min_size_mb,
        name_regex=name_regex,
        bundle_allowlist=bundle_allowlist,
        bundle_blocklist=bundle_blocklist,
        delete_mode=delete_mode,
        plan_file=plan_file,
        rows=rows,
    )
    expected_confirmation_token = ai_confirmation_token(confirmation_context)
    confirmation_token_validated = False
    operation_log_entries: list[dict[str, Any]] = []
    command_text = shlex.join(["cleanmac.py", *command_argv]) if command_argv else "cleanmac.py clean run"
    ai_operation_audit = {
        "schema": "cleanmac.operation-log-ai-audit.v1",
        "originated_plan": ai_originated_plan,
        "plan_file": confirmation_context.get("plan_file"),
        "plan_sha256": confirmation_context.get("plan_sha256"),
        "require_plan_context": require_plan_context,
        "confirmation_token_required": require_confirmation_token,
        "confirmation_token_validated": False,
        "review_selection": review_selection_audit(review_selection),
    }
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
                    "ai": dict(ai_operation_audit),
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
    if execute and (require_confirmation_token or confirmation_token):
        if not confirmation_token:
            raise SystemExit("Refusing to execute cleanup because confirmation token is required.")
        if confirmation_token != expected_confirmation_token:
            raise SystemExit("Refusing to execute cleanup because confirmation token mismatch.")
        confirmation_token_validated = True
    ai_operation_audit["confirmation_token_validated"] = confirmation_token_validated
    for log_entry in operation_log_entries:
        log_entry["ai"] = dict(ai_operation_audit)
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
                row["reason"] = delete_failure_reason(exc)
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
                operation_log_entries.append(
                    operation_log_entry(
                        session_id=session_id,
                        command_text=command_text,
                        action="failed",
                        row=row,
                        delete_mode=delete_mode,
                        root=root,
                        home=home,
                        ai_operation_audit=ai_operation_audit,
                    )
                )
                if fail_fast or row["reason"] in {"protected-path", "symlink-protected"}:
                    raise
                continue
            operation_log_entries.append(
                operation_log_entry(
                    session_id=session_id,
                    command_text=command_text,
                    action="delete",
                    row=row,
                    delete_mode=delete_mode,
                    root=root,
                    home=home,
                    ai_operation_audit=ai_operation_audit,
                )
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
    ai_confirmation_summary = render_ai_confirmation_summary(
        categories,
        execute=execute,
        confirmation_token_context=confirmation_context,
        confirmation_token_value=expected_confirmation_token,
        confirmation_token_validated=confirmation_token_validated,
        delete_mode=delete_mode,
        operation_log=operation_log,
        operation_log_path=operation_log_path,
        total_bytes=candidate_bytes,
        rows=rows,
        skipped=skipped,
        risk_policy=risk_policy,
        max_delete_mb=max_delete_mb,
        max_items=max_items,
        pre_report=pre_report,
    )
    ai_execution_ledger = render_ai_execution_ledger(
        execute=execute,
        confirmation_token_context=confirmation_context,
        confirmation_token_value=expected_confirmation_token,
        confirmation_token_required=require_confirmation_token,
        confirmation_token_validated=confirmation_token_validated,
        operation_log=operation_log,
        operation_log_path=operation_log_path,
        operation_log_status=operation_log_status,
        operation_session_id=session_id,
        operation_log_entry_count=len(operation_log_entries),
        delete_mode=delete_mode,
        require_plan_context=require_plan_context,
        ai_originated_plan=ai_originated_plan,
    )
    ai_summary = render_ai_summary(
        categories,
        phase="clean-execute" if execute else "clean-dry-run",
        total_bytes=candidate_bytes,
        item_count=len(rows),
        skipped_count=len(skipped),
        recommended_next_action="review_operation_log" if execute else "ask_user_confirmation",
        delete_mode=delete_mode,
        operation_log=operation_log_path or operation_log,
        risk_policy=risk_policy,
        max_delete_mb=max_delete_mb,
        max_items=max_items,
    )
    human_summary = render_clean_human_summary(
        categories,
        execute=execute,
        total_bytes=candidate_bytes,
        item_count=len(rows),
        skipped_count=len(skipped),
        delete_mode=delete_mode,
        operation_log=operation_log_path or operation_log,
        confirmation_token_value=expected_confirmation_token,
        plan_file=plan_file,
        command_argv=command_argv,
        warnings=ai_confirmation_summary["warnings"],
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
        "review_selection": review_selection,
        "debug_elapsed_ms": elapsed_ms,
        "deletion_log": display_path(deletion_log_path_for_context(root=root, home=home)) if execute else None,
        "safety_gate": safety_gate,
        "selected_categories": [category_metadata(category) for category in categories],
        "pre_clean_report": pre_report,
        "post_clean_report": post_report,
        "ai_confirmation_summary": ai_confirmation_summary,
        "ai_execution_ledger": ai_execution_ledger,
        "ai_summary": ai_summary,
        "human_summary": human_summary,
        "total_bytes": candidate_bytes,
        "total_human": human_size(candidate_bytes),
        "by_category": rows_by_category(rows),
        "skipped_by_category": rows_by_category(skipped),
        "skipped_count": len(skipped),
        "deleted_count": sum(1 for row in rows if row.get("deleted")),
        "failed_count": sum(1 for row in rows if row.get("status") == "failed"),
        "failed_by_category": rows_by_category([row for row in rows if row.get("status") == "failed"]),
        "failed": [row for row in rows if row.get("status") == "failed"],
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
    ai_origin: bool = False,
) -> dict[str, Any]:
    category_keys = [category.key for category in categories]
    generated_at = datetime.now(timezone.utc)
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
    ai_summary = render_ai_summary(
        categories,
        phase="plan",
        total_bytes=pre_report["summary"]["estimated_reclaimable_bytes"],
        item_count=pre_report["summary"]["candidate_count"],
        skipped_count=0,
        recommended_next_action="dry_run_plan",
        risk_policy=risk_policy,
        max_delete_mb=max_delete_mb,
        max_items=max_items,
    )
    plan_candidates = pre_report["candidates"]
    confirmation_context = ai_confirmation_token_context(
        categories,
        root=root,
        home=home,
        risk_policy=risk_policy,
        max_delete_mb=max_delete_mb,
        max_items=max_items,
        include_patterns=include_patterns,
        exclude_patterns=exclude_patterns,
        older_than_days=older_than_days,
        min_size_mb=min_size_mb,
        name_regex=name_regex,
        bundle_allowlist=[],
        bundle_blocklist=DEFAULT_PROTECTED_BUNDLE_IDS,
        delete_mode="permanent",
        plan_file=None,
        rows=plan_candidates,
    )
    confirmation_token_value = ai_confirmation_token(confirmation_context)
    ai_confirmation_summary = render_ai_confirmation_summary(
        categories,
        execute=False,
        confirmation_token_context=confirmation_context,
        confirmation_token_value=confirmation_token_value,
        confirmation_token_validated=False,
        delete_mode="permanent",
        operation_log=None,
        operation_log_path=None,
        total_bytes=int(pre_report["summary"]["estimated_reclaimable_bytes"]),
        rows=plan_candidates,
        skipped=[],
        risk_policy=risk_policy,
        max_delete_mb=max_delete_mb,
        max_items=max_items,
        pre_report=pre_report,
    )
    return {
        "schema": "cleanmac.plan.v1",
        "destructive": False,
        "dry_run": True,
        "generated_at": generated_at.isoformat(),
        "expires_at": (generated_at + timedelta(seconds=PLAN_MAX_AGE_SECONDS)).isoformat(),
        "plan_max_age_seconds": PLAN_MAX_AGE_SECONDS,
        "ai_origin": ai_origin,
        "ai_summary": ai_summary,
        "ai_confirmation_summary": ai_confirmation_summary,
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
        "candidate_fingerprints": candidate_fingerprints(pre_report["candidates"]),
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
            interaction_metadata = path_interaction_metadata(path)
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
                    **interaction_metadata,
                    "manual_command": command,
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
    schema_negotiation = plan["schema_negotiation"]
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
        "valid": bool(schema_negotiation["accepted"] and not unknown),
        "plan": plan,
        "schema_negotiation": schema_negotiation,
        "schema_warnings": plan_schema_warnings(schema_negotiation),
        "unknown_categories": unknown,
        "context_warnings": context_warnings,
        "preview": preview,
        "budget_summary": budget_summary,
        "replay_clean_command": build_clean_command(
            [str(key) for key in plan["category_keys"] if str(key) in CATEGORY_BY_KEY], execute=False
        ),
        "execute_command_requires_review": True,
    }


def render_ai_policy_simulation(
    *,
    plan_file: str,
    root: Path,
    home: Path,
    execute: bool,
    delete_mode: str,
    operation_log: str | None,
    require_plan_context: bool,
    require_confirmation_token: bool,
    confirmation_token: str | None,
    review_selection_file: str | None,
    original_argv: Sequence[str],
) -> dict[str, Any]:
    plan = load_clean_plan(plan_file)
    ensure_supported_plan_schema(plan)
    context_warnings = []
    missing_requirements: list[str] = []
    blocking_reasons: list[dict[str, Any]] = []
    policy_decisions: list[dict[str, Any]] = []
    if plan.get("root") and not same_context_path(str(plan["root"]), root):
        context_warnings.append({"field": "root", "expected": plan["root"], "actual": display_path(root)})
    if plan.get("home") and not same_context_path(str(plan["home"]), home):
        context_warnings.append({"field": "home", "expected": plan["home"], "actual": display_path(home)})
    freshness = render_plan_freshness_report(plan)
    review_selection = review_selection_constraints(plan_file, review_selection_file) if review_selection_file else None
    if execute and plan.get("ai_origin"):
        checks = [
            ("ai_origin_requires_trash", delete_mode == "trash", "--delete-mode trash"),
            (
                "ai_origin_requires_operation_log",
                "--operation-log" in original_argv and bool(operation_log),
                "--operation-log",
            ),
            (
                "ai_origin_requires_confirmation_token",
                require_confirmation_token and bool(confirmation_token),
                "--require-confirmation-token with --confirmation-token",
            ),
            ("ai_origin_requires_plan_context", require_plan_context, "--require-plan-context"),
        ]
        for rule, passed, requirement in checks:
            policy_decisions.append({"rule": rule, "result": "pass" if passed else "fail"})
            if not passed:
                missing_requirements.append(requirement)
                blocking_reasons.append(
                    {
                        "code": rule.upper(),
                        "severity": "error",
                        "requirement": requirement,
                        "safe_to_auto_fix": rule
                        in {
                            "ai_origin_requires_trash",
                            "ai_origin_requires_plan_context",
                            "ai_origin_requires_operation_log",
                        },
                        "suggested_fix": requirement,
                    }
                )
    if execute and context_warnings:
        missing_requirements.append("matching root/home plan context")
        blocking_reasons.append(
            {
                "code": "PLAN_CONTEXT_MISMATCH",
                "severity": "error",
                "requirement": "matching root/home plan context",
                "safe_to_auto_fix": False,
                "suggested_fix": "regenerate_plan_for_current_root_home_context",
            }
        )
        policy_decisions.append({"rule": "plan_context_matches", "result": "fail"})
    elif execute:
        policy_decisions.append({"rule": "plan_context_matches", "result": "pass"})
    if execute and not freshness["fresh"]:
        missing_requirements.append("fresh non-drifted plan")
        blocking_reasons.append(
            {
                "code": "PLAN_STALE_OR_DRIFTED",
                "severity": "error",
                "requirement": "fresh non-drifted plan",
                "safe_to_auto_fix": False,
                "suggested_fix": "regenerate_plan_and_repeat_dry_run",
            }
        )
        policy_decisions.append({"rule": "plan_freshness", "result": "fail"})
    else:
        policy_decisions.append({"rule": "plan_freshness", "result": "pass"})
    if review_selection_file:
        policy_decisions.append({"rule": "review_selection_valid", "result": "pass"})
    allowed = execute is False or not missing_requirements
    safe_argv = [
        "cleanmac",
        "--json",
        "clean",
        "run",
        "--plan-file",
        plan_file,
        "--require-plan-context",
        "--delete-mode",
        "trash",
    ]
    if review_selection_file:
        safe_argv.extend(["--review-selection-file", review_selection_file])
    if execute:
        safe_argv.extend(
            [
                "--execute",
                "--yes",
                "--operation-log",
                operation_log or OPERATIONS_LOG_FILE,
                "--require-confirmation-token",
                "--confirmation-token",
                confirmation_token or "{confirmation_token_from_matching_dry_run}",
            ]
        )
    return {
        "schema": "cleanmac.ai-policy-simulation.v1",
        "destructive": execute,
        "dry_run": not execute,
        "allowed": allowed,
        "would_be_destructive": execute,
        "plan_file": plan_file,
        "plan": plan,
        "review_selection": review_selection,
        "missing_requirements": missing_requirements,
        "blocking_reasons": blocking_reasons,
        "safe_to_auto_retry": bool(blocking_reasons) and all(row["safe_to_auto_fix"] for row in blocking_reasons),
        "retry_requires_user_confirmation": any(not row["safe_to_auto_fix"] for row in blocking_reasons),
        "context_warnings": context_warnings,
        "plan_freshness": freshness,
        "policy_decisions": policy_decisions,
        "required_user_confirmation": execute,
        "required_confirmation_phrase": ai_schema.CONFIRMATION_PHRASE if execute else None,
        "safe_argv": safe_argv,
        "recommended_next_action": "execute_after_user_confirmation"
        if allowed and execute
        else ("dry_run_or_execute_with_safe_argv" if allowed else "fix_missing_requirements_and_repeat_dry_run"),
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


def render_workflow_ux_guide(
    selected_keys: Sequence[str],
    dry_run_keys: Sequence[str],
    *,
    root: Path,
    home: Path,
    dry_run_scope: str,
    dry_run_report: dict[str, Any],
) -> dict[str, Any]:
    categories_arg = ",".join(selected_keys)
    dry_run_categories_arg = ",".join(dry_run_keys)
    plan_file = "{plan_file}"
    review_selection_file = "{review_selection_file}"
    operation_log = "{operation_log}"
    confirmation_token = "{confirmation_token_from_matching_dry_run}"
    item_count = len(dry_run_report.get("items", []))
    total_bytes = int(dry_run_report.get("total_bytes") or 0)
    return {
        "schema": "cleanmac.workflow-ux.v1",
        "destructive": False,
        "dry_run": True,
        "purpose": "Make the safe CLI/AI workflow understandable without adding GUI, TUI, or background scanning.",
        "one_command": {
            "description": "Run the common safe workflow once: scripts, analyze, diagnose, inspect, and dry-run summary.",
            "argv": [
                "cleanmac",
                "--json",
                "workflow",
                "--categories",
                categories_arg,
                "--dry-run-scope",
                dry_run_scope,
            ],
            "safe_to_auto_call": True,
            "performs_background_scan": False,
            "executes_cleanup": False,
        },
        "dry_run_summary": {
            "category_keys": list(dry_run_keys),
            "item_count": item_count,
            "total_bytes": total_bytes,
            "total_human": dry_run_report.get("total_human", human_size(total_bytes)),
            "user_visible_summary": f"Dry-run found {item_count} candidate item(s) totaling {human_size(total_bytes)}.",
            "next_action": "review_candidates" if item_count else "no_cleanup_needed",
        },
        "tool_choice_hints": [
            {
                "intent": "understand_available_actions",
                "first_tool": "cleanmac_capabilities",
                "cli": ["cleanmac", "--json", "capabilities"],
                "safe_to_auto_call": True,
                "next_action": "choose_category_or_workflow",
            },
            {
                "intent": "common_safe_cleanup_workflow",
                "first_tool": "cleanmac_workflow",
                "cli": ["cleanmac", "--json", "workflow", "--categories", categories_arg],
                "safe_to_auto_call": True,
                "next_action": "read_dry_run_summary_then_review_candidates",
            },
            {
                "intent": "review_existing_plan_or_report",
                "first_tool": "cleanmac_review",
                "cli": ["cleanmac", "--json", "review", "--input-file", plan_file],
                "safe_to_auto_call": True,
                "next_action": "write_or_validate_review_selection_file",
            },
            {
                "intent": "check_execute_readiness",
                "first_tool": "cleanmac_policy_simulate",
                "cli": [
                    "cleanmac",
                    "--json",
                    "policy-simulate",
                    "--plan-file",
                    plan_file,
                    "--review-selection-file",
                    review_selection_file,
                    "--execute",
                    "--delete-mode",
                    "trash",
                    "--require-plan-context",
                    "--require-confirmation-token",
                ],
                "safe_to_auto_call": True,
                "next_action": "fix_blockers_or_run_dry_run_selected_plan",
            },
            {
                "intent": "execute_cleanup",
                "first_tool": "cleanmac_execute_plan",
                "cli": ["cleanmac", "--json", "clean", "run", "--execute"],
                "safe_to_auto_call": False,
                "requires_human_confirmation": True,
                "next_action": "require_human_confirmation_token_and_operation_log",
            },
        ],
        "common_workflows": [
            {
                "name": "safe_preview_once",
                "description": "One command for common non-destructive UX: inspect, diagnose, and dry-run summary.",
                "argv": ["cleanmac", "--json", "workflow", "--categories", categories_arg],
                "safe_to_auto_call": True,
                "destructive": False,
            },
            {
                "name": "ai_governed_plan_review_dry_run",
                "description": "Generate a governed plan, produce a review selection, simulate policy, then dry-run selected items.",
                "steps": [
                    "generate_plan",
                    "review_plan",
                    "validate_plan",
                    "policy_simulate_execute_intent",
                    "dry_run_selected_plan",
                ],
                "safe_to_auto_call_until": "dry_run_selected_plan",
                "destructive": False,
            },
            {
                "name": "human_confirmed_trash_execute",
                "description": "Final Trash-mode execution only after matching dry-run token and explicit human confirmation.",
                "steps": ["execute_after_human_confirmation"],
                "safe_to_auto_call": False,
                "requires_human_confirmation": True,
                "destructive": True,
            },
        ],
        "file_relationships": [
            {
                "name": "plan_file",
                "schema": "cleanmac.plan.v1",
                "producer": "cleanmac --json plan --ai-origin",
                "consumers": ["validate-plan", "policy-simulate", "review", "clean run --plan-file"],
                "purpose": "Reusable snapshot of candidate categories, root/home context, and execution policy.",
            },
            {
                "name": "review_selection_file",
                "schema": "cleanmac.review-selection.v1",
                "producer": "cleanmac --json review --input-file {plan_file} --selection-file {review_selection_file}",
                "consumers": ["policy-simulate", "clean run --review-selection-file"],
                "purpose": "Human-readable selection constraint; execution may only touch selected reviewed items.",
            },
            {
                "name": "confirmation_token",
                "schema": "cleanmac.ai-confirmation-summary.v1",
                "producer": "matching dry-run clean report",
                "consumers": ["clean run --execute --require-confirmation-token"],
                "purpose": "Binds final execution to the reviewed plan, root/home, budget, delete mode, and selection context.",
            },
            {
                "name": "operation_log",
                "schema": "cleanmac.operation-log-entry.v1",
                "producer": "clean run --operation-log {operation_log}",
                "consumers": ["audit/review after execution"],
                "purpose": "Append-only JSONL audit trail for every evaluated cleanup operation.",
            },
        ],
        "safe_chain": [
            {
                "step": "generate_plan",
                "argv": ["cleanmac", "--json", "plan", "--categories", dry_run_categories_arg, "--ai-origin"],
                "write_stdout_to": plan_file,
                "destructive": False,
                "next_action_on_error": "fix_categories_or_filters_then_regenerate_plan",
            },
            {
                "step": "review_plan",
                "argv": [
                    "cleanmac",
                    "--json",
                    "review",
                    "--input-file",
                    plan_file,
                    "--selection-file",
                    review_selection_file,
                ],
                "destructive": False,
                "next_action_on_error": "inspect_plan_schema_and_regenerate_review_selection",
            },
            {
                "step": "validate_plan",
                "argv": ["cleanmac", "--json", "validate-plan", "--plan-file", plan_file],
                "destructive": False,
                "next_action_on_error": "regenerate_plan_for_current_root_home_context",
            },
            {
                "step": "policy_simulate_execute_intent",
                "argv": [
                    "cleanmac",
                    "--json",
                    "policy-simulate",
                    "--plan-file",
                    plan_file,
                    "--review-selection-file",
                    review_selection_file,
                    "--execute",
                    "--delete-mode",
                    "trash",
                    "--require-plan-context",
                    "--require-confirmation-token",
                ],
                "destructive": False,
                "next_action_on_error": "resolve_blocking_reasons_before_dry_run_or_execute",
            },
            {
                "step": "dry_run_selected_plan",
                "argv": [
                    "cleanmac",
                    "--json",
                    "clean",
                    "run",
                    "--plan-file",
                    plan_file,
                    "--review-selection-file",
                    review_selection_file,
                    "--delete-mode",
                    "trash",
                    "--require-plan-context",
                    "--require-confirmation-token",
                ],
                "destructive": False,
                "next_action_on_error": "follow_cleanmac_ai_error_next_allowed_tools",
            },
            {
                "step": "execute_after_human_confirmation",
                "argv": [
                    "cleanmac",
                    "--json",
                    "clean",
                    "run",
                    "--plan-file",
                    plan_file,
                    "--review-selection-file",
                    review_selection_file,
                    "--execute",
                    "--yes",
                    "--delete-mode",
                    "trash",
                    "--require-plan-context",
                    "--require-confirmation-token",
                    "--confirmation-token",
                    confirmation_token,
                    "--operation-log",
                    operation_log,
                ],
                "destructive": True,
                "safe_to_auto_call": False,
                "requires_human_confirmation": True,
                "next_action_on_error": "do_not_bypass_policy_regenerate_plan_or_repeat_dry_run",
            },
        ],
        "concept_map": {
            "plan": "What could be cleaned and under which root/home/policy context.",
            "review": "Human-readable normalization of a plan/report.",
            "selection": "Constraint file selecting reviewed items; it narrows but never expands execution scope.",
            "policy_simulate": "Read-only check that explains whether execute intent would be allowed.",
            "confirmation_token": "Dry-run-derived token required before AI-originated execute.",
            "operation_log": "JSONL audit trail written during execution evaluation.",
            "delete_mode": "Use trash for recoverability; permanent mode is not allowed for AI-originated execute.",
            "require_plan_context": "Reject stale plans created for a different root/home context.",
        },
    }


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
                "make ai-governance-smoke",
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
        "ux_guide": render_workflow_ux_guide(
            selected_keys,
            dry_run_keys,
            root=root,
            home=home,
            dry_run_scope=dry_run_scope,
            dry_run_report=dry_run_report,
        ),
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


def _ai_workflow_step(
    *,
    number: int,
    step_id: str,
    tool: str,
    argv: list[str],
    input_payload: dict[str, Any],
    output_schema: str,
    destructive: bool,
    auto_call_allowed: bool,
    next_human_action: str,
    failure_recovery: str,
    **extra: Any,
) -> dict[str, Any]:
    step = {
        "number": number,
        "id": step_id,
        "tool": tool,
        "argv": argv,
        "input": input_payload,
        "input_schema": workflow_input_schema(input_payload),
        "output_schema": output_schema,
        "destructive": destructive,
        "auto_call_allowed": auto_call_allowed,
        "next_human_action": next_human_action,
        "failure_recovery": failure_recovery,
    }
    step.update(extra)
    return step


def workflow_input_schema(input_payload: dict[str, Any]) -> dict[str, Any]:
    properties: dict[str, Any] = {}
    for key, value in input_payload.items():
        if isinstance(value, bool):
            properties[key] = {"type": "boolean"}
        elif isinstance(value, int):
            properties[key] = {"type": "integer"}
        elif isinstance(value, list):
            properties[key] = {"type": "array", "items": {"type": "string"}}
        else:
            properties[key] = {"type": "string"}
    return {
        "type": "object",
        "properties": properties,
        "required": list(input_payload),
        "additionalProperties": False,
    }


def render_ai_workflow(categories: list[Category], *, goal: str, root: Path, home: Path) -> dict[str, Any]:
    category_keys = [category.key for category in categories]
    categories_arg = ",".join(category_keys)
    plan_file = "{plan_file}"
    review_selection_file = "{review_selection_file}"
    operation_log = "{operation_log}"
    confirmation_token = "{confirmation_token_from_matching_dry_run}"
    steps = [
        _ai_workflow_step(
            number=1,
            step_id="discover_contract",
            tool="cleanmac_capabilities",
            argv=["cleanmac", "--json", "capabilities"],
            input_payload={},
            output_schema="cleanmac.capabilities.v1",
            destructive=False,
            auto_call_allowed=True,
            next_human_action="none",
            failure_recovery="Stop and show the capabilities error; do not invent categories or shell commands.",
        ),
        _ai_workflow_step(
            number=2,
            step_id="generate_ai_origin_plan",
            tool="cleanmac_generate_plan",
            argv=["cleanmac", "--json", "plan", "--categories", categories_arg, "--ai-origin"],
            input_payload={"categories": category_keys, "ai_origin": True},
            output_schema="cleanmac.plan.v1",
            destructive=False,
            auto_call_allowed=True,
            next_human_action="review generated plan summary",
            failure_recovery="Use cleanmac_list_categories, fix category/filter input, then regenerate the plan.",
            write_stdout_to=plan_file,
        ),
        _ai_workflow_step(
            number=3,
            step_id="normalize_review_selection",
            tool="cleanmac_review",
            argv=[
                "cleanmac",
                "--json",
                "review",
                "--input-file",
                plan_file,
                "--selection-file",
                review_selection_file,
            ],
            input_payload={"input_file": plan_file, "selection_file": review_selection_file},
            output_schema="cleanmac.review.v1",
            destructive=False,
            auto_call_allowed=True,
            next_human_action="approve or edit selected_item_ids in the review selection file",
            failure_recovery="Regenerate review from the same plan; never expand selection beyond reviewed IDs.",
            produces_schema="cleanmac.review-selection.v1",
        ),
        _ai_workflow_step(
            number=4,
            step_id="validate_plan_and_selection",
            tool="cleanmac_validate_plan",
            argv=["cleanmac", "--json", "validate-plan", "--plan-file", plan_file],
            input_payload={"plan_file": plan_file, "review_selection_file": review_selection_file},
            output_schema="cleanmac.validate-plan.v1",
            destructive=False,
            auto_call_allowed=True,
            next_human_action="none unless validation reports stale or unsupported schema",
            failure_recovery="Regenerate the plan under the current root/home and repeat review.",
        ),
        _ai_workflow_step(
            number=5,
            step_id="simulate_execute_policy",
            tool="cleanmac_policy_simulate",
            argv=[
                "cleanmac",
                "--json",
                "policy-simulate",
                "--plan-file",
                plan_file,
                "--review-selection-file",
                review_selection_file,
                "--execute",
                "--delete-mode",
                "trash",
                "--operation-log",
                operation_log,
                "--require-plan-context",
                "--require-confirmation-token",
            ],
            input_payload={
                "plan_file": plan_file,
                "review_selection_file": review_selection_file,
                "execute": True,
                "delete_mode": "trash",
                "operation_log": operation_log,
                "require_plan_context": True,
                "require_confirmation_token": True,
            },
            output_schema="cleanmac.ai-policy-simulation.v1",
            destructive=False,
            auto_call_allowed=True,
            next_human_action="resolve blocking_reasons before preparing execution",
            failure_recovery="Follow blocking_reasons; do not bypass Trash, plan context, token, or operation-log gates.",
        ),
        _ai_workflow_step(
            number=6,
            step_id="dry_run_selected_plan",
            tool="cleanmac_dry_run_plan",
            argv=[
                "cleanmac",
                "--json",
                "clean",
                "run",
                "--plan-file",
                plan_file,
                "--review-selection-file",
                review_selection_file,
                "--delete-mode",
                "trash",
                "--require-plan-context",
            ],
            input_payload={
                "plan_file": plan_file,
                "review_selection_file": review_selection_file,
                "delete_mode": "trash",
                "require_plan_context": True,
            },
            output_schema="cleanmac.clean.v1",
            destructive=False,
            auto_call_allowed=True,
            next_human_action="read dry-run report and decide whether to confirm Trash execution",
            failure_recovery="Use cleanmac.ai-error.v1 next_allowed_tools and repeat from the earliest invalid artifact.",
            required_output="ai_confirmation_summary.confirmation_token",
        ),
        _ai_workflow_step(
            number=7,
            step_id="execute_after_human_confirmation",
            tool="cleanmac_execute_plan",
            argv=[
                "cleanmac",
                "--json",
                "clean",
                "run",
                "--plan-file",
                plan_file,
                "--review-selection-file",
                review_selection_file,
                "--execute",
                "--yes",
                "--delete-mode",
                "trash",
                "--operation-log",
                operation_log,
                "--require-plan-context",
                "--require-confirmation-token",
                "--confirmation-token",
                confirmation_token,
            ],
            input_payload={
                "plan_file": plan_file,
                "review_selection_file": review_selection_file,
                "confirmation_phrase": ai_schema.CONFIRMATION_PHRASE,
                "confirmation_token": confirmation_token,
                "operation_log": operation_log,
            },
            output_schema="cleanmac.clean.v1",
            destructive=True,
            auto_call_allowed=False,
            next_human_action="explicitly confirm with the displayed phrase and matching dry-run token",
            failure_recovery="Do not retry execution blindly; regenerate plan or repeat dry-run if context or token changed.",
            requires_human_confirmation=True,
        ),
    ]
    return {
        "schema": "cleanmac.ai-workflow.v1",
        "destructive": False,
        "dry_run": True,
        "goal": goal,
        "workflow_name": "one-shot-governed-safe-cleanup",
        "purpose": "Give AI hosts a complete governed cleanup route in one read-only response.",
        "runtime_lifecycle": {
            "schema": "cleanmac.runtime-lifecycle-policy.v1",
            "runs_only_when_invoked": True,
            "exits_after_workflow": True,
            "resident_processes": 0,
            "implements_tui": False,
            "implements_gui": False,
            "installs_background_daemon": False,
            "performs_unsolicited_scans": False,
        },
        "selected_categories": [category_metadata(category) for category in categories],
        "inputs": {
            "root": display_path(root),
            "home": display_path(home),
            "categories": category_keys,
            "placeholders": {
                "plan_file": plan_file,
                "review_selection_file": review_selection_file,
                "operation_log": operation_log,
                "confirmation_token": confirmation_token,
            },
        },
        "recommended_tool_call_order": [step["tool"] for step in steps],
        "steps": steps,
        "governance": {
            "default_mode": "dry-run-first",
            "delete_mode_for_execute": "trash",
            "requires_review_selection": True,
            "requires_plan_context": True,
            "requires_operation_log": True,
            "requires_confirmation_token": True,
            "destructive_auto_call_allowed": False,
            "forbidden_patterns": ["raw shell", "background scan", "GUI/TUI session", "permanent AI-originated delete"],
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


def render_completion_shell(shell: str) -> str:
    """Generate a shell completion script for cleanmac."""
    commands = [
        "list",
        "capabilities",
        "doctor",
        "scripts",
        "inspect",
        "analyze",
        "plan",
        "validate-plan",
        "policy-simulate",
        "analyze-tree",
        "diagnose",
        "workflow",
        "ai-workflow",
        "open",
        "links",
        "clean",
        "software",
        "optimize",
        "status",
        "completion",
        "ai-tools",
        "ai-readiness",
        "ai-runbook",
        "ai-self-test",
        "ai-decision-matrix",
        "ai-governance-advice",
        "ai-host-policy",
        "ai-host-integration-pack",
        "ai-host-preflight",
        "ai-host-evidence",
        "mcp-surface-audit",
        "release-readiness",
        "release-diagnostics",
        "release-evidence",
        "release-operator-summary",
        "release-rehearsal",
        "release-promotion-decision",
        "release-rollback-plan",
        "release-post-publish-verification",
        "release-post-publish-result",
        "release-post-publish-evidence-template",
        "ai-schema-registry",
        "ai-eval-pack",
        "ai-eval-run",
    ]
    global_flags = "--root --home --json --report-file --version --verbose --quiet"
    category_flags = "--categories --default --all"
    category_keys = sorted(cat.key for cat in CATEGORIES)
    ai_eval_scenarios = [str(row["id"]) for row in render_ai_eval_pack().get("scenarios", [])]
    ai_eval_run_flags = " ".join(dict.fromkeys(["--scenario", "--trace-file", "smoke", "all", *ai_eval_scenarios]))
    # Command-specific flags: maps command -> list of flag completions
    cmd_flags = {
        "scripts": f"{category_flags} --group",
        "inspect": f"{category_flags} --limit --recursive --min-size-mb --sort --exclude --include --name-regex --older-than-days --max-delete-mb --max-items",
        "analyze": category_flags,
        "plan": f"{category_flags} --risk-policy --max-delete-mb --exclude --include --min-size-mb --name-regex --max-items --older-than-days --ai-origin",
        "validate-plan": "--plan-file",
        "policy-simulate": "--plan-file --execute --delete-mode --operation-log --require-plan-context --require-confirmation-token --confirmation-token",
        "analyze-tree": "--path --depth --top --min-size-mb",
        "diagnose": f"{category_flags} --log-threshold-mb --large-threshold-mb",
        "workflow": f"{category_flags} --inspect-limit --log-threshold-mb --large-threshold-mb --dry-run-scope",
        "open": f"{category_flags} --execute",
        "links": "--kind --execute --remove",
        "clean": f"{category_flags} --execute --yes --risk-policy --delete-mode --max-delete-mb --exclude --include --min-size-mb --name-regex --max-items --older-than-days --fail-on-skipped --bundle-allowlist --bundle-blocklist --delete-mode --operation-log --require-plan-context --require-confirmation-token --confirmation-token --plan-file --allow-live-root",
        "software": "list leftovers startup-items inspect uninstall-plan execute --app --plan-file --review-selection-file --execute --yes --delete-mode --operation-log",
        "optimize": "list plan run --execute",
        "status": "snapshot",
        "completion": "bash zsh fish",
        "ai-tools": "--format openai anthropic mcp all",
        "ai-readiness": "",
        "ai-runbook": "",
        "ai-self-test": "",
        "ai-decision-matrix": "",
        "ai-governance-advice": "",
        "ai-host-policy": "",
        "ai-host-integration-pack": "",
        "ai-host-preflight": "",
        "ai-host-evidence": "",
        "mcp-surface-audit": "",
        "release-readiness": "--dist-dir --assets-dir",
        "release-diagnostics": "--dist-dir --assets-dir",
        "release-evidence": "--dist-dir --assets-dir",
        "release-operator-summary": "--dist-dir --assets-dir",
        "release-rehearsal": "--dist-dir --assets-dir",
        "release-promotion-decision": "--dist-dir --assets-dir",
        "release-rollback-plan": "--dist-dir --assets-dir",
        "release-post-publish-verification": "--dist-dir --assets-dir",
        "release-post-publish-result": "--dist-dir --assets-dir --evidence-file",
        "release-post-publish-evidence-template": "--dist-dir --assets-dir",
        "ai-schema-registry": "",
        "ai-eval-pack": "",
        "ai-eval-run": ai_eval_run_flags,
    }
    if shell == "bash":
        return _render_bash_completion(commands, global_flags, category_keys, cmd_flags)
    if shell == "zsh":
        return _render_zsh_completion(commands, global_flags, category_keys, cmd_flags)
    return _render_fish_completion(commands, global_flags, category_keys, cmd_flags)


def _render_bash_completion(
    commands: list[str], global_flags: str, category_keys: list[str], cmd_flags: dict[str, str]
) -> str:
    cats = " ".join(category_keys)
    cmds = " ".join(commands)
    lines = [
        f"# cleanmac bash completion (v{VERSION})",
        "_cleanmac_completion() {",
        "    local cur prev words cword",
        "    _init_completion || return",
        f'    local commands="{cmds}"',
        f'    local global_flags="{global_flags}"',
        f'    local categories="{cats}"',
        '    case "$prev" in',
        "        --categories)",
        '            COMPREPLY=($(compgen -W "$categories" -- "$cur"))',
        "            return",
        "            ;;",
        "        completion)",
        '            COMPREPLY=($(compgen -W "bash zsh fish" -- "$cur"))',
        "            return",
        "            ;;",
        "    esac",
        "    if [[ $cword -eq 1 ]]; then",
        '        COMPREPLY=($(compgen -W "$commands $global_flags" -- "$cur"))',
        "        return",
        "    fi",
        '    local prev_cmd="${words[1]}"',
        '    case "$prev_cmd" in',  # noqa: F841 (prev_cmd used in cmds)
    ]
    for cmd in commands:
        flags = cmd_flags.get(cmd, "")
        if flags:
            lines.append(f'        {cmd}) COMPREPLY=($(compgen -W "{flags}" -- "$cur")) ;;')
    lines += [
        '        *) COMPREPLY=($(compgen -W "$global_flags" -- "$cur")) ;;',
        "    esac",
        "}",
        "complete -F _cleanmac_completion cleanmac",
        "",
        "# Local variables:",
        "# mode: shell-script",
        "# End:",
    ]
    return "\n".join(lines)


def _render_zsh_completion(
    commands: list[str], global_flags: str, category_keys: list[str], cmd_flags: dict[str, str]
) -> str:
    cats = " ".join(category_keys)
    lines = [
        "#compdef cleanmac",
        f"# cleanmac zsh completion (v{VERSION})",
        "_cleanmac_completion() {",
        "    local -a _cleanmac_commands",
        "    _cleanmac_commands=(",
    ]
    for cmd in commands:
        lines.append(f'        "{cmd}:{cmd_flags.get(cmd, "").split()[0] if cmd_flags.get(cmd) else ""}"')
    lines += [
        "    )",
        "    local -a _cleanmac_categories",
        f"    _cleanmac_categories=({cats})",
        "    _arguments \\",
        '        "{--root,--home,--json,--report-file,--version}[global flags]" \\',
        '        "1: :{${_cleanmac_commands}}" \\',
        '        "*: :->args"',
        "    case $state in",
        "        args)",
        '            local curcontext="$curcontext" word',
        '            case "$words[1]" in',
    ]
    for cmd, flags in cmd_flags.items():
        if flags:
            lines.append(f'                {cmd}) _arguments -s "${{(q)}}"' + " \\")
            for flag in flags.split():
                lines.append('                    "' + "{" + flag + '}" \\')
            lines.append("                    ;;")
        else:
            lines.append(f"                {cmd}) ;;")
    lines += [
        "            esac",
        "            ;;",
        "    esac",
        "}",
        "_cleanmac_completion",
    ]
    return "\n".join(lines)


def _render_fish_completion(
    commands: list[str], global_flags: str, category_keys: list[str], cmd_flags: dict[str, str]
) -> str:
    cats = " ".join(category_keys)
    lines = [
        f"# cleanmac fish completion (v{VERSION})",
    ]
    # Global flags
    for flag in global_flags.split():
        lines.append(f'complete -c cleanmac -n "__fish_use_subcommand" -l {flag.lstrip("-")} -d "global flag"')
    # Commands
    for cmd in commands:
        description = (cmd_flags.get(cmd) or cmd).split()[0]
        lines.append(f'complete -c cleanmac -n "__fish_use_subcommand" -a {cmd} -d "{description}"')
        cmd_flags_str = cmd_flags.get(cmd, "")
        for flag in cmd_flags_str.split():
            clean_flag = flag.lstrip("-")
            if clean_flag != flag:
                # It's a --flag
                lines.append(
                    f'complete -c cleanmac -n "__fish_seen_subcommand_from {cmd}" -l {clean_flag} -d "{cmd} flag"'
                )
            else:
                # It's a positional argument choice
                lines.append(f'complete -c cleanmac -n "__fish_seen_subcommand_from {cmd}" -a {flag} -d "{cmd} action"')
    # Categories for --categories
    if cats:
        lines.append(
            f'complete -c cleanmac -n "__fish_seen_subcommand_from scripts inspect analyze plan diagnose workflow open clean" -l categories -x -a "{cats}" -d "category"'
        )
    return "\n".join(lines) + "\n"


def print_categories(categories: Sequence[Category], *, as_json: bool, quiet: bool = False) -> None:
    if as_json:
        print(
            json.dumps(
                {
                    "schema": "cleanmac.category-list.v1",
                    "categories": [category_metadata(category) for category in categories],
                },
                indent=2,
                ensure_ascii=False,
            )
        )
        return
    if quiet:
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


def print_report(report: dict[str, Any], *, as_json: bool, command: str, quiet: bool = False) -> None:
    if as_json:
        print(json.dumps(report, indent=2, ensure_ascii=False))
        return
    if quiet:
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
    if command == "policy-simulate":
        print(f"Policy simulation allowed: {report['allowed']}")
        print(f"Recommended next action: {report['recommended_next_action']}")
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


def render_html_audit_report(audit_record: dict[str, Any]) -> str:
    report_value = audit_record.get("report")
    report: dict[str, Any] = report_value if isinstance(report_value, dict) else {}
    ai_summary_value = report.get("ai_summary")
    ai_summary: dict[str, Any] = ai_summary_value if isinstance(ai_summary_value, dict) else {}
    items_value = report.get("items")
    items: list[Any] = items_value if isinstance(items_value, list) else []
    failed_value = report.get("failed")
    failed: list[Any] = failed_value if isinstance(failed_value, list) else []
    skipped_value = report.get("skipped")
    skipped: list[Any] = skipped_value if isinstance(skipped_value, list) else []
    rows = []
    for row in items[:200]:
        rows.append(
            "<tr>"
            f"<td>{html.escape(str(row.get('category', '')))}</td>"
            f"<td>{html.escape(str(row.get('status', 'candidate')))}</td>"
            f"<td>{html.escape(str(row.get('human', '')))}</td>"
            f"<td>{html.escape(str(row.get('path', '')))}</td>"
            "</tr>"
        )
    return "\n".join(
        [
            "<!doctype html>",
            "<html><head><meta charset='utf-8'><title>cleanmac audit report</title>",
            "<style>body{font-family:-apple-system,BlinkMacSystemFont,sans-serif;margin:2rem;}code,td{font-family:ui-monospace,monospace;}table{border-collapse:collapse;width:100%;}td,th{border:1px solid #ddd;padding:.4rem;}th{background:#f6f8fa;text-align:left;}.ok{color:#0969da}.bad{color:#cf222e}</style>",
            "</head><body>",
            "<h1>cleanmac audit report</h1>",
            f"<p><strong>Generated:</strong> {html.escape(str(audit_record.get('generated_at')))}</p>",
            f"<p><strong>Command:</strong> <code>{html.escape(str(audit_record.get('command')))}</code></p>",
            f"<p><strong>Root:</strong> <code>{html.escape(str(audit_record.get('root')))}</code> <strong>Home:</strong> <code>{html.escape(str(audit_record.get('home')))}</code></p>",
            f"<p><strong>Dry run:</strong> {html.escape(str(audit_record.get('dry_run')))} <strong>Total:</strong> {html.escape(str(report.get('total_human', ai_summary.get('estimated_reclaimable_human', 'n/a'))))}</p>",
            f"<p><strong>Deleted:</strong> {html.escape(str(report.get('deleted_count', 0)))} <strong>Failed:</strong> <span class='bad'>{html.escape(str(len(failed)))}</span> <strong>Skipped:</strong> {html.escape(str(len(skipped)))}</p>",
            f"<p><strong>Headline:</strong> {html.escape(str(ai_summary.get('headline', '')))}</p>",
            "<h2>Items (first 200)</h2>",
            "<table><thead><tr><th>Category</th><th>Status</th><th>Size</th><th>Path</th></tr></thead><tbody>",
            *rows,
            "</tbody></table>",
            "<h2>Machine-readable payload</h2>",
            f"<pre>{html.escape(json.dumps(audit_record, indent=2, ensure_ascii=False))}</pre>",
            "</body></html>",
        ]
    )


def write_report_file(
    report_file: str,
    *,
    command: str,
    root: Path,
    home: Path,
    argv: Sequence[str],
    report: dict[str, Any],
    report_format: str = "json",
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
        "report_format": report_format,
        "dry_run": report.get("dry_run"),
        "safety_gate": report.get("safety_gate"),
        "selected_category_keys": selected_category_keys,
        "selected_categories": selected_categories,
        "report": report,
    }
    if report_format == "html":
        path.write_text(render_html_report(audit_record), encoding="utf-8")
    elif report_format == "markdown":
        path.write_text(render_markdown_report(audit_record), encoding="utf-8")
    else:
        path.write_text(json.dumps(audit_record, indent=2, ensure_ascii=False), encoding="utf-8")
    return audit_record


def emit_report(
    report: dict[str, Any], *, args: argparse.Namespace, command: str, root: Path, home: Path, argv: Sequence[str]
) -> None:
    if args.report_file:
        audit_record = write_report_file(
            args.report_file,
            command=command,
            root=root,
            home=home,
            argv=argv,
            report=report,
            report_format=args.report_format,
        )
        report["report_file"] = audit_record["report_file"]
        report["report_format"] = audit_record["report_format"]
    print_report(report, as_json=args.json, command=command, quiet=getattr(args, "quiet", False))


def _main_impl(argv: Sequence[str]) -> int:
    original_argv = list(argv)
    actual_argv, grouped_command = normalize_grouped_argv(original_argv)
    args = parse_args(actual_argv)
    if grouped_command:
        args.grouped_command = grouped_command
    root = Path(args.root).expanduser().resolve(strict=False)
    home = Path(args.home).expanduser()
    plan_metadata = apply_clean_plan_defaults(args)

    if getattr(args, "profile", None):
        profile = PROFILES[str(args.profile)]
        if hasattr(args, "risk_policy") and str(getattr(args, "risk_policy", "default")) == "default":
            args.risk_policy = str(profile["risk_policy"])
        if hasattr(args, "delete_mode") and str(getattr(args, "delete_mode", "permanent")) == "permanent":
            args.delete_mode = str(profile["delete_mode"])
        if hasattr(args, "max_delete_mb") and getattr(args, "max_delete_mb", None) is None:
            args.max_delete_mb = float(profile["max_delete_mb"])

    if args.command == "list":
        print_categories(CATEGORIES, as_json=args.json, quiet=args.quiet)
        return 0
    if args.command == "capabilities":
        emit_report(render_capabilities(), args=args, command="capabilities", root=root, home=home, argv=actual_argv)
        return 0
    if args.command == "profiles":
        emit_report(render_profiles(), args=args, command="profiles", root=root, home=home, argv=actual_argv)
        return 0
    if args.command == "doctor":
        emit_report(
            render_doctor(root=root, home=home), args=args, command="doctor", root=root, home=home, argv=actual_argv
        )
        return 0
    if args.command == "completion":
        script = render_completion_shell(args.shell)
        if args.json:
            print(
                json.dumps(
                    {
                        "schema": "cleanmac.completion-script.v1",
                        "shell": args.shell,
                        "script_content": script,
                    },
                    indent=2,
                )
            )
        else:
            print(script)
        return 0
    if args.command == "ai-tools":
        if args.format == "openai":
            report = ai_schema.render_openai_functions()
        elif args.format == "anthropic":
            report = ai_schema.render_anthropic_tools()
        elif args.format == "mcp":
            report = ai_schema.render_mcp_tool_catalog()
        else:
            report = {
                "schema": "cleanmac.ai-tools.v1",
                "openai": ai_schema.render_openai_functions(),
                "anthropic": ai_schema.render_anthropic_tools(),
                "mcp": ai_schema.render_mcp_tool_catalog(),
            }
        print(json.dumps(report, indent=2, ensure_ascii=False))
        return 0
    if args.command == "ai-readiness":
        print(
            json.dumps(
                render_ai_readiness(
                    render_ai_tool_contract(),
                    release_readiness=render_runtime_release_readiness_summary(),
                ),
                indent=2,
                ensure_ascii=False,
            )
        )
        return 0
    if args.command == "ai-runbook":
        print(json.dumps(render_ai_runbook(), indent=2, ensure_ascii=False))
        return 0
    if args.command == "ai-self-test":
        print(json.dumps(render_ai_self_test(), indent=2, ensure_ascii=False))
        return 0
    if args.command == "ai-decision-matrix":
        print(json.dumps(render_ai_decision_matrix(), indent=2, ensure_ascii=False))
        return 0
    if args.command == "ai-governance-advice":
        print(json.dumps(render_ai_governance_advice_report(), indent=2, ensure_ascii=False))
        return 0
    if args.command == "ai-host-policy":
        print(json.dumps(render_ai_host_policy_report(), indent=2, ensure_ascii=False))
        return 0
    if args.command == "ai-host-integration-pack":
        print(json.dumps(render_ai_host_integration_pack_report(), indent=2, ensure_ascii=False))
        return 0
    if args.command == "ai-host-preflight":
        print(json.dumps(render_ai_host_preflight_report(), indent=2, ensure_ascii=False))
        return 0
    if args.command == "ai-host-evidence":
        print(json.dumps(render_ai_host_evidence_report(), indent=2, ensure_ascii=False))
        return 0
    if args.command == "mcp-surface-audit":
        print(json.dumps(render_mcp_surface_audit(), indent=2, ensure_ascii=False))
        return 0
    if args.command == "release-readiness":
        print(
            json.dumps(
                render_release_readiness_report(dist_dir=args.dist_dir, assets_dir=args.assets_dir),
                indent=2,
                ensure_ascii=False,
            )
        )
        return 0
    if args.command == "release-diagnostics":
        print(
            json.dumps(
                render_release_diagnostics_report(dist_dir=args.dist_dir, assets_dir=args.assets_dir),
                indent=2,
                ensure_ascii=False,
            )
        )
        return 0
    if args.command == "release-evidence":
        print(
            json.dumps(
                render_release_evidence_report(dist_dir=args.dist_dir, assets_dir=args.assets_dir),
                indent=2,
                ensure_ascii=False,
            )
        )
        return 0
    if args.command == "release-operator-summary":
        print(
            json.dumps(
                render_release_operator_summary(dist_dir=args.dist_dir, assets_dir=args.assets_dir),
                indent=2,
                ensure_ascii=False,
            )
        )
        return 0
    if args.command == "release-rehearsal":
        print(
            json.dumps(
                render_release_rehearsal_report(dist_dir=args.dist_dir, assets_dir=args.assets_dir),
                indent=2,
                ensure_ascii=False,
            )
        )
        return 0
    if args.command == "release-promotion-decision":
        print(
            json.dumps(
                render_release_promotion_decision_report(dist_dir=args.dist_dir, assets_dir=args.assets_dir),
                indent=2,
                ensure_ascii=False,
            )
        )
        return 0
    if args.command == "release-rollback-plan":
        print(
            json.dumps(
                render_release_rollback_plan_report(dist_dir=args.dist_dir, assets_dir=args.assets_dir),
                indent=2,
                ensure_ascii=False,
            )
        )
        return 0
    if args.command == "release-post-publish-verification":
        print(
            json.dumps(
                render_release_post_publish_verification_report(dist_dir=args.dist_dir, assets_dir=args.assets_dir),
                indent=2,
                ensure_ascii=False,
            )
        )
        return 0
    if args.command == "release-post-publish-result":
        print(
            json.dumps(
                render_release_post_publish_result_report(
                    dist_dir=args.dist_dir,
                    assets_dir=args.assets_dir,
                    evidence_file=args.evidence_file,
                ),
                indent=2,
                ensure_ascii=False,
            )
        )
        return 0
    if args.command == "release-post-publish-evidence-template":
        print(
            json.dumps(
                render_release_post_publish_evidence_template_report(
                    dist_dir=args.dist_dir, assets_dir=args.assets_dir
                ),
                indent=2,
                ensure_ascii=False,
            )
        )
        return 0
    if args.command == "ai-schema-registry":
        print(json.dumps(render_ai_schema_registry(), indent=2, ensure_ascii=False))
        return 0
    if args.command == "ai-contract-samples":
        print(json.dumps(render_ai_contract_samples(), indent=2, ensure_ascii=False))
        return 0
    if args.command == "ai-validate-contract":
        print(
            json.dumps(
                render_ai_contract_validation(args.schema_name, args.payload_file),
                indent=2,
                ensure_ascii=False,
            )
        )
        return 0
    if args.command == "ai-eval-pack":
        print(json.dumps(render_ai_eval_pack(), indent=2, ensure_ascii=False))
        return 0
    if args.command == "ai-eval-run":
        try:
            report = render_ai_eval_run(
                scenario=args.scenario,
                cli=Path(__file__).resolve().parent.parent / "cleanmac.py",
                trace_file=Path(args.trace_file) if args.trace_file else None,
            )
        except ValueError as exc:
            print(
                json.dumps(render_ai_eval_unknown_scenario_error(str(exc), actual_argv), indent=2, ensure_ascii=False),
                file=sys.stderr,
            )
            return 1
        except RuntimeError as exc:
            print(
                json.dumps(
                    {
                        "schema": "cleanmac.ai-error.v1",
                        "ok": False,
                        "destructive_operation_started": False,
                        "safe_to_auto_retry": False,
                        "argv": actual_argv,
                        "error": {
                            "code": "trace-persistence-failed",
                            "category": "ai_trace_persistence",
                            "retryable_after_fix": True,
                            "safe_to_auto_retry": False,
                            "message": str(exc),
                            "next_allowed_commands": ["ai-eval-run --scenario smoke"],
                            "exit_code": 2,
                        },
                    },
                    indent=2,
                    ensure_ascii=False,
                ),
                file=sys.stderr,
            )
            return 2
        print(json.dumps(report, indent=2, ensure_ascii=False))
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
    if args.command == "policy-simulate":
        emit_report(
            render_ai_policy_simulation(
                plan_file=args.plan_file,
                root=root,
                home=home,
                execute=args.execute,
                delete_mode=args.delete_mode,
                operation_log=args.operation_log,
                require_plan_context=args.require_plan_context,
                require_confirmation_token=args.require_confirmation_token,
                confirmation_token=args.confirmation_token,
                review_selection_file=args.review_selection_file,
                original_argv=original_argv,
            ),
            args=args,
            command="policy-simulate",
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
        if args.action == "execute":
            if not args.plan_file:
                raise SystemExit("software execute requires --plan-file.")
            if not args.review_selection_file:
                raise SystemExit("software execute requires --review-selection-file.")
            review_selection = review_selection_constraints(args.plan_file, args.review_selection_file)
            operation_log_status = preflight_operation_log(args.operation_log, root=root, home=home)
            if operation_log_status["status"] != "ready":
                raise SystemExit(
                    f"Refusing to execute software uninstall because operation log preflight failed: {operation_log_status['error']}"
                )
            report = execute_software_uninstall(
                load_json_file(args.plan_file),
                review_selection=review_selection or {},
                execute=args.execute,
                yes=args.yes,
                root=root,
                home=home,
                delete_mode=args.delete_mode,
                delete_path_func=lambda path: delete_path(path, root=root, home=home, delete_mode="trash"),
            )
            if report["operation_log_entries"]:
                report["operation_log"] = append_operation_log(
                    args.operation_log, report.pop("operation_log_entries"), root=root, home=home, rotate=False
                )
            emit_report(report, args=args, command="software", root=root, home=home, argv=actual_argv)
            return 0
        emit_report(
            render_software_report(args.action, app=args.app, root=root, home=home),
            args=args,
            command="software",
            root=root,
            home=home,
            argv=actual_argv,
        )
        return 0
    if args.command == "startup":
        if args.action == "disable":
            if not args.plan_file:
                raise SystemExit("startup disable requires --plan-file.")
            if not args.review_selection_file:
                raise SystemExit("startup disable requires --review-selection-file.")
            review_selection = review_selection_constraints(args.plan_file, args.review_selection_file)
            operation_log_status = preflight_operation_log(args.operation_log, root=root, home=home)
            if operation_log_status["status"] != "ready":
                raise SystemExit(
                    f"Refusing to disable startup items because operation log preflight failed: {operation_log_status['error']}"
                )
            report = disable_startup_items(
                load_json_file(args.plan_file),
                review_selection=review_selection or {},
                execute=args.execute,
                yes=args.yes,
                root=root,
                home=home,
            )
            if report["operation_log_entries"]:
                report["operation_log"] = append_operation_log(
                    args.operation_log, report.pop("operation_log_entries"), root=root, home=home, rotate=False
                )
            emit_report(report, args=args, command="startup", root=root, home=home, argv=actual_argv)
            return 0
        emit_report(
            render_startup(args.action, root=root, home=home),
            args=args,
            command="startup",
            root=root,
            home=home,
            argv=actual_argv,
        )
        return 0
    if args.command == "privacy":
        if args.action == "execute":
            if not args.plan_file:
                raise SystemExit("privacy execute requires --plan-file.")
            if not args.review_selection_file:
                raise SystemExit("privacy execute requires --review-selection-file.")
            review_selection = review_selection_constraints(args.plan_file, args.review_selection_file)
            operation_log_status = preflight_operation_log(args.operation_log, root=root, home=home)
            if operation_log_status["status"] != "ready":
                raise SystemExit(
                    f"Refusing to execute privacy cleanup because operation log preflight failed: {operation_log_status['error']}"
                )
            report = execute_privacy_cleanup(
                load_json_file(args.plan_file),
                review_selection=review_selection or {},
                execute=args.execute,
                yes=args.yes,
                root=root,
                home=home,
                delete_mode=args.delete_mode,
                delete_path_func=lambda path: delete_path(path, root=root, home=home, delete_mode="trash"),
            )
            if report["operation_log_entries"]:
                report["operation_log"] = append_operation_log(
                    args.operation_log, report.pop("operation_log_entries"), root=root, home=home, rotate=False
                )
            emit_report(report, args=args, command="privacy", root=root, home=home, argv=actual_argv)
            return 0
        emit_report(
            render_privacy(args.action, scope=args.scope, root=root, home=home),
            args=args,
            command="privacy",
            root=root,
            home=home,
            argv=actual_argv,
        )
        return 0
    if args.command == "tool-execute":
        operation_log_status = preflight_operation_log(args.operation_log, root=root, home=home)
        if operation_log_status["status"] != "ready":
            raise SystemExit(
                f"Refusing to execute tool adapter because operation log preflight failed: {operation_log_status['error']}"
            )
        report = execute_tool(
            args.tool,
            execute=args.execute,
            yes=args.yes,
            root=root,
            home=home,
            timeout=args.timeout,
        )
        if report["operation_log_entries"]:
            report["operation_log"] = append_operation_log(
                args.operation_log, report.pop("operation_log_entries"), root=root, home=home, rotate=False
            )
        emit_report(report, args=args, command="tool-execute", root=root, home=home, argv=actual_argv)
        return 0
    if args.command == "review":
        source_payload = load_json_file(args.input_file)
        selection_payload = load_json_file(args.selection_input_file) if args.selection_input_file else None
        selected_item_ids = (
            [str(item) for item in selection_payload.get("selected_item_ids", [])] if selection_payload else []
        )
        excluded_item_ids = (
            [str(item) for item in selection_payload.get("excluded_item_ids", [])] if selection_payload else []
        )
        explicit_selects = [str(item) for item in args.select_item]
        excluded_item_ids = [item_id for item_id in excluded_item_ids if item_id not in set(explicit_selects)]
        review_report = render_review(
            source_payload,
            selected_item_ids=[*selected_item_ids, *explicit_selects],
            excluded_item_ids=[*excluded_item_ids, *args.exclude_item],
        )
        if selection_payload:
            review_report["selection_validation"] = validate_review_selection(source_payload, selection_payload)
        review_report = apply_item_scope(review_report, args.item_scope, args.item_sort)
        if args.selection_file:
            Path(args.selection_file).expanduser().write_text(
                json.dumps(review_report["selection"], indent=2, ensure_ascii=False), encoding="utf-8"
            )
            review_report["selection_file"] = display_path(Path(args.selection_file).expanduser())
        if args.format == "html":
            print(render_review_html(review_report))
        else:
            print(json.dumps(review_report, indent=2, ensure_ascii=False) if args.json else review_report)
        if args.require_valid_selection and not review_report.get("selection_validation", {}).get("valid", True):
            return 1
        return 0
    if args.command == "permissions":
        categories = select_categories(args)
        emit_report(
            render_permissions_preflight(categories, root=root, home=home),
            args=args,
            command="permissions",
            root=root,
            home=home,
            argv=actual_argv,
        )
        return 0
    if args.command == "tool-plan":
        emit_report(
            render_tool_plan(args.tool, root=root, home=home),
            args=args,
            command="tool-plan",
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
            ai_origin=args.ai_origin,
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
    if args.command == "ai-workflow":
        report = render_ai_workflow(categories, goal=args.goal, root=root, home=home)
        emit_report(report, args=args, command="ai-workflow", root=root, home=home, argv=actual_argv)
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
        if args.execute and plan_metadata and plan_metadata.get("ai_origin"):
            if args.delete_mode != "trash":
                raise SystemExit("AI-originated plan requires --delete-mode trash before execution.")
            if "--operation-log" not in original_argv:
                raise SystemExit("AI-originated plan requires --operation-log before execution.")
            if not args.require_confirmation_token:
                raise SystemExit("AI-originated plan requires --require-confirmation-token before execution.")
            if not args.require_plan_context:
                raise SystemExit("AI-originated plan requires --require-plan-context before execution.")
        if args.require_plan_context and plan_metadata:
            if plan_metadata.get("root") and not same_context_path(str(plan_metadata["root"]), root):
                raise SystemExit(f"Plan root mismatch: expected {plan_metadata['root']} actual {display_path(root)}")
            if plan_metadata.get("home") and not same_context_path(str(plan_metadata["home"]), home):
                raise SystemExit(f"Plan home mismatch: expected {plan_metadata['home']} actual {display_path(home)}")
        if args.execute and plan_metadata and plan_metadata.get("ai_origin"):
            freshness = render_plan_freshness_report(plan_metadata)
            if not freshness["fresh"]:
                raise SystemExit(
                    "Refusing to execute cleanup because AI-originated plan is stale or drifted; regenerate plan and repeat dry-run."
                )
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
        review_selection = review_selection_constraints(args.plan_file, args.review_selection_file)
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
            fail_fast=args.fail_fast,
            bundle_allowlist=parse_csv(args.bundle_allowlist),
            bundle_blocklist=parse_csv(args.bundle_blocklist),
            delete_mode=args.delete_mode,
            operation_log=args.operation_log,
            confirmation_token=args.confirmation_token,
            require_confirmation_token=args.require_confirmation_token,
            require_plan_context=args.require_plan_context,
            ai_originated_plan=bool(plan_metadata and plan_metadata.get("ai_origin")),
            review_selection=review_selection,
            command_argv=original_argv,
        )
        if plan_metadata:
            report["plan_metadata"] = plan_metadata
        emit_report(report, args=args, command="clean", root=root, home=home, argv=actual_argv)
        return 0
    raise SystemExit(f"Unsupported command: {args.command}")


def main(argv: Sequence[str] | None = None) -> int:
    original_argv = list(sys.argv[1:] if argv is None else argv)
    as_json = "--json" in original_argv
    try:
        return _main_impl(original_argv)
    except CleanMacCLIError as exc:
        return emit_cli_error(exc.message, argv=original_argv, exit_code=exc.exit_code, as_json=as_json)
    except SystemExit as exc:
        if exc.code in (None, 0):
            return 0
        exit_code = exc.code if isinstance(exc.code, int) else 1
        message = str(exc.code) if exc.code is not None else "cleanmac exited unexpectedly"
        return emit_cli_error(message, argv=original_argv, exit_code=exit_code, as_json=as_json)


if __name__ == "__main__":
    raise SystemExit(main())
