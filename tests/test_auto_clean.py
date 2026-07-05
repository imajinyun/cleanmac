from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from cleancli.auto_clean import DEFAULT_AUTO_CATEGORIES, render_auto_clean
from tests.helpers import make_sandbox, run_cli


class _Category:
    def __init__(self, key: str) -> None:
        self.key = key


def test_auto_clean_module_reports_no_candidates() -> None:
    categories = [_Category("darwinUserTemp")]

    def inspect_items(*args: Any, **kwargs: Any) -> dict[str, Any]:
        return {"total_candidates": 0, "shown_candidates": 0, "total_bytes": 0, "total_human": "0 B", "by_category": {}, "skipped_count": 0}

    def render_plan(*args: Any, **kwargs: Any) -> dict[str, Any]:
        return {"schema": "cleanmac.plan.v1", "candidate_fingerprints": []}

    def validate_plan(payload: dict[str, Any], root: Path, home: Path) -> dict[str, Any]:
        return {"schema": "cleanmac.validate-plan.v1", "valid": True}

    def clean(*args: Any, **kwargs: Any) -> dict[str, Any]:
        return {
            "items": [],
            "total_bytes": 0,
            "total_human": "0 B",
            "skipped_count": 0,
            "deleted_count": 0,
            "failed_count": 0,
            "ai_summary": {"risk_level": "low"},
            "ai_confirmation_summary": {"requires_confirmation": True},
        }

    report = render_auto_clean(
        categories=categories,
        root=Path("/tmp/root"),
        home=Path("/Users/tester"),
        execute=False,
        older_than_days=None,
        max_delete_mb=None,
        max_items=None,
        inspect_items=inspect_items,
        render_clean_plan=render_plan,
        validate_clean_plan_payload=validate_plan,
        clean=clean,
    )

    assert report["schema"] == "cleanmac.auto.v1"
    assert report["phase"] == "dry-run"
    assert report["inspect_summary"]["candidate_count"] == 0
    assert report["dry_run"] is True
    assert report["dry_run_summary"]["item_count"] == 0
    assert report["bytes_freed"] == 0
    assert report["execution"]["executed"] is False


def test_auto_cli_defaults_to_dry_run_with_default_categories() -> None:
    tmp, root, home = make_sandbox()
    with tmp:
        result = run_cli("--root", str(root), "--home", str(home), "--json", "auto")
        report = json.loads(result.stdout)

        assert report["schema"] == "cleanmac.auto.v1"
        assert report["destructive"] is False
        assert report["dry_run"] is True
        assert report["phase"] == "dry-run"
        assert report["selected_categories"] == list(DEFAULT_AUTO_CATEGORIES)
        assert report["execution"]["executed"] is False
        assert report["dry_run_summary"]["item_count"] == len(report["reports"]["dry_run"]["items"])
        assert report["reports"]["execute"] is None


def test_auto_cli_accepts_categories_and_filters() -> None:
    tmp, root, home = make_sandbox()
    with tmp:
        result = run_cli(
            "--root",
            str(root),
            "--home",
            str(home),
            "--json",
            "auto",
            "--categories",
            "trash,userCache",
            "--older-than-days",
            "30",
            "--max-items",
            "5",
        )
        report = json.loads(result.stdout)

        assert report["selected_categories"] == ["trash", "userCache"]
        assert report["older_than_days"] == 30.0
        assert report["max_items"] == 5
        assert report["plan"]["valid"] is True
        assert report["review"]["safe_to_auto_execute"] is False


def test_auto_cli_execute_uses_existing_clean_execution() -> None:
    tmp, root, home = make_sandbox()
    with tmp:
        trash_file = root / "Users/tester/.Trash/old.tmp"
        result = run_cli(
            "--root",
            str(root),
            "--home",
            str(home),
            "--json",
            "auto",
            "--categories",
            "trash",
            "--execute",
        )
        report = json.loads(result.stdout)

        assert report["destructive"] is True
        assert report["phase"] == "execute"
        assert report["execution"]["executed"] is True
        assert report["execution"]["deleted_count"] == 1
        assert report["bytes_freed"] > 0
        assert not trash_file.exists()


def test_auto_cli_rejects_live_root_execute_without_allow_live_root() -> None:
    result = run_cli("--json", "auto", "--execute", "--categories", "trash", check=False)

    assert result.returncode != 0
    assert "Refusing to execute auto cleanup against live root" in result.stderr
