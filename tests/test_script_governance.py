from __future__ import annotations

import json

from tests.helpers import run_cli


def test_destructive_script_templates_are_not_safe_to_auto_execute() -> None:
    report = json.loads(run_cli("--json", "clean", "scripts", "--categories", "trash,systemLogs").stdout)

    destructive_templates = [
        template
        for category in report["categories"]
        for templates in category["command_templates"].values()
        for template in templates
        if template["destructive"]
    ]
    assert destructive_templates
    assert all(not template["safe_to_auto_execute"] for template in destructive_templates)


def test_recommended_script_templates_do_not_show_raw_rm_rf() -> None:
    report = json.loads(run_cli("--json", "clean", "scripts", "--categories", "trash,systemLogs").stdout)

    commands = [
        command
        for category in report["categories"]
        for bucket in ("analyze", "delete")
        for command in category["commands"][bucket]
    ]
    commands.extend(
        template["command"] for group in report["groups"].values() for template in group.get("command_templates", [])
    )

    assert all("rm -rf" not in command for command in commands)
    delete_commands = [command for category in report["categories"] for command in category["commands"]["delete"]]
    assert delete_commands
    assert all("clean run" in command and "--delete-mode trash" in command for command in delete_commands)
