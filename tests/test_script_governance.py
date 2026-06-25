from __future__ import annotations

import json
import shlex
from pathlib import Path

import cleancli.core as cleancli
from tests.helpers import PROJECT_ROOT, make_sandbox, run_cli


def test_safe_test_runner_sets_no_auth_and_stubs_dangerous_commands() -> None:
    runner_path = PROJECT_ROOT / "scripts/test.sh"
    runner = runner_path.read_text(encoding="utf-8")

    assert runner_path.is_file()
    assert "set -euo pipefail" in runner
    assert "export CLEANMAC_TEST_NO_AUTH=1" in runner
    assert "export CLEANMAC_TEST_MODE=1" in runner
    removed_product_test_prefix = "".join(chr(code) for code in (77, 79, 76, 69, 95, 84, 69, 83, 84, 95))
    assert removed_product_test_prefix not in runner
    assert "mktemp -d" in runner
    assert 'cat > "$TEST_SYSTEM_STUB_DIR/sudo"' in runner
    assert 'cat > "$TEST_SYSTEM_STUB_DIR/osascript"' in runner
    assert 'cat > "$TEST_SYSTEM_STUB_DIR/launchctl"' in runner
    assert 'cat > "$TEST_SYSTEM_STUB_DIR/rm"' in runner
    assert 'export PATH="$TEST_SYSTEM_STUB_DIR:$PATH"' in runner
    assert '"$PYTHON_BIN" -m unittest -v' in runner
    assert '"$MAKE_BIN" governance-smoke' in runner
    assert '"$MAKE_BIN" script-smoke' in runner
    assert "cleanmac test blocked sudo" in runner
    assert "cleanmac test blocked osascript" in runner
    assert "cleanmac test blocked launchctl" in runner
    assert "cleanmac test blocked rm -rf style command" in runner


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


def test_scripts_reports_current_command_templates() -> None:
    result = run_cli("--json", "scripts", "--categories", "terminal,imessage")
    report = json.loads(result.stdout)
    inventory = report["script_inventory"]
    validation = report["template_validation"]
    migration = report["template_migration"]
    terminal = report["categories"][0]
    imessage = report["categories"][1]

    assert validation["schema"] == "cleanmac.command-template-validation.v1"
    assert validation["valid"] is True
    assert validation["violation_count"] == 0
    assert validation["violations"] == []
    assert validation["template_count"] > 0
    assert validation["destructive_template_count"] > 0
    assert validation["safe_to_auto_execute_template_count"] > 0
    assert migration["schema"] == "cleanmac.command-template-migration.v1"
    assert migration["raw_rm_rf_template_count"] == 0
    assert migration["deprecated_template_count"] == 0
    assert migration["replacement_template_count"] == 0
    assert migration["recommended_delete_template_count"] > 0
    assert migration["all_recommended_delete_templates_use_cleanmac_cli"] is True
    assert inventory["shell_execution"]["launch_path"] == "/bin/sh"
    assert inventory["schema"] == "cleanmac.script-groups.v1"
    assert inventory["command_template_contract"]["required_fields"] == [
        "id",
        "kind",
        "command",
        "argv",
        "placeholders",
        "uses_shell",
        "destructive",
        "safe_to_auto_execute",
        "manual_review_required",
        "execution_policy",
    ]
    assert "clean" in report["groups"]
    assert "software" in report["groups"]
    assert "python3 cleanmac.py --json clean inspect" in report["groups"]["clean"]["commands"][0]
    assert report["groups"]["clean"]["safe_to_auto_execute"] is False
    assert report["groups"]["clean"]["contains_destructive_templates"] is True
    assert report["groups"]["clean"]["manual_review_required"] is True
    assert report["groups"]["clean"]["command_templates"][0]["id"] == "clean-inspect-selected"
    assert report["groups"]["clean"]["command_templates"][0]["kind"] == "argv"
    assert report["groups"]["clean"]["command_templates"][0]["argv"] == [
        "python3",
        "cleanmac.py",
        "--json",
        "clean",
        "inspect",
        "--categories",
        "<keys>",
    ]
    assert report["groups"]["clean"]["command_templates"][0]["uses_shell"] is False
    assert report["groups"]["clean"]["command_templates"][0]["destructive"] is False
    assert (
        report["groups"]["clean"]["command_templates"][0]["execution_policy"]["requires_placeholder_substitution"]
        is True
    )
    assert report["groups"]["clean"]["command_templates"][2]["destructive"] is True
    assert report["groups"]["clean"]["command_templates"][2]["manual_review_required"] is True
    assert report["groups"]["software"]["safe_to_auto_execute"] is False
    assert report["groups"]["software"]["contains_destructive_templates"] is True
    assert report["groups"]["software"]["destructive"] is True
    assert report["groups"]["software"]["command_templates"][0]["id"] == "software-list"
    assert report["groups"]["software"]["command_templates"][0]["argv"] == [
        "python3",
        "cleanmac.py",
        "--json",
        "software",
        "list",
    ]
    assert report["groups"]["software"]["command_templates"][-1]["destructive"] is True
    assert report["groups"]["software"]["command_templates"][-1]["safe_to_auto_execute"] is False
    assert report["groups"]["software"]["command_templates"][-1]["manual_review_required"] is True
    assert "boundary_governance" in inventory
    assert inventory["boundary_governance"]["script_template_policy"]["auto_execute_allowed"] is False
    assert inventory["boundary_governance"]["script_template_policy"]["global_flags_before_command"] is True
    assert "symbolic_links" in inventory
    assert inventory["open_in_finder"]["command"] == "python3 cleanmac.py clean open --categories <keys>"
    assert "du -smc" in terminal["commands"]["analyze"][0]
    assert "/private/var/log/asl/*.asl" in terminal["commands"]["analyze"][0]
    assert "python3 cleanmac.py" in terminal["commands"]["delete"][0]
    assert "clean run" in terminal["commands"]["delete"][0]
    assert "--delete-mode trash" in terminal["commands"]["delete"][0]
    assert "rm -rf" not in terminal["commands"]["delete"][0]
    assert terminal["command_templates"]["analyze"][0]["id"] == "terminal-analyze-1"
    assert terminal["command_templates"]["analyze"][0]["kind"] == "shell"
    assert terminal["command_templates"]["analyze"][0]["uses_shell"] is True
    assert terminal["command_templates"]["analyze"][0]["destructive"] is False
    assert terminal["command_templates"]["analyze"][0]["execution_policy"]["uses_shell"] is True
    assert terminal["command_templates"]["delete"][0]["uses_shell"] is False
    assert terminal["command_templates"]["delete"][0]["kind"] == "argv"
    assert terminal["command_templates"]["delete"][0]["destructive"] is True
    assert terminal["command_templates"]["delete"][0]["safe_to_auto_execute"] is False
    assert terminal["command_templates"]["delete"][0]["manual_review_required"] is True
    assert imessage["full_disk_access"] is True
    assert imessage["requires_privilege"] is True


def test_scripts_group_filter_returns_selected_group() -> None:
    result = run_cli("--json", "clean", "scripts", "--group", "status")
    report = json.loads(result.stdout)

    assert report["script_inventory"]["selected_group"] == "status"
    assert list(report["groups"].keys()) == ["status"]
    assert report["groups"]["status"]["commands"][0] == "python3 cleanmac.py --json status snapshot"


def test_command_template_validation_reports_policy_violations() -> None:
    invalid_template = {
        "id": "bad-delete",
        "kind": "argv",
        "command": "rm -rf /tmp/example",
        "argv": ["rm", "-rf", "/tmp/example"],
        "placeholders": [],
        "uses_shell": False,
        "destructive": True,
        "safe_to_auto_execute": True,
        "manual_review_required": False,
        "execution_policy": {
            "uses_shell": False,
            "destructive": True,
            "safe_to_auto_execute": True,
            "manual_review_required": False,
            "requires_placeholder_substitution": False,
        },
    }

    validation = cleancli.validate_command_templates(
        {"bad": {"command_templates": [invalid_template]}},
        [],
    )
    violation_codes = {violation["code"] for violation in validation["violations"]}

    assert validation["valid"] is False
    assert validation["template_count"] == 1
    assert validation["destructive_template_count"] == 1
    assert "destructive-auto-execute" in violation_codes
    assert "destructive-without-review" in violation_codes
    assert "destructive-not-cleanmac-cli" in violation_codes
    assert "raw-rm-forbidden" in violation_codes


def test_script_group_commands_follow_cli_global_flag_order_and_parse() -> None:
    result = run_cli("--json", "scripts", "--categories", "trash")
    report = json.loads(result.stdout)

    for group_name, group_report in report["groups"].items():
        for command in group_report["commands"]:
            normalized = (
                command.replace("<keys>", "trash")
                .replace("<plan.json>", "/tmp/cleanmac-plan.json")
                .replace("<AppName>", "Example.app")
            )
            parts = shlex.split(normalized)
            assert parts[:2] == ["python3", "cleanmac.py"], command
            assert "--json" in parts[2:], command
            assert parts.index("--json") < parts.index(group_name), command

            actual_argv, grouped_command = cleancli.normalize_grouped_argv(parts[2:])
            parsed = cleancli.parse_args(actual_argv)
            assert parsed.json is True, command
            if grouped_command is not None:
                assert grouped_command["group"] == group_name


def _add_workflow_fixture(root: Path) -> None:
    mail_downloads = root / "Users/tester/Library/Mail Downloads"
    xcode_derived_data = root / "Users/tester/Library/Developer/Xcode/DerivedData/App-a"
    mail_downloads.mkdir(parents=True)
    xcode_derived_data.mkdir(parents=True)
    (mail_downloads / "old-mail.pdf").write_text("mail-old", encoding="utf-8")
    (xcode_derived_data / "cache.db").write_text("derived", encoding="utf-8")


def test_workflow_runs_fixed_non_destructive_phases() -> None:
    tmp, root, home = make_sandbox()
    with tmp:
        _add_workflow_fixture(root)
        result = run_cli(
            "--root",
            str(root),
            "--home",
            str(home),
            "--json",
            "workflow",
            "--categories",
            "trash,mails,xcode,userLogs,downloads",
            "--log-threshold-mb",
            "0",
            "--inspect-limit",
            "3",
        )
        report = json.loads(result.stdout)
        automation = report["automation_playbook"]
        iteration = report["reports"]["iteration_status"]
        ux_guide = report["ux_guide"]

        assert report["workflow_name"] == "safe-cleaning-workflow"
        assert [step["name"] for step in report["steps"]] == [
            "script-audit",
            "analyze-space",
            "diagnose-problems",
            "inspect-candidates",
            "dry-run-clean",
            "manual-execute-gate",
        ]
        assert report["steps"][4]["destructive"] is False
        assert report["steps"][5]["destructive"] is True
        assert [category["key"] for category in report["dry_run_categories"]] == ["trash", "mails", "xcode"]
        assert automation["schema"] == "cleanmac.workflow-automation.v1"
        assert automation["safe_to_auto_execute"] is True
        assert automation["destructive_cleanup_allowed"] is False
        assert automation["test_acceptance"]["environment"]["requires_virtualenv"] is True
        assert automation["test_acceptance"]["environment"]["workflow_python_env"] == "PYTHON=.venv/bin/python"
        assert automation["test_acceptance"]["environment"]["tooling_must_run_in_virtualenv"] == [
            "ruff",
            "mypy",
            "pytest",
            "coverage",
        ]
        assert "make docker-test" in automation["test_acceptance"]["environment"]["docker_fallback"]
        assert "clean --execute" in automation["agent_contract"]["forbidden_command_patterns"]
        assert automation["test_acceptance"]["required_commands"] == [
            "make quality-check",
            "make local-test",
            "make build-check",
            "make package-smoke",
            "make script-smoke",
            "make bundle-audit-smoke",
            "make macos-smoke",
            "make security-smoke",
            "make dependency-audit-smoke",
            "make docs-smoke",
            "make governance-smoke",
            "make open-source-smoke",
            "make distribution-smoke",
            "make docker-test",
            "make release-check",
        ]
        assert iteration["schema"] == "cleanmac.workflow-iteration-status.v1"
        assert iteration["safe_to_auto_continue"] is True
        assert iteration["destructive_cleanup_allowed"] is False
        assert iteration["next_checkpoint"] == "test-acceptance"
        assert iteration["acceptance_gate"]["ready_for_docker_validation"] is True
        assert ux_guide["schema"] == "cleanmac.workflow-ux.v1"
        assert ux_guide["one_command"]["safe_to_auto_call"] is True
        assert ux_guide["one_command"]["performs_background_scan"] is False
        assert ux_guide["one_command"]["executes_cleanup"] is False
        assert ux_guide["dry_run_summary"]["next_action"] == "review_candidates"
        single_shot = {row["id"]: row for row in report["single_shot_workflows"]}
        assert single_shot["quick-safe-clean"]["safe_to_auto_call"] is True
        assert single_shot["quick-safe-clean"]["destructive"] is False
        assert "trash,downloads,mails,xcode" in single_shot["quick-safe-clean"]["argv"]
        assert single_shot["developer-clean"]["exits_after_workflow"] is True
        assert "nodePackageCaches" in single_shot["developer-clean"]["categories"]
        assert single_shot["large-files-review"]["destructive"] is False
        tool_hints = {row["intent"]: row for row in ux_guide["tool_choice_hints"]}
        assert tool_hints["understand_available_actions"]["first_tool"] == "cleanmac_capabilities"
        assert tool_hints["common_safe_cleanup_workflow"]["first_tool"] == "cleanmac_workflow"
        assert tool_hints["check_execute_readiness"]["safe_to_auto_call"] is True
        assert tool_hints["execute_cleanup"]["first_tool"] == "cleanmac_execute_plan"
        assert tool_hints["execute_cleanup"]["safe_to_auto_call"] is False
        common_workflows = {row["name"]: row for row in ux_guide["common_workflows"]}
        assert common_workflows["safe_preview_once"]["safe_to_auto_call"] is True
        assert common_workflows["safe_preview_once"]["destructive"] is False
        assert common_workflows["ai_governed_plan_review_dry_run"]["safe_to_auto_call_until"] == (
            "dry_run_selected_plan"
        )
        assert common_workflows["human_confirmed_trash_execute"]["safe_to_auto_call"] is False
        assert common_workflows["human_confirmed_trash_execute"]["requires_human_confirmation"] is True
        file_relationships = {row["name"]: row for row in ux_guide["file_relationships"]}
        assert file_relationships["plan_file"]["schema"] == "cleanmac.plan.v1"
        assert "review" in file_relationships["plan_file"]["consumers"]
        assert file_relationships["review_selection_file"]["schema"] == "cleanmac.review-selection.v1"
        assert file_relationships["confirmation_token"]["schema"] == "cleanmac.ai-confirmation-summary.v1"
        assert file_relationships["operation_log"]["schema"] == "cleanmac.operation-log-entry.v1"
        safe_chain = {row["step"]: row for row in ux_guide["safe_chain"]}
        assert "--ai-origin" in safe_chain["generate_plan"]["argv"]
        assert "--selection-file" in safe_chain["review_plan"]["argv"]
        assert "--review-selection-file" in safe_chain["policy_simulate_execute_intent"]["argv"]
        assert "--require-plan-context" in safe_chain["dry_run_selected_plan"]["argv"]
        assert safe_chain["execute_after_human_confirmation"]["destructive"] is True
        assert safe_chain["execute_after_human_confirmation"]["safe_to_auto_call"] is False
        assert "--confirmation-token" in safe_chain["execute_after_human_confirmation"]["argv"]
        assert ux_guide["concept_map"]["delete_mode"] == (
            "Use trash for recoverability; permanent mode is not allowed for AI-originated execute."
        )
        assert (root / "Users/tester/.Trash/old.tmp").exists()
        assert (root / "Users/tester/Downloads/download.bin").exists()
