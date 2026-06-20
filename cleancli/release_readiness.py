"""Release readiness evidence aggregation for cleanmac."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any


def _passed_bool(payload: Mapping[str, Any], *keys: str) -> bool:
    return all(bool(payload.get(key)) for key in keys)


def _evidence_ref(payload: Mapping[str, Any], *, producer: str) -> dict[str, Any]:
    ref: dict[str, Any] = {"producer": producer}
    if payload.get("path"):
        ref["path"] = payload["path"]
    if payload.get("dist_dir"):
        ref["dist_dir"] = payload["dist_dir"]
    if payload.get("assets_dir"):
        ref["assets_dir"] = payload["assets_dir"]
    return ref


def _gate(
    *,
    gate_id: str,
    passed: bool,
    evidence_schema: Any,
    evidence_ref: Mapping[str, Any],
    diagnostic: str,
    blocking_code: str,
    next_actions: Sequence[Sequence[str]],
) -> dict[str, Any]:
    gate = {
        "id": gate_id,
        "passed": passed,
        "severity": "none" if passed else "blocking",
        "evidence_schema": str(evidence_schema or "unknown"),
        "evidence_ref": dict(evidence_ref),
        "diagnostic": "passed" if passed else diagnostic,
        "next_actions": [list(action) for action in next_actions],
    }
    if not passed:
        gate["blocking_code"] = blocking_code
    return gate


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
    release_manifest_valid = bool(release_manifest.get("valid") is True)
    release_manifest_error_code = str(
        release_manifest.get("error_code")
        or (
            "RELEASE_ARTIFACT_MANIFEST_INVALID" if release_manifest.get("path") else "RELEASE_ARTIFACT_MANIFEST_MISSING"
        )
    )
    gates = [
        _gate(
            gate_id="ai-host-integration-pack-ready",
            passed=_passed_bool(ai_host_integration_pack, "ready"),
            evidence_schema=ai_host_integration_pack.get("schema"),
            evidence_ref={"producer": "cleanmac --json ai-host-integration-pack"},
            diagnostic="AI Host integration pack is not ready for release review.",
            blocking_code="AI_HOST_INTEGRATION_PACK_NOT_READY",
            next_actions=[["make", "ai-host-smoke"]],
        ),
        _gate(
            gate_id="ai-host-preflight-ready",
            passed=_passed_bool(ai_host_preflight, "ready"),
            evidence_schema=ai_host_preflight.get("schema"),
            evidence_ref={"producer": "cleanmac --json ai-host-preflight"},
            diagnostic="AI Host runtime preflight failed.",
            blocking_code="AI_HOST_PREFLIGHT_NOT_READY",
            next_actions=[["make", "ai-host-smoke"]],
        ),
        _gate(
            gate_id="ai-host-evidence-ready",
            passed=_passed_bool(ai_host_evidence, "ready"),
            evidence_schema=ai_host_evidence.get("schema"),
            evidence_ref={"producer": "cleanmac --json ai-host-evidence"},
            diagnostic="AI Host evidence pack is incomplete.",
            blocking_code="AI_HOST_EVIDENCE_NOT_READY",
            next_actions=[["make", "ai-host-smoke"], ["make", "mcp-smoke"]],
        ),
        _gate(
            gate_id="contract-validation-ready",
            passed=_passed_bool(contract_validation, "ready", "valid"),
            evidence_schema=contract_validation.get("schema"),
            evidence_ref={"producer": "cleanmac --json ai-readiness"},
            diagnostic="AI contract validation is not passing.",
            blocking_code="AI_CONTRACT_VALIDATION_NOT_READY",
            next_actions=[["make", "ai-contract-smoke"]],
        ),
        _gate(
            gate_id="ai-eval-smoke-passed",
            passed=bool(eval_smoke.get("passed") and int(eval_smoke.get("failed_count") or 0) == 0),
            evidence_schema=eval_smoke.get("schema"),
            evidence_ref={"producer": "cleanmac --json ai-eval-run --scenario smoke"},
            diagnostic="AI eval smoke did not pass cleanly.",
            blocking_code="AI_EVAL_SMOKE_FAILED",
            next_actions=[["make", "ai-host-smoke"], ["cleanmac", "--json", "ai-eval-run", "--scenario", "smoke"]],
        ),
        _gate(
            gate_id="release-artifact-manifest-valid",
            passed=release_manifest_valid,
            evidence_schema=release_manifest.get("schema"),
            evidence_ref=_evidence_ref(release_manifest, producer="scripts/generate_release_manifest.py"),
            diagnostic=str(release_manifest.get("error") or "Release artifact manifest is invalid."),
            blocking_code=release_manifest_error_code,
            next_actions=[["make", "release-artifacts-smoke"], ["make", "release-readiness-smoke"]],
        ),
        _gate(
            gate_id="required-make-targets-present",
            passed=all(bool(target) for target in required_make_targets),
            evidence_schema="Makefile",
            evidence_ref={"path": "Makefile", "producer": "release-check target"},
            diagnostic="One or more required release make targets are missing.",
            blocking_code="REQUIRED_MAKE_TARGETS_MISSING",
            next_actions=[["make", "release-check"]],
        ),
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
