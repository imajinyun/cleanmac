from __future__ import annotations

import io
import json
import subprocess
from contextlib import redirect_stdout

import pytest

from cleancli.core import VERSION, main


def _capture_main(*argv: str) -> tuple[int, str]:
    buf = io.StringIO()
    with redirect_stdout(buf):
        code = main(list(argv))
    return code, buf.getvalue()


def test_update_dry_run_json():
    code, out = _capture_main("--json", "update", "--dry-run")
    assert code == 0
    data = json.loads(out)
    assert data["schema"] == "cleanmac.update.v1"
    assert data["dry_run"] is True
    assert data["status"] == "checking"
    assert "current_version" in data
    assert "target_version" in data
    assert "package_spec" in data


def test_update_dry_run_human():
    code, out = _capture_main("update", "--dry-run")
    assert code == 0
    assert "Current version" in out
    assert "Target" in out
    assert "Run without --dry-run" in out


def test_update_dry_run_with_version_json():
    code, out = _capture_main("--json", "update", "--version", "2.0.0", "--dry-run")
    assert code == 0
    data = json.loads(out)
    assert data["target_version"] == "2.0.0"
    assert data["package_spec"] == "cleanmac==2.0.0"


def test_update_execute_success(monkeypatch: pytest.MonkeyPatch):
    called: list[list[str]] = []

    def fake_run(args, **kwargs):
        called.append(list(args) if isinstance(args, list) else [args])
        if len(args) >= 3 and args[2] == "pip":
            return subprocess.CompletedProcess(args=args, returncode=0, stdout="Successfully installed", stderr="")
        return subprocess.CompletedProcess(args=args, returncode=0, stdout="1.0.0", stderr="")

    monkeypatch.setattr(subprocess, "run", fake_run)

    code, out = _capture_main("--json", "update")
    assert code == 0
    data = json.loads(out)
    assert data["schema"] == "cleanmac.update.v1"
    assert data["success"] is True

    pip_calls = [c for c in called if "pip" in c]
    assert len(pip_calls) >= 1


def test_update_execute_failure(monkeypatch: pytest.MonkeyPatch):
    def fake_run(args, **kwargs):
        if len(args) >= 3 and args[2] == "pip":
            return subprocess.CompletedProcess(args=args, returncode=1, stdout="", stderr="pip install failed")
        return subprocess.CompletedProcess(args=args, returncode=0, stdout="0.9.0", stderr="")

    monkeypatch.setattr(subprocess, "run", fake_run)

    code, out = _capture_main("--json", "update")
    assert code != 0
    data = json.loads(out)
    assert data["success"] is False
    assert data["error"] is not None


def test_update_execute_human_success(monkeypatch: pytest.MonkeyPatch):
    def fake_run(args, **kwargs):
        if len(args) >= 3 and args[2] == "pip":
            return subprocess.CompletedProcess(args=args, returncode=0, stdout="Successfully installed", stderr="")
        return subprocess.CompletedProcess(args=args, returncode=0, stdout="1.5.0", stderr="")

    monkeypatch.setattr(subprocess, "run", fake_run)

    code, out = _capture_main("update")
    assert code == 0
    assert "Updated cleanmac" in out


def test_update_with_pip_args(monkeypatch: pytest.MonkeyPatch):
    called: list[list[str]] = []

    def fake_run(args, **kwargs):
        called.append(list(args) if isinstance(args, list) else [args])
        if len(args) >= 3 and args[2] == "pip":
            return subprocess.CompletedProcess(args=args, returncode=0, stdout="ok", stderr="")
        return subprocess.CompletedProcess(args=args, returncode=0, stdout="1.0.0", stderr="")

    monkeypatch.setattr(subprocess, "run", fake_run)

    _capture_main("--json", "update", "--pip-args", "--user --quiet")

    pip_calls = [c for c in called if "pip" in c and "install" in c]
    assert len(pip_calls) == 1
    assert "--user" in pip_calls[0]
    assert "--quiet" in pip_calls[0]


def test_update_dry_run_is_not_executing():
    code, out = _capture_main("--json", "update", "--dry-run")
    data = json.loads(out)
    assert data["dry_run"] is True
    assert "success" not in data


def test_update_current_version_matches_module():
    code, out = _capture_main("--json", "update", "--dry-run")
    data = json.loads(out)
    assert data["current_version"] == VERSION


def test_update_dry_run_default_target_is_latest():
    code, out = _capture_main("--json", "update", "--dry-run")
    data = json.loads(out)
    assert data["target_version"] == "latest"
    assert data["package_spec"] == "cleanmac"


def test_update_execute_human_failure(monkeypatch: pytest.MonkeyPatch):
    def fake_run(args, **kwargs):
        if len(args) >= 3 and args[2] == "pip":
            return subprocess.CompletedProcess(args=args, returncode=1, stdout="", stderr="connection error")
        return subprocess.CompletedProcess(args=args, returncode=0, stdout="0.9.0", stderr="")

    monkeypatch.setattr(subprocess, "run", fake_run)

    code, out = _capture_main("update")
    assert code != 0
    assert "Update failed" in out


def test_update_version_check_after_install(monkeypatch: pytest.MonkeyPatch):

    called: list[list[str]] = []

    def fake_run(args, **kwargs):
        called.append(list(args) if isinstance(args, list) else [args])
        if len(args) >= 3 and args[2] == "pip":
            return subprocess.CompletedProcess(args=args, returncode=0, stdout="Successfully installed", stderr="")
        if "importlib.metadata" in " ".join(args):
            return subprocess.CompletedProcess(args=args, returncode=0, stdout="9.9.9", stderr="")
        return subprocess.CompletedProcess(args=args, returncode=0, stdout="", stderr="")

    monkeypatch.setattr(subprocess, "run", fake_run)

    code, out = _capture_main("--json", "update")
    assert code == 0
    data = json.loads(out)
    assert data["new_version"] == "9.9.9"
    assert data["current_version"] == VERSION
