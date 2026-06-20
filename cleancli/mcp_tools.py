"""Central MCP tool index and safety metadata for cleanmac AI hosts."""

from __future__ import annotations

from typing import Any

MCP_TOOL_INDEX_SCHEMA = "cleanmac.mcp-tool-index.v1"
MCP_TOOL_INDEX_URI = "cleanmac://mcp/tool-index"
MCP_TOOL_SENSITIVE_DATA_POLICY = "metadata-only-no-local-paths-no-credentials"


def _tool_row(tool: dict[str, Any]) -> dict[str, Any]:
    annotations = tool.get("annotations", {}) if isinstance(tool.get("annotations"), dict) else {}
    invocation = tool.get("invocation", {}) if isinstance(tool.get("invocation"), dict) else {}
    destructive = bool(annotations.get("destructiveHint"))
    return {
        "name": tool.get("name", ""),
        "description": tool.get("description", ""),
        "risk": tool.get("risk", ""),
        "auto_call_allowed": bool(tool.get("auto_call_allowed")),
        "requires_confirmation": bool(tool.get("requires_confirmation")),
        "destructive": destructive,
        "dry_run": not destructive,
        "safe_for_mcp": True,
        "uses_shell": bool(invocation.get("uses_shell")),
        "invocation_mode": invocation.get("mode", ""),
        "argv_template": list(invocation.get("argv_template", [])),
        "annotations": annotations,
        "inputSchema": tool.get("inputSchema", {}),
        "sensitive_data_policy": MCP_TOOL_SENSITIVE_DATA_POLICY,
    }


def mcp_tool_catalog() -> list[dict[str, Any]]:
    """Return deterministic MCP tool metadata with safety defaults."""

    from cleancli.ai_schema import render_mcp_tool_catalog

    return [_tool_row(dict(tool)) for tool in render_mcp_tool_catalog()["tools"]]


def mcp_tool_names() -> list[str]:
    return [row["name"] for row in mcp_tool_catalog()]


def validate_mcp_tool_catalog() -> dict[str, Any]:
    tools = mcp_tool_catalog()
    seen: set[str] = set()
    duplicate_names = []
    invalid_tools = []
    destructive_tool_names = []
    auto_call_denied_tool_names = []
    for tool in tools:
        name = str(tool.get("name", ""))
        if name in seen:
            duplicate_names.append(name)
        seen.add(name)
        missing = [
            key
            for key in ("name", "description", "risk", "annotations", "inputSchema", "invocation_mode", "argv_template")
            if not tool.get(key)
        ]
        if tool.get("destructive") is True:
            destructive_tool_names.append(name)
        if tool.get("auto_call_allowed") is not True:
            auto_call_denied_tool_names.append(name)
        invalid = bool(
            missing
            or tool.get("safe_for_mcp") is not True
            or tool.get("uses_shell") is not False
            or tool.get("invocation_mode") != "argv"
            or (tool.get("destructive") is True and tool.get("auto_call_allowed") is not False)
            or (tool.get("destructive") is True and tool.get("requires_confirmation") is not True)
        )
        if invalid:
            invalid_tools.append({"name": name, "missing": missing})
    return {
        "valid": not duplicate_names and not invalid_tools,
        "tool_count": len(tools),
        "duplicate_names": duplicate_names,
        "invalid_tools": invalid_tools,
        "destructive_tool_names": destructive_tool_names,
        "auto_call_denied_tool_names": auto_call_denied_tool_names,
    }


def render_mcp_tool_index() -> dict[str, Any]:
    tools = mcp_tool_catalog()
    validation = validate_mcp_tool_catalog()
    return {
        "schema": MCP_TOOL_INDEX_SCHEMA,
        "destructive": False,
        "dry_run": True,
        "ready": validation["valid"],
        "tool_count": len(tools),
        "tools": tools,
        "tool_names": [tool["name"] for tool in tools],
        "destructive_tool_names": validation["destructive_tool_names"],
        "auto_call_denied_tool_names": validation["auto_call_denied_tool_names"],
        "validation": validation,
        "sensitive_data_policy": MCP_TOOL_SENSITIVE_DATA_POLICY,
        "recommended_commands": [["make", "mcp-smoke"], ["make", "mcp-tool-index-smoke"], ["make", "ai-host-smoke"]],
    }
