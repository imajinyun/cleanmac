from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from cleancli.release_artifacts import (
    build_release_artifact_manifest,
    build_release_evidence_bundle,
    render_homebrew_formula,
    render_sha256sums,
    verify_release_artifact_manifest,
)

PROJECT_ROOT = Path(__file__).resolve().parent.parent


def test_manifest_hashes_dist_files_and_sbom(tmp_path: Path) -> None:
    dist = tmp_path / "dist"
    assets = tmp_path / "release-assets"
    dist.mkdir()
    assets.mkdir()
    (dist / "cleanmac-0.1.0-py3-none-any.whl").write_text("wheel", encoding="utf-8")
    (dist / "cleanmac-0.1.0.tar.gz").write_text("sdist", encoding="utf-8")
    (assets / "SBOM.json").write_text('{"bomFormat":"CycloneDX"}', encoding="utf-8")
    (assets / "cleanmac.rb").write_text("class Cleanmac < Formula\nend\n", encoding="utf-8")

    manifest = build_release_artifact_manifest(dist_dir=dist, assets_dir=assets)

    assert manifest["schema"] == "cleanmac.release-artifact-manifest.v1"
    assert [row["name"] for row in manifest["artifacts"]] == [
        "cleanmac-0.1.0-py3-none-any.whl",
        "cleanmac-0.1.0.tar.gz",
        "SBOM.json",
        "cleanmac.rb",
    ]
    assert all(len(row["sha256"]) == 64 for row in manifest["artifacts"])
    assert manifest["distribution_policy"]["homebrew_formula"] == "tap-publishable"
    assert manifest["distribution_policy"]["homebrew_tap"] == "cleanmac/tap"
    assert manifest["distribution_policy"]["homebrew_install_commands"] == [
        "brew tap cleanmac/tap",
        "brew install cleanmac",
    ]
    assert manifest["distribution_policy"]["publish_after_cross_platform_verification"] is True


def test_homebrew_formula_uses_tap_install_safe_capabilities_test() -> None:
    formula = render_homebrew_formula(
        version="0.1.0",
        archive_url="https://github.com/cleanmac/cleanmac/archive/refs/tags/v0.1.0.tar.gz",
        sha256="A" * 64,
    )

    assert "class Cleanmac < Formula" in formula
    assert "include Language::Python::Virtualenv" in formula
    assert 'url "https://github.com/cleanmac/cleanmac/archive/refs/tags/v0.1.0.tar.gz"' in formula
    assert f'sha256 "{"a" * 64}"' in formula
    assert 'license "MIT"' in formula
    assert 'depends_on "python@3.12"' in formula
    assert "virtualenv_install_with_resources" in formula
    assert 'shell_output("#{bin}/cleanmac --json capabilities")' in formula
    assert 'assert_match "cleanmac.capabilities.v1", output' in formula


def test_homebrew_formula_rejects_invalid_sha256() -> None:
    with pytest.raises(ValueError, match="64-character hexadecimal"):
        render_homebrew_formula(
            version="0.1.0",
            archive_url="https://github.com/cleanmac/cleanmac/archive/refs/tags/v0.1.0.tar.gz",
            sha256="not-a-digest",
        )


def test_sha256sums_matches_manifest_artifacts() -> None:
    manifest = {
        "schema": "cleanmac.release-artifact-manifest.v1",
        "artifacts": [
            {"name": "cleanmac.whl", "sha256": "a" * 64, "kind": "whl"},
            {"name": "SBOM.json", "sha256": "b" * 64, "kind": "sbom"},
        ],
    }

    assert render_sha256sums(manifest) == f"{'a' * 64}  cleanmac.whl\n{'b' * 64}  SBOM.json\n"


def test_verify_manifest_fails_closed_when_artifact_is_missing(tmp_path: Path) -> None:
    dist = tmp_path / "dist"
    assets = tmp_path / "release-assets"
    dist.mkdir()
    assets.mkdir()
    (assets / "SBOM.json").write_text("{}", encoding="utf-8")
    manifest = {
        "schema": "cleanmac.release-artifact-manifest.v1",
        "artifacts": [{"name": "missing.whl", "sha256": "0" * 64, "kind": "whl"}],
    }

    with pytest.raises(FileNotFoundError, match="missing.whl"):
        verify_release_artifact_manifest(manifest, dist_dir=dist, assets_dir=assets)


def test_verify_manifest_fails_closed_when_artifact_checksum_changes(tmp_path: Path) -> None:
    dist = tmp_path / "dist"
    assets = tmp_path / "release-assets"
    dist.mkdir()
    assets.mkdir()
    wheel = dist / "cleanmac-0.1.0-py3-none-any.whl"
    wheel.write_text("original wheel", encoding="utf-8")
    (assets / "SBOM.json").write_text("{}", encoding="utf-8")
    manifest = build_release_artifact_manifest(dist_dir=dist, assets_dir=assets)
    wheel.write_text("tampered wheel", encoding="utf-8")

    with pytest.raises(ValueError, match="SHA256 mismatch for cleanmac-0.1.0-py3-none-any.whl"):
        verify_release_artifact_manifest(manifest, dist_dir=dist, assets_dir=assets)


def test_manifest_json_is_deterministic(tmp_path: Path) -> None:
    dist = tmp_path / "dist"
    assets = tmp_path / "release-assets"
    dist.mkdir()
    assets.mkdir()
    (dist / "cleanmac-0.1.0-py3-none-any.whl").write_text("wheel", encoding="utf-8")
    (assets / "SBOM.json").write_text("{}", encoding="utf-8")
    (assets / "cleanmac.rb").write_text("class Cleanmac < Formula\nend\n", encoding="utf-8")

    first = build_release_artifact_manifest(dist_dir=dist, assets_dir=assets)
    second = build_release_artifact_manifest(dist_dir=dist, assets_dir=assets)

    assert json.dumps(first, sort_keys=True) == json.dumps(second, sort_keys=True)


def test_release_evidence_bundle_tracks_missing_required_assets(tmp_path: Path) -> None:
    dist = tmp_path / "dist"
    assets = tmp_path / "release-assets"
    dist.mkdir()
    assets.mkdir()

    bundle = build_release_evidence_bundle(dist_dir=dist, assets_dir=assets)

    assert bundle["schema"] == "cleanmac.release-evidence.v1"
    assert bundle["ready"] is False
    assert "RELEASE-READINESS.json" in bundle["assets"]["missing"]
    assert "RELEASE-REHEARSAL.json" in bundle["assets"]["missing"]
    assert "RELEASE-PROMOTION-DECISION.json" in bundle["assets"]["missing"]
    assert "RELEASE-POST-PUBLISH-VERIFICATION.json" in bundle["assets"]["missing"]
    assert "RELEASE-POST-PUBLISH-RESULT.json" in bundle["assets"]["missing"]
    assert "RELEASE-ROLLBACK-PLAN.json" in bundle["assets"]["missing"]


def test_script_writes_manifest_and_sha256sums(tmp_path: Path) -> None:
    dist = tmp_path / "dist"
    assets = tmp_path / "release-assets"
    dist.mkdir()
    assets.mkdir()
    (dist / "cleanmac-0.1.0-py3-none-any.whl").write_text("wheel", encoding="utf-8")
    (assets / "SBOM.json").write_text("{}", encoding="utf-8")

    result = subprocess.run(
        [
            sys.executable,
            str(PROJECT_ROOT / "scripts/generate_release_manifest.py"),
            "--dist-dir",
            str(dist),
            "--assets-dir",
            str(assets),
        ],
        text=True,
        capture_output=True,
        check=True,
    )
    stdout = json.loads(result.stdout)

    assert stdout["schema"] == "cleanmac.release-artifact-manifest.v1"
    assert (assets / "SHA256SUMS").is_file()
    assert (assets / "ARTIFACT-MANIFEST.json").is_file()


def test_script_can_write_release_evidence_bundle(tmp_path: Path) -> None:
    dist = tmp_path / "dist"
    assets = tmp_path / "release-assets"
    dist.mkdir()
    assets.mkdir()
    (dist / "cleanmac-0.1.0-py3-none-any.whl").write_text("wheel", encoding="utf-8")
    (assets / "SBOM.json").write_text("{}", encoding="utf-8")
    (assets / "cleanmac.rb").write_text("class Cleanmac < Formula\nend\n", encoding="utf-8")
    (assets / "RELEASE-READINESS.json").write_text(
        json.dumps({"schema": "cleanmac.release-readiness.v1", "ready": True, "failed_gate_ids": []}),
        encoding="utf-8",
    )

    result = subprocess.run(
        [
            sys.executable,
            str(PROJECT_ROOT / "scripts/generate_release_manifest.py"),
            "--dist-dir",
            str(dist),
            "--assets-dir",
            str(assets),
            "--evidence",
        ],
        text=True,
        capture_output=True,
        check=True,
    )

    stdout = json.loads(result.stdout)
    assert stdout["schema"] == "cleanmac.release-evidence.v1"
    assert stdout["ready"] is True, stdout
    assert (assets / "RELEASE-EVIDENCE.json").is_file()
    assert (assets / "RELEASE-DIAGNOSTICS.json").is_file()
    assert (assets / "RELEASE-REHEARSAL.json").is_file()
    assert (assets / "RELEASE-PROMOTION-DECISION.json").is_file()
    assert (assets / "RELEASE-POST-PUBLISH-VERIFICATION.json").is_file()
    assert (assets / "RELEASE-POST-PUBLISH-RESULT.json").is_file()
    assert (assets / "RELEASE-POST-PUBLISH-EVIDENCE.example.json").is_file()
    assert (assets / "RELEASE-ROLLBACK-PLAN.json").is_file()
    assert stdout["release_rehearsal"]["schema"] == "cleanmac.release-rehearsal.v1"
    assert stdout["release_rehearsal"]["ready"] is True, stdout
    assert stdout["promotion_decision"]["schema"] == "cleanmac.release-promotion-decision.v1"
    assert stdout["promotion_decision"]["decision"] == "promote"
    assert stdout["post_publish_verification"]["schema"] == "cleanmac.release-post-publish-verification.v1"
    assert stdout["post_publish_result"]["schema"] == "cleanmac.release-post-publish-result.v1"
    assert stdout["post_publish_result"]["ready"] is False
    assert stdout["post_publish_evidence_template"]["schema"] == "cleanmac.release-post-publish-evidence-template.v1"
    assert (
        stdout["post_publish_evidence_template"]["target_input_schema"]
        == "cleanmac.release-post-publish-evidence-input.v1"
    )
    assert stdout["rollback_plan"]["schema"] == "cleanmac.release-rollback-plan.v1"


def test_homebrew_formula_script_writes_formula(tmp_path: Path) -> None:
    output = tmp_path / "release-assets" / "cleanmac.rb"

    result = subprocess.run(
        [
            sys.executable,
            str(PROJECT_ROOT / "scripts/generate_homebrew_formula.py"),
            "--version",
            "0.1.0",
            "--archive-url",
            "https://github.com/cleanmac/cleanmac/archive/refs/tags/v0.1.0.tar.gz",
            "--sha256",
            "0" * 64,
            "--output",
            str(output),
        ],
        text=True,
        capture_output=True,
        check=True,
    )

    assert result.stdout == ""
    text = output.read_text(encoding="utf-8")
    assert "class Cleanmac < Formula" in text
    assert 'sha256 "0000000000000000000000000000000000000000000000000000000000000000"' in text


def test_distribution_smoke_mentions_contract_and_release_commands() -> None:
    makefile = (PROJECT_ROOT / "Makefile").read_text(encoding="utf-8")

    assert "cleanmac.ai-contract-samples.v1" in makefile
    assert "cleanmac.release-artifact-manifest.v1" in makefile
    assert "cleanmac --json capabilities" in makefile.replace('"', "")


def test_release_workflow_supply_chain_contract() -> None:
    release = (PROJECT_ROOT / ".github/workflows/release.yml").read_text(encoding="utf-8")
    expected_release_assets = {
        "release-assets/SBOM.json",
        "release-assets/SHA256SUMS",
        "release-assets/ARTIFACT-MANIFEST.json",
        "release-assets/RELEASE-READINESS.json",
        "release-assets/RELEASE-DIAGNOSTICS.json",
        "release-assets/RELEASE-EVIDENCE.json",
        "release-assets/RELEASE-REHEARSAL.json",
        "release-assets/RELEASE-PROMOTION-DECISION.json",
        "release-assets/RELEASE-ROLLBACK-PLAN.json",
        "release-assets/RELEASE-POST-PUBLISH-VERIFICATION.json",
        "release-assets/RELEASE-POST-PUBLISH-RESULT.json",
        "release-assets/cleanmac.rb",
    }

    assert "permissions:\n  contents: read" in release
    assert "name: Build release artifacts" in release
    assert "name: Verify release artifacts (${{ matrix.os }})" in release
    assert "name: Attest and publish release artifacts" in release
    assert "contents: write" in release
    assert "id-token: write" in release
    assert "attestations: write" in release
    assert "environment: release" in release
    assert "PYTHON: .venv/bin/python" in release
    assert "Create venv and install build dependencies" in release
    assert ".venv/bin/python -m pip install -e '.[dev,build]'" in release
    assert "name: cleanmac-dist" in release
    assert "name: cleanmac-release-assets" in release
    assert "pypa/gh-action-pypi-publish@cef221092ed1bacb1cc03d23a2d87d1d172e277b" in release
    assert "pypa/gh-action-pypi-publish@release/v1" in release
    assert "actions/attest-build-provenance@a2bbfa25375fe432b6a289bc6b6cd05ecd0c4c32" in release
    assert "softprops/action-gh-release@718ea10b132b3b2eba29c1007bb80653f286566b" in release
    assert 'packages-dir: "release-assets"' not in release

    uses_lines = [line.strip() for line in release.splitlines() if line.strip().startswith("uses: ")]
    assert uses_lines
    for line in uses_lines:
        assert "@" in line, line
        ref = line.split("@", 1)[1].split()[0]
        assert len(ref) == 40
        assert all(char in "0123456789abcdef" for char in ref), line

    for asset in expected_release_assets:
        assert asset in release, asset
