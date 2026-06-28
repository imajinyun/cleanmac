from __future__ import annotations

import json

from cleancli.ai_versioning import validate_contract_payload
from tests.helpers import run_cli


def test_xcode_ios_governance_contract_is_ready_and_read_only() -> None:
    report = json.loads(run_cli("--json", "xcode-ios-governance").stdout)

    assert report["schema"] == "cleanmac.xcode-ios-governance.v1"
    assert report["destructive"] is False
    assert report["dry_run"] is True
    assert report["ready"] is True
    assert report["failed_check_ids"] == []
    assert report["destructive_paths_absent"] is True
    assert report["in_progress_backlog_item_ids"] == ["p0-xcode-ios-deep-cleanup"]
    assert "cleanmac.software-ios-backups.v1" in report["evidence_refs"]
    assert ["make", "xcode-ios-governance-smoke"] in report["release_gate_commands"]
    assert validate_contract_payload("cleanmac.xcode-ios-governance.v1", report)["valid"] is True


def test_xcode_ios_governance_declares_required_evidence_fields() -> None:
    report = json.loads(run_cli("--json", "xcode-ios-governance").stdout)

    required = {
        "path_role",
        "tool_domain",
        "regenerable",
        "contains_user_data",
        "release_artifact_risk",
        "active_runtime_hint",
        "retention_reason",
        "default_selected",
        "why_not_default",
        "recommended_next_action",
    }
    assert set(report["evidence_fields"]) == required
    for policy in report["path_policies"]:
        assert required.issubset(policy), policy


def test_xcode_ios_governance_keeps_risky_surfaces_out_of_defaults() -> None:
    report = json.loads(run_cli("--json", "xcode-ios-governance").stdout)
    policies = {policy["path_role"]: policy for policy in report["path_policies"]}

    assert policies["xcode_derived_data"]["default_selected"] is True
    assert policies["xcode_module_cache"]["default_selected"] is True
    assert policies["core_simulator_cache"]["default_selected"] is True
    assert policies["xcode_products"]["default_selected"] is False
    assert policies["xcode_archives"]["default_selected"] is False
    assert policies["device_support"]["default_selected"] is False
    assert policies["ios_backup"]["default_selected"] is False
    assert policies["unavailable_simulator_device"]["default_selected"] is False
    assert policies["xcode_archives"]["release_artifact_risk"] == "high"
    assert policies["ios_backup"]["contains_user_data"] is True
    assert "xcode_archives" in report["default_selection_policy"]["never_default_selected_path_roles"]
    assert "ios_backup" in report["default_selection_policy"]["never_default_selected_path_roles"]


def test_xcode_ios_governance_marks_gap_backlog_in_progress() -> None:
    capabilities = json.loads(run_cli("--json", "capabilities").stdout)
    gap_todo = capabilities["boundary_governance"]["open_source_gap_governance_todo"]
    by_id = {item["id"]: item for item in gap_todo["items"]}

    assert gap_todo["landed_count"] == 2
    assert gap_todo["in_progress_count"] == 1
    assert gap_todo["pending_count"] == 7
    item = by_id["p0-xcode-ios-deep-cleanup"]
    assert item["status"] == "in_progress"
    assert item["landing_evidence"]["state"] == "in_progress"
    assert item["landing_evidence"]["release_gated"] is True
    assert "cleanmac.xcode-ios-governance.v1" in item["landing_evidence"]["evidence_refs"]


def test_xcode_ios_governance_is_wired_into_governance_integrity() -> None:
    report = json.loads(run_cli("--json", "governance-integrity").stdout)
    checks = {check["id"]: check for check in report["checks"]}

    assert report["ready"] is True
    assert report["failed_check_ids"] == []
    assert checks["xcode-ios-governance-ready"]["passed"] is True
    assert "cleanmac.xcode-ios-governance.v1" in report["governed_contracts"]
