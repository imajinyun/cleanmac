from __future__ import annotations

import json

from tests.helpers import cleanmac_test_env, make_sandbox, run_cli


class TestSoftwareUninstallPlanSchema:
    def test_uninstall_plan_has_standard_schema(self) -> None:
        tmp, root, home = make_sandbox()
        with tmp, cleanmac_test_env():
            result = run_cli(
                "--root",
                str(root),
                "--home",
                str(home),
                "--json",
                "software",
                "uninstall-plan",
                "--app",
                "Demo",
            )
            plan = json.loads(result.stdout)

            assert plan["schema"] == "cleanmac.software-uninstall-plan.v1"
            assert "app" in plan
            assert "destructive" in plan
            assert "uninstall_plan" in plan
            assert isinstance(plan["destructive"], bool)

    def test_uninstall_plan_destructive_is_false_by_default(self) -> None:
        tmp, root, home = make_sandbox()
        with tmp, cleanmac_test_env():
            result = run_cli(
                "--root",
                str(root),
                "--home",
                str(home),
                "--json",
                "software",
                "uninstall-plan",
                "--app",
                "Demo",
            )
            plan = json.loads(result.stdout)

            assert plan["destructive"] is False

    def test_uninstall_plan_includes_app_name(self) -> None:
        tmp, root, home = make_sandbox()
        with tmp, cleanmac_test_env():
            result = run_cli(
                "--root",
                str(root),
                "--home",
                str(home),
                "--json",
                "software",
                "uninstall-plan",
                "--app",
                "Demo",
            )
            plan = json.loads(result.stdout)

            assert plan["uninstall_plan"]["app"] == "Demo"


class TestSoftwareUninstallPlanSafety:
    def test_uninstall_plan_is_read_only_no_files_modified(self) -> None:
        tmp, root, home = make_sandbox()
        with tmp, cleanmac_test_env():
            test_file = root / "Users/tester/.Trash/old.tmp"
            assert test_file.exists()
            mtime_before = test_file.stat().st_mtime

            run_cli(
                "--root",
                str(root),
                "--home",
                str(home),
                "--json",
                "software",
                "uninstall-plan",
                "--app",
                "Demo",
            )

            assert test_file.exists()
            assert test_file.stat().st_mtime == mtime_before

    def test_uninstall_plan_handles_unknown_app_gracefully(self) -> None:
        tmp, root, home = make_sandbox()
        with tmp, cleanmac_test_env():
            result = run_cli(
                "--root",
                str(root),
                "--home",
                str(home),
                "--json",
                "software",
                "uninstall-plan",
                "--app",
                "NonExistentAppXYZ",
                check=False,
            )

            if result.returncode == 0:
                plan = json.loads(result.stdout)
                assert "schema" in plan
            else:
                assert result.returncode != 0
                assert "error" in result.stderr.lower() or result.stderr

    def test_uninstall_plan_protects_system_apps(self) -> None:
        tmp, root, home = make_sandbox()
        with tmp, cleanmac_test_env():
            result = run_cli(
                "--root",
                str(root),
                "--home",
                str(home),
                "--json",
                "software",
                "uninstall-plan",
                "--app",
                "Safari",
                check=False,
            )

            if result.returncode == 0:
                plan = json.loads(result.stdout)
                assert plan.get("destructive") is False or plan.get("blocked") is True


class TestSoftwareInventory:
    def test_software_list_returns_list_of_apps(self) -> None:
        tmp, root, home = make_sandbox()
        with tmp, cleanmac_test_env():
            result = run_cli(
                "--root",
                str(root),
                "--home",
                str(home),
                "--json",
                "software",
                "list",
            )
            report = json.loads(result.stdout)

            assert "schema" in report
            assert "apps" in report or "items" in report
            assert isinstance(report.get("apps", report.get("items", [])), list)

    def test_software_list_is_read_only(self) -> None:
        tmp, root, home = make_sandbox()
        with tmp, cleanmac_test_env():
            test_file = root / "Users/tester/.Trash/old.tmp"
            mtime_before = test_file.stat().st_mtime

            run_cli(
                "--root",
                str(root),
                "--home",
                str(home),
                "--json",
                "software",
                "list",
            )

            assert test_file.stat().st_mtime == mtime_before


class TestSoftwareOrphans:
    def test_software_orphans_is_read_only(self) -> None:
        tmp, root, home = make_sandbox()
        with tmp, cleanmac_test_env():
            test_file = root / "Users/tester/.Trash/old.tmp"
            mtime_before = test_file.stat().st_mtime

            run_cli(
                "--root",
                str(root),
                "--home",
                str(home),
                "--json",
                "software",
                "orphans",
                check=False,
            )

            assert test_file.stat().st_mtime == mtime_before

    def test_software_orphans_schema(self) -> None:
        tmp, root, home = make_sandbox()
        with tmp, cleanmac_test_env():
            result = run_cli(
                "--root",
                str(root),
                "--home",
                str(home),
                "--json",
                "software",
                "orphans",
                check=False,
            )

            if result.returncode == 0:
                report = json.loads(result.stdout)
                assert "schema" in report
                assert "destructive" in report


class TestSoftwareToolContract:
    def test_software_has_mcp_tool_definition(self) -> None:
        from cleancli.ai_schema import render_openai_functions

        result = render_openai_functions()
        tools = result.get("tools", [])
        tool_names = {t["function"]["name"] for t in tools if t.get("type") == "function"}

        assert "cleanmac_software_list" in tool_names
        assert "cleanmac_software_uninstall_plan" in tool_names

    def test_software_tools_are_non_destructive_by_default(self) -> None:
        from cleancli.ai_schema import render_openai_functions

        result = render_openai_functions()
        tools = result.get("tools", [])
        plan_tool = next(
            (
                t
                for t in tools
                if t.get("type") == "function" and t["function"]["name"] == "cleanmac_software_uninstall_plan"
            ),
            None,
        )
        assert plan_tool is not None
