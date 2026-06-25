from __future__ import annotations

import json

import pytest

import cleancli.core as cleancli
from cleancli.ai_eval import render_ai_eval_pack
from tests.helpers import run_cli


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


def test_quiet_suppresses_human_readable_output_but_not_json() -> None:
    quiet_result = run_cli("-q", "list")

    assert quiet_result.stdout.strip() == ""

    json_result = run_cli("-q", "--json", "list")
    report = json.loads(json_result.stdout)
    assert report["schema"] == "cleanmac.category-list.v1"
    assert len(report["categories"]) > 0
