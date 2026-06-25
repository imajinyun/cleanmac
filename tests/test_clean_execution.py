from __future__ import annotations

import json

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
