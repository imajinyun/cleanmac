from __future__ import annotations

import hashlib
import json

from tests.helpers import cleanmac_test_env, make_sandbox, run_cli


class TestAnalyzeTree:
    def test_analyze_tree_reports_largest_directories(self) -> None:
        tmp, root, home = make_sandbox()
        with tmp, cleanmac_test_env():
            large_dir = root / "Users/tester/large-stuff"
            large_dir.mkdir(parents=True)
            (large_dir / "big.bin").write_bytes(b"x" * 1024 * 100)
            small_dir = root / "Users/tester/small-stuff"
            small_dir.mkdir(parents=True)
            (small_dir / "tiny.txt").write_text("small")

            result = run_cli(
                "--root",
                str(root),
                "--home",
                str(home),
                "--json",
                "analyze-tree",
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
            assert len(report["entries"]) >= 2

    def test_analyze_tree_min_size_filters_small_files(self) -> None:
        tmp, root, home = make_sandbox()
        with tmp, cleanmac_test_env():
            big = root / "Users/tester/big-file.bin"
            big.write_bytes(b"x" * 1024 * 1024 * 2)
            small = root / "Users/tester/small-file.txt"
            small.write_text("tiny")

            result = run_cli(
                "--root",
                str(root),
                "--home",
                str(home),
                "--json",
                "analyze-tree",
                "--path",
                "/Users/tester",
                "--depth",
                "0",
                "--min-size-mb",
                "1",
            )
            report = json.loads(result.stdout)

            for entry in report["entries"]:
                assert entry["bytes"] >= 1024 * 1024

    def test_analyze_tree_top_limits_results(self) -> None:
        tmp, root, home = make_sandbox()
        with tmp, cleanmac_test_env():
            for i in range(10):
                d = root / f"Users/tester/dir-{i}"
                d.mkdir(parents=True)
                (d / "file.bin").write_bytes(b"x" * 1024 * (i + 1) * 10)

            result = run_cli(
                "--root",
                str(root),
                "--home",
                str(home),
                "--json",
                "analyze-tree",
                "--path",
                "/Users/tester",
                "--depth",
                "1",
                "--top",
                "3",
            )
            report = json.loads(result.stdout)

            assert len(report["entries"]) <= 3

    def test_analyze_tree_is_read_only(self) -> None:
        tmp, root, home = make_sandbox()
        with tmp, cleanmac_test_env():
            test_file = root / "Users/tester/test.txt"
            test_file.write_text("hello")
            mtime_before = test_file.stat().st_mtime

            run_cli(
                "--root",
                str(root),
                "--home",
                str(home),
                "--json",
                "analyze-tree",
                "--path",
                "/Users/tester",
            )

            assert test_file.exists()
            assert test_file.stat().st_mtime == mtime_before


class TestDuplicateFiles:
    def test_analyze_duplicates_finds_identical_files(self) -> None:
        tmp, root, home = make_sandbox()
        with tmp, cleanmac_test_env():
            dup_dir = root / "Users/tester/duplicates"
            dup_dir.mkdir(parents=True)
            content = b"duplicate content here" * 1000
            (dup_dir / "copy-a.bin").write_bytes(content)
            (dup_dir / "copy-b.bin").write_bytes(content)
            (dup_dir / "copy-c.bin").write_bytes(content)
            (dup_dir / "unique.bin").write_bytes(b"unique content")

            result = run_cli(
                "--root",
                str(root),
                "--home",
                str(home),
                "--json",
                "analyze-duplicates",
                "--path",
                "/Users/tester/duplicates",
                "--min-size-mb",
                "0",
            )
            report = json.loads(result.stdout)

            assert report["schema"] == "cleanmac.duplicate-files.v1"
            assert report["total_groups"] >= 1
            assert report["total_duplicate_files"] >= 2
            assert "groups" in report

    def test_analyze_duplicates_sha256_matches(self) -> None:
        tmp, root, home = make_sandbox()
        with tmp, cleanmac_test_env():
            dup_dir = root / "Users/tester/dup-check"
            dup_dir.mkdir(parents=True)
            content = b"verify-hash" * 500
            (dup_dir / "a.bin").write_bytes(content)
            (dup_dir / "b.bin").write_bytes(content)
            expected_hash = hashlib.sha256(content).hexdigest()

            result = run_cli(
                "--root",
                str(root),
                "--home",
                str(home),
                "--json",
                "analyze-duplicates",
                "--path",
                "/Users/tester/dup-check",
                "--min-size-mb",
                "0",
            )
            report = json.loads(result.stdout)

            found = False
            for group in report["groups"]:
                if group["hash"] == expected_hash:
                    found = True
                    assert group["file_count"] == 2
                    assert len(group["files"]) == 2
                    break
            assert found, f"Expected hash {expected_hash} not found in groups"

    def test_analyze_duplicates_is_read_only(self) -> None:
        tmp, root, home = make_sandbox()
        with tmp, cleanmac_test_env():
            dup_dir = root / "Users/tester/dup-safe"
            dup_dir.mkdir(parents=True)
            content = b"read-only test" * 1000
            (dup_dir / "file1.bin").write_bytes(content)
            (dup_dir / "file2.bin").write_bytes(content)
            count_before = len(list(dup_dir.iterdir()))

            run_cli(
                "--root",
                str(root),
                "--home",
                str(home),
                "--json",
                "analyze-duplicates",
                "--path",
                "/Users/tester/dup-safe",
                "--min-size-mb",
                "0",
            )

            assert len(list(dup_dir.iterdir())) == count_before

    def test_analyze_duplicates_min_size_excludes_small_files(self) -> None:
        tmp, root, home = make_sandbox()
        with tmp, cleanmac_test_env():
            dup_dir = root / "Users/tester/dup-filtered"
            dup_dir.mkdir(parents=True)
            (dup_dir / "small-a.txt").write_text("same")
            (dup_dir / "small-b.txt").write_text("same")

            result = run_cli(
                "--root",
                str(root),
                "--home",
                str(home),
                "--json",
                "analyze-duplicates",
                "--path",
                "/Users/tester/dup-filtered",
                "--min-size-mb",
                "1",
            )
            report = json.loads(result.stdout)

            assert report["total_groups"] == 0
            assert report["total_duplicate_files"] == 0


class TestLargeFilesCategory:
    def test_large_files_category_exists(self) -> None:
        from cleancli.core import CATEGORY_BY_KEY

        assert "largeFiles" in CATEGORY_BY_KEY
        cat = CATEGORY_BY_KEY["largeFiles"]
        assert cat.risk in ("low", "medium", "high")

    def test_large_files_is_advanced_by_default(self) -> None:
        from cleancli.core import CATEGORY_BY_KEY

        cat = CATEGORY_BY_KEY["largeFiles"]
        assert cat.advanced is True


class TestOldFilesCategory:
    def test_old_files_category_exists(self) -> None:
        from cleancli.core import CATEGORY_BY_KEY

        assert "oldFiles" in CATEGORY_BY_KEY

    def test_old_files_has_age_config(self) -> None:
        from cleancli.core import CATEGORY_BY_KEY

        cat = CATEGORY_BY_KEY["oldFiles"]
        assert hasattr(cat, "default_older_than_days")
        assert cat.default_older_than_days is not None
        assert cat.default_older_than_days > 0


class TestAnalyzeToolContracts:
    def test_analyze_tree_schema_version_is_stable(self) -> None:
        from cleancli.ai_versioning import render_ai_schema_registry

        registry = render_ai_schema_registry()
        names = [e.get("name", "") for e in registry.get("entries", [])]
        assert "cleanmac.analyze-tree.v1" in names

    def test_duplicate_files_schema_version_is_stable(self) -> None:
        from cleancli.ai_versioning import render_ai_schema_registry

        registry = render_ai_schema_registry()
        names = [e.get("name", "") for e in registry.get("entries", [])]
        assert "cleanmac.duplicate-files.v1" in names

    def test_ai_tools_include_analyze_entries(self) -> None:
        result = run_cli("--json", "ai-tools")
        tools = json.loads(result.stdout)
        tool_list = tools.get("tools", tools.get("openai", []))
        if isinstance(tool_list, dict):
            tool_list = tool_list.get("tools", [])
        tool_names = set()
        for t in tool_list:
            if isinstance(t, dict):
                tool_names.add(t.get("function", {}).get("name", ""))
                tool_names.add(t.get("name", ""))

        assert "cleanmac_analyze_tree" in tool_names
        assert "cleanmac_analyze_duplicates" in tool_names
        assert "cleanmac_analyze_large_files" in tool_names
        assert "cleanmac_analyze_old_files" in tool_names
