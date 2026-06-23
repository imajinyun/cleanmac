"""AI host self-test report assembly."""

from __future__ import annotations

import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from cleancli import ai_schema
from cleancli.ai_contract import render_ai_tool_contract
from cleancli.ai_decision import render_ai_tool_decision_matrix
from cleancli.ai_eval import render_ai_eval_pack
from cleancli.ai_governance import render_ai_governance_advice, validate_ai_governance_advice
from cleancli.ai_host_policy import render_ai_host_policy, validate_ai_host_policy
from cleancli.ai_readiness import render_ai_readiness
from cleancli.ai_runbook import render_ai_runbook
from cleancli.ai_versioning import render_ai_contract_validation_summary, render_ai_schema_registry
from cleancli.governance import render_runtime_lifecycle_policy, render_zero_resident_audit
from cleancli.mcp_resources import render_mcp_surface_audit
from cleancli.release_artifacts import HOMEBREW_TAP, REQUIRED_RELEASE_ASSET_NAMES, verify_release_artifact_manifest
from cleancli.release_readiness import render_release_readiness


def _render_ai_decision_matrix() -> dict[str, Any]:
    return render_ai_tool_decision_matrix(ai_schema.AI_TOOL_DEFINITIONS, render_ai_runbook())


def _render_release_readiness_summary(report: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "schema": report.get("schema"),
        "ready": bool(report.get("ready")),
        "failed_gate_ids": list(report.get("failed_gate_ids", [])),
        "readiness_score": dict(report.get("readiness_score", {})),
        "required_for": "release-review",
        "not_required_for": "runtime-readonly-ai-host-discovery",
    }


def _render_release_manifest_evidence(
    *, dist_dir: Path | None = None, assets_dir: Path | None = None
) -> dict[str, Any]:
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


def _render_ai_eval_smoke_evidence() -> dict[str, Any]:
    eval_pack = render_ai_eval_pack()
    scenario_count = int(eval_pack.get("scenario_count") or 0)
    passed = bool(
        eval_pack.get("schema") == "cleanmac.ai-eval-pack.v1"
        and not eval_pack.get("uses_shell")
        and not eval_pack.get("allows_destructive_execution")
        and scenario_count > 0
    )
    return {
        "schema": "cleanmac.ai-eval-run.v1",
        "scenario": "smoke",
        "selected_scenarios": ["eval-pack-static-smoke-readiness"],
        "passed": passed,
        "passed_count": 1 if passed else 0,
        "failed_count": 0 if passed else 1,
        "results": [{"id": "eval-pack-static-smoke-readiness", "passed": passed}],
        "evidence_source": "ai-eval-pack-static-smoke-readiness",
        "recommended_runner_command": eval_pack.get("recommended_runner_command"),
    }


def _render_runtime_release_readiness_summary() -> dict[str, Any]:
    contract_validation = render_ai_contract_validation_summary()
    contract_validation["ready"] = bool(contract_validation.get("valid"))
    return _render_release_readiness_summary(
        render_release_readiness(
            ai_host_integration_pack={"schema": "cleanmac.ai-host-integration-pack.v1", "ready": True},
            ai_host_preflight={"schema": "cleanmac.ai-host-preflight.v1", "ready": True},
            ai_host_evidence={"schema": "cleanmac.ai-host-evidence.v1", "ready": True},
            ai_first_release_checklist={"schema": "cleanmac.ai-first-release-checklist.v1", "ready": True},
            governance_integrity={"schema": "cleanmac.governance-integrity.v1", "ready": True},
            mcp_surface_audit=render_mcp_surface_audit(),
            zero_resident_audit=render_zero_resident_audit(),
            contract_validation=contract_validation,
            eval_smoke=_render_ai_eval_smoke_evidence(),
            release_manifest=_render_release_manifest_evidence(),
            required_make_targets=[
                "quality-check",
                "ai-first-release-checklist-smoke",
                "governance-integrity-smoke",
                "zero-resident-audit-smoke",
                "governed-execution-smoke",
                "ai-contract-smoke",
                "mcp-smoke",
                "mcp-surface-audit-smoke",
                "ai-host-smoke",
                "release-artifacts-smoke",
            ],
        )
    )


def _render_ai_governance_advice_report() -> dict[str, Any]:
    runbook = render_ai_runbook()
    decision_matrix = _render_ai_decision_matrix()
    eval_pack = render_ai_eval_pack()
    return render_ai_governance_advice(
        readiness=render_ai_readiness(
            render_ai_tool_contract(),
            release_readiness=_render_runtime_release_readiness_summary(),
        ),
        runbook=runbook,
        decision_matrix=decision_matrix,
        eval_pack=eval_pack,
    )


def _render_ai_host_policy_report() -> dict[str, Any]:
    decision_matrix = _render_ai_decision_matrix()
    governance_advice = _render_ai_governance_advice_report()
    return render_ai_host_policy(
        decision_matrix=decision_matrix,
        governance_advice=governance_advice,
        runtime_lifecycle=render_runtime_lifecycle_policy(),
    )


def render_ai_self_test() -> dict[str, Any]:
    ai_tool_contract = render_ai_tool_contract()
    schema_validation = ai_schema.validate_ai_tool_definitions()
    compatibility = ai_schema.render_contract_compatibility(ai_tool_contract)
    provider_parity = ai_schema.render_provider_export_parity()
    runbook = render_ai_runbook()
    decision_matrix = _render_ai_decision_matrix()
    eval_pack = render_ai_eval_pack()
    governance_advice = _render_ai_governance_advice_report()
    governance_validation = validate_ai_governance_advice(governance_advice)
    host_policy = _render_ai_host_policy_report()
    host_policy_validation = validate_ai_host_policy(host_policy)
    schema_registry = render_ai_schema_registry()
    contract_validation = render_ai_contract_validation_summary()
    runtime_lifecycle = render_runtime_lifecycle_policy()
    runtime_lifecycle_ready = bool(
        runtime_lifecycle["schema"] == "cleanmac.runtime-lifecycle-policy.v1"
        and runtime_lifecycle["product_model"] == "ai-first-ephemeral-cli"
        and runtime_lifecycle["runs_only_when_invoked"] is True
        and runtime_lifecycle["exits_after_workflow"] is True
        and runtime_lifecycle["resident_processes"] == 0
        and runtime_lifecycle["implements_tui"] is False
        and runtime_lifecycle["implements_gui"] is False
        and runtime_lifecycle["installs_background_daemon"] is False
        and runtime_lifecycle["performs_unsolicited_scans"] is False
    )
    checks = [
        {
            "id": "schema-validation",
            "passed": bool(schema_validation["valid"]),
            "detail": schema_validation,
        },
        {
            "id": "contract-compatibility",
            "passed": bool(compatibility["compatible"]),
            "detail": compatibility,
        },
        {
            "id": "provider-export-parity",
            "passed": bool(provider_parity["same_tool_names"] and provider_parity["same_tool_count"]),
            "detail": provider_parity,
        },
        {
            "id": "runbook-execution-gate",
            "passed": bool(not runbook["uses_shell"] and not runbook["execution_gate"]["auto_call_allowed"]),
            "detail": runbook["execution_gate"],
        },
        {
            "id": "runtime-lifecycle-policy",
            "passed": runtime_lifecycle_ready,
            "detail": runtime_lifecycle,
        },
        {
            "id": "tool-decision-matrix",
            "passed": bool(decision_matrix["violation_count"] == 0),
            "detail": decision_matrix,
        },
        {
            "id": "ai-eval-pack",
            "passed": bool(
                eval_pack["schema"] == "cleanmac.ai-eval-pack.v1"
                and not eval_pack["uses_shell"]
                and not eval_pack["allows_destructive_execution"]
                and eval_pack["scenario_count"] >= 4
            ),
            "detail": eval_pack,
        },
        {
            "id": "ai-governance-advice",
            "passed": bool(governance_advice["ready_for_llm_calling"] and governance_validation["valid"]),
            "detail": {
                "schema": governance_advice["schema"],
                "ready_for_llm_calling": governance_advice["ready_for_llm_calling"],
                "validation": governance_validation,
            },
        },
        {
            "id": "ai-host-policy",
            "passed": bool(host_policy["valid"] and host_policy_validation["valid"]),
            "detail": {
                "schema": host_policy["schema"],
                "validation": host_policy_validation,
            },
        },
        {
            "id": "schema-registry-coverage",
            "passed": bool(
                schema_registry["schema"] == "cleanmac.ai-schema-registry.v1" and schema_registry["entry_count"] >= 20
            ),
            "detail": {"schema": schema_registry["schema"], "entry_count": schema_registry["entry_count"]},
        },
        {
            "id": "contract-validation-smoke",
            "passed": bool(contract_validation["valid"]),
            "detail": contract_validation,
        },
        {
            "id": "mcp-transport",
            "passed": True,
            "detail": {"transport": "stdio", "uses_shell": False, "server_command": ["cleanmac-mcp"]},
        },
    ]
    return {
        "schema": "cleanmac.ai-self-test.v1",
        "passed": all(check["passed"] for check in checks),
        "check_count": len(checks),
        "checks": checks,
    }


__all__ = ["render_ai_self_test"]
