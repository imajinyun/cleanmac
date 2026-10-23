"""Read-only Time Machine local snapshot inspection tests."""

from __future__ import annotations

import json
from collections.abc import Sequence

import pytest

from cleancli import time_machine
from cleancli.ai_versioning import validate_contract_payload
from tests.helpers import make_sandbox, run_cli


@pytest.fixture
def tmutil_available(monkeypatch: pytest.MonkeyPatch) -> None:
    # These tests drive the full tmutil sequence through an injected FakeRunner,
    # so the host need not provide tmutil (keeps the logic covered on Linux CI).
    monkeypatch.setattr(time_machine.shutil, "which", lambda name: "/usr/bin/tmutil")


class FakeRunner:
    """Scripted host command runner; records invocations."""

    def __init__(self, responses: dict[tuple[str, ...], time_machine.HostCommandResult | None]):
        self.responses = responses
        self.calls: list[list[str]] = []

    def __call__(self, argv: Sequence[str], timeout: float) -> time_machine.HostCommandResult | None:
        args = list(argv)
        self.calls.append(args)
        return self.responses.get(tuple(args))


def _result(stdout: str = "", returncode: int = 0) -> time_machine.HostCommandResult:
    return time_machine.HostCommandResult(returncode=returncode, stdout=stdout)


def test_parse_auto_backup() -> None:
    assert time_machine.parse_auto_backup("1\n") is True
    assert time_machine.parse_auto_backup("0") is False
    assert time_machine.parse_auto_backup("") is None
    assert time_machine.parse_auto_backup(None) is None
    assert time_machine.parse_auto_backup("unexpected") is None


def test_parse_backup_state() -> None:
    assert time_machine.parse_backup_state("{\n Running = 1;\n}") == "running"
    assert time_machine.parse_backup_state("Running = 0;") == "idle"
    assert time_machine.parse_backup_state("") == "unknown"
    assert time_machine.parse_backup_state(None) == "unknown"
    assert time_machine.parse_backup_state("{ DestinationID = ...; }") == "unknown"


def test_parse_local_snapshots_extracts_name_date_and_keeps_occurrences() -> None:
    output = (
        "Snapshots for volume group containing disk:\n"
        "Snapshots for disk /:\n"
        "com.apple.TimeMachine.2026-10-19-080010.local\n"
        "com.apple.TimeMachine.2026-10-18-213045\n"
        "not-a-snapshot.txt\n"
    )

    snapshots = time_machine.parse_local_snapshots(output)

    assert [snapshot["name"] for snapshot in snapshots] == [
        "com.apple.TimeMachine.2026-10-19-080010.local",
        "com.apple.TimeMachine.2026-10-18-213045",
    ]
    assert snapshots[0]["date_token"] == "2026-10-19-080010"
    assert snapshots[0]["timestamp"] == "2026-10-19T08:00:10"
    assert time_machine.parse_local_snapshots("") == []
    assert time_machine.parse_local_snapshots(None) == []


def test_disabled_host_tools_skip_every_command() -> None:
    runner = FakeRunner({})
    report = time_machine.render_time_machine(host_tools_enabled=False, runner=runner)

    assert report["schema"] == "cleanmac.time-machine.v1"
    assert report["destructive"] is False
    assert report["read_only"] is True
    assert report["deletion_supported"] is False
    assert report["enumeration_status"] == "skipped-host-tools-disabled"
    assert report["snapshots"] == []
    assert report["snapshot_count"] == 0
    assert runner.calls == []


def test_missing_tmutil_is_reported_without_command_calls(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(time_machine.shutil, "which", lambda name: None)
    runner = FakeRunner({})

    report = time_machine.render_time_machine(runner=runner)

    assert report["enumeration_status"] == "skipped-tmutil-unavailable"
    assert report["host_tools"]["tmutil_available"] is False
    assert runner.calls == []


def test_unconfigured_time_machine_skips_tmutil_sequence(tmutil_available: None) -> None:
    runner = FakeRunner(
        {("defaults", "read", time_machine.AUTOBACKUP_DOMAIN, "AutoBackup"): _result(returncode=1)}
    )

    report = time_machine.render_time_machine(runner=runner)

    assert report["configured"] is False
    assert report["auto_backup"] is None
    assert report["enumeration_status"] == "skipped-not-configured"
    assert all(call[0] == "defaults" for call in runner.calls)


def test_backup_in_progress_blocks_enumeration(tmutil_available: None) -> None:
    runner = FakeRunner(
        {
            ("defaults", "read", time_machine.AUTOBACKUP_DOMAIN, "AutoBackup"): _result("1"),
            ("tmutil", "status"): _result("Running = 1;"),
        }
    )

    report = time_machine.render_time_machine(runner=runner)

    assert report["configured"] is True
    assert report["auto_backup"] is True
    assert report["backup_state"] == "running"
    assert report["enumeration_status"] == "skipped-backup-in-progress"
    assert all(call[0] != "tmutil" or call[1] == "status" for call in runner.calls)
    assert not any(call[:2] == ("tmutil", "listlocalsnapshots") for call in runner.calls)


def test_unknown_backup_state_fails_closed(tmutil_available: None) -> None:
    runner = FakeRunner(
        {
            ("defaults", "read", time_machine.AUTOBACKUP_DOMAIN, "AutoBackup"): _result("0"),
            ("tmutil", "status"): _result(returncode=2),
        }
    )

    report = time_machine.render_time_machine(runner=runner)

    assert report["backup_state"] == "unknown"
    assert report["enumeration_status"] == "skipped-status-unknown"
    assert report["snapshots"] == []
    assert not any(call[:2] == ("tmutil", "listlocalsnapshots") for call in runner.calls)


def test_idle_state_enumerates_snapshots(tmutil_available: None) -> None:
    listing = (
        "Snapshots for disk /:\n"
        "com.apple.TimeMachine.2026-10-19-080010.local\n"
        "com.apple.TimeMachine.2026-10-18-213045\n"
    )
    runner = FakeRunner(
        {
            ("defaults", "read", time_machine.AUTOBACKUP_DOMAIN, "AutoBackup"): _result("1"),
            ("tmutil", "status"): _result("Running = 0;"),
            ("tmutil", "listlocalsnapshots", "/"): _result(listing),
        }
    )

    report = time_machine.render_time_machine(mount="/", runner=runner)

    assert report["configured"] is True
    assert report["backup_state"] == "idle"
    assert report["enumeration_status"] == "enumerated"
    assert report["snapshot_count"] == 2
    assert report["manual_review_command"] == ["tmutil", "listlocalsnapshots", "/"]
    assert report["deletion_policy"]["snapshot_deletion_supported"] is False
    validation = validate_contract_payload("cleanmac.time-machine.v1", report)
    assert validation["valid"] is True, validation


def test_enumeration_command_failure_is_reported(tmutil_available: None) -> None:
    runner = FakeRunner(
        {
            ("defaults", "read", time_machine.AUTOBACKUP_DOMAIN, "AutoBackup"): _result("1"),
            ("tmutil", "status"): _result("Running = 0;"),
            ("tmutil", "listlocalsnapshots", "/"): None,
        }
    )

    report = time_machine.render_time_machine(runner=runner)

    assert report["enumeration_status"] == "enumeration-failed"
    assert report["snapshots"] == []


def test_default_runner_never_invokes_host_tools_in_test_mode(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CLEANMAC_TEST_MODE", "1")

    def fail_subprocess(*args: object, **kwargs: object) -> None:
        raise AssertionError("host subprocess must not run in test mode")

    monkeypatch.setattr(time_machine.subprocess, "run", fail_subprocess)

    report = time_machine.render_time_machine(host_tools_enabled=True)

    assert report["enumeration_status"] == "skipped-not-configured"
    assert report["host_tools"]["invoked_commands"] == []


def test_default_runner_never_invokes_host_tools_in_no_auth_mode(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("CLEANMAC_TEST_MODE", raising=False)
    monkeypatch.setenv("CLEANMAC_TEST_NO_AUTH", "1")

    def fail_subprocess(*args: object, **kwargs: object) -> None:
        raise AssertionError("host subprocess must not run in no-auth mode")

    monkeypatch.setattr(time_machine.subprocess, "run", fail_subprocess)

    report = time_machine.render_time_machine()

    assert report["enumeration_status"] == "skipped-not-configured"


def test_cli_sandbox_reports_disabled_host_tools_and_dry_run_contract() -> None:
    tmp, root, home = make_sandbox()
    with tmp:
        result = run_cli(
            "--root", str(root), "--home", str(home), "--json", "time-machine", "--mount", "/"
        )
        report = json.loads(result.stdout)

        assert report["schema"] == "cleanmac.time-machine.v1"
        assert report["destructive"] is False
        assert report["dry_run"] is True
        assert report["read_only"] is True
        assert report["deletion_supported"] is False
        assert report["enumeration_status"] == "skipped-host-tools-disabled"
        assert report["host_tools"]["enabled"] is False
        assert report["snapshot_count"] == 0
