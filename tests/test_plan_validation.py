from __future__ import annotations

import json
from typing import Any

import pytest

import cleancli.core as cleancli
from tests.helpers import make_sandbox, run_cli


def test_plan_command_marks_ai_originated_plan() -> None:
    tmp, root, home = make_sandbox()
    with tmp:
        plan_result = run_cli(
            "--root",
            str(root),
            "--home",
            str(home),
            "--json",
            "clean",
            "plan",
            "--categories",
            "trash",
            "--ai-origin",
        )
        plan_file = root / "ai-plan.json"
        plan_file.write_text(plan_result.stdout, encoding="utf-8")
        plan = json.loads(plan_result.stdout)

        assert plan["ai_origin"] is True

        validate_result = run_cli(
            "--root",
            str(root),
            "--home",
            str(home),
            "--json",
            "clean",
            "validate-plan",
            "--plan-file",
            str(plan_file),
        )
        validate_report = json.loads(validate_result.stdout)

        assert validate_report["valid"] is True
        assert validate_report["plan"]["ai_origin"] is True


def test_clean_plan_file_reuses_categories_and_policy() -> None:
    tmp, root, home = make_sandbox()
    with tmp:
        plan_file = root / "plan.json"
        plan_file.write_text(
            json.dumps(
                {
                    "categories": ["trash"],
                    "risk_policy": "strict",
                    "max_delete_mb": 5,
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
        )
        report = json.loads(result.stdout)

        assert [row["key"] for row in report["selected_categories"]] == ["trash"]
        assert report["risk_policy"] == "strict"
        assert report["max_delete_mb"] == 5.0
        assert report["plan_metadata"]["path"] == str(plan_file)


def test_validate_plan_reports_replay_metadata() -> None:
    tmp, root, home = make_sandbox()
    with tmp:
        plan_file = root / "plan.json"
        plan_file.write_text(
            json.dumps(
                {
                    "schema": "cleanmac.plan.v1",
                    "selected_category_keys": ["trash"],
                    "risk_policy": "default",
                    "root": str(root),
                    "home": str(home),
                }
            )
        )
        result = run_cli(
            "--root",
            str(root),
            "--home",
            str(home),
            "--json",
            "validate-plan",
            "--plan-file",
            str(plan_file),
        )
        report = json.loads(result.stdout)

        assert report["valid"] is True
        assert report["plan"]["category_keys"] == ["trash"]
        assert report["schema_negotiation"]["schema"] == "cleanmac.plan.v1"
        assert report["schema_negotiation"]["accepted"] is True
        assert report["unknown_categories"] == []
        assert report["context_warnings"] == []
        assert "clean" in report["replay_clean_command"]


def test_validate_plan_reports_unknown_categories_as_invalid() -> None:
    tmp, root, home = make_sandbox()
    with tmp:
        plan_file = root / "unknown-plan.json"
        plan_file.write_text(json.dumps({"selected_category_keys": ["trash", "ghost"]}))

        result = run_cli(
            "--root",
            str(root),
            "--home",
            str(home),
            "--json",
            "validate-plan",
            "--plan-file",
            str(plan_file),
        )
        report = json.loads(result.stdout)

        assert report["valid"] is False
        assert report["unknown_categories"] == ["ghost"]
        assert "trash" in report["replay_clean_command"]
        assert "ghost" not in report["replay_clean_command"]


def test_validate_plan_rejects_unsupported_schema_version() -> None:
    tmp, root, home = make_sandbox()
    with tmp:
        plan_file = root / "unsupported-plan.json"
        plan_file.write_text(
            json.dumps(
                {
                    "schema": "cleanmac.plan." + "v99",
                    "selected_category_keys": ["trash"],
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
            "validate-plan",
            "--plan-file",
            str(plan_file),
        )
        report = json.loads(result.stdout)

        assert report["valid"] is False
        assert report["schema_negotiation"]["schema"] == "cleanmac.plan." + "v99"
        assert report["schema_negotiation"]["reason"] == "unsupported-schema-version"
        assert report["schema_negotiation"]["latest_supported_schema"] == "cleanmac.plan.v1"


def test_plan_schema_negotiation_is_exposed_in_process_for_coverage() -> None:
    tmp, root, home = make_sandbox()
    with tmp:
        supported_plan = root / "supported-plan.json"
        supported_plan.write_text(
            json.dumps(
                {
                    "schema": "cleanmac.plan.v1",
                    "selected_category_keys": ["trash"],
                    "risk_policy": "default",
                    "root": str(root),
                    "home": str(home),
                }
            ),
            encoding="utf-8",
        )
        loaded = cleancli.load_clean_plan(str(supported_plan))
        assert loaded["source_schema"] == "cleanmac.plan.v1"
        assert loaded["schema_negotiation"]["accepted"] is True

        validation = cleancli.validate_clean_plan(str(supported_plan), root=root, home=home)
        assert validation["valid"] is True
        assert validation["schema_negotiation"]["latest_supported_schema"] == "cleanmac.plan.v1"

        legacy_plan = root / "legacy-plan.json"
        legacy_plan.write_text(json.dumps({"selected_category_keys": ["trash"]}), encoding="utf-8")
        legacy = cleancli.load_clean_plan(str(legacy_plan))
        assert legacy["source_schema"] == ""
        assert legacy["schema_negotiation"]["reason"] == "legacy-missing-schema-field"

        unsupported_plan = root / "unsupported-in-process-plan.json"
        unsupported_plan.write_text(
            json.dumps({"schema": "cleanmac.plan." + "v99", "selected_category_keys": ["trash"]}),
            encoding="utf-8",
        )
        unsupported = cleancli.load_clean_plan(str(unsupported_plan))
        with pytest.raises(SystemExit, match="Unsupported plan schema cleanmac.plan." + "v99"):
            cleancli.ensure_supported_plan_schema(unsupported)


@pytest.mark.parametrize(
    ("label", "schema", "expected_valid", "expected_legacy"),
    [
        ("latest", "cleanmac.plan.v1", True, False),
        ("clean-report", "cleanmac.clean.v1", True, True),
        ("legacy-plan", "cleanmac.clean-plan.v1", True, True),
        ("missing-schema", None, True, True),
        ("unsupported", "cleanmac.plan." + "v99", False, False),
    ],
)
def test_plan_schema_negotiation_matrix_for_ai_hosts(
    label: str, schema: str | None, expected_valid: bool, expected_legacy: bool
) -> None:
    tmp, root, home = make_sandbox()
    with tmp:
        plan_file = root / f"{label}.json"
        plan_payload: dict[str, Any] = {"selected_category_keys": ["trash"]}
        if schema is not None:
            plan_payload["schema"] = schema
        plan_file.write_text(json.dumps(plan_payload), encoding="utf-8")

        validation = cleancli.validate_clean_plan(str(plan_file), root=root, home=home)
        assert validation["valid"] == expected_valid
        assert validation["schema_negotiation"]["legacy"] == expected_legacy
        if expected_legacy:
            assert validation["schema_warnings"][0]["code"] == "LEGACY_PLAN_SCHEMA"
        else:
            assert validation["schema_warnings"] == []

        loaded = cleancli.load_clean_plan(str(plan_file))
        if expected_valid:
            cleancli.ensure_supported_plan_schema(loaded)
        else:
            with pytest.raises(SystemExit, match="Unsupported plan schema cleanmac.plan." + "v99"):
                cleancli.ensure_supported_plan_schema(loaded)


def test_clean_can_replay_categories_from_audit_report_file() -> None:
    tmp, root, home = make_sandbox()
    with tmp:
        audit_file = root / "clean-audit.json"
        run_cli(
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

        result = run_cli(
            "--root",
            str(root),
            "--home",
            str(home),
            "--json",
            "clean",
            "--plan-file",
            str(audit_file),
        )
        report = json.loads(result.stdout)

        assert [row["key"] for row in report["selected_categories"]] == ["trash"]
        assert report["plan_metadata"]["path"] == str(audit_file)
        assert (root / "Users/tester/.Trash/old.tmp").exists()


def test_validate_plan_includes_current_preview_and_budgets() -> None:
    tmp, root, home = make_sandbox()
    with tmp:
        plan_file = root / "plan-preview.json"
        plan_file.write_text(
            json.dumps(
                {
                    "selected_category_keys": ["trash"],
                    "include_patterns": ["old.tmp"],
                    "max_items": 2,
                    "max_delete_mb": 1,
                }
            )
        )
        result = run_cli(
            "--root",
            str(root),
            "--home",
            str(home),
            "--json",
            "validate-plan",
            "--plan-file",
            str(plan_file),
        )
        report = json.loads(result.stdout)

        assert report["valid"] is True
        assert report["preview"] is not None
        assert report["preview"]["include_patterns"] == ["old.tmp"]
        assert report["preview"]["shown_candidates"] == 1
        assert report["budget_summary"]["within_max_items"] is True
        assert report["budget_summary"]["within_max_delete_budget"] is True
