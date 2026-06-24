from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
CLI = PROJECT_ROOT / "cleanmac.py"


@pytest.fixture(scope="module")
def governance_report() -> dict[str, Any]:
    result = subprocess.run(
        [sys.executable, str(CLI), "--json", "ai-governance-advice"],
        text=True,
        capture_output=True,
        check=True,
    )
    return json.loads(result.stdout)


def test_governance_advice_schema(governance_report: dict[str, Any]) -> None:
    assert governance_report["schema"] == "cleanmac.ai-governance-advice.v1"


def test_governance_advice_ready_for_llm_calling(governance_report: dict[str, Any]) -> None:
    assert governance_report["ready_for_llm_calling"], governance_report


def test_governance_advice_default_policy(governance_report: dict[str, Any]) -> None:
    assert governance_report["governance_score"]["level"] == "strong"
    assert not governance_report["default_policy"]["shell_allowed"]
    assert "cleanmac_execute_plan" in governance_report["default_policy"]["auto_call_denied_tools"]
    assert "cleanmac_startup_disable" in governance_report["default_policy"]["auto_call_denied_tools"]
    assert "cleanmac_privacy_execute" in governance_report["default_policy"]["auto_call_denied_tools"]
    assert "cleanmac_capabilities" in governance_report["default_policy"]["auto_call_allowed_tools"]
    assert "cleanmac_execute_plan" in governance_report["default_policy"]["human_confirmation_required_for"]
    assert "cleanmac_privacy_execute" in governance_report["default_policy"]["human_confirmation_required_for"]


def test_governance_advice_required_host_controls_and_recommendations(
    governance_report: dict[str, Any],
) -> None:
    assert len(governance_report["required_host_controls"]) >= 5
    assert len(governance_report["recommendations"]) >= 5


def test_governance_advice_release_gate_commands(governance_report: dict[str, Any]) -> None:
    assert ["make", "ai-governance-smoke"] in governance_report["release_gate_commands"]
    assert ["make", "ai-contract-smoke"] in governance_report["release_gate_commands"]
    assert ["make", "ai-host-smoke"] in governance_report["release_gate_commands"]
    assert ["make", "release-readiness-smoke"] in governance_report["release_gate_commands"]
    assert ["cleanmac", "--json", "ai-host-policy"] in governance_report["release_gate_commands"]
    assert ["cleanmac", "--json", "ai-host-evidence"] in governance_report["release_gate_commands"]
    assert ["cleanmac", "--json", "release-readiness"] in governance_report["release_gate_commands"]


def test_governance_advice_recommendation_statuses(governance_report: dict[str, Any]) -> None:
    assert "read cleanmac://ai/host-policy" in governance_report["recommended_call_sequence"]
    assert "read cleanmac://ai/runtime-lifecycle-policy" in governance_report["recommended_call_sequence"]
    assert "read cleanmac://mcp/surface-audit" in governance_report["recommended_call_sequence"]
    assert "read cleanmac://ai/host-evidence" in governance_report["recommended_call_sequence"]
    assert "read cleanmac://release/readiness" in governance_report["recommended_call_sequence"]
    recommendations = {item["id"]: item for item in governance_report["recommendations"]}
    assert recommendations["preflight-first"]["priority"] == "p0"
    assert recommendations["deny-auto-destructive"]["status"] == "satisfied"
    assert "cleanmac_execute_plan" in recommendations["deny-auto-destructive"]["blocked_tools"]
    assert "cleanmac_privacy_execute" in recommendations["deny-auto-destructive"]["blocked_tools"]
    assert recommendations["dry-run-token-gate"]["status"] == "satisfied"
    assert "cleanmac_dry_run_plan" in recommendations["dry-run-token-gate"]["required_before_execute"]
    assert "Skipping ai-eval-run smoke" in "\n".join(governance_report["anti_patterns"])
    assert "cleanmac.ai-host-policy.v1" in "\n".join(governance_report["anti_patterns"])
    assert "ai-readiness.ready=true" in "\n".join(governance_report["anti_patterns"])
    assert "failed_gate_ids" in "\n".join(governance_report["anti_patterns"])
    assert "resident GUI" in "\n".join(governance_report["anti_patterns"])
    assert "cleanmac://mcp/surface-audit" in "\n".join(governance_report["required_host_controls"])
    assert "cleanmac://ai/runtime-lifecycle-policy" in "\n".join(governance_report["required_host_controls"])


def test_governance_advice_governance_route_all_satisfied(governance_report: dict[str, Any]) -> None:
    route = {item["id"]: item for item in governance_report["governance_route"]}
    assert len(route) >= 10
    assert all(item["status"] == "satisfied" for item in route.values()), route
    assert "ci-release-gate" in route
    assert "audit-traceability" in route


def test_governance_advice_marks_incomplete_inputs_needs_attention() -> None:
    from cleancli.ai_governance import render_ai_governance_advice

    report = render_ai_governance_advice(
        readiness={"ready": False, "eval_pack": {"ready": False}},
        runbook={"uses_shell": True, "default_mode": "execute-first", "execution_gate": "invalid"},
        decision_matrix={
            "violation_count": 2,
            "violations": ["unsafe auto-call"],
            "tools": [
                {"name": "cleanmac_capabilities", "risk": "readonly", "auto_call_allowed": True},
                {"name": "cleanmac_execute_plan", "risk": "destructive", "auto_call_allowed": True},
                "not-a-tool-row",
            ],
        },
        eval_pack={"schema": "cleanmac.ai-eval-pack.v1", "allows_destructive_execution": True, "scenarios": []},
    )

    assert report["schema"] == "cleanmac.ai-governance-advice.v1"
    assert not report["ready_for_llm_calling"]
    assert report["governance_score"] == {"passed": 0, "total": 4, "level": "partial"}

    recommendations = {item["id"]: item for item in report["recommendations"]}
    assert recommendations["preflight-first"]["status"] == "needs_attention"
    assert recommendations["deny-auto-destructive"]["status"] == "needs_attention"
    assert recommendations["argv-only-transport"]["status"] == "needs_attention"
    assert recommendations["dry-run-token-gate"]["status"] == "needs_attention"
    assert recommendations["trace-and-eval-regression"]["status"] == "needs_attention"
    assert recommendations["structured-error-recovery"]["status"] == "needs_attention"

    route = {item["id"]: item for item in report["governance_route"]}
    assert route["prompt-injection-boundary"]["status"] == "needs_attention"
    assert route["mcp-host-governance"]["status"] == "needs_attention"
    assert route["audit-traceability"]["status"] == "needs_attention"


def test_governance_validation_reports_structural_violations() -> None:
    from cleancli.ai_governance import validate_ai_governance_advice

    validation = validate_ai_governance_advice(
        {
            "schema": "cleanmac.not-governance.v1",
            "default_policy": "invalid",
            "recommendations": "invalid",
            "governance_route": "invalid",
            "release_gate_commands": [],
        }
    )

    assert validation["schema"] == "cleanmac.ai-governance-advice-validation.v1"
    assert not validation["valid"]
    assert "schema must be cleanmac.ai-governance-advice.v1" in validation["violations"]
    assert "default_policy must be an object" in validation["violations"]
    assert "recommendations must be a sequence" in validation["violations"]
    assert "governance_route must be a sequence" in validation["violations"]
    assert "release_gate_commands must include make ai-governance-smoke" in validation["violations"]


def test_governance_validation_reports_unsatisfied_route_and_policy_gaps() -> None:
    from cleancli.ai_governance import validate_ai_governance_advice

    validation = validate_ai_governance_advice(
        {
            "schema": "cleanmac.ai-governance-advice.v1",
            "default_policy": {"shell_allowed": True, "auto_call_denied_tools": []},
            "recommendations": [{"id": str(index)} for index in range(4)],
            "governance_route": [{"id": str(index), "status": "satisfied"} for index in range(9)]
            + [{"id": "blocked", "status": "needs_attention"}],
            "release_gate_commands": [["make", "ai-governance-smoke"]],
        }
    )

    assert not validation["valid"]
    joined = "\n".join(validation["violations"])
    assert "shell_allowed must be false" in joined
    assert "cleanmac_execute_plan must be denied for auto-call" in joined
    assert "recommendations must include at least five governance controls" in joined
    assert "governance_route contains unsatisfied items: blocked" in joined


def test_governance_validation_requires_ten_route_items() -> None:
    from cleancli.ai_governance import validate_ai_governance_advice

    validation = validate_ai_governance_advice(
        {
            "schema": "cleanmac.ai-governance-advice.v1",
            "default_policy": {"shell_allowed": False, "auto_call_denied_tools": ["cleanmac_execute_plan"]},
            "recommendations": [{"id": str(index)} for index in range(5)],
            "governance_route": [{"id": str(index), "status": "satisfied"} for index in range(9)],
            "release_gate_commands": [["make", "ai-governance-smoke"]],
        }
    )

    assert not validation["valid"]
    assert "governance_route must cover the ten governance route items" in validation["violations"]
