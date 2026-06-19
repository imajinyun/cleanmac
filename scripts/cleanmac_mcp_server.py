#!/usr/bin/env python3
"""cleanmac MCP (Model Context Protocol) stdio server.

Serves AI_TOOL_DEFINITIONS as MCP tools via stdio transport.
Usage:
    python3 scripts/cleanmac_mcp_server.py

MCP clients (e.g. Claude Desktop) can connect with:
    python3 /path/to/cleanmac/scripts/cleanmac_mcp_server.py
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

CLEANMAC_CLI: list[str] | None = None


def ensure_project_root_on_path() -> None:
    """Ensure cleancli imports work when running this script directly."""
    project_root = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
    if project_root not in sys.path:
        sys.path.insert(0, project_root)


def find_cleanmac() -> list[str]:
    """Locate the cleanmac CLI entry point."""
    # 1. Check CLEANMAC_CLI env var
    env_path = os.environ.get("CLEANMAC_CLI")
    if env_path:
        return [env_path]

    # 2. Check alongside this script
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.abspath(os.path.join(script_dir, ".."))
    cli_candidates = [
        os.path.join(project_root, "cleanmac.py"),
        os.path.join(project_root, "cleanmac"),
    ]
    for candidate in cli_candidates:
        if os.path.isfile(candidate):
            return [sys.executable, candidate]

    # 3. Check PATH
    import shutil

    path_cli = shutil.which("cleanmac")
    if path_cli:
        return [path_cli]

    return [sys.executable, "cleanmac.py"]


def get_tool_definitions() -> list[dict]:
    """Import AI_TOOL_DEFINITIONS from cleancli.ai_schema."""
    ensure_project_root_on_path()
    from cleancli.ai_schema import AI_TOOL_DEFINITIONS  # type: ignore[import-untyped]

    return list(AI_TOOL_DEFINITIONS)


def tool_to_mcp(tool: dict) -> dict:
    """Convert an AI_TOOL_DEFINITION entry to MCP tool format."""
    from cleancli.ai_decision import mcp_annotations_for_tool  # type: ignore[import-untyped]

    return {
        "name": tool["name"],
        "description": tool["description"],
        "annotations": mcp_annotations_for_tool(tool),
        "inputSchema": tool["parameters"],
    }


def parse_json_output(output: str) -> dict | None:
    try:
        parsed = json.loads(output)
    except json.JSONDecodeError:
        return None
    if isinstance(parsed, dict):
        return parsed
    return {"items": parsed}


def structured_error(tool_name: str, message: str) -> dict:
    parsed = parse_json_output(message)
    lower_message = message.lower()
    missing_or_invalid_arguments: list[str] = []
    if "categories" in lower_message:
        missing_or_invalid_arguments.append("categories")
    if "plan_file" in lower_message or "plan-file" in lower_message:
        missing_or_invalid_arguments.append("plan_file")
    if "confirmation_token" in lower_message or "confirmation-token" in lower_message:
        missing_or_invalid_arguments.append("confirmation_token")

    argument_error = bool(missing_or_invalid_arguments or "failed to build argv" in lower_message)
    return {
        "schema": "cleanmac.mcp-tool-error.v1",
        "tool": tool_name,
        "message": message,
        "parsed_error": parsed,
        "host_action": "fix_arguments_and_retry" if argument_error else "stop_and_show_structured_error",
        "missing_or_invalid_arguments": missing_or_invalid_arguments,
        "retryable": argument_error,
        "safe_to_auto_retry": False,
    }


def resolve_tool_timeout() -> float:
    raw = os.environ.get("CLEANMAC_MCP_TOOL_TIMEOUT")
    if not raw:
        return 120.0
    try:
        value = float(raw)
    except ValueError:
        return 120.0
    return value if value > 0 else 120.0


def mcp_resources() -> list[dict]:
    return [
        {
            "uri": "cleanmac://capabilities",
            "name": "cleanmac capabilities",
            "description": "Full cleanmac capability and AI governance report.",
            "mimeType": "application/json",
        },
        {
            "uri": "cleanmac://ai/function-schemas",
            "name": "cleanmac function schemas",
            "description": "JSON Schema function definitions for LLM tool calling.",
            "mimeType": "application/json",
        },
        {
            "uri": "cleanmac://ai/mcp-tool-catalog",
            "name": "cleanmac MCP tool catalog",
            "description": "MCP-compatible tool metadata and argv templates.",
            "mimeType": "application/json",
        },
        {
            "uri": "cleanmac://ai/readiness",
            "name": "cleanmac AI readiness",
            "description": "AI host readiness report with provider parity and integration status.",
            "mimeType": "application/json",
        },
        {
            "uri": "cleanmac://ai/runbook",
            "name": "cleanmac AI runbook",
            "description": "Ordered safe workflow phases and execution gate for AI hosts.",
            "mimeType": "application/json",
        },
        {
            "uri": "cleanmac://ai/self-test",
            "name": "cleanmac AI self-test",
            "description": "Machine-readable AI host integration self-check report.",
            "mimeType": "application/json",
        },
        {
            "uri": "cleanmac://ai/tool-decision-matrix",
            "name": "cleanmac AI tool decision matrix",
            "description": "Per-tool AI Host decision metadata, MCP annotations, phase, and recovery guidance.",
            "mimeType": "application/json",
        },
        {
            "uri": "cleanmac://ai/governance-advice",
            "name": "cleanmac AI governance advice",
            "description": "Governance recommendations for safe large-model cleanmac tool calling.",
            "mimeType": "application/json",
        },
        {
            "uri": "cleanmac://ai/host-policy",
            "name": "cleanmac AI host policy",
            "description": "Machine-readable allow/deny policy for AI Host cleanmac tool calling.",
            "mimeType": "application/json",
        },
        {
            "uri": "cleanmac://ai/schema-registry",
            "name": "cleanmac AI schema registry",
            "description": "Inventory of cleanmac.*.v* schemas with stability and compatibility policy.",
            "mimeType": "application/json",
        },
        {
            "uri": "cleanmac://ai/contract-validation",
            "name": "cleanmac AI contract validation",
            "description": "Self-validation report for cleanmac AI/MCP machine-readable contracts.",
            "mimeType": "application/json",
        },
        {
            "uri": "cleanmac://ai/contract-samples",
            "name": "cleanmac AI contract samples",
            "description": "Sample payloads for critical cleanmac AI/MCP machine-readable contracts.",
            "mimeType": "application/json",
        },
        {
            "uri": "cleanmac://ai/eval-pack",
            "name": "cleanmac AI eval pack",
            "description": "Static AI Host integration scenarios and expected safety assertions.",
            "mimeType": "application/json",
        },
        {
            "uri": "cleanmac://ai/eval-run-smoke",
            "name": "cleanmac AI eval smoke run",
            "description": "Safe sandbox replay result for the smoke AI Host integration scenarios.",
            "mimeType": "application/json",
        },
    ]


def read_mcp_resource(uri: str) -> dict:
    ensure_project_root_on_path()
    from cleancli import ai_schema  # type: ignore[import-untyped]
    from cleancli.ai_readiness import render_ai_readiness  # type: ignore[import-untyped]
    from cleancli.ai_runbook import render_ai_runbook  # type: ignore[import-untyped]
    from cleancli.ai_versioning import (  # type: ignore[import-untyped]
        render_ai_contract_samples,
        render_ai_contract_validation_summary,
        render_ai_schema_registry,
    )
    from cleancli.core import (  # type: ignore[import-untyped]
        render_ai_decision_matrix,
        render_ai_eval_pack,
        render_ai_eval_run,
        render_ai_governance_advice_report,
        render_ai_host_policy_report,
        render_ai_self_test,
        render_ai_tool_contract,
        render_capabilities,
    )

    if uri == "cleanmac://capabilities":
        payload = render_capabilities()
    elif uri == "cleanmac://ai/function-schemas":
        payload = ai_schema.render_function_schemas()
    elif uri == "cleanmac://ai/mcp-tool-catalog":
        payload = ai_schema.render_mcp_tool_catalog()
    elif uri == "cleanmac://ai/readiness":
        payload = render_ai_readiness(render_ai_tool_contract())
    elif uri == "cleanmac://ai/runbook":
        payload = render_ai_runbook()
    elif uri == "cleanmac://ai/self-test":
        payload = render_ai_self_test()
    elif uri == "cleanmac://ai/tool-decision-matrix":
        payload = render_ai_decision_matrix()
    elif uri == "cleanmac://ai/governance-advice":
        payload = render_ai_governance_advice_report()
    elif uri == "cleanmac://ai/host-policy":
        payload = render_ai_host_policy_report()
    elif uri == "cleanmac://ai/schema-registry":
        payload = render_ai_schema_registry()
    elif uri == "cleanmac://ai/contract-validation":
        payload = render_ai_contract_validation_summary()
    elif uri == "cleanmac://ai/contract-samples":
        payload = render_ai_contract_samples()
    elif uri == "cleanmac://ai/eval-pack":
        payload = render_ai_eval_pack()
    elif uri == "cleanmac://ai/eval-run-smoke":
        payload = render_ai_eval_run(scenario="smoke", cli=Path(__file__).resolve().parent.parent / "cleanmac.py")
    else:
        raise ValueError(f"Unknown resource URI: {uri}")
    return {
        "uri": uri,
        "mimeType": "application/json",
        "text": json.dumps(payload, indent=2, ensure_ascii=False),
    }


def mcp_prompts() -> list[dict]:
    return [
        {
            "name": "safe-cleanup-review",
            "description": "Inspect and plan cleanup without executing deletion.",
            "arguments": [
                {
                    "name": "categories",
                    "description": "Comma-separated cleanup category keys to inspect and plan.",
                    "required": True,
                }
            ],
        },
        {
            "name": "confirm-execution-gate",
            "description": "Prepare a human-facing checklist before destructive execution.",
            "arguments": [
                {
                    "name": "plan_file",
                    "description": "Path to the cleanmac plan JSON file that would be executed.",
                    "required": True,
                }
            ],
        },
        {
            "name": "explain-tool-decision",
            "description": "Explain whether an AI host may call a cleanmac tool and why.",
            "arguments": [
                {
                    "name": "tool_name",
                    "description": "cleanmac_* tool name to explain.",
                    "required": True,
                }
            ],
        },
        {
            "name": "review-ai-governance",
            "description": "Summarize governance advice before an AI Host calls cleanmac tools.",
            "arguments": [],
        },
        {
            "name": "review-ai-host-policy",
            "description": "Summarize the AI Host allow/deny policy before tool orchestration.",
            "arguments": [],
        },
        {
            "name": "run-ai-eval-smoke",
            "description": "Guide an AI Host through the safe cleanmac integration smoke evaluation.",
            "arguments": [],
        },
    ]


def get_mcp_prompt(name: str, arguments: dict) -> dict:
    if name == "safe-cleanup-review":
        categories = str(arguments.get("categories") or "trash")
        return {
            "description": "Safe cleanmac cleanup review workflow",
            "messages": [
                {
                    "role": "user",
                    "content": {
                        "type": "text",
                        "text": (
                            "Use cleanmac safely. Start with cleanmac_capabilities, inspect categories "
                            f"{categories}, generate an AI-originated plan, validate it, simulate policy, "
                            "and never call cleanmac_execute_plan without explicit human confirmation."
                        ),
                    },
                }
            ],
        }
    if name == "confirm-execution-gate":
        plan_file = str(arguments.get("plan_file") or "")
        return {
            "description": "Human confirmation gate before cleanmac execution",
            "messages": [
                {
                    "role": "user",
                    "content": {
                        "type": "text",
                        "text": (
                            "Before any destructive cleanmac execution for plan "
                            f"{plan_file}, call cleanmac_validate_plan, cleanmac_policy_simulate "
                            "with execute=true, and cleanmac_dry_run_plan. Show the human the "
                            "candidate count, total bytes, delete mode, operation log path, and "
                            "ai_confirmation_summary.confirmation_token. Only call cleanmac_execute_plan "
                            "after the human explicitly provides the required confirmation phrase and token."
                        ),
                    },
                }
            ],
        }
    if name == "explain-tool-decision":
        tool_name = str(arguments.get("tool_name") or "cleanmac_capabilities")
        return {
            "description": "Explain cleanmac AI tool decision metadata",
            "messages": [
                {
                    "role": "user",
                    "content": {
                        "type": "text",
                        "text": (
                            "Read cleanmac://ai/tool-decision-matrix and explain whether an AI host "
                            f"may call {tool_name}. Include risk, runbook phase, MCP annotations, "
                            "required predecessor tools, on_error host action, and the rule: "
                            "do not auto-call destructive tools."
                        ),
                    },
                }
            ],
        }
    if name == "run-ai-eval-smoke":
        return {
            "description": "Run cleanmac AI eval smoke workflow",
            "messages": [
                {
                    "role": "user",
                    "content": {
                        "type": "text",
                        "text": (
                            "Read cleanmac://ai/eval-pack, then read cleanmac://ai/eval-run-smoke. "
                            "Summarize passed_count, failed_count, scenario ids, and trace event_count. "
                            "This evaluation is non-destructive; do not call cleanmac_execute_plan."
                        ),
                    },
                }
            ],
        }
    if name == "review-ai-governance":
        return {
            "description": "Review cleanmac AI governance advice",
            "messages": [
                {
                    "role": "user",
                    "content": {
                        "type": "text",
                        "text": (
                            "Read cleanmac://ai/governance-advice and summarize ready_for_llm_calling, "
                            "default_policy, required_host_controls, anti_patterns, and p0 recommendations. "
                            "Do not call cleanmac_execute_plan while producing this governance review."
                        ),
                    },
                }
            ],
        }
    if name == "review-ai-host-policy":
        return {
            "description": "Review cleanmac AI Host allow/deny policy",
            "messages": [
                {
                    "role": "user",
                    "content": {
                        "type": "text",
                        "text": (
                            "Read cleanmac://ai/host-policy before calling cleanmac tools. Summarize "
                            "default_decision, transport.shell_allowed, auto_call.allow, auto_call.deny, "
                            "execution_gate, prompt_injection_boundary, and error_recovery. Do not call "
                            "cleanmac_execute_plan while producing this policy review."
                        ),
                    },
                }
            ],
        }
    raise ValueError(f"Unknown prompt: {name}")


def execute_tool(tool: dict, arguments: dict) -> str:
    """Execute a cleanmac tool by building argv and running the CLI."""
    global CLEANMAC_CLI
    if CLEANMAC_CLI is None:
        CLEANMAC_CLI = find_cleanmac()

    ensure_project_root_on_path()
    from cleancli.ai_schema import build_tool_argv  # type: ignore[import-untyped]

    name = tool["name"]
    try:
        argv = build_tool_argv(name, arguments)
    except (ValueError, KeyError) as exc:
        raise RuntimeError(f"Failed to build argv for {name}: {exc}") from exc

    cmd = CLEANMAC_CLI + argv[1:] if CLEANMAC_CLI[0].endswith(".py") else CLEANMAC_CLI + argv[1:]

    try:
        timeout_seconds = resolve_tool_timeout()
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
        )
    except subprocess.TimeoutExpired as exc:
        raise RuntimeError(f"Tool {name} timed out after {resolve_tool_timeout()}s") from exc
    except FileNotFoundError as exc:
        raise RuntimeError(f"cleanmac CLI not found: {exc}") from exc

    if result.returncode != 0 and result.stderr:
        # Parse JSON error if possible
        stderr = result.stderr.strip()
        try:
            err_data = json.loads(stderr)
            return json.dumps(err_data, indent=2)
        except (json.JSONDecodeError, ValueError):
            pass
        raise RuntimeError(f"Tool {name} failed (exit {result.returncode}): {stderr}")

    return result.stdout


def handle_request(request: dict) -> tuple[dict | None, list[dict]]:
    """Process a single JSON-RPC request.

    Returns (response, notifications) where notifications is a list of
    server-initiated messages to send after the response.
    """
    req_id = request.get("id")
    if request.get("jsonrpc") != "2.0":
        return (
            {
                "jsonrpc": "2.0",
                "id": req_id,
                "error": {
                    "code": -32600,
                    "message": "Invalid Request: missing or unsupported jsonrpc version (must be 2.0)",
                },
            },
            [],
        )
    method = request.get("method", "")

    if method == "initialize":
        tools = get_tool_definitions()
        response = {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {
                "protocolVersion": "2024-11-05",
                "capabilities": {
                    "tools": {},
                    "resources": {},
                    "prompts": {},
                },
                "serverInfo": {
                    "name": "cleanmac-mcp",
                    "version": tools[0].get("version", "0.1.0") if tools else "0.1.0",
                },
            },
        }
        # Per MCP spec (2024-11-05), the server must send
        # notifications/initialized after handling initialize.
        return response, [{"jsonrpc": "2.0", "method": "notifications/initialized"}]

    if method == "notifications/initialized":
        return None, []  # no response for notifications

    if method == "tools/list":
        tools = get_tool_definitions()
        return (
            {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {"tools": [tool_to_mcp(t) for t in tools]},
            },
            [],
        )

    if method == "resources/list":
        return (
            {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {"resources": mcp_resources()},
            },
            [],
        )

    if method == "resources/read":
        params = request.get("params", {})
        uri = str(params.get("uri", ""))
        try:
            resource = read_mcp_resource(uri)
        except ValueError as exc:
            return (
                {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "error": {"code": -32602, "message": str(exc)},
                },
                [],
            )
        return (
            {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {"contents": [resource]},
            },
            [],
        )

    if method == "prompts/list":
        return (
            {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {"prompts": mcp_prompts()},
            },
            [],
        )

    if method == "prompts/get":
        params = request.get("params", {})
        name = str(params.get("name", ""))
        arguments = params.get("arguments", {})
        if not isinstance(arguments, dict):
            arguments = {}
        try:
            prompt = get_mcp_prompt(name, arguments)
        except ValueError as exc:
            return (
                {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "error": {"code": -32602, "message": str(exc)},
                },
                [],
            )
        return (
            {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": prompt,
            },
            [],
        )

    if method == "tools/call":
        params = request.get("params", {})
        name = params.get("name", "")
        arguments = params.get("arguments", {})

        tools = get_tool_definitions()
        tool_map = {t["name"]: t for t in tools}
        tool = tool_map.get(name)
        if not tool:
            return (
                {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "error": {"code": -32602, "message": f"Unknown tool: {name}"},
                },
                [],
            )

        try:
            output = execute_tool(tool, arguments)
            result = {
                "content": [{"type": "text", "text": output}],
                "isError": False,
            }
            structured_content = parse_json_output(output)
            if structured_content is not None:
                result["structuredContent"] = structured_content
            return (
                {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "result": result,
                },
                [],
            )
        except RuntimeError as exc:
            message = str(exc)
            return (
                {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "result": {
                        "content": [{"type": "text", "text": message}],
                        "structuredContent": structured_error(str(name), message),
                        "isError": True,
                    },
                },
                [],
            )
        except Exception as exc:
            return (
                {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "error": {"code": -32603, "message": f"Internal error: {exc}"},
                },
                [],
            )

    if method == "shutdown":
        return (
            {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": None,
            },
            [],
        )

    # Unknown method
    return (
        {
            "jsonrpc": "2.0",
            "id": req_id,
            "error": {"code": -32601, "message": f"Method not found: {method}"},
        },
        [],
    )


def main() -> None:
    """Main loop: read JSON-RPC requests from stdin, write responses to stdout."""
    # Log to stderr so MCP transport stays clean
    print("cleanmac MCP server starting...", file=sys.stderr, flush=True)

    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue

        try:
            request = json.loads(line)
        except json.JSONDecodeError as exc:
            print(
                json.dumps({"jsonrpc": "2.0", "error": {"code": -32700, "message": f"Parse error: {exc}"}}),
                file=sys.stdout,
                flush=True,
            )
            continue

        try:
            response, notifications = handle_request(request)
        except Exception as exc:
            req_id = request.get("id") if isinstance(request, dict) else None
            response = {
                "jsonrpc": "2.0",
                "id": req_id,
                "error": {"code": -32603, "message": f"Unhandled error: {exc}"},
            }
            notifications = []

        if response is not None:
            print(json.dumps(response), file=sys.stdout, flush=True)

        for notification in notifications:
            print(json.dumps(notification), file=sys.stdout, flush=True)


if __name__ == "__main__":
    main()
