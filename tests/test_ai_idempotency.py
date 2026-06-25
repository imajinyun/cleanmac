"""Behavior-level idempotency tests for AI-friendly cleanmac workflows."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, cast

from cleancli.core import CATEGORIES, ai_confirmation_token, ai_confirmation_token_context
from tests.helpers import cleanmac_test_env, make_sandbox, run_clean_json

VOLATILE_KEYS = {"generated_at", "expires_at", "timestamp", "started_at", "finished_at", "duration_ms"}


def _strip_volatile(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: _strip_volatile(child) for key, child in value.items() if key not in VOLATILE_KEYS}
    if isinstance(value, list):
        return [_strip_volatile(child) for child in value]
    return value


def test_repeated_inspect_produces_stable_output() -> None:
    with cleanmac_test_env():
        tmp, root, home = make_sandbox()
        with tmp:
            first = run_clean_json(root, home, "inspect", "--categories", "trash")
            second = run_clean_json(root, home, "inspect", "--categories", "trash")

    assert _strip_volatile(first) == _strip_volatile(second)


def test_repeated_generate_plan_produces_stable_plan_after_stripping_expiry() -> None:
    with cleanmac_test_env():
        tmp, root, home = make_sandbox()
        with tmp:
            first = run_clean_json(root, home, "plan", "--categories", "trash", "--ai-origin")
            second = run_clean_json(root, home, "plan", "--categories", "trash", "--ai-origin")

    assert first["schema"] == "cleanmac.plan.v1"
    assert _strip_volatile(first) == _strip_volatile(second)


def test_replayed_dry_run_keeps_token_stable_within_same_plan() -> None:
    with cleanmac_test_env():
        tmp, root, home = make_sandbox()
        with tmp:
            plan_file = Path(tmp.name) / "plan.json"
            plan = run_clean_json(root, home, "plan", "--categories", "trash", "--ai-origin")
            plan_file.write_text(json.dumps(plan), encoding="utf-8")

            first = run_clean_json(root, home, "run", "--plan-file", str(plan_file), "--delete-mode", "trash")
            second = run_clean_json(root, home, "run", "--plan-file", str(plan_file), "--delete-mode", "trash")

    token1 = cast(dict[str, Any], first["ai_confirmation_summary"])["confirmation_token"]
    token2 = cast(dict[str, Any], second["ai_confirmation_summary"])["confirmation_token"]
    assert token1
    assert token1 == token2


def test_replayed_dry_run_token_changes_when_plan_content_changes() -> None:
    with cleanmac_test_env():
        tmp, root, home = make_sandbox()
        with tmp:
            plan_file = Path(tmp.name) / "plan.json"
            plan = run_clean_json(root, home, "plan", "--categories", "trash", "--ai-origin")
            plan_file.write_text(json.dumps(plan), encoding="utf-8")
            first = run_clean_json(root, home, "run", "--plan-file", str(plan_file), "--delete-mode", "trash")

            drifted_plan = dict(plan)
            drifted_plan["selected_category_keys"] = ["downloads"]
            drifted_plan["categories"] = ["downloads"]
            plan_file.write_text(json.dumps(drifted_plan), encoding="utf-8")
            second = run_clean_json(root, home, "run", "--plan-file", str(plan_file), "--delete-mode", "trash")

    first_summary = cast(dict[str, Any], first["ai_confirmation_summary"])
    second_summary = cast(dict[str, Any], second["ai_confirmation_summary"])
    token1 = first_summary["confirmation_token"]
    token2 = second_summary["confirmation_token"]
    sha1 = cast(dict[str, Any], first_summary["confirmation_token_context"])["plan_sha256"]
    sha2 = cast(dict[str, Any], second_summary["confirmation_token_context"])["plan_sha256"]

    assert token1
    assert token2
    assert token1 != token2
    assert sha1 != sha2


def test_ai_confirmation_token_changes_across_execution_boundaries() -> None:
    categories = [category for category in CATEGORIES if category.key in ("trash", "downloads")]
    base: dict[str, Any] = {
        "categories": categories,
        "root": Path("/sandbox"),
        "home": Path("/Users/tester"),
        "risk_policy": "default",
        "max_delete_mb": 10.0,
        "max_items": 5,
        "include_patterns": [],
        "exclude_patterns": [],
        "older_than_days": None,
        "min_size_mb": 0,
        "name_regex": None,
        "bundle_allowlist": [],
        "bundle_blocklist": ["com.apple.mail"],
        "delete_mode": "trash",
        "plan_file": None,
        "rows": [],
    }

    context = ai_confirmation_token_context(**base)
    token = ai_confirmation_token(context)
    hex_part = token.removeprefix("cleanmac-confirm-")

    assert token.startswith("cleanmac-confirm-")
    assert len(hex_part) == 32
    assert set(hex_part).issubset(set("0123456789abcdef"))
    assert ai_confirmation_token(ai_confirmation_token_context(**base)) == token
    assert context["delete_mode"] == "trash"
    assert context["max_delete_mb"] == 10.0
    assert context["max_items"] == 5
    assert context["bundle_blocklist"] == ["com.apple.mail"]

    assert ai_confirmation_token(ai_confirmation_token_context(**(base | {"root": Path("/other")}))) != token
    assert ai_confirmation_token(ai_confirmation_token_context(**(base | {"home": Path("/Users/other")}))) != token
    assert ai_confirmation_token(ai_confirmation_token_context(**(base | {"delete_mode": "permanent"}))) != token
    assert ai_confirmation_token(ai_confirmation_token_context(**(base | {"max_delete_mb": 20.0}))) != token
    assert ai_confirmation_token(ai_confirmation_token_context(**(base | {"max_items": 10}))) != token

    single_category = [category for category in CATEGORIES if category.key == "trash"]
    assert ai_confirmation_token(ai_confirmation_token_context(**(base | {"categories": single_category}))) != token

    empty_context = ai_confirmation_token_context(
        categories=[],
        root=Path("/"),
        home=Path("/"),
        risk_policy="default",
        max_delete_mb=None,
        max_items=None,
        include_patterns=[],
        exclude_patterns=[],
        older_than_days=None,
        min_size_mb=0,
        name_regex=None,
        bundle_allowlist=[],
        bundle_blocklist=[],
        delete_mode="permanent",
        plan_file=None,
        rows=[],
    )
    empty_token = ai_confirmation_token(empty_context)
    assert empty_token.startswith("cleanmac-confirm-")
    assert len(empty_token.removeprefix("cleanmac-confirm-")) == 32


def test_ai_confirmation_token_binds_filters_plan_and_candidate_rows(tmp_path: Path) -> None:
    categories = [category for category in CATEGORIES if category.key in ("trash", "downloads")]
    plan_file = tmp_path / "plan.json"
    plan_file.write_text('{"schema":"cleanmac.plan.v1","selected_category_keys":["trash"]}', encoding="utf-8")
    base: dict[str, Any] = {
        "categories": categories,
        "root": Path("/sandbox"),
        "home": Path("/Users/tester"),
        "risk_policy": "default",
        "max_delete_mb": 10.0,
        "max_items": 5,
        "include_patterns": ["*.tmp"],
        "exclude_patterns": ["*.keep"],
        "older_than_days": 7.0,
        "min_size_mb": 1,
        "name_regex": "cache",
        "bundle_allowlist": ["com.example.allowed"],
        "bundle_blocklist": ["com.apple.mail"],
        "delete_mode": "trash",
        "plan_file": str(plan_file),
        "rows": [
            {
                "category": "trash",
                "path": "/sandbox/Users/tester/.Trash/old.tmp",
                "bytes": 10,
                "bundle_id": None,
            }
        ],
    }

    context = ai_confirmation_token_context(**base)
    token = ai_confirmation_token(context)

    assert context["plan_file"] == str(plan_file)
    assert context["plan_sha256"]
    assert context["candidate_count"] == 1
    assert context["candidate_bytes"] == 10
    assert context["candidates"] == [
        {
            "category": "trash",
            "path": "/sandbox/Users/tester/.Trash/old.tmp",
            "bytes": 10,
            "bundle_id": None,
        }
    ]

    variant_keys = {
        "include_patterns": ["*.log"],
        "exclude_patterns": ["*.bak"],
        "older_than_days": 30.0,
        "min_size_mb": 2,
        "name_regex": "logs",
        "bundle_allowlist": ["com.example.other"],
        "bundle_blocklist": ["com.apple.MobileSMS"],
        "rows": [
            {
                "category": "downloads",
                "path": "/sandbox/Users/tester/Downloads/download.bin",
                "bytes": 20,
                "bundle_id": "com.example.app",
            }
        ],
    }
    for key, value in variant_keys.items():
        changed = base | {key: value}
        assert ai_confirmation_token(ai_confirmation_token_context(**changed)) != token

    plan_file.write_text('{"schema":"cleanmac.plan.v1","selected_category_keys":["downloads"]}', encoding="utf-8")
    assert ai_confirmation_token(ai_confirmation_token_context(**base)) != token
