from __future__ import annotations

from typing import Any


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
            "requires_confirmation_phrase": "确认执行 cleanmac 清理",
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
            "purpose": "Fetch the full governed plan/review/policy/dry-run/confirmation/execute route in one read-only call.",
        },
        "phases": [
            {
                "id": "discover",
                "description": "Discover cleanmac capabilities and valid cleanup categories.",
                "tools": ["cleanmac_capabilities", "cleanmac_list_categories", "cleanmac_ai_workflow"],
                "auto_call_allowed": True,
                "stop_on_error": True,
            },
            {
                "id": "inspect",
                "description": "Inspect and diagnose candidates without deleting files.",
                "tools": ["cleanmac_inspect", "cleanmac_diagnose", "cleanmac_analyze_categories"],
                "auto_call_allowed": True,
                "stop_on_error": True,
            },
            {
                "id": "plan",
                "description": "Generate an AI-originated reusable cleanup plan.",
                "tools": ["cleanmac_generate_plan"],
                "auto_call_allowed": True,
                "required_arguments": ["categories"],
                "stop_on_error": True,
            },
            {
                "id": "preflight",
                "description": "Validate plan and simulate policy before any deletion intent.",
                "tools": ["cleanmac_validate_plan", "cleanmac_policy_simulate"],
                "auto_call_allowed": True,
                "stop_on_error": True,
            },
            {
                "id": "dry_run",
                "description": "Run the plan without execution to obtain the confirmation token.",
                "tools": ["cleanmac_dry_run_plan"],
                "auto_call_allowed": True,
                "required_output": "ai_confirmation_summary.confirmation_token",
                "stop_on_error": True,
            },
            {
                "id": "execute",
                "description": "Execute only after explicit human confirmation and matching token.",
                "tools": ["cleanmac_execute_plan"],
                "auto_call_allowed": False,
                "required_arguments": ["plan_file", "confirmation_phrase", "confirmation_token"],
                "stop_on_error": True,
            },
        ],
    }
