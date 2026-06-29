from __future__ import annotations

import json
from pathlib import Path

from cleancli.ai_versioning import validate_contract_payload
from tests.helpers import run_cli


def _write_fixture(root: Path, relative: str, content: str = "fixture") -> Path:
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return path


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
    assert "cleanmac.xcode-ios-candidates.v1" in report["evidence_refs"]
    assert report["read_only_surfaces"]["candidate_evidence"] == (
        "cleanmac --json xcode-ios-candidates --summary-only"
    )
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


def test_xcode_ios_candidates_emit_bounded_read_only_evidence(tmp_path: Path) -> None:
    root = tmp_path / "root"
    home = Path("/Users/tester")
    _write_fixture(root, "Users/tester/Library/Developer/Xcode/DerivedData/App-a/cache.db", "derived")
    _write_fixture(root, "Users/tester/Library/Developer/Xcode/ModuleCache.noindex/module.cache", "module")
    _write_fixture(root, "Users/tester/Library/Developer/CoreSimulator/Caches/sim.cache", "sim")
    _write_fixture(root, "Users/tester/Library/Developer/Xcode/Archives/2026-06/App.xcarchive/info.plist", "archive")
    _write_fixture(root, "Users/tester/Library/Developer/Xcode/iOS DeviceSupport/17.5/symbols.db", "symbols")
    _write_fixture(root, "Users/tester/Library/Application Support/MobileSync/Backup/device-1/Manifest.plist", "backup")

    report = json.loads(
        run_cli(
            "--json",
            "--root",
            str(root),
            "--home",
            str(home),
            "xcode-ios-candidates",
            "--limit",
            "20",
            "--max-scan-entries",
            "20",
        ).stdout
    )

    assert report["schema"] == "cleanmac.xcode-ios-candidates.v1"
    assert report["destructive"] is False
    assert report["dry_run"] is True
    assert report["read_only"] is True
    assert report["destructive_paths_absent"] is True
    assert report["candidate_count"] >= 6
    assert report["shown_candidate_count"] == len(report["candidates"])
    assert validate_contract_payload("cleanmac.xcode-ios-candidates.v1", report)["valid"] is True

    required = set(json.loads(run_cli("--json", "xcode-ios-governance").stdout)["evidence_fields"])
    roles = {candidate["path_role"] for candidate in report["candidates"]}
    assert {
        "xcode_derived_data",
        "xcode_module_cache",
        "core_simulator_cache",
        "xcode_archives",
        "device_support",
        "ios_backup",
    }.issubset(roles)
    for candidate in report["candidates"]:
        assert required.issubset(candidate), candidate
        assert candidate["review_evidence"]["schema"] == "cleanmac.candidate-review-evidence.v1"

    by_role = {candidate["path_role"]: candidate for candidate in report["candidates"]}
    assert by_role["xcode_derived_data"]["default_selected"] is True
    assert by_role["xcode_archives"]["default_selected"] is False
    assert by_role["device_support"]["default_selected"] is False
    assert by_role["ios_backup"]["default_selected"] is False
    assert by_role["ios_backup"]["contains_user_data"] is True
    assert "ios_backup" in report["never_default_selected_path_roles"]


def test_xcode_ios_candidates_summary_only_hides_candidate_details(tmp_path: Path) -> None:
    root = tmp_path / "root"
    home = Path("/Users/tester")
    _write_fixture(root, "Users/tester/Library/Developer/Xcode/DerivedData/App-a/cache.db")

    report = json.loads(
        run_cli(
            "--json",
            "--root",
            str(root),
            "--home",
            str(home),
            "xcode-ios-candidates",
            "--summary-only",
            "--max-scan-entries",
            "5",
        ).stdout
    )

    assert report["summary_only"] is True
    assert report["candidate_count"] == 1
    assert report["shown_candidate_count"] == 0
    assert report["candidates"] == []
    assert report["candidate_count_by_path_role"] == {"xcode_derived_data": 1}
    assert report["next_review_command"] == [
        "cleanmac",
        "--json",
        "review",
        "--input-file",
        "<xcode-ios-candidates.json>",
    ]


def test_xcode_ios_candidates_normalize_through_review(tmp_path: Path) -> None:
    root = tmp_path / "root"
    home = Path("/Users/tester")
    _write_fixture(root, "Users/tester/Library/Developer/Xcode/DerivedData/App-a/cache.db")
    _write_fixture(root, "Users/tester/Library/Developer/Xcode/Archives/2026-06/App.xcarchive/info.plist")
    payload_path = tmp_path / "xcode-ios-candidates.json"

    report = json.loads(
        run_cli(
            "--json",
            "--root",
            str(root),
            "--home",
            str(home),
            "xcode-ios-candidates",
            "--limit",
            "10",
        ).stdout
    )
    payload_path.write_text(json.dumps(report), encoding="utf-8")
    review = json.loads(run_cli("--json", "review", "--input-file", str(payload_path)).stdout)

    assert review["schema"] == "cleanmac.review.v1"
    assert review["source_schema"] == "cleanmac.xcode-ios-candidates.v1"
    assert review["item_count"] == 2
    selected_roles = {
        item["review_evidence"]["matched_rule"].removeprefix("xcode-ios.")
        for item in review["items"]
        if item["id"] in set(review["selection"]["selected_item_ids"])
    }
    assert selected_roles == {"xcode_derived_data"}
