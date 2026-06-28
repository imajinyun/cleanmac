from __future__ import annotations

import subprocess

import pytest

from cleancli.optimize import (
    OPTIMIZE_TASKS,
    execute_optimize_tasks,
    list_optimize_tasks,
    render_optimize_human,
)


def test_optimize_task_count():
    assert len(OPTIMIZE_TASKS) == 10


def test_optimize_tasks_have_required_fields():
    for task in OPTIMIZE_TASKS:
        assert "key" in task
        assert "title" in task
        assert "description" in task
        assert "command" in task
        assert "requires_privilege" in task
        assert "destructive" in task
        assert "category" in task


def test_optimize_tasks_keys_are_unique():
    keys = [t["key"] for t in OPTIMIZE_TASKS]
    assert len(keys) == len(set(keys))


def test_optimize_tasks_none_are_destructive():
    for task in OPTIMIZE_TASKS:
        assert not task["destructive"], f"{task['key']} should not be destructive"


def test_list_optimize_tasks_returns_copy():
    tasks1 = list_optimize_tasks()
    tasks2 = list_optimize_tasks()
    tasks1[0]["key"] = "mutated"
    assert tasks2[0]["key"] != "mutated"


def test_execute_dry_run_defaults():
    result = execute_optimize_tasks(action="plan", execute=False)
    assert result["schema"] == "cleanmac.optimize.v1"
    assert result["action"] == "plan"
    assert result["dry_run"] is True
    assert result["execute_requested"] is False
    assert result["total_tasks"] == 10
    assert result["skipped_count"] == 10
    assert result["success_count"] == 0
    assert result["failed_count"] == 0


def test_execute_dry_run_all_status_dry_run():
    result = execute_optimize_tasks(action="plan", execute=False)
    for task in result["tasks"]:
        assert task["status"] == "dry-run"


def test_execute_test_mode_blocks_execution():
    result = execute_optimize_tasks(
        action="run",
        execute=True,
        test_mode=True,
        sudo_available=True,
    )
    assert result["execute_requested"] is True
    for task in result["tasks"]:
        assert task["status"] == "skipped"
        assert task["output"] == "[test-mode] command not executed"


def test_execute_privilege_tasks_blocked_without_sudo():
    result = execute_optimize_tasks(
        action="run",
        execute=True,
        test_mode=False,
        sudo_available=False,
    )

    for task in result["tasks"]:
        if task["requires_privilege"]:
            assert task["status"] == "blocked"
            assert "sudo" in task["error"]


def test_execute_non_privilege_tasks_run_without_sudo(monkeypatch: pytest.MonkeyPatch):
    called_commands: list[str] = []

    def fake_run(args, **kwargs):
        called_commands.append(" ".join(args) if isinstance(args, list) else args)
        return subprocess.CompletedProcess(args=args, returncode=0, stdout="ok", stderr="")

    monkeypatch.setattr(subprocess, "run", fake_run)

    result = execute_optimize_tasks(
        action="run",
        execute=True,
        test_mode=False,
        sudo_available=False,
    )

    non_privilege = [t for t in result["tasks"] if not t["requires_privilege"]]
    for task in non_privilege:
        assert task["status"] == "success"

    privilege = [t for t in result["tasks"] if t["requires_privilege"]]
    for task in privilege:
        assert task["status"] == "blocked"


def test_execute_with_sudo_runs_all_tasks(monkeypatch: pytest.MonkeyPatch):
    def fake_run(args, **kwargs):
        return subprocess.CompletedProcess(args=args, returncode=0, stdout="ok", stderr="")

    monkeypatch.setattr(subprocess, "run", fake_run)

    result = execute_optimize_tasks(
        action="run",
        execute=True,
        test_mode=False,
        sudo_available=True,
    )

    assert result["success_count"] == 10
    assert result["failed_count"] == 0


def test_execute_failed_task(monkeypatch: pytest.MonkeyPatch):
    def fake_run(args, **kwargs):
        return subprocess.CompletedProcess(args=args, returncode=1, stdout="", stderr="error msg")

    monkeypatch.setattr(subprocess, "run", fake_run)

    result = execute_optimize_tasks(
        action="run",
        execute=True,
        test_mode=False,
        sudo_available=True,
    )

    assert result["failed_count"] == 10
    for task in result["tasks"]:
        assert task["status"] == "failed"
        assert task["error"] is not None


def test_execute_command_timeout(monkeypatch: pytest.MonkeyPatch):
    def fake_run(args, **kwargs):
        raise subprocess.TimeoutExpired(cmd=args, timeout=60)

    monkeypatch.setattr(subprocess, "run", fake_run)

    result = execute_optimize_tasks(
        action="run",
        execute=True,
        test_mode=False,
        sudo_available=True,
    )

    for task in result["tasks"]:
        assert task["status"] == "failed"
        assert "timed out" in task["error"]


def test_execute_command_not_found(monkeypatch: pytest.MonkeyPatch):
    def fake_run(args, **kwargs):
        raise FileNotFoundError("cmd not found")

    monkeypatch.setattr(subprocess, "run", fake_run)

    result = execute_optimize_tasks(
        action="run",
        execute=True,
        test_mode=False,
        sudo_available=True,
    )

    for task in result["tasks"]:
        assert task["status"] == "failed"
        assert "command not found" in task["error"]


def test_task_filter():
    result = execute_optimize_tasks(
        action="plan",
        execute=False,
        task_filter={"quicklook-cache", "finder-restart"},
    )
    assert result["total_tasks"] == 2
    keys = {t["key"] for t in result["tasks"]}
    assert keys == {"quicklook-cache", "finder-restart"}


def test_task_filter_empty():
    result = execute_optimize_tasks(
        action="plan",
        execute=False,
        task_filter=set(),
    )
    assert result["total_tasks"] == 0


def test_render_optimize_human_dry_run():
    result = execute_optimize_tasks(action="plan", execute=False)
    output = render_optimize_human(result)
    assert "System Optimization" in output
    assert "Mode: dry-run" in output
    assert "Quick Look" in output
    assert "Run with --execute --yes" in output


def test_render_optimize_human_execute(monkeypatch: pytest.MonkeyPatch):
    def fake_run(args, **kwargs):
        return subprocess.CompletedProcess(args=args, returncode=0, stdout="ok", stderr="")

    monkeypatch.setattr(subprocess, "run", fake_run)

    result = execute_optimize_tasks(
        action="run",
        execute=True,
        test_mode=False,
        sudo_available=True,
    )
    output = render_optimize_human(result)
    assert "Mode: execute" in output
    assert "Success: 10" in output
    assert "✓" in output


def test_render_optimize_human_with_errors(monkeypatch: pytest.MonkeyPatch):
    def fake_run(args, **kwargs):
        return subprocess.CompletedProcess(args=args, returncode=1, stdout="", stderr="something broke")

    monkeypatch.setattr(subprocess, "run", fake_run)

    result = execute_optimize_tasks(
        action="run",
        execute=True,
        test_mode=False,
        sudo_available=True,
        task_filter={"quicklook-cache"},
    )
    output = render_optimize_human(result)
    assert "✗" in output
    assert "Error:" in output


def test_render_optimize_human_empty():
    result = execute_optimize_tasks(
        action="plan",
        execute=False,
        task_filter=set(),
    )
    output = render_optimize_human(result)
    assert "No optimize tasks configured" in output


def test_privilege_tasks_are_known():
    privilege_keys = {t["key"] for t in OPTIMIZE_TASKS if t["requires_privilege"]}
    expected = {"spotlight-reindex", "dns-cache-flush", "kernel-cache-update"}
    assert privilege_keys == expected


def test_categories_are_known():
    categories = {t["category"] for t in OPTIMIZE_TASKS}
    expected = {"caches", "indexes", "services", "logs", "network"}
    assert categories == expected


def test_execute_is_not_destructive():
    result = execute_optimize_tasks(action="run", execute=True)
    assert result["destructive"] is False
