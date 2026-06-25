from __future__ import annotations

import json
import plistlib
from pathlib import Path

from cleancli.ai_versioning import validate_contract_payload
from tests.helpers import make_sandbox, run_cli
from tests.test_review_selection import run_cli_unchecked, write_startup_fixtures


def write_startup_selection(root: Path, home: Path) -> tuple[Path, Path, dict[str, object]]:
    plan_file = root / "startup-plan.json"
    selection_file = root / "startup-selection.json"
    plan = json.loads(run_cli("--root", str(root), "--home", str(home), "--json", "startup", "plan").stdout)
    plan_file.write_text(json.dumps(plan), encoding="utf-8")
    review_report = json.loads(
        run_cli("--json", "review", "--input-file", str(plan_file), "--selection-file", str(selection_file)).stdout
    )
    selected_id = next(item["id"] for item in review_report["items"] if "com.example.agent" in item["id"])
    selection = dict(review_report["selection"])
    selection["selected_item_ids"] = [selected_id]
    selection["excluded_item_ids"] = [item["id"] for item in review_report["items"] if item["id"] != selected_id]
    selection_file.write_text(json.dumps(selection), encoding="utf-8")
    return plan_file, selection_file, review_report


def test_startup_audit_and_plan_classify_disable_candidates() -> None:
    tmp, root, home = make_sandbox()
    with tmp:
        write_startup_fixtures(root)
        audit = json.loads(run_cli("--root", str(root), "--home", str(home), "--json", "startup", "audit").stdout)
        by_label = {item["label"]: item for item in audit["items"]}

        assert audit["schema"] == "cleanmac.startup-audit.v1"
        assert audit["destructive"] is False
        assert audit["item_count"] == 2
        assert by_label["com.example.agent"]["recommendation"] == "review-disable"
        assert by_label["com.example.agent"]["default_selected"] is True
        assert by_label["com.example.daemon"]["requires_privilege"] is True
        assert by_label["com.example.daemon"]["default_selected"] is False
        assert audit["recommendation_counts"]["review-disable"] == 2
        assert audit["risk_counts"] == {"high": 1, "medium": 1}
        assert audit["recommended_next_action"] == "review_disable_plan"
        assert validate_contract_payload("cleanmac.startup-audit.v1", audit)["valid"] is True

        plan = json.loads(run_cli("--root", str(root), "--home", str(home), "--json", "startup", "plan").stdout)

        assert plan["schema"] == "cleanmac.startup-plan.v1"
        assert plan["disable_plan"]["requires_explicit_execute"] is True
        assert plan["disable_plan"]["requires_explicit_future_execute"] is True
        assert plan["disable_plan"]["safe_to_auto_execute"] is False
        assert plan["disable_plan"]["candidate_count"] == 2
        assert plan["disable_plan"]["default_selected_count"] == 1
        assert plan["disable_plan"]["requires_privilege_count"] == 1
        assert plan["disable_plan"]["risk_counts"] == {"high": 1, "medium": 1}
        assert validate_contract_payload("cleanmac.startup-plan.v1", plan)["valid"] is True


def test_startup_disable_requires_review_selection_and_records_audit() -> None:
    tmp, root, home = make_sandbox()
    with tmp:
        write_startup_fixtures(root)
        operation_log = root / "logs" / "startup-disable.jsonl"
        plan_file, selection_file, _review_report = write_startup_selection(root, home)

        missing_selection = run_cli_unchecked(
            "--root", str(root), "--home", str(home), "--json", "startup", "disable", "--plan-file", str(plan_file)
        )

        assert missing_selection.returncode != 0
        assert json.loads(missing_selection.stderr)["error"]["code"] == "SELECTION_VALIDATION_FAILED"

        result = run_cli(
            "--root",
            str(root),
            "--home",
            str(home),
            "--json",
            "startup",
            "disable",
            "--plan-file",
            str(plan_file),
            "--review-selection-file",
            str(selection_file),
            "--execute",
            "--yes",
            "--operation-log",
            str(operation_log),
        )
        report = json.loads(result.stdout)
        agent_plist = root / "Users/tester/Library/LaunchAgents/com.example.agent.plist"
        daemon_plist = root / "Library/LaunchDaemons/com.example.daemon.plist"
        records = [json.loads(line) for line in operation_log.read_text(encoding="utf-8").splitlines()]

        assert report["schema"] == "cleanmac.startup-disable-result.v1"
        assert report["dry_run"] is False
        assert report["disabled_count"] == 1
        assert report["skipped_count"] == 1
        assert validate_contract_payload("cleanmac.startup-disable-result.v1", report)["valid"] is True
        assert plistlib.loads(agent_plist.read_bytes())["Disabled"] is True
        assert "Disabled" not in plistlib.loads(daemon_plist.read_bytes())
        assert len(records) == 2
        assert {record["ai"]["review_selection"]["selected_count"] for record in records} == {1}
        assert {len(record["ai"]["review_selection"]["selected_review_evidence"]) for record in records} == {1}
        assert all(
            record["ai"]["candidate_review_evidence"]["schema"] == "cleanmac.candidate-review-evidence.v1"
            for record in records
        )
        disabled_result = next(item for item in report["results"] if item["status"] == "disabled")
        disabled_record = next(record for record in records if record["status"] == "disabled")
        assert disabled_result["review_evidence"]["schema"] == "cleanmac.candidate-review-evidence.v1"
        assert disabled_record["backup_path"] == disabled_result["backup_path"]
        assert disabled_record["backup_sha256"] == disabled_result["backup_sha256"]
        assert disabled_record["ai"]["candidate_review_evidence"] == disabled_result["review_evidence"]
        selected_evidence = disabled_record["ai"]["review_selection"]["selected_review_evidence"][0]
        assert selected_evidence["id"] == disabled_result["id"]
        assert selected_evidence["path"] == disabled_result["path"]
        assert selected_evidence["review_evidence"] == disabled_result["review_evidence"]
        assert "not-in-review-selection" in {record.get("reason") for record in records}


def test_startup_disable_creates_backup_before_plist_write() -> None:
    tmp, root, home = make_sandbox()
    with tmp:
        write_startup_fixtures(root)
        plan_file, selection_file, _review_report = write_startup_selection(root, home)

        result = run_cli(
            "--root",
            str(root),
            "--home",
            str(home),
            "--json",
            "startup",
            "disable",
            "--plan-file",
            str(plan_file),
            "--review-selection-file",
            str(selection_file),
            "--execute",
            "--yes",
        )
        report = json.loads(result.stdout)
        disabled = next(item for item in report["results"] if item["status"] == "disabled")

        assert disabled["backup_path"] is not None
        assert Path(disabled["backup_path"]).exists()
        assert disabled["backup_sha256"]
        assert validate_contract_payload("cleanmac.startup-disable-result.v1", report)["valid"] is True
