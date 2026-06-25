from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from tests.helpers import CLI, PROJECT_ROOT, make_sandbox, run_cli


def run_cli_unchecked(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(CLI), *args],
        cwd=PROJECT_ROOT,
        text=True,
        capture_output=True,
        check=False,
    )


def write_review_selection(root: Path, home: Path, categories: str) -> tuple[Path, Path, dict[str, object]]:
    plan_file = root / "plan.json"
    selection_file = root / "selection.json"
    plan_result = run_cli(
        "--root",
        str(root),
        "--home",
        str(home),
        "--json",
        "clean",
        "plan",
        "--categories",
        categories,
    )
    plan_file.write_text(plan_result.stdout, encoding="utf-8")

    review_report = json.loads(run_cli("--json", "review", "--input-file", str(plan_file)).stdout)
    trash_item_id = next(item["id"] for item in review_report["items"] if item["category"] == "trash")
    selection = dict(review_report["selection"])
    selection["selected_item_ids"] = [trash_item_id]
    selection["excluded_item_ids"] = [item["id"] for item in review_report["items"] if item["id"] != trash_item_id]
    selection_file.write_text(json.dumps(selection), encoding="utf-8")
    return plan_file, selection_file, review_report


def test_clean_plan_dry_run_can_be_constrained_by_review_selection() -> None:
    tmp, root, home = make_sandbox()
    with tmp:
        plan_file, selection_file, review_report = write_review_selection(root, home, "trash,downloads")
        expected_skipped = len(review_report["items"]) - 1

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
        )
        report = json.loads(result.stdout)

        assert report["schema"] == "cleanmac.clean.v1"
        assert report["destructive"] is False
        assert report["review_selection"]["selected_count"] == 1
        assert len(report["review_selection"]["selected_review_evidence"]) == 1
        assert report["safety_gate"]["review_selection_applied"] is True
        assert [item["category"] for item in report["items"]] == ["trash"]
        assert report["items"][0]["review_evidence"]["schema"] == "cleanmac.candidate-review-evidence.v1"
        assert report["skipped_summary"]["by_reason"]["not-in-review-selection"] == expected_skipped
        assert (root / "Users/tester/Downloads/download.bin").exists()


def test_clean_review_selection_file_must_match_plan_fingerprint() -> None:
    tmp, root, home = make_sandbox()
    with tmp:
        plan_file, selection_file, _review_report = write_review_selection(root, home, "trash")
        selection = json.loads(selection_file.read_text(encoding="utf-8"))
        selection["source_fingerprint"] = "stale"
        selection_file.write_text(json.dumps(selection), encoding="utf-8")

        result = run_cli_unchecked(
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
        )

        assert result.returncode != 0
        error_report = json.loads(result.stderr)
        assert error_report["error"]["code"] == "SELECTION_VALIDATION_FAILED"
        assert "source-fingerprint-mismatch" in error_report["error"]["message"]


def test_policy_simulate_includes_review_selection_in_safe_argv() -> None:
    tmp, root, home = make_sandbox()
    with tmp:
        plan_file, selection_file, _review_report = write_review_selection(root, home, "trash")

        result = run_cli(
            "--root",
            str(root),
            "--home",
            str(home),
            "--json",
            "clean",
            "policy-simulate",
            "--plan-file",
            str(plan_file),
            "--execute",
            "--delete-mode",
            "trash",
            "--review-selection-file",
            str(selection_file),
        )
        report = json.loads(result.stdout)

        assert report["schema"] == "cleanmac.ai-policy-simulation.v1"
        assert report["review_selection"]["schema"] == "cleanmac.review-selection-constraint.v1"
        assert "--review-selection-file" in report["safe_argv"]
        assert str(selection_file) in report["safe_argv"]
        assert {"rule": "review_selection_valid", "result": "pass"} in report["policy_decisions"]
