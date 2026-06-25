from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Any
from unittest import mock

import cleancli.core as cleancli
from cleancli.ai_versioning import validate_contract_payload
from tests.helpers import make_sandbox, run_cli


def test_clean_defaults_to_dry_run() -> None:
    tmp, root, home = make_sandbox()
    with tmp:
        run_cli(
            "--root",
            str(root),
            "--home",
            str(home),
            "clean",
            "--categories",
            "trash",
        )

        assert (root / "Users/tester/.Trash/old.tmp").exists()


def test_clean_dry_run_includes_pre_clean_report() -> None:
    tmp, root, home = make_sandbox()
    with tmp:
        (root / "Users/tester/Downloads/partial.crdownload").write_text("partial", encoding="utf-8")
        result = run_cli(
            "--root",
            str(root),
            "--home",
            str(home),
            "--json",
            "clean",
            "--categories",
            "trash,downloads",
        )
        report = json.loads(result.stdout)
        pre = report["pre_clean_report"]
        preview_by_key = {row["key"]: row for row in pre["category_preview"]}

        assert report["dry_run"] is True
        assert report["post_clean_report"] is None
        assert pre["phase"] == "pre-clean"
        assert pre["summary"]["selected_category_count"] == 2
        assert pre["summary"]["candidate_count"] == 3
        assert pre["summary"]["estimated_reclaimable_bytes"] > 0
        assert pre["summary"]["high_risk_categories"] == ["downloads"]
        assert pre["cleanup_flow"]["progress_messages"] == ["Cleaning...", "Finishing!", "Success!"]
        assert preview_by_key["trash"]["candidate_count"] == 1
        assert preview_by_key["downloads"]["risk"] == "high"
        for candidate in pre["candidates"]:
            evidence = candidate["review_evidence"]
            assert evidence["schema"] == "cleanmac.candidate-review-evidence.v1"
            assert evidence["matched_rule"].startswith("clean.")
            assert evidence["risk"] == candidate["risk"]
            assert evidence["default_selected"] == candidate["default_selected"]
            assert evidence["protected"] == candidate["protected"]
            assert validate_contract_payload("cleanmac.candidate-review-evidence.v1", evidence)["valid"] is True
        assert (root / "Users/tester/.Trash/old.tmp").exists()


def test_pre_clean_report_notes_symbolic_link_refresh() -> None:
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
            "userAppLogs",
        )
        report = json.loads(result.stdout)
        symbolic = report["pre_clean_report"]["cleanup_flow"]["symbolic_link_refresh"]

        assert symbolic["enabled_when_selected"] is True
        assert symbolic["logs_link_dir"] == "~/.CleanMacAppLogLinks/"


def test_clean_execute_includes_post_clean_report() -> None:
    tmp, root, home = make_sandbox()
    with tmp:
        (root / "Users/tester/Downloads/partial.crdownload").write_text("partial", encoding="utf-8")
        result = run_cli(
            "--root",
            str(root),
            "--home",
            str(home),
            "--json",
            "clean",
            "--categories",
            "trash,downloads",
            "--execute",
            "--yes",
        )
        report = json.loads(result.stdout)
        post = report["post_clean_report"]
        deltas = {row["key"]: row for row in post["category_deltas"]}
        preservation = {row["path"]: row for row in post["target_preservation"]}

        assert report["dry_run"] is False
        assert report["pre_clean_report"]["summary"]["candidate_count"] == 3
        assert post["phase"] == "post-clean"
        assert post["summary"]["deleted_item_count"] == 3
        assert post["summary"]["remaining_reclaimable_bytes"] == 0
        assert deltas["trash"]["reclaimed_bytes"] > 0
        assert deltas["downloads"]["reclaimed_bytes"] > 0
        assert preservation[str(root / "Users/tester/.Trash")]["exists_after_clean"] is True
        assert preservation[str(root / "Users/tester/Downloads")]["exists_after_clean"] is True
        assert not (root / "Users/tester/.Trash/old.tmp").exists()
        assert not (root / "Users/tester/Downloads/download.bin").exists()


def test_clean_human_output_shows_pre_and_post_reports() -> None:
    tmp, root, home = make_sandbox()
    with tmp:
        result = run_cli(
            "--root",
            str(root),
            "--home",
            str(home),
            "clean",
            "--categories",
            "trash",
            "--execute",
        )

        assert "Pre-clean report:" in result.stdout
        assert "Post-clean report:" in result.stdout
        assert "estimated reclaim" in result.stdout
        assert "estimated reclaimed" in result.stdout


def test_clean_human_dry_run_shows_pre_clean_report_without_post_clean_report() -> None:
    tmp, root, home = make_sandbox()
    with tmp:
        result = run_cli(
            "--root",
            str(root),
            "--home",
            str(home),
            "clean",
            "--categories",
            "trash,downloads",
        )

        assert "Pre-clean report:" in result.stdout
        assert "selected categories : 2" in result.stdout
        assert "high-risk categories: downloads" in result.stdout
        assert "semantics           : delete target contents; preserve parent directories" in result.stdout
        assert "DRY-RUN:" in result.stdout
        assert "[trash] would delete:" in result.stdout
        assert "[downloads] would delete:" in result.stdout
        assert "Post-clean report:" not in result.stdout
        assert (root / "Users/tester/.Trash/old.tmp").exists()
        assert (root / "Users/tester/Downloads/download.bin").exists()


def test_clean_reports_ai_confirmation_summary_for_dry_run_and_execute() -> None:
    tmp, root, home = make_sandbox()
    with tmp:
        dry_run = run_cli(
            "--root",
            str(root),
            "--home",
            str(home),
            "--json",
            "clean",
            "run",
            "--categories",
            "trash,downloads",
            "--delete-mode",
            "trash",
            "--max-items",
            "10",
            "--max-delete-mb",
            "5",
        )
        dry_report = json.loads(dry_run.stdout)
        summary = dry_report["ai_confirmation_summary"]

        assert summary["requires_confirmation"] is True
        assert summary["recommended_confirmation_phrase"] == "Confirm cleanmac cleanup execution"
        assert summary["confirmation_token"].startswith("cleanmac-confirm-")
        assert summary["confirmation_token_context"]["delete_mode"] == "trash"
        assert summary["confirmation_token_context"]["max_items"] == 10
        assert summary["confirmation_token_context"]["schema"] == "cleanmac.ai-confirmation-token-context.v1"
        assert summary["confirmation_token_context"]["root"] == str(root)
        assert summary["confirmation_token_context"]["home"] == str(home)
        assert summary["confirmation_token_context"]["selected_categories"] == ["trash", "downloads"]
        assert summary["confirmation_token_context"]["max_delete_mb"] == 5.0
        assert summary["confirmation_token_context"]["candidate_count"] == len(dry_report["items"])
        assert summary["confirmation_token_context"]["plan_file"] is None
        assert summary["delete_mode"] == "trash"
        assert summary["operation_log"] == cleancli.OPERATIONS_LOG_FILE
        assert summary["estimated_reclaimable_bytes"] == dry_report["total_bytes"]
        assert summary["category_count"] == 2
        assert summary["item_count"] == len(dry_report["items"])
        assert summary["skipped_count"] == dry_report["skipped_count"]
        assert summary["recommended_next_action"] == "ask_user_confirmation"
        assert summary["safe_to_auto_execute"] is False
        assert {"trash", "downloads"}.issubset(summary["selected_categories"])

        human_summary = dry_report["human_summary"]
        assert human_summary["schema"] == "cleanmac.human-summary.v1"
        assert "Dry-run found" in human_summary["headline"]
        assert human_summary["safe_to_execute"] is False
        assert "--execute" in human_summary["next_command"]
        assert "--confirmation-token" in human_summary["next_command"]
        assert summary["confirmation_token"] in human_summary["next_command"]
        assert human_summary["top_reasons_to_review"]

        ai_summary = dry_report["ai_summary"]
        assert ai_summary["schema"] == "cleanmac.ai-summary.v1"
        assert ai_summary["phase"] == "clean-dry-run"
        assert ai_summary["recommended_next_action"] == "ask_user_confirmation"
        assert ai_summary["safe_to_execute_after_confirmation"] is True
        assert "Trash" in " ".join(ai_summary["reasons"])

        execute = run_cli(
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
        )
        execute_report = json.loads(execute.stdout)
        execute_summary = execute_report["ai_confirmation_summary"]
        execute_ledger = execute_report["ai_execution_ledger"]

        assert execute_summary["requires_confirmation"] is False
        assert execute_summary["recommended_next_action"] == "review_operation_log"
        assert execute_summary["deleted_count"] == sum(1 for row in execute_report["items"] if row["deleted"])
        assert execute_summary["operation_log"] == execute_report["operation_log"]
        assert execute_ledger["schema"] == "cleanmac.ai-execution-ledger.v1"
        assert execute_ledger["phase"] == "clean-execute"
        assert execute_ledger["execution"]["delete_mode"] == "trash"
        assert execute_ledger["execution"]["destructive"] is True
        assert execute_ledger["execution"]["trash_recoverable"] is True
        assert execute_ledger["confirmation"]["token_validated"] is False
        assert execute_ledger["confirmation"]["token_required"] is False
        assert execute_ledger["operation_log"]["status"] == "ready"
        assert execute_ledger["operation_log"]["ready"] is True
        assert execute_ledger["operation_log"]["path"] == execute_report["operation_log"]
        assert execute_ledger["operation_log"]["entry_count"] >= 1
        assert execute_report["ai_summary"]["phase"] == "clean-execute"
        assert execute_report["ai_summary"]["recommended_next_action"] == "review_operation_log"
        assert execute_report["human_summary"]["headline"].startswith("Executed ")
        assert execute_report["human_summary"]["next_command"] == []
        assert execute_report["human_summary"]["safe_to_execute"] is False


def test_clean_execute_removes_only_sandbox_contents() -> None:
    tmp, root, home = make_sandbox()
    with tmp:
        run_cli(
            "--root",
            str(root),
            "--home",
            str(home),
            "clean",
            "--categories",
            "trash,downloads",
            "--execute",
            "--yes",
        )

        assert not (root / "Users/tester/.Trash/old.tmp").exists()
        assert not (root / "Users/tester/Downloads/download.bin").exists()
        assert (root / "Users/tester/.Trash").exists()
        assert (root / "Users/tester/Downloads").exists()
        assert (root / "Users/tester/Library/Containers/com.example/Data/Library/Caches/cache.bin").exists()


def test_clean_writes_json_audit_report_file() -> None:
    tmp, root, home = make_sandbox()
    with tmp:
        audit_file = root / "cleanmac-audit.json"
        result = run_cli(
            "--root",
            str(root),
            "--home",
            str(home),
            "--report-file",
            str(audit_file),
            "--json",
            "clean",
            "--categories",
            "trash",
        )
        report = json.loads(result.stdout)
        audit = json.loads(audit_file.read_text(encoding="utf-8"))

        assert report["report_file"] == str(audit_file)
        assert audit["schema"] == "cleanmac.audit.v1"
        assert audit["command"] == "clean"
        assert audit["root"] == str(root)
        assert audit["dry_run"] is True
        assert "--report-file" in audit["argv"]
        assert audit["selected_category_keys"] == ["trash"]


def test_plan_file_reuses_filters_during_execute() -> None:
    tmp, root, home = make_sandbox()
    with tmp:
        keep = root / "Users/tester/.Trash/keep.keep"
        old_file = root / "Users/tester/.Trash/old.tmp"
        keep.write_text("keep", encoding="utf-8")
        old_file.write_text("old", encoding="utf-8")
        old_time = time.time() - 10 * 24 * 60 * 60
        os.utime(old_file, (old_time, old_time))
        os.utime(keep, (old_time, old_time))
        plan_file = root / "plan.json"
        plan_file.write_text(
            json.dumps(
                {
                    "selected_category_keys": ["trash"],
                    "exclude_patterns": ["*.keep"],
                    "older_than_days": 7,
                }
            ),
            encoding="utf-8",
        )

        result = run_cli(
            "--root",
            str(root),
            "--home",
            str(home),
            "--json",
            "clean",
            "--plan-file",
            str(plan_file),
            "--execute",
        )
        report = json.loads(result.stdout)

        assert report["exclude_patterns"] == ["*.keep"]
        assert report["older_than_days"] == 7.0
        assert report["skipped_summary"]["by_reason"] == {"excluded": 1}
        assert keep.exists()
        assert not old_file.exists()


def test_ai_confirmation_token_is_required_and_bound_before_execute() -> None:
    tmp, root, home = make_sandbox()
    with tmp:
        dry_run = run_cli(
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
            "--max-items",
            "10",
            "--max-delete-mb",
            "5",
        )
        token = json.loads(dry_run.stdout)["ai_confirmation_summary"]["confirmation_token"]
        candidate = root / "Users/tester/Downloads/download.bin"

        missing = run_cli(
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
            "--max-items",
            "10",
            "--max-delete-mb",
            "5",
            "--execute",
            "--yes",
            "--require-confirmation-token",
            check=False,
        )
        assert missing.returncode != 0
        assert "confirmation token" in missing.stderr
        assert candidate.exists()

        mismatch = run_cli(
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
            "--max-items",
            "99",
            "--max-delete-mb",
            "5",
            "--execute",
            "--yes",
            "--require-confirmation-token",
            "--confirmation-token",
            token,
            check=False,
        )
        assert mismatch.returncode != 0
        assert "confirmation token mismatch" in mismatch.stderr
        assert candidate.exists()

        execute = run_cli(
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
            "--max-items",
            "10",
            "--max-delete-mb",
            "5",
            "--execute",
            "--yes",
            "--require-confirmation-token",
            "--confirmation-token",
            token,
        )
        report = json.loads(execute.stdout)

        assert not candidate.exists()
        assert report["ai_confirmation_summary"]["confirmation_token_validated"] is True
        assert report["ai_execution_ledger"]["confirmation"]["token_required"] is True
        assert report["ai_execution_ledger"]["confirmation"]["token_validated"] is True


def test_filters_apply_to_inspect_and_clean() -> None:
    tmp, root, home = make_sandbox()
    with tmp:
        keep = root / "Users/tester/.Trash/keep.tmp"
        remove = root / "Users/tester/.Trash/remove.log"
        keep.write_text("keep", encoding="utf-8")
        remove.write_text("remove", encoding="utf-8")

        inspect_result = run_cli(
            "--root",
            str(root),
            "--home",
            str(home),
            "--json",
            "inspect",
            "--categories",
            "trash",
            "--name-regex",
            "remove\\.log$",
        )
        inspect_report = json.loads(inspect_result.stdout)
        inspect_paths = [row["path"] for row in inspect_report["items"]]

        assert str(remove) in inspect_paths
        assert str(keep) not in inspect_paths
        assert "name-regex-mismatch" in inspect_report["skipped_summary"]["by_reason"]

        clean_result = run_cli(
            "--root",
            str(root),
            "--home",
            str(home),
            "--json",
            "clean",
            "--categories",
            "trash",
            "--exclude",
            "*keep.tmp",
            "--execute",
        )
        clean_report = json.loads(clean_result.stdout)

        assert clean_report["skipped_summary"]["by_reason"] == {"excluded": 1}
        assert keep.exists()
        assert not remove.exists()


def test_clean_execute_records_item_failures_and_continues_by_default() -> None:
    tmp, root, home = make_sandbox()
    with tmp:
        (root / "Users/tester/Downloads/partial.crdownload").write_text("partial", encoding="utf-8")
        operation_log = root / "logs" / "operations.jsonl"
        original_delete_path = cleancli.delete_path

        def flaky_delete(path: Path, **kwargs: Any) -> Path | None:
            if path.name == "download.bin":
                raise PermissionError("Operation not permitted")
            return original_delete_path(path, **kwargs)

        with mock.patch.object(cleancli, "delete_path", side_effect=flaky_delete):
            report = cleancli.clean(
                [cleancli.CATEGORY_BY_KEY["downloads"]],
                root=root,
                home=home,
                execute=True,
                risk_policy="default",
                delete_mode="trash",
                operation_log=str(operation_log),
                command_argv=["clean", "--categories", "downloads", "--execute"],
            )

        records = [json.loads(line) for line in operation_log.read_text(encoding="utf-8").splitlines()]
        failed = [row for row in report["items"] if row.get("status") == "failed"]
        deleted = [row for row in report["items"] if row.get("status") == "deleted"]

        assert report["failed_count"] == 1
        assert report["deleted_count"] == 1
        assert failed[0]["reason"] == "permission-denied"
        assert (root / "Users/tester/Downloads/download.bin").exists()
        assert not (root / "Users/tester/Downloads/partial.crdownload").exists()
        assert {record["status"] for record in records} == {"failed", "deleted"}
        assert len(deleted) == 1


def test_clean_safety_gate_exposes_single_fail_fast_flag() -> None:
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
            "trash",
            "--fail-fast",
        )
        report = json.loads(result.stdout)

        assert list(report["safety_gate"]).count("fail_fast") == 1
        assert report["safety_gate"]["fail_fast"] is True


def test_execute_high_risk_requires_yes() -> None:
    tmp, root, home = make_sandbox()
    with tmp:
        result = run_cli(
            "--root",
            str(root),
            "--home",
            str(home),
            "clean",
            "--categories",
            "downloads",
            "--execute",
            check=False,
        )

        assert result.returncode != 0
        assert "without --yes" in result.stderr
        assert (root / "Users/tester/Downloads/download.bin").exists()


def test_clean_risk_policy_strict_requires_yes_for_medium_risk() -> None:
    tmp, root, home = make_sandbox()
    with tmp:
        log_file = root / "Users/tester/Library/logs/noisy.log"
        log_file.parent.mkdir(parents=True, exist_ok=True)
        log_file.write_text("log", encoding="utf-8")
        result = run_cli(
            "--root",
            str(root),
            "--home",
            str(home),
            "clean",
            "--categories",
            "userLogs",
            "--execute",
            "--risk-policy",
            "strict",
            check=False,
        )

        assert result.returncode != 0
        assert "risk policy 'strict'" in result.stderr
        assert log_file.exists()


def test_clean_risk_policy_permissive_allows_high_risk_without_yes() -> None:
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
            "--risk-policy",
            "permissive",
        )
        report = json.loads(result.stdout)

        assert report["risk_policy"] == "permissive"
        assert report["pre_clean_report"]["summary"]["yes_required_categories"] == []
        assert not (root / "Users/tester/Downloads/download.bin").exists()


def test_clean_execute_live_root_requires_explicit_allow_flag() -> None:
    result = run_cli("clean", "--categories", "trash", "--execute", check=False)

    assert result.returncode != 0
    assert "live root '/'" in result.stderr


def test_clean_max_delete_budget_blocks_execute_before_deleting() -> None:
    tmp, root, home = make_sandbox()
    with tmp:
        result = run_cli(
            "--root",
            str(root),
            "--home",
            str(home),
            "clean",
            "--categories",
            "trash",
            "--execute",
            "--max-delete-mb",
            "0",
            check=False,
        )

        assert result.returncode != 0
        assert "exceed --max-delete-mb budget" in result.stderr
        assert (root / "Users/tester/.Trash/old.tmp").exists()


def test_clean_max_items_blocks_execute_before_deleting() -> None:
    tmp, root, home = make_sandbox()
    with tmp:
        (root / "Users/tester/.Trash/extra.tmp").write_text("extra", encoding="utf-8")
        result = run_cli(
            "--root",
            str(root),
            "--home",
            str(home),
            "clean",
            "--categories",
            "trash",
            "--execute",
            "--max-items",
            "1",
            check=False,
        )

        assert result.returncode != 0
        assert "exceeds --max-items budget" in result.stderr
        assert (root / "Users/tester/.Trash/old.tmp").exists()
        assert (root / "Users/tester/.Trash/extra.tmp").exists()
