from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from cleancli import delete_ops, unified_logs
from cleancli.ai_versioning import validate_contract_payload
from tests.helpers import cleanmac_test_env, make_sandbox, run_cli

LIVE_ROOT = Path("/")
ERASE_ARGV = ["sudo", "-n", "log", "erase", "--all"]


def _make_sandbox_stores(root: Path) -> tuple[Path, Path]:
    diagnostics = root / "private/var/db/diagnostics"
    uuidtext = root / "private/var/db/uuidtext"
    (diagnostics / "Persist").mkdir(parents=True)
    (uuidtext / "2A").mkdir(parents=True)
    (diagnostics / "Persist/001.tracev3").write_bytes(b"x" * 4096)
    (diagnostics / "timesync").write_bytes(b"y" * 1024)
    (uuidtext / "2A/ABC.UUID").write_bytes(b"z" * 512)
    return diagnostics, uuidtext


@pytest.fixture
def sandbox() -> Any:
    tmp, root, home = make_sandbox()
    _make_sandbox_stores(root)
    with tmp:
        yield root, home


# ---------------------------------------------------------------------------
# delete_ops primitive
# ---------------------------------------------------------------------------


def test_erase_command_constant_is_non_interactive_log_erase() -> None:
    assert list(delete_ops.SUDO_LOG_ERASE_COMMAND) == ERASE_ARGV
    assert "-n" in delete_ops.SUDO_LOG_ERASE_COMMAND


def test_erase_unified_logs_dry_run_runs_nothing_and_records_audit_hook() -> None:
    actions: list[tuple[str, Path, str]] = []

    result = delete_ops.erase_unified_logs(
        dry_run=True,
        operation_log=lambda action, target, detail: actions.append((action, target, detail)),
    )

    assert result.dry_run is True
    assert result.executed is False
    assert result.returncode is None
    assert list(result.command) == ERASE_ARGV
    assert len(actions) == 1
    action, target, detail = actions[0]
    assert action == "dry-run"
    assert target == Path("/private/var/db/diagnostics")
    assert "log erase --all" in detail


def test_erase_unified_logs_blocked_under_test_no_auth() -> None:
    actions: list[tuple[str, Path, str]] = []
    with cleanmac_test_env():
        with pytest.raises(RuntimeError, match="test/no-auth"):
            delete_ops.erase_unified_logs(
                dry_run=False,
                operation_log=lambda action, target, detail: actions.append((action, target, detail)),
            )
    assert actions and actions[0][0] == "failed"


# ---------------------------------------------------------------------------
# inspect / bounded accounting
# ---------------------------------------------------------------------------


def _lstat_total(path: Path) -> int:
    # Mirror bounded_store_size: rglob children (files and directories) and
    # sum lstat sizes without following symlinks.
    return sum(child.lstat().st_size for child in path.rglob("*") if child.exists() or child.is_symlink())


def test_inspect_counts_both_stores_under_sandbox(sandbox: Any) -> None:
    root, home = sandbox
    diagnostics = root / "private/var/db/diagnostics"
    uuidtext = root / "private/var/db/uuidtext"
    report = unified_logs.inspect_unified_logs(root=root, home=home)

    assert report["schema"] == "cleanmac.unified-logs-inspect.v1"
    assert report["destructive"] is False
    assert report["dry_run"] is True
    assert report["status"] == "read-only-inspect"
    assert report["live_root"] is False
    assert report["erased_together"] is True
    assert report["erase_method"] == "permanent"
    assert report["trash_routing"] is False
    assert report["erase_command"] == ERASE_ARGV
    by_name = {row["name"]: row for row in report["stores"]}
    assert set(by_name) == {"diagnostics", "uuidtext"}
    expected_diagnostics = _lstat_total(diagnostics)
    expected_uuidtext = _lstat_total(uuidtext)
    assert expected_diagnostics >= 4096 + 1024
    assert by_name["diagnostics"]["bytes"] == expected_diagnostics
    assert by_name["uuidtext"]["bytes"] == expected_uuidtext
    assert report["total_bytes"] == expected_diagnostics + expected_uuidtext
    assert report["warnings"]  # live-root warning on sandbox roots
    assert by_name["diagnostics"]["path"].startswith(str(root))


def test_inspect_missing_stores_report_zero(sandbox: Any) -> None:
    root, home = sandbox
    missing_root = root / "empty-machine"
    missing_root.mkdir()
    report = unified_logs.inspect_unified_logs(root=missing_root, home=home)
    assert report["total_bytes"] == 0
    assert all(not row["exists"] for row in report["stores"])


def test_store_size_walk_is_bounded(sandbox: Any) -> None:
    root, _home = sandbox
    size = unified_logs.bounded_store_size(
        "diagnostics",
        unified_logs.DIAGNOSTICS_REL,
        "note",
        root=root,
        max_entries=1,
    )
    assert size.truncated is True
    assert size.entries_scanned <= 1


# ---------------------------------------------------------------------------
# erase plan + gates
# ---------------------------------------------------------------------------


def test_erase_defaults_to_dry_run_plan(sandbox: Any) -> None:
    root, home = sandbox
    report = unified_logs.run_erase(root=root, home=home)

    assert report["schema"] == "cleanmac.unified-logs-erase-plan.v1"
    assert report["status"] == "dry-run"
    assert report["destructive"] is True
    assert report["dry_run"] is True
    assert report["safe_to_execute_after_confirmation"] is False
    assert report["required_flags"] == ["--execute", "--yes", "--confirm-permanent-erase"]
    assert report["trash_routing"] is False
    assert any("irreversible" in note for note in report["disclosures"])
    # Sandbox roots cannot reclaim anything.
    assert report["estimated_reclaimable_bytes"] == 0


def test_execute_refuses_sandbox_root_and_never_invokes_runner(sandbox: Any) -> None:
    root, home = sandbox
    invoked = []

    def runner(**_kwargs: Any) -> Any:
        invoked.append(True)
        raise AssertionError("runner must not be invoked for sandbox roots")

    report = unified_logs.run_erase(
        root=root,
        home=home,
        execute=True,
        confirmed=True,
        permanent_confirmed=True,
        sudo_available=True,
        erase_runner=runner,
    )

    assert report["schema"] == "cleanmac.unified-logs-erase-result.v1"
    assert report["status"] == "refused"
    assert report["executed"] is False
    assert report["error_code"] == "SANDBOX_ROOT_UNSUPPORTED"
    assert report["reclaimed_bytes"] == 0
    assert not invoked


def test_execute_requires_both_confirmation_flags() -> None:
    missing_yes = unified_logs.run_erase(root=LIVE_ROOT, execute=True, confirmed=False, permanent_confirmed=True)
    assert missing_yes["status"] == "refused"
    assert missing_yes["error_code"] == "CONFIRMATION_REQUIRED"
    assert "--yes" in missing_yes["error"]

    missing_permanent = unified_logs.run_erase(root=LIVE_ROOT, execute=True, confirmed=True, permanent_confirmed=False)
    assert missing_permanent["status"] == "refused"
    assert missing_permanent["error_code"] == "CONFIRMATION_REQUIRED"
    assert "--confirm-permanent-erase" in missing_permanent["error"]


def test_execute_requires_sudo_preflight() -> None:
    report = unified_logs.run_erase(
        root=LIVE_ROOT,
        execute=True,
        confirmed=True,
        permanent_confirmed=True,
        sudo_available=False,
    )
    assert report["status"] == "refused"
    assert report["error_code"] == "SUDO_PREFLIGHT_FAILED"


def test_successful_erase_reports_reclaimed_bytes_and_forwards_hook() -> None:
    hooks: list[tuple[str, Path, str]] = []

    class FakeOutcome:
        command = tuple(ERASE_ARGV)
        dry_run = False
        returncode = 0
        stdout = "Log Erasing successful"
        stderr = ""

    def runner(**kwargs: Any) -> FakeOutcome:
        assert kwargs["dry_run"] is False
        hook = kwargs["operation_log"]
        hook("deleted", Path("/private/var/db/diagnostics"), "sudo log erase --all")
        return FakeOutcome()

    report = unified_logs.run_erase(
        root=LIVE_ROOT,
        execute=True,
        confirmed=True,
        permanent_confirmed=True,
        sudo_available=True,
        operation_log=lambda action, target, detail: hooks.append((action, target, detail)),
        erase_runner=runner,
    )

    assert report["status"] == "executed"
    assert report["executed"] is True
    assert report["error"] is None
    assert report["returncode"] == 0
    assert report["command"] == ERASE_ARGV
    assert report["erase_method"] == "permanent"
    assert report["trash_routing"] is False
    assert isinstance(report["reclaimed_bytes"], int)
    assert "stores_before" in report and "stores_after" in report
    assert hooks == [("deleted", Path("/private/var/db/diagnostics"), "sudo log erase --all")]


def test_runner_failure_is_fail_closed_result() -> None:
    def runner(**_kwargs: Any) -> Any:
        raise RuntimeError("Failed to erase unified logs: auth required")

    report = unified_logs.run_erase(
        root=LIVE_ROOT,
        execute=True,
        confirmed=True,
        permanent_confirmed=True,
        sudo_available=True,
        erase_runner=runner,
    )
    assert report["status"] == "failed"
    assert report["executed"] is False
    assert report["error_code"] == "ERASE_FAILED"
    assert "auth required" in report["error"]
    assert report["reclaimed_bytes"] == 0


# ---------------------------------------------------------------------------
# CLI surface
# ---------------------------------------------------------------------------


def test_cli_system_logs_inspect_and_erase_dry_run(sandbox: Any) -> None:
    root, home = sandbox
    with cleanmac_test_env():
        inspect_report = json.loads(
            run_cli("--root", str(root), "--home", str(home), "--json", "system-logs", "inspect").stdout
        )
        plan_report = json.loads(
            run_cli("--root", str(root), "--home", str(home), "--json", "system-logs", "erase").stdout
        )

    assert inspect_report["schema"] == "cleanmac.unified-logs-inspect.v1"
    expected_total = _lstat_total(root / "private/var/db/diagnostics") + _lstat_total(
        root / "private/var/db/uuidtext"
    )
    assert inspect_report["total_bytes"] == expected_total
    assert plan_report["schema"] == "cleanmac.unified-logs-erase-plan.v1"
    assert plan_report["status"] == "dry-run"


def test_cli_system_logs_execute_refuses_sandbox_without_deleting(sandbox: Any) -> None:
    root, home = sandbox
    diag_file = root / "private/var/db/diagnostics/Persist/001.tracev3"
    with cleanmac_test_env():
        result = run_cli(
            "--root",
            str(root),
            "--home",
            str(home),
            "--json",
            "system-logs",
            "erase",
            "--execute",
            "--yes",
            "--confirm-permanent-erase",
        )
    report = json.loads(result.stdout)
    assert report["status"] == "refused"
    assert report["error_code"] == "SANDBOX_ROOT_UNSUPPORTED"
    assert diag_file.exists()  # nothing was removed


def test_cli_system_logs_live_execute_blocked_by_test_mode_sudo_preflight() -> None:
    tmp, root, home = make_sandbox()
    with tmp, cleanmac_test_env():
        operation_log = Path(tmp.name) / "operations.jsonl"
        result = run_cli(
            "--json",
            "system-logs",
            "erase",
            "--execute",
            "--yes",
            "--confirm-permanent-erase",
            "--operation-log",
            str(operation_log),
        )
        report = json.loads(result.stdout)
        assert report["status"] == "refused"
        assert report["error_code"] == "SUDO_PREFLIGHT_FAILED"
        # Refusals before the primitive must not emit audit entries.
        assert not operation_log.exists() or operation_log.read_text(encoding="utf-8") == ""


def test_cli_system_logs_is_listed_in_capabilities() -> None:
    with cleanmac_test_env():
        report = json.loads(run_cli("--json", "capabilities").stdout)
    assert "system-logs" in report["commands"]
    assert report["command_groups"]["system-logs"]["commands"] == ["system-logs inspect", "system-logs erase"]


# ---------------------------------------------------------------------------
# contract validation
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "report",
    [
        unified_logs.inspect_unified_logs(root=Path("/nonexistent-unified-logs-root")),
        unified_logs.run_erase(root=Path("/nonexistent-unified-logs-root")),
        unified_logs.run_erase(root=LIVE_ROOT, execute=True, confirmed=False, permanent_confirmed=False),
    ],
)
def test_reports_validate_against_registered_contracts(report: dict[str, Any]) -> None:
    validation = validate_contract_payload(str(report["schema"]), report)
    assert validation["valid"] is True, validation["errors"]
