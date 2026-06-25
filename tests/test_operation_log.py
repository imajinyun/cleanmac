from __future__ import annotations

import json

from cleancli import core
from tests.helpers import make_sandbox, run_cli
from tests.test_review_selection import write_review_selection


def test_operation_log_records_delete_status_path_bytes_mode_and_trash_path() -> None:
    tmp, root, home = make_sandbox()
    with tmp:
        operation_log = root / "logs/operations.jsonl"
        result = run_cli(
            "--root",
            str(root),
            "--home",
            str(home),
            "--json",
            "clean",
            "--categories",
            "downloads",
            "--delete-mode",
            "trash",
            "--execute",
            "--yes",
            "--operation-log",
            str(operation_log),
        )
        report = json.loads(result.stdout)
        records = [json.loads(line) for line in operation_log.read_text(encoding="utf-8").splitlines()]

        record = next(row for row in records if str(row["path"]).endswith("download.bin"))
        assert report["operation_log"] == str(operation_log)
        assert record["status"] == "deleted"
        assert str(record["path"]).endswith("download.bin")
        assert record["bytes"] > 0
        assert record["delete_mode"] == "trash"
        assert record["trash_path"]
        assert record["tool"] == "cleanmac.clean.run"
        assert record["parameters"]["category"] == "downloads"
        assert str(record["parameters"]["path"]).endswith("download.bin")
        assert record["parameters"]["delete_mode"] == "trash"
        assert record["result"]["action"] == "delete"
        assert record["result"]["status"] == "deleted"
        assert record["result"]["deleted"] is True
        assert str(record["impact_scope"]["path"]).endswith("download.bin")
        assert record["impact_scope"]["bytes"] == record["bytes"]
        assert record["ai"]["originated_plan"] is False
        assert record["ai"]["plan_file"] is None
        assert record["ai"]["plan_sha256"] is None
        assert record["ai"]["confirmation_token_validated"] is False


def test_clean_execute_persists_operation_log_entries() -> None:
    tmp, root, home = make_sandbox()
    with tmp:
        operation_log = root / "logs" / "cleanmac-operations.jsonl"
        result = run_cli(
            "--root",
            str(root),
            "--home",
            str(home),
            "--json",
            "clean",
            "--categories",
            "downloads",
            "--execute",
            "--yes",
            "--operation-log",
            str(operation_log),
        )
        report = json.loads(result.stdout)
        records = [json.loads(line) for line in operation_log.read_text(encoding="utf-8").splitlines()]

        assert report["operation_log"] == str(operation_log)
        assert report["operation_log_entry_count"] == len(records)
        assert len(records) >= 1
        assert {record["schema"] for record in records} == {"cleanmac.operation-log-entry.v1"}
        assert {record["delete_mode"] for record in records} == {"permanent"}
        assert all("cleanmac.py" in record["command"] for record in records)
        assert all("downloads" in record["command"] for record in records)
        assert all(record["deleted"] for record in records)


def test_clean_execute_uses_default_operation_log_under_remapped_home() -> None:
    tmp, root, home = make_sandbox()
    with tmp:
        result = run_cli(
            "--root",
            str(root),
            "--home",
            str(home),
            "--json",
            "clean",
            "--categories",
            "downloads",
            "--execute",
            "--yes",
        )
        report = json.loads(result.stdout)
        operation_log = root / "Users/tester/.cleanmac/operations.jsonl"
        records = [json.loads(line) for line in operation_log.read_text(encoding="utf-8").splitlines()]

        assert report["operation_log"] == str(operation_log)
        assert report["operation_log_entry_count"] == len(records)
        assert records[0]["command"].split()[:2] == ["cleanmac.py", "--root"]
        assert str(root / "Users/tester/Downloads/download.bin") in {record["path"] for record in records}


def test_rotate_log_once_rotates_oversized_logs() -> None:
    tmp, root, _home = make_sandbox()
    with tmp:
        log_path = root / "logs" / "operations.jsonl"
        log_path.parent.mkdir(parents=True)
        log_path.write_text("x" * 32, encoding="utf-8")

        rotated = core.rotate_log_once(log_path, max_bytes=16)

        assert rotated is True
        assert not log_path.exists()
        assert (root / "logs" / "operations.jsonl.1").read_text(encoding="utf-8") == "x" * 32


def test_clean_execute_operation_log_records_review_selection_constraint() -> None:
    tmp, root, home = make_sandbox()
    with tmp:
        operation_log = root / "logs" / "review-selection-operations.jsonl"
        plan_file, selection_file, _review_report = write_review_selection(root, home, "trash,downloads")

        result = run_cli(
            "--root",
            str(root),
            "--home",
            str(home),
            "--json",
            "clean",
            "run",
            "--plan-file",
            str(plan_file),
            "--review-selection-file",
            str(selection_file),
            "--delete-mode",
            "trash",
            "--execute",
            "--yes",
            "--operation-log",
            str(operation_log),
        )
        report = json.loads(result.stdout)
        records = [json.loads(line) for line in operation_log.read_text(encoding="utf-8").splitlines()]

        assert report["operation_log_entry_count"] == len(records)
        assert {record["ai"]["review_selection"]["schema"] for record in records} == {
            "cleanmac.operation-log-review-selection.v1"
        }
        assert {record["ai"]["review_selection"]["selection_file"] for record in records} == {str(selection_file)}
        assert {record["ai"]["review_selection"]["selected_count"] for record in records} == {1}
        assert {len(record["ai"]["review_selection"]["selected_review_evidence"]) for record in records} == {1}
        assert {record["ai"]["review_selection"]["validation_valid"] for record in records} == {True}
        assert all(
            record["ai"]["candidate_review_evidence"]["schema"] == "cleanmac.candidate-review-evidence.v1"
            for record in records
        )
        assert "not-in-review-selection" in {record.get("reason") for record in records}
        assert (root / "Users/tester/Downloads/download.bin").exists()


def test_operation_log_explainability_contract_is_ready() -> None:
    result = run_cli("--json", "operation-log-explainability")
    payload = json.loads(result.stdout)

    assert payload["schema"] == "cleanmac.operation-log-explainability.v1"
    assert payload["destructive"] is False
    assert payload["dry_run"] is True
    assert payload["ready"] is True, payload
    assert payload["format"] == "jsonl"
    assert payload["append_only"] is True
    assert payload["validation"]["valid"] is True
    assert {"timestamp", "tool", "parameters", "result", "impact_scope"}.issubset(set(payload["required_entry_fields"]))
    sample = payload["sample_entry"]
    assert sample["schema"] == "cleanmac.operation-log-entry.v1"
    assert sample["tool"] == "cleanmac.clean.run"
    assert isinstance(sample["parameters"], dict)
    assert isinstance(sample["result"], dict)
    assert isinstance(sample["impact_scope"], dict)


def test_cold_start_budget_contract_is_ready() -> None:
    result = run_cli("--json", "cold-start-budget")
    payload = json.loads(result.stdout)

    assert payload["schema"] == "cleanmac.cold-start-budget.v1"
    assert payload["destructive"] is False
    assert payload["dry_run"] is True
    assert payload["ready"] is True, payload
    assert payload["validation"]["valid"] is True
    assert payload["budgets"]["cli_cold_start_max_ms"] == 1200
    assert payload["budgets"]["ai_host_preflight_max_ms"] == 2000
    assert payload["budgets"]["resident_processes_after_exit"] == 0
    assert ["cleanmac", "--json", "capabilities"] in payload["ai_host_preflight_probes"]


def test_dependency_governance_contract_is_ready() -> None:
    result = run_cli("--json", "dependency-governance")
    payload = json.loads(result.stdout)

    assert payload["schema"] == "cleanmac.dependency-governance.v1"
    assert payload["destructive"] is False
    assert payload["dry_run"] is True
    assert payload["ready"] is True, payload
    assert payload["resource_uri"] == "cleanmac://release/dependency-governance"
    assert payload["pyproject"]["runtime_dependencies"] == []
    assert payload["pyproject"]["runtime_dependency_count"] == 0
    assert {"build", "dev", "lint", "test"}.issubset(set(payload["pyproject"]["optional_dependency_group_names"]))
    assert payload["runtime_dependency_policy"] == "stdlib-only-runtime-by-default"
    assert payload["network_required_at_runtime"] is False
    assert payload["installs_background_services"] is False
    assert payload["allows_gui_tui_resident_dependencies"] is False
    assert ["python3", "-m", "pip_audit", "--skip-editable", "--progress-spinner", "off"] in payload["audit"][
        "commands"
    ]
    assert ["python3", "scripts/generate_sbom.py", "--output", "SBOM.json"] in payload["audit"]["commands"]
    assert ["make", "dependency-audit-smoke"] in payload["release_gate_commands"]
    assert payload["validation"]["valid"] is True


def test_no_disturbance_contract_is_ready() -> None:
    result = run_cli("--json", "no-disturbance")
    payload = json.loads(result.stdout)

    assert payload["schema"] == "cleanmac.no-disturbance.v1"
    assert payload["destructive"] is False
    assert payload["dry_run"] is True
    assert payload["ready"] is True, payload
    assert payload["resource_uri"] == "cleanmac://ai/no-disturbance"
    assert payload["silent_by_default"] is True
    assert payload["sends_notifications"] is False
    assert payload["shows_dialogs"] is False
    assert payload["plays_sounds"] is False
    assert payload["uses_osascript_for_ui"] is False
    assert payload["push_reminders"] is False
    assert payload["background_prompts"] is False
    assert payload["retention_pattern"] == "do-not-retain-user-attention"
    assert payload["output_policy"]["default_stdout"] == "explicit-invocation-results-only"
    assert ["make", "no-disturbance-smoke"] in payload["release_gate_commands"]
    assert payload["validation"]["valid"] is True


def test_operation_log_preflight_blocks_execute_when_parent_is_symlink() -> None:
    tmp, root, home = make_sandbox()
    with tmp:
        real_logs = root / "real-logs"
        real_logs.mkdir()
        symlink_logs = root / "logs-link"
        symlink_logs.symlink_to(real_logs, target_is_directory=True)
        candidate = root / "Users/tester/Downloads/download.bin"

        result = run_cli(
            "--root",
            str(root),
            "--home",
            str(home),
            "--json",
            "clean",
            "run",
            "--categories",
            "downloads",
            "--execute",
            "--yes",
            "--operation-log",
            str(symlink_logs / "operations.jsonl"),
            check=False,
        )

        assert result.returncode != 0
        assert "operation log preflight failed" in result.stderr
        assert candidate.exists()


def test_operation_log_preflight_blocks_execute_when_log_path_is_directory() -> None:
    tmp, root, home = make_sandbox()
    with tmp:
        operation_log = root / "logs/operations.jsonl"
        operation_log.mkdir(parents=True)
        candidate = root / "Users/tester/Downloads/download.bin"

        result = run_cli(
            "--root",
            str(root),
            "--home",
            str(home),
            "--json",
            "clean",
            "run",
            "--categories",
            "downloads",
            "--execute",
            "--yes",
            "--operation-log",
            str(operation_log),
            check=False,
        )

        assert result.returncode != 0
        assert "operation log preflight failed" in result.stderr
        assert candidate.exists()


def test_operation_log_preflight_rotates_oversized_log_before_delete() -> None:
    tmp, root, home = make_sandbox()
    with tmp:
        operation_log = root / "logs/operations.jsonl"
        operation_log.parent.mkdir(parents=True)
        operation_log.write_text("x" * (core.OPERATIONS_LOG_ROTATE_BYTES + 1), encoding="utf-8")
        rotated_log = operation_log.with_name("operations.jsonl.1")
        rotated_log.write_text("old rotated content", encoding="utf-8")

        result = run_cli(
            "--root",
            str(root),
            "--home",
            str(home),
            "--json",
            "clean",
            "run",
            "--categories",
            "downloads",
            "--delete-mode",
            "trash",
            "--execute",
            "--yes",
            "--operation-log",
            str(operation_log),
        )
        report = json.loads(result.stdout)
        records = [json.loads(line) for line in operation_log.read_text(encoding="utf-8").splitlines()]

        assert report["operation_log"] == str(operation_log)
        assert report["operation_log_status"] == "ready"
        assert report["operation_log_error"] is None
        assert report["operation_log_rotated"] is True
        assert report["operation_log_preflight"]["rotated"] is True
        assert rotated_log.exists()
        assert rotated_log.read_text(encoding="utf-8").startswith("x")
        assert records
        assert all(record["schema"] == "cleanmac.operation-log-entry.v1" for record in records)
