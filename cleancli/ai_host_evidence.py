"""Auditable AI Host evidence pack for cleanmac runtime governance."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any


def _all_decisions_denied(samples: Sequence[Mapping[str, Any]]) -> bool:
    return all(
        isinstance(sample.get("decision"), Mapping) and sample["decision"].get("allowed") is False for sample in samples
    )


def _blocking_codes(samples: Sequence[Mapping[str, Any]]) -> list[str]:
    codes: set[str] = set()
    for sample in samples:
        decision = sample.get("decision", {})
        if not isinstance(decision, Mapping):
            continue
        for reason in decision.get("blocking_reasons", []):
            if isinstance(reason, Mapping) and reason.get("code"):
                codes.add(str(reason["code"]))
    return sorted(codes)


def render_ai_host_evidence(
    *,
    integration_pack: Mapping[str, Any],
    preflight: Mapping[str, Any],
    contract_validation: Mapping[str, Any],
    runtime_policy_evidence: Sequence[Mapping[str, Any]],
    critical_schemas: Sequence[str],
) -> dict[str, Any]:
    """Return a non-destructive audit evidence pack for AI Host release gates."""

    mcp = integration_pack.get("mcp", {})
    resources = mcp.get("resources", []) if isinstance(mcp, Mapping) else []
    evidence_checks = [
        {
            "id": "integration-pack-ready",
            "passed": bool(integration_pack.get("ready")),
            "evidence": "cleanmac.ai-host-integration-pack.v1",
        },
        {
            "id": "preflight-ready",
            "passed": bool(preflight.get("ready")),
            "evidence": "cleanmac.ai-host-preflight.v1",
        },
        {
            "id": "contract-validation-ready",
            "passed": bool(contract_validation.get("valid")),
            "evidence": "cleanmac.ai-contract-validation-summary.v1",
        },
        {
            "id": "runtime-denials-covered",
            "passed": _all_decisions_denied(runtime_policy_evidence),
            "evidence": "cleanmac.ai-host-tool-call-decision.v1",
        },
        {
            "id": "mcp-evidence-resource-advertised",
            "passed": "cleanmac://ai/host-evidence" in resources,
            "evidence": "cleanmac://ai/host-evidence",
        },
        {
            "id": "release-readiness-resource-advertised",
            "passed": "cleanmac://release/readiness" in resources,
            "evidence": "cleanmac://release/readiness",
        },
    ]
    return {
        "schema": "cleanmac.ai-host-evidence.v1",
        "destructive": False,
        "dry_run": True,
        "ready": all(check["passed"] for check in evidence_checks),
        "source": "cleanmac-ai-host-evidence",
        "purpose": "Auditable evidence pack for AI Host runtime governance release gates.",
        "critical_schemas": list(critical_schemas),
        "evidence_checks": evidence_checks,
        "observed_blocking_codes": _blocking_codes(runtime_policy_evidence),
        "integration_pack": {
            "schema": integration_pack.get("schema"),
            "ready": bool(integration_pack.get("ready")),
            "mcp_resource": "cleanmac://ai/host-integration-pack",
        },
        "preflight": dict(preflight),
        "contract_validation": dict(contract_validation),
        "runtime_policy_evidence": [dict(sample) for sample in runtime_policy_evidence],
        "release_gate_commands": [
            ["cleanmac", "--json", "ai-host-integration-pack"],
            ["cleanmac", "--json", "ai-host-preflight"],
            ["cleanmac", "--json", "ai-host-evidence"],
            ["cleanmac", "--json", "release-readiness"],
            ["make", "ai-contract-smoke"],
            ["make", "mcp-smoke"],
            ["make", "ai-governance-smoke"],
            ["make", "ai-host-smoke"],
            ["make", "release-readiness-smoke"],
        ],
        "review_questions": [
            "Did the host load cleanmac://ai/host-integration-pack before tool calls?",
            "Did the host run cleanmac.ai-host-preflight.v1 and stop if ready=false?",
            "Were raw command arguments denied before CLI execution?",
            "Were destructive calls denied when confirmation gates were missing?",
            "Did CI run ai-contract-smoke, mcp-smoke, ai-governance-smoke, and ai-host-smoke?",
            "Did release-readiness-smoke aggregate AI Host, contract, eval, and artifact evidence?",
        ],
    }
