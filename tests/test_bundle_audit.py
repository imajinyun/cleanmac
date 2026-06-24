from __future__ import annotations

import importlib.util
import plistlib
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path


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


def test_bundle_drift_audit_reports_uncovered_system_bundles_only(tmp_path: Path) -> None:
    audit = load_audit_module()
    system_root = tmp_path / "System" / "Applications"
    applications_root = tmp_path / "Applications"
    write_app(system_root, "Finder.app", "com.apple.finder")
    write_app(system_root, "NewSystemTool.app", "org.example.system-tool")
    write_bundle(system_root, "NewExtension.appex", "org.example.system-extension")
    write_bundle(system_root, "ApplePreference.prefPane", "com.apple.preference.sound")
    write_app(system_root, "Broken.app", None)
    write_app(applications_root, "ThirdParty.app", "org.example.third-party")

    report = audit.audit_bundle_drift(system_roots=[system_root], informational_roots=[applications_root])

    assert report["schema"] == "cleanmac.bundle-drift-audit.v1"
    assert report["summary"]["drift_detected"]
    assert report["summary"]["system_bundle_count"] == 5
    assert report["summary"]["informational_bundle_count"] == 1
    assert [row["bundle_id"] for row in report["uncovered_system_bundles"]] == [
        "org.example.system-extension",
        "org.example.system-tool",
    ]
    extension = next(row for row in report["system_bundles"] if row["bundle_id"] == "org.example.system-extension")
    assert extension["bundle_type"] == "appex"
    assert extension["policy_action"] == "uncovered-system"
    assert extension["source_root"] == str(system_root)
    assert extension["relative_path"] == "NewExtension.appex"
    preference = next(row for row in report["system_bundles"] if row["bundle_type"] == "prefPane")
    assert preference["coverage"] == "protected-bundle-prefix"
    assert preference["policy_action"] == "covered"
    assert [row["path"].endswith("Broken.app") for row in report["unreadable_system_bundles"]] == [True]
    assert report["informational_bundles"][0]["bundle_id"] == "org.example.third-party"
    assert report["informational_bundles"][0]["policy_action"] == "informational-only"
    assert ".appex" in report["bundle_suffixes"]


def test_bundle_drift_cli_exits_nonzero_when_fail_on_drift_is_requested(tmp_path: Path) -> None:
    audit = load_audit_module()
    system_root = tmp_path / "System" / "Applications"
    write_app(system_root, "NewSystemTool.app", "org.example.system-tool")

    with redirect_stdout(StringIO()):
        status = audit.main(
            [
                "--system-root",
                str(system_root),
                "--informational-root",
                str(tmp_path / "Applications"),
                "--json",
                "--fail-on-drift",
            ]
        )

    assert status == 1
