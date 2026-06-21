"""Automation and cleanup-boundary governance metadata."""

from __future__ import annotations

from typing import Any


def render_boundary_governance() -> dict[str, Any]:
    runtime_lifecycle = render_runtime_lifecycle_policy()
    return {
        "schema": "cleanmac.boundary-governance.v1",
        "purpose": "Define safe automation boundaries for cleanup operations.",
        "runtime_lifecycle": runtime_lifecycle,
        "automated_safe_behaviors": [
            "list",
            "capabilities",
            "doctor",
            "analyze",
            "diagnose",
            "inspect",
            "plan",
            "validate-plan",
            "policy-simulate",
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
        "forbidden_automation": [
            "clean --execute",
            "--allow-live-root",
            "sudo rm",
            "rm -rf /",
            "background daemon",
            "menu bar resident app",
            "unsolicited scheduled scan",
        ],
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
                "make ai-governance-smoke",
                "make open-source-smoke",
                "make distribution-smoke",
                "make docker-test",
                "make release-check",
            ],
        },
    }


def render_runtime_lifecycle_policy() -> dict[str, Any]:
    return {
        "schema": "cleanmac.runtime-lifecycle-policy.v1",
        "product_model": "ai-first-ephemeral-cli",
        "runs_only_when_invoked": True,
        "exits_after_workflow": True,
        "resident_processes": 0,
        "background_cpu_policy": "zero-when-not-invoked",
        "background_memory_policy": "zero-when-not-invoked",
        "implements_tui": False,
        "implements_gui": False,
        "installs_background_daemon": False,
        "installs_login_item": False,
        "performs_unsolicited_scans": False,
        "retention_pattern": "do-not-retain-user-attention",
        "interaction_layer": "AI host or explicit CLI command",
        "state_model": "plan files, review-selection files, reports, and operation logs instead of resident app state",
        "allowed_long_lived_state": [
            "cleanmac.plan.v1 files explicitly written by the caller",
            "cleanmac.review-selection.v1 files explicitly written by the caller",
            "JSON/HTML/Markdown reports explicitly requested with --report-file",
            "operation log JSONL records for auditability",
        ],
        "forbidden_product_patterns": [
            "TUI workflow as primary product surface",
            "GUI workflow as primary product surface",
            "menu bar resident monitor",
            "background cleanup daemon",
            "automatic cleanup without explicit invocation",
            "push-style cleanup reminders",
        ],
    }


def render_capabilities(*args: Any, **kwargs: Any) -> dict[str, Any]:
    from .core import render_capabilities as _render_capabilities

    return _render_capabilities(*args, **kwargs)


def render_doctor(*args: Any, **kwargs: Any) -> dict[str, Any]:
    from .core import render_doctor as _render_doctor

    return _render_doctor(*args, **kwargs)


__all__ = [
    "render_boundary_governance",
    "render_capabilities",
    "render_doctor",
    "render_runtime_lifecycle_policy",
]
