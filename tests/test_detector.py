"""Tests for detector module."""

from terminal_activator.monitor import TerminalTab
from terminal_activator.detector import is_shell_foreground, ContentTracker


class TestIsShellForeground:
    def _tab(self, fg_process: str) -> TerminalTab:
        return TerminalTab(tty="/dev/ttys001", window_id=1, tab_index=1, fg_process=fg_process)

    def test_zsh(self):
        assert is_shell_foreground(self._tab("zsh")) is True

    def test_login_zsh(self):
        assert is_shell_foreground(self._tab("-zsh")) is True

    def test_bash(self):
        assert is_shell_foreground(self._tab("bash")) is True

    def test_login_bash(self):
        assert is_shell_foreground(self._tab("-bash")) is True

    def test_fish(self):
        assert is_shell_foreground(self._tab("fish")) is True

    def test_sh(self):
        assert is_shell_foreground(self._tab("sh")) is True

    def test_claude_not_shell(self):
        assert is_shell_foreground(self._tab("claude")) is False

    def test_python_not_shell(self):
        assert is_shell_foreground(self._tab("python3")) is False

    def test_vim_not_shell(self):
        assert is_shell_foreground(self._tab("vim")) is False

    def test_empty_process(self):
        assert is_shell_foreground(self._tab("")) is False

    def test_full_path_zsh(self):
        assert is_shell_foreground(self._tab("/bin/zsh")) is True

    def test_full_path_bash(self):
        assert is_shell_foreground(self._tab("/bin/bash")) is True


class TestContentTracker:
    def test_initial_poll_not_idle(self):
        tracker = ContentTracker()
        assert tracker.update("/dev/ttys001", "abc123") is False

    def test_second_poll_same_hash_not_idle_yet(self):
        tracker = ContentTracker()
        tracker.update("/dev/ttys001", "abc123")
        assert tracker.update("/dev/ttys001", "abc123") is False

    def test_reaches_threshold_becomes_idle(self):
        tracker = ContentTracker()
        tty = "/dev/ttys001"
        # First poll sets baseline
        tracker.update(tty, "abc123")
        # Polls 2-5: static count goes 1,2,3,4
        for i in range(4):
            result = tracker.update(tty, "abc123")
            assert result is False, f"Should not be idle at static count {i+1}"
        # Poll 6: static count = 5 = threshold
        assert tracker.update(tty, "abc123") is True

    def test_content_change_resets_count(self):
        tracker = ContentTracker()
        tty = "/dev/ttys001"
        # Build up 4 static polls
        for _ in range(5):
            tracker.update(tty, "abc123")
        # Content changes
        tracker.update(tty, "def456")
        # Need 5 more static polls to be idle again
        for _ in range(4):
            assert tracker.update(tty, "def456") is False
        assert tracker.update(tty, "def456") is True

    def test_multiple_ttys_independent(self):
        tracker = ContentTracker()
        tty1 = "/dev/ttys001"
        tty2 = "/dev/ttys002"
        # tty1 becomes idle
        for _ in range(6):
            tracker.update(tty1, "aaa")
        assert tracker.is_content_idle(tty1) is True
        # tty2 is not idle
        tracker.update(tty2, "bbb")
        assert tracker.is_content_idle(tty2) is False

    def test_empty_hash_resets(self):
        tracker = ContentTracker()
        tty = "/dev/ttys001"
        tracker.update(tty, "abc123")
        tracker.update(tty, "abc123")
        tracker.update(tty, "abc123")
        # Empty hash = something went wrong, resets
        tracker.update(tty, "")
        assert tracker.is_content_idle(tty) is False

    def test_is_content_idle_method(self):
        tracker = ContentTracker()
        tty = "/dev/ttys001"
        assert tracker.is_content_idle(tty) is False
        for _ in range(6):
            tracker.update(tty, "stable")
        assert tracker.is_content_idle(tty) is True
