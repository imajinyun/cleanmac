from __future__ import annotations

import json
import os
import time
from collections.abc import Iterator

import pytest

from tests.helpers import cleanmac_test_env, make_sandbox, run_cli


def run_cli_unchecked(*args: str):
    return run_cli(*args, check=False)


@pytest.fixture(autouse=True)
def _test_env() -> Iterator[None]:
    with cleanmac_test_env():
        yield


class TestPlanCommand:
    def test_plan_generates_reusable_cleanup_plan_with_all_filters(self) -> None:
        tmp, root, home = make_sandbox()
        with tmp:
            result = run_cli(
                "--root",
                str(root),
                "--home",
                str(home),
                "--json",
                "plan",
                "--categories",
                "trash,downloads",
                "--risk-policy",
                "strict",
                "--max-delete-mb",
                "10",
                "--include",
                "*.tmp",
                "--exclude",
                "*.keep",
                "--min-size-mb",
                "1",
                "--name-regex",
                "tmp$",
                "--max-items",
                "5",
                "--older-than-days",
                "3",
            )
            report = json.loads(result.stdout)

            assert report["schema"] == "cleanmac.plan.v1"
            assert report["selected_category_keys"] == ["trash", "downloads"]
            assert report["risk_policy"] == "strict"
            assert report["max_delete_mb"] == 10.0
            assert report["include_patterns"] == ["*.tmp"]
            assert report["exclude_patterns"] == ["*.keep"]
            assert report["min_size_mb"] == 1
            assert report["name_regex"] == "tmp$"
            assert report["max_items"] == 5
            assert report["older_than_days"] == 3.0
            assert report["dry_run"] is True
            assert report["ai_origin"] is False
            assert "pre_clean_report" in report
            assert report["ai_summary"]["schema"] == "cleanmac.ai-summary.v1"
            assert report["ai_summary"]["phase"] == "plan"
            assert report["ai_summary"]["recommended_next_action"] == "dry_run_plan"
            assert report["ai_summary"]["safe_to_execute_after_confirmation"] is False
            assert "trash" in report["ai_summary"]["selected_categories"]
            assert report["ai_confirmation_summary"]["schema"] == "cleanmac.ai-confirmation-summary.v1"
            assert (
                report["ai_confirmation_summary"]["confirmation_token_embedded"]
                == report["ai_confirmation_summary"]["confirmation_token"]
            )
            assert report["ai_confirmation_summary"]["confirmation_token_embedded"].startswith("cleanmac-confirm-")

            plan_file = root / "contract-plan.json"
            plan_file.write_text(json.dumps(report), encoding="utf-8")
            validation = run_cli(
                "--json",
                "ai-validate-contract",
                "--schema",
                "cleanmac.plan.v1",
                "--payload-file",
                str(plan_file),
            )
            validation_report = json.loads(validation.stdout)
            assert validation_report["schema"] == "cleanmac.ai-contract-validation.v1"
            assert validation_report["valid"] is True
            assert validation_report["target_schema"] == "cleanmac.plan.v1"
            assert validation_report["error_count"] == 0

    def test_plan_file_reuses_filters_on_execute(self) -> None:
        tmp, root, home = make_sandbox()
        with tmp:
            keep = root / "Users/tester/.Trash/keep.keep"
            old_file = root / "Users/tester/.Trash/old.tmp"
            keep.write_text("keep")
            old_file.write_text("old")
            old_time = time.time() - 10 * 24 * 60 * 60
            os.utime(old_file, (old_time, old_time))
            plan_file = root / "plan.json"
            plan_file.write_text(
                json.dumps(
                    {
                        "selected_category_keys": ["trash"],
                        "exclude_patterns": ["*.keep"],
                        "older_than_days": 7,
                    }
                )
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
            assert keep.exists()
            assert not old_file.exists()


class TestPlanContext:
    def test_require_plan_context_rejects_root_mismatch(self) -> None:
        tmp, root, home = make_sandbox()
        with tmp:
            plan_file = root / "plan.json"
            plan_file.write_text(
                json.dumps(
                    {
                        "selected_category_keys": ["trash"],
                        "root": "/different/root",
                        "home": str(home),
                    }
                )
            )
            result = run_cli_unchecked(
                "--root",
                str(root),
                "--home",
                str(home),
                "clean",
                "--plan-file",
                str(plan_file),
                "--require-plan-context",
            )

            assert result.returncode != 0
            assert "Plan root mismatch" in result.stderr

    def test_require_plan_context_requires_plan_file(self) -> None:
        tmp, root, home = make_sandbox()
        with tmp:
            result = run_cli_unchecked(
                "--root",
                str(root),
                "--home",
                str(home),
                "clean",
                "--categories",
                "trash",
                "--require-plan-context",
            )

            assert result.returncode != 0
            assert "--plan-file" in result.stderr

    def test_require_plan_context_rejects_home_mismatch(self) -> None:
        tmp, root, home = make_sandbox()
        with tmp:
            plan_file = root / "plan.json"
            plan_file.write_text(
                json.dumps(
                    {
                        "selected_category_keys": ["trash"],
                        "root": str(root),
                        "home": "/different/home",
                    }
                )
            )
            result = run_cli_unchecked(
                "--root",
                str(root),
                "--home",
                str(home),
                "clean",
                "--plan-file",
                str(plan_file),
                "--require-plan-context",
            )

            assert result.returncode != 0
            assert "Plan home mismatch" in result.stderr


class TestPlanDrift:
    def test_ai_originated_execute_refuses_drifted_plan(self) -> None:
        tmp, root, home = make_sandbox()
        with tmp:
            plan_file = root / "ai-plan.json"
            operation_log = root / "operations.jsonl"
            plan_result = run_cli(
                "--root",
                str(root),
                "--home",
                str(home),
                "--json",
                "clean",
                "plan",
                "--categories",
                "downloads",
                "--ai-origin",
            )
            plan_file.write_text(plan_result.stdout, encoding="utf-8")
            dry_run = run_cli(
                "--root",
                str(root),
                "--home",
                str(home),
                "--json",
                "clean",
                "run",
                "--plan-file",
                str(plan_file),
                "--require-plan-context",
                "--delete-mode",
                "trash",
            )
            token = json.loads(dry_run.stdout)["ai_confirmation_summary"]["confirmation_token"]
            (root / "Users/tester/Downloads/download.bin").write_text("download-drifted")

            execute = run_cli_unchecked(
                "--root",
                str(root),
                "--home",
                str(home),
                "--json",
                "clean",
                "run",
                "--plan-file",
                str(plan_file),
                "--require-plan-context",
                "--delete-mode",
                "trash",
                "--execute",
                "--yes",
                "--operation-log",
                str(operation_log),
                "--require-confirmation-token",
                "--confirmation-token",
                token,
            )
            assert execute.returncode != 0
            error_report = json.loads(execute.stderr)
            assert error_report["error"]["code"] == "PLAN_STALE_OR_DRIFTED"
            assert (root / "Users/tester/Downloads/download.bin").exists()

    def test_ai_originated_plan_requires_conservative_execute_guards(self) -> None:
        tmp, root, home = make_sandbox()
        with tmp:
            plan_file = root / "ai-plan.json"
            plan_result = run_cli(
                "--root",
                str(root),
                "--home",
                str(home),
                "--json",
                "plan",
                "--categories",
                "trash",
                "--ai-origin",
            )
            report = json.loads(plan_result.stdout)
            assert report["ai_origin"] is True
            assert report["dry_run"] is True
            assert report["ai_summary"]["phase"] == "plan"

            plan_file.write_text(plan_result.stdout, encoding="utf-8")
            unguarded = run_cli_unchecked(
                "--root",
                str(root),
                "--home",
                str(home),
                "--json",
                "clean",
                "run",
                "--plan-file",
                str(plan_file),
                "--execute",
                "--yes",
            )
            assert unguarded.returncode != 0
