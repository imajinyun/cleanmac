from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from unittest.mock import patch

PROJECT_ROOT = Path(__file__).resolve().parent.parent
CLI = PROJECT_ROOT / "cleanmac.py"


def test_ai_readiness_reports_host_integration_status() -> None:
    result = subprocess.run(
        [sys.executable, str(CLI), "--json", "ai-readiness"],
        text=True,
        capture_output=True,
        check=True,
    )
    report = json.loads(result.stdout)

    assert report["schema"] == "cleanmac.ai-readiness.v1"
    assert report["ready"], report
    assert report["tool_count"] == report["provider_exports"]["openai_tool_count"]
    assert report["tool_count"] == report["provider_exports"]["anthropic_tool_count"]
    assert report["contracts"]["schema_validation"]["valid"]
    assert report["contracts"]["contract_compatibility"]["compatible"]
    assert report["contracts"]["provider_export_parity"]["same_tool_names"]
    assert report["mcp"]["server_command"] == ["cleanmac-mcp"]
    assert report["decision_matrix"]["ready"]
    assert report["decision_matrix"]["schema"] == "cleanmac.ai-tool-decision-matrix.v1"
    assert report["decision_matrix"]["violation_count"] == 0
    assert report["eval_pack"]["ready"]
    assert report["eval_pack"]["schema"] == "cleanmac.ai-eval-pack.v1"
    assert report["eval_pack"]["scenario_count"] >= 4
    assert report["eval_runner"]["default_scenario"] == "smoke"
    assert not report["eval_runner"]["destructive_execution_allowed"]
    assert report["runtime_lifecycle"]["ready"]
    assert report["runtime_lifecycle"]["schema"] == "cleanmac.runtime-lifecycle-policy.v1"
    assert report["runtime_lifecycle"]["resource_uri"] == "cleanmac://ai/runtime-lifecycle-policy"
    assert report["runtime_lifecycle"]["product_model"] == "ai-first-ephemeral-cli"
    assert report["runtime_lifecycle"]["resident_processes"] == 0
    assert report["governance_advice"]["ready"]
    assert report["governance_advice"]["schema"] == "cleanmac.ai-governance-advice.v1"
    assert report["governance_advice"]["level"] == "strong"
    assert report["host_policy"]["ready"]
    assert report["host_policy"]["schema"] == "cleanmac.ai-host-policy.v1"
    assert report["host_policy"]["default_decision"] == "deny"
    assert report["schema_registry"]["ready"]
    assert report["schema_registry"]["schema"] == "cleanmac.ai-schema-registry.v1"
    assert report["schema_registry"]["latest_plan_schema"] == "cleanmac.plan.v1"
    assert report["schema_registry"]["supported_plan_schemas_registered"]
    assert report["schema_registry"]["core_contract_schemas_present"]
    assert report["schema_registry"]["deprecated_schema_count"] == 0
    assert report["contract_validation"]["ready"]
    assert report["contract_validation"]["schema"] == "cleanmac.ai-contract-validation-summary.v1"
    assert report["contract_validation"]["validated_schema_count"] >= 2
    assert report["contract_validation"]["failure_count"] == 0
    assert report["destructive_tool_governance"]["ready"], report["destructive_tool_governance"]
    assert "cleanmac_execute_plan" in report["destructive_tool_governance"]["destructive_tool_names"]
    assert report["operation_log_explainability"]["ready"], report["operation_log_explainability"]
    assert report["operation_log_explainability"]["schema"] == "cleanmac.operation-log-explainability.v1"
    assert "impact_scope" in report["operation_log_explainability"]["required_entry_fields"]
    assert report["cold_start_budget"]["ready"], report["cold_start_budget"]
    assert report["cold_start_budget"]["schema"] == "cleanmac.cold-start-budget.v1"
    assert report["cold_start_budget"]["resource_uri"] == "cleanmac://ai/cold-start-budget"
    assert report["cold_start_budget"]["budgets"]["resident_processes_after_exit"] == 0
    assert report["no_disturbance"]["ready"], report["no_disturbance"]
    assert report["no_disturbance"]["schema"] == "cleanmac.no-disturbance.v1"
    assert report["no_disturbance"]["resource_uri"] == "cleanmac://ai/no-disturbance"
    assert report["no_disturbance"]["silent_by_default"]
    assert report["no_disturbance"]["validation"]["valid"]
    assert report["dependency_governance"]["ready"], report["dependency_governance"]
    assert report["dependency_governance"]["schema"] == "cleanmac.dependency-governance.v1"
    assert report["dependency_governance"]["resource_uri"] == "cleanmac://release/dependency-governance"
    assert report["dependency_governance"]["runtime_dependency_policy"] == "stdlib-only-runtime-by-default"
    assert report["dependency_governance"]["validation"]["valid"]
    assert report["release_readiness"]["schema"] == "cleanmac.release-readiness.v1"
    assert "ready" in report["release_readiness"]
    assert "failed_gate_ids" in report["release_readiness"]
    assert report["release_readiness"]["required_for"] == "release-review"
    assert report["release_readiness"]["not_required_for"] == "runtime-readonly-ai-host-discovery"
    coverage = report["contract_validation"]["contract_schema_coverage"]
    assert "cleanmac.ai-host-policy.v1" in coverage["critical_schemas"]
    assert "cleanmac.ai-governance-advice.v1" in coverage["critical_schemas"]
    assert "cleanmac.ai-eval-pack.v1" in coverage["critical_schemas"]
    assert "cleanmac.no-disturbance.v1" in coverage["critical_schemas"]
    assert "cleanmac.dependency-governance.v1" in coverage["critical_schemas"]
    assert coverage["missing_stable_ai_schema_fragments"] == []
    assert ["cleanmac", "--json", "ai-decision-matrix"] in report["recommended_preflight_commands"]
    assert ["cleanmac", "--json", "ai-governance-advice"] in report["recommended_preflight_commands"]
    assert ["cleanmac", "--json", "ai-host-policy"] in report["recommended_preflight_commands"]
    assert ["cleanmac", "--json", "mcp-destructive-tool-governance"] in report["recommended_preflight_commands"]
    assert ["cleanmac", "--json", "operation-log-explainability"] in report["recommended_preflight_commands"]
    assert ["cleanmac", "--json", "cold-start-budget"] in report["recommended_preflight_commands"]
    assert ["cleanmac", "--json", "no-disturbance"] in report["recommended_preflight_commands"]
    assert ["cleanmac", "--json", "dependency-governance"] in report["recommended_preflight_commands"]
    assert ["cleanmac", "--json", "ai-host-evidence"] in report["recommended_preflight_commands"]
    assert ["cleanmac", "--json", "release-readiness"] in report["recommended_preflight_commands"]
    assert ["cleanmac", "--json", "ai-eval-pack"] in report["recommended_preflight_commands"]
    assert ["cleanmac", "--json", "ai-eval-run", "--scenario", "smoke"] in report["recommended_preflight_commands"]
    assert "cleanmac_capabilities" in report["recommended_starting_tools"]
    assert "cleanmac_policy_simulate" in report["mandatory_before_execute"]


def test_ai_readiness_fails_closed_when_contract_validation_fails() -> None:
    from cleancli.ai_readiness import render_ai_readiness

    failed_contract = {
        "schema": "cleanmac.ai-contract-validation-summary.v1",
        "valid": False,
        "validated_schema_count": 1,
        "failure_count": 1,
        "contract_schema_coverage": {
            "registered_schema_count": 1,
            "json_schema_fragment_count": 0,
            "critical_schemas": ["cleanmac.plan.v1"],
            "critical_schema_count": 1,
            "stable_ai_schema_count": 1,
            "stable_ai_schema_fragment_count": 0,
            "missing_stable_ai_schema_fragments": ["cleanmac.plan.v1"],
        },
    }

    with patch("cleancli.ai_readiness.render_ai_contract_validation_summary", return_value=failed_contract):
        report = render_ai_readiness({"schema": "cleanmac.ai-tool-contract.v1"})

    assert report["schema"] == "cleanmac.ai-readiness.v1"
    assert not report["ready"]
    assert not report["contract_validation"]["ready"]
    assert report["contract_validation"]["failure_count"] == 1
    coverage = report["contract_validation"]["contract_schema_coverage"]
    assert coverage["missing_stable_ai_schema_fragments"] == ["cleanmac.plan.v1"]


def test_ai_readiness_fails_closed_when_host_policy_validation_fails() -> None:
    from cleancli.ai_readiness import render_ai_readiness

    with patch(
        "cleancli.ai_readiness.validate_ai_host_policy",
        return_value={
            "schema": "cleanmac.ai-host-policy-validation.v1",
            "valid": False,
            "errors": ["bad-policy"],
        },
    ):
        report = render_ai_readiness({"schema": "cleanmac.ai-tool-contract.v1"})

    assert report["schema"] == "cleanmac.ai-readiness.v1"
    assert not report["ready"]
    assert not report["host_policy"]["ready"]
    assert report["host_policy"]["validation"]["errors"] == ["bad-policy"]
