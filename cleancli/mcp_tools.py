"""Central MCP tool index and safety metadata for cleanmac AI hosts."""

from __future__ import annotations

from typing import Any

MCP_TOOL_INDEX_SCHEMA = "cleanmac.mcp-tool-index.v1"
MCP_TOOL_INDEX_URI = "cleanmac://mcp/tool-index"
MCP_DESTRUCTIVE_TOOL_GOVERNANCE_SCHEMA = "cleanmac.mcp-destructive-tool-governance.v1"
MCP_DESTRUCTIVE_TOOL_GOVERNANCE_URI = "cleanmac://mcp/destructive-tool-governance"
MCP_TOOL_SENSITIVE_DATA_POLICY = "metadata-only-no-local-paths-no-credentials"
DESTRUCTIVE_TOOL_REQUIRED_FIELDS = frozenset({"confirmation_phrase", "operation_log"})


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


def _destructive_governance_row(tool: dict[str, Any]) -> dict[str, Any]:
    from cleancli.ai_schema import build_tool_argv, representative_args

    annotations = tool.get("annotations", {}) if isinstance(tool.get("annotations"), dict) else {}
    input_schema = tool.get("inputSchema", {}) if isinstance(tool.get("inputSchema"), dict) else {}
    required_fields = [str(field) for field in input_schema.get("required", []) if isinstance(field, str)]
    name = str(tool.get("name") or "")
    safe_argv_template = build_tool_argv(name, representative_args(name))
    return {
        "name": name,
        "risk": str(tool.get("risk") or ""),
        "destructive": bool(tool.get("destructive")),
        "auto_call_allowed": bool(tool.get("auto_call_allowed")),
        "requires_confirmation": bool(tool.get("requires_confirmation")),
        "requires_operation_log": "operation_log" in required_fields,
        "uses_shell": bool(tool.get("uses_shell")),
        "invocation_mode": str(tool.get("invocation_mode") or ""),
        "safe_argv_template": safe_argv_template,
        "required_input_fields": required_fields,
        "mcp_annotations": {
            "readOnlyHint": bool(annotations.get("readOnlyHint")),
            "destructiveHint": bool(annotations.get("destructiveHint")),
            "idempotentHint": bool(annotations.get("idempotentHint")),
            "openWorldHint": bool(annotations.get("openWorldHint")),
        },
        "required_runtime_gates": {
            "auto_call_denied": True,
            "human_confirmation_phrase": True,
            "explicit_operation_log": True,
            "argv_only_no_shell": True,
            "mcp_destructive_hint": True,
            "mcp_readonly_hint_forbidden": True,
        },
    }


def validate_mcp_destructive_tool_governance(report: dict[str, Any] | None = None) -> dict[str, Any]:
    payload = report or {
        "schema": MCP_DESTRUCTIVE_TOOL_GOVERNANCE_SCHEMA,
        "destructive_tools": [
            _destructive_governance_row(tool) for tool in mcp_tool_catalog() if tool.get("destructive") is True
        ],
    }
    violations: list[dict[str, Any]] = []
    destructive_tools = payload.get("destructive_tools", [])
    if payload.get("schema") != MCP_DESTRUCTIVE_TOOL_GOVERNANCE_SCHEMA:
        violations.append({"code": "INVALID_SCHEMA", "path": "$.schema"})
    if not isinstance(destructive_tools, list) or not destructive_tools:
        violations.append({"code": "NO_DESTRUCTIVE_TOOLS_INDEXED", "path": "$.destructive_tools"})
    for index, tool in enumerate(destructive_tools if isinstance(destructive_tools, list) else []):
        if not isinstance(tool, dict):
            violations.append({"code": "INVALID_TOOL_ROW", "path": f"$.destructive_tools[{index}]"})
            continue
        name = str(tool.get("name") or f"index-{index}")
        path = f"$.destructive_tools[{index}]"
        annotations = tool.get("mcp_annotations", {}) if isinstance(tool.get("mcp_annotations"), dict) else {}
        required_fields = {str(field) for field in tool.get("required_input_fields", []) if isinstance(field, str)}
        required_template_tokens = {"--execute", "--yes", "--operation-log"}
        argv_template = [str(token) for token in tool.get("safe_argv_template", [])]
        if tool.get("risk") != "destructive" or tool.get("destructive") is not True:
            violations.append({"code": "DESTRUCTIVE_RISK_REQUIRED", "tool": name, "path": path})
        if tool.get("auto_call_allowed") is not False:
            violations.append({"code": "AUTO_CALL_MUST_BE_DENIED", "tool": name, "path": f"{path}.auto_call_allowed"})
        if tool.get("requires_confirmation") is not True:
            violations.append({"code": "CONFIRMATION_REQUIRED", "tool": name, "path": f"{path}.requires_confirmation"})
        if not DESTRUCTIVE_TOOL_REQUIRED_FIELDS.issubset(required_fields):
            violations.append(
                {"code": "REQUIRED_INPUT_FIELDS_MISSING", "tool": name, "path": f"{path}.required_input_fields"}
            )
        if annotations.get("destructiveHint") is not True or annotations.get("readOnlyHint") is not False:
            violations.append({"code": "MCP_ANNOTATIONS_INVALID", "tool": name, "path": f"{path}.mcp_annotations"})
        if annotations.get("idempotentHint") is not False or annotations.get("openWorldHint") is not False:
            violations.append({"code": "MCP_SAFETY_HINTS_INVALID", "tool": name, "path": f"{path}.mcp_annotations"})
        if tool.get("uses_shell") is not False or tool.get("invocation_mode") != "argv":
            violations.append({"code": "ARGV_ONLY_REQUIRED", "tool": name, "path": path})
        if not required_template_tokens.issubset(set(argv_template)):
            violations.append({"code": "SAFE_ARGV_GATE_MISSING", "tool": name, "path": f"{path}.safe_argv_template"})
    return {
        "schema": "cleanmac.mcp-destructive-tool-governance-validation.v1",
        "valid": not violations,
        "violation_count": len(violations),
        "violations": violations,
    }


def render_mcp_destructive_tool_governance() -> dict[str, Any]:
    tools = mcp_tool_catalog()
    destructive_tools = [_destructive_governance_row(tool) for tool in tools if tool.get("destructive") is True]
    checks = [
        {
            "id": "destructive-tools-indexed",
            "passed": bool(destructive_tools),
            "evidence": MCP_TOOL_INDEX_SCHEMA,
        },
        {
            "id": "destructive-tools-auto-call-denied",
            "passed": all(tool["auto_call_allowed"] is False for tool in destructive_tools),
            "evidence": MCP_TOOL_INDEX_SCHEMA,
        },
        {
            "id": "destructive-tools-confirmation-required",
            "passed": all(tool["requires_confirmation"] is True for tool in destructive_tools),
            "evidence": MCP_TOOL_INDEX_SCHEMA,
        },
        {
            "id": "destructive-tools-operation-log-required",
            "passed": all(tool["requires_operation_log"] is True for tool in destructive_tools),
            "evidence": MCP_TOOL_INDEX_SCHEMA,
        },
        {
            "id": "destructive-tools-mcp-annotations-safe",
            "passed": all(
                tool["mcp_annotations"]["destructiveHint"] is True
                and tool["mcp_annotations"]["readOnlyHint"] is False
                and tool["mcp_annotations"]["idempotentHint"] is False
                and tool["mcp_annotations"]["openWorldHint"] is False
                for tool in destructive_tools
            ),
            "evidence": MCP_TOOL_INDEX_SCHEMA,
        },
        {
            "id": "destructive-tools-argv-only-no-shell",
            "passed": all(
                tool["uses_shell"] is False and tool["invocation_mode"] == "argv" for tool in destructive_tools
            ),
            "evidence": MCP_TOOL_INDEX_SCHEMA,
        },
    ]
    for check in checks:
        check["remediation_commands"] = [
            ["cleanmac", "--json", "mcp-destructive-tool-governance"],
            ["make", "mcp-tool-index-smoke"],
        ]
    validation = validate_mcp_destructive_tool_governance(
        {
            "schema": MCP_DESTRUCTIVE_TOOL_GOVERNANCE_SCHEMA,
            "destructive_tools": destructive_tools,
        }
    )
    ready = bool(validation["valid"] and all(check["passed"] for check in checks))
    return {
        "schema": MCP_DESTRUCTIVE_TOOL_GOVERNANCE_SCHEMA,
        "destructive": False,
        "dry_run": True,
        "ready": ready,
        "resource_uri": MCP_DESTRUCTIVE_TOOL_GOVERNANCE_URI,
        "purpose": "Machine-readable governance for every destructive cleanmac MCP tool.",
        "policy": {
            "default_decision": "deny",
            "auto_call_allowed_for_destructive_tools": False,
            "raw_command_input_allowed": False,
            "shell_allowed": False,
            "required_mcp_annotations": {
                "readOnlyHint": False,
                "destructiveHint": True,
                "idempotentHint": False,
                "openWorldHint": False,
            },
            "required_input_fields": sorted(DESTRUCTIVE_TOOL_REQUIRED_FIELDS),
            "required_argv_tokens": ["--execute", "--yes", "--operation-log"],
        },
        "destructive_tool_count": len(destructive_tools),
        "destructive_tool_names": [tool["name"] for tool in destructive_tools],
        "destructive_tools": destructive_tools,
        "checks": checks,
        "failed_check_ids": [str(check["id"]) for check in checks if not check["passed"]],
        "validation": validation,
        "readiness_score": {
            "passed": sum(1 for check in checks if check["passed"]),
            "total": len(checks),
            "level": "ready" if ready else "blocked",
        },
        "required_resources_before_execution": [
            MCP_TOOL_INDEX_URI,
            MCP_DESTRUCTIVE_TOOL_GOVERNANCE_URI,
            "cleanmac://ai/host-policy",
            "cleanmac://ai/safety-chain",
        ],
        "release_gate_commands": [
            ["cleanmac", "--json", "mcp-destructive-tool-governance"],
            ["make", "mcp-tool-index-smoke"],
            ["make", "mcp-surface-audit-smoke"],
            ["make", "ai-host-smoke"],
        ],
        "sensitive_data_policy": MCP_TOOL_SENSITIVE_DATA_POLICY,
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
