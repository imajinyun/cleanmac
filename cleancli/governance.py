"""Automation and cleanup-boundary governance metadata."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any


GOVERNANCE_INTEGRITY_REMEDIATION_COMMANDS = [
    ["cleanmac", "--json", "governance-integrity"],
    ["make", "governance-integrity-smoke"],
    ["make", "governance-smoke"],
]


def _unique_commands(commands: list[list[str]]) -> list[list[str]]:
    seen: set[tuple[str, ...]] = set()
    unique: list[list[str]] = []
    for command in commands:
        key = tuple(command)
        if key not in seen:
            seen.add(key)
            unique.append(list(command))
    return unique


def render_development_governance_todo() -> dict[str, Any]:
    """Return the ordered AI-first governance TODO backlog."""

    items = [
        (
            "strengthen-ai-first-entrypoints",
            "Strengthen AI-first entrypoints",
            "Keep capabilities, workflow, explain, and ai-host-integration-pack as the primary discovery and orchestration surfaces for AI Hosts.",
            ["cleanmac", "--json", "capabilities"],
        ),
        (
            "stabilize-json-mcp-argv-contracts",
            "Stabilize JSON Schema, MCP, and argv contracts",
            "Expose new capabilities through machine-readable schemas, MCP tool definitions, and safe argv templates before human-facing presentation.",
            ["cleanmac", "--json", "ai-schema-registry"],
        ),
        (
            "enforce-zero-resident-governance",
            "Enforce zero-resident governance checks",
            "Reject GUI, TUI, LaunchAgent, LaunchDaemon, login item, background scan, menu-bar, and daemon drift through release gates.",
            ["make", "zero-resident-audit-smoke"],
        ),
        (
            "complete-ai-decision-matrix",
            "Complete the AI decision matrix",
            "Teach AI Hosts when to inspect, plan, dry-run, execute, explain, and validate-plan instead of jumping directly to execution.",
            ["cleanmac", "--json", "ai-decision-matrix"],
        ),
        (
            "expand-explainability",
            "Expand explainability",
            "Make explain output clarify candidate source, risk, protection decisions, delete eligibility, and skip reasons.",
            ["cleanmac", "--json", "explain", "--input-file", "<plan-or-report>"],
        ),
        (
            "govern-plan-files",
            "Govern plan files",
            "Treat plans as first-class artifacts with fingerprints, root/home binding, review handoff, context validation, drift checks, and replay guards.",
            ["cleanmac", "--json", "validate-plan", "--plan-file", "<plan>"],
        ),
        (
            "complete-review-selection-workflow",
            "Complete review-selection workflow",
            "Allow AI or users to constrain a plan while preserving fingerprint validation, Trash routing, confirmation tokens, and require-plan-context gates.",
            ["cleanmac", "--json", "review", "--input-file", "<plan-or-report>"],
        ),
        (
            "extend-readonly-analysis",
            "Extend read-only analysis",
            "Improve analyze, status, software, finder, permissions, and tool-plan context without cleanup side effects.",
            ["cleanmac", "--json", "analyze"],
        ),
        (
            "make-safety-policy-explainable",
            "Make safety policy explainable",
            "Expose protected bundles, sensitive paths, Group Container policy, Trash fail-closed behavior, and no-auth test policy in capabilities.",
            ["cleanmac", "--json", "capabilities"],
        ),
        (
            "tighten-delete-exit",
            "Tighten the single delete exit",
            "Keep cleancli/delete_ops.py as the only low-level deletion owner; business modules may only pass policy and candidate paths.",
            ["python3", "-m", "unittest", "test_cleanmac.CleanMacCLITests.test_real_delete_primitives_are_owned_by_delete_ops", "-v"],
        ),
        (
            "harden-operation-log-reliability",
            "Harden operation-log reliability",
            "Ensure execute-mode operation-log failures are visible in reports and never masquerade as safely audited success.",
            ["python3", "-m", "unittest", "tests.test_operation_log", "-v"],
        ),
        (
            "unify-confirmation-token-gates",
            "Unify confirmation-token gates",
            "Bind destructive CLI and MCP execution to context-matched confirmation tokens for plan, selection, root/home, and execution arguments.",
            ["cleanmac", "--json", "ai-safety-chain"],
        ),
        (
            "expand-ai-safety-regressions",
            "Expand AI safety regressions",
            "Cover direct execute attempts, missing plans, selection fingerprint mismatch, stale plans, dangerous paths, and protected app data.",
            ["make", "ai-governance-smoke"],
        ),
        (
            "maintain-dangerous-path-corpus",
            "Maintain dangerous path corpus",
            "Continuously update tests/data/dangerous_paths.txt for system roots, Mail, Messages, Keychains, CloudDocs, Containers, and Group Containers.",
            ["python3", "-m", "unittest", "test_cleanmac.CleanMacCLITests.test_path_safety_rejects_dangerous_path_data", "-v"],
        ),
        (
            "improve-dry-run-report-quality",
            "Improve dry-run report quality",
            "Make dry-run the primary UX with reclaimable bytes, category, risk, skip reason, confirmation needs, and review guidance.",
            ["cleanmac", "--json", "plan", "--categories", "trash", "--max-items", "10"],
        ),
        (
            "reject-retention-oriented-features",
            "Reject retention-oriented features",
            "Forbid reminders, resident monitoring, automatic scans, background optimization, scheduled cleanup, and menu-bar status surfaces.",
            ["cleanmac", "--json", "product-surface-drift-audit"],
        ),
        (
            "keep-workflow-nondestructive",
            "Keep workflow nondestructive",
            "Limit workflow to safe inspect, diagnose, plan, dry-run, and explain phases; never add destructive cleanup to the default workflow path.",
            ["cleanmac", "--json", "workflow"],
        ),
        (
            "publish-ai-host-integration-guide",
            "Publish AI Host integration guide",
            "Document the host sequence: capabilities, plan, explain, review-selection, and user-confirmed execute.",
            ["cleanmac", "--json", "ai-host-integration-pack"],
        ),
        (
            "standardize-positioning-language",
            "Standardize positioning language",
            "Keep README, release notes, package metadata, and external summaries aligned on AI-first, zero-resident macOS cleanup CLI positioning.",
            ["make", "docs-smoke"],
        ),
        (
            "strengthen-governance-self-check",
            "Strengthen governance self-check",
            "Scan for resident surfaces, unsafe deletion primitives, confirmation bypasses, and incorrect GUI/TUI/background positioning.",
            ["make", "governance-integrity-smoke"],
        ),
        (
            "optimize-single-shot-performance",
            "Optimize single-shot performance",
            "Optimize for fast cold start, bounded scans, stable output, and immediate exit with zero idle CPU and memory.",
            ["cleanmac", "--json", "zero-resident"],
        ),
        (
            "encode-do-not-disturb-principle",
            "Encode do-not-disturb principle",
            "Do not add notifications, resident reminders, background health scores, or daily scans; run only on explicit invocation.",
            ["cleanmac", "--json", "zero-resident-audit"],
        ),
        (
            "support-explicit-cli-composition",
            "Support explicit CLI composition",
            "Keep outputs stable for shells, explicit cron jobs, CI, AI Hosts, and user scripts without installing schedulers.",
            ["cleanmac", "--json", "ai-entrypoints"],
        ),
        (
            "improve-stable-failure-modes",
            "Improve stable failure modes",
            "Return stable error codes for protected paths, Trash failures, permission gaps, plan context mismatch, and selection validation failure.",
            ["cleanmac", "--json", "capabilities"],
        ),
        (
            "gate-release-with-ai-mcp-checklist",
            "Gate release with AI/MCP checklist",
            "Require provider export parity, MCP smoke, AI host smoke, governance smoke, dangerous-path regression, dry-run defaults, and zero-resident checks before release.",
            ["make", "ai-first-release-checklist-smoke"],
        ),
    ]
    return {
        "schema": "cleanmac.development-governance-todo.v1",
        "destructive": False,
        "dry_run": True,
        "purpose": "Ordered governance backlog for cleanmac's AI-first, single-shot, zero-resident product direction.",
        "ordered": True,
        "item_count": len(items),
        "status": "active",
        "items": [
            {
                "order": index,
                "id": item_id,
                "title": title,
                "governance_action": governance_action,
                "status": "governed",
                "verification_command": verification_command,
            }
            for index, (item_id, title, governance_action, verification_command) in enumerate(items, start=1)
        ],
        "release_gate_commands": [
            ["cleanmac", "--json", "capabilities"],
            ["cleanmac", "--json", "governance-integrity"],
            ["make", "governance-smoke"],
            ["make", "governance-integrity-smoke"],
            ["make", "ai-first-release-checklist-smoke"],
        ],
    }


def render_boundary_governance() -> dict[str, Any]:
    runtime_lifecycle = render_runtime_lifecycle_policy()
    zero_resident_contract = render_zero_resident_contract(runtime_lifecycle=runtime_lifecycle)
    product_surface_drift_audit = render_product_surface_drift_audit()
    development_governance_todo = render_development_governance_todo()
    return {
        "schema": "cleanmac.boundary-governance.v1",
        "purpose": "Define safe automation boundaries for cleanup operations.",
        "runtime_lifecycle": runtime_lifecycle,
        "zero_resident_contract": zero_resident_contract,
        "zero_resident_audit": render_zero_resident_audit(
            runtime_lifecycle=runtime_lifecycle,
            zero_resident_contract=zero_resident_contract,
            product_surface_drift_audit=product_surface_drift_audit,
        ),
        "product_surface_drift_audit": product_surface_drift_audit,
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
        "development_governance_todo": development_governance_todo,
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
                "make governance-integrity-smoke",
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


def render_zero_resident_contract(*, runtime_lifecycle: dict[str, Any] | None = None) -> dict[str, Any]:
    """Return the compact machine-verifiable zero-resident product contract."""

    lifecycle = dict(runtime_lifecycle or render_runtime_lifecycle_policy())
    expected = {
        "resident_processes_expected": 0,
        "background_cpu_expected": 0,
        "background_memory_expected": 0,
        "login_items_created": False,
        "launch_agents_created": False,
        "launch_daemons_created": False,
        "auto_scan_enabled": False,
        "implements_tui": False,
        "implements_gui": False,
        "lifecycle": "single-shot",
    }
    evidence = {
        "resident_processes": lifecycle.get("resident_processes"),
        "background_cpu_policy": lifecycle.get("background_cpu_policy"),
        "background_memory_policy": lifecycle.get("background_memory_policy"),
        "login_items_created": lifecycle.get("installs_login_item"),
        "launch_agents_created": lifecycle.get("installs_background_daemon"),
        "launch_daemons_created": lifecycle.get("installs_background_daemon"),
        "auto_scan_enabled": lifecycle.get("performs_unsolicited_scans"),
        "implements_tui": lifecycle.get("implements_tui"),
        "implements_gui": lifecycle.get("implements_gui"),
        "lifecycle": "single-shot" if lifecycle.get("exits_after_workflow") is True else "resident-or-unknown",
    }
    evidence_key_by_expected_field = {
        "resident_processes_expected": "resident_processes",
        "background_cpu_expected": "background_cpu_expected",
        "background_memory_expected": "background_memory_expected",
        "login_items_created": "login_items_created",
        "launch_agents_created": "launch_agents_created",
        "launch_daemons_created": "launch_daemons_created",
        "auto_scan_enabled": "auto_scan_enabled",
        "implements_tui": "implements_tui",
        "implements_gui": "implements_gui",
        "lifecycle": "lifecycle",
    }
    evidence["background_cpu_expected"] = 0 if lifecycle.get("background_cpu_policy") == "zero-when-not-invoked" else None
    evidence["background_memory_expected"] = 0 if lifecycle.get("background_memory_policy") == "zero-when-not-invoked" else None
    failed_fields = [
        field for field, value in expected.items() if evidence.get(evidence_key_by_expected_field[field]) != value
    ]
    return {
        "schema": "cleanmac.zero-resident.v1",
        "destructive": False,
        "dry_run": True,
        "ready": not failed_fields,
        "product_model": lifecycle.get("product_model"),
        **expected,
        "evidence": evidence,
        "failed_fields": failed_fields,
        "stop_reason": "" if not failed_fields else "zero-resident contract failed: " + ", ".join(failed_fields),
        "next_action": "Run make zero-resident-audit-smoke before release readiness.",
        "release_gate_commands": [["cleanmac", "--json", "zero-resident"], ["make", "zero-resident-audit-smoke"]],
    }


@lru_cache(maxsize=4)
def _product_surface_drift_violations(project_root: str) -> tuple[str, ...]:
    root = Path(project_root).resolve(strict=False)
    from scripts import security_scan

    violations: list[str] = []
    for path in security_scan.iter_repo_files(root):
        relative = path.relative_to(root)
        violations.extend(security_scan.scan_product_surface_text(root, path))
        if path.suffix == ".py":
            violations.extend(
                violation
                for violation in security_scan.scan_python_ast(root, path)
                if "forbidden" in violation
                or "autostart" in violation
                or "LaunchAgent" in violation
                or "LaunchDaemon" in violation
            )
        if security_scan.is_workflow_file(relative):
            violations.extend(
                violation
                for violation in security_scan.scan_workflow_file(root, path)
                if "LaunchAgent" in violation or "LaunchDaemon" in violation or "login" in violation.lower()
            )
    return tuple(violations)


def render_product_surface_drift_audit(*, project_root: Path | None = None) -> dict[str, Any]:
    """Return a static drift audit for forbidden GUI/TUI/resident product surfaces."""

    root = (project_root or Path(__file__).resolve().parent.parent).resolve(strict=False)
    scan_available = (root / "scripts" / "security_scan.py").is_file()
    scan_warning = ""
    if scan_available:
        try:
            violations = list(_product_surface_drift_violations(str(root)))
        except Exception as exc:  # pragma: no cover - defensive guard for unexpected scanner errors.
            violations = [f"product-surface-drift-audit failed: {exc}"]
    else:
        violations = []
        scan_warning = "Repository security scanner is not packaged; release gates run this audit from source checkout."
    forbidden_dependency_families = list(render_product_surface_policy().get("forbidden_dependency_families", []))
    return {
        "schema": "cleanmac.product-surface-drift-audit.v1",
        "destructive": False,
        "dry_run": True,
        "ready": not violations,
        "scan_scope": "forbidden GUI/TUI dependencies, imports, LaunchAgent/LaunchDaemon/LoginItems, and resident product surfaces",
        "project_root": str(root),
        "scan_available": scan_available,
        "scan_warning": scan_warning,
        "forbidden_dependency_families": forbidden_dependency_families,
        "violation_count": len(violations),
        "violations": violations,
        "failed_check_ids": [] if not violations else ["forbidden-product-surface-drift"],
        "stop_reason": "" if not violations else "Forbidden GUI/TUI/resident product-surface drift detected.",
        "release_gate_commands": [["cleanmac", "--json", "product-surface-drift-audit"], ["python3", "scripts/security_scan.py"]],
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


def _governance_integrity_check(
    *,
    check_id: str,
    passed: bool,
    evidence: Any,
    expected: Any,
    remediation: str,
    remediation_commands: list[list[str]] | None = None,
) -> dict[str, Any]:
    return {
        "id": check_id,
        "passed": passed,
        "severity": "none" if passed else "blocking",
        "evidence": evidence,
        "expected": expected,
        "remediation": remediation,
        "remediation_commands": _unique_commands(remediation_commands or GOVERNANCE_INTEGRITY_REMEDIATION_COMMANDS),
    }


def render_governance_integrity_report(
    *,
    runtime_lifecycle: dict[str, Any],
    product_surface_policy: dict[str, Any],
    geo_discoverability_policy: dict[str, Any],
    boundary_governance: dict[str, Any],
    ai_tool_contract: dict[str, Any],
    product_positioning: dict[str, Any],
) -> dict[str, Any]:
    """Return a release-gateable consistency report for governance contracts."""

    discoverability_hints = ai_tool_contract.get("discoverability_hints", {})
    zero_resident_contract = boundary_governance.get("zero_resident_contract", {})
    zero_resident_audit = boundary_governance.get("zero_resident_audit", {})
    product_surface_drift_audit = boundary_governance.get("product_surface_drift_audit", {})
    checks = [
        _governance_integrity_check(
            check_id="boundary-runtime-lifecycle-single-source",
            passed=boundary_governance.get("runtime_lifecycle") == runtime_lifecycle,
            evidence=boundary_governance.get("runtime_lifecycle", {}).get("schema"),
            expected=runtime_lifecycle.get("schema"),
            remediation="Render boundary governance from the same runtime lifecycle policy used by capabilities.",
        ),
        _governance_integrity_check(
            check_id="boundary-product-surface-single-source",
            passed=boundary_governance.get("product_surface_policy") == product_surface_policy,
            evidence=boundary_governance.get("product_surface_policy", {}).get("schema"),
            expected=product_surface_policy.get("schema"),
            remediation="Render product surface policy once and reuse it across boundary and capabilities contracts.",
        ),
        _governance_integrity_check(
            check_id="boundary-geo-policy-single-source",
            passed=boundary_governance.get("geo_discoverability_policy") == geo_discoverability_policy,
            evidence=boundary_governance.get("geo_discoverability_policy", {}).get("schema"),
            expected=geo_discoverability_policy.get("schema"),
            remediation="Keep GEO discoverability metadata centralized in render_geo_discoverability_policy().",
        ),
        _governance_integrity_check(
            check_id="positioning-reuses-geo-summary",
            passed=product_positioning.get("canonical_summary") == geo_discoverability_policy.get("canonical_summary"),
            evidence=product_positioning.get("canonical_summary"),
            expected=geo_discoverability_policy.get("canonical_summary"),
            remediation="Use the GEO canonical summary as the capabilities product_positioning canonical summary.",
        ),
        _governance_integrity_check(
            check_id="positioning-reuses-geo-search-queries",
            passed=product_positioning.get("search_queries") == geo_discoverability_policy.get("primary_queries"),
            evidence=product_positioning.get("search_queries"),
            expected=geo_discoverability_policy.get("primary_queries"),
            remediation="Expose GEO primary queries directly as product_positioning.search_queries.",
        ),
        _governance_integrity_check(
            check_id="ai-contract-geo-entrypoints-covered",
            passed=all(
                entrypoint in discoverability_hints.get("best_entrypoints", [])
                for entrypoint in geo_discoverability_policy.get("ai_entrypoints", [])
            ),
            evidence=discoverability_hints.get("best_entrypoints", []),
            expected=geo_discoverability_policy.get("ai_entrypoints", []),
            remediation="Keep AI contract discoverability_hints.best_entrypoints aligned with the GEO policy.",
        ),
        _governance_integrity_check(
            check_id="ai-contract-forbidden-positioning-covered",
            passed=all(
                label in discoverability_hints.get("do_not_position_as", [])
                for label in geo_discoverability_policy.get("must_not_describe_as", [])
            ),
            evidence=discoverability_hints.get("do_not_position_as", []),
            expected=geo_discoverability_policy.get("must_not_describe_as", []),
            remediation="Keep AI contract forbidden positioning labels aligned with the GEO policy.",
        ),
        _governance_integrity_check(
            check_id="zero-resident-audit-ready",
            passed=zero_resident_audit.get("ready") is True,
            evidence=zero_resident_audit.get("readiness_score"),
            expected={"level": "ready"},
            remediation="Fix zero-resident audit failures before release or public positioning changes.",
        ),
        _governance_integrity_check(
            check_id="zero-resident-contract-ready",
            passed=zero_resident_contract.get("ready") is True,
            evidence={
                "schema": zero_resident_contract.get("schema"),
                "failed_fields": zero_resident_contract.get("failed_fields", []),
            },
            expected={"schema": "cleanmac.zero-resident.v1", "ready": True},
            remediation="Keep the compact zero-resident contract ready before release readiness.",
            remediation_commands=[
                ["cleanmac", "--json", "zero-resident"],
                ["make", "zero-resident-audit-smoke"],
                *GOVERNANCE_INTEGRITY_REMEDIATION_COMMANDS,
            ],
        ),
        _governance_integrity_check(
            check_id="product-surface-drift-audit-ready",
            passed=product_surface_drift_audit.get("ready") is True,
            evidence={
                "schema": product_surface_drift_audit.get("schema"),
                "violation_count": product_surface_drift_audit.get("violation_count"),
            },
            expected={"schema": "cleanmac.product-surface-drift-audit.v1", "violation_count": 0},
            remediation="Remove forbidden GUI/TUI dependencies, autostart files, or resident product-surface drift.",
            remediation_commands=[
                ["cleanmac", "--json", "product-surface-drift-audit"],
                ["python3", "scripts/security_scan.py"],
                *GOVERNANCE_INTEGRITY_REMEDIATION_COMMANDS,
            ],
        ),
        _governance_integrity_check(
            check_id="development-governance-todo-ordered",
            passed=(
                boundary_governance.get("development_governance_todo", {}).get("schema")
                == "cleanmac.development-governance-todo.v1"
                and boundary_governance.get("development_governance_todo", {}).get("item_count") == 25
                and [
                    item.get("order")
                    for item in boundary_governance.get("development_governance_todo", {}).get("items", [])
                ]
                == list(range(1, 26))
            ),
            evidence={
                "schema": boundary_governance.get("development_governance_todo", {}).get("schema"),
                "item_count": boundary_governance.get("development_governance_todo", {}).get("item_count"),
                "ordered": boundary_governance.get("development_governance_todo", {}).get("ordered"),
            },
            expected={
                "schema": "cleanmac.development-governance-todo.v1",
                "item_count": 25,
                "orders": list(range(1, 26)),
            },
            remediation="Keep the 25 AI-first governance TODO items present and in their approved order.",
        ),
    ]
    failed_check_ids = [check["id"] for check in checks if not check["passed"]]
    release_gate_commands = _unique_commands(GOVERNANCE_INTEGRITY_REMEDIATION_COMMANDS)
    failed_remediation_commands = _unique_commands(
        [command for check in checks if not check["passed"] for command in check["remediation_commands"]]
    )
    return {
        "schema": "cleanmac.governance-integrity.v1",
        "destructive": False,
        "dry_run": True,
        "ready": not failed_check_ids,
        "failed_check_ids": failed_check_ids,
        "stop_reason": "" if not failed_check_ids else "governance-integrity failed: " + ", ".join(failed_check_ids),
        "next_action": "Run make governance-integrity-smoke before release readiness.",
        "remediation_commands": failed_remediation_commands or release_gate_commands,
        "readiness_score": {
            "passed": len(checks) - len(failed_check_ids),
            "total": len(checks),
            "level": "ready" if not failed_check_ids else "blocked",
        },
        "checks": checks,
        "governed_contracts": [
            runtime_lifecycle.get("schema"),
            product_surface_policy.get("schema"),
            geo_discoverability_policy.get("schema"),
            boundary_governance.get("schema"),
            ai_tool_contract.get("schema"),
            product_positioning.get("schema"),
            zero_resident_contract.get("schema"),
            zero_resident_audit.get("schema"),
            product_surface_drift_audit.get("schema"),
            boundary_governance.get("development_governance_todo", {}).get("schema"),
        ],
        "release_gate_commands": release_gate_commands,
        "review_questions": [
            "Do all public positioning fields reuse the centralized GEO policy?",
            "Do AI contract hints agree with the GEO policy entrypoints and forbidden positioning labels?",
            "Does zero-resident audit remain ready before release?",
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


def _ai_first_release_check(
    *,
    check_id: str,
    passed: bool,
    evidence: Any,
    expected: Any,
    remediation: str,
    remediation_commands: list[list[str]],
) -> dict[str, Any]:
    return {
        "id": check_id,
        "passed": passed,
        "severity": "none" if passed else "blocking",
        "evidence": evidence,
        "expected": expected,
        "remediation": remediation,
        "remediation_commands": _unique_commands(remediation_commands),
    }


def render_ai_first_release_checklist(
    *,
    ai_host_integration_pack: dict[str, Any],
    ai_host_preflight: dict[str, Any],
    ai_host_evidence: dict[str, Any],
    governance_integrity: dict[str, Any],
    development_governance_todo: dict[str, Any],
    zero_resident_audit: dict[str, Any],
    product_surface_drift_audit: dict[str, Any],
    mcp_surface_audit: dict[str, Any],
    contract_validation: dict[str, Any],
) -> dict[str, Any]:
    """Return the release checklist that keeps publishing aligned with AI-first positioning."""

    contract_coverage = contract_validation.get("contract_schema_coverage", {})
    zero_resident_contract = zero_resident_audit.get("zero_resident_contract", {})
    entrypoint_contract = ai_host_integration_pack.get("entrypoint_contract", {})
    checks = [
        _ai_first_release_check(
            check_id="ai-host-entrypoints-ready",
            passed=all(
                payload.get("ready") is True
                for payload in (ai_host_integration_pack, ai_host_preflight, ai_host_evidence)
            ),
            evidence={
                "integration_pack_ready": ai_host_integration_pack.get("ready"),
                "entrypoint_contract_ready": entrypoint_contract.get("ready") if isinstance(entrypoint_contract, dict) else None,
                "preflight_ready": ai_host_preflight.get("ready"),
                "evidence_ready": ai_host_evidence.get("ready"),
            },
            expected={"ready": True},
            remediation="Keep AI Host integration pack, preflight, and evidence ready before release.",
            remediation_commands=[
                ["cleanmac", "--json", "ai-host-integration-pack"],
                ["cleanmac", "--json", "ai-host-preflight"],
                ["cleanmac", "--json", "ai-host-evidence"],
                ["make", "ai-host-smoke"],
            ],
        ),
        _ai_first_release_check(
            check_id="json-contracts-registered",
            passed=contract_validation.get("valid") is True
            and not contract_coverage.get("missing_stable_ai_schema_fragments")
            and not contract_coverage.get("missing_release_critical_contract_fragments"),
            evidence={
                "valid": contract_validation.get("valid"),
                "missing_stable_ai_schema_fragments": contract_coverage.get("missing_stable_ai_schema_fragments", []),
                "missing_release_critical_contract_fragments": contract_coverage.get(
                    "missing_release_critical_contract_fragments", []
                ),
            },
            expected={"valid": True, "missing_fragments": []},
            remediation="Register every AI-first and release-critical schema before publishing.",
            remediation_commands=[
                ["cleanmac", "--json", "ai-schema-registry"],
                ["cleanmac", "--json", "ai-contract-samples"],
                ["make", "ai-contract-smoke"],
            ],
        ),
        _ai_first_release_check(
            check_id="governance-integrity-ready",
            passed=governance_integrity.get("ready") is True,
            evidence={"failed_check_ids": governance_integrity.get("failed_check_ids", [])},
            expected={"ready": True, "failed_check_ids": []},
            remediation="Resolve governance integrity drift before AI-first release review.",
            remediation_commands=[
                ["cleanmac", "--json", "governance-integrity"],
                ["make", "governance-integrity-smoke"],
            ],
        ),
        _ai_first_release_check(
            check_id="development-governance-todo-ready",
            passed=development_governance_todo.get("schema") == "cleanmac.development-governance-todo.v1"
            and development_governance_todo.get("item_count") == 25
            and [
                item.get("order")
                for item in development_governance_todo.get("items", [])
            ]
            == list(range(1, 26)),
            evidence={
                "schema": development_governance_todo.get("schema"),
                "item_count": development_governance_todo.get("item_count"),
                "ordered": development_governance_todo.get("ordered"),
            },
            expected={
                "schema": "cleanmac.development-governance-todo.v1",
                "item_count": 25,
                "orders": list(range(1, 26)),
            },
            remediation="Keep the AI-first governance TODO contract ordered and release-gated.",
            remediation_commands=[
                ["cleanmac", "--json", "capabilities"],
                ["cleanmac", "--json", "governance-integrity"],
                ["make", "governance-smoke"],
                ["make", "governance-integrity-smoke"],
            ],
        ),
        _ai_first_release_check(
            check_id="zero-resident-contract-ready",
            passed=zero_resident_contract.get("ready") is True and zero_resident_audit.get("ready") is True,
            evidence={
                "zero_resident_contract_ready": zero_resident_contract.get("ready"),
                "zero_resident_audit_ready": zero_resident_audit.get("ready"),
            },
            expected={"zero_resident_contract_ready": True, "zero_resident_audit_ready": True},
            remediation="Keep cleanmac single-shot, non-resident, and explicit-invocation only.",
            remediation_commands=[
                ["cleanmac", "--json", "zero-resident"],
                ["cleanmac", "--json", "zero-resident-audit"],
                ["make", "zero-resident-audit-smoke"],
            ],
        ),
        _ai_first_release_check(
            check_id="product-surface-drift-clean",
            passed=product_surface_drift_audit.get("ready") is True
            and int(product_surface_drift_audit.get("violation_count") or 0) == 0,
            evidence={
                "ready": product_surface_drift_audit.get("ready"),
                "violation_count": product_surface_drift_audit.get("violation_count"),
            },
            expected={"ready": True, "violation_count": 0},
            remediation="Remove GUI/TUI, autostart, menu-bar, daemon, or resident product-surface drift.",
            remediation_commands=[
                ["cleanmac", "--json", "product-surface-drift-audit"],
                ["python3", "scripts/security_scan.py"],
            ],
        ),
        _ai_first_release_check(
            check_id="mcp-surface-audit-ready",
            passed=mcp_surface_audit.get("ready") is True,
            evidence={"failed_check_ids": mcp_surface_audit.get("failed_check_ids", [])},
            expected={"ready": True, "failed_check_ids": []},
            remediation="Keep MCP resources, prompts, and tools discoverable and safe for AI hosts.",
            remediation_commands=[
                ["cleanmac", "--json", "mcp-surface-audit"],
                ["make", "mcp-surface-audit-smoke"],
                ["make", "mcp-smoke"],
            ],
        ),
    ]
    failed_check_ids = [check["id"] for check in checks if not check["passed"]]
    release_gate_commands = _unique_commands(
        [
            ["cleanmac", "--json", "ai-first-release-checklist"],
            ["make", "ai-first-release-checklist-smoke"],
            ["make", "release-readiness-smoke"],
        ]
    )
    failed_remediation_commands = _unique_commands(
        [command for check in checks if not check["passed"] for command in check["remediation_commands"]]
    )
    return {
        "schema": "cleanmac.ai-first-release-checklist.v1",
        "destructive": False,
        "dry_run": True,
        "ready": not failed_check_ids,
        "failed_check_ids": failed_check_ids,
        "stop_reason": ""
        if not failed_check_ids
        else "ai-first-release-checklist failed: " + ", ".join(failed_check_ids),
        "next_action": "Run make ai-first-release-checklist-smoke before release readiness.",
        "readiness_score": {
            "passed": len(checks) - len(failed_check_ids),
            "total": len(checks),
            "level": "ready" if not failed_check_ids else "blocked",
        },
        "checks": checks,
        "remediation_commands": failed_remediation_commands or release_gate_commands,
        "release_gate_commands": release_gate_commands,
        "review_questions": [
            "Do AI Host entrypoints remain the primary release-review path?",
            "Are all 25 AI-first governance TODO items present, ordered, and governed?",
            "Are all AI-first and release-critical JSON contracts registered and sample-covered?",
            "Did zero-resident and product-surface drift audits pass before publish?",
        ],
    }


def render_zero_resident_audit(
    *,
    runtime_lifecycle: dict[str, Any] | None = None,
    zero_resident_contract: dict[str, Any] | None = None,
    product_surface_drift_audit: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Return a release-gateable audit proving cleanmac remains non-resident."""

    lifecycle = dict(runtime_lifecycle or render_runtime_lifecycle_policy())
    contract = dict(zero_resident_contract or render_zero_resident_contract(runtime_lifecycle=lifecycle))
    drift_audit = dict(product_surface_drift_audit or render_product_surface_drift_audit())
    forbidden_patterns = list(lifecycle.get("forbidden_product_patterns") or [])
    checks = [
        _zero_resident_check(
            check_id="zero-resident-contract-ready",
            passed=contract.get("ready") is True,
            evidence={"schema": contract.get("schema"), "failed_fields": contract.get("failed_fields", [])},
            expected={"schema": "cleanmac.zero-resident.v1", "ready": True},
            remediation="Restore the compact zero-resident contract before release readiness.",
        ),
        _zero_resident_check(
            check_id="product-surface-drift-audit-ready",
            passed=drift_audit.get("ready") is True,
            evidence={"schema": drift_audit.get("schema"), "violation_count": drift_audit.get("violation_count")},
            expected={"schema": "cleanmac.product-surface-drift-audit.v1", "ready": True, "violation_count": 0},
            remediation="Remove forbidden GUI/TUI dependencies, autostart surfaces, or resident product-surface drift.",
        ),
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
        "zero_resident_contract": contract,
        "product_surface_drift_audit": drift_audit,
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
    "render_ai_first_release_checklist",
    "render_capabilities",
    "render_development_governance_todo",
    "render_doctor",
    "render_geo_discoverability_policy",
    "render_governance_integrity_report",
    "render_product_surface_policy",
    "render_product_surface_drift_audit",
    "render_runtime_lifecycle_policy",
    "render_zero_resident_contract",
    "render_zero_resident_audit",
]
