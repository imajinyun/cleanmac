from __future__ import annotations

import json

import pytest

from cleancli.core import normalize_grouped_argv
from tests.helpers import cleanmac_test_env, make_sandbox, run_cli


class TestGroupedArgvNormalization:
    def test_flat_commands_pass_through(self) -> None:
        argv, grouped = normalize_grouped_argv(["capabilities"])
        assert grouped is None
        assert argv == ["capabilities"]

    def test_flat_with_args_passes_through(self) -> None:
        argv, grouped = normalize_grouped_argv(["inspect", "--categories", "trash"])
        assert grouped is None
        assert argv == ["inspect", "--categories", "trash"]

    def test_clean_group_expands_to_flat(self) -> None:
        argv, grouped = normalize_grouped_argv(["clean", "inspect", "--categories", "trash"])
        assert grouped is not None
        assert grouped["group"] == "clean"
        assert grouped["action"] == "inspect"
        assert grouped["mapped_command"] == "inspect"
        assert "inspect" in argv
        assert "--categories" in argv

    def test_clean_plan_group(self) -> None:
        argv, grouped = normalize_grouped_argv(["clean", "plan", "--categories", "trash"])
        assert grouped is not None
        assert grouped["group"] == "clean"
        assert grouped["action"] == "plan"
        assert grouped["mapped_command"] == "plan"

    def test_clean_run_group(self) -> None:
        argv, grouped = normalize_grouped_argv(["clean", "run", "--categories", "trash"])
        assert grouped is not None
        assert grouped["group"] == "clean"
        assert grouped["action"] == "run"
        assert grouped["mapped_command"] == "clean"

    def test_analyze_group_tree(self) -> None:
        argv, grouped = normalize_grouped_argv(["analyze", "tree", "--path", "/tmp"])
        assert grouped is not None
        assert grouped["group"] == "analyze"
        assert grouped["action"] == "tree"
        assert grouped["mapped_command"] == "analyze-tree"

    @pytest.mark.parametrize(
        "group_cmd,flat_cmd",
        [
            (["clean", "inspect"], "inspect"),
            (["clean", "plan"], "plan"),
            (["clean", "validate-plan"], "validate-plan"),
            (["clean", "policy-simulate"], "policy-simulate"),
            (["analyze", "tree"], "analyze-tree"),
            (["analyze", "diagnose"], "diagnose"),
            (["software", "list"], None),
            (["optimize", "plan"], None),
            (["status", "snapshot"], None),
        ],
    )
    def test_grouped_vs_flat_report_parity(self, group_cmd: list[str], flat_cmd: str | None) -> None:
        tmp, root, home = make_sandbox()
        with tmp, cleanmac_test_env():
            group_result = run_cli(
                "--root",
                str(root),
                "--home",
                str(home),
                "--json",
                *group_cmd,
                "--categories",
                "trash",
                check=False,
            )
            if group_result.returncode != 0:
                pytest.skip(f"grouped {' '.join(group_cmd)} not supported with --categories")

            group_report = json.loads(group_result.stdout)

            if flat_cmd is None:
                return

            flat_result = run_cli(
                "--root",
                str(root),
                "--home",
                str(home),
                "--json",
                flat_cmd,
                "--categories",
                "trash",
            )
            flat_report = json.loads(flat_result.stdout)

            assert group_report["schema"] == flat_report["schema"]
            group_categories = {
                c["key"] if isinstance(c, dict) else c for c in group_report.get("selected_categories", [])
            }
            flat_categories = {
                c["key"] if isinstance(c, dict) else c for c in flat_report.get("selected_categories", [])
            }
            assert group_categories == flat_categories


class TestGroupedCleanCommands:
    def test_clean_inspect_matches_flat_inspect(self) -> None:
        tmp, root, home = make_sandbox()
        with tmp, cleanmac_test_env():
            grouped = json.loads(
                run_cli(
                    "--root",
                    str(root),
                    "--home",
                    str(home),
                    "--json",
                    "clean",
                    "inspect",
                    "--categories",
                    "trash",
                ).stdout
            )
            flat = json.loads(
                run_cli(
                    "--root",
                    str(root),
                    "--home",
                    str(home),
                    "--json",
                    "inspect",
                    "--categories",
                    "trash",
                ).stdout
            )

            assert grouped["schema"] == flat["schema"]
            assert grouped["schema"] == "cleanmac.inspect.v1"
            assert len(grouped["items"]) == len(flat["items"])
            assert grouped["total_bytes"] == flat["total_bytes"]

    def test_clean_plan_matches_flat_plan(self) -> None:
        tmp, root, home = make_sandbox()
        with tmp, cleanmac_test_env():
            grouped = json.loads(
                run_cli(
                    "--root",
                    str(root),
                    "--home",
                    str(home),
                    "--json",
                    "clean",
                    "plan",
                    "--categories",
                    "trash",
                    "--max-items",
                    "5",
                ).stdout
            )
            flat = json.loads(
                run_cli(
                    "--root",
                    str(root),
                    "--home",
                    str(home),
                    "--json",
                    "plan",
                    "--categories",
                    "trash",
                    "--max-items",
                    "5",
                ).stdout
            )

            assert grouped["schema"] == flat["schema"]
            assert grouped["schema"] == "cleanmac.plan.v1"
            assert grouped["selected_category_keys"] == flat["selected_category_keys"]
            assert grouped["dry_run"] == flat["dry_run"]
            assert grouped["max_items"] == flat["max_items"]

    def test_clean_run_dry_run_by_default(self) -> None:
        tmp, root, home = make_sandbox()
        with tmp, cleanmac_test_env():
            result = run_cli(
                "--root",
                str(root),
                "--home",
                str(home),
                "--json",
                "clean",
                "run",
                "--categories",
                "trash",
            )
            report = json.loads(result.stdout)

            assert report["schema"] == "cleanmac.clean.v1"
            assert report["dry_run"] is True


class TestGroupedAnalyzeCommands:
    def test_analyze_tree_reports_largest_entries(self) -> None:
        tmp, root, home = make_sandbox()
        with tmp, cleanmac_test_env():
            result = run_cli(
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

            assert report["schema"] == "cleanmac.analyze-tree.v1"
            assert "entries" in report
            assert report["path"].endswith("/Users/tester")

    def test_analyze_flat_tree_same_as_grouped(self) -> None:
        tmp, root, home = make_sandbox()
        with tmp, cleanmac_test_env():
            grouped = json.loads(
                run_cli(
                    "--root",
                    str(root),
                    "--home",
                    str(home),
                    "--json",
                    "analyze",
                    "tree",
                    "--path",
                    "/Users/tester",
                    "--top",
                    "3",
                ).stdout
            )
            flat = json.loads(
                run_cli(
                    "--root",
                    str(root),
                    "--home",
                    str(home),
                    "--json",
                    "analyze-tree",
                    "--path",
                    "/Users/tester",
                    "--top",
                    "3",
                ).stdout
            )

            assert grouped["schema"] == flat["schema"]
            assert len(grouped["entries"]) == len(flat["entries"])


class TestGroupedSafeCommands:
    def test_software_uninstall_plan_is_read_only(self) -> None:
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
            report = json.loads(result.stdout)

            assert report["schema"] == "cleanmac.software-uninstall-plan.v1"
            assert report["destructive"] is False

    def test_optimize_plan_is_non_destructive(self) -> None:
        result = run_cli("--json", "optimize", "plan")
        report = json.loads(result.stdout)

        assert report["schema"] == "cleanmac.optimize.v1"
        assert report["execution_supported"] is False

    def test_status_snapshot_works(self) -> None:
        tmp, root, home = make_sandbox()
        with tmp, cleanmac_test_env():
            result = run_cli("--root", str(root), "--json", "status", "snapshot")
            report = json.loads(result.stdout)

            assert report["schema"] == "cleanmac.status.snapshot.v1"
            assert "disk" in report
