from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
CLI = PROJECT_ROOT / "cleanmac.py"
TEST_ENV = {**os.environ, "CLEANMAC_TEST_MODE": "1", "CLEANMAC_TEST_NO_AUTH": "1"}


def run_json(*args: str) -> dict:
    result = subprocess.run(
        [sys.executable, str(CLI), "--json", *args],
        text=True,
        capture_output=True,
        check=True,
        env=TEST_ENV,
    )
    return json.loads(result.stdout)


def run_ai_eval_with_trace_file(trace_file: Path, *, check: bool) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            sys.executable,
            str(CLI),
            "--json",
            "ai-eval-run",
            "--scenario",
            "discover_readiness",
            "--trace-file",
            str(trace_file),
        ],
        text=True,
        capture_output=True,
        check=check,
        env=TEST_ENV,
        timeout=120,
    )


def test_trace_file_writes_redacted_jsonl_when_writable(tmp_path: Path) -> None:
    trace_file = tmp_path / "trace.jsonl"
    result = run_ai_eval_with_trace_file(trace_file, check=True)
    report = json.loads(result.stdout)

    assert trace_file.exists()
    lines = [json.loads(line) for line in trace_file.read_text(encoding="utf-8").splitlines() if line]
    assert len(lines) >= 1
    for line in lines:
        assert "schema" in line
        joined_argv = " ".join(str(token) for token in line.get("argv", []))
        assert "|" not in joined_argv
        assert ";" not in joined_argv
    assert report["trace_persistence"]["status"] == "written"
    assert report["trace_persistence"]["path"] == str(trace_file)


def test_trace_persistence_helpers_redact_shell_like_tokens_in_process(tmp_path: Path) -> None:
    from cleancli.ai_eval import _persist_trace, _redact_event

    trace_file = tmp_path / "nested" / "trace.jsonl"
    event = {
        "argv": ["cleanmac", "--json", "safe", "bad|pipe", "bad;semicolon", "bad&and", "bad`tick", "bad$var"],
        "schema": "cleanmac.ai-trace-test.v1",
        "ok": True,
    }

    redacted = _redact_event(event)
    assert redacted["argv"] == ["cleanmac", "--json", "safe"]

    persistence = _persist_trace(trace_file, [event])
    assert persistence["status"] == "written"
    assert persistence["path"] == str(trace_file)
    assert persistence["event_count"] == 1
    rows = [json.loads(line) for line in trace_file.read_text(encoding="utf-8").splitlines()]
    assert rows[0]["argv"] == ["cleanmac", "--json", "safe"]


def test_trace_persistence_helpers_fail_closed_for_directory_and_symlink_in_process(tmp_path: Path) -> None:
    from cleancli.ai_eval import _persist_trace

    directory = tmp_path / "trace-dir"
    directory.mkdir()
    with pytest.raises(RuntimeError, match="trace-file-is-directory"):
        _persist_trace(directory, [])

    target = tmp_path / "target.jsonl"
    symlink = tmp_path / "trace-link.jsonl"
    symlink.symlink_to(target)
    with pytest.raises(RuntimeError, match="trace-file-is-symlink"):
        _persist_trace(symlink, [])


def test_trace_persistence_helper_wraps_write_errors_in_process(tmp_path: Path) -> None:
    from cleancli.ai_eval import _persist_trace

    parent_file = tmp_path / "not-a-directory"
    parent_file.write_text("occupied", encoding="utf-8")
    with pytest.raises(RuntimeError, match="trace-file-write-failed"):
        _persist_trace(parent_file / "trace.jsonl", [])


def test_trace_file_fails_closed_when_path_is_directory(tmp_path: Path) -> None:
    bad_path = tmp_path / "trace-as-dir"
    bad_path.mkdir()
    result = run_ai_eval_with_trace_file(bad_path, check=False)

    assert result.returncode != 0
    report = json.loads(result.stderr or result.stdout)
    assert report["schema"] == "cleanmac.ai-error.v1"
    assert "trace" in report["error"]["code"].lower()


def test_trace_file_fails_closed_when_path_is_symlink(tmp_path: Path) -> None:
    target = tmp_path / "real-trace.jsonl"
    symlink = tmp_path / "trace-link.jsonl"
    symlink.symlink_to(target)
    result = run_ai_eval_with_trace_file(symlink, check=False)

    assert result.returncode != 0
    report = json.loads(result.stderr or result.stdout)
    assert report["schema"] == "cleanmac.ai-error.v1"
    assert "trace" in report["error"]["code"].lower()


@pytest.mark.parametrize(
    ("scenario", "observed_schema", "observed_blocking_codes"),
    [
        ("confirmation_token_execution", "cleanmac.clean.v1", ["CONFIRMATION_TOKEN_MISMATCH"]),
        (
            "confirmation_token_validation",
            "cleanmac.ai-policy-simulation.v1",
            ["AI_ORIGIN_REQUIRES_CONFIRMATION_TOKEN"],
        ),
        ("bundle_protection_enforcement", "cleanmac.clean.v1", []),
    ],
)
def test_ai_eval_run_terminal_governance_scenarios(
    scenario: str,
    observed_schema: str,
    observed_blocking_codes: list[str],
) -> None:
    report = run_json("ai-eval-run", "--scenario", scenario)

    assert report["schema"] == "cleanmac.ai-eval-run.v1"
    assert report["passed"], report
    assert report["selected_scenarios"] == [scenario]
    assert report["passed_count"] == 1
    assert report["failed_count"] == 0

    result = report["results"][0]
    assert result["id"] == scenario
    assert result["observed_schema"] == observed_schema
    assert result["observed_blocking_codes"] == observed_blocking_codes
