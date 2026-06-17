from __future__ import annotations

import importlib.util
import plistlib
import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
from tempfile import TemporaryDirectory


def load_audit_module():
    path = Path(__file__).resolve().parents[1] / "scripts" / "audit_bundle_drift.py"
    spec = importlib.util.spec_from_file_location("cleanmac_audit_bundle_drift", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def write_app(root: Path, name: str, bundle_id: str | None) -> Path:
    app = root / name
    contents = app / "Contents"
    contents.mkdir(parents=True)
    if bundle_id is not None:
        with (contents / "Info.plist").open("wb") as handle:
            plistlib.dump({"CFBundleIdentifier": bundle_id}, handle)
    return app


def write_bundle(root: Path, name: str, bundle_id: str | None) -> Path:
    bundle = root / name
    contents = bundle / "Contents"
    contents.mkdir(parents=True)
    if bundle_id is not None:
        with (contents / "Info.plist").open("wb") as handle:
            plistlib.dump({"CFBundleIdentifier": bundle_id}, handle)
    return bundle


class BundleDriftAuditTests(unittest.TestCase):
    def test_bundle_drift_audit_reports_uncovered_system_bundles_only(self) -> None:
        audit = load_audit_module()
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            system_root = root / "System" / "Applications"
            applications_root = root / "Applications"
            write_app(system_root, "Finder.app", "com.apple.finder")
            write_app(system_root, "NewSystemTool.app", "org.example.system-tool")
            write_bundle(system_root, "NewExtension.appex", "org.example.system-extension")
            write_bundle(system_root, "ApplePreference.prefPane", "com.apple.preference.sound")
            write_app(system_root, "Broken.app", None)
            write_app(applications_root, "ThirdParty.app", "org.example.third-party")

            report = audit.audit_bundle_drift(system_roots=[system_root], informational_roots=[applications_root])

        self.assertEqual(report["schema"], "cleanmac.bundle-drift-audit.v1")
        self.assertTrue(report["summary"]["drift_detected"])
        self.assertEqual(report["summary"]["system_bundle_count"], 5)
        self.assertEqual(report["summary"]["informational_bundle_count"], 1)
        self.assertEqual(
            [row["bundle_id"] for row in report["uncovered_system_bundles"]],
            ["org.example.system-extension", "org.example.system-tool"],
        )
        extension = next(row for row in report["system_bundles"] if row["bundle_id"] == "org.example.system-extension")
        self.assertEqual(extension["bundle_type"], "appex")
        self.assertEqual(extension["policy_action"], "uncovered-system")
        self.assertEqual(extension["source_root"], str(system_root))
        self.assertEqual(extension["relative_path"], "NewExtension.appex")
        preference = next(row for row in report["system_bundles"] if row["bundle_type"] == "prefPane")
        self.assertEqual(preference["coverage"], "protected-bundle-prefix")
        self.assertEqual(preference["policy_action"], "covered")
        self.assertEqual([row["path"].endswith("Broken.app") for row in report["unreadable_system_bundles"]], [True])
        self.assertEqual(report["informational_bundles"][0]["bundle_id"], "org.example.third-party")
        self.assertEqual(report["informational_bundles"][0]["policy_action"], "informational-only")
        self.assertIn(".appex", report["bundle_suffixes"])

    def test_bundle_drift_cli_exits_nonzero_when_fail_on_drift_is_requested(self) -> None:
        audit = load_audit_module()
        with TemporaryDirectory() as tmp:
            system_root = Path(tmp) / "System" / "Applications"
            write_app(system_root, "NewSystemTool.app", "org.example.system-tool")

            with redirect_stdout(StringIO()):
                status = audit.main(
                    [
                        "--system-root",
                        str(system_root),
                        "--informational-root",
                        str(Path(tmp) / "Applications"),
                        "--json",
                        "--fail-on-drift",
                    ]
                )

        self.assertEqual(status, 1)


if __name__ == "__main__":
    unittest.main()
