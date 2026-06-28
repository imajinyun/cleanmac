"""Tests for cleancli.progress stderr progress bar."""

from __future__ import annotations

import io
import sys

from cleancli.progress import (
    _BAR_FILL,
    _CLEAN_ICON,
    _DONE_MARK,
    _SCAN_ICON,
    ProgressBar,
    close_progress,
    make_execute_progress,
    make_scan_progress,
)


class FakeTTY(io.StringIO):
    def isatty(self) -> bool:
        return True


class TestProgressBarTTYMode:
    def test_renders_unicode_bar_with_percentage(self) -> None:
        stream = FakeTTY()
        bar = ProgressBar(10, label="Scan", stream=stream)
        assert bar._active
        assert bar._is_tty

        bar.update(5)
        output = stream.getvalue()
        assert "Scan" in output
        assert "50%" in output
        assert _BAR_FILL in output
        assert "\r" in output

    def test_close_shows_complete_with_checkmark(self) -> None:
        stream = FakeTTY()
        bar = ProgressBar(4, label="Test", stream=stream)
        bar.update(2)
        bar.close()
        output = stream.getvalue()
        assert _DONE_MARK in output
        assert "complete" in output
        assert output.endswith("\n")

    def test_has_colors_on_tty(self) -> None:
        stream = FakeTTY()
        bar = ProgressBar(5, label="Test", stream=stream)
        bar.update(3)
        bar.close()
        output = stream.getvalue()
        assert "\033[32m" in output
        assert "\033[36m" in output
        assert "\033[0m" in output

    def test_icon_is_displayed(self) -> None:
        stream = FakeTTY()
        bar = ProgressBar(5, label="Scan", stream=stream, icon=_SCAN_ICON)
        bar.update(1)
        output = stream.getvalue()
        assert _SCAN_ICON in output

    def test_shows_elapsed_time(self) -> None:
        stream = FakeTTY()
        bar = ProgressBar(5, label="Test", stream=stream)
        bar.update(2)
        bar.close()
        output = stream.getvalue()
        assert "s" in output


class TestProgressBarNonTTYMode:
    def test_non_tty_uses_log_friendly_messages(self) -> None:
        stream = io.StringIO()
        bar = ProgressBar(10, label="Scan", stream=stream)
        assert bar._active
        assert not bar._is_tty
        bar.update(5)
        bar.close()
        output = stream.getvalue()
        assert "Scan..." in output
        assert "done" in output
        assert "\r" not in output

    def test_non_tty_no_ansi_codes(self) -> None:
        stream = io.StringIO()
        bar = ProgressBar(10, label="Scan", stream=stream)
        bar.update(5)
        bar.close()
        output = stream.getvalue()
        assert "\033[" not in output

    def test_non_tty_shows_duration(self) -> None:
        stream = io.StringIO()
        bar = ProgressBar(10, label="Scan", stream=stream)
        bar.close()
        output = stream.getvalue()
        assert "s)" in output or "s," in output


class TestProgressBarEdgeCases:
    def test_sets_total_to_zero_for_negative(self) -> None:
        stream = FakeTTY()
        bar = ProgressBar(-5, label="Test", stream=stream)
        assert bar.total == 0
        assert not bar._active

    def test_none_stream_falls_back_to_sys_stderr(self) -> None:
        bar = ProgressBar(10, label="Test", stream=None)
        assert bar.stream is sys.stderr
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

    def test_zero_total_is_inactive(self) -> None:
        stream = FakeTTY()
        bar = ProgressBar(0, label="Test", stream=stream)
        assert not bar._active

    def test_uses_current_sys_stderr(self) -> None:
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
        cb = make_scan_progress(5, enabled=True)
        assert hasattr(cb, "_bar")
        assert cb._bar.label == "Scanning"  # type: ignore[attr-defined]
        assert cb._bar._icon == _SCAN_ICON  # type: ignore[attr-defined]
        cb()
        cb(2)
        assert cb._bar.current == 3  # type: ignore[attr-defined]

    def test_disabled_returns_noop(self) -> None:
        cb = make_scan_progress(5, enabled=False)
        assert callable(cb)
        assert not hasattr(cb, "_bar")
        cb()

    def test_zero_total_returns_noop(self) -> None:
        cb = make_scan_progress(0, enabled=True)
        assert callable(cb)
        assert not hasattr(cb, "_bar")
        cb()


class TestMakeExecuteProgress:
    def test_enabled_creates_callable_with_clean_icon(self) -> None:
        cb = make_execute_progress(10, enabled=True)
        assert hasattr(cb, "_bar")
        assert cb._bar.label == "Cleaning"  # type: ignore[attr-defined]
        assert cb._bar._icon == _CLEAN_ICON  # type: ignore[attr-defined]

    def test_disabled_returns_noop(self) -> None:
        cb = make_execute_progress(10, enabled=False)
        assert callable(cb)
        assert not hasattr(cb, "_bar")


class TestCloseProgress:
    def test_close_with_valid_cb(self) -> None:
        stream = FakeTTY()
        cb = make_scan_progress(5, enabled=True)
        cb._bar.stream = stream  # type: ignore[attr-defined]
        cb._bar._is_tty = True  # type: ignore[attr-defined]
        close_progress(cb)
        output = stream.getvalue()
        assert "100%" in output

    def test_close_with_none_is_safe(self) -> None:
        close_progress(None)

    def test_close_with_noop_is_safe(self) -> None:
        cb = make_scan_progress(0, enabled=True)
        close_progress(cb)
