from __future__ import annotations

import json
import plistlib
import subprocess
import sys
from pathlib import Path

from cleancli.ai_versioning import validate_contract_payload
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


def write_startup_fixtures(root: Path) -> None:
    user_agents = root / "Users/tester/Library/LaunchAgents"
    daemons = root / "Library/LaunchDaemons"
    user_agents.mkdir(parents=True)
    daemons.mkdir(parents=True)
    (user_agents / "com.example.agent.plist").write_bytes(
        plistlib.dumps(
            {
                "Label": "com.example.agent",
                "ProgramArguments": ["/Applications/Example.app/Contents/MacOS/agent"],
                "RunAtLoad": True,
            }
        )
    )
    (daemons / "com.example.daemon.plist").write_bytes(
        plistlib.dumps({"Label": "com.example.daemon", "KeepAlive": True})
    )


def write_privacy_cache_fixtures(root: Path) -> None:
    paths = [
        root / "Users/tester/Library/Caches/Google/Chrome/Default/Cache/data_0",
        root / "Users/tester/Library/Application Support/Google/Chrome/Default/Code Cache/js/cache.js",
        root / "Users/tester/Library/Application Support/Microsoft Edge/Default/Cache/data_0",
        root
        / "Users/tester/Library/Application Support/Microsoft Edge/Default/Service Worker/CacheStorage/cache-a/cache.bin",
        root / "Users/tester/Library/Application Support/BraveSoftware/Brave-Browser/Default/Cache/data_0",
        root / "Users/tester/Library/Application Support/Arc/User Data/Default/Cache/data_0",
        root / "Users/tester/Library/Caches/Firefox/Profiles/dev.default-release/cache2/entries/cache.bin",
        root / "Users/tester/Library/Application Support/Firefox/Profiles/dev.default-release/cache2/entries/cache.bin",
        root / "Users/tester/Library/Application Support/Slack/Cache/cache.bin",
        root / "Users/tester/Library/Application Support/discord/Cache/cache.bin",
        root / "Users/tester/Library/Application Support/Notion/Cache/cache.bin",
    ]
    for path in paths:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("privacy-cache", encoding="utf-8")


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


def test_review_generates_selection_file_from_plan() -> None:
    tmp, root, _home = make_sandbox()
    with tmp:
        plan_file = root / "plan.json"
        selection_file = root / "selection.json"
        plan_file.write_text(
            json.dumps(
                {
                    "schema": "cleanmac.software-uninstall-plan.v1",
                    "uninstall_plan": {
                        "candidates": [
                            {
                                "id": "cache:/tmp/cache",
                                "path": "/tmp/cache",
                                "kind": "cache",
                                "risk": "low",
                                "default_selected": True,
                                "matched_rule": "software-orphan.cache.missing-installed-bundle-id",
                                "match_reason": "missing-installed-bundle-id",
                                "confidence": "medium",
                                "risk_reason": "rebuildable cache",
                                "risk_explanation": "Caches are rebuildable after review.",
                                "recovery": "Restore from Trash if needed.",
                                "delete_mode": "trash",
                                "review_evidence": {
                                    "schema": "cleanmac.candidate-review-evidence.v1",
                                    "matched_rule": "software-orphan.cache.missing-installed-bundle-id",
                                    "match_reason": "missing-installed-bundle-id",
                                    "confidence": "medium",
                                    "risk": "low",
                                    "risk_reason": "rebuildable cache",
                                    "risk_explanation": "Caches are rebuildable after review.",
                                    "default_selected": True,
                                    "why_not_default": None,
                                    "protected": False,
                                    "delete_mode": "trash",
                                    "recovery": "Restore from Trash if needed.",
                                    "contains_user_data": False,
                                    "shared_container": False,
                                    "recommended_next_action": "review-orphan-before-trash-execution",
                                },
                            }
                        ]
                    },
                }
            ),
            encoding="utf-8",
        )

        report = json.loads(
            run_cli("--json", "review", "--input-file", str(plan_file), "--selection-file", str(selection_file)).stdout
        )
        selection = json.loads(selection_file.read_text(encoding="utf-8"))
        item = report["items"][0]

        assert report["schema"] == "cleanmac.review.v1"
        assert selection["schema"] == "cleanmac.review-selection.v1"
        assert selection["selected_item_ids"] == ["cache:/tmp/cache"]
        assert item["matched_rule"] == "software-orphan.cache.missing-installed-bundle-id"
        assert item["match_reason"] == "missing-installed-bundle-id"
        assert item["confidence"] == "medium"
        assert item["review_evidence"]["schema"] == "cleanmac.candidate-review-evidence.v1"
        assert item["review_evidence"]["recommended_next_action"] == "review-orphan-before-trash-execution"
        assert report["selection_summary"] == selection["summary"]
        assert report["human_summary"]["schema"] == "cleanmac.human-summary.v1"
        assert "Review selected 1 of 1" in report["human_summary"]["headline"]
        assert report["human_summary"]["safe_to_execute"] is False
        assert "--review-selection-file" in report["human_summary"]["next_command"]
        assert selection["summary"]["schema"] == "cleanmac.review-selection-summary.v1"
        assert selection["summary"]["selected_count"] == 1
        assert selection["summary"]["excluded_count"] == 0
        assert selection["summary"]["selected_risk_counts"] == {"low": 1}
        assert selection["summary"]["requires_sensitive_review"] is False
        assert validate_contract_payload("cleanmac.review.v1", report)["valid"] is True
        assert validate_contract_payload("cleanmac.review-selection.v1", selection)["valid"] is True
        assert validate_contract_payload("cleanmac.review-selection-summary.v1", selection["summary"])["valid"] is True


def test_review_selection_supports_explicit_include_and_exclude() -> None:
    tmp, root, _home = make_sandbox()
    with tmp:
        plan_file = root / "plan.json"
        selection_file = root / "selection.json"
        plan_file.write_text(
            json.dumps(
                {
                    "schema": "cleanmac.software-uninstall-plan.v1",
                    "uninstall_plan": {
                        "candidates": [
                            {
                                "id": "cache:/tmp/cache",
                                "path": "/tmp/cache",
                                "kind": "cache",
                                "risk": "low",
                                "default_selected": True,
                            },
                            {
                                "id": "history:/tmp/history",
                                "path": "/tmp/history",
                                "kind": "history",
                                "risk": "medium",
                                "default_selected": False,
                            },
                            {
                                "id": "protected:/System/Library",
                                "path": "/System/Library",
                                "kind": "system",
                                "risk": "critical",
                                "default_selected": False,
                                "protected": True,
                            },
                        ]
                    },
                }
            ),
            encoding="utf-8",
        )

        report = json.loads(
            run_cli(
                "--json",
                "review",
                "--input-file",
                str(plan_file),
                "--selection-file",
                str(selection_file),
                "--exclude-item",
                "cache:/tmp/cache",
                "--select-item",
                "history:/tmp/history",
                "--select-item",
                "protected:/System/Library",
                "--select-item",
                "missing:item",
            ).stdout
        )
        selection = json.loads(selection_file.read_text(encoding="utf-8"))

        assert report["selection"] == selection
        assert selection["selected_item_ids"] == ["history:/tmp/history"]
        assert "cache:/tmp/cache" in selection["excluded_item_ids"]
        assert selection["explicit_selected_item_ids"] == [
            "history:/tmp/history",
            "protected:/System/Library",
            "missing:item",
        ]
        assert selection["explicit_excluded_item_ids"] == ["cache:/tmp/cache"]
        assert selection["protected_item_ids"] == ["protected:/System/Library"]
        assert selection["unknown_item_ids"] == ["missing:item"]
        assert selection["summary"]["selected_risk_counts"] == {"medium": 1}
        assert selection["summary"]["excluded_risk_counts"] == {"critical": 1, "low": 1}
        assert selection["summary"]["protected_count"] == 1
        assert selection["summary"]["unknown_item_count"] == 1
        assert validate_contract_payload("cleanmac.review.v1", report)["valid"] is True
        assert validate_contract_payload("cleanmac.review-selection.v1", selection)["valid"] is True


def test_review_html_escapes_paths() -> None:
    tmp, root, _home = make_sandbox()
    with tmp:
        plan_file = root / "plan.json"
        plan_file.write_text(
            json.dumps({"schema": "cleanmac.test.v1", "items": [{"path": "<script>alert(1)</script>"}]}),
            encoding="utf-8",
        )
        result = run_cli("review", "--input-file", str(plan_file), "--format", "html")

        assert "&lt;script&gt;alert(1)&lt;/script&gt;" in result.stdout
        assert "<script>alert(1)</script>" not in result.stdout


def test_review_supports_startup_and_privacy_plans() -> None:
    tmp, root, home = make_sandbox()
    with tmp:
        write_startup_fixtures(root)
        write_privacy_cache_fixtures(root)
        startup_plan_file = root / "startup-plan.json"
        startup_plan = json.loads(run_cli("--root", str(root), "--home", str(home), "--json", "startup", "plan").stdout)
        startup_plan_file.write_text(json.dumps(startup_plan), encoding="utf-8")
        startup_review = json.loads(run_cli("--json", "review", "--input-file", str(startup_plan_file)).stdout)

        assert startup_review["schema"] == "cleanmac.review.v1"
        assert startup_review["source_schema"] == "cleanmac.startup-plan.v1"
        assert startup_review["item_count"] == 2
        assert startup_review["default_selected_count"] == 1
        assert any(item["recommendation"] == "review-disable" for item in startup_review["items"])
        for item in startup_review["items"]:
            evidence = item["review_evidence"]
            assert evidence["schema"] == "cleanmac.candidate-review-evidence.v1"
            assert evidence["matched_rule"].startswith("startup.")
            assert evidence["risk"] == item["risk"]
            assert evidence["default_selected"] == item["default_selected"]
            assert evidence["protected"] == item["protected"]
            assert validate_contract_payload("cleanmac.candidate-review-evidence.v1", evidence)["valid"] is True

        privacy_plan_file = root / "privacy-plan.json"
        privacy_plan = json.loads(
            run_cli("--root", str(root), "--home", str(home), "--json", "privacy", "plan", "--scope", "cache").stdout
        )
        privacy_plan_file.write_text(json.dumps(privacy_plan), encoding="utf-8")
        privacy_review = json.loads(run_cli("--json", "review", "--input-file", str(privacy_plan_file)).stdout)

        assert privacy_review["schema"] == "cleanmac.review.v1"
        assert privacy_review["source_schema"] == "cleanmac.privacy-plan.v1"
        assert privacy_review["item_count"] >= 8
        assert privacy_review["default_selected_count"] >= 1
        assert any(item["scope"] == "cache" for item in privacy_review["items"])
        for item in privacy_review["items"]:
            evidence = item["review_evidence"]
            assert evidence["schema"] == "cleanmac.candidate-review-evidence.v1"
            assert evidence["matched_rule"].startswith("privacy.")
            assert evidence["risk"] == item["risk"]
            assert evidence["default_selected"] == item["default_selected"]
            assert evidence["protected"] == item["protected"]
            assert validate_contract_payload("cleanmac.candidate-review-evidence.v1", evidence)["valid"] is True
