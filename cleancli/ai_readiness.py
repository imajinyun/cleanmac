from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from cleancli import ai_schema


def render_ai_readiness(contract: Mapping[str, Any]) -> dict[str, Any]:
    schema_validation = ai_schema.validate_ai_tool_definitions()
    compatibility = ai_schema.render_contract_compatibility(contract)
    provider_parity = ai_schema.render_provider_export_parity()
    return {
        "schema": "cleanmac.ai-readiness.v1",
        "ready": bool(
            schema_validation["valid"]
            and compatibility["compatible"]
            and provider_parity["same_tool_names"]
            and provider_parity["same_tool_count"]
        ),
        "tool_count": provider_parity["tool_count"],
        "provider_exports": {
            "function_tool_count": provider_parity["function_tool_count"],
            "openai_tool_count": provider_parity["openai_tool_count"],
            "anthropic_tool_count": provider_parity["anthropic_tool_count"],
            "mcp_tool_count": provider_parity["mcp_tool_count"],
            "same_tool_names": provider_parity["same_tool_names"],
            "same_tool_count": provider_parity["same_tool_count"],
        },
        "contracts": {
            "schema_validation": schema_validation,
            "contract_compatibility": compatibility,
            "provider_export_parity": provider_parity,
        },
        "mcp": {
            "transport": "stdio",
            "server_command": ["cleanmac-mcp"],
            "script_command": ["python3", "scripts/cleanmac_mcp_server.py"],
            "uses_shell": False,
            "resources_supported": True,
            "prompts_supported": True,
            "structured_content_supported": True,
        },
        "recommended_starting_tools": [
            "cleanmac_capabilities",
            "cleanmac_list_categories",
            "cleanmac_workflow",
        ],
        "mandatory_before_execute": [
            "cleanmac_generate_plan",
            "cleanmac_validate_plan",
            "cleanmac_policy_simulate",
            "cleanmac_dry_run_plan",
            "human_confirmation",
        ],
    }
