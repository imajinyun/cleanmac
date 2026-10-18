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
        by_kind = {candidate["kind"]: candidate for candidate in report["candidates"]}
        assert {"app-bundle", "cache"}.issubset(set(by_kind))
        cache_evidence = by_kind["cache"]["discovery_evidence"]
        assert cache_evidence["schema"] == "cleanmac.software-discovery-evidence.v1"
        assert cache_evidence["app_identity"]["bundle_id"] == "com.example.app"
        assert cache_evidence["match_source"] == "bundle-id"
        assert cache_evidence["path_role"] == "cache"
        assert cache_evidence["deletion_eligibility"]["delete_mode"] == "trash"
        assert cache_evidence["deletion_eligibility"]["safe_to_auto_execute"] is False
        assert cache_evidence["deletion_eligibility"]["requires_review_selection"] is True
        assert cache_evidence["deletion_eligibility"]["protected"] is False
        assert validate_contract_payload("cleanmac.software-discovery-evidence.v1", cache_evidence)["valid"] is True
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
        assert report["scan_duration_ms"] >= 0
        assert report["shown_candidate_count"] == len(report["candidates"])
        assert report["truncated"] is False
        assert report["summary"]["schema"] == "cleanmac.software-orphan-summary.v1"
        assert report["summary"]["candidate_count"] == report["candidate_count"]
        assert report["summary"]["candidate_count_by_confidence"]["medium"] == report["candidate_count"]
        assert report["summary"]["candidate_count_by_default_policy"]["default_selected"] == report["default_selected_count"]
        assert report["summary"]["next_review_command"][:4] == ["cleanmac", "--json", "review", "--input-file"]
        assert old_cache in by_path
        assert old_daemon in by_path
        assert old_helper in by_path
        assert installed_cache_path not in by_path
        assert by_path[old_cache]["default_selected"] is False
        assert by_path[old_cache]["suppression_reason"] == "possible app installed outside indexed application directories"
        assert by_path[old_daemon]["default_selected"] is False
        assert by_path[old_daemon]["known_helper_only_bundle"] is True
        assert by_path[old_helper]["risk"] == "critical"
        for candidate in report["candidates"]:
            evidence = candidate["review_evidence"]
            discovery = candidate["discovery_evidence"]
            assert candidate["id"].startswith("orphan:")
            assert candidate["matched_rule"].startswith("software-orphan.")
            assert candidate["installed_app_present"] is False
            assert candidate["delete_mode"] == "trash"
            assert discovery["schema"] == "cleanmac.software-discovery-evidence.v1"
            assert discovery["installed_app_present"] is False
            assert discovery["candidate_id"] == candidate["id"]
            assert discovery["candidate_path"] == candidate["path"]
            assert discovery["deletion_eligibility"]["safe_to_auto_execute"] is False
            assert discovery["deletion_eligibility"]["requires_review_selection"] is True
            assert discovery["confidence_reason"] == candidate["confidence_reason"]
            assert discovery["suppression_reason"] == candidate["suppression_reason"]
            assert validate_contract_payload("cleanmac.software-discovery-evidence.v1", discovery)["valid"] is True
            assert evidence["schema"] == "cleanmac.candidate-review-evidence.v1"
            assert evidence["matched_rule"] == candidate["matched_rule"]
            assert evidence["risk"] == candidate["risk"]
            assert evidence["default_selected"] == candidate["default_selected"]
            assert evidence["confidence_reason"] == candidate["confidence_reason"]
            assert evidence["suppression_reason"] == candidate["suppression_reason"]
            assert evidence["protected"] == candidate["protected"]
            assert evidence["delete_mode"] == "trash"
            assert evidence["recommended_next_action"]
            assert validate_contract_payload("cleanmac.candidate-review-evidence.v1", evidence)["valid"] is True
        assert validate_contract_payload("cleanmac.software-orphans.v1", report)["valid"] is True


def test_software_orphans_supports_summary_and_scan_budgets() -> None:
    tmp, root, home = make_sandbox()
    with tmp:
        for index in range(5):
            path = root / f"Users/tester/Library/Caches/com.example.old{index}"
            path.mkdir(parents=True, exist_ok=True)
            path.joinpath("cache.bin").write_text("orphan", encoding="utf-8")

        limited = json.loads(
            run_cli(
                "--root",
                str(root),
                "--home",
                str(home),
                "--json",
                "software",
                "orphans",
                "--limit",
                "2",
            ).stdout
        )
        summary_only = json.loads(
            run_cli(
                "--root",
                str(root),
                "--home",
                str(home),
                "--json",
                "software",
                "orphans",
                "--summary-only",
            ).stdout
        )
        scan_limited = json.loads(
            run_cli(
                "--root",
                str(root),
                "--home",
                str(home),
                "--json",
                "software",
                "orphans",
                "--max-scan-entries",
                "2",
            ).stdout
        )

        assert limited["candidate_count"] >= 5
        assert limited["shown_candidate_count"] == 2
        assert len(limited["candidates"]) == 2
        assert limited["truncated"] is True
        assert limited["summary"]["truncated"] is True
        assert limited["summary"]["shown_candidate_count"] == 2

        assert summary_only["candidate_count"] == limited["candidate_count"]
        assert summary_only["shown_candidate_count"] == 0
        assert summary_only["candidates"] == []
        assert summary_only["summary_only"] is True
        assert summary_only["truncated"] is True

        assert scan_limited["scan_truncated"] is True
        assert scan_limited["scanned_entry_count"] == 2
        assert scan_limited["candidate_count"] <= 2
        assert scan_limited["summary"]["scan_truncated"] is True
        assert validate_contract_payload("cleanmac.software-orphans.v1", limited)["valid"] is True
        assert validate_contract_payload("cleanmac.software-orphans.v1", summary_only)["valid"] is True
        assert validate_contract_payload("cleanmac.software-orphans.v1", scan_limited)["valid"] is True


def test_software_orphans_default_detail_limit_covers_more_than_100_candidates() -> None:
    tmp, root, home = make_sandbox()
    with tmp:
        for index in range(105):
            path = root / f"Users/tester/Library/Caches/com.example.old{index:03d}"
            path.mkdir(parents=True, exist_ok=True)
            path.joinpath("cache.bin").write_text("orphan", encoding="utf-8")

        report = json.loads(
            run_cli("--root", str(root), "--home", str(home), "--json", "software", "orphans").stdout
        )

        assert report["limit"] == 1000
        assert report["candidate_count"] >= 105
        assert report["shown_candidate_count"] == report["candidate_count"]
        assert report["truncated"] is False


def test_software_orphans_discovers_application_scripts_with_strict_attribution() -> None:
    tmp, root, home = make_sandbox()
    with tmp:
        scripts_root = root / "Users/tester/Library/Application Scripts"
        accepted = {
            "cn.wps.wpslaunchhelper": "cn.wps.wpslaunchhelper",
            "Y5PE65HELJ.com.steipete.codexbar": "com.steipete.codexbar",
            "79RR9LPM2N.group.com.macitbetter.betterzip": "com.macitbetter.betterzip",
            "group.com.qiyi": "com.qiyi",
        }
        for name in accepted:
            path = scripts_root / name
            path.mkdir(parents=True, exist_ok=True)
            path.joinpath("script.scpt").write_text("orphan", encoding="utf-8")

        rejected = [
            "057D7238-B184-4AC3-A30D-F45A77940605",
            "UBF8T346G9.Office",
            "group.com.apple.mail",
            "243LU875E5.groups.com.apple.podcasts",
            ".SiriTodayViewExtension",
        ]
        for name in rejected:
            path = scripts_root / name
            path.mkdir(parents=True, exist_ok=True)
            path.joinpath("script.scpt").write_text("keep", encoding="utf-8")

        symlink_target = root / "Users/tester/scratch/cn.trae.app"
        symlink_target.mkdir(parents=True, exist_ok=True)
        symlink_target.joinpath("real.scpt").write_text("real", encoding="utf-8")
        (scripts_root / "cn.trae.app.linked").symlink_to(symlink_target, target_is_directory=True)

        report = json.loads(
            run_cli("--root", str(root), "--home", str(home), "--json", "software", "orphans").stdout
        )
        scripts = {candidate["bundle_id"]: candidate for candidate in report["candidates"] if candidate["kind"] == "application-scripts"}

        assert set(scripts) == set(accepted.values())
        for raw_name, bundle_id in accepted.items():
            candidate = scripts[bundle_id]
            assert candidate["path"].endswith(f"Application Scripts/{raw_name}")
            assert candidate["leftover_type"] == "application_scripts"
            assert candidate["risk"] == "medium"
            assert candidate["confidence"] == "medium"
            assert candidate["default_selected"] is False
            assert candidate["protected"] is False
            assert candidate["active_process_hint"] is False
            assert candidate["possible_installed_outside_indexed_app_dirs"] is True
            assert candidate["suppression_reason"] == (
                "possible app installed outside indexed application directories"
            )
            assert candidate["delete_mode"] == "trash"
            assert candidate["recovery"]
        rejected_paths = {str(candidate["path"]) for candidate in report["candidates"]}
        for name in rejected:
            assert not any(path.endswith(f"Application Scripts/{name}") for path in rejected_paths)
        assert not any(path.endswith("cn.trae.app.linked") for path in rejected_paths)
        assert any("Application Scripts" in scan_root for scan_root in report["scan_roots"])
        assert report["leftover_type_counts"].get("application_scripts") == len(accepted)
        assert validate_contract_payload("cleanmac.software-orphans.v1", report)["valid"] is True


def test_software_orphans_application_scripts_respect_installed_app_bundle_ids() -> None:
    tmp, root, home = make_sandbox()
    with tmp:
        _write_app(root, "VendorApp", "com.vendor.app")
        scripts_root = root / "Users/tester/Library/Application Scripts"
        # Extension id below the installed app id and parent id above it both belong to the app.
        for name in ("com.vendor.app.widget", "com.vendor"):
            path = scripts_root / name
            path.mkdir(parents=True, exist_ok=True)
            path.joinpath("script.scpt").write_text("installed", encoding="utf-8")
        orphan = scripts_root / "com.other.gone"
        orphan.mkdir(parents=True, exist_ok=True)
        orphan.joinpath("script.scpt").write_text("orphan", encoding="utf-8")

        report = json.loads(
            run_cli("--root", str(root), "--home", str(home), "--json", "software", "orphans").stdout
        )
        script_ids = {
            candidate["bundle_id"]
            for candidate in report["candidates"]
            if candidate["kind"] == "application-scripts"
        }

        assert script_ids == {"com.other.gone"}


def test_software_orphans_broaden_bundle_id_predicate_conservatively() -> None:
    tmp, root, home = make_sandbox()
    with tmp:
        accepted_paths = [
            root / "Users/tester/Library/Containers/cn.wps.wpslaunchhelper",
            root / "Users/tester/Library/Preferences/dev.warp.Warp-Stable.plist",
            root / "Users/tester/Library/Preferences/ai.z.zcode.plist",
            root / "Users/tester/Library/HTTPStorages/pc.your.configure.binarycookies",
        ]
        for path in accepted_paths:
            path.parent.mkdir(parents=True, exist_ok=True)
            if path.suffix == ".plist" or path.name.endswith(".binarycookies"):
                path.write_text("orphan", encoding="utf-8")
            else:
                path.mkdir(parents=True, exist_ok=True)
                path.joinpath("data").write_text("orphan", encoding="utf-8")

        rejected_paths = [
            root / "Users/tester/Library/LaunchAgents/homebrew.mxcl.redis.plist",
            root / "Users/tester/Library/Preferences/.GlobalPreferences.plist",
            root / "Users/tester/Library/Logs/warp.log",
            root / "Users/tester/Library/Logs/PhotosSearch.aapbz",
            root / "Users/tester/Library/Logs/warp.log.old.0",
        ]
        for path in rejected_paths:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("not a bundle id", encoding="utf-8")

        report = json.loads(
            run_cli("--root", str(root), "--home", str(home), "--json", "software", "orphans").stdout
        )
        by_path = {candidate["path"]: candidate for candidate in report["candidates"]}

        assert str((root / "Users/tester/Library/Containers/cn.wps.wpslaunchhelper").resolve(strict=False)) in {
            str(Path(path).resolve(strict=False)) for path in by_path
        }
        cookies = next(
            candidate
            for candidate in report["candidates"]
            if candidate["path"].endswith("pc.your.configure.binarycookies")
        )
        assert cookies["bundle_id"] == "pc.your.configure"
        assert cookies["kind"] == "http-storage"
        resolved_rejected = {str(path.resolve(strict=False)) for path in rejected_paths}
        assert not resolved_rejected.intersection(
            str(Path(path).resolve(strict=False)) for path in by_path
        )


def test_software_orphans_strip_http_cookie_suffix_before_installed_match() -> None:
    tmp, root, home = make_sandbox()
    with tmp:
        _write_app(root, "Mole", "com.tw93.MoleApp")
        installed_cookies = root / "Users/tester/Library/HTTPStorages/com.tw93.MoleApp.binarycookies"
        installed_cookies.parent.mkdir(parents=True, exist_ok=True)
        installed_cookies.write_text("installed", encoding="utf-8")
        orphan_tmp = root / "Users/tester/Library/HTTPStorages/net.byteintl.mira.binarycookies_tmp_89968.dat"
        orphan_tmp.write_text("orphan", encoding="utf-8")

        report = json.loads(
            run_cli("--root", str(root), "--home", str(home), "--json", "software", "orphans").stdout
        )
        paths = {candidate["path"]: candidate.get("bundle_id") for candidate in report["candidates"]}

        assert not any(path.endswith("com.tw93.MoleApp.binarycookies") for path in paths)
        mira = next(
            candidate
            for candidate in report["candidates"]
            if candidate["path"].endswith("binarycookies_tmp_89968.dat")
        )
        assert mira["bundle_id"] == "net.byteintl.mira"


def test_software_orphans_reject_ambiguous_team_prefixed_group_containers() -> None:
    tmp, root, home = make_sandbox()
    with tmp:
        group_root = root / "Users/tester/Library/Group Containers"
        kept = {
            "2BBY89MBSN.dev.vendor.gone": "dev.vendor.gone",
            "ABC1234567.group.com.other.gone": "com.other.gone",
        }
        for name in kept:
            path = group_root / name
            path.mkdir(parents=True, exist_ok=True)
            path.joinpath("data").write_text("orphan", encoding="utf-8")
        for name in ("UBF8T346G9.Office", "88L2Q4487U.WeWorkMac", ".SiriTodayViewExtension"):
            path = group_root / name
            path.mkdir(parents=True, exist_ok=True)
            path.joinpath("data").write_text("keep", encoding="utf-8")
        # Installed app extension hierarchy: installed id is the parent of the container id.
        _write_app(root, "Present", "com.vendor.app")
        installed_group = group_root / "TEAMID0000.com.vendor.app.shared"
        installed_group.mkdir(parents=True, exist_ok=True)
        installed_group.joinpath("data").write_text("installed", encoding="utf-8")

        report = json.loads(
            run_cli("--root", str(root), "--home", str(home), "--json", "software", "orphans").stdout
        )
        groups = {
            candidate["bundle_id"]: candidate
            for candidate in report["candidates"]
            if candidate["kind"] == "group-container"
        }

        assert set(kept.values()).issubset(set(groups))
        assert groups["dev.vendor.gone"]["risk"] == "critical"
        assert groups["dev.vendor.gone"]["default_selected"] is False
        absent_names = (
            "UBF8T346G9.Office",
            "88L2Q4487U.WeWorkMac",
            ".SiriTodayViewExtension",
            "TEAMID0000.com.vendor.app.shared",
        )
        assert all(
            not candidate["path"].rstrip("/").endswith(name)
            for name in absent_names
            for candidate in report["candidates"]
        )


def test_software_leftovers_is_alias_of_orphan_scan() -> None:
    tmp, root, home = make_sandbox()
    with tmp:
        scripts_dir = root / "Users/tester/Library/Application Scripts/com.example.gone"
        scripts_dir.mkdir(parents=True, exist_ok=True)
        scripts_dir.joinpath("script.scpt").write_text("orphan", encoding="utf-8")
        cache_dir = root / "Users/tester/Library/Caches/com.example.gone"
        cache_dir.mkdir(parents=True, exist_ok=True)
        cache_dir.joinpath("cache.bin").write_text("orphan", encoding="utf-8")

        args = ("--root", str(root), "--home", str(home), "--json", "software")
        leftovers = json.loads(run_cli(*args, "leftovers").stdout)
        orphans = json.loads(run_cli(*args, "orphans").stdout)

        assert leftovers["schema"] == "cleanmac.software-orphans.v1"
        assert leftovers["status"] == "read-only-orphan-scan"
        assert leftovers["destructive"] is False
        assert leftovers["dry_run"] is True
        assert leftovers["safe_to_auto_execute"] is False
        assert [candidate["path"] for candidate in leftovers["candidates"]] == [
            candidate["path"] for candidate in orphans["candidates"]
        ]
        assert leftovers["candidate_count"] == orphans["candidate_count"]
        assert validate_contract_payload("cleanmac.software-orphans.v1", leftovers)["valid"] is True


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
