from __future__ import annotations

import json
from pathlib import Path

from cleancli import protection
from tests.helpers import make_sandbox, run_cli


def _write_app(root: Path, name: str, bundle_id: str) -> None:
    app_contents = root / f"Applications/{name}.app/Contents"
    app_contents.mkdir(parents=True)
    app_contents.joinpath("Info.plist").write_bytes(
        b'<?xml version="1.0" encoding="UTF-8"?>'
        b'<plist version="1.0"><dict><key>CFBundleIdentifier</key><string>'
        + bundle_id.encode("utf-8")
        + b"</string></dict></plist>"
    )


def _software_plan(root: Path, home: Path, app: str) -> dict[str, object]:
    result = run_cli("--root", str(root), "--home", str(home), "--json", "software", "uninstall-plan", "--app", app)
    return json.loads(result.stdout)


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


def test_cleanmac_hardening_protection_categories_are_covered() -> None:
    home = Path("/Users/tester")
    protected_paths = (
        home / "Library/Keychains/login.keychain-db",
        home / "Library/Application Support/com.apple.TCC/TCC.db",
        home / "Library/Preferences/SystemConfiguration/preferences.plist",
        home / "Library/Preferences/com.apple.wifi.known-networks.plist",
        home / "Library/Input Methods/Squirrel.app",
        home / "Library/Keyboard Layouts/Custom.keylayout",
        home / "Library/Application Support/Rime/default.custom.yaml",
        home / ".config/karabiner/karabiner.json",
        home / "Library/Application Support/1Password/1Password.sqlite",
        home / "Library/Application Support/Bitwarden/data.json",
        home / "Library/Application Support/Dashlane/session.json",
        home / "Library/Application Support/LastPass/vault.json",
        home / "Library/Application Support/JetBrains/IntelliJIdea/options/ide.general.xml",
        home / "Library/Application Support/Insomnia/insomnia.Request.db",
        home / ".claude.json",
        home / ".cursor/mcp.json",
        home / ".ollama/id_ed25519",
        home / "Library/Application Support/Cursor/User/globalStorage/state.vscdb",
        home / "Library/Application Support/ChatGPT/Local Storage/leveldb/000003.log",
    )

    for path in protected_paths:
        assert protection.should_protect_data(path), str(path)

    assert protection.should_protect_bundle("com.apple.someNewSystemAgent")
    assert protection.should_protect_bundle("com.apple.mail")
    assert protection.should_protect_bundle("com.bitwarden.desktop")
    assert protection.is_critical_system_component(Path("/Library/Keychains/login.keychain-db"))
    assert protection.should_protect_path(home / "Library/Messages/chat.db")
    assert protection.official_uninstaller_vendor(name="Jamf Self Service") == "Jamf"
    assert protection.official_uninstaller_vendor(bundle_id="com.sentinelone.SentinelAgent") == "SentinelOne"
    assert protection.official_uninstaller_vendor(name="ESET Endpoint Security") == "ESET"


def test_extended_app_cache_categories_select_regenerable_caches_and_preserve_credentials() -> None:
    tmp, root, home = make_sandbox()
    with tmp:
        cache_fixtures = {
            "androidStudio": (
                root / "Users/tester/Library/Caches/Google/AndroidStudio2025.1/index.bin",
                root / "Users/tester/Library/Caches/Google/AndroidStudio2025.1/index.bin",
            ),
            "chrome": (
                root / "Users/tester/Library/Application Support/Google/Chrome/Default/Cache/cache.bin",
                root / "Users/tester/Library/Application Support/Google/Chrome/Default/Cache/cache.bin",
            ),
            "slack": (
                root / "Users/tester/Library/Application Support/Slack/Cache/blob.bin",
                root / "Users/tester/Library/Application Support/Slack/Cache/blob.bin",
            ),
            "nodePackageCaches": (
                root / "Users/tester/.npm/_cacache/index-v5/entry",
                root / "Users/tester/.npm/_cacache/index-v5",
            ),
            "pythonPackageCaches": (
                root / "Users/tester/Library/Caches/pip/http-v2/entry",
                root / "Users/tester/Library/Caches/pip/http-v2",
            ),
            "goBuildCaches": (
                root / "Users/tester/Library/Caches/go-build/ab/cache.a",
                root / "Users/tester/Library/Caches/go-build/ab",
            ),
            "homebrewCaches": (
                root / "Users/tester/Library/Caches/Homebrew/package.tar.gz",
                root / "Users/tester/Library/Caches/Homebrew/package.tar.gz",
            ),
        }
        credential_paths = (
            root / "Users/tester/.docker/config.json",
            root / "Users/tester/.pypirc",
            root / "Users/tester/.netrc",
            root / "Users/tester/Library/Application Support/Slack/Cookies",
            root / "Users/tester/Library/Application Support/Google/Chrome/Default/Login Data",
        )
        for path in (*(write_path for write_path, _expected_path in cache_fixtures.values()), *credential_paths):
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("x", encoding="utf-8")

        result = run_cli(
            "--root",
            str(root),
            "--home",
            str(home),
            "--json",
            "clean",
            "inspect",
            "--categories",
            ",".join(cache_fixtures),
        )
        report = json.loads(result.stdout)
        items = report["items"]
        assert isinstance(items, list)
        by_category = {row["category"]: row for row in items if isinstance(row, dict)}
        item_paths = {row["path"] for row in items if isinstance(row, dict)}

        assert set(cache_fixtures).issubset(by_category)
        for category, (_write_path, expected_candidate_path) in cache_fixtures.items():
            row = by_category[category]
            evidence = row["review_evidence"]
            assert row["path"] == str(expected_candidate_path)
            assert row["default_selected"] is True
            assert row["risk"] == "medium"
            assert evidence["schema"] == "cleanmac.candidate-review-evidence.v1"
            assert evidence["matched_rule"] == f"clean.{category}.candidate"
            assert evidence["default_selected"] is True

        assert not any(str(path) in item_paths for path in credential_paths)
        assert protection.should_protect_data(home / ".docker/config.json")


def test_official_uninstaller_rules_cover_security_mdm_edr_vendors() -> None:
    assert protection.official_uninstaller_vendor(bundle_id="com.crowdstrike.falcon.UserAgent") == "CrowdStrike"
    assert protection.official_uninstaller_vendor(name="Jamf Protect") == "Jamf"
    assert protection.official_uninstaller_vendor(bundle_id="com.sentinel-labs.agent") == "SentinelOne"
    assert protection.official_uninstaller_vendor(name="ESET Management Agent") == "ESET"
    assert protection.official_uninstaller_vendor(bundle_id="com.cisco.secureclient.gui") == "Cisco"
    assert protection.official_uninstaller_vendor(name="GlobalProtect") == "GlobalProtect"


def test_software_uninstall_plan_prioritizes_official_uninstaller_by_bundle_id() -> None:
    tmp, root, home = make_sandbox()
    with tmp:
        _write_app(root, "Falcon Console", "com.crowdstrike.falcon.UserAgent")
        cache = root / "Users/tester/Library/Caches/com.crowdstrike.falcon.UserAgent"
        cache.mkdir(parents=True)
        cache.joinpath("cache.bin").write_text("cache", encoding="utf-8")

        plan = _software_plan(root, home, "com.crowdstrike.falcon.UserAgent")
        uninstall_plan = plan["uninstall_plan"]
        assert isinstance(uninstall_plan, dict)

        assert not plan["valid"]
        assert plan["blocked_reasons"] == ["official-uninstaller-required", "protected-from-uninstall"]
        assert uninstall_plan["official_uninstaller_required"] is True
        assert uninstall_plan["official_uninstaller_vendor"] == "CrowdStrike"
        assert uninstall_plan["recommended_action"] == "use-official-uninstaller-first"
        assert all(candidate["default_selected"] is False for candidate in uninstall_plan["candidates"])


def test_software_leftovers_classify_and_default_skip_credentials_and_user_documents() -> None:
    tmp, root, home = make_sandbox()
    with tmp:
        _write_app(root, "Example", "com.example.app")
        paths = {
            "cache": root / "Users/tester/Library/Caches/com.example.app/cache.bin",
            "logs": root / "Users/tester/Library/Logs/com.example.app/app.log",
            "preferences": root / "Users/tester/Library/Preferences/com.example.app.plist",
            "saved_state": root
            / "Users/tester/Library/Saved Application State/com.example.app.savedState/window.plist",
            "containers": root
            / "Users/tester/Library/Containers/com.example.app/Data/Library/Application Support/state.db",
            "credentials": root / "Users/tester/Library/Application Support/Example/Credentials/token.json",
            "user_documents": root / "Users/tester/Documents/Example/project.cleanmac-test",
        }
        for path in paths.values():
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("x", encoding="utf-8")

        plan = _software_plan(root, home, "Example")
        uninstall_plan = plan["uninstall_plan"]
        assert isinstance(uninstall_plan, dict)
        by_leftover_type = {candidate["leftover_type"]: candidate for candidate in uninstall_plan["candidates"]}

        assert {"cache", "logs", "preferences", "saved_state", "containers", "credentials", "user_documents"}.issubset(
            set(by_leftover_type)
        )
        assert by_leftover_type["cache"]["default_selected"] is True
        assert by_leftover_type["logs"]["default_selected"] is True
        assert by_leftover_type["preferences"]["default_selected"] is True
        assert by_leftover_type["saved_state"]["default_selected"] is True
        assert by_leftover_type["containers"]["default_selected"] is False
        assert by_leftover_type["credentials"]["default_selected"] is False
        assert by_leftover_type["credentials"]["protected"] is True
        assert by_leftover_type["credentials"]["why_not_default"] == "protected by bundle/path safety policy"
        assert by_leftover_type["user_documents"]["default_selected"] is False
        assert by_leftover_type["user_documents"]["contains_user_data"] is True
        assert by_leftover_type["containers"]["risk_explanation"].startswith("Container data may include")
        assert "credentials" in uninstall_plan["leftover_type_counts"]


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

        assert report["dry_run"] is True
        assert report["bundle_allowlist"] == ["com.allowed"]
        assert report["skipped_summary"]["by_reason"] == {"bundle-not-allowlisted": 2}


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

        assert report["dry_run"] is False
        assert report["bundle_blocklist"] == ["com.example"]
        assert report["total_bytes"] == 0
        assert report["skipped_summary"]["by_reason"]["bundle-blocklisted"] == 1
        assert (root / "Users/tester/Library/Containers/com.example/Data/Library/Caches/cache.bin").exists()


def test_container_cache_policy_preserves_protected_app_data() -> None:
    tmp, root, home = make_sandbox()
    with tmp:
        result = run_cli(
            "--root",
            str(root),
            "--home",
            str(home),
            "--json",
            "clean",
            "inspect",
            "--categories",
            "userAppCache",
        )
        report = json.loads(result.stdout)
        item_paths = {row["path"] for row in report["items"]}
        skipped_paths = {row["path"]: row["reason"] for row in report["skipped"]}

        assert str(root / "Users/tester/Library/Containers/com.example/Data/Library/Caches/cache.bin") in item_paths
        assert (
            skipped_paths[str(root / "Users/tester/Library/Containers/com.apple.Notes/Data/Library/Caches/cache.bin")]
            == "protected-container-data"
        )


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
