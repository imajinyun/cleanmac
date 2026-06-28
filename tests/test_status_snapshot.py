from __future__ import annotations

from pathlib import Path

import pytest

from cleancli.core import _get_battery_info, _get_cpu_info, _get_memory_info, _get_uptime, render_status_snapshot


def test_status_snapshot_schema(tmp_path: Path):
    result = render_status_snapshot(root=tmp_path)
    assert result["schema"] == "cleanmac.status.snapshot.v1"
    assert result["destructive"] is False
    assert "timestamp" in result


def test_status_snapshot_has_disk(tmp_path: Path):
    result = render_status_snapshot(root=tmp_path)
    disk = result["disk"]
    assert "total_bytes" in disk
    assert "used_bytes" in disk
    assert "free_bytes" in disk
    assert "total_human" in disk
    assert "used_percent" in disk
    assert disk["total_bytes"] > 0
    assert 0 <= disk["used_percent"] <= 100


def test_status_snapshot_has_load_average(tmp_path: Path):
    result = render_status_snapshot(root=tmp_path)
    load = result["load_average"]
    assert "1m" in load
    assert "5m" in load
    assert "15m" in load


def test_status_snapshot_metrics_available_includes_disk_and_load(tmp_path: Path):
    result = render_status_snapshot(root=tmp_path)
    available = result["metrics_available"]
    assert "disk" in available
    assert "load_average" in available


def test_status_snapshot_metrics_deferred(tmp_path: Path):
    result = render_status_snapshot(root=tmp_path)
    deferred = result["metrics_deferred"]
    assert "gpu" in deferred
    assert "network" in deferred
    assert "temperature" in deferred
    assert "fan" in deferred
    assert "processes" in deferred


def test_memory_info_returns_none_when_sysctl_fails(monkeypatch: pytest.MonkeyPatch):
    import subprocess

    def bad_run(args, **kwargs):
        return subprocess.CompletedProcess(args=args, returncode=1, stdout="", stderr="error")

    monkeypatch.setattr(subprocess, "run", bad_run)
    assert _get_memory_info() is None


def test_cpu_info_graceful_degradation(monkeypatch: pytest.MonkeyPatch):
    import subprocess

    def bad_run(args, **kwargs):
        raise ValueError("simulated failure")

    monkeypatch.setattr(subprocess, "run", bad_run)
    assert _get_cpu_info() is None


def test_battery_info_graceful_degradation(monkeypatch: pytest.MonkeyPatch):
    import subprocess

    def bad_run(args, **kwargs):
        return subprocess.CompletedProcess(args=args, returncode=1, stdout="", stderr="error")

    monkeypatch.setattr(subprocess, "run", bad_run)
    assert _get_battery_info() is None


def test_uptime_graceful_degradation(monkeypatch: pytest.MonkeyPatch):
    import subprocess

    def bad_run(args, **kwargs):
        return subprocess.CompletedProcess(args=args, returncode=1, stdout="", stderr="error")

    monkeypatch.setattr(subprocess, "run", bad_run)
    assert _get_uptime() is None


def test_memory_info_structure():
    info = _get_memory_info()
    if info is None:
        pytest.skip("memory info not available on this platform")
    assert "total_bytes" in info
    assert "free_bytes" in info
    assert "active_bytes" in info
    assert "inactive_bytes" in info
    assert "wired_bytes" in info
    assert "used_percent" in info


def test_cpu_info_structure():
    info = _get_cpu_info()
    if info is None:
        pytest.skip("CPU info not available on this platform")
    assert "brand" in info
    assert "physical_cores" in info
    assert "logical_cores" in info


def test_battery_info_structure():
    info = _get_battery_info()
    if info is None:
        pytest.skip("battery info not available on this platform (desktop Mac)")
    assert "percent" in info
    assert "status" in info
    assert "time_remaining" in info
    assert "raw" in info


def test_uptime_structure():
    info = _get_uptime()
    if info is None:
        pytest.skip("uptime not available on this platform")
    assert isinstance(info, str)
    assert len(info) > 0


def test_status_snapshot_root_nonexistent(tmp_path: Path):
    nonexistent = tmp_path / "does_not_exist"
    result = render_status_snapshot(root=nonexistent)
    assert result["schema"] == "cleanmac.status.snapshot.v1"
    assert result["disk"]["total_bytes"] > 0


def test_status_snapshot_used_percent_valid(tmp_path: Path):
    result = render_status_snapshot(root=tmp_path)
    pct = result["disk"]["used_percent"]
    assert isinstance(pct, float)
    assert 0 <= pct <= 100


def test_status_snapshot_has_memory_when_available(tmp_path: Path):
    result = render_status_snapshot(root=tmp_path)
    if "memory" in result["metrics_available"]:
        assert result["memory"] is not None
        assert isinstance(result["memory"], dict)
    else:
        assert result["memory"] is None
