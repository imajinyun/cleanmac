from __future__ import annotations

from typing import Any

from cleancli import ai_schema


def render_ai_runbook() -> dict[str, Any]:
    return {
        "schema": "cleanmac.ai-runbook.v1",
        "default_mode": "dry-run-first",
        "runtime_lifecycle": {
            "schema": "cleanmac.runtime-lifecycle-policy.v1",
            "product_model": "ai-first-ephemeral-cli",
            "runs_only_when_invoked": True,
            "exits_after_workflow": True,
            "resident_processes": 0,
            "implements_tui": False,
            "implements_gui": False,
            "installs_background_daemon": False,
            "performs_unsolicited_scans": False,
            "interaction_layer": "AI host or explicit CLI command",
        },
        "uses_shell": False,
        "command_transport": "argv-only",
        "execution_gate": {
            "destructive_tool": "cleanmac_execute_plan",
            "auto_call_allowed": False,
            "requires_confirmation_phrase": ai_schema.CONFIRMATION_PHRASE,
            "requires_confirmation_token": True,
            "required_before_execute": [
                "cleanmac_generate_plan",
                "cleanmac_validate_plan",
                "cleanmac_policy_simulate",
                "cleanmac_dry_run_plan",
                "human_confirmation",
            ],
        },
        "one_shot_governed_workflow": {
            "tool": "cleanmac_ai_workflow",
            "cli": [
                "cleanmac",
                "--json",
                "ai-workflow",
                "--goal",
                "safe-cleanup",
                "--categories",
                "trash,downloads,xcode",
            ],
            "schema": "cleanmac.ai-workflow.v1",
            "auto_call_allowed": True,
            "destructive": False,
            "purpose": "🧭 Fetch the complete governed route in one read-only call: plan, review, policy simulation, dry-run, human confirmation, and Trash execution.",
        },
        "phases": [
            {
                "id": "discover",
                "description": "🔎 Discover cleanmac capabilities, valid cleanup categories, and the safe AI workflow contract.",
                "tools": ["cleanmac_capabilities", "cleanmac_list_categories", "cleanmac_ai_workflow"],
                "auto_call_allowed": True,
                "stop_on_error": True,
            },
            {
                "id": "inspect",
                "description": "🧪 Inspect and diagnose cleanup candidates without deleting files or starting background scans.",
                "tools": ["cleanmac_inspect", "cleanmac_diagnose", "cleanmac_analyze_categories"],
                "auto_call_allowed": True,
                "stop_on_error": True,
            },
            {
                "id": "plan",
                "description": "📝 Generate an AI-originated, reusable cleanup plan that remains non-destructive.",
                "tools": ["cleanmac_generate_plan"],
                "auto_call_allowed": True,
                "required_arguments": ["categories"],
                "stop_on_error": True,
            },
            {
                "id": "preflight",
                "description": "🛡️ Validate the plan and simulate execution policy before any deletion intent is allowed.",
                "tools": ["cleanmac_validate_plan", "cleanmac_policy_simulate"],
                "auto_call_allowed": True,
                "stop_on_error": True,
            },
            {
                "id": "dry_run",
                "description": "🎟️ Run the selected plan in dry-run mode to preview Trash actions and obtain the confirmation token.",
                "tools": ["cleanmac_dry_run_plan"],
                "auto_call_allowed": True,
                "required_output": "ai_confirmation_summary.confirmation_token",
                "stop_on_error": True,
            },
            {
                "id": "execute",
                "description": "🗑️ Execute only after explicit human confirmation, a matching dry-run token, Trash routing, and operation logging.",
                "tools": ["cleanmac_execute_plan"],
                "auto_call_allowed": False,
                "required_arguments": ["plan_file", "confirmation_phrase", "confirmation_token"],
                "stop_on_error": True,
            },
        ],
    }
