from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any
from unittest import mock

import cleancli.tool_adapters as tool_adapters
from cleancli.ai_versioning import validate_contract_payload
from tests.helpers import make_sandbox, run_cli


def test_permissions_preflight_reports_privilege_and_fda_requirements() -> None:
    tmp, root, home = make_sandbox()
    with tmp:
        result = run_cli(
            "--root",
            str(root),
            "--home",
            str(home),
            "--json",
            "permissions",
            "--categories",
            "imessage,systemLogs,trash",
        )
        report = json.loads(result.stdout)
        by_key = {row["key"]: row for row in report["categories"]}

        assert report["schema"] == "cleanmac.permissions-preflight.v1"
        assert report["destructive"] is False
        assert report["dry_run"] is True
        assert report["category_count"] == 3
        assert set(by_key) == {"imessage", "systemLogs", "trash"}
        assert report["live_root"] is False
        assert report["blocked_or_needs_attention_count"] == 0
        assert report["recommended_next_action"] == "safe_to_dry_run_selected_categories"
        assert by_key["imessage"]["full_disk_access"] is True
        assert by_key["imessage"]["requires_privilege"] is True
        assert by_key["imessage"]["execute_ready"] is True
        assert by_key["imessage"]["blockers"] == []
        assert by_key["imessage"]["hints"] == []
        assert by_key["systemLogs"]["requires_privilege"] is True
        assert by_key["systemLogs"]["full_disk_access"] is False
        assert by_key["systemLogs"]["execute_ready"] is True
        assert by_key["systemLogs"]["blockers"] == []
        assert by_key["trash"]["requires_privilege"] is False
        assert by_key["trash"]["full_disk_access"] is False
        assert by_key["trash"]["execute_ready"] is True
        assert validate_contract_payload("cleanmac.permissions-preflight.v1", report)["valid"] is True


def test_tool_plan_is_readonly_and_lists_manual_commands() -> None:
    result = run_cli("--json", "tool-plan", "--tool", "docker")
    report = json.loads(result.stdout)
    adapter = report["adapters"][0]

    assert report["schema"] == "cleanmac.tool-plan.v1"
    assert report["destructive"] is False
    assert report["dry_run"] is True
    assert report["adapter_count"] == 1
    assert report["selected_tool"] == "docker"
    assert report["safe_to_auto_execute"] is False
    assert report["execution_policy"] == {
        "default_mode": "dry-run",
        "auto_execute_allowed": False,
        "requires_human_confirmation_for_execute": True,
        "external_prune_commands_are_recommendations_only_in_plan": True,
    }
    assert adapter["key"] == "docker"
    assert ["docker", "system", "df"] in adapter["dry_run_commands"]
    assert ["docker", "system", "df", "--verbose"] in adapter["dry_run_commands"]
    assert ["docker", "builder", "du"] in adapter["dry_run_commands"]
    assert ["docker", "builder", "prune"] in adapter["manual_execute_commands"]
    assert ["docker", "image", "prune"] in adapter["manual_execute_commands"]
    assert ["docker", "container", "prune"] in adapter["manual_execute_commands"]
    assert ["docker", "volume", "prune"] in adapter["excluded_destructive_commands"]
    assert ["docker", "system", "prune", "--volumes"] in adapter["excluded_destructive_commands"]
    assert adapter["execution_policy"]["external_prune_commands_are_recommendations_only_in_plan"] is True
    assert all(command["auto_call_allowed"] is True for command in adapter["recommended_commands"][:3])
    assert all(command["auto_call_allowed"] is False for command in adapter["recommended_commands"][3:])
    assert adapter["auto_execute_allowed"] is False
    assert any("read-only" in note for note in adapter["notes"])
    assert validate_contract_payload("cleanmac.tool-plan.v1", report)["valid"] is True
    assert not any(adapter["auto_execute_allowed"] for adapter in report["adapters"])


def test_tool_plan_expands_package_manager_dry_run_adapters() -> None:
    result = run_cli("--json", "tool-plan", "--tool", "package-managers")
    report = json.loads(result.stdout)
    adapters = {adapter["key"]: adapter for adapter in report["adapters"]}

    assert report["schema"] == "cleanmac.tool-plan.v1"
    assert report["destructive"] is False
    assert report["dry_run"] is True
    assert report["selected_tool"] == "package-managers"
    assert report["adapter_count"] == 7
    assert set(adapters) == {"npm", "pnpm", "yarn", "pip", "uv", "poetry", "cargo"}
    assert ["npm", "cache", "verify"] in adapters["npm"]["dry_run_commands"]
    assert ["npm", "config", "get", "cache"] in adapters["npm"]["dry_run_commands"]
    assert ["npm", "cache", "clean", "--force"] in adapters["npm"]["manual_execute_commands"]
    assert ["pnpm", "store", "status"] in adapters["pnpm"]["dry_run_commands"]
    assert ["pnpm", "store", "path"] in adapters["pnpm"]["dry_run_commands"]
    assert ["pnpm", "store", "prune"] in adapters["pnpm"]["manual_execute_commands"]
    assert ["yarn", "cache", "dir"] in adapters["yarn"]["dry_run_commands"]
    assert ["rm", "-rf", "~/.yarn"] in adapters["yarn"]["excluded_destructive_commands"]
    assert ["pip", "cache", "info"] in adapters["pip"]["dry_run_commands"]
    assert ["pip", "cache", "dir"] in adapters["pip"]["dry_run_commands"]
    assert ["pip", "cache", "purge"] in adapters["pip"]["manual_execute_commands"]
    assert ["uv", "cache", "dir"] in adapters["uv"]["dry_run_commands"]
    assert ["uv", "cache", "clean"] in adapters["uv"]["excluded_destructive_commands"]
    assert ["poetry", "cache", "list"] in adapters["poetry"]["dry_run_commands"]
    assert ["poetry", "cache", "clear", "PyPI", "--all"] in adapters["poetry"]["manual_execute_commands"]
    assert ["cargo", "--version"] in adapters["cargo"]["dry_run_commands"]
    assert adapters["cargo"]["manual_execute_commands"] == []
    assert ["cargo", "cache", "--remove-dir", "all"] in adapters["cargo"]["excluded_destructive_commands"]
    assert adapters["npm"]["path_categories"] == ["nodePackageCaches"]
    assert adapters["pnpm"]["path_categories"] == ["nodePackageCaches"]
    assert adapters["yarn"]["path_categories"] == ["nodePackageCaches"]
    assert adapters["pip"]["path_categories"] == ["pythonPackageCaches"]
    assert adapters["uv"]["path_categories"] == ["pythonPackageCaches"]
    assert adapters["poetry"]["path_categories"] == ["pythonPackageCaches"]
    assert adapters["cargo"]["path_categories"] == ["cargoCaches"]
    assert not any(adapter["auto_execute_allowed"] for adapter in adapters.values())
    assert all(
        command["auto_call_allowed"] is True
        for adapter in adapters.values()
        for command in adapter["recommended_commands"]
        if command["purpose"] == "dry-run-analysis"
    )
    assert all(
        command["auto_call_allowed"] is False
        for adapter in adapters.values()
        for command in adapter["recommended_commands"]
        if command["purpose"] == "manual-human-confirmed-cleanup"
    )


def test_developer_tool_plan_explains_cleanup_scope_and_risks() -> None:
    result = run_cli("--json", "tool-plan", "--tool", "all")
    report = json.loads(result.stdout)
    adapters = {adapter["key"]: adapter for adapter in report["adapters"]}

    assert report["execution_policy"]["auto_execute_allowed"] is False
    assert report["execution_policy"]["requires_human_confirmation_for_execute"] is True
    assert report["execution_policy"]["external_prune_commands_are_recommendations_only_in_plan"] is True
    assert "DerivedData" in " ".join(adapters["xcode"]["cleanup_scope"])
    assert "Archives" in " ".join(adapters["xcode"]["cleanup_scope"])
    assert "CoreSimulator" in " ".join(adapters["xcode"]["cleanup_scope"])
    assert "homebrewCaches" in adapters["homebrew"]["path_categories"]
    assert "nodePackageCaches" in adapters["yarn"]["path_categories"]
    assert "pythonPackageCaches" in adapters["poetry"]["path_categories"]
    assert "cargoCaches" in adapters["cargo"]["path_categories"]
    assert all(adapter["risk_explanation"] for adapter in adapters.values())
    assert all(
        command["auto_call_allowed"] is False
        for adapter in adapters.values()
        for command in adapter["recommended_commands"]
        if command["purpose"] == "manual-human-confirmed-cleanup"
    )


def test_tool_execute_dry_run_uses_allowlisted_commands() -> None:
    calls: list[list[str]] = []

    def fake_runner(argv: Any, timeout: float) -> subprocess.CompletedProcess[str]:
        calls.append(list(argv))
        return subprocess.CompletedProcess(list(argv), 0, stdout="TYPE TOTAL", stderr="")

    with mock.patch.object(tool_adapters.shutil, "which", return_value="/usr/local/bin/docker"):
        report = tool_adapters.execute_tool(
            "docker",
            execute=False,
            yes=False,
            root=Path("/tmp/cleanmac-sandbox"),
            home=Path("/Users/tester"),
            runner=fake_runner,
        )

    assert report["schema"] == "cleanmac.tool-execution-result.v1"
    assert report["destructive"] is False
    assert report["dry_run"] is True
    assert report["selected_tool"] == "docker"
    assert report["safe_to_auto_execute"] is False
    assert report["blocked_reasons"] == []
    assert calls == [
        ["docker", "system", "df"],
        ["docker", "system", "df", "--verbose"],
        ["docker", "builder", "du"],
    ]
    assert ["docker", "builder", "prune", "--force"] not in calls
    assert ["docker", "image", "prune", "--force"] not in calls
    assert ["docker", "container", "prune", "--force"] not in calls
    assert [result["argv"] for result in report["results"]] == calls
    assert [entry["action"] for entry in report["operation_log_entries"]] == ["tool-dry-run"] * 3
    assert report["failed_count"] == 0
    assert report["succeeded_count"] == 3


def test_package_manager_tool_execute_dry_run_uses_only_readonly_commands() -> None:
    calls: list[list[str]] = []

    def fake_runner(argv: Any, timeout: float) -> subprocess.CompletedProcess[str]:
        calls.append(list(argv))
        return subprocess.CompletedProcess(list(argv), 0, stdout="ok", stderr="")

    with mock.patch.object(tool_adapters.shutil, "which", return_value="/usr/local/bin/tool"):
        report = tool_adapters.execute_tool(
            "package-managers",
            execute=False,
            yes=False,
            root=Path("/tmp/cleanmac-sandbox"),
            home=Path("/Users/tester"),
            runner=fake_runner,
        )

    assert report["destructive"] is False
    assert calls == [
        ["npm", "cache", "verify"],
        ["npm", "config", "get", "cache"],
        ["pnpm", "store", "status"],
        ["pnpm", "store", "path"],
        ["yarn", "cache", "dir"],
        ["pip", "cache", "info"],
        ["pip", "cache", "dir"],
        ["uv", "cache", "dir"],
        ["poetry", "cache", "list"],
        ["cargo", "--version"],
    ]
    assert not any("prune" in result["argv"] or "purge" in result["argv"] for result in report["results"])
    assert report["failed_count"] == 0


def test_tool_execute_blocks_destructive_without_yes() -> None:
    runner = mock.Mock()
    with mock.patch.object(tool_adapters.shutil, "which", return_value="/usr/local/bin/docker"):
        report = tool_adapters.execute_tool(
            "docker",
            execute=True,
            yes=False,
            root=Path("/tmp/root"),
            home=Path("/Users/tester"),
            runner=runner,
        )

    assert report["destructive"] is True
    assert report["dry_run"] is False
    assert report["selected_tool"] == "docker"
    assert report["safe_to_auto_execute"] is False
    assert report["blocked_reasons"] == ["explicit-yes-required"]
    assert "explicit-yes-required" in report["blocked_reasons"]
    assert [result["argv"] for result in report["results"]] == [
        ["docker", "builder", "prune", "--force"],
        ["docker", "image", "prune", "--force"],
        ["docker", "container", "prune", "--force"],
    ]
    assert all(result["status"] == "blocked" for result in report["results"])
    assert all(result["returncode"] is None for result in report["results"])
    assert all(result["error"] == "explicit --yes required" for result in report["results"])
    assert [entry["action"] for entry in report["operation_log_entries"]] == ["tool-execute"] * 3
    assert all(entry["status"] == "blocked" for entry in report["operation_log_entries"])
    assert report["succeeded_count"] == 0
    assert report["failed_count"] == 3
    runner.assert_not_called()
