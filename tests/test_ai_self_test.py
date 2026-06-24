from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from cleancli.ai_self_test import render_ai_self_test
from cleancli.core import render_ai_self_test as render_core_ai_self_test

PROJECT_ROOT = Path(__file__).resolve().parent.parent
CLI = PROJECT_ROOT / "cleanmac.py"


def test_ai_self_test_is_owned_outside_core_and_reexported() -> None:
    report = render_ai_self_test()

    assert report == render_core_ai_self_test()
    assert report["schema"] == "cleanmac.ai-self-test.v1"
    assert report["passed"], report


def test_ai_self_test_reports_all_checks_passed() -> None:
    result = subprocess.run(
        [sys.executable, str(CLI), "--json", "ai-self-test"],
        text=True,
        capture_output=True,
        check=True,
    )
    report = json.loads(result.stdout)

    assert report["schema"] == "cleanmac.ai-self-test.v1"
    assert report["passed"], report
    check_ids = {check["id"] for check in report["checks"]}
    assert "schema-validation" in check_ids
    assert "contract-compatibility" in check_ids
    assert "provider-export-parity" in check_ids
    assert "runbook-execution-gate" in check_ids
    assert "runtime-lifecycle-policy" in check_ids
    assert "tool-decision-matrix" in check_ids
    assert "ai-eval-pack" in check_ids
    assert "ai-governance-advice" in check_ids
    assert "ai-host-policy" in check_ids
    assert "contract-validation-smoke" in check_ids
    assert "mcp-transport" in check_ids
    checks = {check["id"]: check for check in report["checks"]}
    assert checks["tool-decision-matrix"]["passed"]
    assert checks["tool-decision-matrix"]["detail"]["violation_count"] == 0
    assert checks["runtime-lifecycle-policy"]["passed"]
    assert checks["runtime-lifecycle-policy"]["detail"]["schema"] == "cleanmac.runtime-lifecycle-policy.v1"
    assert checks["runtime-lifecycle-policy"]["detail"]["resident_processes"] == 0
    assert checks["ai-eval-pack"]["passed"]
    assert checks["ai-eval-pack"]["detail"]["schema"] == "cleanmac.ai-eval-pack.v1"
    assert checks["ai-governance-advice"]["passed"]
    assert checks["ai-governance-advice"]["detail"]["schema"] == "cleanmac.ai-governance-advice.v1"
    assert checks["ai-host-policy"]["passed"]
    assert checks["ai-host-policy"]["detail"]["schema"] == "cleanmac.ai-host-policy.v1"
    assert checks["contract-validation-smoke"]["passed"]
    assert checks["contract-validation-smoke"]["detail"]["schema"] == "cleanmac.ai-contract-validation-summary.v1"
    coverage = checks["contract-validation-smoke"]["detail"]["contract_schema_coverage"]
    assert "cleanmac.ai-eval-run.v1" in coverage["critical_schemas"]
    assert coverage["missing_stable_ai_schema_fragments"] == []
    assert all(check["passed"] for check in report["checks"]), report["checks"]
