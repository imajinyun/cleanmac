from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from cleancli.release_artifacts import (
    build_release_artifact_manifest,
    render_sha256sums,
    verify_release_artifact_manifest,
)

PROJECT_ROOT = Path(__file__).resolve().parent.parent


class ReleaseArtifactManifestTests(unittest.TestCase):
    def test_manifest_hashes_dist_files_and_sbom(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            dist = root / "dist"
            assets = root / "release-assets"
            dist.mkdir()
            assets.mkdir()
            (dist / "cleanmac-0.1.0-py3-none-any.whl").write_text("wheel", encoding="utf-8")
            (dist / "cleanmac-0.1.0.tar.gz").write_text("sdist", encoding="utf-8")
            (assets / "SBOM.json").write_text('{"bomFormat":"CycloneDX"}', encoding="utf-8")

            manifest = build_release_artifact_manifest(dist_dir=dist, assets_dir=assets)

            self.assertEqual(manifest["schema"], "cleanmac.release-artifact-manifest.v1")
            self.assertEqual(
                [row["name"] for row in manifest["artifacts"]],
                [
                    "cleanmac-0.1.0-py3-none-any.whl",
                    "cleanmac-0.1.0.tar.gz",
                    "SBOM.json",
                ],
            )
            self.assertTrue(all(len(row["sha256"]) == 64 for row in manifest["artifacts"]))
            self.assertEqual(manifest["distribution_policy"]["homebrew_formula"], "preflight-only")
            self.assertTrue(manifest["distribution_policy"]["publish_after_cross_platform_verification"])

    def test_sha256sums_matches_manifest_artifacts(self) -> None:
        manifest = {
            "schema": "cleanmac.release-artifact-manifest.v1",
            "artifacts": [
                {"name": "cleanmac.whl", "sha256": "a" * 64, "kind": "whl"},
                {"name": "SBOM.json", "sha256": "b" * 64, "kind": "sbom"},
            ],
        }

        self.assertEqual(render_sha256sums(manifest), f"{'a' * 64}  cleanmac.whl\n{'b' * 64}  SBOM.json\n")

    def test_verify_manifest_fails_closed_when_artifact_is_missing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            dist = root / "dist"
            assets = root / "release-assets"
            dist.mkdir()
            assets.mkdir()
            (assets / "SBOM.json").write_text("{}", encoding="utf-8")
            manifest = {
                "schema": "cleanmac.release-artifact-manifest.v1",
                "artifacts": [{"name": "missing.whl", "sha256": "0" * 64, "kind": "whl"}],
            }

            with self.assertRaisesRegex(FileNotFoundError, "missing.whl"):
                verify_release_artifact_manifest(manifest, dist_dir=dist, assets_dir=assets)

    def test_manifest_json_is_deterministic(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            dist = root / "dist"
            assets = root / "release-assets"
            dist.mkdir()
            assets.mkdir()
            (dist / "cleanmac-0.1.0-py3-none-any.whl").write_text("wheel", encoding="utf-8")
            (assets / "SBOM.json").write_text("{}", encoding="utf-8")

            first = build_release_artifact_manifest(dist_dir=dist, assets_dir=assets)
            second = build_release_artifact_manifest(dist_dir=dist, assets_dir=assets)

            self.assertEqual(json.dumps(first, sort_keys=True), json.dumps(second, sort_keys=True))


class GenerateReleaseManifestScriptTests(unittest.TestCase):
    def test_script_writes_manifest_and_sha256sums(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            dist = root / "dist"
            assets = root / "release-assets"
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

            self.assertEqual(stdout["schema"], "cleanmac.release-artifact-manifest.v1")
            self.assertTrue((assets / "SHA256SUMS").is_file())
            self.assertTrue((assets / "ARTIFACT-MANIFEST.json").is_file())


class InstalledCliParityTests(unittest.TestCase):
    def test_distribution_smoke_mentions_contract_and_release_commands(self) -> None:
        makefile = (PROJECT_ROOT / "Makefile").read_text(encoding="utf-8")

        self.assertIn("cleanmac.ai-contract-samples.v1", makefile)
        self.assertIn("cleanmac.release-artifact-manifest.v1", makefile)
        self.assertIn("cleanmac --json capabilities", makefile.replace('"', ""))


if __name__ == "__main__":
    unittest.main()
