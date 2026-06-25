from __future__ import annotations

import json
from pathlib import Path

from cleancli.ai_versioning import validate_contract_payload
from tests.helpers import make_sandbox, run_cli


def _write_app(root: Path, name: str, bundle_id: str) -> Path:
    app_contents = root / f"Applications/{name}.app/Contents"
    app_contents.mkdir(parents=True)
    app_contents.joinpath("Info.plist").write_bytes(
        b'<?xml version="1.0" encoding="UTF-8"?>'
        b'<plist version="1.0"><dict><key>CFBundleIdentifier</key><string>'
        + bundle_id.encode("utf-8")
        + b"</string></dict></plist>"
    )
    return app_contents


def test_software_inspect_reports_uninstall_candidates() -> None:
    tmp, root, home = make_sandbox()
    with tmp:
        _write_app(root, "Example", "com.example.app")
        cache = root / "Users/tester/Library/Caches/com.example.app/cache.bin"
        cache.parent.mkdir(parents=True, exist_ok=True)
        cache.write_text("cache", encoding="utf-8")
        result = run_cli(
            "--root",
            str(root),
            "--home",
            str(home),
            "--json",
            "software",
            "inspect",
            "--app",
            "Example",
        )
        report = json.loads(result.stdout)

        assert report["schema"] == "cleanmac.software-inspect.v1"
        assert report["found"] is True
        assert {"app-bundle", "cache"}.issubset({candidate["kind"] for candidate in report["candidates"]})
        assert validate_contract_payload("cleanmac.software-inspect.v1", report)["valid"] is True


def test_software_orphans_reports_read_only_leftovers_for_missing_apps() -> None:
    tmp, root, home = make_sandbox()
    with tmp:
        orphan_paths = [
            root / "Users/tester/Library/Caches/com.example.oldapp",
            root / "Users/tester/Library/Preferences/com.example.oldapp.plist",
            root / "Users/tester/Library/Saved Application State/com.example.oldapp.savedState",
            root / "Users/tester/Library/Containers/com.example.oldapp",
            root / "Users/tester/Library/Group Containers/group.com.example.oldapp",
            root / "Library/LaunchDaemons/com.example.oldapp.plist",
            root / "Library/PrivilegedHelperTools/com.example.oldapp",
        ]
        for path in orphan_paths:
            path.parent.mkdir(parents=True, exist_ok=True)
            if path.suffix == ".plist" or "PrivilegedHelperTools" in path.parts:
                path.write_text("orphan", encoding="utf-8")
            else:
                path.mkdir(parents=True, exist_ok=True)
                path.joinpath("data").write_text("orphan", encoding="utf-8")

        _write_app(root, "Example", "com.example.app")
        installed_cache = root / "Users/tester/Library/Caches/com.example.app"
        installed_cache.mkdir(parents=True, exist_ok=True)
        installed_cache.joinpath("cache.bin").write_text("installed", encoding="utf-8")

        result = run_cli("--root", str(root), "--home", str(home), "--json", "software", "orphans")
        report = json.loads(result.stdout)
        by_path = {str(Path(candidate["path"]).resolve(strict=False)): candidate for candidate in report["candidates"]}
        old_cache = str((root / "Users/tester/Library/Caches/com.example.oldapp").resolve(strict=False))
        old_daemon = str((root / "Library/LaunchDaemons/com.example.oldapp.plist").resolve(strict=False))
        old_helper = str((root / "Library/PrivilegedHelperTools/com.example.oldapp").resolve(strict=False))
        installed_cache_path = str(installed_cache.resolve(strict=False))

        assert report["schema"] == "cleanmac.software-orphans.v1"
        assert report["destructive"] is False
        assert report["dry_run"] is True
        assert report["status"] == "read-only-orphan-scan"
        assert report["safe_to_auto_execute"] is False
        assert old_cache in by_path
        assert old_daemon in by_path
        assert old_helper in by_path
        assert installed_cache_path not in by_path
        assert by_path[old_cache]["default_selected"] is True
        assert by_path[old_daemon]["default_selected"] is False
        assert by_path[old_helper]["risk"] == "critical"
        for candidate in report["candidates"]:
            evidence = candidate["review_evidence"]
            assert candidate["id"].startswith("orphan:")
            assert candidate["matched_rule"].startswith("software-orphan.")
            assert candidate["installed_app_present"] is False
            assert candidate["delete_mode"] == "trash"
            assert evidence["schema"] == "cleanmac.candidate-review-evidence.v1"
            assert evidence["matched_rule"] == candidate["matched_rule"]
            assert evidence["risk"] == candidate["risk"]
            assert evidence["default_selected"] == candidate["default_selected"]
            assert evidence["protected"] == candidate["protected"]
            assert evidence["delete_mode"] == "trash"
            assert evidence["recommended_next_action"]
            assert validate_contract_payload("cleanmac.candidate-review-evidence.v1", evidence)["valid"] is True
        assert validate_contract_payload("cleanmac.software-orphans.v1", report)["valid"] is True


def test_software_uninstall_plan_blocks_official_uninstallers_with_structured_schema() -> None:
    tmp, root, home = make_sandbox()
    with tmp:
        _write_app(root, "Falcon", "com.crowdstrike.falcon.UserAgent")
        result = run_cli(
            "--root",
            str(root),
            "--home",
            str(home),
            "--json",
            "software",
            "uninstall-plan",
            "--app",
            "Falcon",
        )
        report = json.loads(result.stdout)

        assert report["schema"] == "cleanmac.software-uninstall-plan.v1"
        assert "official-uninstaller-required" in report["blocked_reasons"]
        assert report["uninstall_plan"]["official_uninstaller_required"] is True
        assert validate_contract_payload("cleanmac.software-uninstall-plan.v1", report)["valid"] is True


def test_software_uninstall_plan_finds_extended_leftovers_but_preserves_high_risk_defaults() -> None:
    tmp, root, home = make_sandbox()
    with tmp:
        _write_app(root, "Example", "com.example.app")
        paths = [
            root / "Users/tester/Library/Saved Application State/com.example.app.savedState",
            root / "Users/tester/Library/HTTPStorages/com.example.app",
            root / "Users/tester/Library/WebKit/com.example.app",
            root / "Users/tester/Library/Group Containers/group.com.example.app",
            root / "Library/LaunchDaemons/com.example.app.plist",
            root / "Library/PrivilegedHelperTools/com.example.app",
            root / "Library/Application Support/Example",
        ]
        for path in paths:
            if path.suffix == ".plist" or "PrivilegedHelperTools" in path.parts:
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text("x", encoding="utf-8")
            else:
                path.mkdir(parents=True, exist_ok=True)
                path.joinpath("data").write_text("x", encoding="utf-8")

        result = run_cli(
            "--root",
            str(root),
            "--home",
            str(home),
            "--json",
            "software",
            "uninstall-plan",
            "--app",
            "Example",
        )
        report = json.loads(result.stdout)
        uninstall_plan = report["uninstall_plan"]
        by_kind = {candidate["kind"]: candidate for candidate in uninstall_plan["candidates"]}

        assert {
            "saved-state",
            "http-storage",
            "webkit-data",
            "group-container",
            "launch-daemon",
            "privileged-helper",
            "system-application-support",
        }.issubset(set(by_kind))
        assert set(uninstall_plan["candidate_explainability_fields"]) == {
            "reason",
            "risk_reason",
            "risk_explanation",
            "recovery",
            "matched_rule",
            "app_owner",
            "confidence",
            "leftover_type",
            "contains_user_data",
            "why_not_default",
        }
        for candidate in uninstall_plan["candidates"]:
            assert candidate["reason"]
            assert candidate["risk_reason"]
            assert candidate["risk_explanation"]
            assert candidate["recovery"]
            assert candidate["leftover_type"]
            assert candidate["matched_rule"].startswith("software-uninstall.")
            assert candidate["app_owner"] == "example"
            assert candidate["finder_url"].startswith("file://")
            assert candidate["open_command"][0] == "open"
            assert candidate["reveal_command"][:2] == ["open", "-R"]
            assert "open -R" in candidate["reveal_command_text"]
        assert by_kind["group-container"]["default_selected"] is False
        assert (
            by_kind["group-container"]["why_not_default"]
            == "critical-risk candidate requires explicit review selection"
        )
        assert by_kind["privileged-helper"]["default_selected"] is False
        assert by_kind["privileged-helper"]["risk"] == "critical"


def test_software_uninstall_plan_protects_system_bundle_with_explainable_default_skip() -> None:
    tmp, root, home = make_sandbox()
    with tmp:
        _write_app(root, "Safari", "com.apple.Safari")
        result = run_cli(
            "--root",
            str(root),
            "--home",
            str(home),
            "--json",
            "software",
            "uninstall-plan",
            "--app",
            "Safari",
        )
        report = json.loads(result.stdout)
        app_bundle = next(
            candidate for candidate in report["uninstall_plan"]["candidates"] if candidate["kind"] == "app-bundle"
        )

        assert report["valid"] is False
        assert "protected-from-uninstall" in report["blocked_reasons"]
        assert report["uninstall_plan"]["safe_to_auto_execute"] is False
        assert app_bundle["protected"] is True
        assert app_bundle["default_selected"] is False
        assert app_bundle["why_not_default"] == "plan blocked: protected-from-uninstall"
        assert app_bundle["app_owner"] == "apple"


def test_software_uninstall_execute_requires_review_selection_and_records_trash_evidence() -> None:
    tmp, root, home = make_sandbox()
    with tmp:
        _write_app(root, "Example", "com.example.app")
        app_support = root / "Users/tester/Library/Application Support/Example"
        app_support.mkdir(parents=True)
        app_support.joinpath("state.db").write_text("preserve until explicit selection", encoding="utf-8")
        cache_path = root / "Users/tester/Library/Caches/com.example.app"
        cache_path.mkdir(parents=True)
        cache_path.joinpath("cache.bin").write_text("cache", encoding="utf-8")
        plan_file = root / "software-plan.json"
        selection_file = root / "software-selection.json"
        operation_log = root / "logs" / "software-uninstall.jsonl"

        plan = json.loads(
            run_cli(
                "--root",
                str(root),
                "--home",
                str(home),
                "--json",
                "software",
                "uninstall-plan",
                "--app",
                "Example",
            ).stdout
        )
        plan_file.write_text(json.dumps(plan), encoding="utf-8")
        review_report = json.loads(
            run_cli("--json", "review", "--input-file", str(plan_file), "--selection-file", str(selection_file)).stdout
        )
        selected_ids = [item["id"] for item in review_report["items"] if item["kind"] in {"app-bundle", "cache"}]
        selection = dict(review_report["selection"])
        selection["selected_item_ids"] = selected_ids
        selection["excluded_item_ids"] = [
            item["id"] for item in review_report["items"] if item["id"] not in selected_ids
        ]
        selection_file.write_text(json.dumps(selection), encoding="utf-8")

        missing_selection = run_cli(
            "--root",
            str(root),
            "--home",
            str(home),
            "--json",
            "software",
            "execute",
            "--plan-file",
            str(plan_file),
            check=False,
        )
        assert missing_selection.returncode != 0
        assert json.loads(missing_selection.stderr)["error"]["code"] == "SELECTION_VALIDATION_FAILED"

        dry_run_report = json.loads(
            run_cli(
                "--root",
                str(root),
                "--home",
                str(home),
                "--json",
                "software",
                "execute",
                "--plan-file",
                str(plan_file),
                "--review-selection-file",
                str(selection_file),
                "--operation-log",
                str(operation_log),
            ).stdout
        )
        planned_result = next(item for item in dry_run_report["results"] if item["status"] == "planned")

        assert dry_run_report["schema"] == "cleanmac.software-uninstall-result.v1"
        assert dry_run_report["dry_run"] is True
        assert dry_run_report["planned_count"] == 2
        assert dry_run_report["skipped_count"] >= 1
        assert len(dry_run_report["review_selection"]["selected_review_evidence"]) == 2
        assert planned_result["finder_url"].startswith("file://")
        assert planned_result["reveal_command"][:2] == ["open", "-R"]
        assert planned_result["review_evidence"]["schema"] == "cleanmac.candidate-review-evidence.v1"
        assert (root / "Applications/Example.app").exists()
        assert cache_path.exists()
        assert app_support.exists()
        assert validate_contract_payload("cleanmac.software-uninstall-result.v1", dry_run_report)["valid"] is True

        execute_report = json.loads(
            run_cli(
                "--root",
                str(root),
                "--home",
                str(home),
                "--json",
                "software",
                "execute",
                "--plan-file",
                str(plan_file),
                "--review-selection-file",
                str(selection_file),
                "--execute",
                "--yes",
                "--delete-mode",
                "trash",
                "--operation-log",
                str(operation_log),
            ).stdout
        )
        records = [json.loads(line) for line in operation_log.read_text(encoding="utf-8").splitlines()]

        assert execute_report["dry_run"] is False
        assert execute_report["deleted_count"] == 2
        assert execute_report["skipped_count"] >= 1
        assert not (root / "Applications/Example.app").exists()
        assert not cache_path.exists()
        assert app_support.exists()
        assert all(item["delete_mode"] == "trash" for item in execute_report["results"])
        assert {record["ai"]["review_selection"]["selected_count"] for record in records} == {2}
        assert {len(record["ai"]["review_selection"]["selected_review_evidence"]) for record in records} == {2}
        assert all(
            record["ai"]["candidate_review_evidence"]["schema"] == "cleanmac.candidate-review-evidence.v1"
            for record in records
        )
        assert "not-in-review-selection" in {record.get("reason") for record in records}
        assert any(record.get("trash_path") for record in records if record["status"] == "deleted")
        assert validate_contract_payload("cleanmac.software-uninstall-result.v1", execute_report)["valid"] is True
