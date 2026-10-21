"""Virtualization cache categories (Mole clean_virtualization_tools parity).

Covers UTM (app cache, sandboxed container cache, and container tmp with a
running-process guard), the VirtualBox ``.cache`` leaf, Lima downloaded OS
image blobs, and Vagrant package extraction temp files. Virtual machine
bundles, disk images, instances, boxes, and configuration must never become
candidates. Tart is covered as an owner-command tool adapter in
``test_tool_governance`` rather than as a path category.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from unittest.mock import patch

from cleancli import core
from cleancli.protection_data import APP_CLEANUP_RULES
from tests.helpers import make_sandbox, run_cli

CATEGORIES = "utm,virtualbox,lima,vagrant"

# Cache leaf (a marker file inside a declared cache root) -> owning category.
CACHE_FIXTURES: dict[str, str] = {
    # UTM: app cache plus both sandboxed container locations.
    "Library/Caches/com.utmapp.UTM/CloudCache/blob": "utm",
    "Library/Containers/com.utmapp.UTM/Data/Library/Caches/WebCache/blob": "utm",
    "Library/Containers/com.utmapp.UTM/Data/tmp/scratch/blob": "utm",
    # VirtualBox: only the hidden .cache leaf beside the VM folder.
    "VirtualBox VMs/.cache/extracted/blob": "virtualbox",
    # Lima: downloaded OS image blobs keyed by URL hash.
    "Library/Caches/lima/download/by-url-sha256/abcdef/images/disk": "lima",
    # Vagrant: package extraction tempdir only.
    ".vagrant.d/tmp/extract/package": "vagrant",
}

# Marker files that make their enclosing cache candidate protected.
PROTECTED_DESCENDANTS: dict[str, str] = {
    "Library/Caches/com.utmapp.UTM/dir/disk.qcow2": "utm",
    "Library/Containers/com.utmapp.UTM/Data/Library/Caches/dir/VM.utm/config": "utm",
    "VirtualBox VMs/.cache/dir/vm.vdi": "virtualbox",
    "Library/Caches/lima/download/by-url-sha256/1234/conf.yaml": "lima",
    ".vagrant.d/tmp/dir/package.box": "vagrant",
}

# VM state and configuration that lives outside the declared cache leaves and
# must therefore never appear as a candidate.
NEVER_CANDIDATE_PATHS = (
    "Library/Containers/com.utmapp.UTM/Data/Documents/VM.utm/config",
    "Library/Containers/com.utmapp.UTM/Data/Documents/disk.qcow2",
    "VirtualBox VMs/Default VM/Default VM.vbox",
    "VirtualBox VMs/Default VM/Default VM.vdi",
    "Library/Caches/lima/instances/default/basedisk",
    "Library/Caches/lima/_config/settings.yaml",
    ".vagrant.d/boxes/ubuntu/virtualbox/box.ovf",
    ".vagrant.d/data/machine-index/index",
    ".vagrant.d/Vagrantfile",
)


def _write(root: Path, relative: str) -> Path:
    path = root / "Users/tester" / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("x", encoding="utf-8")
    return path


def _inspect(root: Path) -> list[dict[str, object]]:
    result = run_cli(
        "--root",
        str(root),
        "--home",
        "/Users/tester",
        "--json",
        "clean",
        "inspect",
        "--categories",
        CATEGORIES,
    )
    report = json.loads(result.stdout)
    return [row for row in report["items"] if isinstance(row, dict)]


def _inspect_report(root: Path) -> dict[str, Any]:
    result = run_cli(
        "--root",
        str(root),
        "--home",
        "/Users/tester",
        "--json",
        "clean",
        "inspect",
        "--categories",
        CATEGORIES,
    )
    return json.loads(result.stdout)


def test_virtualization_cache_leaves_are_discovered() -> None:
    tmp, root, _home = make_sandbox()
    with tmp:
        for relative in CACHE_FIXTURES:
            _write(root, relative)

        rows = _inspect(root)
        rows_by_category: dict[str, list[dict[str, object]]] = {}
        for row in rows:
            rows_by_category.setdefault(str(row["category"]), []).append(row)
            assert row["default_selected"] is True
            assert row.get("skip_reason") is None
            assert row["risk"] in {"medium", "high"}

        assert set(rows_by_category) == {"utm", "virtualbox", "lima", "vagrant"}
        user_root = str(root / "Users/tester")
        for relative, category in CACHE_FIXTURES.items():
            fixture_abs = f"{user_root}/{relative}"
            assert any(
                fixture_abs == str(row["path"]) or fixture_abs.startswith(str(row["path"]) + "/")
                for row in rows_by_category[category]
            ), f"{relative} not reachable from {category} candidates"
        # UTM alone contributes three cache roots.
        assert len(rows_by_category["utm"]) == 3


def test_protected_vm_artifacts_skip_their_cache_candidate() -> None:
    tmp, root, _home = make_sandbox()
    with tmp:
        for relative in PROTECTED_DESCENDANTS:
            _write(root, relative)

        report = _inspect_report(root)
        assert report["items"] == []
        by_reason = report["skipped_summary"]["by_reason"]
        assert by_reason == {"app-protected-data": len(PROTECTED_DESCENDANTS)}
        skipped_categories = {row["category"] for row in report["skipped"]}
        assert skipped_categories == {"utm", "virtualbox", "lima", "vagrant"}


def test_vm_state_and_configuration_siblings_never_become_candidates() -> None:
    tmp, root, _home = make_sandbox()
    with tmp:
        for relative in NEVER_CANDIDATE_PATHS:
            _write(root, relative)

        assert _inspect(root) == []


def test_rules_target_exact_cache_leaves() -> None:
    forbidden_roots = {
        "~/Library/Containers/com.utmapp.UTM/",
        "~/Library/Containers/com.utmapp.UTM/Data/",
        "~/VirtualBox VMs/",
        "~/Library/Caches/lima/",
        "~/.vagrant.d/",
    }
    for key in ("utm", "virtualbox", "lima", "vagrant"):
        rule = APP_CLEANUP_RULES[key]
        paths = rule["paths"]
        assert paths and all(path.startswith("~/") for path in paths)
        assert not forbidden_roots.intersection(paths)
        assert rule["protected_patterns"]
    assert "*/Containers/com.utmapp.UTM/Data/Documents/*" in APP_CLEANUP_RULES["utm"]["protected_patterns"]
    assert "*.vdi" in APP_CLEANUP_RULES["virtualbox"]["protected_patterns"]
    assert "*.box" in APP_CLEANUP_RULES["vagrant"]["protected_patterns"]


def test_categories_are_registered_with_expected_risk_and_guards() -> None:
    for key in ("utm", "virtualbox", "lima", "vagrant"):
        category = core.CATEGORY_BY_KEY[key]
        assert category.advanced is True
        assert category.default is False
        assert category.recommended is False

    assert core.CATEGORY_BY_KEY["utm"].risk == "high"
    assert core.CATEGORY_BY_KEY["utm"].process_guard == "UTM"
    assert core.CATEGORY_BY_KEY["virtualbox"].risk == "high"
    assert core.CATEGORY_BY_KEY["virtualbox"].process_guard == "VirtualBox"
    assert core.CATEGORY_BY_KEY["lima"].risk == "medium"
    assert core.CATEGORY_BY_KEY["lima"].process_guard is None
    assert core.CATEGORY_BY_KEY["vagrant"].risk == "medium"
    assert core.CATEGORY_BY_KEY["vagrant"].process_guard is None


def test_utm_cache_is_skipped_while_utm_runs(tmp_path: Path) -> None:
    # One cache child under each of UTM's three roots.
    for relative in (
        "Library/Caches/com.utmapp.UTM/CloudCache/blob",
        "Library/Containers/com.utmapp.UTM/Data/Library/Caches/WebCache/blob",
        "Library/Containers/com.utmapp.UTM/Data/tmp/scratch/blob",
    ):
        path = tmp_path / "Users/tester" / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b"x")
    with (
        patch.object(core, "run_text_command", return_value="UTM"),
        patch.object(core, "is_test_no_auth", return_value=False),
    ):
        report = core.inspect_items([core.CATEGORY_BY_KEY["utm"]], root=tmp_path, home=Path("/Users/tester"), limit=-1)
    assert report["items"] == []
    assert report["skipped_summary"]["by_reason"] == {"app-running": 3}
    assert all(row["application"] == "UTM" for row in report["skipped"])
