"""Release readiness evidence aggregation for cleanmac."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any


def _passed_bool(payload: Mapping[str, Any], *keys: str) -> bool:
    return all(bool(payload.get(key)) for key in keys)


def render_release_readiness(
    *,
    ai_host_integration_pack: Mapping[str, Any],
    ai_host_preflight: Mapping[str, Any],
    ai_host_evidence: Mapping[str, Any],
    contract_validation: Mapping[str, Any],
    eval_smoke: Mapping[str, Any],
    release_manifest: Mapping[str, Any],
    required_make_targets: Sequence[str],
) -> dict[str, Any]:
    gates = [
        {
            "id": "ai-host-integration-pack-ready",
            "passed": _passed_bool(ai_host_integration_pack, "ready"),
            "evidence_schema": ai_host_integration_pack.get("schema"),
        },
        {
            "id": "ai-host-preflight-ready",
            "passed": _passed_bool(ai_host_preflight, "ready"),
            "evidence_schema": ai_host_preflight.get("schema"),
        },
        {
            "id": "ai-host-evidence-ready",
            "passed": _passed_bool(ai_host_evidence, "ready"),
            "evidence_schema": ai_host_evidence.get("schema"),
        },
        {
            "id": "contract-validation-ready",
            "passed": _passed_bool(contract_validation, "ready", "valid"),
            "evidence_schema": contract_validation.get("schema"),
        },
        {
            "id": "ai-eval-smoke-passed",
            "passed": bool(eval_smoke.get("passed") and int(eval_smoke.get("failed_count") or 0) == 0),
            "evidence_schema": eval_smoke.get("schema"),
        },
        {
            "id": "release-artifact-manifest-valid",
            "passed": bool(release_manifest.get("valid") is True),
            "evidence_schema": release_manifest.get("schema"),
        },
        {
            "id": "required-make-targets-present",
            "passed": all(bool(target) for target in required_make_targets),
            "evidence_schema": "Makefile",
        },
    ]
    failed_gate_ids = [gate["id"] for gate in gates if not gate["passed"]]
    passed_count = len(gates) - len(failed_gate_ids)
    release_gate_commands = [["make", target] for target in required_make_targets]
    return {
        "schema": "cleanmac.release-readiness.v1",
        "destructive": False,
        "dry_run": True,
        "ready": not failed_gate_ids,
        "manual_review_required": bool(failed_gate_ids),
        "readiness_score": {
            "passed": passed_count,
            "total": len(gates),
            "level": "release-ready" if not failed_gate_ids else "blocked",
        },
        "failed_gate_ids": failed_gate_ids,
        "gates": gates,
        "release_gate_commands": release_gate_commands,
        "review_questions": [
            "Did ai-host-preflight pass before tool orchestration?",
            "Did ai-host-evidence include runtime denial samples?",
            "Did governed-execution-smoke pass after startup/privacy executor changes?",
            "Did release artifacts include manifest, SHA256SUMS, SBOM, and Homebrew formula evidence?",
        ],
    }
