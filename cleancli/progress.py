"""Lightweight stderr progress bar for human-readable CLI output.

Only used when stdout is not JSON and --quiet is not set.
Writes to stderr so JSON stdout remains clean and machine-parseable.
"""

from __future__ import annotations

import sys
from collections.abc import Callable


class ProgressBar:
    """In-place stderr progress bar with pytest-style percentage display.

    Uses carriage return to redraw the same line. Call close() to finalize.
    """

    def __init__(
        self,
        total: int,
        *,
        label: str = "",
        width: int = 20,
        stream=None,
    ) -> None:
        self.total = max(total, 0)
        self.label = label
        self.width = width
        self.stream = stream if stream is not None else sys.stderr
        self.current = 0
        self._last_len = 0
        self._active = total > 0 and self.stream is not None and self.stream.isatty()

    def update(self, n: int = 1) -> None:
        self.current = min(self.current + n, self.total)
        self._render()

    def set_current(self, value: int) -> None:
        self.current = min(max(value, 0), self.total)
        self._render()

    def _render(self) -> None:
        if not self._active or self.stream is None:
            return
        if self.total == 0:
            pct = 100
            filled = self.width
        else:
            pct = int(self.current * 100 / self.total)
            filled = int(self.current * self.width / self.total)
        bar = "#" * filled + " " * (self.width - filled)
        line = f"{self.label} [{bar}] {pct:>3}% ({self.current}/{self.total})"
        # Pad with spaces to clear previous longer line, then \r
        if len(line) < self._last_len:
            line = line + " " * (self._last_len - len(line))
        self._last_len = len(line)
        print(f"\r{line}", end="", file=self.stream, flush=True)

    def close(self) -> None:
        if not self._active or self.stream is None:
            return
        # Final render at 100% then newline
        self.current = self.total
        self._render()
        print("", file=self.stream, flush=True)
        self._active = False


def _noop_progress(_n: int = 1) -> None:
    pass


def make_scan_progress(total: int, *, enabled: bool) -> Callable[[int], None]:
    """Create a scan-phase progress callback. Returns a no-op if disabled."""
    if not enabled or total <= 0:
        return _noop_progress
    bar = ProgressBar(total, label="Scanning")

    def _tick(n: int = 1) -> None:
        bar.update(n)

    # Attach close so caller can finalize
    _tick._bar = bar  # type: ignore[attr-defined]
    return _tick


def make_execute_progress(total: int, *, enabled: bool) -> Callable[[int], None]:
    """Create an execute-phase progress callback. Returns a no-op if disabled."""
    if not enabled or total <= 0:
        return _noop_progress
    bar = ProgressBar(total, label="Cleaning")

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
