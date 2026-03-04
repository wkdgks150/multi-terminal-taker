"""Tests for detector module."""

import os
import tempfile
from unittest.mock import patch
from terminal_activator.monitor import TerminalTab
from terminal_activator.detector import (
    is_shell_foreground, is_interactive_app, has_idle_marker,
    ContentStasisTracker, MARKER_DIR, STASIS_POLLS,
)


def _tab(tty: str, fg: str = "") -> TerminalTab:
    return TerminalTab(tty=tty, window_id=1, tab_index=1, fg_process=fg)


class TestShellDetection:
    def test_zsh_detected(self):
        assert is_shell_foreground(_tab("/dev/ttys001", "-zsh")) is True

    def test_bash_detected(self):
        assert is_shell_foreground(_tab("/dev/ttys001", "bash")) is True

    def test_fish_detected(self):
        assert is_shell_foreground(_tab("/dev/ttys001", "fish")) is True

    def test_full_path_detected(self):
        assert is_shell_foreground(_tab("/dev/ttys001", "/bin/zsh")) is True

    def test_claude_not_shell(self):
        assert is_shell_foreground(_tab("/dev/ttys001", "claude")) is False

    def test_vim_not_shell(self):
        assert is_shell_foreground(_tab("/dev/ttys001", "vim")) is False

    def test_empty_process(self):
        assert is_shell_foreground(_tab("/dev/ttys001", "")) is False

    def test_whitespace_process(self):
        assert is_shell_foreground(_tab("/dev/ttys001", "  ")) is False


class TestIdleMarker:
    def test_no_marker_not_idle(self):
        assert has_idle_marker("/dev/ttys999") is False

    def test_marker_exists_is_idle(self):
        os.makedirs(MARKER_DIR, exist_ok=True)
        marker = os.path.join(MARKER_DIR, "ttys999.idle")
        try:
            open(marker, "w").close()
            assert has_idle_marker("/dev/ttys999") is True
        finally:
            os.remove(marker)

    def test_marker_removed_not_idle(self):
        os.makedirs(MARKER_DIR, exist_ok=True)
        marker = os.path.join(MARKER_DIR, "ttys998.idle")
        open(marker, "w").close()
        os.remove(marker)
        assert has_idle_marker("/dev/ttys998") is False


class TestInteractiveApp:
    def test_claude_is_interactive(self):
        assert is_interactive_app(_tab("/dev/ttys001", "claude")) is True

    def test_node_is_interactive(self):
        assert is_interactive_app(_tab("/dev/ttys001", "node")) is True

    def test_shell_not_interactive(self):
        assert is_interactive_app(_tab("/dev/ttys001", "zsh")) is False

    def test_vim_not_interactive(self):
        assert is_interactive_app(_tab("/dev/ttys001", "vim")) is False

    def test_empty_not_interactive(self):
        assert is_interactive_app(_tab("/dev/ttys001", "")) is False


class TestContentStasis:
    def test_not_stale_initially(self):
        tracker = ContentStasisTracker()
        assert tracker.update("/dev/ttys001", 1000) is False

    def test_stale_after_threshold(self):
        tracker = ContentStasisTracker()
        for _ in range(STASIS_POLLS):
            tracker.update("/dev/ttys001", 1000)
        assert tracker.update("/dev/ttys001", 1000) is True

    def test_reset_on_content_change(self):
        tracker = ContentStasisTracker()
        for _ in range(STASIS_POLLS - 1):
            tracker.update("/dev/ttys001", 1000)
        # Content changes → reset
        tracker.update("/dev/ttys001", 1500)
        assert tracker.update("/dev/ttys001", 1500) is False

    def test_independent_per_tty(self):
        tracker = ContentStasisTracker()
        for _ in range(STASIS_POLLS + 1):
            tracker.update("/dev/ttys001", 1000)
        assert tracker.update("/dev/ttys001", 1000) is True
        # Different TTY starts fresh
        assert tracker.update("/dev/ttys002", 1000) is False

    def test_remove_stops_tracking(self):
        tracker = ContentStasisTracker()
        for _ in range(STASIS_POLLS + 1):
            tracker.update("/dev/ttys001", 1000)
        tracker.remove("/dev/ttys001")
        assert tracker.update("/dev/ttys001", 1000) is False
