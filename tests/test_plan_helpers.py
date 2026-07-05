from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from cleancli import plan as plan_helpers


def test_load_clean_plan_accepts_audit_wrapped_report(tmp_path: Path) -> None:
    plan_file = tmp_path / "audit.json"
    plan_file.write_text(
        json.dumps(
            {
                "schema": "cleanmac.audit.v1",
                "report": {
                    "schema": "cleanmac.plan.v1",
                    "selected_category_keys": ["trash"],
                    "risk_policy": "strict",
                    "max_delete_mb": 5,
                },
            }
        ),
        encoding="utf-8",
    )

    loaded = plan_helpers.load_clean_plan(
        str(plan_file),
        display_path=str,
        negotiate_plan_schema=lambda payload: {"accepted": True, "schema": payload["schema"]},
    )

    assert loaded["path"] == str(plan_file.resolve(strict=False))
    assert loaded["source_schema"] == "cleanmac.plan.v1"
    assert loaded["category_keys"] == ["trash"]
    assert loaded["risk_policy"] == "strict"
    assert loaded["max_delete_mb"] == 5


def test_load_clean_plan_rejects_non_object_payload(tmp_path: Path) -> None:
    plan_file = tmp_path / "bad.json"
    plan_file.write_text("[]", encoding="utf-8")

    with pytest.raises(ValueError, match="Plan file must contain a JSON object"):
        plan_helpers.load_clean_plan(
            str(plan_file),
            display_path=str,
            negotiate_plan_schema=lambda payload: {"accepted": True},
        )


def test_plan_schema_warnings_reports_legacy_schema() -> None:
    warnings = plan_helpers.plan_schema_warnings(
        {
            "accepted": True,
            "legacy": True,
            "schema": "cleanmac.clean-plan.v1",
            "latest_supported_schema": "cleanmac.plan.v1",
        }
    )

    assert warnings == [
        {
            "code": "LEGACY_PLAN_SCHEMA",
            "schema": "cleanmac.clean-plan.v1",
            "message": "Plan schema cleanmac.clean-plan.v1 is supported for compatibility; cleanmac.plan.v1 is preferred.",
        }
    ]


def test_render_plan_freshness_detects_expired_plan_and_drift() -> None:
    now = datetime(2026, 1, 1, tzinfo=timezone.utc)
    generated = now - timedelta(seconds=120)
    expires = now - timedelta(seconds=1)

    report = plan_helpers.render_plan_freshness_report(
        {
            "generated_at": generated.isoformat(),
            "expires_at": expires.isoformat(),
            "plan_max_age_seconds": 30,
            "candidate_fingerprints": [{"path": "/tmp/a"}],
        },
        compare_candidate_fingerprints=lambda rows: [{"path": rows[0]["path"], "status": "changed"}],
        parse_iso_datetime=lambda value: datetime.fromisoformat(str(value)) if value else None,
        plan_max_age_seconds=1800,
        now=now,
    )

    assert report["schema"] == "cleanmac.plan-freshness.v1"
    assert report["fresh"] is False
    assert report["stale_reasons"] == ["plan-age-exceeded", "plan-expired"]
    assert report["drift_count"] == 1
    assert report["suggested_next_action"] == "regenerate_plan_and_repeat_dry_run"


def test_build_clean_plan_payload_preserves_plan_contract() -> None:
    generated = datetime(2026, 1, 1, tzinfo=timezone.utc)
    pre_report = {
        "summary": {
            "estimated_reclaimable_bytes": 128,
            "estimated_reclaimable_human": "128 B",
            "requires_yes_for_execute": False,
            "yes_required_categories": [],
        },
        "candidates": [],
    }

    payload = plan_helpers.build_clean_plan_payload(
        generated_at=generated,
        plan_max_age_seconds=60,
        ai_origin=True,
        ai_summary={"schema": "cleanmac.ai-summary.v1"},
        ai_confirmation_summary={"schema": "cleanmac.ai-confirmation-summary.v1"},
        category_keys=["trash"],
        selected_categories=[{"key": "trash"}],
        risk_policy="default",
        max_delete_mb=5,
        include_patterns=["*.tmp"],
        exclude_patterns=["*.keep"],
        older_than_days=7,
        min_size_mb=1,
        name_regex="tmp$",
        max_items=10,
        root="/tmp/root",
        home="/Users/tester",
        pre_clean_report=pre_report,
        candidate_fingerprints=[],
        by_category={},
        by_file_type={},
        by_parent_directory={},
        replay_command="python3 cleanmac.py clean --categories trash",
    )

    assert payload["schema"] == "cleanmac.plan.v1"
    assert payload["destructive"] is False
    assert payload["dry_run"] is True
    assert payload["generated_at"] == generated.isoformat()
    assert payload["expires_at"] == (generated + timedelta(seconds=60)).isoformat()
    assert payload["ai_origin"] is True
    assert payload["selected_category_keys"] == ["trash"]
    assert payload["estimated_reclaimable_bytes"] == 128
    assert payload["replay_command"] == "python3 cleanmac.py clean --categories trash"
