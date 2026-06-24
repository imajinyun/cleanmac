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


def test_quiet_suppresses_human_readable_output_but_not_json() -> None:
    quiet_result = run_cli("-q", "list")

    assert quiet_result.stdout.strip() == ""

    json_result = run_cli("-q", "--json", "list")
    report = json.loads(json_result.stdout)
    assert report["schema"] == "cleanmac.category-list.v1"
    assert len(report["categories"]) > 0
