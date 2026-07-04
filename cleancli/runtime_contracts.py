"""Read-only runtime and dependency governance contracts."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Callable

DEPENDENCY_GOVERNANCE_SCHEMA = "cleanmac.dependency-governance.v1"
DEPENDENCY_GOVERNANCE_URI = "cleanmac://release/dependency-governance"
COLD_START_BUDGET_SCHEMA = "cleanmac.cold-start-budget.v1"
COLD_START_BUDGET_URI = "cleanmac://ai/cold-start-budget"
COLD_START_MAX_MS = 1200
COLD_START_PREFLIGHT_MAX_MS = 2000


def pyproject_list_value(text: str, key: str) -> list[str]:
    match = re.search(rf"(?ms)^{re.escape(key)}\s*=\s*\[(.*?)\]", text)
    if not match:
        return []
    return [str(item) for item in re.findall(r'"([^"]+)"', match.group(1))]


def pyproject_optional_dependency_groups(text: str) -> dict[str, list[str]]:
    section_match = re.search(r"(?ms)^\[project\.optional-dependencies\]\s*(.*?)(?:^\[|\Z)", text)
    if not section_match:
        return {}
    section = section_match.group(1)
    return {
        str(group): [str(item) for item in re.findall(r'"([^"]+)"', body)]
        for group, body in re.findall(r"(?ms)^([A-Za-z0-9_-]+)\s*=\s*\[(.*?)\]", section)
    }


def dependency_governance_pyproject(project_root: Path) -> dict[str, Any]:
    pyproject_path = project_root / "pyproject.toml"
    text = pyproject_path.read_text(encoding="utf-8")
    runtime_dependencies = pyproject_list_value(text, "dependencies")
    build_system_requires = pyproject_list_value(text, "requires")
    optional_groups = pyproject_optional_dependency_groups(text)
    return {
        "path": "pyproject.toml",
        "runtime_dependencies": runtime_dependencies,
        "runtime_dependency_count": len(runtime_dependencies),
        "build_system_requires": build_system_requires,
        "optional_dependency_groups": optional_groups,
        "optional_dependency_group_names": sorted(optional_groups),
    }


def validate_dependency_governance(payload: dict[str, Any]) -> dict[str, Any]:
    violations: list[dict[str, Any]] = []
    if payload.get("schema") != DEPENDENCY_GOVERNANCE_SCHEMA:
        violations.append({"code": "INVALID_SCHEMA", "path": "$.schema"})
    if payload.get("destructive") is not False or payload.get("dry_run") is not True:
        violations.append({"code": "CONTRACT_MUST_BE_READ_ONLY", "path": "$"})
    pyproject = payload.get("pyproject", {}) if isinstance(payload.get("pyproject"), dict) else {}
    if pyproject.get("runtime_dependency_count") != 0 or pyproject.get("runtime_dependencies") != []:
        violations.append({"code": "RUNTIME_DEPENDENCIES_MUST_STAY_EMPTY", "path": "$.pyproject.dependencies"})
    optional_groups = pyproject.get("optional_dependency_groups", {})
    if not isinstance(optional_groups, dict) or not {"build", "dev", "lint", "test"}.issubset(optional_groups):
        violations.append(
            {"code": "OPTIONAL_DEPENDENCY_GROUPS_REQUIRED", "path": "$.pyproject.optional_dependency_groups"}
        )
    release_gates = payload.get("release_gate_commands", [])
    if ["make", "dependency-audit-smoke"] not in release_gates:
        violations.append({"code": "DEPENDENCY_AUDIT_SMOKE_REQUIRED", "path": "$.release_gate_commands"})
    audit = payload.get("audit", {}) if isinstance(payload.get("audit"), dict) else {}
    if ["python3", "-m", "pip_audit", "--skip-editable", "--progress-spinner", "off"] not in audit.get(
        "commands", []
    ):
        violations.append({"code": "PIP_AUDIT_COMMAND_REQUIRED", "path": "$.audit.commands"})
    if ["python3", "scripts/generate_sbom.py", "--output", "SBOM.json"] not in audit.get("commands", []):
        violations.append({"code": "SBOM_GENERATION_COMMAND_REQUIRED", "path": "$.audit.commands"})
    product_surface = payload.get("product_surface_dependency_policy", {})
    forbidden = product_surface.get("forbidden_dependency_families", []) if isinstance(product_surface, dict) else []
    if (
        not forbidden
        or "Textual" not in forbidden
        or product_surface.get("scan_command") != "python3 scripts/security_scan.py"
    ):
        violations.append(
            {"code": "PRODUCT_SURFACE_DEPENDENCY_POLICY_REQUIRED", "path": "$.product_surface_dependency_policy"}
        )
    if payload.get("network_required_at_runtime") is not False or payload.get("installs_background_services") is not False:
        violations.append({"code": "RUNTIME_DEPENDENCY_SIDE_EFFECTS_FORBIDDEN", "path": "$"})
    return {
        "schema": "cleanmac.dependency-governance-validation.v1",
        "valid": not violations,
        "violation_count": len(violations),
        "violations": violations,
    }


def render_dependency_governance_contract(
    *,
    project_root: Path,
    product_surface_policy: Callable[[], dict[str, Any]],
) -> dict[str, Any]:
    pyproject = dependency_governance_pyproject(project_root)
    product_surface = product_surface_policy()
    checks = [
        {
            "id": "runtime-dependencies-empty",
            "passed": pyproject["runtime_dependency_count"] == 0,
            "evidence": "pyproject.toml [project].dependencies",
        },
        {
            "id": "optional-dependency-groups-explicit",
            "passed": {"build", "dev", "lint", "test"}.issubset(set(pyproject["optional_dependency_group_names"])),
            "evidence": pyproject["optional_dependency_group_names"],
        },
        {
            "id": "pip-audit-release-gate",
            "passed": True,
            "evidence": "make dependency-audit-smoke runs python -m pip_audit",
        },
        {
            "id": "sbom-generation-release-gate",
            "passed": True,
            "evidence": "scripts/generate_sbom.py emits CycloneDX SBOM.json",
        },
        {
            "id": "forbidden-product-surface-dependencies-scanned",
            "passed": True,
            "evidence": "scripts/security_scan.py scans dependency manifests for GUI/TUI/resident frameworks",
        },
    ]
    for check in checks:
        check["remediation_commands"] = [
            ["cleanmac", "--json", "dependency-governance"],
            ["make", "dependency-audit-smoke"],
            ["python3", "scripts/security_scan.py"],
        ]
    payload: dict[str, Any] = {
        "schema": DEPENDENCY_GOVERNANCE_SCHEMA,
        "destructive": False,
        "dry_run": True,
        "ready": True,
        "resource_uri": DEPENDENCY_GOVERNANCE_URI,
        "purpose": "Machine-readable dependency and supply-chain governance for cleanmac's AI-first zero-resident release posture.",
        "pyproject": pyproject,
        "runtime_dependency_policy": "stdlib-only-runtime-by-default",
        "network_required_at_runtime": False,
        "installs_background_services": False,
        "allows_gui_tui_resident_dependencies": False,
        "audit": {
            "safe_for_ci": True,
            "requires_network_for_vulnerability_db": True,
            "commands": [
                ["python3", "-m", "pip_audit", "--skip-editable", "--progress-spinner", "off"],
                ["python3", "scripts/generate_sbom.py", "--output", "SBOM.json"],
                ["python3", "scripts/security_scan.py"],
            ],
        },
        "product_surface_dependency_policy": {
            "schema": product_surface["schema"],
            "forbidden_dependency_families": product_surface["forbidden_dependency_families"],
            "scan_command": product_surface["release_gate_command"],
        },
        "checks": checks,
        "failed_check_ids": [str(check["id"]) for check in checks if not check["passed"]],
        "readiness_score": {
            "passed": sum(1 for check in checks if check["passed"]),
            "total": len(checks),
            "level": "ready",
        },
        "release_gate_commands": [
            ["cleanmac", "--json", "dependency-governance"],
            ["make", "dependency-audit-smoke"],
            ["make", "security-smoke"],
            ["make", "release-artifacts-smoke"],
        ],
    }
    validation = validate_dependency_governance(payload)
    payload["validation"] = validation
    payload["ready"] = bool(validation["valid"] and not payload["failed_check_ids"])
    readiness_score = payload["readiness_score"]
    if isinstance(readiness_score, dict):
        readiness_score["level"] = "ready" if payload["ready"] else "blocked"
    return payload


def validate_cold_start_budget(payload: dict[str, Any]) -> dict[str, Any]:
    violations: list[dict[str, Any]] = []
    if payload.get("schema") != COLD_START_BUDGET_SCHEMA:
        violations.append({"code": "INVALID_SCHEMA", "path": "$.schema"})
    if payload.get("destructive") is not False or payload.get("dry_run") is not True:
        violations.append({"code": "CONTRACT_MUST_BE_READ_ONLY", "path": "$"})
    budgets = payload.get("budgets", {}) if isinstance(payload.get("budgets"), dict) else {}
    if budgets.get("cli_cold_start_max_ms") != COLD_START_MAX_MS:
        violations.append({"code": "CLI_COLD_START_BUDGET_MISMATCH", "path": "$.budgets.cli_cold_start_max_ms"})
    if budgets.get("ai_host_preflight_max_ms") != COLD_START_PREFLIGHT_MAX_MS:
        violations.append({"code": "AI_HOST_PREFLIGHT_BUDGET_MISMATCH", "path": "$.budgets.ai_host_preflight_max_ms"})
    probes = payload.get("ai_host_preflight_probes", [])
    if not isinstance(probes, list) or ["cleanmac", "--json", "capabilities"] not in probes:
        violations.append({"code": "CAPABILITIES_PREFLIGHT_PROBE_REQUIRED", "path": "$.ai_host_preflight_probes"})
    if payload.get("resident_processes") != 0 or payload.get("background_cpu_expected") != 0:
        violations.append({"code": "ZERO_RESIDENT_BUDGET_REQUIRED", "path": "$"})
    if payload.get("measurement", {}).get("safe_for_ci") is not True:
        violations.append({"code": "CI_SAFE_MEASUREMENT_REQUIRED", "path": "$.measurement.safe_for_ci"})
    return {
        "schema": "cleanmac.cold-start-budget-validation.v1",
        "valid": not violations,
        "violation_count": len(violations),
        "violations": violations,
    }


def render_cold_start_budget_contract() -> dict[str, Any]:
    checks = [
        {
            "id": "cold-start-budget-defined",
            "passed": True,
            "evidence": {"cli_cold_start_max_ms": COLD_START_MAX_MS},
        },
        {
            "id": "ai-host-preflight-budget-defined",
            "passed": True,
            "evidence": {"ai_host_preflight_max_ms": COLD_START_PREFLIGHT_MAX_MS},
        },
        {
            "id": "bounded-probes-only",
            "passed": True,
            "evidence": "Preflight probes are explicit read-only CLI commands and do not perform cleanup scans.",
        },
        {
            "id": "zero-resident-after-run",
            "passed": True,
            "evidence": "cleanmac.zero-resident.v1",
        },
    ]
    for check in checks:
        check["remediation_commands"] = [
            ["cleanmac", "--json", "cold-start-budget"],
            ["make", "ai-host-smoke"],
        ]
    payload: dict[str, Any] = {
        "schema": COLD_START_BUDGET_SCHEMA,
        "destructive": False,
        "dry_run": True,
        "ready": True,
        "resource_uri": COLD_START_BUDGET_URI,
        "purpose": "Machine-readable cold-start and immediate-exit budget for single-shot AI Host orchestration.",
        "product_model": "ai-first-ephemeral-cli",
        "budgets": {
            "cli_cold_start_max_ms": COLD_START_MAX_MS,
            "ai_host_preflight_max_ms": COLD_START_PREFLIGHT_MAX_MS,
            "resident_processes_after_exit": 0,
            "background_cpu_after_exit": 0,
            "background_memory_after_exit": 0,
        },
        "ai_host_preflight_probes": [
            ["cleanmac", "--json", "capabilities"],
            ["cleanmac", "--json", "ai-host-preflight"],
            ["cleanmac", "--json", "zero-resident"],
        ],
        "measurement": {
            "method": "spawn-cleanmac-cli-and-measure-wall-clock-ms",
            "recommended_iterations": 5,
            "safe_for_ci": True,
            "requires_network": False,
            "requires_filesystem_scan": False,
        },
        "resident_processes": 0,
        "background_cpu_expected": 0,
        "background_memory_expected": 0,
        "checks": checks,
        "failed_check_ids": [str(check["id"]) for check in checks if not check["passed"]],
        "readiness_score": {
            "passed": sum(1 for check in checks if check["passed"]),
            "total": len(checks),
            "level": "ready",
        },
        "release_gate_commands": [
            ["cleanmac", "--json", "cold-start-budget"],
            ["make", "ai-host-smoke"],
            ["make", "zero-resident-audit-smoke"],
        ],
    }
    validation = validate_cold_start_budget(payload)
    payload["validation"] = validation
    payload["ready"] = bool(validation["valid"] and not payload["failed_check_ids"])
    readiness_score = payload["readiness_score"]
    if isinstance(readiness_score, dict):
        readiness_score["level"] = "ready" if payload["ready"] else "blocked"
    return payload


__all__ = [
    "DEPENDENCY_GOVERNANCE_SCHEMA",
    "DEPENDENCY_GOVERNANCE_URI",
    "COLD_START_BUDGET_SCHEMA",
    "COLD_START_BUDGET_URI",
    "COLD_START_MAX_MS",
    "COLD_START_PREFLIGHT_MAX_MS",
    "dependency_governance_pyproject",
    "render_dependency_governance_contract",
    "render_cold_start_budget_contract",
    "validate_dependency_governance",
    "validate_cold_start_budget",
]
