from __future__ import annotations

import contextlib
import io
import json
import tempfile
from pathlib import Path
from unittest.mock import patch

import cleancli.core as cleancli
from cleancli.release_artifacts import build_release_artifact_manifest


def run_main_json(*args: str) -> dict[str, object]:
    stdout = io.StringIO()
    with contextlib.redirect_stdout(stdout):
        exit_code = cleancli.main(["--json", *args])

    assert exit_code == 0, stdout.getvalue()
    return json.loads(stdout.getvalue())


def test_core_main_ai_dispatches_are_covered_in_process() -> None:
    commands = [
        (("list",), "cleanmac.category-list.v1"),
        (("capabilities",), "cleanmac.capabilities.v1"),
        (("completion", "bash"), "cleanmac.completion-script.v1"),
        (("ai-tools",), "cleanmac.ai-tools.v1"),
        (("ai-tools", "--format", "openai"), "cleanmac.ai-openai-functions.v1"),
        (("ai-tools", "--format", "anthropic"), "cleanmac.ai-anthropic-tools.v1"),
        (("ai-tools", "--format", "mcp"), "cleanmac.mcp-tool-catalog.v1"),
        (("ai-readiness",), "cleanmac.ai-readiness.v1"),
        (("ai-runbook",), "cleanmac.ai-runbook.v1"),
        (("ai-self-test",), "cleanmac.ai-self-test.v1"),
        (("ai-decision-matrix",), "cleanmac.ai-tool-decision-matrix.v1"),
        (("ai-governance-advice",), "cleanmac.ai-governance-advice.v1"),
        (("ai-host-policy",), "cleanmac.ai-host-policy.v1"),
        (("ai-host-integration-pack",), "cleanmac.ai-host-integration-pack.v1"),
        (("ai-host-preflight",), "cleanmac.ai-host-preflight.v1"),
        (("governance-integrity",), "cleanmac.governance-integrity.v1"),
        (("zero-resident",), "cleanmac.zero-resident.v1"),
        (("product-surface-drift-audit",), "cleanmac.product-surface-drift-audit.v1"),
        (("ai-first-release-checklist",), "cleanmac.ai-first-release-checklist.v1"),
        (("ai-schema-registry",), "cleanmac.ai-schema-registry.v1"),
        (("release-readiness",), "cleanmac.release-readiness.v1"),
        (("release-diagnostics",), "cleanmac.release-diagnostics.v1"),
        (("release-evidence",), "cleanmac.release-evidence.v1"),
        (("release-operator-summary",), "cleanmac.release-operator-summary.v1"),
        (("release-rehearsal",), "cleanmac.release-rehearsal.v1"),
        (("release-promotion-decision",), "cleanmac.release-promotion-decision.v1"),
        (("release-rollback-plan",), "cleanmac.release-rollback-plan.v1"),
        (("release-post-publish-verification",), "cleanmac.release-post-publish-verification.v1"),
        (("release-post-publish-result",), "cleanmac.release-post-publish-result.v1"),
        (("release-post-publish-evidence-template",), "cleanmac.release-post-publish-evidence-template.v1"),
        (("ai-contract-samples",), "cleanmac.ai-contract-samples.v1"),
        (("ai-eval-pack",), "cleanmac.ai-eval-pack.v1"),
    ]

    for args, expected_schema in commands:
        assert run_main_json(*args)["schema"] == expected_schema, args


def test_core_main_release_readiness_dispatches_in_process() -> None:
    release_readiness = run_main_json("release-readiness")

    assert release_readiness["destructive"] is False
    assert release_readiness["dry_run"] is True
    gate_ids = {gate["id"] for gate in release_readiness["gates"]}
    assert "ai-first-release-checklist-ready" in gate_ids
    assert "governance-integrity-ready" in gate_ids
    assert ["make", "ai-first-release-checklist-smoke"] in release_readiness["release_gate_commands"]
    assert ["make", "governance-integrity-smoke"] in release_readiness["release_gate_commands"]
    assert ["make", "governed-execution-smoke"] in release_readiness["release_gate_commands"]
    assert "release-artifact-manifest-valid" in release_readiness["failed_gate_ids"]

    governance_integrity = run_main_json("governance-integrity")
    assert governance_integrity["ready"], governance_integrity
    assert governance_integrity["failed_check_ids"] == []
    assert governance_integrity["stop_reason"] == ""
    assert ["make", "governance-integrity-smoke"] in governance_integrity["remediation_commands"]
    assert "cleanmac.geo-discoverability-policy.v1" in governance_integrity["governed_contracts"]

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        dist = root / "dist"
        assets = root / "release-assets"
        dist.mkdir()
        assets.mkdir()
        (dist / "cleanmac-0.1.0-py3-none-any.whl").write_text("wheel", encoding="utf-8")
        (dist / "cleanmac-0.1.0.tar.gz").write_text("sdist", encoding="utf-8")
        (assets / "SBOM.json").write_text("{}", encoding="utf-8")
        (assets / "cleanmac.rb").write_text("class Cleanmac < Formula\nend\n", encoding="utf-8")
        manifest = build_release_artifact_manifest(dist_dir=dist, assets_dir=assets)
        (assets / "ARTIFACT-MANIFEST.json").write_text(
            json.dumps(manifest, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )

        explicit_readiness = run_main_json("release-readiness", "--dist-dir", str(dist), "--assets-dir", str(assets))

    assert explicit_readiness["ready"], explicit_readiness
    assert explicit_readiness["failed_gate_ids"] == []
    assert explicit_readiness["readiness_score"] == {"passed": 13, "total": 13, "level": "release-ready"}


def test_core_main_contract_validation_and_eval_run_dispatches_in_process() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        payload_file = Path(tmp) / "payload.json"
        payload_file.write_text(
            json.dumps(
                {
                    "schema": "cleanmac.ai-contract-samples.v1",
                    "destructive": False,
                    "dry_run": True,
                    "sample_count": 0,
                    "samples": [],
                }
            ),
            encoding="utf-8",
        )
        validation = run_main_json(
            "ai-validate-contract",
            "--schema",
            "cleanmac.ai-contract-samples.v1",
            "--payload-file",
            str(payload_file),
        )

    assert validation["valid"], validation

    eval_report = {
        "schema": "cleanmac.ai-eval-run.v1",
        "scenario": "contract_samples_roundtrip",
        "passed": True,
        "passed_count": 1,
        "failed_count": 0,
        "results": [],
        "trace": {"schema": "cleanmac.ai-trace.v1", "event_count": 0},
        "trace_persistence": {"status": "skipped", "path": None},
    }
    with patch("cleancli.core.render_ai_eval_run", return_value=eval_report):
        assert run_main_json("ai-eval-run", "--scenario", "contract_samples_roundtrip") == eval_report
