#!/usr/bin/env python3
from __future__ import annotations

import importlib
import json
import os
import shlex
import shutil
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path
from typing import Any

import cleancli.core as cleancli

PROJECT_ROOT = Path(__file__).resolve().parent
CLI = PROJECT_ROOT / "cleanmac.py"


class CleanMacCLITests(unittest.TestCase):
    def run_cli(self, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(CLI), *args],
            text=True,
            capture_output=True,
            check=True,
        )

    def run_cli_unchecked(self, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(CLI), *args],
            text=True,
            capture_output=True,
            check=False,
        )

    def make_sandbox(self) -> tuple[tempfile.TemporaryDirectory[str], Path, Path]:
        tmp = tempfile.TemporaryDirectory()
        root = Path(tmp.name)
        home = Path("/Users/tester")

        (root / "Users/tester/.Trash").mkdir(parents=True)
        (root / "Users/tester/Downloads").mkdir(parents=True)
        (root / "Users/tester/Library/Mail Downloads").mkdir(parents=True)
        (root / "Users/tester/Library/Developer/Xcode/DerivedData/App-a").mkdir(parents=True)
        (root / "Users/tester/Library/Developer/Xcode/iOS Device Logs").mkdir(parents=True)
        (root / "Users/tester/Library/Developer/Xcode/Archives/App.xcarchive").mkdir(parents=True)
        (root / "Users/tester/Library/Developer/Xcode/Products/App").mkdir(parents=True)
        (root / "Users/tester/Library/Developer/Xcode/ModuleCache.noindex/Module-a").mkdir(parents=True)
        (root / "Users/tester/Library/Developer/Xcode/iOS DeviceSupport/17.0").mkdir(parents=True)
        (root / "Users/tester/Library/Developer/CoreSimulator/Caches/dyld").mkdir(parents=True)
        (root / "Users/tester/Library/Containers/com.apple.mail/Data/Library/Mail Downloads").mkdir(parents=True)
        (root / "Users/tester/Library/Containers/com.example/Data/Library/Logs").mkdir(parents=True)
        (root / "Users/tester/Library/Containers/com.example/Data/Library/Caches").mkdir(parents=True)
        (root / "Users/tester/Library/Containers/com.apple.Notes/Data/Library/Caches").mkdir(parents=True)
        (root / "Users/tester/Library/Group Containers/group.com.apple.notes/Library/Caches").mkdir(parents=True)
        (root / "Users/tester/Library/Group Containers/group.com.example.app/Library/Caches").mkdir(parents=True)
        (root / "Users/tester/Library/Group Containers/group.com.example.app/Library/Logs").mkdir(parents=True)
        (root / "Users/tester/Library/Caches/Google/AndroidStudio2024.1").mkdir(parents=True)
        (root / "Users/tester/Library/Caches/JetBrains/IntelliJIdea2024.1").mkdir(parents=True)
        (root / "Users/tester/Library/Application Support/Code/Cache").mkdir(parents=True)
        (root / "Users/tester/Library/Caches/com.docker.docker").mkdir(parents=True)
        (root / "Users/tester/Library/Caches/Google/Chrome/Default/Cache").mkdir(parents=True)
        (root / "Users/tester/Library/Application Support/Google/Chrome/Default/Code Cache/js").mkdir(parents=True)
        (root / "Users/tester/Library/Caches/Firefox/Profiles/dev.default-release/cache2/entries").mkdir(parents=True)
        (root / "Users/tester/Library/Application Support/Firefox/Profiles/dev.default-release/cache2/entries").mkdir(
            parents=True
        )
        (root / "Users/tester/Library/Application Support/Slack/Cache").mkdir(parents=True)
        (root / "Users/tester/Library/Application Support/Slack/Service Worker/CacheStorage/cache-a").mkdir(
            parents=True
        )
        (root / "Users/tester/Library/Application Support/zoom.us/data/Cache").mkdir(parents=True)
        (root / "Users/tester/Library/Caches/us.zoom.xos").mkdir(parents=True)
        (root / "Users/tester/Library/Application Support/Microsoft/Teams/Cache").mkdir(parents=True)
        (root / "Users/tester/Library/Application Support/Microsoft/Teams/Service Worker/CacheStorage/cache-a").mkdir(
            parents=True
        )
        (root / "Users/tester/.npm/_cacache/content-v2/sha512/aa").mkdir(parents=True)
        (root / "Users/tester/Library/pnpm/store/v3/files/aa").mkdir(parents=True)
        (root / "Users/tester/Library/Caches/Yarn/v6/npm-example").mkdir(parents=True)
        (root / "Users/tester/Library/Caches/pip/http-v2/a/b").mkdir(parents=True)
        (root / "Users/tester/Library/Caches/go-build/aa").mkdir(parents=True)
        (root / "Users/tester/go/pkg/mod/cache/download/example.com/pkg/@v").mkdir(parents=True)
        (root / "Applications/Falcon.app/Contents").mkdir(parents=True)
        (root / "Users/tester/Library/logs").mkdir(parents=True)
        (root / "Users/tester/Library/Caches/com.example.app").mkdir(parents=True)
        (root / "Library/Logs/DiagnosticReports").mkdir(parents=True)
        (root / "private/var/db/oah/runtime-cache").mkdir(parents=True)
        (root / "private/var/db/DetachedSignatures/signature-cache").mkdir(parents=True)

        (root / "Users/tester/.Trash/old.tmp").write_text("trash")
        (root / "Users/tester/Downloads/download.bin").write_text("download")
        (root / "Users/tester/Downloads/partial.crdownload").write_text("partial")
        (root / "Users/tester/Library/Mail Downloads/old-mail.pdf").write_text("mail-old")
        (root / "Users/tester/Library/Developer/Xcode/DerivedData/App-a/cache.db").write_text("derived")
        (root / "Users/tester/Library/Developer/Xcode/iOS Device Logs/log.txt").write_text("device")
        (root / "Users/tester/Library/Developer/Xcode/Archives/App.xcarchive/info.plist").write_text("archive")
        (root / "Users/tester/Library/Developer/Xcode/Products/App/product.bin").write_text("product")
        (root / "Users/tester/Library/Developer/Xcode/ModuleCache.noindex/Module-a/cache.pcm").write_text("module")
        (root / "Users/tester/Library/Developer/Xcode/iOS DeviceSupport/17.0/symbols.bin").write_text("symbols")
        (root / "Users/tester/Library/Developer/CoreSimulator/Caches/dyld/cache.bin").write_text("sim-cache")
        (root / "Users/tester/Library/Containers/com.apple.mail/Data/Library/Mail Downloads/mail.pdf").write_text(
            "mail"
        )
        (root / "Users/tester/Library/Containers/com.example/Data/Library/Logs/app.log").write_text("app-log")
        (root / "Users/tester/Library/Containers/com.example/Data/Library/Caches/cache.bin").write_text("app-cache")
        (root / "Users/tester/Library/Containers/com.apple.Notes/Data/Library/Caches/cache.bin").write_text("notes")
        (root / "Users/tester/Library/Group Containers/group.com.apple.notes/Library/Caches/cache.bin").write_text(
            "notes-group"
        )
        (root / "Users/tester/Library/Group Containers/group.com.example.app/Library/Caches/cache.bin").write_text(
            "group-cache"
        )
        (root / "Users/tester/Library/Group Containers/group.com.example.app/Library/Logs/app.log").write_text(
            "group-log"
        )
        (root / "Users/tester/Library/Caches/Google/AndroidStudio2024.1/cache.bin").write_text("android")
        (root / "Users/tester/Library/Caches/JetBrains/IntelliJIdea2024.1/cache.bin").write_text("jetbrains")
        (root / "Users/tester/Library/Application Support/Code/Cache/cache.bin").write_text("vscode")
        (root / "Users/tester/Library/Caches/com.docker.docker/cache.bin").write_text("docker")
        (root / "Users/tester/Library/Caches/Google/Chrome/Default/Cache/data_0").write_text("chrome-cache")
        (root / "Users/tester/Library/Application Support/Google/Chrome/Default/Code Cache/js/cache.js").write_text(
            "chrome-code-cache"
        )
        (root / "Users/tester/Library/Caches/Firefox/Profiles/dev.default-release/cache2/entries/cache.bin").write_text(
            "firefox-cache"
        )
        (
            root
            / "Users/tester/Library/Application Support/Firefox/Profiles/dev.default-release/cache2/entries/cache.bin"
        ).write_text("firefox-profile-cache")
        (root / "Users/tester/Library/Application Support/Slack/Cache/cache.bin").write_text("slack-cache")
        (
            root / "Users/tester/Library/Application Support/Slack/Service Worker/CacheStorage/cache-a/cache.bin"
        ).write_text("slack-service-worker-cache")
        (
            root / "Users/tester/Library/Application Support/Slack/Service Worker/CacheStorage/cache-a/Cookies"
        ).write_text("nested-cookie")
        (root / "Users/tester/Library/Application Support/zoom.us/data/Cache/cache.bin").write_text("zoom-cache")
        (root / "Users/tester/Library/Caches/us.zoom.xos/cache.bin").write_text("zoom-cache-2")
        (root / "Users/tester/Library/Application Support/Microsoft/Teams/Cache/cache.bin").write_text("teams-cache")
        (
            root
            / "Users/tester/Library/Application Support/Microsoft/Teams/Service Worker/CacheStorage/cache-a/cache.bin"
        ).write_text("teams-service-worker-cache")
        (root / "Users/tester/.npm/_cacache/content-v2/sha512/aa/cache.bin").write_text("npm-cache")
        (root / "Users/tester/Library/pnpm/store/v3/files/aa/cache.bin").write_text("pnpm-cache")
        (root / "Users/tester/Library/Caches/Yarn/v6/npm-example/package.tgz").write_text("yarn-cache")
        (root / "Users/tester/Library/Caches/pip/http-v2/a/b/cache.bin").write_text("pip-cache")
        (root / "Users/tester/Library/Caches/go-build/aa/cache-a").write_text("go-build-cache")
        (root / "Users/tester/go/pkg/mod/cache/download/example.com/pkg/@v/v1.0.0.zip").write_text("go-mod-cache")
        (root / "Users/tester/Library/Application Support/Google/Chrome/Default/Bookmarks").write_text("bookmarks")
        (root / "Users/tester/Library/Application Support/Google/Chrome/Default/Login Data").write_text("login-data")
        (root / "Users/tester/Library/Application Support/Google/Chrome/Default/Cookies").write_text("cookies")
        (root / "Users/tester/Library/Application Support/Firefox/Profiles/dev.default-release/logins.json").write_text(
            "firefox-logins"
        )
        (root / "Users/tester/Library/Application Support/Firefox/Profiles/dev.default-release/key4.db").write_text(
            "firefox-key"
        )
        (root / "Users/tester/Library/Application Support/Slack/Local Storage/leveldb").mkdir(parents=True)
        (root / "Users/tester/Library/Application Support/Slack/Local Storage/leveldb/state.ldb").write_text(
            "slack-local-storage"
        )
        (root / "Users/tester/.npmrc").write_text("//registry.example/:_authToken=secret")
        (root / "Users/tester/.pypirc").write_text("[distutils]")
        (root / "Users/tester/.netrc").write_text("machine example.com login token")
        (root / "Applications/Falcon.app/Contents/Info.plist").write_bytes(
            b'<?xml version="1.0" encoding="UTF-8"?><!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd"><plist version="1.0"><dict><key>CFBundleIdentifier</key><string>com.crowdstrike.falcon.UserAgent</string></dict></plist>'
        )
        (root / "Users/tester/Library/logs/noisy.log").write_text("log")
        (root / "Users/tester/Library/Caches/com.example.app/cache.bin").write_text("cache")
        (root / "Library/Logs/DiagnosticReports/crash.ips").write_text("diagnostic")
        (root / "private/var/db/oah/runtime-cache/cache.bin").write_text("oah")
        (root / "private/var/db/DetachedSignatures/signature-cache/cache.bin").write_text("signature")
        return tmp, root, home

    def test_cli_version(self) -> None:
        result = self.run_cli("--version")
        self.assertIn("cleanmac", result.stdout.strip())
        self.assertIn(cleancli.VERSION, result.stdout.strip())

    def test_completion_bash_includes_commands_and_categories(self) -> None:
        result = self.run_cli("completion", "bash")
        self.assertIn("cleanmac bash completion", result.stdout)
        self.assertIn("list", result.stdout)
        self.assertIn("ai-tools", result.stdout)
        self.assertIn("trash", result.stdout)
        self.assertIn("complete -F _cleanmac_completion cleanmac", result.stdout)

    def test_completion_zsh_includes_commands(self) -> None:
        result = self.run_cli("completion", "zsh")
        self.assertIn("cleanmac zsh completion", result.stdout)
        self.assertIn("#compdef cleanmac", result.stdout)

    def test_completion_fish_includes_commands(self) -> None:
        result = self.run_cli("completion", "fish")
        self.assertIn("cleanmac fish completion", result.stdout)
        self.assertIn("__fish_use_subcommand", result.stdout)

    def test_completion_json_includes_schema(self) -> None:
        result = self.run_cli("--json", "completion", "bash")
        report = json.loads(result.stdout)
        self.assertEqual(report["schema"], "cleanmac.completion-script.v1")
        self.assertEqual(report["shell"], "bash")
        self.assertIn("_cleanmac_completion", report["script_content"])

    def test_ai_tools_exports_provider_specific_tool_formats(self) -> None:
        openai_result = self.run_cli("ai-tools", "--format", "openai")
        openai_report = json.loads(openai_result.stdout)
        self.assertEqual(openai_report["schema"], "cleanmac.ai-openai-functions.v1")
        self.assertTrue(all(tool["type"] == "function" for tool in openai_report["tools"]))
        self.assertIn("function", openai_report["tools"][0])

        anthropic_result = self.run_cli("ai-tools", "--format", "anthropic")
        anthropic_report = json.loads(anthropic_result.stdout)
        self.assertEqual(anthropic_report["schema"], "cleanmac.ai-anthropic-tools.v1")
        self.assertIn("input_schema", anthropic_report["tools"][0])

        all_result = self.run_cli("ai-tools")
        all_report = json.loads(all_result.stdout)
        self.assertEqual(all_report["schema"], "cleanmac.ai-tools.v1")
        self.assertEqual(all_report["openai"]["schema"], "cleanmac.ai-openai-functions.v1")
        self.assertEqual(all_report["anthropic"]["schema"], "cleanmac.ai-anthropic-tools.v1")

        # === Anthropic-specific schema assertions ===
        anthropic_tools = anthropic_report["tools"]
        for tool in anthropic_tools:
            self.assertIn("name", tool)
            self.assertIn("description", tool)
            self.assertIn("input_schema", tool)
            self.assertIsInstance(tool["input_schema"], dict)
            self.assertEqual(tool["input_schema"]["type"], "object")
            self.assertIn("properties", tool["input_schema"])
            self.assertFalse(tool["input_schema"].get("additionalProperties", False))
            self.assertTrue(tool["name"].startswith("cleanmac_"))

        EXPECTED_TOOL_COUNT = 22
        self.assertEqual(len(anthropic_tools), EXPECTED_TOOL_COUNT)
        self.assertEqual(len(openai_report["tools"]), EXPECTED_TOOL_COUNT)

    def test_list_shows_categories(self) -> None:
        result = self.run_cli("list")
        self.assertIn("trash", result.stdout)
        self.assertIn("imessage", result.stdout)
        self.assertIn("Spotlight", result.stdout)

    def test_list_json_includes_category_metadata(self) -> None:
        result = self.run_cli("--json", "list")
        report = json.loads(result.stdout)
        self.assertEqual(report["schema"], "cleanmac.category-list.v1")
        self.assertIn("categories", report)
        by_key = {row["key"]: row for row in report["categories"]}

        self.assertEqual(len(report["categories"]), len(cleancli.CATEGORIES))
        self.assertIn("Deletes all files", by_key["trash"]["description"])
        self.assertTrue(by_key["trash"]["default"])
        self.assertTrue(by_key["incompleteDownloads"]["default"])
        self.assertFalse(by_key["downloads"]["default"])
        self.assertEqual(by_key["mails"]["default_older_than_days"], 30)
        self.assertIn("Archives", ",".join(by_key["xcode"]["paths"]))
        self.assertEqual(by_key["deviceFirmware"]["default_older_than_days"], 30)
        self.assertIn("Rosetta", by_key["appleSiliconCaches"]["title"])
        self.assertIn("Group Container", by_key["groupContainerCaches"]["title"])
        self.assertIn("Android Studio", by_key["androidStudio"]["title"])
        self.assertIn("JetBrains", by_key["jetbrains"]["title"])
        self.assertIn("Docker", by_key["docker"]["title"])
        self.assertEqual(by_key["gpuCaches"]["provider"], "gpu-cache")
        self.assertTrue(by_key["imessage"]["full_disk_access"])

    def test_quiet_suppresses_human_readable_output_but_not_json(self) -> None:
        quiet_result = self.run_cli("-q", "list")
        self.assertEqual(quiet_result.stdout.strip(), "")

        json_result = self.run_cli("-q", "--json", "list")
        report = json.loads(json_result.stdout)
        self.assertEqual(report["schema"], "cleanmac.category-list.v1")
        self.assertGreater(len(report["categories"]), 0)

    def test_capabilities_describes_commands_and_safety_model(self) -> None:
        result = self.run_cli("--json", "capabilities")
        report = json.loads(result.stdout)

        self.assertEqual(report["category_count"], len(cleancli.CATEGORIES))
        self.assertIn("clean", report["commands"])
        self.assertIn("software", report["commands"])
        self.assertIn("optimize", report["commands"])
        self.assertIn("status", report["commands"])
        self.assertIn("validate-plan", report["commands"])
        self.assertEqual(report["preferred_command_style"], "grouped")
        self.assertTrue(report["flat_command_compatibility"])
        self.assertIn("clean", report["command_groups"])
        self.assertIn("software", report["command_groups"])
        self.assertIn("status snapshot", report["command_groups"]["status"]["commands"])
        self.assertNotIn("par" + "ity", report["commands"])
        self.assertTrue(report["safety_guardrails"]["dry_run_default"])
        self.assertEqual(report["safety_guardrails"]["bundle_allowlist_flag"], "clean --bundle-allowlist")
        self.assertEqual(report["safety_guardrails"]["bundle_blocklist_flag"], "clean --bundle-blocklist")
        self.assertEqual(report["safety_guardrails"]["trash_routing_flag"], "clean --delete-mode trash")
        self.assertEqual(report["safety_guardrails"]["operation_log_flag"], "clean --operation-log")
        self.assertEqual(report["safety_guardrails"]["default_operation_log_file"], cleancli.OPERATIONS_LOG_FILE)
        self.assertEqual(
            report["safety_guardrails"]["log_rotation"]["operations_log_rotate_bytes"],
            5 * 1024 * 1024,
        )
        self.assertIn("deviceFirmware", report["safety_guardrails"]["deep_system_cleanup_categories"])
        self.assertIn("appleSiliconCaches", report["safety_guardrails"]["deep_system_cleanup_categories"])
        self.assertGreaterEqual(report["safety_guardrails"]["default_protected_bundle_count"], 40)
        self.assertIn(
            "groupContainerCaches",
            {row["key"] for row in report["command_groups"]["clean"].get("categories", [])}
            if "categories" in report["command_groups"]["clean"]
            else {category.key for category in cleancli.CATEGORIES},
        )
        self.assertIn("CrowdStrike", report["safety_guardrails"]["official_uninstaller_vendors"])
        self.assertIn("CLEANMAC_TEST_NO_AUTH", report["safety_guardrails"]["test_mode_environment"]["no_auth"])
        self.assertIn("com.apple.mail", report["safety_guardrails"]["default_protected_bundle_ids"])
        self.assertEqual(
            report["safety_guardrails"]["deletion_budget_flag"],
            "clean --max-delete-mb",
        )
        self.assertTrue(report["safety_guardrails"]["private_path_allowlist_enabled"])
        self.assertTrue(report["safety_guardrails"]["symlink_target_validation_enabled"])
        self.assertIn("gpuCaches", report["safety_guardrails"]["dynamic_provider_categories"])
        boundaries = report["boundary_governance"]
        self.assertEqual(boundaries["schema"], "cleanmac.boundary-governance.v1")
        self.assertIn("clean --execute", boundaries["forbidden_automation"])
        self.assertIn("--allow-live-root", boundaries["forbidden_automation"])
        self.assertIn("make docs-smoke", boundaries["verification"]["required_commands"])
        self.assertIn("make governance-smoke", boundaries["verification"]["required_commands"])
        self.assertIn("make open-source-smoke", boundaries["verification"]["required_commands"])
        self.assertIn("make bundle-audit-smoke", boundaries["verification"]["required_commands"])
        self.assertIn("make macos-smoke", boundaries["verification"]["required_commands"])
        self.assertIn("make security-smoke", boundaries["verification"]["required_commands"])
        self.assertTrue(boundaries["verification"]["python_test_environment"]["requires_virtualenv"])
        self.assertEqual(
            boundaries["verification"]["python_test_environment"]["workflow_python_env"],
            "PYTHON=.venv/bin/python",
        )
        self.assertEqual(
            report["safety_guardrails"]["bundle_drift_audit"]["command"],
            "python3 scripts/audit_bundle_drift.py --json --fail-on-drift",
        )
        distribution_governance = report["safety_guardrails"]["distribution_governance"]
        self.assertEqual(distribution_governance["schema"], "cleanmac.distribution-governance.v1")
        self.assertIn("standalone-zipapp", distribution_governance["supported_artifacts"])
        self.assertEqual(distribution_governance["release_manifest"], "release-assets/ARTIFACT-MANIFEST.json")
        self.assertEqual(distribution_governance["homebrew_formula_policy"]["status"], "preflight-only")
        self.assertFalse(distribution_governance["homebrew_formula_policy"]["publish_automatically"])
        self.assertEqual(
            report["safety_guardrails"]["privileged_command_ownership"]["scan_command"],
            "python3 scripts/security_scan.py",
        )
        ai_contract = report["ai_tool_contract"]
        self.assertEqual(ai_contract["schema"], "cleanmac.ai-tool-contract.v1")
        self.assertTrue(ai_contract["default_invocation"]["json_required"])
        self.assertEqual(ai_contract["default_invocation"]["preferred_command_style"], "grouped")
        self.assertIn("clean inspect", ai_contract["auto_call_allowed"])
        self.assertIn("clean plan", ai_contract["auto_call_allowed"])
        self.assertIn("clean run --execute", ai_contract["confirmation_required"])
        self.assertIn("clean open --execute", ai_contract["confirmation_required"])
        self.assertIn("rm " + "-rf", ai_contract["forbidden"])
        self.assertIn("osascript", ai_contract["forbidden"])
        self.assertTrue(ai_contract["execution_requirements"]["confirmation_token_supported"])
        self.assertIn(
            "--require-plan-context",
            ai_contract["execution_requirements"]["ai_originated_plan_requires"],
        )
        self.assertEqual(ai_contract["error_taxonomy_schema"], "cleanmac.ai-error.v1")
        error_codes = {row["code"] for row in report["ai_error_taxonomy"]}
        self.assertIn("CLI_ARGUMENT_ERROR", error_codes)
        self.assertIn("UNKNOWN_CATEGORY", error_codes)
        self.assertIn("CONFIRMATION_TOKEN_MISMATCH", error_codes)
        stale_error = next(row for row in report["ai_error_taxonomy"] if row["code"] == "PLAN_STALE_OR_DRIFTED")
        self.assertFalse(stale_error["safe_to_auto_retry"])
        self.assertIn("cleanmac_generate_plan", stale_error["next_allowed_tools"])
        llm_guide = report["llm_invocation_guide"]
        self.assertEqual(llm_guide["schema"], "cleanmac.llm-invocation-guide.v1")
        self.assertEqual(llm_guide["must_start_with"], "cleanmac_capabilities")
        self.assertIn("cleanmac_execute_plan", llm_guide["never_call_directly"])
        self.assertIn("cleanmac_policy_simulate", llm_guide["mandatory_before_execute"])
        self.assertIn("PLAN_STALE_OR_DRIFTED", llm_guide["safe_retry_rules"])
        prompt_policy = report["prompt_injection_policy"]
        self.assertEqual(prompt_policy["schema"], "cleanmac.prompt-injection-policy.v1")
        self.assertTrue(prompt_policy["file_names_are_data_not_instructions"])
        self.assertTrue(prompt_policy["ai_must_ignore_instructions_inside_paths"])
        plan_policy = report["plan_policy"]
        self.assertEqual(plan_policy["schema"], "cleanmac.plan-policy.v1")
        self.assertTrue(plan_policy["ai_originated_plan_requires_freshness_check"])
        self.assertEqual(plan_policy["max_age_seconds"], cleancli.PLAN_MAX_AGE_SECONDS)
        workflow = report["ai_recommended_workflow"]
        self.assertEqual(workflow[0]["step"], "discover")
        self.assertEqual(workflow[-1]["step"], "execute")
        self.assertFalse(workflow[-1]["auto_call_allowed"])
        self.assertTrue(workflow[-1]["requires_user_confirmation"])
        self.assertIn("--execute", workflow[-1]["command_template"])
        self.assertIn("--require-confirmation-token", workflow[-1]["command_template"])
        plan_step = next(row for row in workflow if row["step"] == "plan")
        self.assertIn("--ai-origin", plan_step["command_template"])
        dry_run_step = next(row for row in workflow if row["step"] == "dry_run")
        self.assertTrue(dry_run_step["auto_call_allowed"])
        self.assertNotIn("--execute", dry_run_step["command_template"])
        self.assertIn("--require-plan-context", dry_run_step["command_template"])
        confirm_step = next(row for row in workflow if row["step"] == "confirm")
        self.assertFalse(confirm_step["auto_call_allowed"])
        self.assertTrue(confirm_step["auto_prepare_allowed"])
        intents = {row["intent"]: row for row in report["ai_intent_hints"]}
        self.assertIn("developer_cache_cleanup", intents)
        self.assertIn("nodePackageCaches", intents["developer_cache_cleanup"]["recommended_categories"])
        self.assertIn("browser_cache_cleanup", intents)
        self.assertIn("browserCodeSignCache", intents["browser_cache_cleanup"]["recommended_categories"])
        self.assertIn("xcode_cleanup", intents)
        self.assertIn("warning", intents["xcode_cleanup"])
        function_schemas = report["ai_function_schemas"]
        self.assertEqual(function_schemas["schema"], "cleanmac.ai-function-schemas.v1")
        tool_names = {tool["name"] for tool in function_schemas["tools"]}
        self.assertIn("cleanmac_generate_plan", tool_names)
        self.assertIn("cleanmac_execute_plan", tool_names)
        self.assertIn("cleanmac_policy_simulate", tool_names)
        self.assertIn("cleanmac_workflow", tool_names)
        self.assertIn("cleanmac_software_uninstall_plan", tool_names)
        execute_tool = next(tool for tool in function_schemas["tools"] if tool["name"] == "cleanmac_execute_plan")
        self.assertEqual(execute_tool["risk"], "destructive")
        self.assertTrue(execute_tool["requires_confirmation"])
        self.assertFalse(execute_tool["auto_call_allowed"])
        self.assertIn("confirmation_phrase", execute_tool["parameters"]["required"])
        self.assertIn("confirmation_token", execute_tool["parameters"]["required"])
        self.assertNotIn("shell", json.dumps(execute_tool["parameters"]))
        openai_functions = report["ai_openai_functions"]
        self.assertEqual(openai_functions["schema"], "cleanmac.ai-openai-functions.v1")
        self.assertEqual({tool["function"]["name"] for tool in openai_functions["tools"]}, tool_names)
        self.assertTrue(all(tool["type"] == "function" for tool in openai_functions["tools"]))
        anthropic_tools = report["ai_anthropic_tools"]
        self.assertEqual(anthropic_tools["schema"], "cleanmac.ai-anthropic-tools.v1")
        self.assertEqual({tool["name"] for tool in anthropic_tools["tools"]}, tool_names)
        provider_parity = report["ai_provider_export_parity"]
        self.assertEqual(provider_parity["schema"], "cleanmac.ai-provider-export-parity.v1")
        self.assertTrue(provider_parity["same_tool_names"], provider_parity["violations"])
        self.assertEqual(provider_parity["violation_count"], 0)
        readiness = report["ai_readiness"]
        self.assertEqual(readiness["schema"], "cleanmac.ai-readiness.v1")
        self.assertTrue(readiness["ready"], readiness)
        mcp_catalog = report["mcp_tool_catalog"]
        self.assertEqual(mcp_catalog["schema"], "cleanmac.mcp-tool-catalog.v1")
        self.assertEqual({tool["name"] for tool in mcp_catalog["tools"]}, tool_names)
        self.assertTrue(all(tool["invocation"]["mode"] == "argv" for tool in mcp_catalog["tools"]))
        self.assertTrue(all(not tool["invocation"].get("uses_shell", True) for tool in mcp_catalog["tools"]))
        schema_validation = report["ai_schema_validation"]
        self.assertEqual(schema_validation["schema"], "cleanmac.ai-schema-validation.v1")
        self.assertTrue(schema_validation["valid"], schema_validation["violations"])
        self.assertEqual(schema_validation["tool_count"], len(tool_names))
        self.assertIn("cleanmac_execute_plan", schema_validation["destructive_tools"])
        contract_compatibility = report["ai_contract_compatibility"]
        self.assertEqual(contract_compatibility["schema"], "cleanmac.ai-contract-compatibility.v1")
        self.assertTrue(contract_compatibility["compatible"], contract_compatibility["violations"])
        self.assertEqual(contract_compatibility["function_tool_count"], len(tool_names))
        self.assertEqual(contract_compatibility["mcp_tool_count"], len(tool_names))
        manual_ids = {row["id"] for row in boundaries["manual_only_behaviors"]}
        self.assertIn("destructive-clean-execution", manual_ids)

    def test_provider_export_parity_reports_same_tool_names(self) -> None:
        ai_schema = importlib.import_module("cleancli.ai_schema")
        report = ai_schema.render_provider_export_parity()

        self.assertEqual(report["schema"], "cleanmac.ai-provider-export-parity.v1")
        self.assertTrue(report["same_tool_names"], report["violations"])
        self.assertTrue(report["same_tool_count"], report["violations"])
        self.assertEqual(report["violation_count"], 0)

    def test_ai_schema_builds_safe_argv_without_shell_or_implicit_execute(self) -> None:
        ai_schema = importlib.import_module("cleancli.ai_schema")

        schemas = ai_schema.render_function_schemas()
        validation = ai_schema.validate_ai_tool_definitions()
        by_name = {tool["name"]: tool for tool in schemas["tools"]}

        self.assertEqual(validation["schema"], "cleanmac.ai-schema-validation.v1")
        self.assertTrue(validation["valid"], validation["violations"])
        self.assertEqual(validation["tool_count"], len(schemas["tools"]))
        self.assertIn("cleanmac_execute_plan", validation["destructive_tools"])
        self.assertIn("cleanmac_inspect", by_name)
        self.assertIn("cleanmac_execute_plan", by_name)
        self.assertFalse(by_name["cleanmac_inspect"]["requires_confirmation"])
        self.assertTrue(by_name["cleanmac_execute_plan"]["requires_confirmation"])
        self.assertNotIn("operation_log", by_name["cleanmac_execute_plan"]["parameters"]["required"])
        self.assertNotIn("require_plan_context", by_name["cleanmac_execute_plan"]["parameters"]["required"])
        self.assertEqual(
            by_name["cleanmac_execute_plan"]["parameters"]["properties"]["require_plan_context"]["default"], True
        )
        self.assertEqual(
            ai_schema.build_tool_argv("cleanmac_generate_plan", {"categories": ["trash", "downloads"], "max_items": 5}),
            [
                "cleanmac",
                "--json",
                "clean",
                "plan",
                "--categories",
                "trash,downloads",
                "--ai-origin",
                "--max-items",
                "5",
            ],
        )
        self.assertEqual(
            ai_schema.build_tool_argv("cleanmac_dry_run_plan", {"plan_file": "/tmp/plan.json"}),
            [
                "cleanmac",
                "--json",
                "clean",
                "run",
                "--plan-file",
                "/tmp/plan.json",
                "--require-plan-context",
                "--delete-mode",
                "trash",
            ],
        )
        self.assertEqual(
            ai_schema.build_tool_argv(
                "cleanmac_policy_simulate", {"plan_file": "/tmp/plan.json", "execute": True, "delete_mode": "trash"}
            ),
            [
                "cleanmac",
                "--json",
                "clean",
                "policy-simulate",
                "--plan-file",
                "/tmp/plan.json",
                "--execute",
                "--delete-mode",
                "trash",
                "--require-plan-context",
            ],
        )
        with self.assertRaisesRegex(ValueError, "requires explicit user confirmation"):
            ai_schema.build_tool_argv("cleanmac_execute_plan", {"plan_file": "/tmp/plan.json"})
        self.assertEqual(
            ai_schema.build_tool_argv(
                "cleanmac_execute_plan",
                {
                    "plan_file": "/tmp/plan.json",
                    "confirmation_phrase": "确认执行 cleanmac 清理",
                    "confirmation_token": "cleanmac-confirm-test",
                },
            ),
            [
                "cleanmac",
                "--json",
                "clean",
                "run",
                "--plan-file",
                "/tmp/plan.json",
                "--require-plan-context",
                "--delete-mode",
                "trash",
                "--execute",
                "--yes",
                "--operation-log",
                cleancli.OPERATIONS_LOG_FILE,
                "--require-confirmation-token",
                "--confirmation-token",
                "cleanmac-confirm-test",
            ],
        )
        with self.assertRaisesRegex(ValueError, "Unknown cleanmac AI tool"):
            ai_schema.build_tool_argv("shell", {"command": "rm -rf /"})

    def test_clean_reports_ai_confirmation_summary_for_dry_run_and_execute(self) -> None:
        tmp, root, home = self.make_sandbox()
        with tmp:
            dry_run = self.run_cli(
                "--root",
                str(root),
                "--home",
                str(home),
                "--json",
                "clean",
                "run",
                "--categories",
                "trash,downloads",
                "--delete-mode",
                "trash",
                "--max-items",
                "10",
                "--max-delete-mb",
                "5",
            )
            dry_report = json.loads(dry_run.stdout)
            summary = dry_report["ai_confirmation_summary"]

            self.assertTrue(summary["requires_confirmation"])
            self.assertEqual(summary["recommended_confirmation_phrase"], "确认执行 cleanmac 清理")
            self.assertTrue(summary["confirmation_token"].startswith("cleanmac-confirm-"))
            self.assertEqual(summary["confirmation_token_context"]["delete_mode"], "trash")
            self.assertEqual(summary["confirmation_token_context"]["max_items"], 10)
            self.assertEqual(summary["delete_mode"], "trash")
            self.assertEqual(summary["operation_log"], cleancli.OPERATIONS_LOG_FILE)
            self.assertEqual(summary["estimated_reclaimable_bytes"], dry_report["total_bytes"])
            self.assertEqual(summary["category_count"], 2)
            self.assertEqual(summary["item_count"], len(dry_report["items"]))
            self.assertEqual(summary["skipped_count"], dry_report["skipped_count"])
            self.assertEqual(summary["recommended_next_action"], "ask_user_confirmation")
            self.assertFalse(summary["safe_to_auto_execute"])
            self.assertIn("trash", summary["selected_categories"])
            self.assertIn("downloads", summary["selected_categories"])
            ai_summary = dry_report["ai_summary"]
            self.assertEqual(ai_summary["schema"], "cleanmac.ai-summary.v1")
            self.assertEqual(ai_summary["phase"], "clean-dry-run")
            self.assertEqual(ai_summary["recommended_next_action"], "ask_user_confirmation")
            self.assertTrue(ai_summary["safe_to_execute_after_confirmation"])
            self.assertIn("Trash", " ".join(ai_summary["reasons"]))

            execute = self.run_cli(
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
            )
            execute_report = json.loads(execute.stdout)
            execute_summary = execute_report["ai_confirmation_summary"]
            execute_ledger = execute_report["ai_execution_ledger"]

            self.assertFalse(execute_summary["requires_confirmation"])
            self.assertEqual(execute_summary["recommended_next_action"], "review_operation_log")
            self.assertEqual(
                execute_summary["deleted_count"], sum(1 for row in execute_report["items"] if row["deleted"])
            )
            self.assertEqual(execute_summary["operation_log"], execute_report["operation_log"])
            self.assertEqual(execute_ledger["schema"], "cleanmac.ai-execution-ledger.v1")
            self.assertEqual(execute_ledger["phase"], "clean-execute")
            self.assertEqual(execute_ledger["confirmation"]["token_validated"], False)
            self.assertEqual(execute_ledger["operation_log"]["status"], "ready")
            self.assertTrue(execute_ledger["operation_log"]["ready"])
            self.assertEqual(execute_report["ai_summary"]["phase"], "clean-execute")
            self.assertEqual(execute_report["ai_summary"]["recommended_next_action"], "review_operation_log")

    def test_ai_confirmation_token_is_required_and_bound_before_execute(self) -> None:
        tmp, root, home = self.make_sandbox()
        with tmp:
            dry_run = self.run_cli(
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
                "--max-items",
                "10",
                "--max-delete-mb",
                "5",
            )
            token = json.loads(dry_run.stdout)["ai_confirmation_summary"]["confirmation_token"]
            candidate = root / "Users/tester/Downloads/download.bin"

            missing = self.run_cli_unchecked(
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
                "--max-items",
                "10",
                "--max-delete-mb",
                "5",
                "--execute",
                "--yes",
                "--require-confirmation-token",
            )
            self.assertNotEqual(missing.returncode, 0)
            self.assertIn("confirmation token", missing.stderr)
            self.assertTrue(candidate.exists())

            mismatch = self.run_cli_unchecked(
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
                "--max-items",
                "99",
                "--max-delete-mb",
                "5",
                "--execute",
                "--yes",
                "--require-confirmation-token",
                "--confirmation-token",
                token,
            )
            self.assertNotEqual(mismatch.returncode, 0)
            self.assertIn("confirmation token mismatch", mismatch.stderr)
            self.assertTrue(candidate.exists())

            execute = self.run_cli(
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
                "--max-items",
                "10",
                "--max-delete-mb",
                "5",
                "--execute",
                "--yes",
                "--require-confirmation-token",
                "--confirmation-token",
                token,
            )
            report = json.loads(execute.stdout)

            self.assertFalse(candidate.exists())
            self.assertTrue(report["ai_confirmation_summary"]["confirmation_token_validated"])

    def test_ai_confirmation_token_boundary_conditions(self) -> None:
        from cleancli.core import CATEGORIES, ai_confirmation_token, ai_confirmation_token_context

        cats = [c for c in CATEGORIES if c.key in ("trash", "downloads")]
        base: dict[str, Any] = {
            "categories": cats,
            "root": Path("/sandbox"),
            "home": Path("/Users/tester"),
            "risk_policy": "default",
            "max_delete_mb": 10.0,
            "max_items": 5,
            "include_patterns": [],
            "exclude_patterns": [],
            "older_than_days": None,
            "min_size_mb": 0,
            "name_regex": None,
            "bundle_allowlist": [],
            "bundle_blocklist": ["com.apple.mail"],
            "delete_mode": "trash",
            "plan_file": None,
            "rows": [],
        }
        ctx = ai_confirmation_token_context(**base)
        token = ai_confirmation_token(ctx)

        # Token format: cleanmac-confirm-<32 hex chars>
        self.assertTrue(token.startswith("cleanmac-confirm-"))
        hex_part = token[len("cleanmac-confirm-") :]
        self.assertEqual(len(hex_part), 32)
        self.assertTrue(all(c in "0123456789abcdef" for c in hex_part))

        # Determinism: same context -> same token
        ctx2 = ai_confirmation_token_context(**base)
        token2 = ai_confirmation_token(ctx2)
        self.assertEqual(token, token2)

        # Context sensitivity: different root -> different token
        diff_root = dict(base, root=Path("/other"))
        diff_root_token = ai_confirmation_token(ai_confirmation_token_context(**diff_root))
        self.assertNotEqual(token, diff_root_token)

        # Different categories -> different token
        single_cat = dict(base, categories=[c for c in CATEGORIES if c.key == "trash"])
        single_cat_token = ai_confirmation_token(ai_confirmation_token_context(**single_cat))
        self.assertNotEqual(token, single_cat_token)

        # Different home -> different token
        diff_home = dict(base, home=Path("/Users/other"))
        diff_home_token = ai_confirmation_token(ai_confirmation_token_context(**diff_home))
        self.assertNotEqual(token, diff_home_token)

        # Empty context generates valid format too
        empty_ctx = ai_confirmation_token_context(
            categories=[],
            root=Path("/"),
            home=Path("/"),
            risk_policy="default",
            max_delete_mb=None,
            max_items=None,
            include_patterns=[],
            exclude_patterns=[],
            older_than_days=None,
            min_size_mb=0,
            name_regex=None,
            bundle_allowlist=[],
            bundle_blocklist=[],
            delete_mode="permanent",
            plan_file=None,
            rows=[],
        )
        empty_token = ai_confirmation_token(empty_ctx)
        self.assertTrue(empty_token.startswith("cleanmac-confirm-"))
        self.assertEqual(len(empty_token[len("cleanmac-confirm-") :]), 32)

    def test_json_errors_emit_ai_safe_error_taxonomy(self) -> None:
        tmp, root, home = self.make_sandbox()
        with tmp:
            unknown_category = self.run_cli_unchecked(
                "--root",
                str(root),
                "--home",
                str(home),
                "--json",
                "clean",
                "run",
                "--categories",
                "doesNotExist",
            )
            unknown_report = json.loads(unknown_category.stderr)

            self.assertNotEqual(unknown_category.returncode, 0)
            self.assertEqual(unknown_report["schema"], "cleanmac.ai-error.v1")
            self.assertFalse(unknown_report["ok"])
            self.assertFalse(unknown_report["destructive_operation_started"])
            self.assertEqual(unknown_report["error"]["code"], "UNKNOWN_CATEGORY")
            self.assertEqual(unknown_report["error"]["category"], "invalid_category")
            self.assertEqual(
                unknown_report["error"]["suggested_next_action"], "call_capabilities_or_clean_list_then_retry"
            )
            self.assertIn("Unknown category: doesNotExist", unknown_report["error"]["message"])

            missing_token = self.run_cli_unchecked(
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
                "--require-confirmation-token",
            )
            missing_token_report = json.loads(missing_token.stderr)

            self.assertNotEqual(missing_token.returncode, 0)
            self.assertEqual(missing_token_report["error"]["code"], "CONFIRMATION_TOKEN_REQUIRED")
            self.assertEqual(missing_token_report["error"]["category"], "confirmation_required")
            self.assertFalse(missing_token_report["safe_to_auto_retry"])
            self.assertTrue((root / "Users/tester/Downloads/download.bin").exists())

            bad_argument = self.run_cli_unchecked("--json", "clean", "run", "--definitely-unknown")
            bad_argument_report = json.loads(bad_argument.stderr)

            self.assertNotEqual(bad_argument.returncode, 0)
            self.assertEqual(bad_argument_report["error"]["code"], "CLI_ARGUMENT_ERROR")
            self.assertEqual(bad_argument_report["error"]["exit_code"], 2)
            self.assertIn("unrecognized arguments", bad_argument_report["error"]["message"])

    def test_grouped_clean_commands_match_flat_alias_reports(self) -> None:
        tmp, root, home = self.make_sandbox()
        with tmp:
            flat_alias = self.run_cli(
                "--root", str(root), "--home", str(home), "--json", "inspect", "--categories", "trash"
            )
            grouped = self.run_cli(
                "--root", str(root), "--home", str(home), "--json", "clean", "inspect", "--categories", "trash"
            )
            flat_alias_report = json.loads(flat_alias.stdout)
            grouped_report = json.loads(grouped.stdout)

            self.assertEqual(grouped_report["total_candidates"], flat_alias_report["total_candidates"])
            self.assertEqual(grouped_report["items"], flat_alias_report["items"])

    def test_grouped_clean_run_executes_dry_run_alias(self) -> None:
        tmp, root, home = self.make_sandbox()
        with tmp:
            result = self.run_cli(
                "--root", str(root), "--home", str(home), "--json", "clean", "run", "--categories", "trash"
            )
            report = json.loads(result.stdout)

            self.assertTrue(report["dry_run"])
            self.assertEqual(report["selected_categories"][0]["key"], "trash")
            self.assertTrue((root / "Users/tester/.Trash/old.tmp").exists())

    def test_grouped_analyze_tree_reports_largest_entries(self) -> None:
        tmp, root, home = self.make_sandbox()
        with tmp:
            result = self.run_cli(
                "--root",
                str(root),
                "--home",
                str(home),
                "--json",
                "analyze",
                "tree",
                "--path",
                "/Users/tester",
                "--depth",
                "1",
                "--top",
                "5",
            )
            report = json.loads(result.stdout)

            self.assertEqual(report["schema"], "cleanmac.analyze-tree.v1")
            self.assertFalse(report["destructive"])
            self.assertTrue(report["exists"])
            self.assertLessEqual(report["shown_entries"], 5)

    def test_analyze_group_rejects_non_cli_view_action(self) -> None:
        removed_action = "t" + "ui"
        result = self.run_cli_unchecked("--json", "analyze", removed_action, "--path", ".")

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("unrecognized arguments", result.stderr)

    def test_software_optimize_and_status_grouped_commands_are_safe(self) -> None:
        tmp, root, home = self.make_sandbox()
        with tmp:
            software = json.loads(
                self.run_cli(
                    "--root", str(root), "--home", str(home), "--json", "software", "uninstall-plan", "--app", "Demo"
                ).stdout
            )
            optimize = json.loads(self.run_cli("--json", "optimize", "plan").stdout)
            status = json.loads(self.run_cli("--root", str(root), "--json", "status", "snapshot").stdout)

            self.assertEqual(software["schema"], "cleanmac.software.v1")
            self.assertFalse(software["destructive"])
            self.assertEqual(software["uninstall_plan"]["app"], "Demo")
            self.assertEqual(optimize["schema"], "cleanmac.optimize.v1")
            self.assertFalse(optimize["execution_supported"])
            self.assertEqual(status["schema"], "cleanmac.status.snapshot.v1")
            self.assertIn("disk", status)

    def test_doctor_reports_environment_and_full_disk_access_guidance(self) -> None:
        result = self.run_cli("--json", "doctor")
        report = json.loads(result.stdout)

        self.assertEqual(report["schema"], "cleanmac.doctor.v1")
        self.assertFalse(report["destructive"])
        self.assertIn("platform", report)
        self.assertIn("python", report)
        self.assertIn("full_disk_access", report["checks"])
        self.assertIn("live_root_execution", report["checks"])
        self.assertIn("private_path_policy", report["checks"])
        self.assertIn("lsof_available", report["checks"])
        self.assertIn("getconf_available", report["checks"])

    def test_unknown_category_is_rejected_with_valid_category_guidance(self) -> None:
        result = self.run_cli_unchecked("list", "--categories", "doesNotExist")

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("unrecognized arguments", result.stderr)

        result = self.run_cli_unchecked("inspect", "--categories", "doesNotExist")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Unknown category: doesNotExist", result.stderr)
        self.assertIn("trash", result.stderr)
        self.assertIn("imessage", result.stderr)

    def test_open_reports_special_finder_targets(self) -> None:
        tmp, root, home = self.make_sandbox()
        with tmp:
            result = self.run_cli(
                "--root",
                str(root),
                "--home",
                str(home),
                "--json",
                "open",
                "--categories",
                "terminal,userAppLogs,userAppCache,trash",
            )
            report = json.loads(result.stdout)
            targets = {row["category"]: row for row in report["targets"]}

            self.assertTrue(report["dry_run"])
            self.assertTrue(targets["terminal"]["special_case"])
            self.assertTrue(targets["terminal"]["path"].endswith("/private/var/log/asl"))
            self.assertIn(".CleanMacAppLogLinks", targets["userAppLogs"]["path"])
            self.assertIn(".CleanMacAppCacheLinks", targets["userAppCache"]["path"])
            self.assertTrue(targets["trash"]["path"].endswith("/Users/tester/.Trash"))

    def test_links_reports_symbolic_link_mappings(self) -> None:
        tmp, root, home = self.make_sandbox()
        with tmp:
            result = self.run_cli(
                "--root",
                str(root),
                "--home",
                str(home),
                "--json",
                "links",
            )
            report = json.loads(result.stdout)

            self.assertTrue(report["dry_run"])
            self.assertEqual(report["mode"], "create-update")
            self.assertEqual({row["kind"] for row in report["mappings"]}, {"logs", "cache"})
            self.assertFalse((root / "Users/tester/.CleanMacAppLogLinks").exists())

    def test_links_execute_creates_and_removes_symlink_dirs(self) -> None:
        tmp, root, home = self.make_sandbox()
        with tmp:
            logs = root / "Users/tester/Library/Containers/com.example/Data/Library/Logs"
            self.run_cli(
                "--root",
                str(root),
                "--home",
                str(home),
                "links",
                "--kind",
                "logs",
                "--execute",
            )
            link_path = root / "Users/tester/.CleanMacAppLogLinks/com.example"
            self.assertTrue(link_path.is_symlink())
            self.assertEqual(link_path.resolve(), logs.resolve())

            result = self.run_cli(
                "--root",
                str(root),
                "--home",
                str(home),
                "--json",
                "links",
                "--kind",
                "logs",
                "--remove",
                "--execute",
            )
            report = json.loads(result.stdout)
            self.assertEqual(report["mode"], "remove")
            self.assertTrue(report["removed"][0]["removed"])
            self.assertFalse((root / "Users/tester/.CleanMacAppLogLinks").exists())

    def test_links_remove_dry_run_preserves_existing_link_directory(self) -> None:
        tmp, root, home = self.make_sandbox()
        with tmp:
            link_dir = root / "Users/tester/.CleanMacAppLogLinks"
            link_dir.mkdir(parents=True)

            result = self.run_cli(
                "--root",
                str(root),
                "--home",
                str(home),
                "--json",
                "links",
                "--kind",
                "logs",
                "--remove",
            )
            report = json.loads(result.stdout)

            self.assertTrue(report["dry_run"])
            self.assertEqual(report["mode"], "remove")
            self.assertTrue(report["removed"][0]["existed_before"])
            self.assertFalse(report["removed"][0]["removed"])
            self.assertTrue(link_dir.exists())

    def test_links_execute_skips_existing_non_symlink_mapping(self) -> None:
        tmp, root, home = self.make_sandbox()
        with tmp:
            link_path = root / "Users/tester/.CleanMacAppLogLinks/com.example"
            link_path.parent.mkdir(parents=True)
            link_path.mkdir()

            result = self.run_cli(
                "--root",
                str(root),
                "--home",
                str(home),
                "--json",
                "links",
                "--kind",
                "logs",
                "--execute",
            )
            report = json.loads(result.stdout)
            mapping = report["mappings"][0]

            self.assertEqual(mapping["status"], "skipped-existing-non-symlink")
            self.assertTrue(link_path.is_dir())
            self.assertFalse(link_path.is_symlink())

    def test_analyze_uses_sandbox_root(self) -> None:
        tmp, root, home = self.make_sandbox()
        with tmp:
            result = self.run_cli(
                "--root",
                str(root),
                "--home",
                str(home),
                "--json",
                "analyze",
                "--default",
            )
            report = json.loads(result.stdout)
            paths = "\n".join(target["path"] for target in report["targets"])

            self.assertGreater(report["total_bytes"], 0)
            self.assertIn("human", report["categories"][0])
            self.assertIn(str(root / "Users/tester/.Trash"), paths)

    def test_clean_defaults_to_dry_run(self) -> None:
        tmp, root, home = self.make_sandbox()
        with tmp:
            self.run_cli(
                "--root",
                str(root),
                "--home",
                str(home),
                "clean",
                "--categories",
                "trash",
            )
            self.assertTrue((root / "Users/tester/.Trash/old.tmp").exists())

    def test_clean_dry_run_includes_pre_clean_report(self) -> None:
        tmp, root, home = self.make_sandbox()
        with tmp:
            result = self.run_cli(
                "--root",
                str(root),
                "--home",
                str(home),
                "--json",
                "clean",
                "--categories",
                "trash,downloads",
            )
            report = json.loads(result.stdout)
            pre = report["pre_clean_report"]
            preview_by_key = {row["key"]: row for row in pre["category_preview"]}

            self.assertTrue(report["dry_run"])
            self.assertIsNone(report["post_clean_report"])
            self.assertEqual(pre["phase"], "pre-clean")
            self.assertEqual(pre["summary"]["selected_category_count"], 2)
            self.assertEqual(pre["summary"]["candidate_count"], 3)
            self.assertGreater(pre["summary"]["estimated_reclaimable_bytes"], 0)
            self.assertEqual(pre["summary"]["high_risk_categories"], ["downloads"])
            self.assertEqual(
                pre["cleanup_flow"]["progress_messages"],
                ["Cleaning...", "Finishing!", "Success!"],
            )
            self.assertEqual(preview_by_key["trash"]["candidate_count"], 1)
            self.assertEqual(preview_by_key["downloads"]["risk"], "high")
            self.assertTrue((root / "Users/tester/.Trash/old.tmp").exists())

    def test_pre_clean_report_notes_symbolic_link_refresh(self) -> None:
        tmp, root, home = self.make_sandbox()
        with tmp:
            result = self.run_cli(
                "--root",
                str(root),
                "--home",
                str(home),
                "--json",
                "clean",
                "--categories",
                "userAppLogs",
            )
            report = json.loads(result.stdout)
            symbolic = report["pre_clean_report"]["cleanup_flow"]["symbolic_link_refresh"]

            self.assertTrue(symbolic["enabled_when_selected"])
            self.assertEqual(symbolic["logs_link_dir"], "~/.CleanMacAppLogLinks/")

    def test_clean_execute_includes_post_clean_report(self) -> None:
        tmp, root, home = self.make_sandbox()
        with tmp:
            result = self.run_cli(
                "--root",
                str(root),
                "--home",
                str(home),
                "--json",
                "clean",
                "--categories",
                "trash,downloads",
                "--execute",
                "--yes",
            )
            report = json.loads(result.stdout)
            post = report["post_clean_report"]
            deltas = {row["key"]: row for row in post["category_deltas"]}
            preservation = {row["path"]: row for row in post["target_preservation"]}

            self.assertFalse(report["dry_run"])
            self.assertEqual(report["pre_clean_report"]["summary"]["candidate_count"], 3)
            self.assertEqual(post["phase"], "post-clean")
            self.assertEqual(post["summary"]["deleted_item_count"], 3)
            self.assertEqual(post["summary"]["remaining_reclaimable_bytes"], 0)
            self.assertGreater(deltas["trash"]["reclaimed_bytes"], 0)
            self.assertGreater(deltas["downloads"]["reclaimed_bytes"], 0)
            self.assertTrue(preservation[str(root / "Users/tester/.Trash")]["exists_after_clean"])
            self.assertTrue(preservation[str(root / "Users/tester/Downloads")]["exists_after_clean"])
            self.assertFalse((root / "Users/tester/.Trash/old.tmp").exists())
            self.assertFalse((root / "Users/tester/Downloads/download.bin").exists())

    def test_clean_human_output_shows_pre_and_post_reports(self) -> None:
        tmp, root, home = self.make_sandbox()
        with tmp:
            result = self.run_cli(
                "--root",
                str(root),
                "--home",
                str(home),
                "clean",
                "--categories",
                "trash",
                "--execute",
            )
            self.assertIn("Pre-clean report:", result.stdout)
            self.assertIn("Post-clean report:", result.stdout)
            self.assertIn("estimated reclaim", result.stdout)
            self.assertIn("estimated reclaimed", result.stdout)

    def test_clean_execute_removes_only_sandbox_contents(self) -> None:
        tmp, root, home = self.make_sandbox()
        with tmp:
            self.run_cli(
                "--root",
                str(root),
                "--home",
                str(home),
                "clean",
                "--categories",
                "trash,downloads",
                "--execute",
                "--yes",
            )
            self.assertFalse((root / "Users/tester/.Trash/old.tmp").exists())
            self.assertFalse((root / "Users/tester/Downloads/download.bin").exists())
            self.assertTrue((root / "Users/tester/.Trash").exists())
            self.assertTrue((root / "Users/tester/Downloads").exists())
            self.assertTrue((root / "Users/tester/Library/Developer/Xcode/DerivedData/App-a/cache.db").exists())

    def test_clean_writes_json_audit_report_file(self) -> None:
        tmp, root, home = self.make_sandbox()
        with tmp:
            audit_file = root / "cleanmac-audit.json"
            result = self.run_cli(
                "--root",
                str(root),
                "--home",
                str(home),
                "--report-file",
                str(audit_file),
                "--json",
                "clean",
                "--categories",
                "trash",
            )
            report = json.loads(result.stdout)
            audit = json.loads(audit_file.read_text())

            self.assertEqual(report["report_file"], str(audit_file))
            self.assertEqual(audit["schema"], "cleanmac.audit.v1")
            self.assertEqual(audit["command"], "clean")
            self.assertEqual(audit["root"], str(root))
            self.assertTrue(audit["dry_run"])
            self.assertIn("--report-file", audit["argv"])
            self.assertEqual(audit["selected_category_keys"], ["trash"])

    def test_clean_bundle_blocklist_protects_application_owned_candidates(self) -> None:
        tmp, root, home = self.make_sandbox()
        with tmp:
            result = self.run_cli(
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

            self.assertFalse(report["dry_run"])
            self.assertEqual(report["bundle_blocklist"], ["com.example"])
            self.assertEqual(report["total_bytes"], 0)
            self.assertEqual(report["skipped_summary"]["by_reason"]["bundle-blocklisted"], 1)
            self.assertTrue(
                (root / "Users/tester/Library/Containers/com.example/Data/Library/Caches/cache.bin").exists()
            )

    def test_clean_bundle_allowlist_skips_non_allowlisted_application_candidates(self) -> None:
        tmp, root, home = self.make_sandbox()
        with tmp:
            result = self.run_cli(
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

            self.assertTrue(report["dry_run"])
            self.assertEqual(report["bundle_allowlist"], ["com.allowed"])
            self.assertEqual(report["skipped_summary"]["by_reason"], {"bundle-not-allowlisted": 2})

    def test_container_cache_policy_preserves_protected_app_data(self) -> None:
        tmp, root, home = self.make_sandbox()
        with tmp:
            result = self.run_cli(
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

            self.assertIn(
                str(root / "Users/tester/Library/Containers/com.example/Data/Library/Caches/cache.bin"), item_paths
            )
            self.assertEqual(
                skipped_paths[
                    str(root / "Users/tester/Library/Containers/com.apple.Notes/Data/Library/Caches/cache.bin")
                ],
                "protected-container-data",
            )

    def test_group_container_policy_skips_apple_and_allows_non_protected_cache(self) -> None:
        tmp, root, home = self.make_sandbox()
        with tmp:
            result = self.run_cli(
                "--root",
                str(root),
                "--home",
                str(home),
                "--json",
                "clean",
                "inspect",
                "--categories",
                "groupContainerCaches",
                "--older-than-days",
                "0",
            )
            report = json.loads(result.stdout)
            item_paths = {row["path"] for row in report["items"]}
            skipped_reasons = {row["path"]: row["reason"] for row in report["skipped"]}

            self.assertIn(
                str(root / "Users/tester/Library/Group Containers/group.com.example.app/Library/Caches/cache.bin"),
                item_paths,
            )
            self.assertEqual(
                skipped_reasons[
                    str(root / "Users/tester/Library/Group Containers/group.com.apple.notes/Library/Caches/cache.bin")
                ],
                "protected-group-container",
            )

    def test_app_specific_cleanup_rules_cover_developer_tools(self) -> None:
        tmp, root, home = self.make_sandbox()
        with tmp:
            original_test_mode = os.environ.get("CLEANMAC_TEST_MODE")
            os.environ["CLEANMAC_TEST_MODE"] = "1"
            try:
                result = self.run_cli(
                    "--root",
                    str(root),
                    "--home",
                    str(home),
                    "--json",
                    "clean",
                    "inspect",
                    "--categories",
                    "androidStudio,jetbrains,vscode,docker",
                )
            finally:
                if original_test_mode is None:
                    os.environ.pop("CLEANMAC_TEST_MODE", None)
                else:
                    os.environ["CLEANMAC_TEST_MODE"] = original_test_mode
            report = json.loads(result.stdout)
            paths = {row["path"] for row in report["items"]}

            self.assertIn(str(root / "Users/tester/Library/Caches/Google/AndroidStudio2024.1/cache.bin"), paths)
            self.assertIn(str(root / "Users/tester/Library/Caches/JetBrains/IntelliJIdea2024.1/cache.bin"), paths)
            self.assertIn(str(root / "Users/tester/Library/Application Support/Code/Cache/cache.bin"), paths)
            self.assertIn(str(root / "Users/tester/Library/Caches/com.docker.docker/cache.bin"), paths)

    def test_app_specific_cleanup_rules_cover_browser_collaboration_and_package_caches(self) -> None:
        tmp, root, home = self.make_sandbox()
        with tmp:
            original_test_mode = os.environ.get("CLEANMAC_TEST_MODE")
            os.environ["CLEANMAC_TEST_MODE"] = "1"
            try:
                result = self.run_cli(
                    "--root",
                    str(root),
                    "--home",
                    str(home),
                    "--json",
                    "clean",
                    "inspect",
                    "--categories",
                    "chrome,firefox,slack,zoom,teams,nodePackageCaches,pythonPackageCaches,goBuildCaches",
                )
            finally:
                if original_test_mode is None:
                    os.environ.pop("CLEANMAC_TEST_MODE", None)
                else:
                    os.environ["CLEANMAC_TEST_MODE"] = original_test_mode
            report = json.loads(result.stdout)
            paths = {row["path"] for row in report["items"]}

            self.assertIn(str(root / "Users/tester/Library/Caches/Google/Chrome/Default/Cache/data_0"), paths)
            self.assertIn(
                str(root / "Users/tester/Library/Caches/Firefox/Profiles/dev.default-release/cache2/entries/cache.bin"),
                paths,
            )
            self.assertIn(str(root / "Users/tester/Library/Application Support/Slack/Cache/cache.bin"), paths)
            self.assertIn(str(root / "Users/tester/Library/Application Support/zoom.us/data/Cache/cache.bin"), paths)
            self.assertIn(str(root / "Users/tester/Library/Application Support/Microsoft/Teams/Cache/cache.bin"), paths)
            self.assertIn(str(root / "Users/tester/.npm/_cacache/content-v2"), paths)
            self.assertIn(str(root / "Users/tester/Library/Caches/pip/http-v2"), paths)
            self.assertIn(str(root / "Users/tester/Library/Caches/go-build/aa"), paths)

    def test_expanded_app_cleanup_rules_preserve_user_data_and_credentials(self) -> None:
        tmp, root, home = self.make_sandbox()
        with tmp:
            original_test_mode = os.environ.get("CLEANMAC_TEST_MODE")
            os.environ["CLEANMAC_TEST_MODE"] = "1"
            try:
                result = self.run_cli(
                    "--root",
                    str(root),
                    "--home",
                    str(home),
                    "--json",
                    "clean",
                    "inspect",
                    "--categories",
                    "chrome,firefox,slack,nodePackageCaches,pythonPackageCaches,goBuildCaches",
                )
            finally:
                if original_test_mode is None:
                    os.environ.pop("CLEANMAC_TEST_MODE", None)
                else:
                    os.environ["CLEANMAC_TEST_MODE"] = original_test_mode
            report = json.loads(result.stdout)
            candidate_paths = {row["path"] for row in report["items"]}
            skipped_reasons = {row["path"]: row["reason"] for row in report["skipped"]}

            self.assertNotIn(
                str(root / "Users/tester/Library/Application Support/Google/Chrome/Default/Bookmarks"),
                candidate_paths,
            )
            self.assertNotIn(
                str(root / "Users/tester/Library/Application Support/Google/Chrome/Default/Login Data"),
                candidate_paths,
            )
            self.assertNotIn(
                str(root / "Users/tester/Library/Application Support/Firefox/Profiles/dev.default-release/logins.json"),
                candidate_paths,
            )
            self.assertNotIn(
                str(root / "Users/tester/Library/Application Support/Slack/Local Storage/leveldb/state.ldb"),
                candidate_paths,
            )
            self.assertNotIn(
                str(root / "Users/tester/Library/Application Support/Slack/Service Worker/CacheStorage/cache-a"),
                candidate_paths,
            )
            self.assertEqual(
                skipped_reasons[
                    str(root / "Users/tester/Library/Application Support/Slack/Service Worker/CacheStorage/cache-a")
                ],
                "app-protected-data",
            )
            self.assertNotIn(str(root / "Users/tester/.npmrc"), candidate_paths)
            self.assertNotIn(str(root / "Users/tester/.pypirc"), candidate_paths)
            self.assertNotIn(str(root / "Users/tester/.netrc"), candidate_paths)

    def test_software_uninstall_plan_routes_official_uninstallers(self) -> None:
        tmp, root, home = self.make_sandbox()
        with tmp:
            listing = json.loads(
                self.run_cli("--root", str(root), "--home", str(home), "--json", "software", "list").stdout
            )
            plan = json.loads(
                self.run_cli(
                    "--root", str(root), "--home", str(home), "--json", "software", "uninstall-plan", "--app", "Falcon"
                ).stdout
            )

            falcon = next(app for app in listing["apps"] if app["name"] == "Falcon.app")
            self.assertEqual(falcon["bundle_id"], "com.crowdstrike.falcon.UserAgent")
            self.assertTrue(falcon["protected_from_uninstall"])
            self.assertEqual(falcon["official_uninstaller_vendor"], "CrowdStrike")
            self.assertTrue(plan["uninstall_plan"]["official_uninstaller_required"])
            self.assertEqual(plan["uninstall_plan"]["official_uninstaller_vendor"], "CrowdStrike")

    def test_clean_execute_persists_operation_log_entries(self) -> None:
        tmp, root, home = self.make_sandbox()
        with tmp:
            operation_log = root / "logs" / "cleanmac-operations.jsonl"
            result = self.run_cli(
                "--root",
                str(root),
                "--home",
                str(home),
                "--json",
                "clean",
                "--categories",
                "downloads",
                "--execute",
                "--yes",
                "--operation-log",
                str(operation_log),
            )
            report = json.loads(result.stdout)
            records = [json.loads(line) for line in operation_log.read_text(encoding="utf-8").splitlines()]

            self.assertEqual(report["operation_log"], str(operation_log))
            self.assertEqual(report["operation_log_entry_count"], len(records))
            self.assertGreaterEqual(len(records), 1)
            self.assertEqual({record["schema"] for record in records}, {"cleanmac.operation-log-entry.v1"})
            self.assertEqual({record["delete_mode"] for record in records}, {"permanent"})
            self.assertTrue(all("cleanmac.py" in record["command"] for record in records))
            self.assertTrue(all("downloads" in record["command"] for record in records))
            self.assertTrue(all(record["deleted"] for record in records))

    def test_clean_execute_uses_default_operation_log_under_remapped_home(self) -> None:
        tmp, root, home = self.make_sandbox()
        with tmp:
            result = self.run_cli(
                "--root",
                str(root),
                "--home",
                str(home),
                "--json",
                "clean",
                "--categories",
                "downloads",
                "--execute",
                "--yes",
            )
            report = json.loads(result.stdout)
            operation_log = root / "Users/tester/.cleanmac/operations.jsonl"
            records = [json.loads(line) for line in operation_log.read_text(encoding="utf-8").splitlines()]

            self.assertEqual(report["operation_log"], str(operation_log))
            self.assertEqual(report["operation_log_entry_count"], len(records))
            self.assertEqual(records[0]["command"].split()[:2], ["cleanmac.py", "--root"])
            self.assertIn(str(root / "Users/tester/Downloads/download.bin"), {record["path"] for record in records})

    def test_rotate_log_once_rotates_oversized_logs(self) -> None:
        tmp, root, _home = self.make_sandbox()
        with tmp:
            log_path = root / "logs" / "operations.jsonl"
            log_path.parent.mkdir(parents=True)
            log_path.write_text("x" * 32, encoding="utf-8")

            rotated = cleancli.rotate_log_once(log_path, max_bytes=16)

            self.assertTrue(rotated)
            self.assertFalse(log_path.exists())
            self.assertEqual((root / "logs" / "operations.jsonl.1").read_text(encoding="utf-8"), "x" * 32)

    def test_clean_trash_delete_mode_routes_candidates_to_recoverable_trash(self) -> None:
        tmp, root, home = self.make_sandbox()
        with tmp:
            result = self.run_cli(
                "--root",
                str(root),
                "--home",
                str(home),
                "--json",
                "clean",
                "--categories",
                "downloads",
                "--delete-mode",
                "trash",
                "--execute",
                "--yes",
            )
            report = json.loads(result.stdout)
            trash_entries = list((root / "Users/tester/.Trash").glob("cleanmac-*download.bin*"))

            self.assertEqual(report["delete_mode"], "trash")
            self.assertFalse((root / "Users/tester/Downloads/download.bin").exists())
            self.assertTrue(trash_entries)
            self.assertTrue(any(row["trash_path"] for row in report["items"] if row["path"].endswith("download.bin")))
            deletion_log = root / "Users/tester/.cleanmac/deletions.log"
            self.assertIn("\ttrash\t", deletion_log.read_text(encoding="utf-8"))

    @unittest.skipIf(not hasattr(os, "symlink"), "symlink unsupported")
    def test_trash_delete_mode_rejects_symlink_candidates(self) -> None:
        tmp, root, home = self.make_sandbox()
        with tmp:
            target = root / "Users/tester/Downloads/target.txt"
            link = root / "Users/tester/Downloads/link.txt"
            target.write_text("target")
            os.symlink(target, link)

            result = self.run_cli_unchecked(
                "--root",
                str(root),
                "--home",
                str(home),
                "--json",
                "clean",
                "--categories",
                "downloads",
                "--delete-mode",
                "trash",
                "--include",
                "link.txt",
                "--execute",
                "--yes",
            )

            self.assertNotEqual(result.returncode, 0)
            self.assertTrue(link.is_symlink())
            deletion_log = root / "Users/tester/.cleanmac/deletions.log"
            self.assertIn("\tfailed\t", deletion_log.read_text(encoding="utf-8"))

    def test_debug_session_log_records_millisecond_timer(self) -> None:
        tmp, root, home = self.make_sandbox()
        with tmp:
            env = {**os.environ, "CLEANMAC_DEBUG": "1"}
            result = subprocess.run(
                [
                    sys.executable,
                    str(CLI),
                    "--root",
                    str(root),
                    "--home",
                    str(home),
                    "--json",
                    "clean",
                    "--categories",
                    "trash",
                ],
                text=True,
                capture_output=True,
                check=True,
                env=env,
            )
            report = json.loads(result.stdout)
            debug_log = root / "Users/tester/.cleanmac/cleanmac_debug_session.log"

            self.assertIn("debug_elapsed_ms", report)
            self.assertIn("PERF\tclean", debug_log.read_text(encoding="utf-8"))

    def test_test_mode_blocks_privileged_and_automation_helpers(self) -> None:
        original = os.environ.copy()
        try:
            os.environ["CLEANMAC_TEST_NO_AUTH"] = "1"
            self.assertIsNone(cleancli.run_text_command(["sudo", "-n", "true"]))
            self.assertIsNone(cleancli.run_text_command(["osascript", "-e", "return 1"]))
            self.assertIsNone(cleancli.run_text_command(["launchctl", "print", "system"]))
        finally:
            os.environ.clear()
            os.environ.update(original)

    def test_safe_test_runner_sets_no_auth_and_stubs_dangerous_commands(self) -> None:
        runner_path = PROJECT_ROOT / "scripts/test.sh"
        runner = runner_path.read_text(encoding="utf-8")

        self.assertTrue(runner_path.is_file())
        self.assertIn("set -euo pipefail", runner)
        self.assertIn("export CLEANMAC_TEST_NO_AUTH=1", runner)
        self.assertIn("export CLEANMAC_TEST_MODE=1", runner)
        removed_product_test_prefix = "".join(chr(code) for code in (77, 79, 76, 69, 95, 84, 69, 83, 84, 95))
        self.assertNotIn(removed_product_test_prefix, runner)
        self.assertIn("mktemp -d", runner)
        self.assertIn('cat > "$TEST_SYSTEM_STUB_DIR/sudo"', runner)
        self.assertIn('cat > "$TEST_SYSTEM_STUB_DIR/osascript"', runner)
        self.assertIn('cat > "$TEST_SYSTEM_STUB_DIR/launchctl"', runner)
        self.assertIn('cat > "$TEST_SYSTEM_STUB_DIR/rm"', runner)
        self.assertIn('export PATH="$TEST_SYSTEM_STUB_DIR:$PATH"', runner)
        self.assertIn('"$PYTHON_BIN" -m unittest -v', runner)
        self.assertIn('"$MAKE_BIN" governance-smoke', runner)
        self.assertIn('"$MAKE_BIN" script-smoke', runner)
        self.assertIn("cleanmac test blocked sudo", runner)
        self.assertIn("cleanmac test blocked osascript", runner)
        self.assertIn("cleanmac test blocked launchctl", runner)
        self.assertIn("cleanmac test blocked rm -rf style command", runner)

    def test_real_delete_primitives_are_owned_by_delete_ops(self) -> None:
        core_text = (PROJECT_ROOT / "cleancli/core.py").read_text(encoding="utf-8")
        delete_ops_text = (PROJECT_ROOT / "cleancli/delete_ops.py").read_text(encoding="utf-8")

        self.assertNotIn("shutil.rmtree(", core_text)
        self.assertNotIn("shutil.move(", core_text)
        self.assertNotIn(".unlink(", core_text)
        self.assertIn("shutil.rmtree(", delete_ops_text)
        self.assertIn("shutil.move(", delete_ops_text)
        self.assertIn("BLOCKED_TEST_COMMANDS", delete_ops_text)
        self.assertIn("def validate_deletion_path", delete_ops_text)
        self.assertIn("def safe_remove", delete_ops_text)
        self.assertIn("def safe_trash_move", delete_ops_text)
        self.assertIn("def safe_sudo_remove", delete_ops_text)
        self.assertIn("SUDO_REMOVE_COMMAND", delete_ops_text)

    def test_protection_data_is_centralized_outside_core(self) -> None:
        core_text = (PROJECT_ROOT / "cleancli/core.py").read_text(encoding="utf-8")
        protection_data_text = (PROJECT_ROOT / "cleancli/protection_data.py").read_text(encoding="utf-8")
        protection_text = (PROJECT_ROOT / "cleancli/protection.py").read_text(encoding="utf-8")

        self.assertNotIn("DEFAULT_PROTECTED_BUNDLE_IDS = (", core_text)
        self.assertNotIn("APP_CLEANUP_RULES: dict", core_text)
        self.assertNotIn('"/Library/Containers/com.apple."', core_text)
        self.assertNotIn('"/Library/Group Containers/group.com.apple."', core_text)
        self.assertNotIn('"/Library/Group Containers/systemgroup.com.apple."', core_text)
        self.assertIn("DEFAULT_PROTECTED_BUNDLE_IDS = (", protection_data_text)
        self.assertIn("APP_CLEANUP_RULES: dict", protection_data_text)
        self.assertNotIn("def ", protection_data_text)
        self.assertNotIn("dataclass", protection_data_text)
        self.assertIn("SENSITIVE_USER_DATA_FRAGMENTS = (", protection_data_text)
        self.assertIn("CRITICAL_SYSTEM_PATHS_EXACT = (", protection_data_text)
        self.assertIn("PROTECTED_BUNDLE_PREFIXES = (", protection_data_text)
        self.assertIn("def should_protect_path", protection_text)
        self.assertIn("def should_protect_bundle", protection_text)
        self.assertIn("def should_protect_data", protection_text)
        self.assertIn("def is_critical_system_component", protection_text)
        self.assertIn("def bundle_policy_reason", protection_text)
        self.assertIn("def official_uninstaller_vendor", protection_text)
        self.assertIn("def container_policy_reason", protection_text)
        self.assertIn("def is_protected_user_data_path", protection_text)

    def test_cleanmac_hardening_protection_categories_are_covered(self) -> None:
        from cleancli import protection

        home = Path("/Users/tester")
        protected_data_paths = (
            home / "Library/Keychains/login.keychain-db",
            home / "Library/Application Support/com.apple.TCC/TCC.db",
            home / "Library/Preferences/SystemConfiguration/preferences.plist",
            home / "Library/Preferences/com.apple.networkextension.plist",
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
            home / "Library/Application Support/Code/User/settings.json",
            home / ".docker/config.json",
            home / "Library/Application Support/Postman/IndexedDB/state.leveldb",
            home / "Library/Application Support/Insomnia/insomnia.Request.db",
            home / ".claude.json",
            home / ".codex/auth.json",
            home / ".cursor/mcp.json",
            home / ".ollama/id_ed25519",
            home / "Library/Application Support/Claude/session.json",
            home / "Library/Application Support/Cursor/User/globalStorage/state.vscdb",
            home / "Library/Application Support/ChatGPT/Local Storage/leveldb/000003.log",
        )
        for path in protected_data_paths:
            self.assertTrue(protection.should_protect_data(path), str(path))

        self.assertTrue(protection.should_protect_bundle("com.apple.someNewSystemAgent"))
        self.assertTrue(protection.should_protect_bundle("com.apple.mail"))
        self.assertTrue(protection.should_protect_bundle("com.bitwarden.desktop"))
        self.assertTrue(protection.is_critical_system_component(Path("/Library/Keychains/login.keychain-db")))
        self.assertTrue(protection.should_protect_path(home / "Library/Messages/chat.db"))

        self.assertEqual(
            protection.official_uninstaller_vendor(bundle_id="com.crowdstrike.falcon.UserAgent"), "CrowdStrike"
        )
        self.assertEqual(protection.official_uninstaller_vendor(name="Jamf Self Service"), "Jamf")
        self.assertEqual(
            protection.official_uninstaller_vendor(bundle_id="com.sentinelone.SentinelAgent"), "SentinelOne"
        )
        self.assertEqual(protection.official_uninstaller_vendor(name="ESET Endpoint Security"), "ESET")
        self.assertEqual(protection.official_uninstaller_vendor(name="Cisco Secure Client"), "Cisco")
        self.assertEqual(protection.official_uninstaller_vendor(name="GlobalProtect"), "GlobalProtect")

    @unittest.skipIf(not hasattr(os, "symlink"), "symlink unsupported")
    def test_trash_delete_mode_fails_closed_when_trash_root_is_symlink(self) -> None:
        tmp, root, home = self.make_sandbox()
        with tmp:
            trash = root / "Users/tester/.Trash"
            routed = root / "Users/tester/TrashTarget"
            shutil.rmtree(trash)
            routed.mkdir(parents=True)
            os.symlink(routed, trash)

            result = self.run_cli_unchecked(
                "--root",
                str(root),
                "--home",
                str(home),
                "--json",
                "clean",
                "--categories",
                "downloads",
                "--delete-mode",
                "trash",
                "--include",
                "download.bin",
                "--execute",
                "--yes",
            )

            self.assertNotEqual(result.returncode, 0)
            self.assertTrue((root / "Users/tester/Downloads/download.bin").exists())
            self.assertEqual(list(routed.iterdir()), [])

    def test_deep_system_cleanup_categories_cover_xcode_firmware_apple_silicon_and_diagnostics(self) -> None:
        tmp, root, home = self.make_sandbox()
        with tmp:
            result = self.run_cli(
                "--root",
                str(root),
                "--home",
                str(home),
                "--json",
                "clean",
                "inspect",
                "--categories",
                "xcode,deviceFirmware,appleSiliconCaches,systemDiagnostics",
                "--older-than-days",
                "0",
                "--limit",
                "50",
            )
            report = json.loads(result.stdout)
            paths = [row["path"] for row in report["items"]]

            self.assertIn(str(root / "Users/tester/Library/Developer/Xcode/Archives/App.xcarchive"), paths)
            self.assertIn(str(root / "Users/tester/Library/Developer/Xcode/iOS DeviceSupport/17.0"), paths)
            self.assertIn(str(root / "private/var/db/oah/runtime-cache"), paths)
            self.assertIn(str(root / "private/var/db/DetachedSignatures/signature-cache"), paths)
            self.assertIn(str(root / "Library/Logs/DiagnosticReports/crash.ips"), paths)
            self.assertEqual(report["by_category"]["deviceFirmware"]["count"], 1)
            self.assertEqual(report["by_category"]["appleSiliconCaches"]["count"], 2)

    def test_plan_command_generates_reusable_cleanup_plan(self) -> None:
        tmp, root, home = self.make_sandbox()
        with tmp:
            result = self.run_cli(
                "--root",
                str(root),
                "--home",
                str(home),
                "--json",
                "plan",
                "--categories",
                "trash,downloads",
                "--risk-policy",
                "strict",
                "--max-delete-mb",
                "10",
                "--include",
                "*.tmp",
                "--exclude",
                "*.keep",
                "--min-size-mb",
                "1",
                "--name-regex",
                "tmp$",
                "--max-items",
                "5",
                "--older-than-days",
                "3",
            )
            report = json.loads(result.stdout)

            self.assertEqual(report["schema"], "cleanmac.plan.v1")
            self.assertEqual(report["selected_category_keys"], ["trash", "downloads"])
            self.assertEqual(report["risk_policy"], "strict")
            self.assertEqual(report["max_delete_mb"], 10.0)
            self.assertEqual(report["include_patterns"], ["*.tmp"])
            self.assertEqual(report["exclude_patterns"], ["*.keep"])
            self.assertEqual(report["min_size_mb"], 1)
            self.assertEqual(report["name_regex"], "tmp$")
            self.assertEqual(report["max_items"], 5)
            self.assertEqual(report["older_than_days"], 3.0)
            self.assertTrue(report["dry_run"])
            self.assertFalse(report["ai_origin"])
            self.assertIn("pre_clean_report", report)
            self.assertEqual(report["ai_summary"]["schema"], "cleanmac.ai-summary.v1")
            self.assertEqual(report["ai_summary"]["phase"], "plan")
            self.assertEqual(report["ai_summary"]["recommended_next_action"], "dry_run_plan")
            self.assertFalse(report["ai_summary"]["safe_to_execute_after_confirmation"])
            self.assertIn("trash", report["ai_summary"]["selected_categories"])
            self.assertEqual(report["ai_confirmation_summary"]["schema"], "cleanmac.ai-confirmation-summary.v1")
            self.assertEqual(
                report["ai_confirmation_summary"]["confirmation_token_embedded"],
                report["ai_confirmation_summary"]["confirmation_token"],
            )
            self.assertTrue(
                report["ai_confirmation_summary"]["confirmation_token_embedded"].startswith("cleanmac-confirm-")
            )

    def test_plan_command_marks_ai_originated_plan(self) -> None:
        tmp, root, home = self.make_sandbox()
        with tmp:
            plan_result = self.run_cli(
                "--root",
                str(root),
                "--home",
                str(home),
                "--json",
                "clean",
                "plan",
                "--categories",
                "trash",
                "--ai-origin",
            )
            plan_file = root / "ai-plan.json"
            plan_file.write_text(plan_result.stdout, encoding="utf-8")
            plan = json.loads(plan_result.stdout)

            self.assertTrue(plan["ai_origin"])

            validate_result = self.run_cli(
                "--root",
                str(root),
                "--home",
                str(home),
                "--json",
                "clean",
                "validate-plan",
                "--plan-file",
                str(plan_file),
            )
            validate_report = json.loads(validate_result.stdout)

            self.assertTrue(validate_report["valid"])
            self.assertTrue(validate_report["plan"]["ai_origin"])

    def test_clean_plan_file_reuses_categories_and_policy(self) -> None:
        tmp, root, home = self.make_sandbox()
        with tmp:
            plan_file = root / "plan.json"
            plan_file.write_text(
                json.dumps(
                    {
                        "categories": ["trash"],
                        "risk_policy": "strict",
                        "max_delete_mb": 5,
                    }
                )
            )
            result = self.run_cli(
                "--root",
                str(root),
                "--home",
                str(home),
                "--json",
                "clean",
                "--plan-file",
                str(plan_file),
            )
            report = json.loads(result.stdout)

            self.assertEqual([row["key"] for row in report["selected_categories"]], ["trash"])
            self.assertEqual(report["risk_policy"], "strict")
            self.assertEqual(report["max_delete_mb"], 5.0)
            self.assertEqual(report["plan_metadata"]["path"], str(plan_file))

    def test_validate_plan_reports_replay_metadata(self) -> None:
        tmp, root, home = self.make_sandbox()
        with tmp:
            plan_file = root / "plan.json"
            plan_file.write_text(
                json.dumps(
                    {
                        "schema": "cleanmac.plan.v1",
                        "selected_category_keys": ["trash"],
                        "risk_policy": "default",
                        "root": str(root),
                        "home": str(home),
                    }
                )
            )
            result = self.run_cli(
                "--root",
                str(root),
                "--home",
                str(home),
                "--json",
                "validate-plan",
                "--plan-file",
                str(plan_file),
            )
            report = json.loads(result.stdout)

            self.assertTrue(report["valid"])
            self.assertEqual(report["plan"]["category_keys"], ["trash"])
            self.assertEqual(report["unknown_categories"], [])
            self.assertEqual(report["context_warnings"], [])
            self.assertIn("clean", report["replay_clean_command"])

    def test_validate_plan_reports_unknown_categories_as_invalid(self) -> None:
        tmp, root, home = self.make_sandbox()
        with tmp:
            plan_file = root / "unknown-plan.json"
            plan_file.write_text(json.dumps({"selected_category_keys": ["trash", "ghost"]}))

            result = self.run_cli(
                "--root",
                str(root),
                "--home",
                str(home),
                "--json",
                "validate-plan",
                "--plan-file",
                str(plan_file),
            )
            report = json.loads(result.stdout)

            self.assertFalse(report["valid"])
            self.assertEqual(report["unknown_categories"], ["ghost"])
            self.assertIn("trash", report["replay_clean_command"])
            self.assertNotIn("ghost", report["replay_clean_command"])

    def test_clean_can_replay_categories_from_audit_report_file(self) -> None:
        tmp, root, home = self.make_sandbox()
        with tmp:
            audit_file = root / "clean-audit.json"
            self.run_cli(
                "--root",
                str(root),
                "--home",
                str(home),
                "--report-file",
                str(audit_file),
                "--json",
                "clean",
                "--categories",
                "trash",
            )

            result = self.run_cli(
                "--root",
                str(root),
                "--home",
                str(home),
                "--json",
                "clean",
                "--plan-file",
                str(audit_file),
            )
            report = json.loads(result.stdout)

            self.assertEqual([row["key"] for row in report["selected_categories"]], ["trash"])
            self.assertEqual(report["plan_metadata"]["path"], str(audit_file))
            self.assertTrue((root / "Users/tester/.Trash/old.tmp").exists())

    def test_validate_plan_includes_current_preview_and_budgets(self) -> None:
        tmp, root, home = self.make_sandbox()
        with tmp:
            plan_file = root / "plan-preview.json"
            plan_file.write_text(
                json.dumps(
                    {
                        "selected_category_keys": ["trash"],
                        "include_patterns": ["old.tmp"],
                        "max_items": 2,
                        "max_delete_mb": 1,
                    }
                )
            )
            result = self.run_cli(
                "--root",
                str(root),
                "--home",
                str(home),
                "--json",
                "validate-plan",
                "--plan-file",
                str(plan_file),
            )
            report = json.loads(result.stdout)

            self.assertTrue(report["valid"])
            self.assertIsNotNone(report["preview"])
            self.assertEqual(report["preview"]["include_patterns"], ["old.tmp"])
            self.assertEqual(report["preview"]["shown_candidates"], 1)
            self.assertTrue(report["budget_summary"]["within_max_items"])
            self.assertTrue(report["budget_summary"]["within_max_delete_budget"])

    def test_ai_policy_simulator_reports_missing_and_satisfied_guards(self) -> None:
        tmp, root, home = self.make_sandbox()
        with tmp:
            plan_file = root / "ai-plan.json"
            plan_result = self.run_cli(
                "--root",
                str(root),
                "--home",
                str(home),
                "--json",
                "clean",
                "plan",
                "--categories",
                "downloads",
                "--ai-origin",
            )
            plan = json.loads(plan_result.stdout)
            self.assertEqual(plan["schema"], "cleanmac.plan.v1")
            self.assertIn("generated_at", plan)
            self.assertIn("expires_at", plan)
            self.assertGreater(len(plan["candidate_fingerprints"]), 0)
            plan_file.write_text(plan_result.stdout, encoding="utf-8")

            missing = self.run_cli(
                "--root",
                str(root),
                "--home",
                str(home),
                "--json",
                "clean",
                "policy-simulate",
                "--plan-file",
                str(plan_file),
                "--execute",
            )
            missing_report = json.loads(missing.stdout)
            self.assertEqual(missing_report["schema"], "cleanmac.ai-policy-simulation.v1")
            self.assertFalse(missing_report["allowed"])
            self.assertIn("--delete-mode trash", missing_report["missing_requirements"])
            self.assertIn("--operation-log", missing_report["missing_requirements"])
            self.assertIn("--require-plan-context", missing_report["missing_requirements"])
            blocking_codes = {row["code"] for row in missing_report["blocking_reasons"]}
            self.assertIn("AI_ORIGIN_REQUIRES_TRASH", blocking_codes)
            self.assertFalse(missing_report["safe_to_auto_retry"])
            self.assertTrue(missing_report["retry_requires_user_confirmation"])

            satisfied = self.run_cli(
                "--root",
                str(root),
                "--home",
                str(home),
                "--json",
                "clean",
                "policy-simulate",
                "--plan-file",
                str(plan_file),
                "--execute",
                "--delete-mode",
                "trash",
                "--operation-log",
                str(root / "operations.jsonl"),
                "--require-plan-context",
                "--require-confirmation-token",
                "--confirmation-token",
                "cleanmac-confirm-test",
            )
            satisfied_report = json.loads(satisfied.stdout)
            self.assertTrue(satisfied_report["allowed"], satisfied_report["missing_requirements"])
            self.assertTrue(satisfied_report["plan_freshness"]["fresh"])
            self.assertEqual(satisfied_report["missing_requirements"], [])
            self.assertEqual(satisfied_report["blocking_reasons"], [])

    def test_ai_originated_execute_refuses_drifted_plan(self) -> None:
        tmp, root, home = self.make_sandbox()
        with tmp:
            plan_file = root / "ai-plan.json"
            operation_log = root / "operations.jsonl"
            plan_result = self.run_cli(
                "--root",
                str(root),
                "--home",
                str(home),
                "--json",
                "clean",
                "plan",
                "--categories",
                "downloads",
                "--ai-origin",
            )
            plan_file.write_text(plan_result.stdout, encoding="utf-8")
            dry_run = self.run_cli(
                "--root",
                str(root),
                "--home",
                str(home),
                "--json",
                "clean",
                "run",
                "--plan-file",
                str(plan_file),
                "--require-plan-context",
                "--delete-mode",
                "trash",
            )
            token = json.loads(dry_run.stdout)["ai_confirmation_summary"]["confirmation_token"]
            (root / "Users/tester/Downloads/download.bin").write_text("download-drifted")

            execute = self.run_cli_unchecked(
                "--root",
                str(root),
                "--home",
                str(home),
                "--json",
                "clean",
                "run",
                "--plan-file",
                str(plan_file),
                "--require-plan-context",
                "--delete-mode",
                "trash",
                "--execute",
                "--yes",
                "--operation-log",
                str(operation_log),
                "--require-confirmation-token",
                "--confirmation-token",
                token,
            )
            self.assertNotEqual(execute.returncode, 0)
            error_report = json.loads(execute.stderr)
            self.assertEqual(error_report["error"]["code"], "PLAN_STALE_OR_DRIFTED")
            self.assertTrue((root / "Users/tester/Downloads/download.bin").exists())

    def test_require_plan_context_rejects_root_mismatch(self) -> None:
        tmp, root, home = self.make_sandbox()
        with tmp:
            plan_file = root / "plan.json"
            plan_file.write_text(
                json.dumps(
                    {
                        "selected_category_keys": ["trash"],
                        "root": "/different/root",
                        "home": str(home),
                    }
                )
            )
            result = self.run_cli_unchecked(
                "--root",
                str(root),
                "--home",
                str(home),
                "clean",
                "--plan-file",
                str(plan_file),
                "--require-plan-context",
            )

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("Plan root mismatch", result.stderr)

    def test_require_plan_context_requires_plan_file(self) -> None:
        tmp, root, home = self.make_sandbox()
        with tmp:
            result = self.run_cli_unchecked(
                "--root",
                str(root),
                "--home",
                str(home),
                "clean",
                "--categories",
                "trash",
                "--require-plan-context",
            )

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("requires --plan-file", result.stderr)

    def test_require_plan_context_rejects_home_mismatch(self) -> None:
        tmp, root, home = self.make_sandbox()
        with tmp:
            plan_file = root / "plan.json"
            plan_file.write_text(
                json.dumps(
                    {
                        "selected_category_keys": ["trash"],
                        "root": str(root),
                        "home": "/Users/other",
                    }
                )
            )

            result = self.run_cli_unchecked(
                "--root",
                str(root),
                "--home",
                str(home),
                "clean",
                "--plan-file",
                str(plan_file),
                "--require-plan-context",
            )

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("Plan home mismatch", result.stderr)

    def test_ai_originated_plan_requires_conservative_execute_guards(self) -> None:
        tmp, root, home = self.make_sandbox()
        with tmp:
            plan_file = root / "ai-plan.json"
            operation_log = root / "logs" / "ai-operations.jsonl"
            plan_result = self.run_cli(
                "--root",
                str(root),
                "--home",
                str(home),
                "--json",
                "clean",
                "plan",
                "--categories",
                "downloads",
                "--max-items",
                "10",
                "--max-delete-mb",
                "5",
                "--ai-origin",
            )
            plan_file.write_text(plan_result.stdout, encoding="utf-8")

            dry_run = self.run_cli(
                "--root",
                str(root),
                "--home",
                str(home),
                "--json",
                "clean",
                "run",
                "--plan-file",
                str(plan_file),
                "--require-plan-context",
                "--delete-mode",
                "trash",
            )
            dry_report = json.loads(dry_run.stdout)
            token = dry_report["ai_confirmation_summary"]["confirmation_token"]
            dry_ledger = dry_report["ai_execution_ledger"]
            self.assertEqual(dry_ledger["schema"], "cleanmac.ai-execution-ledger.v1")
            self.assertEqual(dry_ledger["phase"], "clean-dry-run")
            self.assertEqual(dry_ledger["plan"]["file"], cleancli.display_path(plan_file.resolve(strict=False)))
            self.assertEqual(dry_ledger["plan"]["sha256"], cleancli.file_sha256(str(plan_file)))
            self.assertTrue(dry_ledger["plan"]["ai_originated"])
            self.assertTrue(dry_ledger["plan"]["context_required"])
            self.assertEqual(dry_ledger["confirmation"]["token"], token)
            self.assertFalse(dry_ledger["confirmation"]["token_validated"])
            self.assertFalse(dry_ledger["safe_chain_complete"])
            candidate = root / "Users/tester/Downloads/download.bin"

            permanent = self.run_cli_unchecked(
                "--root",
                str(root),
                "--home",
                str(home),
                "--json",
                "clean",
                "run",
                "--plan-file",
                str(plan_file),
                "--require-plan-context",
                "--delete-mode",
                "permanent",
                "--execute",
                "--yes",
                "--operation-log",
                str(operation_log),
                "--require-confirmation-token",
                "--confirmation-token",
                token,
            )
            self.assertNotEqual(permanent.returncode, 0)
            self.assertIn("AI-originated plan requires --delete-mode trash", permanent.stderr)
            self.assertTrue(candidate.exists())

            missing_operation_log = self.run_cli_unchecked(
                "--root",
                str(root),
                "--home",
                str(home),
                "--json",
                "clean",
                "run",
                "--plan-file",
                str(plan_file),
                "--require-plan-context",
                "--delete-mode",
                "trash",
                "--execute",
                "--yes",
                "--require-confirmation-token",
                "--confirmation-token",
                token,
            )
            self.assertNotEqual(missing_operation_log.returncode, 0)
            self.assertIn("AI-originated plan requires --operation-log", missing_operation_log.stderr)
            self.assertTrue(candidate.exists())

            missing_token_requirement = self.run_cli_unchecked(
                "--root",
                str(root),
                "--home",
                str(home),
                "--json",
                "clean",
                "run",
                "--plan-file",
                str(plan_file),
                "--require-plan-context",
                "--delete-mode",
                "trash",
                "--execute",
                "--yes",
                "--operation-log",
                str(operation_log),
                "--confirmation-token",
                token,
            )
            self.assertNotEqual(missing_token_requirement.returncode, 0)
            self.assertIn("AI-originated plan requires --require-confirmation-token", missing_token_requirement.stderr)
            self.assertTrue(candidate.exists())

            missing_plan_context = self.run_cli_unchecked(
                "--root",
                str(root),
                "--home",
                str(home),
                "--json",
                "clean",
                "run",
                "--plan-file",
                str(plan_file),
                "--delete-mode",
                "trash",
                "--execute",
                "--yes",
                "--operation-log",
                str(operation_log),
                "--require-confirmation-token",
                "--confirmation-token",
                token,
            )
            self.assertNotEqual(missing_plan_context.returncode, 0)
            self.assertIn("AI-originated plan requires --require-plan-context", missing_plan_context.stderr)
            self.assertTrue(candidate.exists())

            execute = self.run_cli(
                "--root",
                str(root),
                "--home",
                str(home),
                "--json",
                "clean",
                "run",
                "--plan-file",
                str(plan_file),
                "--require-plan-context",
                "--delete-mode",
                "trash",
                "--execute",
                "--yes",
                "--operation-log",
                str(operation_log),
                "--require-confirmation-token",
                "--confirmation-token",
                token,
            )
            report = json.loads(execute.stdout)
            execute_ledger = report["ai_execution_ledger"]
            records = [json.loads(line) for line in operation_log.read_text(encoding="utf-8").splitlines()]
            delete_record = next(row for row in records if row["action"] == "delete")

            self.assertFalse(candidate.exists())
            self.assertTrue(operation_log.exists())
            self.assertTrue(report["plan_metadata"]["ai_origin"])
            self.assertTrue(report["ai_confirmation_summary"]["confirmation_token_validated"])
            self.assertEqual(execute_ledger["phase"], "clean-execute")
            self.assertEqual(execute_ledger["plan"]["file"], cleancli.display_path(plan_file.resolve(strict=False)))
            self.assertEqual(execute_ledger["plan"]["sha256"], cleancli.file_sha256(str(plan_file)))
            self.assertTrue(execute_ledger["confirmation"]["token_required"])
            self.assertTrue(execute_ledger["confirmation"]["token_validated"])
            self.assertEqual(
                execute_ledger["operation_log"]["path"], cleancli.display_path(operation_log.resolve(strict=False))
            )
            self.assertEqual(execute_ledger["operation_log"]["status"], "ready")
            self.assertTrue(execute_ledger["operation_log"]["ready"])
            self.assertTrue(execute_ledger["safe_chain_complete"])
            self.assertTrue(delete_record["ai"]["originated_plan"])
            self.assertEqual(delete_record["ai"]["plan_file"], cleancli.display_path(plan_file.resolve(strict=False)))
            self.assertEqual(delete_record["ai"]["plan_sha256"], cleancli.file_sha256(str(plan_file)))
            self.assertTrue(delete_record["ai"]["require_plan_context"])
            self.assertTrue(delete_record["ai"]["confirmation_token_required"])
            self.assertTrue(delete_record["ai"]["confirmation_token_validated"])

    def test_plan_file_reuses_filters(self) -> None:
        tmp, root, home = self.make_sandbox()
        with tmp:
            keep = root / "Users/tester/.Trash/keep.keep"
            old_file = root / "Users/tester/.Trash/old.tmp"
            keep.write_text("keep")
            old_file.write_text("old")
            old_time = time.time() - 10 * 24 * 60 * 60
            os.utime(old_file, (old_time, old_time))
            plan_file = root / "plan.json"
            plan_file.write_text(
                json.dumps(
                    {
                        "selected_category_keys": ["trash"],
                        "exclude_patterns": ["*.keep"],
                        "older_than_days": 7,
                    }
                )
            )
            result = self.run_cli(
                "--root",
                str(root),
                "--home",
                str(home),
                "--json",
                "clean",
                "--plan-file",
                str(plan_file),
                "--execute",
            )
            report = json.loads(result.stdout)

            self.assertEqual(report["exclude_patterns"], ["*.keep"])
            self.assertEqual(report["older_than_days"], 7.0)
            self.assertTrue(keep.exists())
            self.assertFalse(old_file.exists())

    def test_inspect_lists_direct_children_sorted_by_size(self) -> None:
        tmp, root, home = self.make_sandbox()
        with tmp:
            (root / "Users/tester/.Trash/big.tmp").write_text("x" * 100)
            result = self.run_cli(
                "--root",
                str(root),
                "--home",
                str(home),
                "--json",
                "inspect",
                "--categories",
                "trash",
                "--limit",
                "1",
            )
            report = json.loads(result.stdout)

            self.assertEqual(report["shown_candidates"], 1)
            self.assertTrue(report["items"][0]["path"].endswith("big.tmp"))
            self.assertEqual(report["ai_summary"]["schema"], "cleanmac.ai-summary.v1")
            self.assertEqual(report["ai_summary"]["phase"], "inspect")
            self.assertEqual(report["ai_summary"]["recommended_next_action"], "generate_plan")
            self.assertFalse(report["ai_summary"]["safe_to_execute_after_confirmation"])
            self.assertIn("trash", report["ai_summary"]["selected_categories"])
            self.assertTrue(report["ai_summary"]["headline"])

    def test_inspect_supports_recursive_min_size_and_path_sort(self) -> None:
        tmp, root, home = self.make_sandbox()
        with tmp:
            nested = root / "Users/tester/.Trash/nested"
            nested.mkdir()
            (nested / "small.txt").write_text("tiny")
            (nested / "large.bin").write_bytes(b"x" * (1024 * 1024 + 1))
            result = self.run_cli(
                "--root",
                str(root),
                "--home",
                str(home),
                "--json",
                "inspect",
                "--categories",
                "trash",
                "--recursive",
                "--min-size-mb",
                "1",
                "--sort",
                "path",
            )
            report = json.loads(result.stdout)
            paths = [row["path"] for row in report["items"]]

            self.assertTrue(report["recursive"])
            self.assertEqual(report["min_size_mb"], 1)
            self.assertEqual(paths, sorted(paths))
            self.assertTrue(any(path.endswith("nested/large.bin") for path in paths))
            large_row = next(row for row in report["items"] if row["path"].endswith("nested/large.bin"))
            self.assertEqual(large_row["depth"], 2)

    def test_inspect_accepts_budget_flags_as_non_destructive_preview(self) -> None:
        tmp, root, home = self.make_sandbox()
        with tmp:
            old_time = time.time() - 8 * 24 * 60 * 60
            log_file = root / "Users/tester/Library/logs/noisy.log"
            os.utime(log_file, (old_time, old_time))
            result = self.run_cli(
                "--root",
                str(root),
                "--home",
                str(home),
                "--json",
                "inspect",
                "--categories",
                "userLogs",
                "--older-than-days",
                "7",
                "--max-delete-mb",
                "1000",
                "--max-items",
                "500",
            )
            report = json.loads(result.stdout)

            self.assertEqual(report["max_delete_mb"], 1000.0)
            self.assertEqual(report["max_items"], 500)
            self.assertTrue(report["budget_summary"]["within_max_delete_budget"])
            self.assertTrue(report["budget_summary"]["within_max_items"])
            self.assertFalse(report["budget_summary"]["applies_to_execute"])
            self.assertTrue(log_file.exists())

    def test_invalid_name_regex_is_rejected_before_deletion(self) -> None:
        tmp, root, home = self.make_sandbox()
        with tmp:
            result = self.run_cli_unchecked(
                "--root",
                str(root),
                "--home",
                str(home),
                "inspect",
                "--categories",
                "trash",
                "--name-regex",
                "[",
            )

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("Invalid --name-regex", result.stderr)
            self.assertTrue((root / "Users/tester/.Trash/old.tmp").exists())

    def test_direct_delete_safety_blocks_top_level_and_outside_sandbox_paths(self) -> None:
        tmp, root, home = self.make_sandbox()
        with tmp:
            with self.assertRaisesRegex(RuntimeError, "unsafe top-level path"):
                cleancli.assert_safe_to_delete(
                    root / "Users/tester",
                    root=root,
                    home=home,
                )

    def test_delete_safety_rejects_malformed_and_protected_paths(self) -> None:
        tmp, root, home = self.make_sandbox()
        with tmp:
            with self.assertRaisesRegex(RuntimeError, "non-absolute"):
                cleancli.assert_safe_to_delete(Path("relative.tmp"), root=root, home=home)

            with self.assertRaisesRegex(RuntimeError, "traversal"):
                cleancli.assert_safe_to_delete(root / "Users/tester/.Trash/../escape", root=root, home=home)

            with self.assertRaisesRegex(RuntimeError, "control characters"):
                cleancli.assert_safe_to_delete(root / "Users/tester/.Trash/bad\nname", root=root, home=home)

            protected = root / "System/Library"
            protected.mkdir(parents=True)
            with self.assertRaisesRegex(RuntimeError, "protected system path"):
                cleancli.assert_safe_to_delete(protected, root=root, home=home)

    def test_path_safety_rejects_dangerous_path_data(self) -> None:
        tmp, root, home = self.make_sandbox()
        corpus = PROJECT_ROOT / "tests/data/dangerous_paths.txt"
        with tmp:
            dangerous_paths = [
                line.strip()
                for line in corpus.read_text(encoding="utf-8").splitlines()
                if line.strip() and not line.startswith("#")
            ]
            self.assertGreaterEqual(len(dangerous_paths), 50)

            for value in dangerous_paths:
                candidate = Path(value)
                mapped = candidate if not candidate.is_absolute() else root / value.lstrip("/")
                with self.subTest(path=value):
                    with self.assertRaises(RuntimeError):
                        cleancli.assert_safe_to_delete(mapped, root=root, home=home)

    def test_delete_safety_allows_private_allowlist_and_rejects_private_db(self) -> None:
        tmp, root, home = self.make_sandbox()
        with tmp:
            log_file = root / "private/var/log/app.log"
            log_file.parent.mkdir(parents=True)
            log_file.write_text("log")
            cleancli.assert_safe_to_delete(log_file, root=root, home=home)

            db_file = root / "private/var/db/important.db"
            db_file.parent.mkdir(parents=True, exist_ok=True)
            db_file.write_text("db")
            with self.assertRaisesRegex(RuntimeError, "protected system path"):
                cleancli.assert_safe_to_delete(db_file, root=root, home=home)

    @unittest.skipIf(not hasattr(os, "symlink"), "symlink unsupported")
    def test_delete_safety_rejects_symlink_to_protected_path(self) -> None:
        tmp, root, home = self.make_sandbox()
        with tmp:
            protected = root / "System/Library"
            protected.mkdir(parents=True)
            link = root / "Users/tester/.Trash/system-link"
            os.symlink(protected, link)

            with self.assertRaisesRegex(RuntimeError, "symlink pointing to protected path"):
                cleancli.assert_safe_to_delete(link, root=root, home=home)

    def test_incomplete_downloads_skip_active_files(self) -> None:
        tmp, root, home = self.make_sandbox()
        with tmp:
            original = cleancli.is_file_open
            cleancli.is_file_open = lambda path: path.name == "partial.crdownload"  # type: ignore[assignment]
            try:
                report = cleancli.inspect_items(
                    [cleancli.CATEGORY_BY_KEY["incompleteDownloads"]],
                    root=root,
                    home=home,
                    limit=50,
                )
            finally:
                cleancli.is_file_open = original  # type: ignore[assignment]

            self.assertEqual(report["total_candidates"], 0)
            self.assertIn("active-file", report["skipped_summary"]["by_reason"])

    def test_mail_downloads_use_age_and_size_defaults(self) -> None:
        tmp, root, home = self.make_sandbox()
        with tmp:
            old_time = time.time() - 40 * 24 * 60 * 60
            old_mail = root / "Users/tester/Library/Mail Downloads/old-mail.pdf"
            os.utime(old_mail, (old_time, old_time))
            original_test_mode = os.environ.get("CLEANMAC_TEST_MODE")
            os.environ["CLEANMAC_TEST_MODE"] = "1"
            try:
                result = self.run_cli(
                    "--root",
                    str(root),
                    "--home",
                    str(home),
                    "--json",
                    "inspect",
                    "--categories",
                    "mails",
                )
            finally:
                if original_test_mode is None:
                    os.environ.pop("CLEANMAC_TEST_MODE", None)
                else:
                    os.environ["CLEANMAC_TEST_MODE"] = original_test_mode
            report = json.loads(result.stdout)

            self.assertEqual(report["total_candidates"], 0)
            self.assertIn("below-min-size", report["skipped_summary"]["by_reason"])

    def test_gpu_cache_provider_only_returns_stale_allowlisted_dirs(self) -> None:
        tmp, root, home = self.make_sandbox()
        with tmp:
            stale = root / "private/var/folders/aa/bb/C/app/com.apple.metal"
            recent = root / "private/var/folders/aa/bb/C/app/com.apple.metalfe"
            stale.mkdir(parents=True)
            recent.mkdir(parents=True)
            stale_file = stale / "shader.cache"
            recent_file = recent / "shader.cache"
            stale_file.write_text("old")
            recent_file.write_text("new")
            old_time = time.time() - 3 * 24 * 60 * 60
            os.utime(stale_file, (old_time, old_time))
            os.utime(stale, (old_time, old_time))

            result = self.run_cli(
                "--root",
                str(root),
                "--home",
                str(home),
                "--json",
                "inspect",
                "--categories",
                "gpuCaches",
            )
            report = json.loads(result.stdout)
            paths = [row["path"] for row in report["items"]]

            self.assertIn(str(stale), paths)
            self.assertNotIn(str(recent), paths)
            self.assertIn("not-stale", report["skipped_summary"]["by_reason"])

    def test_browser_code_sign_cache_provider_uses_x_shard(self) -> None:
        tmp, root, home = self.make_sandbox()
        with tmp:
            cache = root / "private/var/folders/aa/bb/X/com.browser/foo.code_sign_clone"
            cache.mkdir(parents=True)

            result = self.run_cli(
                "--root",
                str(root),
                "--home",
                str(home),
                "--json",
                "inspect",
                "--categories",
                "browserCodeSignCache",
            )
            report = json.loads(result.stdout)

            self.assertEqual(report["total_candidates"], 1)
            self.assertEqual(report["items"][0]["path"], str(cache))

            with self.assertRaisesRegex(RuntimeError, "outside sandbox root"):
                cleancli.assert_safe_to_delete(
                    Path("/tmp/cleanmac-outside-candidate"),
                    root=root,
                    home=home,
                )

    def test_filters_apply_to_inspect_and_clean(self) -> None:
        tmp, root, home = self.make_sandbox()
        with tmp:
            keep = root / "Users/tester/.Trash/keep.tmp"
            remove = root / "Users/tester/.Trash/remove.log"
            keep.write_text("keep")
            remove.write_text("remove")

            inspect_result = self.run_cli(
                "--root",
                str(root),
                "--home",
                str(home),
                "--json",
                "inspect",
                "--categories",
                "trash",
                "--name-regex",
                "remove\\.log$",
            )
            inspect_report = json.loads(inspect_result.stdout)
            inspect_paths = [row["path"] for row in inspect_report["items"]]
            self.assertIn(str(remove), inspect_paths)
            self.assertNotIn(str(keep), inspect_paths)
            self.assertIn("name-regex-mismatch", inspect_report["skipped_summary"]["by_reason"])

            clean_result = self.run_cli(
                "--root",
                str(root),
                "--home",
                str(home),
                "--json",
                "clean",
                "--categories",
                "trash",
                "--exclude",
                "*keep.tmp",
                "--execute",
            )
            clean_report = json.loads(clean_result.stdout)
            self.assertEqual(clean_report["skipped_summary"]["by_reason"], {"excluded": 1})
            self.assertTrue(keep.exists())
            self.assertFalse(remove.exists())

    def test_older_than_days_filters_new_candidates(self) -> None:
        tmp, root, home = self.make_sandbox()
        with tmp:
            old_file = root / "Users/tester/.Trash/ancient.tmp"
            new_file = root / "Users/tester/.Trash/fresh.tmp"
            old_file.write_text("old")
            new_file.write_text("new")
            old_time = time.time() - 10 * 24 * 60 * 60
            os.utime(old_file, (old_time, old_time))
            result = self.run_cli(
                "--root",
                str(root),
                "--home",
                str(home),
                "--json",
                "inspect",
                "--categories",
                "trash",
                "--older-than-days",
                "7",
                "--sort",
                "path",
            )
            report = json.loads(result.stdout)
            paths = [row["path"] for row in report["items"]]

            self.assertIn(str(old_file), paths)
            self.assertNotIn(str(new_file), paths)
            self.assertIn("too-new", report["skipped_summary"]["by_reason"])

    def test_execute_high_risk_requires_yes(self) -> None:
        tmp, root, home = self.make_sandbox()
        with tmp:
            result = self.run_cli_unchecked(
                "--root",
                str(root),
                "--home",
                str(home),
                "clean",
                "--categories",
                "downloads",
                "--execute",
            )

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("without --yes", result.stderr)
            self.assertTrue((root / "Users/tester/Downloads/download.bin").exists())

    def test_clean_risk_policy_strict_requires_yes_for_medium_risk(self) -> None:
        tmp, root, home = self.make_sandbox()
        with tmp:
            result = self.run_cli_unchecked(
                "--root",
                str(root),
                "--home",
                str(home),
                "clean",
                "--categories",
                "userLogs",
                "--execute",
                "--risk-policy",
                "strict",
            )

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("risk policy 'strict'", result.stderr)
            self.assertTrue((root / "Users/tester/Library/logs/noisy.log").exists())

    def test_clean_risk_policy_permissive_allows_high_risk_without_yes(self) -> None:
        tmp, root, home = self.make_sandbox()
        with tmp:
            result = self.run_cli(
                "--root",
                str(root),
                "--home",
                str(home),
                "--json",
                "clean",
                "--categories",
                "downloads",
                "--execute",
                "--risk-policy",
                "permissive",
            )
            report = json.loads(result.stdout)

            self.assertEqual(report["risk_policy"], "permissive")
            self.assertEqual(report["pre_clean_report"]["summary"]["yes_required_categories"], [])
            self.assertFalse((root / "Users/tester/Downloads/download.bin").exists())

    def test_clean_execute_live_root_requires_explicit_allow_flag(self) -> None:
        result = self.run_cli_unchecked("clean", "--categories", "trash", "--execute")

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("live root '/'", result.stderr)

    def test_clean_max_delete_budget_blocks_execute_before_deleting(self) -> None:
        tmp, root, home = self.make_sandbox()
        with tmp:
            result = self.run_cli_unchecked(
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
            )

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("exceed --max-delete-mb budget", result.stderr)
            self.assertTrue((root / "Users/tester/.Trash/old.tmp").exists())

    def test_clean_max_items_blocks_execute_before_deleting(self) -> None:
        tmp, root, home = self.make_sandbox()
        with tmp:
            (root / "Users/tester/.Trash/extra.tmp").write_text("extra")
            result = self.run_cli_unchecked(
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
            )

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("exceeds --max-items budget", result.stderr)
            self.assertTrue((root / "Users/tester/.Trash/old.tmp").exists())
            self.assertTrue((root / "Users/tester/.Trash/extra.tmp").exists())

    def test_clean_fail_on_skipped_blocks_execute_before_deleting(self) -> None:
        tmp, root, home = self.make_sandbox()
        with tmp:
            remove = root / "Users/tester/.Trash/remove.tmp"
            keep = root / "Users/tester/.Trash/keep.tmp"
            remove.write_text("remove")
            keep.write_text("keep")
            result = self.run_cli_unchecked(
                "--root",
                str(root),
                "--home",
                str(home),
                "clean",
                "--categories",
                "trash",
                "--exclude",
                "*keep.tmp",
                "--fail-on-skipped",
                "--execute",
            )

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("candidate(s) were skipped", result.stderr)
            self.assertTrue(remove.exists())
            self.assertTrue(keep.exists())

    def test_scripts_reports_current_command_templates(self) -> None:
        result = self.run_cli("--json", "scripts", "--categories", "terminal,imessage")
        report = json.loads(result.stdout)
        inventory = report["script_inventory"]
        validation = report["template_validation"]
        migration = report["template_migration"]
        terminal = report["categories"][0]
        imessage = report["categories"][1]

        self.assertEqual(validation["schema"], "cleanmac.command-template-validation.v1")
        self.assertTrue(validation["valid"])
        self.assertEqual(validation["violation_count"], 0)
        self.assertEqual(validation["violations"], [])
        self.assertGreater(validation["template_count"], 0)
        self.assertGreater(validation["destructive_template_count"], 0)
        self.assertGreater(validation["safe_to_auto_execute_template_count"], 0)
        self.assertEqual(migration["schema"], "cleanmac.command-template-migration.v1")
        self.assertEqual(migration["raw_rm_rf_template_count"], 0)
        self.assertEqual(migration["deprecated_template_count"], 0)
        self.assertEqual(migration["replacement_template_count"], 0)
        self.assertGreater(migration["recommended_delete_template_count"], 0)
        self.assertTrue(migration["all_recommended_delete_templates_use_cleanmac_cli"])
        self.assertEqual(inventory["shell_execution"]["launch_path"], "/bin/sh")
        self.assertEqual(inventory["schema"], "cleanmac.script-groups.v1")
        self.assertEqual(
            inventory["command_template_contract"]["required_fields"],
            [
                "id",
                "kind",
                "command",
                "argv",
                "placeholders",
                "uses_shell",
                "destructive",
                "safe_to_auto_execute",
                "manual_review_required",
                "execution_policy",
            ],
        )
        self.assertIn("clean", report["groups"])
        self.assertIn("software", report["groups"])
        self.assertIn("python3 cleanmac.py --json clean inspect", report["groups"]["clean"]["commands"][0])
        self.assertFalse(report["groups"]["clean"]["safe_to_auto_execute"])
        self.assertTrue(report["groups"]["clean"]["contains_destructive_templates"])
        self.assertTrue(report["groups"]["clean"]["manual_review_required"])
        self.assertEqual(report["groups"]["clean"]["command_templates"][0]["id"], "clean-inspect-selected")
        self.assertEqual(report["groups"]["clean"]["command_templates"][0]["kind"], "argv")
        self.assertEqual(
            report["groups"]["clean"]["command_templates"][0]["argv"],
            ["python3", "cleanmac.py", "--json", "clean", "inspect", "--categories", "<keys>"],
        )
        self.assertFalse(report["groups"]["clean"]["command_templates"][0]["uses_shell"])
        self.assertFalse(report["groups"]["clean"]["command_templates"][0]["destructive"])
        self.assertEqual(
            report["groups"]["clean"]["command_templates"][0]["execution_policy"]["requires_placeholder_substitution"],
            True,
        )
        self.assertTrue(report["groups"]["clean"]["command_templates"][2]["destructive"])
        self.assertTrue(report["groups"]["clean"]["command_templates"][2]["manual_review_required"])
        self.assertTrue(report["groups"]["software"]["safe_to_auto_execute"])
        self.assertFalse(report["groups"]["software"]["contains_destructive_templates"])
        self.assertFalse(report["groups"]["software"]["destructive"])
        self.assertEqual(report["groups"]["software"]["command_templates"][0]["id"], "software-list")
        self.assertEqual(
            report["groups"]["software"]["command_templates"][0]["argv"],
            ["python3", "cleanmac.py", "--json", "software", "list"],
        )
        self.assertIn("boundary_governance", inventory)
        self.assertFalse(inventory["boundary_governance"]["script_template_policy"]["auto_execute_allowed"])
        self.assertTrue(inventory["boundary_governance"]["script_template_policy"]["global_flags_before_command"])
        self.assertIn("symbolic_links", inventory)
        self.assertEqual(inventory["open_in_finder"]["command"], "python3 cleanmac.py clean open --categories <keys>")
        self.assertIn("du -smc", terminal["commands"]["analyze"][0])
        self.assertIn("/private/var/log/asl/*.asl", terminal["commands"]["analyze"][0])
        self.assertIn("python3 cleanmac.py", terminal["commands"]["delete"][0])
        self.assertIn("clean run", terminal["commands"]["delete"][0])
        self.assertIn("--delete-mode trash", terminal["commands"]["delete"][0])
        self.assertNotIn("rm -rf", terminal["commands"]["delete"][0])
        self.assertEqual(terminal["command_templates"]["analyze"][0]["id"], "terminal-analyze-1")
        self.assertEqual(terminal["command_templates"]["analyze"][0]["kind"], "shell")
        self.assertTrue(terminal["command_templates"]["analyze"][0]["uses_shell"])
        self.assertFalse(terminal["command_templates"]["analyze"][0]["destructive"])
        self.assertEqual(terminal["command_templates"]["analyze"][0]["execution_policy"]["uses_shell"], True)
        self.assertFalse(terminal["command_templates"]["delete"][0]["uses_shell"])
        self.assertEqual(terminal["command_templates"]["delete"][0]["kind"], "argv")
        self.assertTrue(terminal["command_templates"]["delete"][0]["destructive"])
        self.assertFalse(terminal["command_templates"]["delete"][0]["safe_to_auto_execute"])
        self.assertTrue(terminal["command_templates"]["delete"][0]["manual_review_required"])
        self.assertTrue(imessage["full_disk_access"])
        self.assertTrue(imessage["requires_privilege"])

    def test_scripts_group_filter_returns_selected_group(self) -> None:
        result = self.run_cli("--json", "clean", "scripts", "--group", "status")
        report = json.loads(result.stdout)

        self.assertEqual(report["script_inventory"]["selected_group"], "status")
        self.assertEqual(list(report["groups"].keys()), ["status"])
        self.assertEqual(report["groups"]["status"]["commands"][0], "python3 cleanmac.py --json status snapshot")

    def test_command_template_validation_reports_policy_violations(self) -> None:
        invalid_template = {
            "id": "bad-delete",
            "kind": "argv",
            "command": "rm -rf /tmp/example",
            "argv": ["rm", "-rf", "/tmp/example"],
            "placeholders": [],
            "uses_shell": False,
            "destructive": True,
            "safe_to_auto_execute": True,
            "manual_review_required": False,
            "execution_policy": {
                "uses_shell": False,
                "destructive": True,
                "safe_to_auto_execute": True,
                "manual_review_required": False,
                "requires_placeholder_substitution": False,
            },
        }

        validation = cleancli.validate_command_templates(
            {"bad": {"command_templates": [invalid_template]}},
            [],
        )
        violation_codes = {violation["code"] for violation in validation["violations"]}

        self.assertFalse(validation["valid"])
        self.assertEqual(validation["template_count"], 1)
        self.assertEqual(validation["destructive_template_count"], 1)
        self.assertIn("destructive-auto-execute", violation_codes)
        self.assertIn("destructive-without-review", violation_codes)
        self.assertIn("destructive-not-cleanmac-cli", violation_codes)
        self.assertIn("raw-rm-forbidden", violation_codes)

    def test_script_group_commands_follow_cli_global_flag_order_and_parse(self) -> None:
        result = self.run_cli("--json", "scripts", "--categories", "trash")
        report = json.loads(result.stdout)

        for group_name, group_report in report["groups"].items():
            for command in group_report["commands"]:
                normalized = (
                    command.replace("<keys>", "trash")
                    .replace("<plan.json>", "/tmp/cleanmac-plan.json")
                    .replace("<AppName>", "Example.app")
                )
                parts = shlex.split(normalized)
                self.assertEqual(parts[:2], ["python3", "cleanmac.py"], command)
                self.assertIn("--json", parts[2:], command)
                self.assertLess(parts.index("--json"), parts.index(group_name), command)

                actual_argv, grouped_command = cleancli.normalize_grouped_argv(parts[2:])
                parsed = cleancli.parse_args(actual_argv)
                self.assertTrue(parsed.json, command)
                if grouped_command is not None:
                    self.assertEqual(grouped_command["group"], group_name)

    def test_cleancli_public_modules_import_after_package_split(self) -> None:
        module_names = [
            "cleancli",
            "cleancli.cli",
            "cleancli.core",
            "cleancli.delete_ops",
            "cleancli.protection",
            "cleancli.protection_data",
            "cleancli.clean",
            "cleancli.analyze",
            "cleancli.categories",
            "cleancli.finder",
            "cleancli.governance",
            "cleancli.models",
            "cleancli.optimize",
            "cleancli.paths",
            "cleancli.reports",
            "cleancli.scripts",
            "cleancli.software",
            "cleancli.status",
            "cleancli.workflow",
            "cleancli.ai_schema",
        ]

        modules = {name: importlib.import_module(name) for name in module_names}
        cleanmac_module = importlib.import_module("cleanmac")

        self.assertIs(modules["cleancli"].main, modules["cleancli.cli"].main)
        self.assertIs(cleanmac_module.main, modules["cleancli.cli"].main)
        self.assertTrue(callable(modules["cleancli.workflow"].workflow_automation_playbook))
        self.assertTrue(callable(modules["cleancli.workflow"].workflow_iteration_status))

    def test_grouped_command_matrix_smoke_is_non_destructive(self) -> None:
        tmp, root, home = self.make_sandbox()
        with tmp:
            plan_file = root / "plan.json"
            plan_result = self.run_cli(
                "--root",
                str(root),
                "--home",
                str(home),
                "--json",
                "clean",
                "plan",
                "--categories",
                "trash",
            )
            plan_file.write_text(plan_result.stdout, encoding="utf-8")

            cases = [
                (
                    ["clean", "list"],
                    lambda report: (
                        report["schema"] == "cleanmac.category-list.v1" and isinstance(report.get("categories"), list)
                    ),
                ),
                (
                    ["clean", "inspect", "--categories", "trash"],
                    lambda report: report["schema"] == "cleanmac.inspect.v1" and report["dry_run"],
                ),
                (["clean", "plan", "--categories", "trash"], lambda report: report["schema"] == "cleanmac.plan.v1"),
                (
                    ["clean", "validate-plan", "--plan-file", str(plan_file)],
                    lambda report: report["schema"] == "cleanmac.validate-plan.v1" and report["valid"],
                ),
                (
                    ["clean", "scripts", "--categories", "trash"],
                    lambda report: (
                        report["schema"] == "cleanmac.scripts.v1"
                        and report["script_inventory"]["schema"] == "cleanmac.script-groups.v1"
                    ),
                ),
                (
                    ["clean", "open", "--categories", "trash"],
                    lambda report: report["schema"] == "cleanmac.open.v1" and report["dry_run"],
                ),
                (["clean", "links"], lambda report: report["schema"] == "cleanmac.links.v1" and report["dry_run"]),
                (
                    ["software", "list"],
                    lambda report: report["schema"] == "cleanmac.software.v1" and not report["destructive"],
                ),
                (
                    ["software", "leftovers"],
                    lambda report: report["schema"] == "cleanmac.software.v1" and not report["destructive"],
                ),
                (
                    ["software", "startup-items"],
                    lambda report: report["schema"] == "cleanmac.software.v1" and not report["destructive"],
                ),
                (
                    ["optimize", "list"],
                    lambda report: report["schema"] == "cleanmac.optimize.v1" and not report["destructive"],
                ),
                (
                    ["optimize", "run", "--execute"],
                    lambda report: report["schema"] == "cleanmac.optimize.v1" and not report["execution_supported"],
                ),
                (
                    ["analyze", "categories", "--categories", "trash"],
                    lambda report: report["schema"] == "cleanmac.analyze.v1" and report["dry_run"],
                ),
                (
                    ["analyze", "scan", "--path", "/Users/tester", "--depth", "1"],
                    lambda report: report["schema"] == "cleanmac.analyze-tree.v1",
                ),
                (
                    ["status", "snapshot"],
                    lambda report: report["schema"] == "cleanmac.status.snapshot.v1" and not report["destructive"],
                ),
            ]

            for command_args, assertion in cases:
                result = self.run_cli(
                    "--root",
                    str(root),
                    "--home",
                    str(home),
                    "--json",
                    *command_args,
                )
                report = json.loads(result.stdout)
                self.assertTrue(assertion(report), command_args)

            self.assertTrue((root / "Users/tester/.Trash/old.tmp").exists())
            self.assertTrue((root / "Users/tester/Downloads/download.bin").exists())

    def test_diagnose_recommends_safe_categories_and_flags_logs(self) -> None:
        tmp, root, home = self.make_sandbox()
        with tmp:
            result = self.run_cli(
                "--root",
                str(root),
                "--home",
                str(home),
                "--json",
                "diagnose",
                "--categories",
                "trash,mails,xcode,userLogs,downloads",
                "--log-threshold-mb",
                "0",
            )
            report = json.loads(result.stdout)
            issue_codes = {issue["code"] for issue in report["issues"]}

            self.assertEqual(report["recommended_clean_categories"], ["trash", "mails", "xcode"])
            self.assertIn("userLogs", report["advanced_options"]["selected_advanced_keys"])
            self.assertTrue(report["advanced_options"]["requires_extra_review"])
            self.assertIn("large-logs-may-indicate-problem", issue_codes)
            self.assertIn("downloads", report["caution_clean_categories"])
            self.assertIn("trash,mails,xcode", report["suggested_safe_command"])

    def test_workflow_runs_fixed_non_destructive_phases(self) -> None:
        tmp, root, home = self.make_sandbox()
        with tmp:
            result = self.run_cli(
                "--root",
                str(root),
                "--home",
                str(home),
                "--json",
                "workflow",
                "--categories",
                "trash,mails,xcode,userLogs,downloads",
                "--log-threshold-mb",
                "0",
                "--inspect-limit",
                "3",
            )
            report = json.loads(result.stdout)
            automation = report["automation_playbook"]
            iteration = report["reports"]["iteration_status"]

            self.assertEqual(report["workflow_name"], "safe-cleaning-workflow")
            self.assertEqual(
                [step["name"] for step in report["steps"]],
                [
                    "script-audit",
                    "analyze-space",
                    "diagnose-problems",
                    "inspect-candidates",
                    "dry-run-clean",
                    "manual-execute-gate",
                ],
            )
            self.assertFalse(report["steps"][4]["destructive"])
            self.assertTrue(report["steps"][5]["destructive"])
            self.assertEqual(
                [category["key"] for category in report["dry_run_categories"]],
                ["trash", "mails", "xcode"],
            )
            self.assertEqual(automation["schema"], "cleanmac.workflow-automation.v1")
            self.assertTrue(automation["safe_to_auto_execute"])
            self.assertFalse(automation["destructive_cleanup_allowed"])
            self.assertTrue(automation["test_acceptance"]["environment"]["requires_virtualenv"])
            self.assertEqual(
                automation["test_acceptance"]["environment"]["workflow_python_env"],
                "PYTHON=.venv/bin/python",
            )
            self.assertIn(
                "clean --execute",
                automation["agent_contract"]["forbidden_command_patterns"],
            )
            self.assertEqual(
                automation["test_acceptance"]["required_commands"],
                [
                    "make quality-check",
                    "make local-test",
                    "make build-check",
                    "make package-smoke",
                    "make script-smoke",
                    "make bundle-audit-smoke",
                    "make macos-smoke",
                    "make security-smoke",
                    "make dependency-audit-smoke",
                    "make docs-smoke",
                    "make governance-smoke",
                    "make open-source-smoke",
                    "make distribution-smoke",
                    "make docker-test",
                    "make release-check",
                ],
            )
            self.assertEqual(iteration["schema"], "cleanmac.workflow-iteration-status.v1")
            self.assertTrue(iteration["safe_to_auto_continue"])
            self.assertFalse(iteration["destructive_cleanup_allowed"])
            self.assertEqual(iteration["next_checkpoint"], "test-acceptance")
            self.assertTrue(iteration["acceptance_gate"]["ready_for_docker_validation"])
            self.assertTrue((root / "Users/tester/.Trash/old.tmp").exists())
            self.assertTrue((root / "Users/tester/Downloads/download.bin").exists())

    def test_workflow_selected_dry_run_scope_includes_high_risk_without_execute(self) -> None:
        tmp, root, home = self.make_sandbox()
        with tmp:
            result = self.run_cli(
                "--root",
                str(root),
                "--home",
                str(home),
                "--json",
                "workflow",
                "--categories",
                "trash,downloads",
                "--dry-run-scope",
                "selected",
            )
            report = json.loads(result.stdout)

            self.assertEqual(
                [category["key"] for category in report["dry_run_categories"]],
                ["trash", "downloads"],
            )
            self.assertTrue(report["reports"]["dry_run"]["dry_run"])
            self.assertGreaterEqual(len(report["reports"]["dry_run"]["items"]), 2)
            self.assertTrue((root / "Users/tester/Downloads/download.bin").exists())

    def test_makefile_exposes_validation_targets(self) -> None:
        makefile = (PROJECT_ROOT / "Makefile").read_text()

        self.assertIn("format:", makefile)
        self.assertIn("lint:", makefile)
        self.assertIn("type-check:", makefile)
        self.assertIn("coverage:", makefile)
        self.assertIn("quality-check: lint type-check coverage", makefile)
        self.assertIn("local-test:", makefile)
        self.assertIn("PYTHON=$(PYTHON) ./scripts/test.sh", makefile)
        self.assertIn("pytest-test:", makefile)
        self.assertIn('$(PYTHON) -m venv "$$tmpdir/venv"', makefile)
        self.assertIn("\"$$tmpdir/venv/bin/python\" -m pip install -e '.[test]'", makefile)
        self.assertIn('PYTEST_ADDOPTS="-p no:cacheprovider"', makefile)
        self.assertIn('"$$tmpdir/venv/bin/python" -m pytest -q', makefile)
        self.assertIn("build-check:", makefile)
        self.assertIn("package-smoke:", makefile)
        self.assertIn("script-smoke:", makefile)
        self.assertIn("bundle-audit-smoke:", makefile)
        self.assertIn("macos-smoke:", makefile)
        self.assertIn("security-smoke:", makefile)
        self.assertIn("dependency-audit-smoke:", makefile)
        self.assertIn("docs-smoke:", makefile)
        self.assertIn("governance-smoke:", makefile)
        self.assertIn("open-source-smoke:", makefile)
        self.assertIn("distribution-smoke:", makefile)
        self.assertIn("zipapp", makefile)
        self.assertIn("cleanmac.pyz", makefile)
        self.assertIn("class Cleanmac < Formula", makefile)
        self.assertIn("homebrew_formula", makefile)
        self.assertIn("release-artifacts-smoke:", makefile)
        self.assertIn("no-cache-check:", makefile)
        self.assertIn("docker-test", makefile)
        self.assertIn("no-cache-docker-test:", makefile)
        self.assertIn("no-cache-release-check:", makefile)
        self.assertIn(
            "release-check: quality-check local-test pytest-test build-check package-smoke script-smoke bundle-audit-smoke macos-smoke security-smoke dependency-audit-smoke docs-smoke governance-smoke open-source-smoke distribution-smoke release-artifacts-smoke docker-test",
            makefile,
        )
        self.assertIn("PYTHON ?= python3", makefile)
        self.assertIn("DOCKER_IMAGE ?= debian:bookworm-slim", makefile)
        self.assertIn("DOCKER_RUN_FLAGS ?=", makefile)
        self.assertIn('-v "$(SANDBOX_MOUNT):/work:ro"', makefile)
        self.assertIn("$(DOCKER_RUN_FLAGS)", makefile)
        self.assertIn('DOCKER_RUN_FLAGS="--pull=always" $(MAKE) docker-test', makefile)
        self.assertIn("$(PYTHON) -m ruff format --check .", makefile)
        self.assertIn("$(PYTHON) -m ruff check .", makefile)
        self.assertIn("$(PYTHON) -m mypy", makefile)
        self.assertIn("$(PYTHON) -m coverage run -m unittest -v", makefile)
        self.assertIn("PIP_NO_CACHE_DIR=1", makefile)
        self.assertIn('PYTEST_ADDOPTS="-p no:cacheprovider"', makefile)
        self.assertIn('--cache-dir "$$mypy_cache"', makefile)
        self.assertIn("/tmp/cleanmac-mypy-cache-$$$$", makefile)
        self.assertIn('coverage run --data-file "$$coverage_dir/.coverage"', makefile)
        self.assertIn("pip install --no-cache-dir", makefile)
        self.assertIn("[ ! -e .pytest_cache ] || /bin/rm -R .pytest_cache", makefile)
        self.assertIn("./scripts/test.sh", makefile)
        self.assertIn("pytest-test", makefile)
        self.assertIn("$(PYTHON) -m venv", makefile)
        self.assertIn("$(PYTHON) -m build --wheel --sdist --outdir", makefile)
        self.assertIn("$(PYTHON) -m twine check", makefile)
        self.assertIn("-m pip install -e .", makefile)
        self.assertIn("-m build --wheel --sdist", makefile)
        self.assertIn("cleanmac-*.tar.gz", makefile)
        self.assertIn("wheel-capabilities.json", makefile)
        self.assertIn("sdist-capabilities.json", makefile)
        self.assertIn("python3 python3-venv make", makefile)
        self.assertIn("trap 'rm -rf", makefile)
        self.assertIn("capabilities.json", makefile)
        self.assertIn("template_validation", makefile)
        self.assertIn("cleanmac.command-template-validation.v1", makefile)
        self.assertIn("make docs-smoke", makefile)
        self.assertIn("make governance-smoke", makefile)
        self.assertIn("make open-source-smoke", makefile)
        self.assertIn("make dependency-audit-smoke", makefile)
        self.assertIn("make no-cache-check", makefile)
        self.assertIn("make no-cache-release-check", makefile)
        self.assertIn("CONTRIBUTING.md", makefile)
        self.assertIn("SECURITY.md", makefile)
        self.assertIn("CODE_OF_CONDUCT.md", makefile)
        self.assertIn(".github/PULL_REQUEST_TEMPLATE.md", makefile)
        self.assertIn(".gitleaks.toml", makefile)
        self.assertIn(".github/dependabot.yml", makefile)
        self.assertIn(".github/workflows/codeql.yml", makefile)
        self.assertIn(".github/workflows/release.yml", makefile)
        self.assertIn("SHA256SUMS", makefile)
        self.assertIn("SBOM.json", makefile)
        self.assertIn("pip-audit", makefile)
        self.assertIn("trash_routing_flag", makefile)
        self.assertIn("README.CN.md", makefile)
        self.assertIn("-m json.tool", makefile)

    def test_readme_audit_examples_keep_global_flags_before_command(self) -> None:
        for path, heading in (
            (PROJECT_ROOT / "docs/doc/README.md", "### 5. Generate audit report files"),
            (PROJECT_ROOT / "docs/doc/README.CN.md", "### 5. 生成审计报告文件"),
        ):
            lines = path.read_text(encoding="utf-8").splitlines()
            start = lines.index(heading)
            fence_start = next(index for index in range(start, len(lines)) if lines[index] == "```bash")
            fence_end = next(index for index in range(fence_start + 1, len(lines)) if lines[index] == "```")
            command = " ".join(
                line.strip().removesuffix("\\").strip()
                for line in lines[fence_start + 1 : fence_end]
                if not line.strip().startswith(">")
            )
            parts = shlex.split(command)

            self.assertEqual(parts[:2], ["python3", "cleanmac.py"], path.name)
            self.assertLess(parts.index("--report-file"), parts.index("clean"), path.name)
            actual_argv, grouped_command = cleancli.normalize_grouped_argv(parts[2:])
            parsed = cleancli.parse_args(actual_argv)
            self.assertTrue(parsed.json, path.name)
            self.assertEqual(parsed.report_file, "/tmp/cleanmac-audit.json")
            self.assertEqual(parsed.command, "clean")
            self.assertEqual(grouped_command, {"group": "clean", "action": "run", "mapped_command": "clean"})

    def test_makefile_release_check_dry_run_orders_quality_gates(self) -> None:
        if shutil.which("make") is None:
            self.skipTest("make is not installed in this validation environment")
        result = subprocess.run(
            ["make", "-n", "PYTHON=python3", "release-check"],
            cwd=PROJECT_ROOT,
            text=True,
            capture_output=True,
            check=True,
        )
        output = result.stdout

        expected_fragments = [
            "python3 -m ruff format --check .",
            "python3 -m ruff check .",
            "python3 -m mypy",
            "python3 -m coverage run -m unittest -v",
            "PYTHON=python3 ./scripts/test.sh",
            'python3 -m venv "$tmpdir/venv"',
            '"$tmpdir/venv/bin/python" -m pip install -e',
            '"$tmpdir/venv/bin/python" -m pytest -q',
            "python3 -m build --wheel --sdist --outdir",
            "python3 -m twine check",
            "-m pip install -e .",
            'cleanmac" --json capabilities',
            "-m json.tool",
            "python3 -c",
            "template_validation",
            "pip_audit --skip-editable --progress-spinner off",
            "scripts/generate_sbom.py",
            "README.CN.md",
            'run("workflow",',
            "CONTRIBUTING.md",
            'build-venv/bin/python" -m build --wheel --sdist',
            "wheel-capabilities.json",
            "sdist-capabilities.json",
            "install-capabilities.json",
            "docker run --rm",
        ]
        self.assertIn("SHA256SUMS", output)
        cursor = -1
        for fragment in expected_fragments:
            index = output.find(fragment)
            self.assertGreater(index, cursor, fragment)
            cursor = index

    def test_python_quality_tooling_is_configured(self) -> None:
        pyproject = (PROJECT_ROOT / "pyproject.toml").read_text(encoding="utf-8")
        precommit = (PROJECT_ROOT / ".pre-commit-config.yaml").read_text(encoding="utf-8")
        ci = (PROJECT_ROOT / ".github/workflows/ci.yml").read_text(encoding="utf-8")
        makefile = (PROJECT_ROOT / "Makefile").read_text(encoding="utf-8")

        self.assertIn("[project.optional-dependencies]", pyproject)
        self.assertIn('license = "MIT"', pyproject)
        self.assertNotIn("license = {text", pyproject)
        self.assertIn("dev = [", pyproject)
        self.assertIn("ruff>=", pyproject)
        self.assertIn("mypy>=", pyproject)
        self.assertIn("pytest>=", pyproject)
        self.assertIn("coverage[toml]>=", pyproject)
        self.assertIn("pip-audit>=", pyproject)
        self.assertIn("[tool.ruff]", pyproject)
        self.assertIn("[tool.mypy]", pyproject)
        self.assertIn("[tool.pytest.ini_options]", pyproject)
        self.assertIn("[tool.coverage.run]", pyproject)
        self.assertIn("[tool.coverage.report]", pyproject)

        self.assertIn("pre-commit-hooks", precommit)
        self.assertIn("ruff-pre-commit", precommit)
        self.assertIn("mirrors-mypy", precommit)

        self.assertIn("actions/setup-python@v6.2.0", ci)
        self.assertIn("actions/setup-python@a309ff8b426b58ec0e2a45f0f869d46889d02405", ci)
        self.assertIn("PYTHON: .venv/bin/python", ci)
        self.assertIn("Create venv and install dev dependencies", ci)
        self.assertIn("Create venv and install build dependencies", ci)
        self.assertIn("Create venv and install smoke dependencies", ci)
        self.assertIn("Create venv and install test dependencies", ci)
        self.assertIn("Create no-cache venv bootstrap", ci)
        self.assertIn('python-version: ["3.10", "3.11", "3.12", "3.13"]', ci)
        self.assertIn("make quality-check", ci)
        self.assertIn("make local-test", ci)
        self.assertIn("Run pytest compatibility check", ci)
        self.assertIn("make pytest-test", ci)
        self.assertIn("make build-check", ci)
        self.assertIn("make package-smoke", ci)
        self.assertIn("make script-smoke", ci)
        self.assertIn("make docs-smoke", ci)
        self.assertIn("make governance-smoke", ci)
        self.assertIn("make open-source-smoke", ci)
        self.assertIn("make distribution-smoke", ci)
        self.assertIn("make dependency-audit-smoke", ci)
        self.assertIn("make docker-test", ci)
        self.assertIn("make no-cache-check", ci)
        self.assertIn("make no-cache-docker-test", ci)
        self.assertIn("Compatibility smoke", ci)
        self.assertIn("os: [macos-14, macos-15, ubuntu-latest]", ci)
        self.assertIn("CLEANMAC_TEST_NO_AUTH", ci)
        self.assertIn("macOS smoke for remap, Trash, plist, and bundle parsing", ci)
        self.assertIn("make macos-smoke", ci)
        self.assertIn("Ubuntu sandbox, governance JSON, and package build smoke", ci)
        self.assertIn("test_grouped_clean_commands_match_flat_alias_reports", ci)
        self.assertIn("make package-smoke", ci)
        self.assertIn("make build-check", ci)
        self.assertIn("Linux container smoke", ci)
        self.assertIn("Check unsafe delete patterns", ci)
        self.assertIn("make security-smoke", ci)
        self.assertIn(
            "shutil.rmtree must stay in cleancli/delete_ops.py", (PROJECT_ROOT / "scripts/security_scan.py").read_text()
        )
        self.assertIn("subprocess must not directly invoke rm", (PROJECT_ROOT / "scripts/security_scan.py").read_text())
        self.assertIn(
            "shell must not invoke privileged command", (PROJECT_ROOT / "scripts/security_scan.py").read_text()
        )
        self.assertIn(
            "workflow must not invoke privileged command", (PROJECT_ROOT / "scripts/security_scan.py").read_text()
        )
        self.assertIn("Scan for secrets (gitleaks)", ci)
        self.assertIn("gitleaks/gitleaks-action", ci)
        self.assertIn("No-cache dependency install", ci)
        self.assertIn("no-cache-check:", makefile)
        self.assertIn("set -e", makefile)
        self.assertIn("--no-cache-dir", makefile)
        self.assertIn('PYTEST_ADDOPTS="-p no:cacheprovider"', makefile)
        self.assertNotIn("actions/cache", ci)

    def test_release_workflow_generates_checksums_attestation_and_pypi_publish(self) -> None:
        release = (PROJECT_ROOT / ".github/workflows/release.yml").read_text(encoding="utf-8")

        self.assertIn("id-token: write", release)
        self.assertIn("attestations: write", release)
        self.assertIn("SHA256SUMS", release)
        self.assertIn("SBOM.json", release)
        self.assertIn("release-assets/SHA256SUMS", release)
        self.assertIn("release-assets/SBOM.json", release)
        self.assertIn("ARTIFACT-MANIFEST.json", release)
        self.assertIn("cleanmac.release-artifact-manifest.v1", release)
        self.assertIn("homebrew_formula", release)
        self.assertIn("publish_after_cross_platform_verification", release)
        self.assertIn("Build release artifacts", release)
        self.assertIn("Verify release artifacts (${{ matrix.os }})", release)
        self.assertIn("os: [ubuntu-latest, macos-14, macos-15]", release)
        self.assertIn("needs: build", release)
        self.assertIn("needs: verify-release-artifacts", release)
        self.assertIn("actions/upload-artifact@043fb46d1a93c77aae656e7c1c64a875d1fc6a0a", release)
        self.assertIn("actions/download-artifact@37930b1c2abaa49bbe596cd826c3c89aef350131", release)
        self.assertIn("name: cleanmac-dist", release)
        self.assertIn("name: cleanmac-release-assets", release)
        self.assertIn("Verify wheel install and release checksums", release)
        self.assertIn("Run real macOS smoke against release candidate", release)
        self.assertIn("make real-macos-smoke", release)
        self.assertIn("actions/attest-build-provenance@v2", release)
        self.assertIn("actions/attest-build-provenance@e8998f949152b193b063cb0ec769d69d929409be", release)
        self.assertIn("pypa/gh-action-pypi-publish@release/v1", release)
        self.assertIn("pypa/gh-action-pypi-publish@cef221092ed1bacb1cc03d23a2d87d1d172e277b", release)
        self.assertIn("PYTHON: .venv/bin/python", release)
        self.assertIn("Create venv and install build dependencies", release)
        self.assertIn("bundle-audit-smoke", release)
        self.assertIn("macos-smoke", release)
        self.assertIn("security-smoke", release)
        self.assertIn("cleanmac --json capabilities", release)
        self.assertNotIn('packages-dir: "release-assets"', release)

    def test_open_source_governance_files_are_configured(self) -> None:
        required_files = [
            "LICENSE",
            "CONTRIBUTING.md",
            "SECURITY.md",
            "CODE_OF_CONDUCT.md",
            "AGENTS.md",
            ".gitleaks.toml",
            ".github/PULL_REQUEST_TEMPLATE.md",
            ".github/dependabot.yml",
            ".github/workflows/ci.yml",
            ".github/workflows/bundle_audit.yml",
            ".github/workflows/codeql.yml",
            ".github/workflows/release.yml",
            ".github/ISSUE_TEMPLATE/bug_report.yml",
            ".github/ISSUE_TEMPLATE/feature_request.yml",
            ".github/ISSUE_TEMPLATE/config.yml",
            "scripts/generate_sbom.py",
        ]
        for relative_path in required_files:
            self.assertTrue((PROJECT_ROOT / relative_path).is_file(), relative_path)
        self.assertFalse((PROJECT_ROOT / ".github/templates").exists())
        self.assertFalse((PROJECT_ROOT / ".github/CODEOWNERS").exists())

        license_text = (PROJECT_ROOT / "LICENSE").read_text(encoding="utf-8")
        contributing = (PROJECT_ROOT / "CONTRIBUTING.md").read_text(encoding="utf-8")
        security = (PROJECT_ROOT / "SECURITY.md").read_text(encoding="utf-8")
        codeql = (PROJECT_ROOT / ".github/workflows/codeql.yml").read_text(encoding="utf-8")
        dependabot = (PROJECT_ROOT / ".github/dependabot.yml").read_text(encoding="utf-8")
        gitleaks = (PROJECT_ROOT / ".gitleaks.toml").read_text(encoding="utf-8")
        agents = (PROJECT_ROOT / "AGENTS.md").read_text(encoding="utf-8")
        pyproject = (PROJECT_ROOT / "pyproject.toml").read_text(encoding="utf-8")
        readme = (PROJECT_ROOT / "README.md").read_text(encoding="utf-8")
        readme_cn = (PROJECT_ROOT / "README.CN.md").read_text(encoding="utf-8")
        local_developer_path = "/" + "Users" + "/" + "bytedance"

        self.assertIn("MIT License", license_text)
        self.assertIn("make open-source-smoke", contributing)
        self.assertIn("path traversal", security.lower())
        self.assertIn("github/codeql-action/init@v3", codeql)
        uses_lines: list[str] = []
        for workflow in (PROJECT_ROOT / ".github/workflows").glob("*.yml"):
            uses_lines.extend(
                line.strip()
                for line in workflow.read_text(encoding="utf-8").splitlines()
                if line.strip().startswith("uses: ")
            )
        self.assertTrue(uses_lines)
        for line in uses_lines:
            self.assertRegex(line, r"@[0-9a-f]{40}(?:\s|$)", line)
        self.assertIn("package-ecosystem: github-actions", dependabot)
        self.assertIn("useDefault = true", gitleaks)
        self.assertNotIn("README\\.md", gitleaks)
        self.assertNotIn("README\\.CN", gitleaks)
        self.assertIn("Dry-run first", readme)
        self.assertIn("MCP Server", readme)
        self.assertNotIn(local_developer_path, readme)
        self.assertNotIn(local_developer_path, readme_cn)
        self.assertIn("cleancli/delete_ops.py", agents)
        self.assertIn("launchctl", agents)
        self.assertIn("tests/data/dangerous_paths.txt", agents)
        for required_agent_section in (
            "## 项目地图",
            "## 常用命令",
            "## 关键安全规则",
            "## 高风险模块所有权与必跑测试",
            "## 历史事故和踩坑案例",
            "cleancli/protection_data.py",
            "cleancli/protection.py",
            "cleancli/scripts.py",
            "cleancli/governance.py",
            "Symlink 指向系统路径",
            "Group Container wildcard",
            "Trash fail-closed",
            "sudo prompt",
            "Plan replay root/home 不一致",
            "Operation log 不可写",
            "Shell template unsafe auto execution",
            "临时 venv",
        ):
            self.assertIn(required_agent_section, agents)
        self.assertIn('license-files = ["LICENSE"]', pyproject)
        self.assertIn("[project.urls]", pyproject)
        self.assertIn("Security =", pyproject)
        self.assertIn("pip-audit>=", pyproject)

    def test_project_files_do_not_contain_removed_product_references(self) -> None:
        forbidden = ("clean" + "me", "Clean" + " Me", "clean" + " me", "mo" + "le", "MO" + "LE")
        local_developer_path = "/" + "users" + "/" + "bytedance"
        scanned = [
            PROJECT_ROOT / "cleanmac.py",
            PROJECT_ROOT / "test_cleanmac.py",
            PROJECT_ROOT / "README.md",
            PROJECT_ROOT / "README.CN.md",
            PROJECT_ROOT / "Makefile",
            PROJECT_ROOT / ".github/workflows/ci.yml",
        ]

        for path in scanned:
            content = path.read_text(encoding="utf-8")
            lowered = content.lower()
            for token in forbidden:
                self.assertNotIn(token.lower(), lowered, path.name)
            self.assertNotIn(local_developer_path, lowered, path.name)


if __name__ == "__main__":
    unittest.main(verbosity=2)
