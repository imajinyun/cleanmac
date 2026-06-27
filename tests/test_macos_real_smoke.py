from __future__ import annotations

import json
import os
import platform
from pathlib import Path

import pytest

from scripts.audit_bundle_drift import audit_bundle_drift
from tests.helpers import cleanmac_test_env, make_sandbox, run_cli

SKIP_REASON = "real macOS smoke requires a macOS runner"
pytestmark = pytest.mark.skipif(platform.system() != "Darwin", reason="real macOS smoke requires a macOS runner")


def test_real_macos_smoke_skip_reason_is_explicit_for_non_darwin_runners() -> None:
    assert SKIP_REASON == "real macOS smoke requires a macOS runner"
    assert pytestmark.kwargs["reason"] == SKIP_REASON


def test_real_macos_smoke_makefile_uses_temporary_venv_and_no_auth() -> None:
    makefile = Path("Makefile").read_text(encoding="utf-8")
    target = makefile.split("\nreal-macos-smoke:\n", 1)[1].split("\nsecurity-smoke:\n", 1)[0]

    expected_fragments = [
        "tmpdir=$$(mktemp -d)",
        'trap \'rm -rf "$$tmpdir"',
        "EXIT",
        '$(PYTHON) -m venv "$$tmpdir/venv"',
        '"$$tmpdir/venv/bin/python" -m pip install --upgrade pip',
        "\"$$tmpdir/venv/bin/python\" -m pip install -e '.[test]'",
        "CLEANMAC_TEST_MODE=1 CLEANMAC_TEST_NO_AUTH=1 PYTHONDONTWRITEBYTECODE=1",
        'PYTEST_ADDOPTS="-p no:cacheprovider"',
        '"$$tmpdir/venv/bin/python" -m pytest tests/test_macos_real_smoke.py -q',
    ]
    cursor = -1
    for fragment in expected_fragments:
        index = target.find(fragment, cursor + 1)
        assert index > cursor, fragment
        cursor = index

    assert ".venv/bin/python -m pytest tests/test_macos_real_smoke.py" not in target


def test_real_macos_readonly_bundle_audit_emits_schema() -> None:
    report = audit_bundle_drift()

    assert report["schema"] == "cleanmac.bundle-drift-audit.v1"
    assert not report["destructive"]
    assert "/System/Applications" in report["system_roots"]
    assert ".appex" in report["bundle_suffixes"]
    assert isinstance(report["system_bundles"], list)
    assert isinstance(report["uncovered_system_bundles"], list)


def test_real_macos_cli_capabilities_software_and_doctor_are_readonly() -> None:
    capabilities = json.loads(run_cli("--json", "capabilities").stdout)
    software = json.loads(run_cli("--json", "software", "list").stdout)
    with cleanmac_test_env():
        doctor = json.loads(run_cli("--json", "doctor").stdout)

    assert capabilities["schema"] == "cleanmac.capabilities.v1"
    assert not capabilities["destructive"]
    assert software["schema"] == "cleanmac.software.v1"
    assert not software["destructive"]
    assert doctor["schema"] == "cleanmac.doctor.v1"
    assert not doctor["destructive"]


def test_real_macos_trash_mode_routes_sandbox_candidate_to_test_trash(tmp_path: Path) -> None:
    tmp, root, home = make_sandbox()
    with tmp, cleanmac_test_env():
        trash_dir = tmp_path / "Trash"
        os.environ["CLEANMAC_TEST_TRASH_DIR"] = str(trash_dir)
        report = json.loads(
            run_cli(
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
            ).stdout
        )

        deleted = [row for row in report["items"] if str(row["path"]).endswith("download.bin")]
        assert len(deleted) == 1
        assert deleted[0]["deleted"]
        trash_path = Path(deleted[0]["trash_path"]).resolve()
        assert str(trash_path).startswith(str(trash_dir.resolve()))
        assert trash_dir.exists()
