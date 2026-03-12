"""Tests for detector module."""

import os
from unittest.mock import patch
from mtt.monitor import TerminalTab
from mtt.detector import (
    is_shell_foreground, is_interactive_app, has_idle_marker,
    has_busy_marker, detect_idle, ContentStasisTracker, MARKER_DIR,
    STASIS_POLLS,
)


def _tab(tty: str, fg: str = "", content_len: int = 0) -> TerminalTab:
    return TerminalTab(tty=tty, window_id=1, tab_index=1,
                       fg_process=fg, content_len=content_len)


# -- Shell detection --------------------------------------------------

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


# -- Idle marker ------------------------------------------------------

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


# -- Busy marker -------------------------------------------------------

class TestBusyMarker:
    def test_no_marker_not_busy(self):
        assert has_busy_marker("/dev/ttys997") is False

    def test_marker_exists_is_busy(self):
        os.makedirs(MARKER_DIR, exist_ok=True)
        marker = os.path.join(MARKER_DIR, "ttys997.busy")
        try:
            open(marker, "w").close()
            assert has_busy_marker("/dev/ttys997") is True
        finally:
            os.remove(marker)

    def test_marker_removed_not_busy(self):
        os.makedirs(MARKER_DIR, exist_ok=True)
        marker = os.path.join(MARKER_DIR, "ttys996.busy")
        open(marker, "w").close()
        os.remove(marker)
        assert has_busy_marker("/dev/ttys996") is False


# -- Interactive app ---------------------------------------------------

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


# -- Content stasis ----------------------------------------------------

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


# -- Stasis child process tracking -------------------------------------

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


# -- detect_idle() orchestration ---------------------------------------

class TestDetectIdle:
    """Test the idle detection priority chain."""

    def test_marker_highest_priority(self):
        """Marker wins even when shell and stasis would also match."""
        os.makedirs(MARKER_DIR, exist_ok=True)
        marker = os.path.join(MARKER_DIR, "ttys050.idle")
        try:
            open(marker, "w").close()
            tab = _tab("/dev/ttys050", "-zsh", content_len=100)
            stasis = ContentStasisTracker()
            detect_idle(tab, frozenset(), stasis)
            assert tab.waiting_for_input is True
            assert tab.idle_reason == "marker"
        finally:
            os.remove(marker)

    def test_shell_second_priority(self):
        """Shell detected when no marker exists."""
        tab = _tab("/dev/ttys051", "-zsh")
        stasis = ContentStasisTracker()
        detect_idle(tab, frozenset(), stasis)
        assert tab.waiting_for_input is True
        assert tab.idle_reason == "shell"

    def test_stasis_third_priority(self):
        """Interactive app + stasis triggers idle."""
        stasis = ContentStasisTracker()
        tab = _tab("/dev/ttys052", "claude", content_len=500)
        for _ in range(STASIS_POLLS + 1):
            tab.waiting_for_input = False
            tab.idle_reason = ""
            detect_idle(tab, frozenset(), stasis)
        assert tab.waiting_for_input is True
        assert tab.idle_reason == "stasis"

    def test_interactive_not_stale(self):
        """Interactive app but content keeps changing → not idle."""
        stasis = ContentStasisTracker()
        for i in range(STASIS_POLLS + 1):
            tab = _tab("/dev/ttys053", "claude", content_len=100 + i)
            detect_idle(tab, frozenset(), stasis)
        assert tab.waiting_for_input is False
        assert tab.idle_reason == ""

    def test_non_interactive_non_shell(self):
        """Random process (vim, make, etc.) → not idle."""
        tab = _tab("/dev/ttys054", "vim", content_len=100)
        stasis = ContentStasisTracker()
        detect_idle(tab, frozenset(), stasis)
        assert tab.waiting_for_input is False
        assert tab.idle_reason == ""

    def test_busy_marker_overrides_stasis(self):
        """Busy marker prevents stasis from triggering (concocting scenario)."""
        os.makedirs(MARKER_DIR, exist_ok=True)
        busy = os.path.join(MARKER_DIR, "ttys056.busy")
        try:
            open(busy, "w").close()
            stasis = ContentStasisTracker()
            tab = _tab("/dev/ttys056", "claude", content_len=500)
            for _ in range(STASIS_POLLS + 1):
                tab.waiting_for_input = False
                tab.idle_reason = ""
                detect_idle(tab, frozenset(), stasis)
            assert tab.waiting_for_input is False
            assert tab.idle_reason == ""
        finally:
            os.remove(busy)

    def test_busy_marker_overridden_by_idle_marker(self):
        """Idle marker takes priority even when busy marker also exists."""
        os.makedirs(MARKER_DIR, exist_ok=True)
        idle = os.path.join(MARKER_DIR, "ttys057.idle")
        busy = os.path.join(MARKER_DIR, "ttys057.busy")
        try:
            open(idle, "w").close()
            open(busy, "w").close()
            tab = _tab("/dev/ttys057", "claude")
            stasis = ContentStasisTracker()
            detect_idle(tab, frozenset(), stasis)
            assert tab.waiting_for_input is True
            assert tab.idle_reason == "marker"
        finally:
            os.remove(idle)
            os.remove(busy)

    def test_stasis_blocked_by_new_child(self):
        """Interactive app + stasis + new child → not idle (tool running)."""
        stasis = ContentStasisTracker()
        # Baseline with no children
        tab = _tab("/dev/ttys055", "claude", content_len=100)
        detect_idle(tab, frozenset(), stasis)
        tab.content_len = 200
        detect_idle(tab, frozenset(), stasis)
        # Content stops, child appears
        tab.content_len = 200
        for _ in range(STASIS_POLLS + 1):
            tab.waiting_for_input = False
            tab.idle_reason = ""
            detect_idle(tab, frozenset({9999}), stasis)
        assert tab.waiting_for_input is False
