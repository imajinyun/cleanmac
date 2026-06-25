from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
CLI = PROJECT_ROOT / "cleanmac.py"
SAFE_PLAN_TO_DRY_RUN_SCENARIO = "safe_plan_to_dry_run"
ONE_SHOT_GOVERNED_WORKFLOW_SCENARIO = "one_shot_governed_workflow"
INVALID_CATEGORY_RECOVERY_SCENARIO = "invalid_category_recovery"
CONFIRMATION_TOKEN_POLICY_SCENARIO = "confirmation_token_policy"


def run_cli(*args: str, root: Path, home: Path) -> dict:
    env = os.environ.copy()
    env["CLEANMAC_TEST_MODE"] = "1"
    env["CLEANMAC_TEST_NO_AUTH"] = "1"
    result = subprocess.run(
        [sys.executable, str(CLI), "--json", "--root", str(root), "--home", str(home), *args],
        text=True,
        capture_output=True,
        check=True,
        env=env,
    )
    return json.loads(result.stdout)


def run_cli_process(*args: str, root: Path, home: Path) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env["CLEANMAC_TEST_MODE"] = "1"
    env["CLEANMAC_TEST_NO_AUTH"] = "1"
    return subprocess.run(
        [sys.executable, str(CLI), "--json", "--root", str(root), "--home", str(home), *args],
        text=True,
        capture_output=True,
        check=False,
        env=env,
    )


def test_one_shot_governed_workflow_exposes_safe_cleanup_route(tmp_path: Path) -> None:
    assert ONE_SHOT_GOVERNED_WORKFLOW_SCENARIO == "one_shot_governed_workflow"
    root = tmp_path / "root"
    home = root / "Users" / "tester"
    home.mkdir(parents=True)

    report = run_cli(
        "ai-workflow",
        "--goal",
        "safe-cleanup",
        "--categories",
        "trash,downloads,xcode",
        root=root,
        home=home,
    )
    steps = {step["id"]: step for step in report["steps"]}

    assert report["schema"] == "cleanmac.ai-workflow.v1"
    assert report["goal"] == "safe-cleanup"
    assert report["ready"], report
    assert not report["destructive"]
    assert report["dry_run"]
    assert report["step_count"] == 7
    assert report["phase_order"] == [step["id"] for step in report["steps"]]
    assert report["validation"]["valid"], report["validation"]
    assert report["validation"]["schema"] == "cleanmac.ai-workflow-validation.v1"
    assert report["failed_check_ids"] == []
    assert report["readiness_score"] == {"passed": 7, "total": 7, "level": "ready"}
    assert report["inputs"]["categories"] == ["trash", "downloads", "xcode"]
    artifact_contracts = report["artifact_contracts"]
    assert artifact_contracts["plan_file"]["schema"] == "cleanmac.plan.v1"
    assert artifact_contracts["review_selection_file"]["schema"] == "cleanmac.review-selection.v1"
    assert artifact_contracts["review_selection_file"]["required_evidence_field"] == "selected_review_evidence"
    assert artifact_contracts["candidate_review_evidence"]["schema"] == "cleanmac.candidate-review-evidence.v1"
    assert artifact_contracts["candidate_review_evidence"]["operation_log_field"] == "ai.candidate_review_evidence"
    assert artifact_contracts["confirmation_token"]["schema"] == "cleanmac.ai-confirmation-summary.v1"
    assert artifact_contracts["operation_log"]["schema"] == "cleanmac.operation-log-entry.v1"
    assert artifact_contracts["operation_log"]["required_evidence_field"] == "ai.candidate_review_evidence"
    evidence_chain = report["candidate_evidence_chain"]
    assert evidence_chain["schema"] == "cleanmac.candidate-review-evidence.v1"
    assert evidence_chain["fail_closed_if_missing"]
    assert "review_selection_constraint.selected_review_evidence[]" in evidence_chain["required_artifact_paths"]
    assert "operation_log.ai.candidate_review_evidence" in evidence_chain["required_artifact_paths"]
    single_shot = {row["id"]: row for row in report["single_shot_workflows"]}
    assert "quick-safe-clean" in single_shot
    assert "developer-clean" in single_shot
    assert single_shot["developer-clean"]["safe_to_auto_call"]
    assert single_shot["developer-clean"]["exits_after_workflow"]
    assert "cleanmac_generate_plan" in report["recommended_tool_call_order"]
    assert "cleanmac_policy_simulate" in report["recommended_tool_call_order"]
    assert "cleanmac_execute_plan" in report["recommended_tool_call_order"]
    assert steps["generate_ai_origin_plan"]["output_schema"] == "cleanmac.plan.v1"
    assert steps["generate_ai_origin_plan"]["input_schema"]["type"] == "object"
    assert "categories" in steps["generate_ai_origin_plan"]["input_schema"]["required"]
    assert steps["normalize_review_selection"]["produces_schema"] == "cleanmac.review-selection.v1"
    assert steps["normalize_review_selection"]["required_evidence_output"] == "items[].review_evidence"
    assert steps["simulate_execute_policy"]["output_schema"] == "cleanmac.ai-policy-simulation.v1"
    assert steps["simulate_execute_policy"]["input_schema"]["type"] == "object"
    assert steps["simulate_execute_policy"]["input"]["delete_mode"] == "trash"
    assert steps["dry_run_selected_plan"]["required_output"] == "ai_confirmation_summary.confirmation_token"
    assert steps["dry_run_selected_plan"]["required_evidence_output"] == "items[].review_evidence"
    execute = steps["execute_after_human_confirmation"]
    assert execute["destructive"]
    assert not execute["auto_call_allowed"]
    assert execute["requires_human_confirmation"]
    assert "operation_log.ai.candidate_review_evidence" in execute["required_evidence_output"]
    assert "--delete-mode" in execute["argv"]
    assert "trash" in execute["argv"]
    assert "--operation-log" in execute["argv"]
    assert report["execution_gate"]["requires_matching_dry_run_confirmation_token"]
    assert report["execution_gate"]["requires_trash_delete_mode"]
    assert report["execution_gate"]["requires_candidate_evidence_chain"]
    assert "never auto-call cleanmac_execute_plan" in report["host_obligations"]
    assert "verify candidate evidence continuity from review selection to operation log" in report["host_obligations"]
    assert report["governance"]["requires_confirmation_token"]
    assert report["governance"]["requires_candidate_evidence_chain"]
    assert report["governance"]["delete_mode_for_execute"] == "trash"
    assert not report["governance"]["destructive_auto_call_allowed"]


def test_safe_ai_host_plan_to_dry_run_sequence(tmp_path: Path) -> None:
    assert SAFE_PLAN_TO_DRY_RUN_SCENARIO == "safe_plan_to_dry_run"
    root = tmp_path / "root"
    home = root / "Users" / "tester"
    trash = home / ".Trash"
    downloads = home / "Downloads"
    downloads.mkdir(parents=True)
    trash.mkdir(parents=True)
    candidate = downloads / "old-cache.tmp"
    candidate.write_text("cache", encoding="utf-8")
    plan_file = tmp_path / "plan.json"

    capabilities = run_cli("capabilities", root=root, home=home)
    assert capabilities["schema"] == "cleanmac.capabilities.v1"
    assert capabilities["ai_readiness"]["ready"]

    plan = run_cli("clean", "plan", "--categories", "downloads", "--ai-origin", root=root, home=home)
    plan_file.write_text(json.dumps(plan), encoding="utf-8")
    assert plan["schema"] == "cleanmac.plan.v1"
    assert plan["ai_origin"]

    validation = run_cli("clean", "validate-plan", "--plan-file", str(plan_file), root=root, home=home)
    assert validation["valid"], validation

    simulation = run_cli(
        "clean",
        "policy-simulate",
        "--plan-file",
        str(plan_file),
        "--execute",
        "--delete-mode",
        "trash",
        "--require-plan-context",
        "--require-confirmation-token",
        root=root,
        home=home,
    )
    assert not simulation["allowed"]
    blocking_codes = {row["code"] for row in simulation["blocking_reasons"]}
    assert "AI_ORIGIN_REQUIRES_CONFIRMATION_TOKEN" in blocking_codes

    dry_run = run_cli("clean", "run", "--plan-file", str(plan_file), "--delete-mode", "trash", root=root, home=home)
    assert dry_run["dry_run"]
    assert dry_run["ai_confirmation_summary"]["confirmation_token_embedded"]
    assert dry_run["human_summary"]["schema"] == "cleanmac.human-summary.v1"
    assert not dry_run["human_summary"]["safe_to_execute"]
    assert "--execute" in dry_run["human_summary"]["next_command"]
    assert "--confirmation-token" in dry_run["human_summary"]["next_command"]
    assert dry_run["human_summary"]["top_reasons_to_review"]

    review = run_cli("review", "--input-file", str(plan_file), root=root, home=home)
    assert review["human_summary"]["schema"] == "cleanmac.human-summary.v1"
    assert not review["human_summary"]["safe_to_execute"]
    assert "Review selected" in review["human_summary"]["headline"]
    assert "--review-selection-file" in review["human_summary"]["next_command"]


def test_ai_host_policy_simulate_allows_execute_intent_with_dry_run_token(tmp_path: Path) -> None:
    assert CONFIRMATION_TOKEN_POLICY_SCENARIO == "confirmation_token_policy"
    root = tmp_path / "root"
    home = root / "Users" / "tester"
    trash = home / ".Trash"
    downloads = home / "Downloads"
    downloads.mkdir(parents=True)
    trash.mkdir(parents=True)
    (downloads / "old-cache.tmp").write_text("cache", encoding="utf-8")
    plan_file = tmp_path / "plan.json"
    operation_log = tmp_path / "operations.jsonl"

    plan = run_cli("clean", "plan", "--categories", "downloads", "--ai-origin", root=root, home=home)
    plan_file.write_text(json.dumps(plan), encoding="utf-8")
    dry_run = run_cli(
        "clean",
        "run",
        "--plan-file",
        str(plan_file),
        "--delete-mode",
        "trash",
        root=root,
        home=home,
    )
    token = dry_run["ai_confirmation_summary"]["confirmation_token"]

    simulation = run_cli(
        "clean",
        "policy-simulate",
        "--plan-file",
        str(plan_file),
        "--execute",
        "--delete-mode",
        "trash",
        "--operation-log",
        str(operation_log),
        "--require-plan-context",
        "--require-confirmation-token",
        "--confirmation-token",
        token,
        root=root,
        home=home,
    )

    assert simulation["allowed"], simulation
    assert not simulation["blocking_reasons"], simulation["blocking_reasons"]
    decisions = {row["rule"]: row["result"] for row in simulation["policy_decisions"]}
    assert decisions["ai_origin_requires_confirmation_token"] == "pass"
    assert decisions["ai_origin_requires_operation_log"] == "pass"
    assert decisions["plan_context_matches"] == "pass"


def test_prompt_injection_boundary_path_text_treated_as_data(tmp_path: Path) -> None:
    """Verify the host policy declares that paths and filenames are treated as untrusted data."""
    root = tmp_path / "root"
    home = root / "Users" / "tester"
    home.mkdir(parents=True)

    result = run_cli(
        "ai-governance-advice",
        root=root,
        home=home,
    )

    assert result["schema"] == "cleanmac.ai-governance-advice.v1"
    host_controls = result.get("required_host_controls", [])
    path_data_statements = [
        c
        for c in host_controls
        if "path" in str(c).lower() or "data" in str(c).lower() or "untrusted" in str(c).lower()
    ]
    assert len(path_data_statements) >= 1, "Host controls must include path/data/untrusted handling"


def test_plan_context_mismatch_policy_blocks_execution(tmp_path: Path) -> None:
    """Verify execution intent is blocked when plan root/home differs from sandbox context."""
    root = tmp_path / "root"
    home = root / "Users" / "tester"
    other_root = tmp_path / "other_root"
    other_home = other_root / "Users" / "other"
    downloads = home / "Downloads"
    downloads.mkdir(parents=True)
    (downloads / "old-cache.tmp").write_text("cache", encoding="utf-8")
    plan_file = tmp_path / "plan.json"
    operation_log = tmp_path / "operations.jsonl"

    plan = run_cli("clean", "plan", "--categories", "downloads", "--ai-origin", root=root, home=home)
    plan_file.write_text(json.dumps(plan), encoding="utf-8")

    plan_for_token = run_cli(
        "clean", "run", "--plan-file", str(plan_file), "--delete-mode", "trash", root=root, home=home
    )
    token = plan_for_token["ai_confirmation_summary"]["confirmation_token"]

    result = run_cli(
        "clean",
        "policy-simulate",
        "--plan-file",
        str(plan_file),
        "--execute",
        "--delete-mode",
        "trash",
        "--operation-log",
        str(operation_log),
        "--require-plan-context",
        "--require-confirmation-token",
        "--confirmation-token",
        token,
        root=other_root,
        home=other_home,
    )

    assert not result["allowed"], "Policy simulate with mismatched context should be denied"
    blocking_codes = {row["code"] for row in result["blocking_reasons"]}
    assert "PLAN_CONTEXT_MISMATCH" in blocking_codes, (
        f"Expected PLAN_CONTEXT_MISMATCH in blocking reasons, got: {blocking_codes}"
    )


def test_permanent_delete_deny_policy_blocks_ai_origin(tmp_path: Path) -> None:
    """Verify AI-originated execute intent using permanent delete mode is blocked by policy."""
    root = tmp_path / "root"
    home = root / "Users" / "tester"
    downloads = home / "Downloads"
    downloads.mkdir(parents=True)
    (downloads / "old-cache.tmp").write_text("cache", encoding="utf-8")
    plan_file = tmp_path / "plan.json"
    operation_log = tmp_path / "operations.jsonl"

    plan = run_cli("clean", "plan", "--categories", "downloads", "--ai-origin", root=root, home=home)
    plan_file.write_text(json.dumps(plan), encoding="utf-8")

    plan_for_token = run_cli(
        "clean", "run", "--plan-file", str(plan_file), "--delete-mode", "trash", root=root, home=home
    )
    token = plan_for_token["ai_confirmation_summary"]["confirmation_token"]

    result = run_cli(
        "clean",
        "policy-simulate",
        "--plan-file",
        str(plan_file),
        "--execute",
        "--delete-mode",
        "permanent",
        "--operation-log",
        str(operation_log),
        "--require-plan-context",
        "--require-confirmation-token",
        "--confirmation-token",
        token,
        root=root,
        home=home,
    )

    assert not result["allowed"], "Permanent delete simulate with AI origin should be denied"
    blocking_codes = {row["code"] for row in result["blocking_reasons"]}
    assert "AI_ORIGIN_REQUIRES_TRASH" in blocking_codes, (
        f"Expected AI_ORIGIN_REQUIRES_TRASH in blocking reasons, got: {blocking_codes}"
    )


def test_ai_host_invalid_category_error_is_machine_readable(tmp_path: Path) -> None:
    assert INVALID_CATEGORY_RECOVERY_SCENARIO == "invalid_category_recovery"
    root = tmp_path / "root"
    home = root / "Users" / "tester"
    home.mkdir(parents=True)

    result = run_cli_process("clean", "inspect", "--categories", "notACategory", root=root, home=home)

    assert result.returncode != 0
    report = json.loads(result.stderr)
    assert report["schema"] == "cleanmac.ai-error.v1"
    assert report["error"]["code"] == "UNKNOWN_CATEGORY"
    assert report["error"]["retryable_after_fix"]
    assert "cleanmac_list_categories" in report["error"]["next_allowed_tools"]
