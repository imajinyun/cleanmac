"""Tests for AI tool coverage of new features: purge, update, ios-backups, optimize, status."""

from __future__ import annotations

from pathlib import Path

from cleancli import ai_schema

PROJECT_ROOT = Path(__file__).resolve().parents[1]
CLI = PROJECT_ROOT / "cleanmac.py"


NEW_TOOL_NAMES = {
    "cleanmac_purge",
    "cleanmac_update_check",
    "cleanmac_software_ios_backups",
    "cleanmac_optimize",
    "cleanmac_status_snapshot",
}


def test_new_tools_exist_in_definitions():
    names = {t["name"] for t in ai_schema.AI_TOOL_DEFINITIONS}
    for name in NEW_TOOL_NAMES:
        assert name in names, f"{name} missing from AI_TOOL_DEFINITIONS"


def test_new_tools_are_readonly_or_planning_risk():
    by_name = {t["name"]: t for t in ai_schema.AI_TOOL_DEFINITIONS}
    allowed_risks = {"readonly", "planning"}
    for name in NEW_TOOL_NAMES:
        assert by_name[name]["risk"] in allowed_risks, f"{name} risk should be in {allowed_risks}"


def test_new_tools_auto_call_allowed():
    by_name = {t["name"]: t for t in ai_schema.AI_TOOL_DEFINITIONS}
    for name in NEW_TOOL_NAMES:
        assert by_name[name]["auto_call_allowed"] is True, f"{name} should allow auto-call"


def test_new_tools_no_confirmation_required():
    by_name = {t["name"]: t for t in ai_schema.AI_TOOL_DEFINITIONS}
    for name in NEW_TOOL_NAMES:
        assert by_name[name]["requires_confirmation"] is False, f"{name} should not require confirmation"


def test_new_tools_have_argv_template():
    by_name = {t["name"]: t for t in ai_schema.AI_TOOL_DEFINITIONS}
    for name in NEW_TOOL_NAMES:
        template = by_name[name].get("argv_template", [])
        assert len(template) >= 2, f"{name} should have argv_template"
        assert template[0] == "cleanmac", f"{name} argv should start with cleanmac"
        assert template[1] == "--json", f"{name} argv should include --json"


def test_new_tools_have_representative_args():
    for name in NEW_TOOL_NAMES:
        args = ai_schema.representative_args(name)
        assert isinstance(args, dict), f"{name} representative_args should return dict"


def test_new_tools_build_valid_argv():
    for name in NEW_TOOL_NAMES:
        args = ai_schema.representative_args(name)
        argv = ai_schema.build_tool_argv(name, args)
        assert argv[0] == "cleanmac"
        assert argv[1] == "--json"
        assert not any(part in {"sh", "bash", "zsh", "-c", "shell"} for part in argv)


def test_new_tools_not_destructive():
    validation = ai_schema.validate_ai_tool_definitions()
    destructive = set(validation["destructive_tools"])
    for name in NEW_TOOL_NAMES:
        assert name not in destructive, f"{name} should not be a destructive tool"


def test_new_tools_appear_in_mcp_catalog():
    mcp = ai_schema.render_mcp_tool_catalog()
    mcp_names = {t["name"] for t in mcp["tools"]}
    for name in NEW_TOOL_NAMES:
        assert name in mcp_names, f"{name} missing from MCP catalog"


def test_new_tools_appear_in_openai_functions():
    openai = ai_schema.render_openai_functions()
    openai_names = {t["function"]["name"] for t in openai["tools"]}
    for name in NEW_TOOL_NAMES:
        assert name in openai_names, f"{name} missing from OpenAI functions"


def test_new_tools_appear_in_anthropic_tools():
    anthropic = ai_schema.render_anthropic_tools()
    anthropic_names = {t["name"] for t in anthropic["tools"]}
    for name in NEW_TOOL_NAMES:
        assert name in anthropic_names, f"{name} missing from Anthropic tools"


def test_purge_tool_parameters():
    by_name = {t["name"]: t for t in ai_schema.AI_TOOL_DEFINITIONS}
    tool = by_name["cleanmac_purge"]
    params = tool["parameters"]
    assert "recent_days" in params["properties"]
    assert "scan_roots" in params["properties"]


def test_update_check_tool_parameters():
    by_name = {t["name"]: t for t in ai_schema.AI_TOOL_DEFINITIONS}
    tool = by_name["cleanmac_update_check"]
    params = tool["parameters"]
    assert "version" in params["properties"]


def test_purge_build_argv_with_options():
    argv = ai_schema.build_tool_argv("cleanmac_purge", {"recent_days": 14, "scan_roots": ["~/Projects", "~/dev"]})
    assert "--recent-days" in argv
    assert "14" in argv
    assert "--scan-roots" in argv
    assert "~/Projects,~/dev" in argv


def test_update_check_build_argv_with_version():
    argv = ai_schema.build_tool_argv("cleanmac_update_check", {"version": "2.0.0"})
    assert "--version" in argv
    assert "2.0.0" in argv


def test_software_ios_backups_build_argv():
    argv = ai_schema.build_tool_argv("cleanmac_software_ios_backups", {})
    assert argv == ["cleanmac", "--json", "software", "ios-backups"]


def test_new_tools_pass_schema_validation():
    validation = ai_schema.validate_ai_tool_definitions()
    assert validation["valid"], f"Validation violations: {validation['violations']}"


def test_optimize_tool_has_actions():
    argv_list = ai_schema.build_tool_argv("cleanmac_optimize", {"action": "list"})
    argv_plan = ai_schema.build_tool_argv("cleanmac_optimize", {"action": "plan"})
    argv_run = ai_schema.build_tool_argv("cleanmac_optimize", {"action": "run"})
    assert "list" in argv_list
    assert "plan" in argv_plan
    assert "run" in argv_run


def test_status_snapshot_is_no_arg():
    argv = ai_schema.build_tool_argv("cleanmac_status_snapshot", {})
    assert argv == ["cleanmac", "--json", "status", "snapshot"]
