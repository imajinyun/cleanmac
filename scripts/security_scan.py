#!/usr/bin/env python3
"""Static governance scan for destructive, privileged, and resident product surfaces."""

from __future__ import annotations

import argparse
import ast
import shlex
from pathlib import Path

IGNORED_DIRS = {
    ".git",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    ".venv",
    "build",
    "dist",
    "__pycache__",
    "cleanmac.egg-info",
    "venv",
}
TEXT_ALLOWLIST = {
    "AGENTS.md",
    "Makefile",
    "README.md",
    "README.CN.md",
    ".github/workflows/ci.yml",
    "test_cleanmac.py",
    "cleancli/core.py",
    "scripts/test.sh",
    "scripts/security_scan.py",
    "tests/test_script_governance.py",
}
ALLOWED_RM_RF_FRAGMENTS = (
    "trap 'rm -rf",
    "cleanmac test blocked rm -rf style command",
    '"rm -rf /"',
    "rm -rf as a forbidden command pattern",
    "unsafe delete patterns",
    "raw rm -rf is forbidden",
    "raw rm -rf templates",
    "raw-rm-forbidden",
    "ALLOWED_RM_RF_FRAGMENTS",
    'if "rm -rf" in line',
    'and "rm -rf" in command',
    'assertNotIn("rm -rf"',
    '"command": "rm -rf /tmp/example"',
    '"rm -rf" not in command',
    "if needle ==",
)
ALLOWED_RMTREE_FRAGMENTS = (
    "shutil.rmtree(",
    "shutil.rmtree must stay in cleancli/delete_ops.py",
    '"shutil.rmtree(" in text',
    '"shutil.rmtree(" in line',
)
PRIVILEGED_COMMANDS = {"sudo", "osascript", "launchctl"}
PRIVILEGED_BOUNDARY_MODULES = {Path("cleancli/delete_ops.py")}
PRIVILEGED_TEST_ALLOWLIST = {"test_cleanmac.py", "tests/test_sudo_guard.py", "tests/test_delete_ops.py"}
SHELL_ALLOWLIST = {Path("scripts/test.sh")}
SHELL_SUFFIXES = {".sh", ".bash", ".zsh"}
WORKFLOW_PARTS = (".github", "workflows")
FORBIDDEN_PRODUCT_SURFACE_IMPORTS = {
    "curses": "TUI framework",
    "urwid": "TUI framework",
    "textual": "TUI framework",
    "prompt_toolkit": "TUI framework",
    "tkinter": "GUI framework",
    "PyQt5": "GUI framework",
    "PyQt6": "GUI framework",
    "PySide2": "GUI framework",
    "PySide6": "GUI framework",
    "rumps": "menu bar app framework",
    "toga": "GUI framework",
    "wx": "GUI framework",
}
FORBIDDEN_PRODUCT_SURFACE_DEPENDENCIES = {
    "electron": "GUI runtime",
    "textual": "TUI framework",
    "prompt_toolkit": "TUI framework",
    "urwid": "TUI framework",
    "pyqt": "GUI framework",
    "pyside": "GUI framework",
    "rumps": "menu bar app framework",
}
AUTOSTART_CONFIG_PARTS = {"LaunchAgents", "LaunchDaemons", "LoginItems"}
LAUNCH_PLIST_KEYS = {"KeepAlive", "RunAtLoad", "ProgramArguments", "LimitLoadToSessionType"}


def iter_repo_files(root: Path) -> list[Path]:
    return [
        path
        for path in root.rglob("*")
        if path.is_file() and not any(part in IGNORED_DIRS for part in path.relative_to(root).parts)
    ]


def line_allowed(relative: Path, line: str, fragments: tuple[str, ...]) -> bool:
    return str(relative) in TEXT_ALLOWLIST and any(fragment in line for fragment in fragments)


def scan_text_file(root: Path, path: Path) -> list[str]:
    relative = path.relative_to(root)
    try:
        text = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return []
    violations: list[str] = []
    for line_number, line in enumerate(text.splitlines(), start=1):
        if "rm -rf" in line and not line_allowed(relative, line, ALLOWED_RM_RF_FRAGMENTS):
            violations.append(f"{relative}:{line_number}: raw rm -rf is forbidden")
        if "shutil.rmtree(" in line and relative != Path("cleancli/delete_ops.py"):
            if "test" not in str(relative) and not line_allowed(relative, line, ALLOWED_RMTREE_FRAGMENTS):
                violations.append(f"{relative}:{line_number}: shutil.rmtree must stay in cleancli/delete_ops.py")
    return violations


def dependency_surface_candidate(relative: Path) -> bool:
    name = relative.name.lower()
    return (
        name in {"pyproject.toml", "setup.cfg", "setup.py", "requirements.txt", "requirements-dev.txt"}
        or name.endswith(".in")
        or is_workflow_file(relative)
        or relative.suffix in SHELL_SUFFIXES
    )


def scan_product_surface_text(root: Path, path: Path) -> list[str]:
    relative = path.relative_to(root)
    violations: list[str] = []
    if any(part in AUTOSTART_CONFIG_PARTS for part in relative.parts):
        violations.append(f"{relative}: autostart product surface is forbidden for cleanmac")
    try:
        text = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return violations
    if relative.suffix == ".plist" and any(key in text for key in LAUNCH_PLIST_KEYS):
        violations.append(f"{relative}: LaunchAgent/LaunchDaemon plist is forbidden for cleanmac")
    if not dependency_surface_candidate(relative):
        return violations
    folded = text.lower()
    for token, reason in sorted(FORBIDDEN_PRODUCT_SURFACE_DEPENDENCIES.items()):
        if token in folded:
            violations.append(f"{relative}: forbidden {reason} dependency '{token}'")
    return violations


def normalized_command_name(command: str) -> str:
    return Path(command).name


def shell_tokens(line: str) -> list[str]:
    try:
        return shlex.split(line, comments=True, posix=True)
    except ValueError:
        return []


def is_shell_command_separator(token: str) -> bool:
    return token in {"&&", "||", ";", "|"}


def shell_command_names(line: str) -> set[str]:
    names: set[str] = set()
    expecting_command = True
    for token in shell_tokens(line):
        if is_shell_command_separator(token):
            expecting_command = True
            continue
        if "=" in token and not token.startswith(("/", "./", "../")) and token.split("=", 1)[0].isidentifier():
            continue
        if expecting_command:
            names.add(normalized_command_name(token))
            expecting_command = False
        elif normalized_command_name(token) in PRIVILEGED_COMMANDS:
            names.add(normalized_command_name(token))
    return names


def is_workflow_file(relative: Path) -> bool:
    return len(relative.parts) >= 3 and relative.parts[:2] == WORKFLOW_PARTS and relative.suffix in {".yml", ".yaml"}


def scan_shell_file(root: Path, path: Path) -> list[str]:
    relative = path.relative_to(root)
    if relative in SHELL_ALLOWLIST:
        return []
    try:
        text = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return []
    violations: list[str] = []
    for line_number, line in enumerate(text.splitlines(), start=1):
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        for command in sorted(shell_command_names(line) & PRIVILEGED_COMMANDS):
            violations.append(f"{relative}:{line_number}: shell must not invoke privileged command '{command}'")
    return violations


def scan_workflow_file(root: Path, path: Path) -> list[str]:
    relative = path.relative_to(root)
    try:
        text = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return []
    violations: list[str] = []
    in_run_block = False
    run_indent = 0
    for line_number, line in enumerate(text.splitlines(), start=1):
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        indent = len(line) - len(line.lstrip(" "))
        if in_run_block and indent <= run_indent:
            in_run_block = False
        step_line = stripped[2:].lstrip() if stripped.startswith("- ") else stripped
        if step_line.startswith("run: |") or step_line.startswith("run: >"):
            in_run_block = True
            run_indent = indent
            continue
        command_line = (
            step_line.removeprefix("run: ") if step_line.startswith("run: ") else stripped if in_run_block else ""
        )
        if not command_line:
            continue
        for command in sorted(shell_command_names(command_line) & PRIVILEGED_COMMANDS):
            violations.append(f"{relative}:{line_number}: workflow must not invoke privileged command '{command}'")
    return violations


def literal_command_name(node: ast.AST) -> str | None:
    if isinstance(node, ast.List | ast.Tuple) and node.elts:
        first = node.elts[0]
        if isinstance(first, ast.Constant) and isinstance(first.value, str):
            return normalized_command_name(first.value)
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        for command in shell_command_names(node.value):
            if command in PRIVILEGED_COMMANDS or command == "rm":
                return command
    return None


def call_name(node: ast.AST) -> str | None:
    if isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name):
        return f"{node.value.id}.{node.attr}"
    if isinstance(node, ast.Name):
        return node.id
    return None


def scan_python_ast(root: Path, path: Path) -> list[str]:
    relative = path.relative_to(root)
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(relative))
    except (SyntaxError, UnicodeDecodeError):
        return []
    violations: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported = [alias.name.split(".", 1)[0] for alias in node.names]
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported = [node.module.split(".", 1)[0]]
        else:
            continue
        for module in imported:
            reason = FORBIDDEN_PRODUCT_SURFACE_IMPORTS.get(module)
            if reason:
                violations.append(f"{relative}:{node.lineno}: forbidden {reason} import '{module}'")
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call) or not node.args:
            continue
        name = call_name(node.func)
        if name not in {
            "subprocess.run",
            "subprocess.check_call",
            "subprocess.check_output",
            "subprocess.Popen",
            "run_text_command",
        }:
            continue
        command = literal_command_name(node.args[0])
        if command is None:
            continue
        if command == "rm" and relative != Path("cleancli/delete_ops.py") and "test" not in str(relative):
            violations.append(f"{relative}:{node.lineno}: subprocess must not directly invoke rm")
        if command in PRIVILEGED_COMMANDS:
            if relative in PRIVILEGED_BOUNDARY_MODULES or str(relative) in PRIVILEGED_TEST_ALLOWLIST:
                continue
            if relative == Path("cleancli/core.py") and name == "run_text_command" and command == "sudo":
                continue
            violations.append(
                f"{relative}:{node.lineno}: privileged command '{command}' must stay behind boundary guards"
            )
    return violations


def scan_repo(root: Path) -> list[str]:
    violations: list[str] = []
    for path in iter_repo_files(root):
        relative = path.relative_to(root)
        violations.extend(scan_text_file(root, path))
        violations.extend(scan_product_surface_text(root, path))
        if path.suffix in SHELL_SUFFIXES:
            violations.extend(scan_shell_file(root, path))
        if is_workflow_file(relative):
            violations.extend(scan_workflow_file(root, path))
        if path.suffix == ".py":
            violations.extend(scan_python_ast(root, path))
    return violations


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run cleanmac static safety governance checks.")
    parser.add_argument("--root", type=Path, default=Path.cwd())
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    violations = scan_repo(args.root.resolve(strict=False))
    if violations:
        print("\n".join(violations))
        return 1
    print("No unsafe delete or privileged command ownership violations found.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
