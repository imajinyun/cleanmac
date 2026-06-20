from __future__ import annotations

import hashlib
import json
import platform
import re
from pathlib import Path
from typing import Any

RELEASE_ARTIFACT_MANIFEST_SCHEMA = "cleanmac.release-artifact-manifest.v1"
HOMEBREW_FORMULA_NAME = "cleanmac.rb"
HOMEBREW_TAP = "cleanmac/tap"


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
