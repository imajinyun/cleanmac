"""AI-facing invocation contracts and workflow guidance."""

from __future__ import annotations

from typing import Any

from cleancli import ai_schema
from cleancli.ai_errors import render_ai_error_taxonomy


def render_ai_tool_contract() -> dict[str, Any]:
    return {
        "schema": "cleanmac.ai-tool-contract.v1",
        "purpose": "Describe safe cleanmac invocation rules for LLM and agent tool callers.",
        "default_invocation": {
            "json_required": True,
            "preferred_command_style": "grouped",
            "program": "cleanmac",
            "runtime_lifecycle": "single-shot process; no resident GUI, TUI, daemon, or background scan",
            "product_positioning": "AI-first cleanup execution kernel; not an app-first GUI/TUI retention surface",
        },
        "discoverability_hints": {
            "canonical_summary": "AI-first, zero-resident macOS cleanup CLI and MCP-ready execution kernel with dry-run-first cleanup plans, machine-readable reports, safe Trash execution, and auditable operation logs.",
            "answer_when_user_asks_for": [
                "AI-first macOS cleanup CLI",
                "zero-resident Mac cleaner",
                "MCP macOS cleanup tool",
                "dry-run-first disk cleanup",
                "AI Agent cleanup tool",
                "auditable macOS cleaner",
            ],
            "do_not_position_as": [
                "GUI cleaner",
                "TUI app",
                "background optimizer",
                "menu bar monitor",
                "automatic scanner",
                "user-retention interface",
            ],
            "best_entrypoints": [
                ["cleanmac", "--json", "capabilities"],
                ["cleanmac", "--json", "workflow"],
                ["cleanmac", "--json", "explain", "--input-file", "<plan-or-report>"],
                ["cleanmac", "--json", "ai-host-integration-pack"],
            ],
        },
        "auto_call_allowed": [
            "capabilities",
            "doctor",
            "status snapshot",
            "clean list",
            "clean inspect",
            "clean plan",
            "clean validate-plan",
            "explain",
            "clean policy-simulate",
            "workflow",
            "software list",
            "software leftovers",
            "software startup-items",
            "software inspect",
            "software uninstall-plan",
            "analyze categories",
            "analyze tree",
        ],
        "confirmation_required": [
            "clean run --execute",
            "clean links --execute",
            "clean open --execute",
            "software execute --execute --review-selection-file",
        ],
        "forbidden": [
            "--allow-live-root without explicit user instruction",
            "sudo",
            "osascript",
            "launchctl",
            "rm " + "-rf",
            "shell=true deletion",
            "background daemon",
            "resident GUI/TUI workflow",
            "unsolicited scheduled scan",
        ],
        "execution_requirements": {
            "prefer_delete_mode": "trash",
            "require_operation_log": True,
            "require_user_confirmation": True,
            "confirmation_token_supported": True,
            "confirmation_token_flag": "clean --confirmation-token",
            "require_confirmation_token_flag": "clean --require-confirmation-token",
            "recommended_confirmation_phrase": ai_schema.CONFIRMATION_PHRASE,
            "ai_originated_plan_requires": [
                "--delete-mode trash",
                "--operation-log",
                "--require-confirmation-token",
                "--require-plan-context",
            ],
        },
        "one_shot_interaction_model": {
            "ask_ai_first": True,
            "manual_cli_supported": True,
            "must_exit_after_current_workflow": True,
            "must_not_keep_user_in_interface": True,
            "state_handoff": ["plan_file", "review_selection_file", "report_file", "operation_log"],
            "preferred_user_flow": "ask AI or run one explicit command, review machine-readable evidence, optionally confirm execute, then process exits",
        },
        "error_taxonomy_schema": "cleanmac.ai-error.v1",
        "error_taxonomy": render_ai_error_taxonomy(),
    }


def render_ai_recommended_workflow() -> list[dict[str, Any]]:
    return [
        {
            "step": "discover",
            "command": ["cleanmac", "--json", "capabilities"],
            "auto_call_allowed": True,
        },
        {
            "step": "diagnose",
            "command": ["cleanmac", "--json", "doctor"],
            "auto_call_allowed": True,
        },
        {
            "step": "inspect",
            "command_template": ["cleanmac", "--json", "clean", "inspect", "--categories", "{categories}"],
            "auto_call_allowed": True,
        },
        {
            "step": "plan",
            "command_template": [
                "cleanmac",
                "--json",
                "clean",
                "plan",
                "--categories",
                "{categories}",
                "--ai-origin",
            ],
            "auto_call_allowed": True,
        },
        {
            "step": "validate_plan",
            "command_template": ["cleanmac", "--json", "clean", "validate-plan", "--plan-file", "{plan_file}"],
            "auto_call_allowed": True,
        },
        {
            "step": "dry_run",
            "command_template": [
                "cleanmac",
                "--json",
                "clean",
                "run",
                "--plan-file",
                "{plan_file}",
                "--require-plan-context",
                "--delete-mode",
                "trash",
            ],
            "auto_call_allowed": True,
        },
        {
            "step": "confirm",
            "kind": "human_interaction",
            "prompt_template": "Summarize categories, estimated bytes, skipped items, risk, trash mode, and operation log before asking for explicit confirmation.",
            "auto_call_allowed": False,
            "auto_prepare_allowed": True,
            "requires_user_confirmation": True,
            "confirmation_phrase": ai_schema.CONFIRMATION_PHRASE,
        },
        {
            "step": "execute",
            "command_template": [
                "cleanmac",
                "--json",
                "clean",
                "run",
                "--plan-file",
                "{plan_file}",
                "--require-plan-context",
                "--delete-mode",
                "trash",
                "--execute",
                "--yes",
                "--operation-log",
                ai_schema.DEFAULT_OPERATION_LOG,
                "--require-confirmation-token",
                "--confirmation-token",
                "{confirmation_token}",
            ],
            "auto_call_allowed": False,
            "requires_user_confirmation": True,
        },
    ]


def render_ai_intent_hints() -> list[dict[str, Any]]:
    return [
        {
            "intent": "developer_cache_cleanup",
            "phrases": ["开发缓存", "developer cache", "npm cache", "python cache", "go cache"],
            "recommended_categories": ["nodePackageCaches", "pythonPackageCaches", "goBuildCaches"],
            "default_delete_mode": "trash",
            "recommended_risk_policy": "default",
            "warning": "Package managers may re-download dependencies after cleanup.",
        },
        {
            "intent": "browser_cache_cleanup",
            "phrases": ["浏览器缓存", "Chrome cache", "Firefox cache", "browser cache"],
            "recommended_categories": ["chrome", "firefox", "browserCodeSignCache"],
            "default_delete_mode": "trash",
            "recommended_risk_policy": "default",
            "warning": "Browser caches can be rebuilt; credentials, cookies, bookmarks, and profiles remain protected.",
        },
        {
            "intent": "xcode_cleanup",
            "phrases": ["Xcode", "DerivedData", "iOS 模拟器", "device support"],
            "recommended_categories": ["xcode", "deviceFirmware"],
            "default_delete_mode": "trash",
            "recommended_risk_policy": "default",
            "warning": "Xcode may regenerate indexes or re-download device support data after cleanup.",
        },
        {
            "intent": "docker_cleanup",
            "phrases": ["Docker", "container cache", "容器缓存"],
            "recommended_categories": ["docker"],
            "default_delete_mode": "trash",
            "recommended_risk_policy": "default",
            "warning": "Active Docker-related paths are skipped when process guards detect running apps.",
        },
        {
            "intent": "system_log_cleanup",
            "phrases": ["系统日志", "system logs", "diagnostic reports"],
            "recommended_categories": ["systemLogs", "systemDiagnostics", "thirdPartySystemLogs"],
            "default_delete_mode": "trash",
            "recommended_risk_policy": "strict",
            "warning": "Logs may help future troubleshooting; prefer strict risk policy and trash mode.",
        },
        {
            "intent": "large_file_analysis",
            "phrases": ["大文件", "large files", "where is disk space used"],
            "recommended_commands": [
                ["cleanmac", "--json", "analyze", "tree", "--path", "~", "--depth", "2", "--top", "20"]
            ],
            "default_delete_mode": "none",
            "recommended_risk_policy": "readonly",
            "warning": "Analyze commands are read-only and should not be converted into deletion without a plan.",
        },
        {
            "intent": "software_uninstall_planning",
            "phrases": ["卸载软件", "uninstall app", "startup items", "leftovers"],
            "recommended_commands": [
                ["cleanmac", "--json", "software", "list"],
                ["cleanmac", "--json", "software", "uninstall-plan", "--app", "{app}"],
            ],
            "default_delete_mode": "none",
            "recommended_risk_policy": "readonly",
            "warning": "Software uninstall-plan is governance-only and must not run vendor uninstallers automatically.",
        },
    ]


__all__ = ["render_ai_intent_hints", "render_ai_recommended_workflow", "render_ai_tool_contract"]
