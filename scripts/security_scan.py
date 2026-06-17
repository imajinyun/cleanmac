#!/usr/bin/env python3
"""Static governance scan for destructive and privileged command ownership."""

from __future__ import annotations

import argparse
import ast
from pathlib import Path

IGNORED_DIRS = {
    ".git",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    "build",
    "dist",
    "__pycache__",
    "cleanmac.egg-info",
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


def literal_command_name(node: ast.AST) -> str | None:
    if isinstance(node, ast.List | ast.Tuple) and node.elts:
        first = node.elts[0]
        if isinstance(first, ast.Constant) and isinstance(first.value, str):
            return first.value
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
        violations.extend(scan_text_file(root, path))
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
