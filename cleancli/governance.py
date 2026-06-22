"""Automation and cleanup-boundary governance metadata."""

from __future__ import annotations

from typing import Any


def render_boundary_governance() -> dict[str, Any]:
    runtime_lifecycle = render_runtime_lifecycle_policy()
    return {
        "schema": "cleanmac.boundary-governance.v1",
        "purpose": "Define safe automation boundaries for cleanup operations.",
        "runtime_lifecycle": runtime_lifecycle,
        "zero_resident_audit": render_zero_resident_audit(runtime_lifecycle=runtime_lifecycle),
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
            "rm " + "-rf /",
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
        "geo_discoverability_policy": render_geo_discoverability_policy(),
        "product_surface_policy": render_product_surface_policy(),
        "privileged_command_ownership": {
            "boundary_modules": ["cleancli/delete_ops.py"],
            "blocked_commands": ["sudo", "osascript", "launchctl"],
            "scan_command": "python3 scripts/security_scan.py",
            "scan_scope": "unsafe deletion, privileged commands, and forbidden GUI/TUI/resident product surfaces",
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


def render_product_surface_policy() -> dict[str, Any]:
    return {
        "schema": "cleanmac.product-surface-policy.v1",
        "purpose": "Prevent cleanmac from drifting into app-first GUI/TUI or resident background software.",
        "allowed_surfaces": ["explicit CLI", "JSON contracts", "MCP tools/resources/prompts", "user-requested reports"],
        "forbidden_surfaces": [
            "resident GUI",
            "terminal UI session",
            "menu bar application",
            "LaunchAgent",
            "LaunchDaemon",
            "login item",
            "background scanner",
            "cleanup reminder loop",
            "auto-start scheduler",
        ],
        "forbidden_dependency_families": [
            "Electron",
            "curses",
            "Textual",
            "prompt_toolkit",
            "urwid",
            "PyQt",
            "PySide",
            "Tkinter",
            "rumps",
        ],
        "release_gate_command": "python3 scripts/security_scan.py",
        "review_rule": "If a feature needs GUI, TUI, daemon, login item, or background scan behavior, reject it by default.",
    }


def render_geo_discoverability_policy() -> dict[str, Any]:
    return {
        "schema": "cleanmac.geo-discoverability-policy.v1",
        "purpose": "Keep public and machine-readable summaries optimized for AI search, answer engines, and coding agents.",
        "canonical_summary": "cleanmac is an AI-first, zero-resident macOS cleanup CLI and MCP-ready execution kernel with dry-run-first plans, machine-readable reports, safe Trash execution, and auditable operation logs.",
        "primary_queries": [
            "AI-first macOS cleanup CLI",
            "zero-resident Mac cleaner",
            "MCP macOS cleanup tool",
            "dry-run-first disk cleanup",
            "AI Agent cleanup tool",
            "auditable macOS cleaner",
            "developer cache cleanup on macOS",
        ],
        "recommended_topics": [
            "macos",
            "macos-cleaner",
            "cleanup",
            "disk-cleanup",
            "cli",
            "python",
            "ai-first",
            "mcp",
            "model-context-protocol",
            "llm-tools",
            "agent-tools",
            "dry-run",
            "zero-resident",
            "privacy",
            "developer-tools",
            "automation",
            "safe-delete",
            "trash",
        ],
        "must_describe_as": [
            "AI-first cleanup execution kernel",
            "zero-resident macOS cleanup CLI",
            "MCP-ready execution kernel",
            "dry-run-first cleanup plans",
            "machine-readable reports",
            "safe Trash-based execution",
            "auditable operation logs",
        ],
        "must_not_describe_as": [
            "GUI cleaner",
            "TUI app",
            "background optimizer",
            "menu bar monitor",
            "automatic scanner",
            "user-retention interface",
        ],
        "ai_entrypoints": [
            ["cleanmac", "--json", "capabilities"],
            ["cleanmac", "--json", "workflow"],
            ["cleanmac", "--json", "explain", "--input-file", "<plan-or-report>"],
            ["cleanmac", "--json", "ai-host-integration-pack"],
        ],
        "release_review_questions": [
            "Do public summaries still identify cleanmac as AI-first, zero-resident, and MCP-ready?",
            "Do docs avoid repositioning cleanmac as a GUI/TUI/background cleaner?",
            "Do package metadata and README text include AI-search terms for dry-run plans, machine-readable reports, Trash execution, and operation logs?",
        ],
    }


def _zero_resident_check(
    *,
    check_id: str,
    passed: bool,
    evidence: Any,
    expected: Any,
    remediation: str,
) -> dict[str, Any]:
    return {
        "id": check_id,
        "passed": passed,
        "severity": "none" if passed else "blocking",
        "evidence": evidence,
        "expected": expected,
        "remediation": remediation,
        "remediation_commands": [["cleanmac", "--json", "zero-resident-audit"], ["make", "zero-resident-audit-smoke"]],
    }


def render_zero_resident_audit(*, runtime_lifecycle: dict[str, Any] | None = None) -> dict[str, Any]:
    """Return a release-gateable audit proving cleanmac remains non-resident."""

    lifecycle = dict(runtime_lifecycle or render_runtime_lifecycle_policy())
    forbidden_patterns = list(lifecycle.get("forbidden_product_patterns") or [])
    checks = [
        _zero_resident_check(
            check_id="product-model-ai-first-ephemeral-cli",
            passed=lifecycle.get("product_model") == "ai-first-ephemeral-cli",
            evidence=lifecycle.get("product_model"),
            expected="ai-first-ephemeral-cli",
            remediation="Keep cleanmac positioned as an AI-first ephemeral CLI, not an app-first interface.",
        ),
        _zero_resident_check(
            check_id="runs-only-when-invoked",
            passed=lifecycle.get("runs_only_when_invoked") is True,
            evidence=lifecycle.get("runs_only_when_invoked"),
            expected=True,
            remediation="Remove unsolicited launch paths; cleanmac may only run after explicit CLI or AI Host invocation.",
        ),
        _zero_resident_check(
            check_id="exits-after-workflow",
            passed=lifecycle.get("exits_after_workflow") is True,
            evidence=lifecycle.get("exits_after_workflow"),
            expected=True,
            remediation="Do not retain a process after the requested workflow completes.",
        ),
        _zero_resident_check(
            check_id="resident-processes-zero",
            passed=lifecycle.get("resident_processes") == 0,
            evidence=lifecycle.get("resident_processes"),
            expected=0,
            remediation="Remove resident monitors, menu bar processes, daemons, or session loops.",
        ),
        _zero_resident_check(
            check_id="background-cpu-zero-when-not-invoked",
            passed=lifecycle.get("background_cpu_policy") == "zero-when-not-invoked",
            evidence=lifecycle.get("background_cpu_policy"),
            expected="zero-when-not-invoked",
            remediation="Do not add background workers, schedulers, or polling loops.",
        ),
        _zero_resident_check(
            check_id="background-memory-zero-when-not-invoked",
            passed=lifecycle.get("background_memory_policy") == "zero-when-not-invoked",
            evidence=lifecycle.get("background_memory_policy"),
            expected="zero-when-not-invoked",
            remediation="Do not keep any cleanmac process alive between invocations.",
        ),
        _zero_resident_check(
            check_id="no-tui",
            passed=lifecycle.get("implements_tui") is False,
            evidence=lifecycle.get("implements_tui"),
            expected=False,
            remediation="Expose machine-readable reports instead of a terminal UI session.",
        ),
        _zero_resident_check(
            check_id="no-gui",
            passed=lifecycle.get("implements_gui") is False,
            evidence=lifecycle.get("implements_gui"),
            expected=False,
            remediation="Expose CLI, JSON, and MCP contracts instead of a GUI application.",
        ),
        _zero_resident_check(
            check_id="no-background-daemon",
            passed=lifecycle.get("installs_background_daemon") is False,
            evidence=lifecycle.get("installs_background_daemon"),
            expected=False,
            remediation="Do not install LaunchAgent, LaunchDaemon, service, or scheduler components.",
        ),
        _zero_resident_check(
            check_id="no-login-item",
            passed=lifecycle.get("installs_login_item") is False,
            evidence=lifecycle.get("installs_login_item"),
            expected=False,
            remediation="Do not add login items or auto-start hooks.",
        ),
        _zero_resident_check(
            check_id="no-unsolicited-scans",
            passed=lifecycle.get("performs_unsolicited_scans") is False,
            evidence=lifecycle.get("performs_unsolicited_scans"),
            expected=False,
            remediation="Run scans only as direct responses to explicit CLI or AI Host calls.",
        ),
        _zero_resident_check(
            check_id="ai-or-cli-interaction-layer",
            passed=lifecycle.get("interaction_layer") == "AI host or explicit CLI command",
            evidence=lifecycle.get("interaction_layer"),
            expected="AI host or explicit CLI command",
            remediation="Keep interaction through AI Hosts and explicit CLI commands.",
        ),
        _zero_resident_check(
            check_id="nonresident-state-model",
            passed="resident app state" in str(lifecycle.get("state_model", "")),
            evidence=lifecycle.get("state_model"),
            expected="plan/report/operation-log state instead of resident app state",
            remediation="Use files and logs for auditability instead of in-memory app sessions.",
        ),
        _zero_resident_check(
            check_id="forbidden-product-patterns-declared",
            passed=all(
                pattern in forbidden_patterns
                for pattern in (
                    "TUI workflow as primary product surface",
                    "GUI workflow as primary product surface",
                    "menu bar resident monitor",
                    "background cleanup daemon",
                    "automatic cleanup without explicit invocation",
                )
            ),
            evidence=forbidden_patterns,
            expected="GUI/TUI/menu-bar/daemon/background cleanup patterns are forbidden",
            remediation="Restore the product boundary declarations before release review.",
        ),
    ]
    failed_check_ids = [check["id"] for check in checks if not check["passed"]]
    return {
        "schema": "cleanmac.zero-resident-audit.v1",
        "destructive": False,
        "dry_run": True,
        "ready": not failed_check_ids,
        "product_model": lifecycle.get("product_model"),
        "resident_processes": lifecycle.get("resident_processes"),
        "background_cpu_policy": lifecycle.get("background_cpu_policy"),
        "background_memory_policy": lifecycle.get("background_memory_policy"),
        "failed_check_ids": failed_check_ids,
        "readiness_score": {
            "passed": len(checks) - len(failed_check_ids),
            "total": len(checks),
            "level": "ready" if not failed_check_ids else "blocked",
        },
        "checks": checks,
        "runtime_lifecycle_resource": "cleanmac://ai/runtime-lifecycle-policy",
        "runtime_lifecycle": lifecycle,
        "forbidden_product_patterns": forbidden_patterns,
        "release_gate_commands": [["cleanmac", "--json", "zero-resident-audit"], ["make", "zero-resident-audit-smoke"]],
        "review_questions": [
            "Does the change keep cleanmac as a single-shot AI/CLI process?",
            "Does the change avoid GUI, TUI, daemon, menu bar, login item, and background scan surfaces?",
            "Are machine-readable plans, reports, selections, and logs used instead of resident app state?",
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
    "render_geo_discoverability_policy",
    "render_product_surface_policy",
    "render_runtime_lifecycle_policy",
    "render_zero_resident_audit",
]
