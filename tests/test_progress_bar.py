"""Tests for cleancli.progress stderr progress bar."""

from __future__ import annotations

import io
import sys

from cleancli.progress import ProgressBar, close_progress, make_execute_progress, make_scan_progress


class FakeTTY(io.StringIO):
    def isatty(self) -> bool:
        return True


class TestProgressBar:
    def test_renders_pytest_style_percentage(self) -> None:
        stream = FakeTTY()
        bar = ProgressBar(10, label="Scan", stream=stream)
        assert bar._active

        bar.update(5)
        output = stream.getvalue()
        assert "Scan" in output
        assert "50%" in output
        assert "#" in output
        assert "\r" in output

    def test_close_finishes_at_100(self) -> None:
        stream = FakeTTY()
        bar = ProgressBar(4, label="Test", stream=stream)
        bar.update(2)
        bar.close()
        output = stream.getvalue()
        assert "100%" in output
        assert output.endswith("\n")

    def test_sets_total_to_zero_for_negative(self) -> None:
        stream = FakeTTY()
        bar = ProgressBar(-5, label="Test", stream=stream)
        assert bar.total == 0
        assert not bar._active

    def test_inactive_when_stream_is_not_tty(self) -> None:
        stream = io.StringIO()
        bar = ProgressBar(10, label="Test", stream=stream)
        assert not bar._active
        bar.update(5)
        assert stream.getvalue() == ""

    def test_inactive_when_stream_is_none(self) -> None:
        bar = ProgressBar(10, label="Test", stream=None)
        assert not bar._active
        bar.update(5)
        bar.close()

    def test_update_does_not_exceed_total(self) -> None:
        stream = FakeTTY()
        bar = ProgressBar(3, label="Test", stream=stream)
        bar.update(10)
        assert bar.current == 3

    def test_set_current_bounds_check(self) -> None:
        stream = FakeTTY()
        bar = ProgressBar(5, label="Test", stream=stream)
        bar.set_current(10)
        assert bar.current == 5
        bar.set_current(-1)
        assert bar.current == 0

    def test_zero_total_shows_100_percent(self) -> None:
        stream = FakeTTY()
        bar = ProgressBar(0, label="Test", stream=stream)
        assert not bar._active

    def test_progress_bar_uses_current_sys_stderr(self) -> None:
        original = sys.stderr
        fake = FakeTTY()
        try:
            sys.stderr = fake
            bar = ProgressBar(3, label="StderrTest")
            assert bar.stream is fake
            assert bar._active
            bar.update(1)
            assert "StderrTest" in fake.getvalue()
        finally:
            sys.stderr = original


class TestMakeScanProgress:
    def test_enabled_creates_callable_with_bar(self) -> None:
        stream = FakeTTY()
        cb = make_scan_progress(5, enabled=True)
        # Override stream for testing
        cb._bar.stream = stream  # type: ignore[attr-defined]
        cb._bar._active = True  # type: ignore[attr-defined]
        cb()
        cb(2)
        assert cb._bar.current == 3  # type: ignore[attr-defined]

    def test_disabled_returns_noop(self) -> None:
        cb = make_scan_progress(5, enabled=False)
        assert callable(cb)
        cb()
        # Should not raise

    def test_zero_total_returns_noop(self) -> None:
        cb = make_scan_progress(0, enabled=True)
        assert callable(cb)
        cb()


class TestMakeExecuteProgress:
    def test_enabled_creates_callable_with_bar(self) -> None:
        cb = make_execute_progress(10, enabled=True)
        assert hasattr(cb, "_bar")
        assert cb._bar.label == "Cleaning"  # type: ignore[attr-defined]

    def test_disabled_returns_noop(self) -> None:
        cb = make_execute_progress(10, enabled=False)
        assert callable(cb)


class TestCloseProgress:
    def test_close_with_valid_cb(self) -> None:
        stream = FakeTTY()
        cb = make_scan_progress(5, enabled=True)
        cb._bar.stream = stream  # type: ignore[attr-defined]
        cb._bar._active = True  # type: ignore[attr-defined]
        close_progress(cb)
        output = stream.getvalue()
        assert "100%" in output

    def test_close_with_none_is_safe(self) -> None:
        close_progress(None)

    def test_close_with_noop_is_safe(self) -> None:
        cb = make_scan_progress(0, enabled=True)
        close_progress(cb)
