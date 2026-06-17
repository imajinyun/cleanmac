"""Machine-readable AI tool schemas for safe cleanmac integrations."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

DEFAULT_OPERATION_LOG = "~/.cleanmac/operations.jsonl"
CONFIRMATION_PHRASE = "确认执行 cleanmac 清理"


def string_schema(description: str) -> dict[str, Any]:
    return {"type": "string", "description": description}


def number_schema(description: str) -> dict[str, Any]:
    return {"type": "number", "description": description}


def integer_schema(description: str) -> dict[str, Any]:
    return {"type": "integer", "description": description}


def category_array_schema() -> dict[str, Any]:
    return {
        "type": "array",
        "items": {"type": "string"},
        "description": "cleanmac category keys selected from capabilities/list output.",
        "minItems": 1,
    }


def bool_schema(description: str) -> dict[str, Any]:
    return {"type": "boolean", "description": description}


def object_schema(properties: dict[str, Any], required: Sequence[str] = ()) -> dict[str, Any]:
    return {
        "type": "object",
        "properties": properties,
        "required": list(required),
        "additionalProperties": False,
    }


AI_TOOL_DEFINITIONS: tuple[dict[str, Any], ...] = (
    {
        "name": "cleanmac_capabilities",
        "description": "Describe cleanmac commands, categories, safety guardrails, and AI integration contracts.",
        "risk": "readonly",
        "auto_call_allowed": True,
        "requires_confirmation": False,
        "parameters": object_schema({}),
        "argv_template": ["cleanmac", "--json", "capabilities"],
    },
    {
        "name": "cleanmac_doctor",
        "description": "Run non-destructive environment and permission diagnostics.",
        "risk": "readonly",
        "auto_call_allowed": True,
        "requires_confirmation": False,
        "parameters": object_schema({}),
        "argv_template": ["cleanmac", "--json", "doctor"],
    },
    {
        "name": "cleanmac_status_snapshot",
        "description": "Return a read-only system health snapshot.",
        "risk": "readonly",
        "auto_call_allowed": True,
        "requires_confirmation": False,
        "parameters": object_schema({}),
        "argv_template": ["cleanmac", "--json", "status", "snapshot"],
    },
    {
        "name": "cleanmac_list_categories",
        "description": "List cleanmac cleanup categories and metadata.",
        "risk": "readonly",
        "auto_call_allowed": True,
        "requires_confirmation": False,
        "parameters": object_schema({}),
        "argv_template": ["cleanmac", "--json", "clean", "list"],
    },
    {
        "name": "cleanmac_diagnose",
        "description": "Analyze categories and emit non-destructive cleanup recommendations.",
        "risk": "readonly",
        "auto_call_allowed": True,
        "requires_confirmation": False,
        "parameters": object_schema(
            {
                "categories": category_array_schema(),
                "log_threshold_mb": integer_schema("Log warning threshold in MiB."),
                "large_threshold_mb": integer_schema("Large category warning threshold in MiB."),
            }
        ),
        "argv_template": ["cleanmac", "--json", "diagnose"],
    },
    {
        "name": "cleanmac_inspect",
        "description": "Preview cleanup candidates without deleting files.",
        "risk": "readonly",
        "auto_call_allowed": True,
        "requires_confirmation": False,
        "parameters": object_schema(
            {
                "categories": category_array_schema(),
                "limit": integer_schema("Maximum number of candidates to show."),
                "min_size_mb": integer_schema("Minimum candidate size in MiB."),
                "older_than_days": number_schema("Only show candidates older than this many days."),
                "include": string_schema("Optional glob include filter."),
                "exclude": string_schema("Optional glob exclude filter."),
                "name_regex": string_schema("Optional regular expression matched against candidate names."),
            },
            required=("categories",),
        ),
        "argv_template": ["cleanmac", "--json", "clean", "inspect"],
    },
    {
        "name": "cleanmac_analyze_tree",
        "description": "Scan a directory tree and report largest entries without deleting files.",
        "risk": "readonly",
        "auto_call_allowed": True,
        "requires_confirmation": False,
        "parameters": object_schema(
            {
                "path": string_schema("Directory to scan."),
                "depth": integer_schema("Maximum traversal depth."),
                "top": integer_schema("Maximum entries to show."),
                "min_size_mb": integer_schema("Minimum entry size in MiB."),
            }
        ),
        "argv_template": ["cleanmac", "--json", "analyze", "tree"],
    },
    {
        "name": "cleanmac_generate_plan",
        "description": "Generate a reusable non-destructive cleanup plan.",
        "risk": "planning",
        "auto_call_allowed": True,
        "requires_confirmation": False,
        "parameters": object_schema(
            {
                "categories": category_array_schema(),
                "risk_policy": {"type": "string", "enum": ["strict", "default", "permissive"]},
                "max_delete_mb": number_schema("Maximum planned delete budget in MiB."),
                "max_items": integer_schema("Maximum planned candidate count."),
                "min_size_mb": integer_schema("Minimum candidate size in MiB."),
                "older_than_days": number_schema("Only plan candidates older than this many days."),
                "include": string_schema("Optional glob include filter."),
                "exclude": string_schema("Optional glob exclude filter."),
                "name_regex": string_schema("Optional regular expression matched against candidate names."),
            },
            required=("categories",),
        ),
        "argv_template": ["cleanmac", "--json", "clean", "plan"],
    },
    {
        "name": "cleanmac_validate_plan",
        "description": "Validate a cleanmac cleanup plan before dry-run or execution.",
        "risk": "planning",
        "auto_call_allowed": True,
        "requires_confirmation": False,
        "parameters": object_schema({"plan_file": string_schema("Path to a cleanmac plan JSON file.")}, ("plan_file",)),
        "argv_template": ["cleanmac", "--json", "clean", "validate-plan"],
    },
    {
        "name": "cleanmac_dry_run_plan",
        "description": "Run a cleanup plan in dry-run mode with Trash routing selected for the eventual execution path.",
        "risk": "dry-run",
        "auto_call_allowed": True,
        "requires_confirmation": False,
        "parameters": object_schema({"plan_file": string_schema("Path to a cleanmac plan JSON file.")}, ("plan_file",)),
        "argv_template": ["cleanmac", "--json", "clean", "run"],
    },
    {
        "name": "cleanmac_execute_plan",
        "description": "Execute a validated cleanup plan. This is destructive and requires explicit user confirmation.",
        "risk": "destructive",
        "auto_call_allowed": False,
        "requires_confirmation": True,
        "parameters": object_schema(
            {
                "plan_file": string_schema("Path to a cleanmac plan JSON file."),
                "confirmation_phrase": string_schema(f"Must exactly equal: {CONFIRMATION_PHRASE}"),
                "confirmation_token": string_schema(
                    "Token generated by a matching cleanmac dry-run ai_confirmation_summary."
                ),
                "operation_log": string_schema("JSONL operation log path."),
                "require_plan_context": bool_schema("Require root/home context match before execution."),
            },
            ("plan_file", "confirmation_phrase", "confirmation_token"),
        ),
        "argv_template": ["cleanmac", "--json", "clean", "run"],
    },
)


def tool_by_name(name: str) -> dict[str, Any]:
    for tool in AI_TOOL_DEFINITIONS:
        if tool["name"] == name:
            return tool
    raise ValueError(f"Unknown cleanmac AI tool: {name}")


def render_function_schemas() -> dict[str, Any]:
    return {
        "schema": "cleanmac.ai-function-schemas.v1",
        "description": "JSON Schema function definitions for LLM tool calling. No schema accepts arbitrary shell commands.",
        "tools": [
            {
                "name": tool["name"],
                "description": tool["description"],
                "risk": tool["risk"],
                "auto_call_allowed": tool["auto_call_allowed"],
                "requires_confirmation": tool["requires_confirmation"],
                "parameters": tool["parameters"],
            }
            for tool in AI_TOOL_DEFINITIONS
        ],
    }


def render_mcp_tool_catalog() -> dict[str, Any]:
    return {
        "schema": "cleanmac.mcp-tool-catalog.v1",
        "description": "MCP-compatible tool metadata; hosts should execute argv directly without shell expansion.",
        "tools": [
            {
                "name": tool["name"],
                "description": tool["description"],
                "risk": tool["risk"],
                "auto_call_allowed": tool["auto_call_allowed"],
                "requires_confirmation": tool["requires_confirmation"],
                "inputSchema": tool["parameters"],
                "invocation": {
                    "mode": "argv",
                    "uses_shell": False,
                    "argv_template": tool["argv_template"],
                },
            }
            for tool in AI_TOOL_DEFINITIONS
        ],
    }


def categories_arg(value: object) -> str:
    if not isinstance(value, list) or not value or not all(isinstance(item, str) and item for item in value):
        raise ValueError("categories must be a non-empty list of strings")
    return ",".join(value)


def append_option(argv: list[str], args: Mapping[str, Any], key: str, flag: str) -> None:
    value = args.get(key)
    if value is None:
        return
    argv.extend([flag, str(value)])


def build_tool_argv(name: str, args: Mapping[str, Any] | None = None) -> list[str]:
    args = {} if args is None else dict(args)
    tool_by_name(name)
    if name == "cleanmac_capabilities":
        return ["cleanmac", "--json", "capabilities"]
    if name == "cleanmac_doctor":
        return ["cleanmac", "--json", "doctor"]
    if name == "cleanmac_status_snapshot":
        return ["cleanmac", "--json", "status", "snapshot"]
    if name == "cleanmac_list_categories":
        return ["cleanmac", "--json", "clean", "list"]
    if name == "cleanmac_diagnose":
        argv = ["cleanmac", "--json", "diagnose"]
        if "categories" in args:
            argv.extend(["--categories", categories_arg(args["categories"])])
        append_option(argv, args, "log_threshold_mb", "--log-threshold-mb")
        append_option(argv, args, "large_threshold_mb", "--large-threshold-mb")
        return argv
    if name == "cleanmac_inspect":
        argv = ["cleanmac", "--json", "clean", "inspect", "--categories", categories_arg(args.get("categories"))]
        append_option(argv, args, "limit", "--limit")
        append_option(argv, args, "min_size_mb", "--min-size-mb")
        append_option(argv, args, "older_than_days", "--older-than-days")
        append_option(argv, args, "include", "--include")
        append_option(argv, args, "exclude", "--exclude")
        append_option(argv, args, "name_regex", "--name-regex")
        return argv
    if name == "cleanmac_analyze_tree":
        argv = ["cleanmac", "--json", "analyze", "tree"]
        append_option(argv, args, "path", "--path")
        append_option(argv, args, "depth", "--depth")
        append_option(argv, args, "top", "--top")
        append_option(argv, args, "min_size_mb", "--min-size-mb")
        return argv
    if name == "cleanmac_generate_plan":
        argv = ["cleanmac", "--json", "clean", "plan", "--categories", categories_arg(args.get("categories"))]
        append_option(argv, args, "risk_policy", "--risk-policy")
        append_option(argv, args, "max_delete_mb", "--max-delete-mb")
        append_option(argv, args, "max_items", "--max-items")
        append_option(argv, args, "min_size_mb", "--min-size-mb")
        append_option(argv, args, "older_than_days", "--older-than-days")
        append_option(argv, args, "include", "--include")
        append_option(argv, args, "exclude", "--exclude")
        append_option(argv, args, "name_regex", "--name-regex")
        return argv
    if name == "cleanmac_validate_plan":
        plan_file = str(args.get("plan_file") or "")
        if not plan_file:
            raise ValueError("plan_file is required")
        return ["cleanmac", "--json", "clean", "validate-plan", "--plan-file", plan_file]
    if name == "cleanmac_dry_run_plan":
        plan_file = str(args.get("plan_file") or "")
        if not plan_file:
            raise ValueError("plan_file is required")
        return ["cleanmac", "--json", "clean", "run", "--plan-file", plan_file, "--delete-mode", "trash"]
    if name == "cleanmac_execute_plan":
        if args.get("confirmation_phrase") != CONFIRMATION_PHRASE:
            raise ValueError("cleanmac_execute_plan requires explicit user confirmation phrase")
        confirmation_token = str(args.get("confirmation_token") or "")
        if not confirmation_token:
            raise ValueError("cleanmac_execute_plan requires a dry-run confirmation token")
        plan_file = str(args.get("plan_file") or "")
        if not plan_file:
            raise ValueError("plan_file is required")
        operation_log = str(args.get("operation_log") or DEFAULT_OPERATION_LOG)
        argv = ["cleanmac", "--json", "clean", "run", "--plan-file", plan_file]
        if args.get("require_plan_context", True):
            argv.append("--require-plan-context")
        argv.extend(["--delete-mode", "trash", "--execute", "--yes", "--operation-log", operation_log])
        argv.extend(["--require-confirmation-token", "--confirmation-token", confirmation_token])
        return argv
    raise ValueError(f"Unknown cleanmac AI tool: {name}")
