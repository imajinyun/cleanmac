from __future__ import annotations

import json
from pathlib import Path

from cleancli import protection
from tests.helpers import make_sandbox, run_cli


def test_cleanmac_protection_library_covers_uninstall_and_data_bundles() -> None:
    assert protection.should_protect_from_uninstall("com.apple.finder")
    assert protection.should_protect_from_uninstall("com.apple.SystemSettings")
    assert not protection.should_protect_from_uninstall("com.apple.dt.Xcode")
    assert protection.should_protect_bundle("com.openai.codex")
    assert protection.should_protect_bundle("com.postmanlabs.mac")
    assert protection.should_protect_bundle("com.sentinel-labs.Agent")
    assert protection.should_protect_bundle("com.cisco.secureclient.gui")


def test_cleanmac_sensitive_path_library_covers_credentials_dev_ai_and_vpn_data() -> None:
    home = Path("/Users/tester")
    protected_paths = (
        home / "Library/Preferences/org.cups.PrintingPrefs.plist",
        home / "Library/Preferences/ByHost/com.apple.Bluetooth.001.plist",
        home / "Library/Preferences/com.apple.networkextension.plist",
        home / "Library/Application Support/KeePassXC/keepassxc.ini",
        home / "Library/Application Support/Yubico/Yubico Authenticator/config.json",
        home / "Library/Application Support/Code/User/settings.json",
        home / ".docker/config.json",
        home / "Library/Application Support/Postman/IndexedDB/state.leveldb",
        home / "Library/Application Support/Claude/session.json",
        home / ".codex/auth.json",
        home / "Library/Application Support/Windsurf/User/globalStorage/state.vscdb",
        home / "Library/Application Support/LM Studio/config.json",
        home / "Library/Application Support/Tailscale/tailscaled.state",
        home / "Library/Application Support/ClashX/config.yaml",
        home / "Library/Application Support/GlobalProtect/PanGPA.dat",
        home / "Library/Application Support/Cisco/Secure Client/profile.xml",
    )

    for path in protected_paths:
        assert protection.should_protect_data(path), str(path)


def test_official_uninstaller_rules_cover_security_mdm_edr_vendors() -> None:
    assert protection.official_uninstaller_vendor(bundle_id="com.crowdstrike.falcon.UserAgent") == "CrowdStrike"
    assert protection.official_uninstaller_vendor(name="Jamf Protect") == "Jamf"
    assert protection.official_uninstaller_vendor(bundle_id="com.sentinel-labs.agent") == "SentinelOne"
    assert protection.official_uninstaller_vendor(name="ESET Management Agent") == "ESET"
    assert protection.official_uninstaller_vendor(bundle_id="com.cisco.secureclient.gui") == "Cisco"
    assert protection.official_uninstaller_vendor(name="GlobalProtect") == "GlobalProtect"


def test_bundle_allowlist_skips_non_allowlisted_bundle() -> None:
    tmp, root, home = make_sandbox()
    with tmp:
        result = run_cli(
            "--root",
            str(root),
            "--home",
            str(home),
            "--json",
            "clean",
            "--categories",
            "userAppCache",
            "--bundle-allowlist",
            "com.allowed",
        )
        report = json.loads(result.stdout)

        assert report["skipped_summary"]["by_reason"]["bundle-not-allowlisted"] >= 1


def test_bundle_blocklist_skips_matching_bundle() -> None:
    tmp, root, home = make_sandbox()
    with tmp:
        result = run_cli(
            "--root",
            str(root),
            "--home",
            str(home),
            "--json",
            "clean",
            "--categories",
            "userAppCache",
            "--bundle-blocklist",
            "com.example",
            "--execute",
        )
        report = json.loads(result.stdout)

        assert report["skipped_summary"]["by_reason"]["bundle-blocklisted"] == 1
        assert (root / "Users/tester/Library/Containers/com.example/Data/Library/Caches/cache.bin").exists()


def test_max_delete_budget_rejects_execution_before_deleting() -> None:
    tmp, root, home = make_sandbox()
    with tmp:
        result = run_cli(
            "--root",
            str(root),
            "--home",
            str(home),
            "clean",
            "--categories",
            "trash",
            "--execute",
            "--max-delete-mb",
            "0",
            check=False,
        )

        assert result.returncode != 0
        assert "exceed --max-delete-mb budget" in result.stderr
        assert (root / "Users/tester/.Trash/old.tmp").exists()


def test_max_items_rejects_execution_before_deleting() -> None:
    tmp, root, home = make_sandbox()
    with tmp:
        (root / "Users/tester/.Trash/extra.tmp").write_text("extra", encoding="utf-8")
        result = run_cli(
            "--root",
            str(root),
            "--home",
            str(home),
            "clean",
            "--categories",
            "trash",
            "--execute",
            "--max-items",
            "1",
            check=False,
        )

        assert result.returncode != 0
        assert "exceeds --max-items budget" in result.stderr
        assert (root / "Users/tester/.Trash/old.tmp").exists()
        assert (root / "Users/tester/.Trash/extra.tmp").exists()


def test_require_plan_context_rejects_root_and_home_mismatch() -> None:
    tmp, root, home = make_sandbox()
    with tmp:
        root_plan = root / "root-plan.json"
        root_plan.write_text(json.dumps({"selected_category_keys": ["trash"], "root": "/elsewhere", "home": str(home)}))
        root_result = run_cli(
            "--root",
            str(root),
            "--home",
            str(home),
            "clean",
            "--plan-file",
            str(root_plan),
            "--require-plan-context",
            check=False,
        )

        home_plan = root / "home-plan.json"
        home_plan.write_text(
            json.dumps({"selected_category_keys": ["trash"], "root": str(root), "home": "/Users/other"})
        )
        home_result = run_cli(
            "--root",
            str(root),
            "--home",
            str(home),
            "clean",
            "--plan-file",
            str(home_plan),
            "--require-plan-context",
            check=False,
        )

        assert root_result.returncode != 0
        assert "Plan root mismatch" in root_result.stderr
        assert home_result.returncode != 0
        assert "Plan home mismatch" in home_result.stderr
