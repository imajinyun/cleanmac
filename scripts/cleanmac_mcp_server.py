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

CLEANMAC_CLI: list[str] | None = None


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
    sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
    from cleancli.ai_schema import AI_TOOL_DEFINITIONS  # type: ignore[import-untyped]

    return list(AI_TOOL_DEFINITIONS)


def tool_to_mcp(tool: dict) -> dict:
    """Convert an AI_TOOL_DEFINITION entry to MCP tool format."""
    return {
        "name": tool["name"],
        "description": tool["description"],
        "inputSchema": tool["parameters"],
    }


def execute_tool(tool: dict, arguments: dict) -> str:
    """Execute a cleanmac tool by building argv and running the CLI."""
    global CLEANMAC_CLI
    if CLEANMAC_CLI is None:
        CLEANMAC_CLI = find_cleanmac()

    from cleancli.ai_schema import build_tool_argv  # type: ignore[import-untyped]

    name = tool["name"]
    try:
        argv = build_tool_argv(name, arguments)
    except (ValueError, KeyError) as exc:
        raise RuntimeError(f"Failed to build argv for {name}: {exc}") from exc

    cmd = CLEANMAC_CLI + argv[1:] if CLEANMAC_CLI[0].endswith(".py") else CLEANMAC_CLI + argv[1:]

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=120,
        )
    except subprocess.TimeoutExpired as exc:
        raise RuntimeError(f"Tool {name} timed out after 120s") from exc
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
    method = request.get("method", "")
    req_id = request.get("id")

    if method == "initialize":
        tools = get_tool_definitions()
        response = {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {
                "protocolVersion": "2024-11-05",
                "capabilities": {
                    "tools": {},
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
            return (
                {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "result": {
                        "content": [{"type": "text", "text": output}],
                        "isError": False,
                    },
                },
                [],
            )
        except RuntimeError as exc:
            return (
                {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "result": {
                        "content": [{"type": "text", "text": str(exc)}],
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
