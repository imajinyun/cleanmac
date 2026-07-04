from __future__ import annotations

from pathlib import Path

from cleancli import runtime_contracts


def test_pyproject_parsers_extract_lists_and_optional_groups() -> None:
    text = """
[build-system]
requires = ["setuptools>=68", "wheel"]

[project]
dependencies = []

[project.optional-dependencies]
test = ["pytest>=8", "coverage>=7"]
lint = ["ruff>=0.8"]
"""

    assert runtime_contracts.pyproject_list_value(text, "requires") == ["setuptools>=68", "wheel"]
    assert runtime_contracts.pyproject_list_value(text, "dependencies") == []
    assert runtime_contracts.pyproject_optional_dependency_groups(text) == {
        "test": ["pytest>=8", "coverage>=7"],
        "lint": ["ruff>=0.8"],
    }


def test_render_cold_start_budget_contract_is_ready() -> None:
    report = runtime_contracts.render_cold_start_budget_contract()

    assert report["schema"] == "cleanmac.cold-start-budget.v1"
    assert report["destructive"] is False
    assert report["dry_run"] is True
    assert report["ready"] is True
    assert report["budgets"]["resident_processes_after_exit"] == 0
    assert report["validation"]["valid"] is True


def test_render_dependency_governance_contract_is_ready() -> None:
    report = runtime_contracts.render_dependency_governance_contract(
        project_root=Path(__file__).resolve().parents[1],
        product_surface_policy=lambda: {
            "schema": "cleanmac.product-surface-policy.v1",
            "forbidden_dependency_families": ["Textual"],
            "release_gate_command": "python3 scripts/security_scan.py",
        },
    )

    assert report["schema"] == "cleanmac.dependency-governance.v1"
    assert report["destructive"] is False
    assert report["dry_run"] is True
    assert report["ready"] is True
    assert report["resource_uri"] == "cleanmac://release/dependency-governance"
    assert report["pyproject"]["runtime_dependency_count"] == 0
    assert report["validation"]["valid"] is True
