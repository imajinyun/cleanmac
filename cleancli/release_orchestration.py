"""Release rehearsal, promotion, rollback, and post-publish control-plane reports."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from cleancli.release_artifacts import HOMEBREW_FORMULA_NAME, verify_release_artifact_manifest

RELEASE_REHEARSAL_SCHEMA = "cleanmac.release-rehearsal.v1"
RELEASE_PROMOTION_DECISION_SCHEMA = "cleanmac.release-promotion-decision.v1"
RELEASE_ROLLBACK_PLAN_SCHEMA = "cleanmac.release-rollback-plan.v1"
RELEASE_POST_PUBLISH_VERIFICATION_SCHEMA = "cleanmac.release-post-publish-verification.v1"
RELEASE_POST_PUBLISH_RESULT_SCHEMA = "cleanmac.release-post-publish-result.v1"
RELEASE_POST_PUBLISH_EVIDENCE_INPUT_SCHEMA = "cleanmac.release-post-publish-evidence-input.v1"
RELEASE_POST_PUBLISH_EVIDENCE_TEMPLATE_SCHEMA = "cleanmac.release-post-publish-evidence-template.v1"

PROMOTION_REQUIRED_ASSET_NAMES = (
    "SBOM.json",
    "SHA256SUMS",
    "ARTIFACT-MANIFEST.json",
    "RELEASE-READINESS.json",
    "RELEASE-DIAGNOSTICS.json",
    "RELEASE-REHEARSAL.json",
    "RELEASE-POST-PUBLISH-VERIFICATION.json",
    "RELEASE-POST-PUBLISH-RESULT.json",
    "RELEASE-ROLLBACK-PLAN.json",
    HOMEBREW_FORMULA_NAME,
)

POST_PUBLISH_SURFACE_REQUIREMENTS = {
    "github-release": ["GitHub release asset list"],
    "pypi": ["PyPI release page version and file hashes"],
    "homebrew-tap": ["Homebrew tap formula commit"],
}
POST_PUBLISH_VALID_STATUSES = {"verified", "failed", "pending"}


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


def render_release_post_publish_verification(*, dist_dir: Path | str, assets_dir: Path | str) -> dict[str, Any]:
    return {
        "schema": RELEASE_POST_PUBLISH_VERIFICATION_SCHEMA,
        "destructive": False,
        "dry_run": True,
        "manual_only": True,
        "dist_dir": str(Path(dist_dir)),
        "assets_dir": str(Path(assets_dir)),
        "verification_surfaces": [
            {
                "id": "github-release",
                "expected_signals": [
                    "Release assets include wheel, sdist, SBOM, SHA256SUMS, manifest, evidence, and Homebrew formula.",
                    "Attestation is visible for distribution and governance assets.",
                ],
                "safe_copy_paste_commands": [],
            },
            {
                "id": "pypi",
                "expected_signals": [
                    "PyPI project page shows the released version.",
                    "Fresh virtualenv installation succeeds from published wheel.",
                ],
                "safe_copy_paste_commands": [
                    ["python3", "-m", "venv", "/tmp/cleanmac-post-publish-verify"],
                    ["/tmp/cleanmac-post-publish-verify/bin/python", "-m", "pip", "install", "cleanmac"],
                    ["/tmp/cleanmac-post-publish-verify/bin/cleanmac", "--json", "capabilities"],
                ],
            },
            {
                "id": "homebrew-tap",
                "expected_signals": [
                    "Homebrew tap update completed for the release tag.",
                    "Formula install smoke reports cleanmac.capabilities.v1.",
                ],
                "safe_copy_paste_commands": [["brew", "tap", "cleanmac/tap"], ["brew", "install", "cleanmac"]],
            },
        ],
        "required_evidence_after_publish": [
            "GitHub release asset list",
            "PyPI release page version and file hashes",
            "Homebrew tap formula commit",
            "cleanmac --json capabilities output from a fresh install",
        ],
        "incident_response_entrypoints": [
            ["cleanmac", "--json", "release-diagnostics"],
            ["cleanmac", "--json", "release-rollback-plan"],
        ],
        "recommended_commands": [["make", "release-post-publish-smoke"], ["make", "release-check"]],
    }


def _post_publish_evidence_payload(evidence_file: Path | str | None) -> tuple[dict[str, Any], dict[str, Any] | None]:
    if evidence_file is None:
        return {}, None
    path = Path(evidence_file)
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return {}, {"path": str(path), "valid_json": False, "error": str(exc)}
    if not isinstance(payload, dict):
        return {}, {"path": str(path), "valid_json": False, "error": "Evidence input must be a JSON object."}
    schema = payload.get("schema")
    if schema != RELEASE_POST_PUBLISH_EVIDENCE_INPUT_SCHEMA:
        return {}, {
            "path": str(path),
            "valid_json": True,
            "schema": schema,
            "valid_schema": False,
            "error": f"Evidence input schema must be {RELEASE_POST_PUBLISH_EVIDENCE_INPUT_SCHEMA}.",
        }
    surfaces = payload.get("surfaces", {})
    if not isinstance(surfaces, dict):
        return {}, {
            "path": str(path),
            "valid_json": True,
            "schema": schema,
            "valid_schema": False,
            "error": "Evidence input surfaces must be an object keyed by surface id.",
        }
    return surfaces, {
        "path": str(path),
        "valid_json": True,
        "schema": schema,
        "valid_schema": True,
        "surface_count": len(surfaces),
    }


def render_release_post_publish_evidence_template(*, dist_dir: Path | str, assets_dir: Path | str) -> dict[str, Any]:
    template = {
        "schema": RELEASE_POST_PUBLISH_EVIDENCE_INPUT_SCHEMA,
        "surfaces": {
            surface_id: {
                "status": "pending",
                "evidence_refs": [],
                "notes": "",
                "required_evidence": list(required_evidence),
            }
            for surface_id, required_evidence in POST_PUBLISH_SURFACE_REQUIREMENTS.items()
        },
    }
    return {
        "schema": RELEASE_POST_PUBLISH_EVIDENCE_TEMPLATE_SCHEMA,
        "destructive": False,
        "dry_run": True,
        "manual_only": True,
        "dist_dir": str(Path(dist_dir)),
        "assets_dir": str(Path(assets_dir)),
        "target_input_schema": RELEASE_POST_PUBLISH_EVIDENCE_INPUT_SCHEMA,
        "template": template,
        "operator_instructions": [
            "Copy this template to post-publish-evidence.json after publishing completes.",
            "Fill evidence_refs with manually reviewed release URLs, asset lists, or tap commits.",
            "Run release-post-publish-result with --evidence-file to close post-publish verification.",
        ],
        "recommended_commands": [
            ["cleanmac", "--json", "release-post-publish-result", "--evidence-file", "post-publish-evidence.json"],
            ["make", "release-post-publish-evidence-template-smoke"],
        ],
    }


def render_release_post_publish_result(
    *,
    dist_dir: Path | str,
    assets_dir: Path | str,
    evidence_file: Path | str | None = None,
) -> dict[str, Any]:
    evidence_by_surface, evidence_input = _post_publish_evidence_payload(evidence_file)
    evidence_validation_errors = []
    if evidence_input and evidence_input.get("valid_json") is False:
        evidence_validation_errors.append(
            {
                "code": "EVIDENCE_FILE_INVALID_JSON",
                "message": str(evidence_input.get("error") or "Evidence input is not valid JSON."),
            }
        )
    if evidence_input and evidence_input.get("valid_schema") is False:
        evidence_validation_errors.append(
            {
                "code": "EVIDENCE_SCHEMA_MISMATCH",
                "message": str(evidence_input.get("error") or "Evidence input schema is not supported."),
            }
        )
    for surface_id in sorted(set(evidence_by_surface) - set(POST_PUBLISH_SURFACE_REQUIREMENTS)):
        evidence_validation_errors.append(
            {
                "code": "UNKNOWN_POST_PUBLISH_SURFACE",
                "surface_id": str(surface_id),
                "message": f"Unknown post-publish surface: {surface_id}",
            }
        )
    surfaces = []
    failed_surface_ids = []
    pending_surface_ids = []
    verified_surface_ids = []
    for surface_id, required_evidence in POST_PUBLISH_SURFACE_REQUIREMENTS.items():
        raw_surface = evidence_by_surface.get(surface_id, {})
        raw_surface = raw_surface if isinstance(raw_surface, dict) else {}
        status = str(raw_surface.get("status") or "pending")
        surface_validation_errors = []
        if status not in POST_PUBLISH_VALID_STATUSES:
            surface_validation_errors.append(
                {
                    "code": "INVALID_POST_PUBLISH_STATUS",
                    "message": f"Invalid post-publish status for {surface_id}: {status}",
                }
            )
            status = "failed"
        evidence_refs = raw_surface.get("evidence_refs", [])
        if not isinstance(evidence_refs, list):
            evidence_refs = []
        if status == "verified" and not evidence_refs:
            surface_validation_errors.append(
                {
                    "code": "POST_PUBLISH_EVIDENCE_REF_MISSING",
                    "message": f"Verified surface {surface_id} must include at least one evidence_ref.",
                }
            )
            status = "failed"
        blocking_code = None
        if status == "failed":
            failed_surface_ids.append(surface_id)
            blocking_code = f"{surface_id.replace('-', '_').upper()}_POST_PUBLISH_FAILED"
        elif status == "pending":
            pending_surface_ids.append(surface_id)
            blocking_code = f"{surface_id.replace('-', '_').upper()}_POST_PUBLISH_UNVERIFIED"
        else:
            verified_surface_ids.append(surface_id)
        row: dict[str, Any] = {
            "id": surface_id,
            "status": status,
            "required_evidence": list(required_evidence),
            "evidence_refs": [str(ref) for ref in evidence_refs],
        }
        if blocking_code:
            row["blocking_code"] = blocking_code
        if surface_validation_errors:
            row["validation_errors"] = surface_validation_errors
            evidence_validation_errors.extend(
                {"surface_id": surface_id, **error} for error in surface_validation_errors
            )
        surfaces.append(row)
    ready = bool(surfaces and not failed_surface_ids and not pending_surface_ids and not evidence_validation_errors)
    return {
        "schema": RELEASE_POST_PUBLISH_RESULT_SCHEMA,
        "destructive": False,
        "dry_run": True,
        "manual_only": True,
        "ready": ready,
        "dist_dir": str(Path(dist_dir)),
        "assets_dir": str(Path(assets_dir)),
        "verification_plan_schema": RELEASE_POST_PUBLISH_VERIFICATION_SCHEMA,
        "evidence_input": evidence_input or {},
        "evidence_validation_errors": evidence_validation_errors,
        "surfaces": surfaces,
        "verified_surface_ids": verified_surface_ids,
        "failed_surface_ids": failed_surface_ids,
        "pending_surface_ids": pending_surface_ids,
        "incident_response_entrypoints": [
            ["cleanmac", "--json", "release-diagnostics"],
            ["cleanmac", "--json", "release-rollback-plan"],
        ],
        "recommended_commands": [["make", "release-post-publish-result-smoke"], ["make", "release-check"]],
    }
