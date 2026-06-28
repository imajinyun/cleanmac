from __future__ import annotations

import json
import os
import shlex
import time
from pathlib import Path

import pytest

import cleancli.core as cleancli
from cleancli.ai_eval import render_ai_eval_pack
from tests.helpers import make_sandbox, run_cli

PROJECT_ROOT = Path(__file__).resolve().parent.parent


def test_cli_version_reports_package_version() -> None:
    result = run_cli("--version")

    assert "cleanmac" in result.stdout.strip()
    assert cleancli.VERSION in result.stdout.strip()


def test_completion_bash_includes_commands_categories_and_eval_scenarios() -> None:
    result = run_cli("completion", "bash")
    completion = result.stdout
    scenarios = [scenario["id"] for scenario in render_ai_eval_pack()["scenarios"]]

    assert "cleanmac bash completion" in completion
    assert "list" in completion
    assert "ai-tools" in completion
    assert "ai-eval-pack" in completion
    assert "ai-eval-run" in completion
    assert "release_promotion_decision_surface_audit_blocker" in completion
    assert "trash" in completion
    assert "complete -F _cleanmac_completion cleanmac" in completion
    assert "smoke" in completion
    assert "all" in completion
    assert scenarios
    for scenario_id in scenarios:
        assert scenario_id in completion


@pytest.mark.parametrize(
    ("shell", "expected"),
    [
        ("zsh", ("cleanmac zsh completion", "#compdef cleanmac")),
        ("fish", ("cleanmac fish completion", "__fish_use_subcommand")),
    ],
)
def test_completion_shell_includes_expected_boilerplate(shell: str, expected: tuple[str, str]) -> None:
    result = run_cli("completion", shell)

    for token in expected:
        assert token in result.stdout


def test_completion_json_includes_schema() -> None:
    result = run_cli("--json", "completion", "bash")
    report = json.loads(result.stdout)

    assert report["schema"] == "cleanmac.completion-script.v1"
    assert report["shell"] == "bash"
    assert "_cleanmac_completion" in report["script_content"]


def test_list_shows_categories() -> None:
    result = run_cli("list")

    assert "trash" in result.stdout
    assert "imessage" in result.stdout
    assert "Spotlight" in result.stdout


def test_list_json_includes_category_metadata() -> None:
    result = run_cli("--json", "list")
    report = json.loads(result.stdout)
    by_key = {row["key"]: row for row in report["categories"]}

    assert report["schema"] == "cleanmac.category-list.v1"
    assert "categories" in report
    assert len(report["categories"]) == len(cleancli.CATEGORIES)
    assert "Deletes all files" in by_key["trash"]["description"]
    assert by_key["trash"]["default"] is True
    assert by_key["incompleteDownloads"]["default"] is True
    assert by_key["downloads"]["default"] is False
    assert by_key["mails"]["default_older_than_days"] == 30
    assert "Archives" in ",".join(by_key["xcode"]["paths"])
    assert by_key["deviceFirmware"]["default_older_than_days"] == 30
    assert "Rosetta" in by_key["appleSiliconCaches"]["title"]
    assert "Group Container" in by_key["groupContainerCaches"]["title"]
    assert "Android Studio" in by_key["androidStudio"]["title"]
    assert "JetBrains" in by_key["jetbrains"]["title"]
    assert "Docker" in by_key["docker"]["title"]
    assert by_key["gpuCaches"]["provider"] == "gpu-cache"
    assert by_key["imessage"]["full_disk_access"] is True


def test_capabilities_json_exposes_grouped_commands_and_ai_safety_boundaries() -> None:
    result = run_cli("--json", "capabilities")
    report = json.loads(result.stdout)

    assert report["schema"] == "cleanmac.capabilities.v1"
    assert report["category_count"] == len(cleancli.CATEGORIES)
    assert {
        "clean",
        "software",
        "startup",
        "privacy",
        "optimize",
        "status",
        "validate-plan",
        "ai-governance-advice",
        "ai-host-policy",
        "ai-eval-pack",
        "ai-eval-run",
    }.issubset(report["commands"])
    assert "par" + "ity" not in report["commands"]
    assert report["preferred_command_style"] == "grouped"
    assert report["flat_command_compatibility"] is True
    assert {"clean", "software", "startup", "privacy", "status"}.issubset(report["command_groups"])
    assert "startup plan" in report["command_groups"]["startup"]["commands"]
    assert "privacy plan" in report["command_groups"]["privacy"]["commands"]
    assert "status snapshot" in report["command_groups"]["status"]["commands"]

    ai_eval_pack = report["ai_eval_pack"]
    assert ai_eval_pack["schema"] == "cleanmac.ai-eval-pack.v1"
    assert ai_eval_pack["allows_destructive_execution"] is False
    assert ai_eval_pack["scenario_count"] > 0

    governance_advice = report["ai_governance_advice"]
    assert governance_advice["schema"] == "cleanmac.ai-governance-advice.v1"
    assert governance_advice["ready_for_llm_calling"] is True

    host_policy = report["ai_host_policy"]
    assert host_policy["schema"] == "cleanmac.ai-host-policy.v1"
    assert host_policy["valid"] is True
    assert "cleanmac_execute_plan" in host_policy["auto_call"]["deny"]

    safety = report["safety_guardrails"]
    assert safety["dry_run_default"] is True
    assert safety["bundle_allowlist_flag"] == "clean --bundle-allowlist"
    assert safety["bundle_blocklist_flag"] == "clean --bundle-blocklist"
    assert safety["trash_routing_flag"] == "clean --delete-mode trash"
    assert safety["operation_log_flag"] == "clean --operation-log"
    assert safety["default_operation_log_file"] == cleancli.OPERATIONS_LOG_FILE
    assert safety["deletion_budget_flag"] == "clean --max-delete-mb"


def test_capabilities_json_exposes_deep_safety_guardrail_metadata() -> None:
    result = run_cli("--json", "capabilities")
    report = json.loads(result.stdout)

    safety = report["safety_guardrails"]
    assert safety["log_rotation"]["operations_log_rotate_bytes"] == 5 * 1024 * 1024
    assert {"deviceFirmware", "appleSiliconCaches"}.issubset(safety["deep_system_cleanup_categories"])
    assert safety["default_protected_bundle_count"] >= 40
    assert "com.apple.mail" in safety["default_protected_bundle_ids"]
    assert "CrowdStrike" in safety["official_uninstaller_vendors"]
    assert "CLEANMAC_TEST_NO_AUTH" in safety["test_mode_environment"]["no_auth"]
    assert safety["private_path_allowlist_enabled"] is True
    assert safety["symlink_target_validation_enabled"] is True
    assert "gpuCaches" in safety["dynamic_provider_categories"]
    assert safety["bundle_drift_audit"]["command"] == "python3 scripts/audit_bundle_drift.py --json --fail-on-drift"

    clean_categories = report["command_groups"]["clean"].get("categories")
    category_keys = (
        {row["key"] for row in clean_categories}
        if clean_categories
        else {category.key for category in cleancli.CATEGORIES}
    )
    assert "groupContainerCaches" in category_keys


def test_capabilities_json_exposes_runtime_lifecycle_and_product_boundaries() -> None:
    result = run_cli("--json", "capabilities")
    report = json.loads(result.stdout)

    runtime_lifecycle = report["runtime_lifecycle"]
    assert runtime_lifecycle["schema"] == "cleanmac.runtime-lifecycle-policy.v1"
    assert runtime_lifecycle["product_model"] == "ai-first-ephemeral-cli"
    assert runtime_lifecycle["runs_only_when_invoked"] is True
    assert runtime_lifecycle["exits_after_workflow"] is True
    assert runtime_lifecycle["resident_processes"] == 0
    assert runtime_lifecycle["background_cpu_policy"] == "zero-when-not-invoked"
    assert runtime_lifecycle["background_memory_policy"] == "zero-when-not-invoked"
    assert runtime_lifecycle["implements_tui"] is False
    assert runtime_lifecycle["implements_gui"] is False
    assert runtime_lifecycle["installs_background_daemon"] is False
    assert runtime_lifecycle["installs_login_item"] is False
    assert runtime_lifecycle["performs_unsolicited_scans"] is False
    assert "background cleanup daemon" in runtime_lifecycle["forbidden_product_patterns"]

    positioning = report["product_positioning"]
    assert positioning["schema"] == "cleanmac.product-positioning.v1"
    assert "AI-first cleanup execution kernel" in positioning["positioning"]
    assert "AI-first, zero-resident macOS cleanup CLI" in positioning["canonical_summary"]
    assert "MCP macOS cleanup tool" in positioning["search_queries"]
    assert "model-context-protocol" in positioning["recommended_topics"]
    assert "GUI/TUI feature parity with app-first cleaners" in positioning["non_goals"]

    boundaries = report["boundary_governance"]
    assert boundaries["schema"] == "cleanmac.boundary-governance.v1"
    assert boundaries["runtime_lifecycle"] == runtime_lifecycle
    assert "background daemon" in boundaries["forbidden_automation"]
    assert "menu bar resident app" in boundaries["forbidden_automation"]
    assert "unsolicited scheduled scan" in boundaries["forbidden_automation"]
    assert "clean --execute" in boundaries["forbidden_automation"]
    assert "--allow-live-root" in boundaries["forbidden_automation"]

    geo_policy = boundaries["geo_discoverability_policy"]
    assert geo_policy["schema"] == "cleanmac.geo-discoverability-policy.v1"
    assert "AI-first, zero-resident macOS cleanup CLI" in geo_policy["canonical_summary"]
    assert "AI Agent cleanup tool" in geo_policy["primary_queries"]
    assert "safe Trash-based execution" in geo_policy["must_describe_as"]
    assert "GUI cleaner" in geo_policy["must_not_describe_as"]
    assert ["cleanmac", "--json", "capabilities"] in geo_policy["ai_entrypoints"]

    product_surface_policy = boundaries["product_surface_policy"]
    assert product_surface_policy["schema"] == "cleanmac.product-surface-policy.v1"
    assert "LaunchAgent" in product_surface_policy["forbidden_surfaces"]
    assert "Textual" in product_surface_policy["forbidden_dependency_families"]


def test_capabilities_json_exposes_development_governance_todo_integrity() -> None:
    result = run_cli("--json", "capabilities")
    report = json.loads(result.stdout)

    governance_todo = report["boundary_governance"]["development_governance_todo"]
    assert governance_todo["schema"] == "cleanmac.development-governance-todo.v1"
    assert governance_todo["ordered"] is True
    assert governance_todo["item_count"] == 25
    assert governance_todo["landed_count"] == 25
    assert governance_todo["pending_count"] == 0
    assert governance_todo["status"] == "landed"
    assert [item["order"] for item in governance_todo["items"]] == list(range(1, 26))
    assert {item["status"] for item in governance_todo["items"]} == {"landed"}
    assert governance_todo["items"][0]["id"] == "strengthen-ai-first-entrypoints"
    assert governance_todo["items"][24]["id"] == "gate-release-with-ai-mcp-checklist"
    assert ["make", "ai-first-release-checklist-smoke"] in governance_todo["release_gate_commands"]
    assert report["safety_guardrails"]["development_governance_todo"] == governance_todo

    for item in governance_todo["items"]:
        landing_evidence = item["landing_evidence"]
        assert landing_evidence["state"] == "landed"
        assert landing_evidence["release_gated"] is True
        assert landing_evidence["evidence_refs"]


def test_capabilities_json_exposes_open_source_gap_governance_todo() -> None:
    result = run_cli("--json", "capabilities")
    report = json.loads(result.stdout)

    gap_todo = report["boundary_governance"]["open_source_gap_governance_todo"]
    assert gap_todo["schema"] == "cleanmac.open-source-gap-governance-todo.v1"
    assert gap_todo["ordered"] is True
    assert gap_todo["item_count"] == 10
    assert [item["order"] for item in gap_todo["items"]] == list(range(1, 11))
    assert [item["priority"] for item in gap_todo["items"][:4]] == ["P0", "P0", "P0", "P0"]
    assert "GUI parity" in gap_todo["non_goals"]
    assert "TUI parity" in gap_todo["non_goals"]
    assert gap_todo["items"][0]["id"] == "p0-software-leftover-discovery"
    assert gap_todo["items"][1]["id"] == "p0-software-orphan-scan"
    assert gap_todo["destructive"] is False
    assert gap_todo["dry_run"] is True
    assert gap_todo["in_progress_count"] == 0
    assert gap_todo["pending_count"] == 8
    assert gap_todo["landed_count"] == 2
    assert "resident monitoring" in gap_todo["non_goals"]
    assert "background cleanup automation" in gap_todo["non_goals"]

    statuses = {item["status"] for item in gap_todo["items"]}
    priorities = {item["priority"] for item in gap_todo["items"]}
    assert statuses == {"landed", "pending"}
    assert priorities == {"P0", "P1", "P2"}
    assert all(item["governance_action"] for item in gap_todo["items"])
    assert all(item["reference_projects"] for item in gap_todo["items"])
    assert all(isinstance(item["verification_command"], list) for item in gap_todo["items"])
    assert all(item["verification_command"][0] == "cleanmac" for item in gap_todo["items"])
    assert gap_todo["items"][-1]["id"] == "p2-privacy-scope-parity"


def test_doctor_reports_environment_and_full_disk_access_guidance() -> None:
    result = run_cli("--json", "doctor")
    report = json.loads(result.stdout)

    assert report["schema"] == "cleanmac.doctor.v1"
    assert report["destructive"] is False
    assert "platform" in report
    assert "python" in report
    assert "full_disk_access" in report["checks"]
    assert "live_root_execution" in report["checks"]
    assert "private_path_policy" in report["checks"]
    assert "lsof_available" in report["checks"]
    assert "getconf_available" in report["checks"]


def test_capabilities_json_exposes_governance_integrity_contract() -> None:
    result = run_cli("--json", "capabilities")
    report = json.loads(result.stdout)

    boundaries = report["boundary_governance"]
    assert "make docs-smoke" in boundaries["verification"]["required_commands"]
    assert "make governance-smoke" in boundaries["verification"]["required_commands"]
    assert "make governance-integrity-smoke" in boundaries["verification"]["required_commands"]
    assert "make open-source-smoke" in boundaries["verification"]["required_commands"]

    governance_integrity = report["governance_integrity"]
    assert governance_integrity["schema"] == "cleanmac.governance-integrity.v1"
    assert governance_integrity["ready"] is True
    assert governance_integrity["failed_check_ids"] == []
    assert governance_integrity["stop_reason"] == ""
    assert governance_integrity["readiness_score"]["level"] == "ready"
    assert "cleanmac.geo-discoverability-policy.v1" in governance_integrity["governed_contracts"]
    assert "cleanmac.ai-tool-contract.v1" in governance_integrity["governed_contracts"]

    integrity_checks = {row["id"]: row for row in governance_integrity["checks"]}
    runtime_check = integrity_checks["boundary-runtime-lifecycle-single-source"]
    assert runtime_check["passed"] is True
    assert ["make", "governance-integrity-smoke"] in runtime_check["remediation_commands"]
    assert integrity_checks["boundary-product-surface-single-source"]["passed"] is True
    assert integrity_checks["boundary-geo-policy-single-source"]["passed"] is True


@pytest.mark.parametrize(
    ("relative_path", "heading"),
    [
        ("docs/doc/README.md", "### 5. Generate audit report files"),
        ("docs/doc/README.CN.md", "### 5. 生成审计报告文件"),
    ],
)
def test_readme_audit_examples_keep_global_flags_before_grouped_clean_command(
    relative_path: str,
    heading: str,
) -> None:
    path = PROJECT_ROOT / relative_path
    lines = path.read_text(encoding="utf-8").splitlines()
    start = lines.index(heading)
    fence_start = next(index for index in range(start, len(lines)) if lines[index] == "```bash")
    fence_end = next(index for index in range(fence_start + 1, len(lines)) if lines[index] == "```")
    command = " ".join(
        line.strip().removesuffix("\\").strip()
        for line in lines[fence_start + 1 : fence_end]
        if not line.strip().startswith(">")
    )
    parts = shlex.split(command)

    assert parts[:2] == ["python3", "cleanmac.py"]
    assert parts.index("--report-file") < parts.index("clean")
    actual_argv, grouped_command = cleancli.normalize_grouped_argv(parts[2:])
    parsed = cleancli.parse_args(actual_argv)
    assert parsed.json is True
    assert parsed.report_file == "/tmp/cleanmac-audit.json"
    assert parsed.command == "clean"
    assert grouped_command == {"group": "clean", "action": "run", "mapped_command": "clean"}


def test_inspect_lists_direct_children_sorted_by_size_with_ai_summary() -> None:
    tmp, root, home = make_sandbox()
    with tmp:
        (root / "Users/tester/.Trash/big.tmp").write_text("x" * 100, encoding="utf-8")
        result = run_cli(
            "--root",
            str(root),
            "--home",
            str(home),
            "--json",
            "inspect",
            "--categories",
            "trash",
            "--limit",
            "1",
        )
        report = json.loads(result.stdout)
        ai_summary = report["ai_summary"]

        assert report["shown_candidates"] == 1
        assert report["items"][0]["path"].endswith("big.tmp")
        assert ai_summary["schema"] == "cleanmac.ai-summary.v1"
        assert ai_summary["phase"] == "inspect"
        assert ai_summary["recommended_next_action"] == "generate_plan"
        assert ai_summary["safe_to_execute_after_confirmation"] is False
        assert "trash" in ai_summary["selected_categories"]
        assert ai_summary["headline"]


def test_inspect_supports_recursive_min_size_and_path_sort() -> None:
    tmp, root, home = make_sandbox()
    with tmp:
        nested = root / "Users/tester/.Trash/nested"
        nested.mkdir()
        (nested / "small.txt").write_text("tiny", encoding="utf-8")
        (nested / "large.bin").write_bytes(b"x" * (1024 * 1024 + 1))

        result = run_cli(
            "--root",
            str(root),
            "--home",
            str(home),
            "--json",
            "inspect",
            "--categories",
            "trash",
            "--recursive",
            "--min-size-mb",
            "1",
            "--sort",
            "path",
        )
        report = json.loads(result.stdout)
        paths = [row["path"] for row in report["items"]]

        assert report["recursive"] is True
        assert report["min_size_mb"] == 1
        assert paths == sorted(paths)
        assert any(path.endswith("nested/large.bin") for path in paths)
        large_row = next(row for row in report["items"] if row["path"].endswith("nested/large.bin"))
        assert large_row["depth"] == 2


def test_inspect_accepts_budget_flags_as_non_destructive_preview() -> None:
    tmp, root, home = make_sandbox()
    with tmp:
        old_time = time.time() - 8 * 24 * 60 * 60
        log_file = root / "Users/tester/Library/logs/noisy.log"
        log_file.parent.mkdir(parents=True, exist_ok=True)
        log_file.write_text("log", encoding="utf-8")

        os.utime(log_file, (old_time, old_time))
        result = run_cli(
            "--root",
            str(root),
            "--home",
            str(home),
            "--json",
            "inspect",
            "--categories",
            "userLogs",
            "--older-than-days",
            "7",
            "--max-delete-mb",
            "1000",
            "--max-items",
            "500",
        )
        report = json.loads(result.stdout)

        assert report["max_delete_mb"] == 1000.0
        assert report["max_items"] == 500
        assert report["budget_summary"]["within_max_delete_budget"] is True
        assert report["budget_summary"]["within_max_items"] is True
        assert report["budget_summary"]["applies_to_execute"] is False
        assert log_file.exists()


def test_invalid_name_regex_is_rejected_before_deletion() -> None:
    tmp, root, home = make_sandbox()
    with tmp:
        result = run_cli(
            "--root",
            str(root),
            "--home",
            str(home),
            "inspect",
            "--categories",
            "trash",
            "--name-regex",
            "[",
            check=False,
        )

        assert result.returncode != 0
        assert "Invalid --name-regex" in result.stderr
        assert (root / "Users/tester/.Trash/old.tmp").exists()


def test_incomplete_downloads_skip_active_files() -> None:
    tmp, root, home = make_sandbox()
    with tmp:
        (root / "Users/tester/Downloads/partial.crdownload").write_text("partial", encoding="utf-8")
        with pytest.MonkeyPatch.context() as monkeypatch:
            monkeypatch.setattr(cleancli, "is_file_open", lambda path: path.name == "partial.crdownload")
            report = cleancli.inspect_items(
                [cleancli.CATEGORY_BY_KEY["incompleteDownloads"]],
                root=root,
                home=home,
                limit=50,
            )

        assert report["total_candidates"] == 0
        assert "active-file" in report["skipped_summary"]["by_reason"]


def test_mail_downloads_use_age_and_size_defaults() -> None:
    tmp, root, home = make_sandbox()
    with tmp:
        old_time = time.time() - 40 * 24 * 60 * 60
        old_mail = root / "Users/tester/Library/Mail Downloads/old-mail.pdf"
        old_mail.parent.mkdir(parents=True, exist_ok=True)
        old_mail.write_text("mail-old", encoding="utf-8")
        os.utime(old_mail, (old_time, old_time))

        with pytest.MonkeyPatch.context() as monkeypatch:
            monkeypatch.setenv("CLEANMAC_TEST_MODE", "1")
            result = run_cli(
                "--root",
                str(root),
                "--home",
                str(home),
                "--json",
                "inspect",
                "--categories",
                "mails",
            )
        report = json.loads(result.stdout)

        assert report["total_candidates"] == 0
        assert "below-min-size" in report["skipped_summary"]["by_reason"]


def test_gpu_cache_provider_only_returns_stale_allowlisted_dirs() -> None:
    tmp, root, home = make_sandbox()
    with tmp:
        stale = root / "private/var/folders/aa/bb/C/app/com.apple.metal"
        recent = root / "private/var/folders/aa/bb/C/app/com.apple.metalfe"
        stale.mkdir(parents=True)
        recent.mkdir(parents=True)
        stale_file = stale / "shader.cache"
        recent_file = recent / "shader.cache"
        stale_file.write_text("old", encoding="utf-8")
        recent_file.write_text("new", encoding="utf-8")
        old_time = time.time() - 3 * 24 * 60 * 60
        os.utime(stale_file, (old_time, old_time))
        os.utime(stale, (old_time, old_time))

        result = run_cli(
            "--root",
            str(root),
            "--home",
            str(home),
            "--json",
            "inspect",
            "--categories",
            "gpuCaches",
        )
        report = json.loads(result.stdout)
        paths = [row["path"] for row in report["items"]]

        assert str(stale) in paths
        assert str(recent) not in paths
        assert "not-stale" in report["skipped_summary"]["by_reason"]


def test_browser_code_sign_cache_provider_uses_x_shard_and_preserves_sandbox_safety() -> None:
    tmp, root, home = make_sandbox()
    with tmp:
        cache = root / "private/var/folders/aa/bb/X/com.browser/foo.code_sign_clone"
        cache.mkdir(parents=True)

        result = run_cli(
            "--root",
            str(root),
            "--home",
            str(home),
            "--json",
            "inspect",
            "--categories",
            "browserCodeSignCache",
        )
        report = json.loads(result.stdout)

        assert report["total_candidates"] == 1
        assert report["items"][0]["path"] == str(cache)
        with pytest.raises(RuntimeError, match="outside sandbox root"):
            cleancli.assert_safe_to_delete(Path("/tmp/cleanmac-outside-candidate"), root=root, home=home)


def test_capabilities_json_exposes_distribution_governance_metadata() -> None:
    result = run_cli("--json", "capabilities")
    report = json.loads(result.stdout)

    distribution_governance = report["safety_guardrails"]["distribution_governance"]
    assert distribution_governance["schema"] == "cleanmac.distribution-governance.v1"
    assert {"wheel", "sdist", "standalone-zipapp", "homebrew-formula"}.issubset(
        distribution_governance["supported_artifacts"]
    )
    assert distribution_governance["release_manifest"] == "release-assets/ARTIFACT-MANIFEST.json"
    assert distribution_governance["standalone_smoke_command"] == "python cleanmac.pyz --json capabilities"

    homebrew_policy = distribution_governance["homebrew_formula_policy"]
    assert homebrew_policy["status"] == "tap-publishable"
    assert homebrew_policy["tap"] == "cleanmac/tap"
    assert homebrew_policy["formula_path"] == "Formula/cleanmac.rb"
    assert homebrew_policy["formula_asset"] == "release-assets/cleanmac.rb"
    assert homebrew_policy["recommended_install_method"] == "brew tap cleanmac/tap && brew install cleanmac"
    assert homebrew_policy["publish_automatically"] is False
    assert {"class_name", "url", "sha256", "license", "test do"}.issubset(homebrew_policy["formula_checks"])

    privileged_ownership = report["safety_guardrails"]["privileged_command_ownership"]
    assert privileged_ownership["scan_command"] == "python3 scripts/security_scan.py"


def test_quiet_suppresses_human_readable_output_but_not_json() -> None:
    quiet_result = run_cli("-q", "list")

    assert quiet_result.stdout.strip() == ""

    json_result = run_cli("-q", "--json", "list")
    report = json.loads(json_result.stdout)
    assert report["schema"] == "cleanmac.category-list.v1"
    assert len(report["categories"]) > 0
