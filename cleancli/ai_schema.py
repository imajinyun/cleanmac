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
            ("plan_file", "confirmation_phrase", "confirmation_token", "operation_log", "require_plan_context"),
        ),
        "argv_template": [
            "cleanmac",
            "--json",
            "clean",
            "run",
            "--plan-file",
            "{plan_file}",
            "--require-plan-context",
            "--delete-mode",
            "trash",
            "--execute",
            "--yes",
            "--operation-log",
            "{operation_log}",
            "--require-confirmation-token",
            "--confirmation-token",
            "{confirmation_token}",
        ],
    },
)


REQUIRED_TOOL_FIELDS = (
    "name",
    "description",
    "risk",
    "auto_call_allowed",
    "requires_confirmation",
    "parameters",
    "argv_template",
)
ALLOWED_RISKS = {"readonly", "planning", "dry-run", "destructive"}


def tool_definition_violations(tool: Mapping[str, Any], *, seen_names: set[str]) -> list[str]:
    name = str(tool.get("name") or "<missing-name>")
    violations: list[str] = []
    for field in REQUIRED_TOOL_FIELDS:
        if field not in tool:
            violations.append(f"{name}: missing required tool field {field}")
    if not isinstance(tool.get("name"), str) or not str(tool.get("name") or "").startswith("cleanmac_"):
        violations.append(f"{name}: name must be a cleanmac_* string")
    elif name in seen_names:
        violations.append(f"{name}: duplicate tool name")
    else:
        seen_names.add(name)
    if tool.get("risk") not in ALLOWED_RISKS:
        violations.append(f"{name}: invalid risk {tool.get('risk')!r}")
    if not isinstance(tool.get("auto_call_allowed"), bool):
        violations.append(f"{name}: auto_call_allowed must be boolean")
    if not isinstance(tool.get("requires_confirmation"), bool):
        violations.append(f"{name}: requires_confirmation must be boolean")
    parameters = tool.get("parameters")
    if not isinstance(parameters, Mapping) or parameters.get("type") != "object":
        violations.append(f"{name}: parameters must be an object JSON schema")
    else:
        if parameters.get("additionalProperties") is not False:
            violations.append(f"{name}: parameters must set additionalProperties=false")
        required = parameters.get("required", [])
        properties = parameters.get("properties", {})
        if not isinstance(required, list):
            violations.append(f"{name}: parameters.required must be a list")
        if not isinstance(properties, Mapping):
            violations.append(f"{name}: parameters.properties must be an object")
        elif isinstance(required, list):
            for field in required:
                if field not in properties:
                    violations.append(f"{name}: required parameter {field} has no schema")
        if "shell" in str(parameters).lower() or "command" in parameters.get("properties", {}):
            violations.append(f"{name}: parameters must not accept shell or raw command input")
    argv_template = tool.get("argv_template")
    if not isinstance(argv_template, list) or not argv_template or argv_template[:2] != ["cleanmac", "--json"]:
        violations.append(f"{name}: argv_template must start with cleanmac --json")
    elif any(not isinstance(part, str) or not part for part in argv_template):
        violations.append(f"{name}: argv_template parts must be non-empty strings")
    if tool.get("risk") == "destructive":
        if tool.get("auto_call_allowed") is not False:
            violations.append(f"{name}: destructive tools must not be auto-callable")
        if tool.get("requires_confirmation") is not True:
            violations.append(f"{name}: destructive tools must require confirmation")
    elif tool.get("requires_confirmation") is True and tool.get("auto_call_allowed") is True:
        violations.append(f"{name}: confirmation-required tools must not be auto-callable")
    return violations


def representative_args(name: str) -> dict[str, Any]:
    if name in {"cleanmac_capabilities", "cleanmac_doctor", "cleanmac_status_snapshot", "cleanmac_list_categories"}:
        return {}
    if name == "cleanmac_diagnose":
        return {"categories": ["trash"], "log_threshold_mb": 100, "large_threshold_mb": 1024}
    if name == "cleanmac_inspect":
        return {"categories": ["trash"], "limit": 10}
    if name == "cleanmac_analyze_tree":
        return {"path": "~", "depth": 2, "top": 10}
    if name == "cleanmac_generate_plan":
        return {"categories": ["trash"], "max_items": 10, "max_delete_mb": 5}
    if name in {"cleanmac_validate_plan", "cleanmac_dry_run_plan"}:
        return {"plan_file": "/tmp/cleanmac-plan.json"}
    if name == "cleanmac_execute_plan":
        return {
            "plan_file": "/tmp/cleanmac-plan.json",
            "confirmation_phrase": CONFIRMATION_PHRASE,
            "confirmation_token": "cleanmac-confirm-test",
            "operation_log": DEFAULT_OPERATION_LOG,
            "require_plan_context": True,
        }
    return {}


def validate_ai_tool_definitions() -> dict[str, Any]:
    violations: list[str] = []
    seen_names: set[str] = set()
    destructive_tools: list[str] = []
    auto_call_tools: list[str] = []
    for tool in AI_TOOL_DEFINITIONS:
        name = str(tool.get("name") or "<missing-name>")
        violations.extend(tool_definition_violations(tool, seen_names=seen_names))
        if tool.get("risk") == "destructive":
            destructive_tools.append(name)
        if tool.get("auto_call_allowed") is True:
            auto_call_tools.append(name)
        try:
            argv = build_tool_argv(name, representative_args(name))
        except Exception as exc:
            violations.append(f"{name}: representative argv build failed: {exc}")
            continue
        if not argv or argv[:2] != ["cleanmac", "--json"]:
            violations.append(f"{name}: built argv must start with cleanmac --json")
        if any(part in {"sh", "bash", "zsh", "-c", "shell"} for part in argv):
            violations.append(f"{name}: built argv contains shell execution tokens")
        if tool.get("risk") != "destructive" and "--execute" in argv:
            violations.append(f"{name}: non-destructive tool argv must not include --execute")
    function_tool_names = {tool["name"] for tool in render_function_schemas()["tools"]}
    mcp_tool_names = {tool["name"] for tool in render_mcp_tool_catalog()["tools"]}
    definition_names = {str(tool.get("name")) for tool in AI_TOOL_DEFINITIONS}
    if function_tool_names != definition_names:
        violations.append("function schemas do not match AI_TOOL_DEFINITIONS")
    if mcp_tool_names != definition_names:
        violations.append("MCP tool catalog does not match AI_TOOL_DEFINITIONS")
    return {
        "schema": "cleanmac.ai-schema-validation.v1",
        "valid": not violations,
        "tool_count": len(AI_TOOL_DEFINITIONS),
        "auto_call_tool_count": len(auto_call_tools),
        "destructive_tools": destructive_tools,
        "auto_call_tools": auto_call_tools,
        "violation_count": len(violations),
        "violations": violations,
    }


def render_contract_compatibility(contract: Mapping[str, Any]) -> dict[str, Any]:
    function_schemas = render_function_schemas()
    mcp_catalog = render_mcp_tool_catalog()
    function_tools = {tool["name"]: tool for tool in function_schemas["tools"]}
    mcp_tools = {tool["name"]: tool for tool in mcp_catalog["tools"]}
    violations: list[str] = []
    if set(function_tools) != set(mcp_tools):
        violations.append("function schema tool names differ from MCP tool names")
    if contract.get("default_invocation", {}).get("json_required") is not True:
        violations.append("AI contract must require JSON invocation")
    if contract.get("execution_requirements", {}).get("confirmation_token_supported") is not True:
        violations.append("AI contract must advertise confirmation token support")
    for name, tool in function_tools.items():
        mcp_tool = mcp_tools.get(name)
        if not mcp_tool:
            continue
        if tool["parameters"] != mcp_tool["inputSchema"]:
            violations.append(f"{name}: function parameters differ from MCP inputSchema")
        invocation = mcp_tool.get("invocation", {})
        if invocation.get("mode") != "argv" or invocation.get("uses_shell") is not False:
            violations.append(f"{name}: MCP invocation must be argv-only without shell")
    execute_tool = function_tools.get("cleanmac_execute_plan", {})
    execute_required = set(execute_tool.get("parameters", {}).get("required", []))
    for field in {"plan_file", "confirmation_phrase", "confirmation_token", "operation_log", "require_plan_context"}:
        if field not in execute_required:
            violations.append(f"cleanmac_execute_plan: missing required parameter {field}")
    execute_mcp = mcp_tools.get("cleanmac_execute_plan", {})
    execute_argv = execute_mcp.get("invocation", {}).get("argv_template", [])
    if "--execute" not in execute_argv:
        violations.append("cleanmac_execute_plan MCP template must include --execute")
    if execute_tool.get("auto_call_allowed") is not False or execute_tool.get("requires_confirmation") is not True:
        violations.append("cleanmac_execute_plan must be manual confirmation only")
    return {
        "schema": "cleanmac.ai-contract-compatibility.v1",
        "compatible": not violations,
        "function_schema": function_schemas["schema"],
        "mcp_catalog_schema": mcp_catalog["schema"],
        "contract_schema": contract.get("schema"),
        "function_tool_count": len(function_tools),
        "mcp_tool_count": len(mcp_tools),
        "violation_count": len(violations),
        "violations": violations,
    }


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
        argv = [
            "cleanmac",
            "--json",
            "clean",
            "plan",
            "--categories",
            categories_arg(args.get("categories")),
            "--ai-origin",
        ]
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
        return [
            "cleanmac",
            "--json",
            "clean",
            "run",
            "--plan-file",
            plan_file,
            "--require-plan-context",
            "--delete-mode",
            "trash",
        ]
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
