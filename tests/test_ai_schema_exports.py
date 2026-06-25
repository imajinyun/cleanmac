from __future__ import annotations

import json
from typing import Any

from cleancli import ai_schema, ai_versioning
from tests.helpers import run_cli

EXPECTED_TOOL_COUNT = 38


def load_ai_tools(format_name: str | None = None) -> dict[str, Any]:
    args = ["ai-tools"]
    if format_name is not None:
        args.extend(["--format", format_name])
    return json.loads(run_cli(*args).stdout)


def test_ai_tools_exports_provider_specific_tool_formats() -> None:
    openai_report = load_ai_tools("openai")
    anthropic_report = load_ai_tools("anthropic")
    mcp_report = load_ai_tools("mcp")

    assert openai_report["schema"] == "cleanmac.ai-openai-functions.v1"
    assert all(tool["type"] == "function" for tool in openai_report["tools"])
    assert "function" in openai_report["tools"][0]

    assert anthropic_report["schema"] == "cleanmac.ai-anthropic-tools.v1"
    assert "input_schema" in anthropic_report["tools"][0]

    assert mcp_report["schema"] == "cleanmac.mcp-tool-catalog.v1"
    assert "invocation" in mcp_report["tools"][0]

    mcp_tools = {tool["name"]: tool for tool in mcp_report["tools"]}
    execute_annotations = mcp_tools["cleanmac_execute_plan"]["annotations"]
    assert execute_annotations["readOnlyHint"] is False
    assert execute_annotations["destructiveHint"] is True
    assert execute_annotations["idempotentHint"] is False
    assert execute_annotations["openWorldHint"] is False

    inspect_annotations = mcp_tools["cleanmac_inspect"]["annotations"]
    assert inspect_annotations["readOnlyHint"] is True
    assert inspect_annotations["destructiveHint"] is False
    assert inspect_annotations["idempotentHint"] is True
    assert inspect_annotations["openWorldHint"] is False

    all_report = load_ai_tools()
    assert all_report["schema"] == "cleanmac.ai-tools.v1"
    assert all_report["openai"]["schema"] == "cleanmac.ai-openai-functions.v1"
    assert all_report["anthropic"]["schema"] == "cleanmac.ai-anthropic-tools.v1"
    assert all_report["mcp"]["schema"] == "cleanmac.mcp-tool-catalog.v1"
    assert "annotations" in all_report["mcp"]["tools"][0]

    for tool in anthropic_report["tools"]:
        assert "name" in tool
        assert "description" in tool
        assert "input_schema" in tool
        assert isinstance(tool["input_schema"], dict)
        assert tool["input_schema"]["type"] == "object"
        assert "properties" in tool["input_schema"]
        assert tool["input_schema"].get("additionalProperties", False) is False
        assert tool["name"].startswith("cleanmac_")

    assert len(anthropic_report["tools"]) == EXPECTED_TOOL_COUNT
    assert len(openai_report["tools"]) == EXPECTED_TOOL_COUNT
    assert len(mcp_report["tools"]) == EXPECTED_TOOL_COUNT


def test_capabilities_provider_exports_match_mcp_catalog_and_validation() -> None:
    report = json.loads(run_cli("--json", "capabilities").stdout)

    function_schemas = report["ai_function_schemas"]
    assert function_schemas["schema"] == "cleanmac.ai-function-schemas.v1"
    tool_names = {tool["name"] for tool in function_schemas["tools"]}
    assert {
        "cleanmac_ai_governance_advice",
        "cleanmac_ai_host_policy",
        "cleanmac_generate_plan",
        "cleanmac_execute_plan",
        "cleanmac_policy_simulate",
        "cleanmac_workflow",
        "cleanmac_software_uninstall_plan",
        "cleanmac_software_uninstall_execute",
    }.issubset(tool_names)

    execute_tool = next(tool for tool in function_schemas["tools"] if tool["name"] == "cleanmac_execute_plan")
    assert execute_tool["risk"] == "destructive"
    assert execute_tool["requires_confirmation"] is True
    assert execute_tool["auto_call_allowed"] is False
    assert "confirmation_phrase" in execute_tool["parameters"]["required"]
    assert "confirmation_token" in execute_tool["parameters"]["required"]
    assert "shell" not in json.dumps(execute_tool["parameters"])

    openai_functions = report["ai_openai_functions"]
    assert openai_functions["schema"] == "cleanmac.ai-openai-functions.v1"
    assert {tool["function"]["name"] for tool in openai_functions["tools"]} == tool_names
    assert all(tool["type"] == "function" for tool in openai_functions["tools"])

    anthropic_tools = report["ai_anthropic_tools"]
    assert anthropic_tools["schema"] == "cleanmac.ai-anthropic-tools.v1"
    assert {tool["name"] for tool in anthropic_tools["tools"]} == tool_names

    mcp_catalog = report["mcp_tool_catalog"]
    assert mcp_catalog["schema"] == "cleanmac.mcp-tool-catalog.v1"
    assert {tool["name"] for tool in mcp_catalog["tools"]} == tool_names
    assert all(tool["invocation"]["mode"] == "argv" for tool in mcp_catalog["tools"])
    assert all(tool["invocation"].get("uses_shell") is False for tool in mcp_catalog["tools"])

    provider_parity = report["ai_provider_export_parity"]
    assert provider_parity["schema"] == "cleanmac.ai-provider-export-parity.v1"
    assert provider_parity["same_tool_names"] is True
    assert provider_parity["same_tool_count"] is True
    assert provider_parity["violation_count"] == 0

    schema_validation = report["ai_schema_validation"]
    assert schema_validation["schema"] == "cleanmac.ai-schema-validation.v1"
    assert schema_validation["valid"] is True
    assert schema_validation["tool_count"] == len(tool_names)
    assert "cleanmac_execute_plan" in schema_validation["destructive_tools"]

    contract_compatibility = report["ai_contract_compatibility"]
    assert contract_compatibility["schema"] == "cleanmac.ai-contract-compatibility.v1"
    assert contract_compatibility["compatible"] is True
    assert contract_compatibility["function_tool_count"] == len(tool_names)
    assert contract_compatibility["mcp_tool_count"] == len(tool_names)


def test_provider_export_parity_reports_same_tool_names_directly() -> None:
    report = ai_schema.render_provider_export_parity()

    assert report["schema"] == "cleanmac.ai-provider-export-parity.v1"
    assert report["same_tool_names"] is True
    assert report["same_tool_count"] is True
    assert report["tool_count"] == EXPECTED_TOOL_COUNT
    assert report["function_tool_count"] == EXPECTED_TOOL_COUNT
    assert report["openai_tool_count"] == EXPECTED_TOOL_COUNT
    assert report["anthropic_tool_count"] == EXPECTED_TOOL_COUNT
    assert report["mcp_tool_count"] == EXPECTED_TOOL_COUNT
    assert report["violation_count"] == 0
    assert report["violations"] == []


def test_ai_schema_builds_safe_argv_without_shell_or_implicit_execute() -> None:
    schemas = ai_schema.render_function_schemas()
    validation = ai_schema.validate_ai_tool_definitions()
    by_name = {tool["name"]: tool for tool in schemas["tools"]}

    assert validation["schema"] == "cleanmac.ai-schema-validation.v1"
    assert validation["valid"] is True
    assert validation["violations"] == []
    assert validation["tool_count"] == len(schemas["tools"])
    assert "cleanmac_execute_plan" in validation["destructive_tools"]

    inspect_tool = by_name["cleanmac_inspect"]
    execute_tool = by_name["cleanmac_execute_plan"]
    assert inspect_tool["requires_confirmation"] is False
    assert execute_tool["requires_confirmation"] is True
    assert execute_tool["auto_call_allowed"] is False
    assert "operation_log" in execute_tool["parameters"]["required"]
    assert "require_plan_context" not in execute_tool["parameters"]["required"]
    assert execute_tool["parameters"]["properties"]["require_plan_context"]["default"] is True

    assert ai_schema.build_tool_argv(
        "cleanmac_generate_plan",
        {"categories": ["trash", "downloads"], "max_items": 5},
    ) == [
        "cleanmac",
        "--json",
        "clean",
        "plan",
        "--categories",
        "trash,downloads",
        "--ai-origin",
        "--max-items",
        "5",
    ]
    assert ai_schema.build_tool_argv("cleanmac_dry_run_plan", {"plan_file": "/tmp/plan.json"}) == [
        "cleanmac",
        "--json",
        "clean",
        "run",
        "--plan-file",
        "/tmp/plan.json",
        "--require-plan-context",
        "--delete-mode",
        "trash",
    ]
    assert ai_schema.build_tool_argv(
        "cleanmac_policy_simulate",
        {
            "plan_file": "/tmp/plan.json",
            "execute": True,
            "delete_mode": "trash",
            "review_selection_file": "/tmp/selection.json",
        },
    ) == [
        "cleanmac",
        "--json",
        "clean",
        "policy-simulate",
        "--plan-file",
        "/tmp/plan.json",
        "--execute",
        "--delete-mode",
        "trash",
        "--review-selection-file",
        "/tmp/selection.json",
        "--require-plan-context",
    ]

    try:
        ai_schema.build_tool_argv("cleanmac_execute_plan", {"plan_file": "/tmp/plan.json"})
    except ValueError as exc:
        assert "requires explicit user confirmation" in str(exc)
    else:  # pragma: no cover - pytest assertion guard
        raise AssertionError("cleanmac_execute_plan accepted missing confirmation")

    execute_argv = ai_schema.build_tool_argv(
        "cleanmac_execute_plan",
        {
            "plan_file": "/tmp/plan.json",
            "confirmation_phrase": ai_schema.CONFIRMATION_PHRASE,
            "confirmation_token": "cleanmac-confirm-test",
            "operation_log": "/tmp/cleanmac-operations.jsonl",
        },
    )
    assert execute_argv == [
        "cleanmac",
        "--json",
        "clean",
        "run",
        "--plan-file",
        "/tmp/plan.json",
        "--require-plan-context",
        "--delete-mode",
        "trash",
        "--execute",
        "--yes",
        "--operation-log",
        "/tmp/cleanmac-operations.jsonl",
        "--require-confirmation-token",
        "--confirmation-token",
        "cleanmac-confirm-test",
    ]
    assert all(part not in {"sh", "bash", "zsh", "-c", "shell"} for part in execute_argv)
    assert "--execute" not in ai_schema.build_tool_argv("cleanmac_generate_plan", {"categories": ["trash"]})

    try:
        ai_schema.build_tool_argv("shell", {"command": "rm -rf /"})
    except ValueError as exc:
        assert "Unknown cleanmac AI tool" in str(exc)
    else:  # pragma: no cover - pytest assertion guard
        raise AssertionError("unknown shell tool was accepted")


def test_ai_schema_registry_covers_public_ai_schemas() -> None:
    registry = ai_versioning.render_ai_schema_registry()
    names = {entry["name"] for entry in registry["entries"]}
    entries = {entry["name"]: entry for entry in registry["entries"]}

    assert registry["schema"] == "cleanmac.ai-schema-registry.v1"
    assert registry["entry_count"] >= 20
    assert registry["latest_plan_schema"] == "cleanmac.plan.v1"
    assert "cleanmac.ai-readiness.v1" in names
    assert "cleanmac.ai-trace.v1" in names
    assert "cleanmac.capabilities.v1" in names
    assert "cleanmac.runtime-lifecycle-policy.v1" in names
    assert entries["cleanmac.plan.v1"]["producer"] == "clean plan"
    assert "json_schema" in entries["cleanmac.plan.v1"]
    assert entries["cleanmac.plan.v1"]["json_schema"]["properties"]["schema"]["const"] == "cleanmac.plan.v1"
