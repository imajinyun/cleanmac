from __future__ import annotations

import hashlib
import json
import platform
import re
from pathlib import Path
from typing import Any

RELEASE_ARTIFACT_MANIFEST_SCHEMA = "cleanmac.release-artifact-manifest.v1"
RELEASE_EVIDENCE_SCHEMA = "cleanmac.release-evidence.v1"
HOMEBREW_FORMULA_NAME = "cleanmac.rb"
HOMEBREW_TAP = "cleanmac/tap"
REQUIRED_RELEASE_ASSET_NAMES = (
    "SBOM.json",
    "SHA256SUMS",
    "ARTIFACT-MANIFEST.json",
    "RELEASE-READINESS.json",
    "RELEASE-DIAGNOSTICS.json",
    "RELEASE-REHEARSAL.json",
    "RELEASE-PROMOTION-DECISION.json",
    "RELEASE-POST-PUBLISH-VERIFICATION.json",
    "RELEASE-POST-PUBLISH-RESULT.json",
    "RELEASE-ROLLBACK-PLAN.json",
    HOMEBREW_FORMULA_NAME,
)


def validate_sha256_hex(value: str) -> str:
    if not re.fullmatch(r"[0-9a-fA-F]{64}", value):
        raise ValueError("Homebrew formula sha256 must be a 64-character hexadecimal digest.")
    return value.lower()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def artifact_kind(path: Path) -> str:
    if path.name == "SBOM.json":
        return "sbom"
    if path.name == HOMEBREW_FORMULA_NAME:
        return "homebrew-formula"
    if path.suffix == ".whl":
        return "wheel"
    if path.suffixes[-2:] == [".tar", ".gz"]:
        return "sdist"
    if path.suffix == ".pyz":
        return "zipapp"
    return path.suffix.lstrip(".") or "file"


def release_artifact_paths(*, dist_dir: Path, assets_dir: Path) -> list[Path]:
    dist_paths = [path for path in sorted(dist_dir.iterdir()) if path.is_file()]
    sbom_path = assets_dir / "SBOM.json"
    if not sbom_path.is_file():
        raise FileNotFoundError(f"Missing release SBOM: {sbom_path}")
    formula_path = assets_dir / HOMEBREW_FORMULA_NAME
    asset_paths = [sbom_path]
    if formula_path.is_file():
        asset_paths.append(formula_path)
    return [*dist_paths, *asset_paths]


def render_homebrew_formula(*, version: str, archive_url: str, sha256: str) -> str:
    digest = validate_sha256_hex(sha256)
    if not version or version.startswith("v"):
        raise ValueError("Homebrew formula version must omit the leading 'v'.")
    if not archive_url.startswith("https://"):
        raise ValueError("Homebrew formula archive_url must use https.")
    return f'''class Cleanmac < Formula
  include Language::Python::Virtualenv

  desc "macOS cleanup CLI with dry-run and safety guardrails"
  homepage "https://github.com/cleanmac/cleanmac"
  url "{archive_url}"
  sha256 "{digest}"
  license "MIT"
  version "{version}"

  depends_on "python@3.12"

  def install
    virtualenv_install_with_resources
  end

  test do
    output = shell_output("#{{bin}}/cleanmac --json capabilities")
    assert_match "cleanmac.capabilities.v1", output
  end
end
'''


def build_release_artifact_manifest(*, dist_dir: Path, assets_dir: Path) -> dict[str, Any]:
    artifacts = [
        {"name": path.name, "sha256": sha256_file(path), "kind": artifact_kind(path)}
        for path in release_artifact_paths(dist_dir=dist_dir, assets_dir=assets_dir)
    ]
    return {
        "schema": RELEASE_ARTIFACT_MANIFEST_SCHEMA,
        "python_version": platform.python_version(),
        "platform": platform.platform(),
        "artifacts": artifacts,
        "distribution_policy": {
            "homebrew_formula": "tap-publishable",
            "homebrew_tap": HOMEBREW_TAP,
            "homebrew_formula_asset": f"release-assets/{HOMEBREW_FORMULA_NAME}",
            "homebrew_install_commands": ["brew tap cleanmac/tap", "brew install cleanmac"],
            "standalone_zipapp": "smoke-tested outside release upload",
            "publish_after_cross_platform_verification": True,
        },
    }


def render_sha256sums(manifest: dict[str, Any]) -> str:
    artifacts = manifest.get("artifacts")
    if not isinstance(artifacts, list):
        raise ValueError("Manifest artifacts must be a list.")
    lines = []
    for row in artifacts:
        if not isinstance(row, dict):
            raise ValueError("Manifest artifact entries must be objects.")
        digest = str(row.get("sha256") or "")
        name = str(row.get("name") or "")
        if len(digest) != 64 or not name:
            raise ValueError(f"Invalid artifact entry: {row!r}")
        lines.append(f"{digest}  {name}")
    return "\n".join(lines) + "\n"


def artifact_path_for_name(name: str, *, dist_dir: Path, assets_dir: Path) -> Path:
    if name in {"SBOM.json", HOMEBREW_FORMULA_NAME}:
        return assets_dir / name
    return dist_dir / name


def verify_release_artifact_manifest(manifest: dict[str, Any], *, dist_dir: Path, assets_dir: Path) -> None:
    if manifest.get("schema") != RELEASE_ARTIFACT_MANIFEST_SCHEMA:
        raise ValueError(f"Unsupported release manifest schema: {manifest.get('schema')!r}")
    artifacts = manifest.get("artifacts")
    if not isinstance(artifacts, list) or not artifacts:
        raise ValueError("Release manifest must contain at least one artifact.")
    for row in artifacts:
        if not isinstance(row, dict):
            raise ValueError("Release manifest artifact entries must be objects.")
        name = str(row.get("name") or "")
        expected_digest = str(row.get("sha256") or "")
        path = artifact_path_for_name(name, dist_dir=dist_dir, assets_dir=assets_dir)
        if not path.is_file():
            raise FileNotFoundError(f"Missing release artifact: {name}")
        actual_digest = sha256_file(path)
        if actual_digest != expected_digest:
            raise ValueError(f"SHA256 mismatch for {name}: expected {expected_digest}, got {actual_digest}")


def write_release_artifact_outputs(*, dist_dir: Path, assets_dir: Path) -> dict[str, Any]:
    assets_dir.mkdir(parents=True, exist_ok=True)
    manifest = build_release_artifact_manifest(dist_dir=dist_dir, assets_dir=assets_dir)
    verify_release_artifact_manifest(manifest, dist_dir=dist_dir, assets_dir=assets_dir)
    (assets_dir / "SHA256SUMS").write_text(render_sha256sums(manifest), encoding="utf-8")
    (assets_dir / "ARTIFACT-MANIFEST.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return manifest


def _json_file_summary(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {"path": str(path), "present": False, "sha256": None, "schema": None, "valid_json": False}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"path": str(path), "present": True, "sha256": sha256_file(path), "schema": None, "valid_json": False}
    return {
        "path": str(path),
        "present": True,
        "sha256": sha256_file(path),
        "schema": payload.get("schema") if isinstance(payload, dict) else None,
        "valid_json": isinstance(payload, dict),
    }


def _asset_rows(*, dist_dir: Path, assets_dir: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for name in REQUIRED_RELEASE_ASSET_NAMES:
        path = assets_dir / name
        row: dict[str, Any] = {"name": name, "path": str(path), "present": path.is_file()}
        if path.is_file():
            row["sha256"] = sha256_file(path)
            row["kind"] = artifact_kind(path)
        rows.append(row)
    if dist_dir.is_dir():
        for path in sorted(dist_dir.iterdir()):
            if path.is_file():
                rows.append(
                    {
                        "name": path.name,
                        "path": str(path),
                        "present": True,
                        "sha256": sha256_file(path),
                        "kind": artifact_kind(path),
                    }
                )
    return rows


def build_release_evidence_bundle(
    *,
    dist_dir: Path,
    assets_dir: Path,
    release_readiness: dict[str, Any] | None = None,
    release_diagnostics: dict[str, Any] | None = None,
    governance_integrity: dict[str, Any] | None = None,
    contract_validation: dict[str, Any] | None = None,
    ai_host_evidence: dict[str, Any] | None = None,
    eval_smoke: dict[str, Any] | None = None,
    release_rehearsal: dict[str, Any] | None = None,
    promotion_decision: dict[str, Any] | None = None,
    post_publish_verification: dict[str, Any] | None = None,
    post_publish_result: dict[str, Any] | None = None,
    post_publish_evidence_template: dict[str, Any] | None = None,
    rollback_plan: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Return an auditable release evidence bundle without shelling out."""

    manifest_path = assets_dir / "ARTIFACT-MANIFEST.json"
    readiness_path = assets_dir / "RELEASE-READINESS.json"
    manifest_summary = _json_file_summary(manifest_path)
    readiness_summary = _json_file_summary(readiness_path)
    manifest_valid = False
    manifest_error = None
    if manifest_path.is_file():
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            verify_release_artifact_manifest(manifest, dist_dir=dist_dir, assets_dir=assets_dir)
            manifest_valid = True
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            manifest_error = str(exc)
    assets = _asset_rows(dist_dir=dist_dir, assets_dir=assets_dir)
    missing_assets = [row["name"] for row in assets if row.get("present") is False]
    readiness_ready = bool(
        release_readiness.get("ready") if isinstance(release_readiness, dict) else readiness_summary.get("present")
    )
    ready = bool(manifest_valid and readiness_ready and not missing_assets)
    return {
        "schema": RELEASE_EVIDENCE_SCHEMA,
        "destructive": False,
        "dry_run": True,
        "ready": ready,
        "dist_dir": str(dist_dir),
        "assets_dir": str(assets_dir),
        "artifact_manifest": {
            **manifest_summary,
            "schema": manifest_summary.get("schema") or RELEASE_ARTIFACT_MANIFEST_SCHEMA,
            "valid": manifest_valid,
            "error": manifest_error,
        },
        "release_readiness": {
            **readiness_summary,
            "schema": (
                release_readiness.get("schema")
                if isinstance(release_readiness, dict)
                else readiness_summary.get("schema") or "cleanmac.release-readiness.v1"
            ),
            "ready": readiness_ready,
            "failed_gate_ids": list(release_readiness.get("failed_gate_ids", []))
            if isinstance(release_readiness, dict)
            else [],
        },
        "release_diagnostics": dict(release_diagnostics or {}),
        "governance_integrity": dict(governance_integrity or {}),
        "assets": {
            "required": list(REQUIRED_RELEASE_ASSET_NAMES),
            "missing": missing_assets,
            "items": assets,
        },
        "contract_validation": dict(contract_validation or {}),
        "ai_host_evidence": dict(ai_host_evidence or {}),
        "eval_smoke": dict(eval_smoke or {}),
        "release_rehearsal": dict(release_rehearsal or {}),
        "promotion_decision": dict(promotion_decision or {}),
        "post_publish_verification": dict(post_publish_verification or {}),
        "post_publish_result": dict(post_publish_result or {}),
        "post_publish_evidence_template": dict(post_publish_evidence_template or {}),
        "rollback_plan": dict(rollback_plan or {}),
    }


def write_release_evidence_bundle_output(
    *,
    dist_dir: Path,
    assets_dir: Path,
    release_readiness: dict[str, Any] | None = None,
    release_diagnostics: dict[str, Any] | None = None,
    governance_integrity: dict[str, Any] | None = None,
    contract_validation: dict[str, Any] | None = None,
    ai_host_evidence: dict[str, Any] | None = None,
    eval_smoke: dict[str, Any] | None = None,
    release_rehearsal: dict[str, Any] | None = None,
    promotion_decision: dict[str, Any] | None = None,
    post_publish_verification: dict[str, Any] | None = None,
    post_publish_result: dict[str, Any] | None = None,
    post_publish_evidence_template: dict[str, Any] | None = None,
    rollback_plan: dict[str, Any] | None = None,
) -> dict[str, Any]:
    assets_dir.mkdir(parents=True, exist_ok=True)
    bundle = build_release_evidence_bundle(
        dist_dir=dist_dir,
        assets_dir=assets_dir,
        release_readiness=release_readiness,
        release_diagnostics=release_diagnostics,
        governance_integrity=governance_integrity,
        contract_validation=contract_validation,
        ai_host_evidence=ai_host_evidence,
        eval_smoke=eval_smoke,
        release_rehearsal=release_rehearsal,
        promotion_decision=promotion_decision,
        post_publish_verification=post_publish_verification,
        post_publish_result=post_publish_result,
        post_publish_evidence_template=post_publish_evidence_template,
        rollback_plan=rollback_plan,
    )
    (assets_dir / "RELEASE-EVIDENCE.json").write_text(
        json.dumps(bundle, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return bundle
