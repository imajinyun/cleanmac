from __future__ import annotations

import json
from typing import Any

from cleancli import ai_versioning
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
