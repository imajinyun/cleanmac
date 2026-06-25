from __future__ import annotations

import importlib
from types import ModuleType

import pytest

PUBLIC_MODULES = [
    "cleancli",
    "cleancli.cli",
    "cleancli.core",
    "cleancli.delete_ops",
    "cleancli.protection",
    "cleancli.protection_data",
    "cleancli.clean",
    "cleancli.analyze",
    "cleancli.categories",
    "cleancli.finder",
    "cleancli.governance",
    "cleancli.models",
    "cleancli.optimize",
    "cleancli.paths",
    "cleancli.reports",
    "cleancli.scripts",
    "cleancli.software",
    "cleancli.status",
    "cleancli.workflow",
    "cleancli.ai_schema",
]


@pytest.mark.parametrize("module_name", PUBLIC_MODULES)
def test_public_cleancli_module_imports(module_name: str) -> None:
    module = importlib.import_module(module_name)

    assert isinstance(module, ModuleType)


def test_public_main_entrypoints_delegate_to_cli_main() -> None:
    cleancli = importlib.import_module("cleancli")
    cleancli_cli = importlib.import_module("cleancli.cli")
    cleanmac = importlib.import_module("cleanmac")

    assert cleancli.main is cleancli_cli.main
    assert cleanmac.main is cleancli_cli.main


def test_workflow_public_helpers_remain_callable() -> None:
    workflow = importlib.import_module("cleancli.workflow")

    assert callable(workflow.workflow_automation_playbook)
    assert callable(workflow.workflow_iteration_status)
