from __future__ import annotations

import json
import os
import platform
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from scripts.audit_bundle_drift import audit_bundle_drift
from tests.helpers import cleanmac_test_env, make_sandbox, run_cli


@unittest.skipUnless(platform.system() == "Darwin", "real macOS smoke requires a macOS runner")
class RealMacOSSmokeTests(unittest.TestCase):
    def test_real_macos_readonly_bundle_audit_emits_schema(self) -> None:
        report = audit_bundle_drift()

        self.assertEqual(report["schema"], "cleanmac.bundle-drift-audit.v1")
        self.assertFalse(report["destructive"])
        self.assertIn("/System/Applications", report["system_roots"])
        self.assertIn(".appex", report["bundle_suffixes"])
        self.assertIsInstance(report["system_bundles"], list)
        self.assertIsInstance(report["uncovered_system_bundles"], list)

    def test_real_macos_cli_capabilities_software_and_doctor_are_readonly(self) -> None:
        capabilities = json.loads(run_cli("--json", "capabilities").stdout)
        software = json.loads(run_cli("--json", "software", "list").stdout)
        with cleanmac_test_env():
            doctor = json.loads(run_cli("--json", "doctor").stdout)

        self.assertEqual(capabilities["schema"], "cleanmac.capabilities.v1")
        self.assertFalse(capabilities["destructive"])
        self.assertEqual(software["schema"], "cleanmac.software.v1")
        self.assertFalse(software["destructive"])
        self.assertEqual(doctor["schema"], "cleanmac.doctor.v1")
        self.assertFalse(doctor["destructive"])

    def test_real_macos_trash_mode_routes_sandbox_candidate_to_test_trash(self) -> None:
        tmp, root, home = make_sandbox()
        with tmp, TemporaryDirectory() as trash_tmp, cleanmac_test_env():
            trash_dir = Path(trash_tmp) / "Trash"
            os.environ["CLEANMAC_TEST_TRASH_DIR"] = str(trash_dir)
            report = json.loads(
                run_cli(
                    "--root",
                    str(root),
                    "--home",
                    str(home),
                    "--json",
                    "clean",
                    "run",
                    "--categories",
                    "downloads",
                    "--delete-mode",
                    "trash",
                    "--execute",
                    "--yes",
                ).stdout
            )

            deleted = [row for row in report["items"] if str(row["path"]).endswith("download.bin")]
            self.assertEqual(len(deleted), 1)
            self.assertTrue(deleted[0]["deleted"])
            self.assertTrue(str(deleted[0]["trash_path"]).startswith(str(trash_dir)))
            self.assertTrue(trash_dir.exists())


if __name__ == "__main__":
    unittest.main()
