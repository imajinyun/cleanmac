from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import Any

READONLY_RISKS = {"readonly", "planning", "dry-run"}


def mcp_annotations_for_tool(tool: Mapping[str, Any]) -> dict[str, bool]:
    risk = str(tool.get("risk") or "")
    destructive = risk == "destructive"
    return {
        "readOnlyHint": risk in READONLY_RISKS,
        "destructiveHint": destructive,
        "idempotentHint": not destructive,
        "openWorldHint": False,
    }


def _phase_by_tool(runbook: Mapping[str, Any]) -> dict[str, str]:
    phase_by_tool: dict[str, str] = {}
    for phase in runbook.get("phases", []):
        if not isinstance(phase, Mapping):
            continue
        phase_id = str(phase.get("id") or "unknown")
        for tool_name in phase.get("tools", []):
            if isinstance(tool_name, str):
                phase_by_tool[tool_name] = phase_id
    return phase_by_tool


def _required_predecessor_tools(name: str, runbook: Mapping[str, Any]) -> list[str]:
    if name != str(runbook.get("execution_gate", {}).get("destructive_tool") or ""):
        return []
    return [
        str(tool_name)
        for tool_name in runbook.get("execution_gate", {}).get("required_before_execute", [])
        if isinstance(tool_name, str) and tool_name.startswith("cleanmac_")
    ]


def render_ai_tool_decision_matrix(
    tool_definitions: Iterable[Mapping[str, Any]],
    runbook: Mapping[str, Any],
) -> dict[str, Any]:
    phase_by_tool = _phase_by_tool(runbook)
    tools: list[dict[str, Any]] = []
    violations: list[str] = []

    for tool in tool_definitions:
        name = str(tool.get("name") or "")
        risk = str(tool.get("risk") or "")
        auto_call_allowed = bool(tool.get("auto_call_allowed"))
        requires_confirmation = bool(tool.get("requires_confirmation"))
        annotations = mcp_annotations_for_tool(tool)
        phase = phase_by_tool.get(name, "out_of_band")

        if risk == "destructive" and auto_call_allowed:
            violations.append(f"{name}: destructive tool cannot be auto-callable")
        if risk == "destructive" and not requires_confirmation:
            violations.append(f"{name}: destructive tool must require confirmation")
        if risk == "destructive" and annotations["readOnlyHint"]:
            violations.append(f"{name}: destructive tool cannot be readOnlyHint")
        if risk != "destructive" and annotations["destructiveHint"]:
            violations.append(f"{name}: non-destructive tool cannot be destructiveHint")

        tools.append(
            {
                "name": name,
                "risk": risk,
                "phase": phase,
                "auto_call_allowed": auto_call_allowed,
                "requires_human_confirmation": requires_confirmation,
                "required_predecessor_tools": _required_predecessor_tools(name, runbook),
                "mcp_annotations": annotations,
                "on_success": {
                    "host_action": "continue_runbook" if auto_call_allowed else "await_human_review",
                },
                "on_error": {
                    "host_action": "stop_and_show_structured_error",
                    "retry_without_human": risk in {"readonly", "planning", "dry-run"},
                },
            }
        )

    return {
        "schema": "cleanmac.ai-tool-decision-matrix.v1",
        "default_execution_policy": "dry-run-first",
        "uses_shell": False,
        "tool_count": len(tools),
        "tools": tools,
        "violation_count": len(violations),
        "violations": violations,
    }
