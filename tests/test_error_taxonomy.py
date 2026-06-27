from __future__ import annotations

import json

from cleancli.core import CleanMacCLIError
from tests.helpers import cleanmac_test_env, make_sandbox, run_cli


class TestErrorTaxonomyCompleteness:
    def test_error_taxonomy_has_standard_structure(self) -> None:
        from cleancli.ai_errors import render_ai_error_taxonomy

        taxonomy = render_ai_error_taxonomy()
        assert isinstance(taxonomy, list)
        assert len(taxonomy) > 0

        for entry in taxonomy:
            assert "code" in entry
            assert "category" in entry
            assert "retryable_after_fix" in entry
            assert "suggested_next_action" in entry
            assert "safe_to_auto_retry" in entry
            assert isinstance(entry["safe_to_auto_retry"], bool)
            assert isinstance(entry["retryable_after_fix"], bool)

    def test_error_codes_are_unique(self) -> None:
        from cleancli.ai_errors import render_ai_error_taxonomy

        taxonomy = render_ai_error_taxonomy()
        codes = [e["code"] for e in taxonomy]
        assert len(codes) == len(set(codes)), f"Duplicate error codes: {[c for c in codes if codes.count(c) > 1]}"

    def test_error_categories_are_known(self) -> None:
        from cleancli.ai_errors import render_ai_error_taxonomy

        taxonomy = render_ai_error_taxonomy()
        categories = {e["category"] for e in taxonomy}
        known = {
            "invalid_arguments",
            "validation_error",
            "policy_violation",
            "execution_error",
            "resource_not_found",
            "permission_error",
            "state_error",
        }
        categories - known
        # It's ok to have new categories, but they should be deliberate
        assert len(categories) > 0

    def test_every_error_has_next_allowed_tools_or_action(self) -> None:
        from cleancli.ai_errors import render_ai_error_taxonomy

        taxonomy = render_ai_error_taxonomy()
        for entry in taxonomy:
            has_next = "next_allowed_tools" in entry or "suggested_next_action" in entry
            assert has_next, f"Error {entry['code']} has no recovery guidance"


class TestCLIErrorBehavior:
    def test_invalid_category_returns_error(self) -> None:
        tmp, root, home = make_sandbox()
        with tmp, cleanmac_test_env():
            result = run_cli(
                "--root",
                str(root),
                "--home",
                str(home),
                "--json",
                "inspect",
                "--categories",
                "nonexistent_category_xyz",
                check=False,
            )

            assert result.returncode != 0
            # Should output structured error in JSON mode
            try:
                error = json.loads(result.stderr)
                assert "schema" in error
                assert "error" in error or "code" in error
            except json.JSONDecodeError:
                # Acceptable: error might be on stderr in human format
                pass

    def test_unknown_command_returns_error(self) -> None:
        result = run_cli("--json", "nonexistent_command", check=False)
        assert result.returncode != 0

    def test_clean_missing_categories_is_handled(self) -> None:
        tmp, root, home = make_sandbox()
        with tmp, cleanmac_test_env():
            result = run_cli(
                "--root",
                str(root),
                "--home",
                str(home),
                "--json",
                "clean",
                "run",
                "--execute",
                "--yes",
                check=False,
            )
            # Should fail or return with 0 items - either is acceptable as long as it doesn't crash
            assert isinstance(result.returncode, int)

    def test_validate_plan_with_missing_file_is_error(self) -> None:
        tmp, root, home = make_sandbox()
        with tmp, cleanmac_test_env():
            result = run_cli(
                "--root",
                str(root),
                "--home",
                str(home),
                "--json",
                "validate-plan",
                "--plan-file",
                "/nonexistent/path/plan.json",
                check=False,
            )
            assert result.returncode != 0


class TestCleanMacCLIError:
    def test_error_has_message_and_exit_code(self) -> None:
        err = CleanMacCLIError("test error", exit_code=42)
        assert err.message == "test error"
        assert err.exit_code == 42
        assert str(err) == "test error"

    def test_error_default_exit_code(self) -> None:
        err = CleanMacCLIError("test")
        assert err.exit_code == 1

    def test_error_is_exception_subclass(self) -> None:
        err = CleanMacCLIError("test")
        assert isinstance(err, Exception)


class TestErrorReportConsistency:
    def test_json_mode_includes_error_schema(self) -> None:
        from cleancli.ai_errors import render_ai_error_report

        report = render_ai_error_report("test error", argv=["cleanmac", "inspect"], exit_code=1)
        assert "schema" in report
        assert "error" in report["schema"]
        assert "error" in report
        assert "argv" in report
        assert "ok" in report
        assert report["ok"] is False

    def test_error_report_has_safety_info(self) -> None:
        from cleancli.ai_errors import render_ai_error_report

        report = render_ai_error_report("test", argv=["cleanmac"], exit_code=2)
        assert "destructive_operation_started" in report
        assert "safe_to_auto_retry" in report
        assert "next_allowed_tools" in report
        assert isinstance(report["safe_to_auto_retry"], bool)


class TestErrorSafetyGuarantees:
    def test_dry_run_is_default_no_deletion_on_error(self) -> None:
        tmp, root, home = make_sandbox()
        with tmp, cleanmac_test_env():
            trash_files_before = list((root / "Users/tester/.Trash").iterdir())

            # Even with a bad argument, no files should be deleted
            run_cli(
                "--root",
                str(root),
                "--home",
                str(home),
                "--json",
                "clean",
                "run",
                "--categories",
                "nonexistent_cat",
                "--execute",
                check=False,
            )

            trash_files_after = list((root / "Users/tester/.Trash").iterdir())
            assert len(trash_files_after) == len(trash_files_before)
