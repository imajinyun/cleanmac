from __future__ import annotations

import json
from pathlib import Path

from cleancli.ai_versioning import validate_contract_payload
from cleancli.privacy import execute_privacy_cleanup
from tests.helpers import make_sandbox, run_cli
from tests.test_review_selection import run_cli_unchecked, write_privacy_cache_fixtures


def write_privacy_sensitive_fixtures(root: Path) -> None:
    paths = [
        root / "Users/tester/Library/Caches/com.apple.Safari/cache.db",
        root / "Users/tester/Library/Containers/com.apple.Safari/Data/Library/Caches/com.apple.Safari/cache.db",
        root / "Users/tester/Library/Safari/History.db",
        root / "Users/tester/Library/Safari/Downloads.plist",
        root / "Users/tester/Library/Cookies/Cookies.binarycookies",
        root / "Users/tester/Library/Containers/com.apple.Safari/Data/Library/Cookies/Cookies.binarycookies",
        root / "Users/tester/Library/Safari/LocalStorage/site.localstorage",
        root / "Users/tester/Library/Safari/Databases/database.sqlite",
        root / "Users/tester/Library/WebKit/com.apple.Safari/WebsiteData/LocalStorage/site.localstorage",
        root / "Users/tester/Library/WebKit/com.apple.Safari/WebsiteData/IndexedDB/site.example/000003.log",
        root / "Users/tester/Library/Application Support/Google/Chrome/Default/Cookies",
        root / "Users/tester/Library/Application Support/Google/Chrome/Default/History",
        root / "Users/tester/Library/Application Support/Google/Chrome/Default/Login Data",
        root / "Users/tester/Library/Application Support/Google/Chrome/Default/Bookmarks",
        root / "Users/tester/Library/Application Support/Google/Chrome/Default/Local Storage/leveldb/state.ldb",
        root / "Users/tester/Library/Application Support/Google/Chrome/Default/IndexedDB/site.leveldb/000003.log",
        root / "Users/tester/Library/Application Support/Microsoft Edge/Default/Login Data",
        root / "Users/tester/Library/Application Support/Firefox/Profiles/dev.default-release/logins.json",
        root / "Users/tester/Library/Application Support/Firefox/Profiles/dev.default-release/key4.db",
        root / "Users/tester/Library/Application Support/Slack/Local Storage/leveldb/state.ldb",
        root / "Users/tester/Library/Application Support/discord/Local Storage/leveldb/state.ldb",
        root / "Users/tester/Library/Application Support/Notion/IndexedDB/state.leveldb/000003.log",
    ]
    for path in paths:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("privacy-sensitive", encoding="utf-8")


def write_privacy_plan_and_selection(root: Path, home: Path) -> tuple[Path, Path, dict[str, object], str, list[str]]:
    plan_file = root / "privacy-plan.json"
    selection_file = root / "privacy-selection.json"
    plan = json.loads(
        run_cli("--root", str(root), "--home", str(home), "--json", "privacy", "plan", "--scope", "cache").stdout
    )
    plan_file.write_text(json.dumps(plan), encoding="utf-8")
    review_report = json.loads(
        run_cli("--json", "review", "--input-file", str(plan_file), "--selection-file", str(selection_file)).stdout
    )
    selected_item = next(item for item in review_report["items"] if item.get("application") == "Chrome")
    selection = dict(review_report["selection"])
    selection["selected_item_ids"] = [selected_item["id"]]
    selection["excluded_item_ids"] = [
        item["id"] for item in review_report["items"] if item["id"] != selected_item["id"]
    ]
    selection_file.write_text(json.dumps(selection), encoding="utf-8")
    skipped_paths = [item["path"] for item in review_report["items"] if item["id"] != selected_item["id"]]
    return plan_file, selection_file, selection, str(selected_item["path"]), skipped_paths


def test_privacy_inspect_and_plan_preserve_sensitive_scopes_by_default() -> None:
    tmp, root, home = make_sandbox()
    with tmp:
        write_privacy_cache_fixtures(root)
        write_privacy_sensitive_fixtures(root)

        cache_report = json.loads(
            run_cli("--root", str(root), "--home", str(home), "--json", "privacy", "inspect", "--scope", "cache").stdout
        )
        assert cache_report["schema"] == "cleanmac.privacy-inspect.v1"
        assert cache_report["candidate_count"] >= 8
        assert any(item["application"] == "Chrome" for item in cache_report["candidates"])
        assert all(item["scope"] == "cache" for item in cache_report["candidates"])
        assert any(item["default_selected"] for item in cache_report["candidates"])
        assert cache_report["scope_counts"] == {"cache": cache_report["candidate_count"]}
        assert cache_report["application_counts"]["Chrome"] >= 1
        assert cache_report["application_counts"]["Safari"] >= 1
        assert cache_report["privacy_risk_counts"] == {"low": cache_report["candidate_count"]}
        assert cache_report["recommended_next_action"] == "review_privacy_plan"
        assert validate_contract_payload("cleanmac.privacy-inspect.v1", cache_report)["valid"] is True

        all_report = json.loads(
            run_cli("--root", str(root), "--home", str(home), "--json", "privacy", "inspect", "--scope", "all").stdout
        )
        safari_candidates = [item for item in all_report["candidates"] if item["application"] == "Safari"]
        assert len(safari_candidates) >= 7
        assert any(item["kind"] == "cache" and item["default_selected"] for item in safari_candidates)
        assert any(item["scope"] == "cookies" for item in safari_candidates)
        assert any(item["scope"] == "history" for item in safari_candidates)
        assert any(item["scope"] == "local-storage" for item in safari_candidates)
        assert all(
            not item["default_selected"]
            for item in safari_candidates
            if item["scope"] in {"cookies", "history", "local-storage"}
        )

        credentials_report = json.loads(
            run_cli(
                "--root", str(root), "--home", str(home), "--json", "privacy", "plan", "--scope", "credentials"
            ).stdout
        )
        privacy_plan = credentials_report["privacy_plan"]
        assert credentials_report["schema"] == "cleanmac.privacy-plan.v1"
        assert privacy_plan["safe_to_auto_execute"] is False
        assert privacy_plan["candidate_count"] >= 3
        assert privacy_plan["default_selected_count"] == 0
        assert privacy_plan["scope_counts"] == {"credentials": privacy_plan["candidate_count"]}
        assert privacy_plan["privacy_risk_counts"]["critical"] >= 1
        assert all(not item["default_selected"] for item in privacy_plan["candidates"])
        assert validate_contract_payload("cleanmac.privacy-plan.v1", credentials_report)["valid"] is True


def test_privacy_execute_requires_review_selection_and_records_audit() -> None:
    tmp, root, home = make_sandbox()
    with tmp:
        write_privacy_cache_fixtures(root)
        operation_log = root / "logs" / "privacy-execute.jsonl"
        plan_file, selection_file, selection, selected_path, skipped_paths = write_privacy_plan_and_selection(
            root, home
        )

        missing_selection = run_cli_unchecked(
            "--root", str(root), "--home", str(home), "--json", "privacy", "execute", "--plan-file", str(plan_file)
        )
        assert missing_selection.returncode != 0
        assert json.loads(missing_selection.stderr)["error"]["code"] == "SELECTION_VALIDATION_FAILED"

        stale_selection = dict(selection)
        stale_selection["source_fingerprint"] = "0" * 64
        selection_file.write_text(json.dumps(stale_selection), encoding="utf-8")
        stale_result = run_cli_unchecked(
            "--root",
            str(root),
            "--home",
            str(home),
            "--json",
            "privacy",
            "execute",
            "--plan-file",
            str(plan_file),
            "--review-selection-file",
            str(selection_file),
        )
        assert stale_result.returncode != 0
        assert json.loads(stale_result.stderr)["error"]["code"] == "SELECTION_VALIDATION_FAILED"

        selection_file.write_text(json.dumps(selection), encoding="utf-8")
        dry_run_report = json.loads(
            run_cli(
                "--root",
                str(root),
                "--home",
                str(home),
                "--json",
                "privacy",
                "execute",
                "--plan-file",
                str(plan_file),
                "--review-selection-file",
                str(selection_file),
                "--operation-log",
                str(operation_log),
            ).stdout
        )

        assert dry_run_report["schema"] == "cleanmac.privacy-execute-result.v1"
        assert dry_run_report["dry_run"] is True
        assert dry_run_report["planned_count"] == 1
        assert dry_run_report["skipped_count"] >= 1
        assert len(dry_run_report["review_selection"]["selected_review_evidence"]) == 1
        assert validate_contract_payload("cleanmac.privacy-execute-result.v1", dry_run_report)["valid"] is True
        assert dry_run_report["delete_mode"] == "trash"
        assert {item["delete_mode"] for item in dry_run_report["results"]} == {"trash"}
        planned_privacy = next(item for item in dry_run_report["results"] if item["status"] == "planned")
        assert planned_privacy["review_evidence"]["schema"] == "cleanmac.candidate-review-evidence.v1"
        assert Path(selected_path).exists()
        assert all(Path(path).exists() for path in skipped_paths[:2])
        dry_run_records = [json.loads(line) for line in operation_log.read_text(encoding="utf-8").splitlines()]
        assert {record["ai"]["review_selection"]["selected_count"] for record in dry_run_records} == {1}
        assert {len(record["ai"]["review_selection"]["selected_review_evidence"]) for record in dry_run_records} == {1}
        assert all(
            record["ai"]["candidate_review_evidence"]["schema"] == "cleanmac.candidate-review-evidence.v1"
            for record in dry_run_records
        )
        assert "not-in-review-selection" in {record.get("reason") for record in dry_run_records}
        assert {record["delete_mode"] for record in dry_run_records} == {"trash"}

        execute_report = json.loads(
            run_cli(
                "--root",
                str(root),
                "--home",
                str(home),
                "--json",
                "privacy",
                "execute",
                "--plan-file",
                str(plan_file),
                "--review-selection-file",
                str(selection_file),
                "--execute",
                "--yes",
                "--operation-log",
                str(operation_log),
            ).stdout
        )
        all_records = [json.loads(line) for line in operation_log.read_text(encoding="utf-8").splitlines()]

        assert execute_report["dry_run"] is False
        assert execute_report["delete_mode"] == "trash"
        assert execute_report["deleted_count"] == 1
        assert execute_report["skipped_count"] >= 1
        deleted_result = next(item for item in execute_report["results"] if item["status"] == "deleted")
        assert deleted_result["delete_mode"] == "trash"
        assert deleted_result["review_evidence"]["schema"] == "cleanmac.candidate-review-evidence.v1"
        assert deleted_result["trash_path"]
        assert Path(deleted_result["trash_path"]).exists()
        assert not Path(selected_path).exists()
        assert all(Path(path).exists() for path in skipped_paths[:2])
        assert "not-in-review-selection" in {record.get("reason") for record in all_records}
        assert {record["ai"]["review_selection"]["selected_count"] for record in all_records} == {1}
        assert {record["delete_mode"] for record in all_records} == {"trash"}
        deleted_record = next(record for record in all_records if record["status"] == "deleted")
        assert deleted_record["trash_path"] == deleted_result["trash_path"]
        assert deleted_record["ai"]["candidate_review_evidence"] == deleted_result["review_evidence"]
        selected_evidence = deleted_record["ai"]["review_selection"]["selected_review_evidence"][0]
        assert selected_evidence["id"] == deleted_result["id"]
        assert selected_evidence["path"] == deleted_result["path"]
        assert selected_evidence["review_evidence"] == deleted_result["review_evidence"]

        permanent_result = run_cli_unchecked(
            "--root",
            str(root),
            "--home",
            str(home),
            "--json",
            "privacy",
            "execute",
            "--plan-file",
            str(plan_file),
            "--review-selection-file",
            str(selection_file),
            "--delete-mode",
            "permanent",
            "--execute",
            "--yes",
        )
        assert permanent_result.returncode != 0
        permanent_error = json.loads(permanent_result.stderr)
        assert permanent_error["error"]["code"] == "CLI_ARGUMENT_ERROR"
        assert "invalid choice: 'permanent'" in permanent_error["error"]["message"]


def test_privacy_execute_blocks_outside_symlink_and_credential_candidates() -> None:
    tmp, root, home = make_sandbox()
    with tmp:
        write_privacy_cache_fixtures(root)
        outside = root / "Users/tester/Documents/keep.txt"
        outside.parent.mkdir(parents=True, exist_ok=True)
        outside.write_text("must stay", encoding="utf-8")
        symlink = root / "Users/tester/Library/Caches/Google/Chrome/Profile 1/EvilLink"
        symlink.parent.mkdir(parents=True, exist_ok=True)
        symlink.symlink_to(outside)
        credential = root / "Users/tester/Library/Application Support/Google/Chrome/Default/Login Data"
        credential.parent.mkdir(parents=True, exist_ok=True)
        credential.write_text("secret", encoding="utf-8")

        plan = json.loads(
            run_cli("--root", str(root), "--home", str(home), "--json", "privacy", "plan", "--scope", "all").stdout
        )
        plan["privacy_plan"]["candidates"].extend(
            [
                {
                    "id": "privacy:malicious:outside",
                    "path": str(outside),
                    "application": "Malicious",
                    "profile": "default",
                    "kind": "outside",
                    "scope": "cache",
                    "bytes": 9,
                    "privacy_risk": "low",
                    "data_loss_risk": "low",
                    "default_selected": True,
                    "delete_mode": "trash",
                },
                {
                    "id": "privacy:malicious:symlink",
                    "path": str(symlink),
                    "application": "Malicious",
                    "profile": "default",
                    "kind": "symlink",
                    "scope": "cache",
                    "bytes": 9,
                    "privacy_risk": "low",
                    "data_loss_risk": "low",
                    "default_selected": True,
                    "delete_mode": "trash",
                },
            ]
        )
        plan_file = root / "privacy-plan.json"
        selection_file = root / "privacy-selection.json"
        plan_file.write_text(json.dumps(plan), encoding="utf-8")
        review_report = json.loads(
            run_cli("--json", "review", "--input-file", str(plan_file), "--selection-file", str(selection_file)).stdout
        )
        target_paths = {str(outside), str(symlink), str(credential.resolve(strict=False))}
        selected_ids = [item["id"] for item in review_report["items"] if item["path"] in target_paths]
        selection = dict(review_report["selection"])
        selection["selected_item_ids"] = selected_ids
        selection["excluded_item_ids"] = [
            item["id"] for item in review_report["items"] if item["id"] not in selected_ids
        ]
        selection_file.write_text(json.dumps(selection), encoding="utf-8")

        result = json.loads(
            run_cli(
                "--root",
                str(root),
                "--home",
                str(home),
                "--json",
                "privacy",
                "execute",
                "--plan-file",
                str(plan_file),
                "--review-selection-file",
                str(selection_file),
                "--execute",
                "--yes",
            ).stdout
        )

        reasons = {item["reason"] for item in result["results"] if item["status"] == "blocked"}
        assert result["deleted_count"] == 0
        assert result["blocked_count"] >= 3
        assert "outside-privacy-locations" in reasons
        assert "symlink-privacy-candidate" in reasons
        assert "sensitive-scope-blocked" in reasons
        assert outside.exists()
        assert credential.exists()
        assert symlink.is_symlink()


def test_privacy_execute_requires_selected_item_id_and_path_to_match_same_candidate() -> None:
    tmp, root, home = make_sandbox()
    with tmp:
        write_privacy_cache_fixtures(root)
        plan = json.loads(
            run_cli("--root", str(root), "--home", str(home), "--json", "privacy", "plan", "--scope", "cache").stdout
        )
        first = plan["privacy_plan"]["candidates"][0]
        second = plan["privacy_plan"]["candidates"][1]

        report = execute_privacy_cleanup(
            plan,
            review_selection={
                "schema": "cleanmac.review-selection-constraint.v1",
                "selected_item_ids": [first["id"]],
                "selected_paths": [second["path"]],
                "selected_count": 1,
                "validation": {"valid": True},
            },
            execute=True,
            yes=True,
            root=Path(str(plan["root"])),
            home=Path(str(plan["home"])),
            delete_path_func=lambda path: None,
        )

        assert report["deleted_count"] == 0
        assert "selection-id-path-mismatch" in {item["reason"] for item in report["results"]}
