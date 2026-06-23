"""AI-facing invocation contracts and workflow guidance."""

from __future__ import annotations

from typing import Any

from cleancli import ai_schema
from cleancli.ai_errors import render_ai_error_taxonomy
from cleancli.ai_policy import render_plan_policy
from cleancli.ai_versioning import CORE_CONTRACT_SCHEMAS, render_ai_schema_registry


AI_HOST_ENTRYPOINT_SCHEMAS: tuple[str, ...] = (
    "cleanmac.capabilities.v1",
    "cleanmac.workflow.v1",
    "cleanmac.explain.v1",
    "cleanmac.plan.v1",
    "cleanmac.review.v1",
    "cleanmac.validate-plan.v1",
)

AI_SAFETY_CHAIN_SCHEMAS: tuple[str, ...] = (
    "cleanmac.plan.v1",
    "cleanmac.plan-policy.v1",
    "cleanmac.validate-plan.v1",
    "cleanmac.review.v1",
    "cleanmac.review-selection.v1",
    "cleanmac.review-selection-constraint.v1",
    "cleanmac.review-selection-validation.v1",
    "cleanmac.ai-policy-simulation.v1",
    "cleanmac.clean.v1",
    "cleanmac.execute-gate.v1",
)


def render_execute_gate_contract() -> dict[str, Any]:
    """Return the non-bypassable destructive execution gate contract."""

    return {
        "schema": "cleanmac.execute-gate.v1",
        "destructive_tool": "cleanmac_execute_plan",
        "auto_call_allowed": False,
        "requires_human_confirmation": True,
        "requires_confirmation_phrase": True,
        "requires_matching_dry_run_confirmation_token": True,
        "requires_trash_delete_mode": True,
        "requires_operation_log": True,
        "requires_plan_context_match": True,
        "requires_fresh_non_drifted_plan": True,
        "requires_review_selection_validation": True,
        "required_predecessor_tools": [
            "cleanmac_generate_plan",
            "cleanmac_validate_plan",
            "cleanmac_policy_simulate",
            "cleanmac_dry_run_plan",
        ],
        "required_runtime_flags": [
            "--require-plan-context",
            "--delete-mode trash",
            "--operation-log",
            "--require-confirmation-token",
            "--confirmation-token",
            "--yes",
        ],
        "required_output_bindings": {
            "confirmation_token_source": "cleanmac_dry_run_plan.ai_confirmation_summary.confirmation_token",
            "operation_log_source": "explicit --operation-log path",
            "selection_source": "cleanmac.review-selection.v1 validated against source fingerprint",
        },
        "safe_argv_template": [
            "cleanmac",
            "--json",
            "clean",
            "run",
            "--plan-file",
            "{plan_file}",
            "--require-plan-context",
            "--delete-mode",
            "trash",
            "--review-selection-file",
            "{review_selection_file}",
            "--execute",
            "--yes",
            "--operation-log",
            "{operation_log}",
            "--require-confirmation-token",
            "--confirmation-token",
            "{confirmation_token_from_matching_dry_run}",
        ],
        "fail_closed_on": [
            "missing_human_confirmation",
            "missing_or_mismatched_confirmation_token",
            "plan_context_mismatch",
            "stale_or_drifted_plan",
            "review_selection_fingerprint_mismatch",
            "non_trash_delete_mode_for_ai_origin",
            "missing_operation_log",
        ],
    }


def render_ai_safety_chain_contract() -> dict[str, Any]:
    """Return the machine-verifiable plan/review/execute safety chain."""

    registry = render_ai_schema_registry()
    registry_entries = {str(entry["name"]): entry for entry in registry["entries"]}
    execute_gate = render_execute_gate_contract()
    plan_policy = render_plan_policy()
    chain_steps = [
        {
            "id": "plan",
            "tool": "cleanmac_generate_plan",
            "command": ["cleanmac", "--json", "plan", "--categories", "{categories}", "--ai-origin"],
            "output_schema": "cleanmac.plan.v1",
            "auto_call_allowed": True,
            "destructive": False,
            "must_precede": ["validate_plan", "review"],
        },
        {
            "id": "validate_plan",
            "tool": "cleanmac_validate_plan",
            "command": ["cleanmac", "--json", "validate-plan", "--plan-file", "{plan_file}"],
            "output_schema": "cleanmac.validate-plan.v1",
            "auto_call_allowed": True,
            "destructive": False,
            "must_precede": ["policy_simulate", "dry_run", "execute"],
        },
        {
            "id": "review",
            "tool": "cleanmac_review",
            "command": [
                "cleanmac",
                "--json",
                "review",
                "--input-file",
                "{plan_file}",
                "--selection-file",
                "{review_selection_file}",
            ],
            "output_schema": "cleanmac.review.v1",
            "produces": ["cleanmac.review.v1", "cleanmac.review-selection.v1"],
            "auto_call_allowed": True,
            "destructive": False,
            "must_precede": ["dry_run", "execute"],
        },
        {
            "id": "policy_simulate",
            "tool": "cleanmac_policy_simulate",
            "command": [
                "cleanmac",
                "--json",
                "policy-simulate",
                "--plan-file",
                "{plan_file}",
                "--execute",
                "--delete-mode",
                "trash",
                "--operation-log",
                "{operation_log}",
                "--require-plan-context",
                "--require-confirmation-token",
                "--confirmation-token",
                "{confirmation_token_from_matching_dry_run}",
                "--review-selection-file",
                "{review_selection_file}",
            ],
            "output_schema": "cleanmac.ai-policy-simulation.v1",
            "auto_call_allowed": True,
            "destructive": False,
            "must_precede": ["execute"],
        },
        {
            "id": "dry_run",
            "tool": "cleanmac_dry_run_plan",
            "command": [
                "cleanmac",
                "--json",
                "clean",
                "run",
                "--plan-file",
                "{plan_file}",
                "--require-plan-context",
                "--delete-mode",
                "trash",
                "--review-selection-file",
                "{review_selection_file}",
            ],
            "output_schema": "cleanmac.clean.v1",
            "required_output": "ai_confirmation_summary.confirmation_token",
            "auto_call_allowed": True,
            "destructive": False,
            "must_precede": ["execute"],
        },
        {
            "id": "execute",
            "tool": "cleanmac_execute_plan",
            "command": execute_gate["safe_argv_template"],
            "output_schema": "cleanmac.clean.v1",
            "auto_call_allowed": False,
            "destructive": True,
            "requires_gate_schema": "cleanmac.execute-gate.v1",
            "must_precede": [],
        },
    ]
    checks = []
    for schema_name in AI_SAFETY_CHAIN_SCHEMAS:
        checks.append(
            {
                "id": f"{schema_name}-schema-ready",
                "passed": bool(schema_name in registry_entries and schema_name in CORE_CONTRACT_SCHEMAS),
                "schema": schema_name,
                "schema_registered": schema_name in registry_entries,
                "contract_schema_available": schema_name in CORE_CONTRACT_SCHEMAS,
                "remediation_commands": [["cleanmac", "--json", "ai-schema-registry"], ["make", "ai-contract-smoke"]],
            }
        )
    checks.extend(
        [
            {
                "id": "execute-auto-call-denied",
                "passed": execute_gate["auto_call_allowed"] is False,
                "schema": "cleanmac.execute-gate.v1",
                "remediation_commands": [["cleanmac", "--json", "ai-safety-chain"], ["make", "ai-host-smoke"]],
            },
            {
                "id": "required-predecessors-complete",
                "passed": execute_gate["required_predecessor_tools"]
                == [
                    "cleanmac_generate_plan",
                    "cleanmac_validate_plan",
                    "cleanmac_policy_simulate",
                    "cleanmac_dry_run_plan",
                ],
                "schema": "cleanmac.execute-gate.v1",
                "remediation_commands": [["cleanmac", "--json", "ai-safety-chain"], ["make", "ai-host-smoke"]],
            },
        ]
    )
    missing_registry_entries = [schema for schema in AI_SAFETY_CHAIN_SCHEMAS if schema not in registry_entries]
    missing_schema_fragments = [schema for schema in AI_SAFETY_CHAIN_SCHEMAS if schema not in CORE_CONTRACT_SCHEMAS]
    ready = not missing_registry_entries and not missing_schema_fragments and all(check["passed"] for check in checks)
    return {
        "schema": "cleanmac.ai-safety-chain.v1",
        "destructive": False,
        "dry_run": True,
        "ready": ready,
        "purpose": "Machine-verifiable plan/review/dry-run/execute safety chain for AI Hosts.",
        "chain_id": "plan-review-dry-run-execute",
        "chain_step_count": len(chain_steps),
        "chain_steps": chain_steps,
        "required_contract_schemas": list(AI_SAFETY_CHAIN_SCHEMAS),
        "missing_registry_entries": missing_registry_entries,
        "missing_schema_fragments": missing_schema_fragments,
        "plan_policy": plan_policy,
        "execute_gate": execute_gate,
        "non_bypassable_edges": [
            ["plan", "validate_plan"],
            ["plan", "review"],
            ["review", "dry_run"],
            ["validate_plan", "policy_simulate"],
            ["policy_simulate", "execute"],
            ["dry_run", "execute"],
            ["human_confirmation", "execute"],
        ],
        "ai_host_obligations": [
            "Never auto-call cleanmac_execute_plan.",
            "Use only argv templates; never shell/raw command strings.",
            "Bind execute confirmation_token to the latest matching dry-run output.",
            "Use --delete-mode trash and --operation-log for AI-originated execution.",
            "Validate review-selection fingerprints before dry-run and execute.",
        ],
        "checks": checks,
        "readiness_score": {
            "passed": sum(1 for check in checks if check["passed"]),
            "total": len(checks),
            "level": "ready" if ready else "blocked",
        },
        "release_gate_commands": [
            ["cleanmac", "--json", "ai-safety-chain"],
            ["make", "ai-host-smoke"],
            ["make", "ai-contract-smoke"],
            ["make", "governed-execution-smoke"],
        ],
    }


def _entrypoint(
    *,
    entrypoint_id: str,
    command: list[str],
    output_schema: str,
    purpose: str,
    fallback: str,
    required_inputs: list[str] | None = None,
    produces: list[str] | None = None,
) -> dict[str, Any]:
    return {
        "id": entrypoint_id,
        "command": command,
        "uses_shell": False,
        "destructive": False,
        "dry_run": True,
        "auto_call_allowed": True,
        "output_schema": output_schema,
        "required_inputs": required_inputs or [],
        "produces": produces or [output_schema],
        "purpose": purpose,
        "version_compatibility": {
            "schema_family": output_schema.rsplit(".v", 1)[0],
            "latest_schema": output_schema,
            "compatible_major_versions": [1],
            "unknown_schema_strategy": "fail-closed-with-structured-error",
        },
        "fallback_strategy": {
            "on_cli_error": fallback,
            "on_unknown_schema": "Stop orchestration, emit cleanmac.ai-error.v1, and ask the user to upgrade or re-run discovery.",
            "on_missing_input": "Ask for the missing file/category input; do not infer paths or execute cleanup.",
        },
    }


def render_ai_entrypoint_contract() -> dict[str, Any]:
    """Return the stable AI Host contract for the canonical one-shot entrypoints."""

    registry = render_ai_schema_registry()
    registry_entries = {str(entry["name"]): entry for entry in registry["entries"]}
    entrypoints = [
        _entrypoint(
            entrypoint_id="discover_capabilities",
            command=["cleanmac", "--json", "capabilities"],
            output_schema="cleanmac.capabilities.v1",
            purpose="Discover categories, safety guardrails, product positioning, and AI Host integration metadata.",
            fallback="Run cleanmac --json ai-host-integration-pack, then cleanmac --json ai-schema-registry.",
        ),
        _entrypoint(
            entrypoint_id="workflow_guidance",
            command=["cleanmac", "--json", "workflow", "--categories", "{categories}"],
            output_schema="cleanmac.workflow.v1",
            purpose="Return the non-destructive one-shot workflow, UX guidance, automation playbook, and dry-run evidence.",
            fallback="Run cleanmac --json ai-workflow --categories {categories} for a compact governed tool order contract.",
            required_inputs=["categories"],
        ),
        _entrypoint(
            entrypoint_id="explain_report",
            command=["cleanmac", "--json", "explain", "--input-file", "{plan_or_report_file}"],
            output_schema="cleanmac.explain.v1",
            purpose="Explain a plan/report for a user without turning explanation into deletion.",
            fallback="Run cleanmac --json review --input-file {plan_or_report_file} for normalized candidate review.",
            required_inputs=["plan_or_report_file"],
        ),
        _entrypoint(
            entrypoint_id="generate_ai_origin_plan",
            command=["cleanmac", "--json", "plan", "--categories", "{categories}", "--ai-origin"],
            output_schema="cleanmac.plan.v1",
            purpose="Generate a reusable AI-origin cleanup plan with candidate fingerprints and confirmation context.",
            fallback="Run cleanmac --json clean inspect --categories {categories}, then retry plan generation with narrower filters.",
            required_inputs=["categories"],
        ),
        _entrypoint(
            entrypoint_id="normalize_review_selection",
            command=[
                "cleanmac",
                "--json",
                "review",
                "--input-file",
                "{plan_or_report_file}",
                "--selection-file",
                "{review_selection_file}",
            ],
            output_schema="cleanmac.review.v1",
            purpose="Normalize reviewable items and write a constrained review-selection file for later dry-run/execute handoff.",
            fallback="Regenerate review from the same source file; never expand selection beyond reviewed item IDs.",
            required_inputs=["plan_or_report_file", "review_selection_file"],
            produces=["cleanmac.review.v1", "cleanmac.review-selection.v1"],
        ),
        _entrypoint(
            entrypoint_id="validate_plan",
            command=["cleanmac", "--json", "validate-plan", "--plan-file", "{plan_file}"],
            output_schema="cleanmac.validate-plan.v1",
            purpose="Validate plan schema compatibility, categories, root/home context, freshness preview, and budget state.",
            fallback="Regenerate cleanmac.plan.v1 under the current root/home and repeat review before any dry-run or execute.",
            required_inputs=["plan_file"],
        ),
    ]
    checks = []
    for entrypoint_row in entrypoints:
        output_schema = str(entrypoint_row["output_schema"])
        checks.append(
            {
                "id": f"{entrypoint_row['id']}-schema-ready",
                "passed": bool(output_schema in registry_entries and output_schema in CORE_CONTRACT_SCHEMAS),
                "entrypoint": entrypoint_row["id"],
                "output_schema": output_schema,
                "schema_registered": output_schema in registry_entries,
                "contract_schema_available": output_schema in CORE_CONTRACT_SCHEMAS,
                "remediation_commands": [
                    ["cleanmac", "--json", "ai-schema-registry"],
                    ["cleanmac", "--json", "ai-contract-samples"],
                    ["make", "ai-contract-smoke"],
                ],
            }
        )
    missing_schema_fragments = [schema for schema in AI_HOST_ENTRYPOINT_SCHEMAS if schema not in CORE_CONTRACT_SCHEMAS]
    missing_registry_entries = [schema for schema in AI_HOST_ENTRYPOINT_SCHEMAS if schema not in registry_entries]
    return {
        "schema": "cleanmac.ai-entrypoint-contract.v1",
        "destructive": False,
        "dry_run": True,
        "ready": not missing_schema_fragments and not missing_registry_entries and all(check["passed"] for check in checks),
        "purpose": "Machine-verifiable contract for canonical AI Host entrypoints and their fail-closed fallback strategy.",
        "entrypoint_count": len(entrypoints),
        "entrypoint_ids": [str(row["id"]) for row in entrypoints],
        "entrypoints": entrypoints,
        "required_output_schemas": list(AI_HOST_ENTRYPOINT_SCHEMAS),
        "missing_registry_entries": missing_registry_entries,
        "missing_schema_fragments": missing_schema_fragments,
        "checks": checks,
        "readiness_score": {
            "passed": sum(1 for check in checks if check["passed"]),
            "total": len(checks),
            "level": "ready" if all(check["passed"] for check in checks) else "blocked",
        },
        "recommended_call_sequence": [
            ["cleanmac", "--json", "capabilities"],
            ["cleanmac", "--json", "workflow", "--categories", "{categories}"],
            ["cleanmac", "--json", "plan", "--categories", "{categories}", "--ai-origin"],
            ["cleanmac", "--json", "review", "--input-file", "{plan_file}", "--selection-file", "{review_selection_file}"],
            ["cleanmac", "--json", "validate-plan", "--plan-file", "{plan_file}"],
            ["cleanmac", "--json", "explain", "--input-file", "{plan_or_report_file}"],
        ],
        "release_gate_commands": [
            ["cleanmac", "--json", "ai-entrypoints"],
            ["make", "ai-host-smoke"],
            ["make", "ai-contract-smoke"],
        ],
    }


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
                ["cleanmac", "--json", "ai-entrypoints"],
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
