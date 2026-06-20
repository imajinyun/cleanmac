"""Release rehearsal, promotion, and rollback control-plane reports."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from cleancli.release_artifacts import HOMEBREW_FORMULA_NAME, verify_release_artifact_manifest

RELEASE_REHEARSAL_SCHEMA = "cleanmac.release-rehearsal.v1"
RELEASE_PROMOTION_DECISION_SCHEMA = "cleanmac.release-promotion-decision.v1"
RELEASE_ROLLBACK_PLAN_SCHEMA = "cleanmac.release-rollback-plan.v1"

PROMOTION_REQUIRED_ASSET_NAMES = (
    "SBOM.json",
    "SHA256SUMS",
    "ARTIFACT-MANIFEST.json",
    "RELEASE-READINESS.json",
    "RELEASE-DIAGNOSTICS.json",
    "RELEASE-REHEARSAL.json",
    "RELEASE-ROLLBACK-PLAN.json",
    HOMEBREW_FORMULA_NAME,
)


def _json_payload(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return payload if isinstance(payload, dict) else None


def _asset_status(*, assets_dir: Path, names: tuple[str, ...]) -> tuple[list[str], list[dict[str, Any]]]:
    rows = []
    missing = []
    for name in names:
        path = assets_dir / name
        present = path.is_file()
        if not present:
            missing.append(name)
        rows.append({"name": name, "path": str(path), "present": present})
    return missing, rows


def _manifest_phase(*, dist_dir: Path, assets_dir: Path) -> dict[str, Any]:
    path = assets_dir / "ARTIFACT-MANIFEST.json"
    if not path.is_file():
        return {
            "id": "artifact-manifest",
            "status": "blocked",
            "evidence_schema": "cleanmac.release-artifact-manifest.v1",
            "blocking_code": "RELEASE_ARTIFACT_MANIFEST_MISSING",
            "diagnostic": "Release artifact manifest is missing.",
            "next_actions": [["make", "release-artifacts-smoke"]],
        }
    try:
        manifest = json.loads(path.read_text(encoding="utf-8"))
        verify_release_artifact_manifest(manifest, dist_dir=dist_dir, assets_dir=assets_dir)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        return {
            "id": "artifact-manifest",
            "status": "blocked",
            "evidence_schema": "cleanmac.release-artifact-manifest.v1",
            "blocking_code": "RELEASE_ARTIFACT_MANIFEST_INVALID",
            "diagnostic": str(exc),
            "next_actions": [["make", "release-artifacts-smoke"]],
        }
    return {
        "id": "artifact-manifest",
        "status": "passed",
        "evidence_schema": "cleanmac.release-artifact-manifest.v1",
        "diagnostic": "passed",
        "next_actions": [["make", "release-artifacts-smoke"]],
    }


def _readiness_phase(*, assets_dir: Path) -> dict[str, Any]:
    payload = _json_payload(assets_dir / "RELEASE-READINESS.json")
    if payload is None:
        return {
            "id": "release-readiness",
            "status": "blocked",
            "evidence_schema": "cleanmac.release-readiness.v1",
            "blocking_code": "RELEASE_READINESS_MISSING",
            "diagnostic": "Release readiness evidence is missing.",
            "next_actions": [["make", "release-readiness-smoke"]],
        }
    if payload.get("ready") is not True:
        return {
            "id": "release-readiness",
            "status": "blocked",
            "evidence_schema": "cleanmac.release-readiness.v1",
            "blocking_code": "RELEASE_READINESS_BLOCKED",
            "diagnostic": "Release readiness report is not ready.",
            "failed_gate_ids": list(payload.get("failed_gate_ids", [])),
            "next_actions": [["make", "release-readiness-smoke"], ["make", "release-diagnostics-smoke"]],
        }
    return {
        "id": "release-readiness",
        "status": "passed",
        "evidence_schema": "cleanmac.release-readiness.v1",
        "diagnostic": "passed",
        "next_actions": [["make", "release-readiness-smoke"]],
    }


def render_release_rehearsal(*, dist_dir: Path | str, assets_dir: Path | str) -> dict[str, Any]:
    resolved_dist_dir = Path(dist_dir)
    resolved_assets_dir = Path(assets_dir)
    missing_assets, asset_rows = _asset_status(assets_dir=resolved_assets_dir, names=PROMOTION_REQUIRED_ASSET_NAMES)
    phases = [
        _manifest_phase(dist_dir=resolved_dist_dir, assets_dir=resolved_assets_dir),
        _readiness_phase(assets_dir=resolved_assets_dir),
        {
            "id": "release-assets",
            "status": "passed" if not missing_assets else "blocked",
            "evidence_schema": "cleanmac.release-evidence.v1",
            "blocking_code": None if not missing_assets else "RELEASE_REQUIRED_ASSETS_MISSING",
            "diagnostic": "passed" if not missing_assets else "Required release evidence assets are missing.",
            "missing_assets": missing_assets,
            "next_actions": [["make", "release-artifacts-smoke"], ["make", "release-diagnostics-smoke"]],
        },
    ]
    failed_phase_ids = [phase["id"] for phase in phases if phase.get("status") != "passed"]
    return {
        "schema": RELEASE_REHEARSAL_SCHEMA,
        "destructive": False,
        "dry_run": True,
        "ready": not failed_phase_ids,
        "dist_dir": str(resolved_dist_dir),
        "assets_dir": str(resolved_assets_dir),
        "phases": phases,
        "failed_phase_ids": failed_phase_ids,
        "assets": {"required": list(PROMOTION_REQUIRED_ASSET_NAMES), "missing": missing_assets, "items": asset_rows},
        "recommended_commands": [["make", "release-readiness-smoke"], ["make", "release-diagnostics-smoke"]],
    }


def render_release_promotion_decision(*, dist_dir: Path | str, assets_dir: Path | str) -> dict[str, Any]:
    rehearsal = render_release_rehearsal(dist_dir=dist_dir, assets_dir=assets_dir)
    blocking_codes = [
        str(phase.get("blocking_code"))
        for phase in rehearsal.get("phases", [])
        if phase.get("status") != "passed" and phase.get("blocking_code")
    ]
    safe_to_publish = bool(rehearsal.get("ready"))
    return {
        "schema": RELEASE_PROMOTION_DECISION_SCHEMA,
        "destructive": False,
        "dry_run": True,
        "decision": "promote" if safe_to_publish else "block",
        "ready": safe_to_publish,
        "safe_to_publish": safe_to_publish,
        "manual_review_required": not safe_to_publish,
        "blocking_codes": blocking_codes,
        "required_evidence": list(PROMOTION_REQUIRED_ASSET_NAMES),
        "missing_evidence": list(rehearsal.get("assets", {}).get("missing", [])),
        "advisory_evidence": ["RELEASE-EVIDENCE.json"],
        "rehearsal_summary": {
            "schema": rehearsal.get("schema"),
            "ready": rehearsal.get("ready"),
            "failed_phase_ids": list(rehearsal.get("failed_phase_ids", [])),
        },
        "recommended_commands": [["make", "release-rehearsal-smoke"], ["make", "release-check"]],
    }


def render_release_rollback_plan(*, dist_dir: Path | str, assets_dir: Path | str) -> dict[str, Any]:
    return {
        "schema": RELEASE_ROLLBACK_PLAN_SCHEMA,
        "destructive": False,
        "dry_run": True,
        "manual_only": True,
        "dist_dir": str(Path(dist_dir)),
        "assets_dir": str(Path(assets_dir)),
        "rollback_surfaces": [
            {
                "id": "pypi",
                "risk": "distribution",
                "manual_steps": [
                    "Verify the published version and affected files before yanking.",
                    "Use the PyPI project UI or trusted publishing workflow to yank only the broken release.",
                ],
                "safe_copy_paste_commands": [],
            },
            {
                "id": "github-release",
                "risk": "distribution",
                "manual_steps": [
                    "Verify release tag, assets, attestations, and checksums before editing release state.",
                    "Prefer a corrective release note or replacement asset only after checksum and provenance review.",
                ],
                "safe_copy_paste_commands": [],
            },
            {
                "id": "homebrew-tap",
                "risk": "downstream-package-manager",
                "manual_steps": [
                    "Revert the tap formula commit or publish a corrective formula PR after verifying SHA256.",
                    "Confirm brew install smoke succeeds against the corrected formula before closing the incident.",
                ],
                "safe_copy_paste_commands": [],
            },
        ],
        "pre_rollback_checks": [
            ["cleanmac", "--json", "release-diagnostics"],
            ["cleanmac", "--json", "release-evidence"],
        ],
        "recommended_commands": [["make", "release-rollback-smoke"], ["make", "release-diagnostics-smoke"]],
    }
