"""Lightweight stderr progress indicator for human-readable CLI output.

Only used when stdout is not JSON and --quiet is not set.
Writes to stderr so JSON stdout remains clean and machine-parseable.

On TTYs: in-place carriage-return progress bar with colors and timing.
On non-TTYs: one-line start/done messages per phase (safe for logs/CI).
"""

from __future__ import annotations

import sys
import time
from collections.abc import Callable

_BAR_FILL = "█"
_BAR_EMPTY = "░"
_DONE_MARK = "✓"
_SCAN_ICON = "🔍"
_CLEAN_ICON = "🗑️ "

_RESET = "\033[0m"
_GREEN = "\033[32m"
_CYAN = "\033[36m"
_YELLOW = "\033[33m"
_DIM = "\033[2m"


def _color(text: str, code: str, *, enabled: bool) -> str:
    return f"{code}{text}{_RESET}" if enabled else text


def _format_duration(seconds: float) -> str:
    if seconds < 60:
        return f"{seconds:.1f}s"
    mins = int(seconds // 60)
    secs = int(seconds % 60)
    return f"{mins}m{secs:02d}s"


class ProgressBar:
    """Progress indicator with TTY-aware rendering and timing.

    TTY mode: in-place redraw with Unicode bar, colors, and elapsed time.
    Non-TTY mode: start + done messages with counts (log/CI friendly).
    """

    def __init__(
        self,
        total: int,
        *,
        label: str = "",
        width: int = 24,
        stream=None,
        icon: str = "",
    ) -> None:
        self.total = max(total, 0)
        self.label = label
        self.width = width
        self.stream = stream if stream is not None else sys.stderr
        self.current = 0
        self._last_len = 0
        self._is_tty = self.stream is not None and self.stream.isatty()
        self._active = total > 0 and self.stream is not None
        self._started = False
        self._start_time: float | None = None
        self._icon = icon

    def _ensure_started(self) -> None:
        if self._started or not self._active:
            return
        self._started = True
        self._start_time = time.time()
        if not self._is_tty:
            prefix = f"{self._icon} " if self._icon else ""
            print(f"{prefix}{self.label}... ({self.total} items)", file=self.stream, flush=True)

    def update(self, n: int = 1) -> None:
        self.current = min(self.current + n, self.total)
        self._render()

    def set_current(self, value: int) -> None:
        self.current = min(max(value, 0), self.total)
        self._render()

    def _render(self) -> None:
        if not self._active or self.stream is None:
            return
        self._ensure_started()
        if self.total == 0:
            pct = 100
            filled = self.width
        else:
            pct = int(self.current * 100 / self.total)
            filled = int(self.current * self.width / self.total)
        if self._is_tty:
            empty = self.width - filled
            bar = _color(_BAR_FILL * filled, _GREEN, enabled=True) + _color(_BAR_EMPTY * empty, _DIM, enabled=True)
            pct_str = _color(f"{pct:>3}%", _CYAN, enabled=True)
            count_str = _color(f"{self.current}/{self.total}", _DIM, enabled=True)
            elapsed = ""
            if self._start_time is not None:
                elapsed = _color(f" {_format_duration(time.time() - self._start_time)}", _DIM, enabled=True)
            prefix = f"{self._icon} " if self._icon else ""
            line = f"{prefix}{self.label} {bar} {pct_str} {count_str}{elapsed}"
            line_len = len(line) - line.count("\033") * 5 - 2 * line.count("\033[0m")
            if line_len < self._last_len:
                line = line + " " * (self._last_len - line_len)
            self._last_len = line_len
            print(f"\r{line}", end="", file=self.stream, flush=True)

    def close(self) -> None:
        if not self._active or self.stream is None:
            return
        self._ensure_started()
        self.current = self.total
        duration = _format_duration(time.time() - self._start_time) if self._start_time else "0.0s"
        if self._is_tty:
            self._render()
            done = _color(_DONE_MARK, _GREEN, enabled=True)
            label = _color(f"{self.label} complete", _GREEN, enabled=True)
            elapsed = _color(duration, _DIM, enabled=True)
            line = f"  {done} {label} in {elapsed}"
            print(f"\r{line}" + " " * max(0, self._last_len - len(line) + 10), file=self.stream, flush=True)
        else:
            prefix = f"{_DONE_MARK} " if self._icon else ""
            print(f"{prefix}{self.label} done ({self.total} items, {duration})", file=self.stream, flush=True)
        self._active = False


def _noop_progress(_n: int = 1) -> None:
    pass


def make_scan_progress(total: int, *, enabled: bool) -> Callable[..., None]:
    """Create a scan-phase progress callback. Returns a no-op if disabled."""
    if not enabled or total <= 0:
        return _noop_progress
    bar = ProgressBar(total, label="Scanning", icon=_SCAN_ICON)

    def _tick(n: int = 1) -> None:
        bar.update(n)

    # Attach close so caller can finalize
    _tick._bar = bar  # type: ignore[attr-defined]
    return _tick


def make_execute_progress(total: int, *, enabled: bool) -> Callable[..., None]:
    """Create an execute-phase progress callback. Returns a no-op if disabled."""
    if not enabled or total <= 0:
        return _noop_progress
    bar = ProgressBar(total, label="Cleaning", icon=_CLEAN_ICON)

    def _tick(n: int = 1) -> None:
        bar.update(n)

    _tick._bar = bar  # type: ignore[attr-defined]
    return _tick


def close_progress(progress_cb: Callable[..., None] | None) -> None:
    """Safely close a progress bar if the callback has one attached."""
    if progress_cb is None:
        return
    bar = getattr(progress_cb, "_bar", None)
    if bar is not None:
        bar.close()
