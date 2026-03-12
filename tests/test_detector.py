"""Tests for detector module."""

import os
import tempfile
from unittest.mock import patch
from mtt.monitor import TerminalTab
from mtt.detector import (
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


class TestStasisChildProcess:
    """Stasis must not trigger when new child processes indicate a tool call."""

    def test_no_children_stale(self):
        """No children → stasis triggers normally (AskUserQuestion)."""
        tracker = ContentStasisTracker()
        for _ in range(STASIS_POLLS + 1):
            tracker.update("/dev/ttys001", 1000, frozenset())
        assert tracker.update("/dev/ttys001", 1000, frozenset()) is True

    def test_new_child_blocks_stasis(self):
        """New child appearing after content stops → tool call → not idle."""
        tracker = ContentStasisTracker()
        # Content changing phase — baseline recorded with no children
        tracker.update("/dev/ttys001", 100, frozenset())
        tracker.update("/dev/ttys001", 200, frozenset())
        # Content stops, new child appears (bash tool call)
        bash_pid = frozenset({12345})
        for _ in range(STASIS_POLLS + 1):
            tracker.update("/dev/ttys001", 200, bash_pid)
        assert tracker.update("/dev/ttys001", 200, bash_pid) is False

    def test_baseline_child_does_not_block(self):
        """MCP server present during content changes → absorbed into baseline."""
        tracker = ContentStasisTracker()
        mcp = frozenset({99999})
        # Content changing with MCP server running
        tracker.update("/dev/ttys001", 100, mcp)
        tracker.update("/dev/ttys001", 200, mcp)
        # Content stops, same MCP server still there — no new children
        for _ in range(STASIS_POLLS + 1):
            tracker.update("/dev/ttys001", 200, mcp)
        assert tracker.update("/dev/ttys001", 200, mcp) is True

    def test_new_child_plus_baseline(self):
        """MCP server (baseline) + new bash child → not idle."""
        tracker = ContentStasisTracker()
        mcp = frozenset({99999})
        # Baseline includes MCP
        tracker.update("/dev/ttys001", 100, mcp)
        tracker.update("/dev/ttys001", 200, mcp)
        # Content stops, new child alongside MCP
        both = frozenset({99999, 12345})
        for _ in range(STASIS_POLLS + 1):
            tracker.update("/dev/ttys001", 200, both)
        assert tracker.update("/dev/ttys001", 200, both) is False

    def test_child_disappears_resets_baseline(self):
        """Tool finishes → child gone → content changes → new baseline."""
        tracker = ContentStasisTracker()
        # Phase 1: tool running (child present during content change)
        bash = frozenset({12345})
        tracker.update("/dev/ttys001", 100, bash)
        tracker.update("/dev/ttys001", 200, bash)  # baseline = {12345}
        # Phase 2: tool done, child gone, Claude outputs result
        tracker.update("/dev/ttys001", 300, frozenset())  # baseline = {}
        # Phase 3: AskUserQuestion — no children, content stable
        for _ in range(STASIS_POLLS + 1):
            tracker.update("/dev/ttys001", 300, frozenset())
        assert tracker.update("/dev/ttys001", 300, frozenset()) is True
