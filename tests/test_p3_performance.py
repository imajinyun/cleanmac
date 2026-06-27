"""P3-08: Performance benchmarking framework tests.

Validates that core operations complete within reasonable time budgets for typical
single-shot AI-first usage patterns.
"""

from __future__ import annotations

import time
from pathlib import Path

import pytest

from cleancli.core import CATEGORY_BY_KEY, clean, delete_policy_for_context, render_capabilities

LOGICAL_HOME = Path("/Users/tester")


@pytest.fixture
def p3_bench_sandbox(tmp_path: Path) -> Path:
    root = tmp_path
    (root / "Users/tester/.Trash").mkdir(parents=True)
    (root / "Users/tester/Library/Caches/com.example.app").mkdir(parents=True)
    for i in range(20):
        (root / f"Users/tester/Library/Caches/com.example.app/cache_{i}.dat").write_text(f"data {i}" * 1000)
    for i in range(10):
        (root / f"Users/tester/.Trash/trash_{i}.tmp").write_text(f"trash {i}")
    return root


class TestPerformanceBaseline:
    def test_capabilities_render_completes(self) -> None:
        # Capabilities does full discovery; we only verify it completes without error
        result = render_capabilities()
        assert result is not None
        assert "schema" in result

    def test_clean_dry_run_trash_under_2s(self, p3_bench_sandbox: Path) -> None:
        start = time.perf_counter()
        clean(
            [CATEGORY_BY_KEY["trash"]],
            root=p3_bench_sandbox,
            home=LOGICAL_HOME,
            execute=False,
            operation_log=str(p3_bench_sandbox / "ops.jsonl"),
            command_argv=["clean", "--categories", "trash"],
        )
        elapsed = time.perf_counter() - start
        assert elapsed < 2.0, f"Trash dry-run took {elapsed:.3f}s"

    def test_clean_dry_run_usercache_under_2s(self, p3_bench_sandbox: Path) -> None:
        start = time.perf_counter()
        clean(
            [CATEGORY_BY_KEY["userCache"]],
            root=p3_bench_sandbox,
            home=LOGICAL_HOME,
            execute=False,
            operation_log=str(p3_bench_sandbox / "ops.jsonl"),
            command_argv=["clean", "--categories", "userCache"],
        )
        elapsed = time.perf_counter() - start
        assert elapsed < 2.0, f"UserCache dry-run took {elapsed:.3f}s"

    def test_delete_policy_creation_under_10ms(self, tmp_path: Path) -> None:
        start = time.perf_counter()
        for _ in range(10):
            delete_policy_for_context(root=tmp_path, home=LOGICAL_HOME)
        elapsed = (time.perf_counter() - start) / 10
        assert elapsed < 0.01, f"Policy creation took {elapsed:.4f}s per call"

    def test_rows_by_file_type_performance(self) -> None:
        from cleancli.core import rows_by_file_type

        rows = [{"path": f"/tmp/file_{i}.{i % 10}", "bytes": 100} for i in range(1000)]
        start = time.perf_counter()
        for _ in range(10):
            rows_by_file_type(rows)
        elapsed = (time.perf_counter() - start) / 10
        assert elapsed < 0.01, f"rows_by_file_type took {elapsed:.4f}s for 1000 rows"

    def test_rows_by_parent_directory_performance(self) -> None:
        from cleancli.core import rows_by_parent_directory

        rows = [{"parent": f"/tmp/dir_{i % 20}", "bytes": 100} for i in range(1000)]
        start = time.perf_counter()
        for _ in range(10):
            rows_by_parent_directory(rows)
        elapsed = (time.perf_counter() - start) / 10
        assert elapsed < 0.01, f"rows_by_parent_directory took {elapsed:.4f}s for 1000 rows"

    def test_multi_category_dry_run_under_5s(self, p3_bench_sandbox: Path) -> None:
        categories = [CATEGORY_BY_KEY[k] for k in ["trash", "userCache", "downloads"] if k in CATEGORY_BY_KEY]
        if not categories:
            pytest.skip("Not enough categories for multi-category test")
        start = time.perf_counter()
        clean(
            categories,
            root=p3_bench_sandbox,
            home=LOGICAL_HOME,
            execute=False,
            operation_log=str(p3_bench_sandbox / "ops.jsonl"),
            command_argv=["clean", "--categories", "trash,userCache,downloads"],
        )
        elapsed = time.perf_counter() - start
        assert elapsed < 5.0, f"Multi-category dry-run took {elapsed:.3f}s"

    def test_batch_log_append_performance(self, tmp_path: Path) -> None:
        from cleancli.core import batch_append_deletion_log

        entries = [
            {"mode": "trash", "bytes_value": i, "status": "deleted", "path": f"/tmp/file_{i}.txt", "detail": ""}
            for i in range(100)
        ]
        home = tmp_path / "Users" / "tester"
        home.mkdir(parents=True)
        start = time.perf_counter()
        batch_append_deletion_log(root=tmp_path, home=home, entries=entries)
        elapsed = time.perf_counter() - start
        assert elapsed < 0.1, f"Batch log append took {elapsed:.4f}s for 100 entries"
