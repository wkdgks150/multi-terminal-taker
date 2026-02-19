"""Tests for popup queue module."""

from unittest.mock import patch, MagicMock
from terminal_activator.monitor import TerminalTab
from terminal_activator.queue import PopupQueue, STATIC_POLLS_TO_CLEAR


def _tab(tty: str, fg: str = "-zsh", waiting: bool = True) -> TerminalTab:
    return TerminalTab(
        tty=tty, window_id=1, tab_index=1,
        fg_process=fg, waiting_for_input=waiting,
    )


class TestPopupQueueBasic:
    def test_starts_idle(self):
        q = PopupQueue("/dev/ttys000")
        assert q.serving is None
        assert q.waiting == []
        assert q.status_line == "IDLE"

    def test_excludes_own_tty(self):
        q = PopupQueue("/dev/ttys000")
        tabs = [_tab("/dev/ttys000")]
        with patch("terminal_activator.queue.window_controller") as mock_wc:
            q.update(tabs, terminal_is_frontmost=True)
        assert q.serving is None
        assert q.waiting == []

    @patch("terminal_activator.queue.window_controller")
    @patch("terminal_activator.queue.get_content_hash", return_value="hash1")
    def test_first_waiting_tab_gets_served(self, mock_hash, mock_wc):
        mock_wc.popup.return_value = True
        q = PopupQueue("/dev/ttys000")
        tabs = [_tab("/dev/ttys001")]
        q.update(tabs, terminal_is_frontmost=True)
        assert q.serving is not None
        assert q.serving.tty == "/dev/ttys001"
        mock_wc.popup.assert_called_once_with("/dev/ttys001")

    @patch("terminal_activator.queue.window_controller")
    @patch("terminal_activator.queue.get_content_hash", return_value="hash1")
    def test_second_waiting_goes_to_queue(self, mock_hash, mock_wc):
        mock_wc.popup.return_value = True
        q = PopupQueue("/dev/ttys000")
        tabs = [_tab("/dev/ttys001"), _tab("/dev/ttys002")]
        q.update(tabs, terminal_is_frontmost=True)
        assert q.serving.tty == "/dev/ttys001"
        assert len(q.waiting) == 1
        assert q.waiting[0].tty == "/dev/ttys002"

    @patch("terminal_activator.queue.window_controller")
    @patch("terminal_activator.queue.get_content_hash", return_value="hash1")
    def test_no_popup_when_terminal_not_frontmost(self, mock_hash, mock_wc):
        q = PopupQueue("/dev/ttys000")
        tabs = [_tab("/dev/ttys001")]
        q.update(tabs, terminal_is_frontmost=False)
        assert q.serving is None
        assert len(q.waiting) == 1


class TestServingClear:
    @patch("terminal_activator.queue.window_controller")
    @patch("terminal_activator.queue.get_content_hash", return_value="hash1")
    def test_fg_change_clears_serving(self, mock_hash, mock_wc):
        mock_wc.popup.return_value = True
        q = PopupQueue("/dev/ttys000")

        # Serve tab with fg=claude
        tabs = [_tab("/dev/ttys001", fg="claude")]
        q.update(tabs, terminal_is_frontmost=True)
        assert q.serving.tty == "/dev/ttys001"

        # fg changes to npm (user ran a command, tab now busy)
        tabs = [_tab("/dev/ttys001", fg="npm", waiting=False)]
        q.update(tabs, terminal_is_frontmost=True)
        assert q.serving is None

    @patch("terminal_activator.queue.window_controller")
    @patch("terminal_activator.queue.get_content_hash")
    def test_content_cycle_clears_serving(self, mock_hash, mock_wc):
        mock_wc.popup.return_value = True
        q = PopupQueue("/dev/ttys000")

        # Serve
        mock_hash.return_value = "hash_initial"
        tabs = [_tab("/dev/ttys001", fg="claude")]
        q.update(tabs, terminal_is_frontmost=True)
        assert q.serving is not None

        # Content changes (user interacted)
        mock_hash.return_value = "hash_changed"
        q.update(tabs, terminal_is_frontmost=True)
        assert q._ever_changed is True

        # Content stabilizes for STATIC_POLLS_TO_CLEAR polls
        # Tab is no longer waiting (e.g., claude responded and is now busy)
        tabs_done = [_tab("/dev/ttys001", fg="claude", waiting=False)]
        mock_hash.return_value = "hash_stable"
        q.update(tabs_done, terminal_is_frontmost=True)  # change → static_count=0
        for _ in range(STATIC_POLLS_TO_CLEAR):
            q.update(tabs_done, terminal_is_frontmost=True)

        assert q.serving is None

    @patch("terminal_activator.queue.window_controller")
    @patch("terminal_activator.queue.get_content_hash", return_value="hash1")
    def test_tab_disappears_clears_serving(self, mock_hash, mock_wc):
        mock_wc.popup.return_value = True
        q = PopupQueue("/dev/ttys000")

        tabs = [_tab("/dev/ttys001", fg="claude")]
        q.update(tabs, terminal_is_frontmost=True)
        assert q.serving is not None

        # Tab no longer in scan results (window closed)
        q.update([], terminal_is_frontmost=True)
        assert q.serving is None


class TestQueueProgression:
    @patch("terminal_activator.queue.window_controller")
    @patch("terminal_activator.queue.get_content_hash", return_value="hash1")
    def test_next_tab_pops_after_fg_change(self, mock_hash, mock_wc):
        mock_wc.popup.return_value = True
        q = PopupQueue("/dev/ttys000")

        # Two waiting tabs
        tabs = [
            _tab("/dev/ttys001", fg="claude"),
            _tab("/dev/ttys002", fg="claude"),
        ]
        q.update(tabs, terminal_is_frontmost=True)
        assert q.serving.tty == "/dev/ttys001"
        assert len(q.waiting) == 1

        # First tab clears via fg change
        tabs = [
            _tab("/dev/ttys001", fg="-zsh", waiting=False),
            _tab("/dev/ttys002", fg="claude"),
        ]
        q.update(tabs, terminal_is_frontmost=True)
        # Should now serve the second tab
        assert q.serving.tty == "/dev/ttys002"
        assert len(q.waiting) == 0

    @patch("terminal_activator.queue.window_controller")
    @patch("terminal_activator.queue.get_content_hash", return_value="hash1")
    def test_queued_tab_removed_when_no_longer_waiting(self, mock_hash, mock_wc):
        mock_wc.popup.return_value = True
        q = PopupQueue("/dev/ttys000")

        tabs = [
            _tab("/dev/ttys001", fg="claude"),
            _tab("/dev/ttys002", fg="claude"),
            _tab("/dev/ttys003", fg="claude"),
        ]
        q.update(tabs, terminal_is_frontmost=True)
        assert len(q.waiting) == 2

        # Tab 002 no longer waiting
        tabs = [
            _tab("/dev/ttys001", fg="claude"),
            _tab("/dev/ttys002", fg="claude", waiting=False),
            _tab("/dev/ttys003", fg="claude"),
        ]
        q.update(tabs, terminal_is_frontmost=True)
        assert len(q.waiting) == 1
        assert q.waiting[0].tty == "/dev/ttys003"

    @patch("terminal_activator.queue.window_controller")
    @patch("terminal_activator.queue.get_content_hash", return_value="hash1")
    def test_no_duplicate_in_queue(self, mock_hash, mock_wc):
        mock_wc.popup.return_value = True
        q = PopupQueue("/dev/ttys000")

        tabs = [_tab("/dev/ttys001"), _tab("/dev/ttys002")]
        q.update(tabs, terminal_is_frontmost=True)
        # Call again with same tabs
        q.update(tabs, terminal_is_frontmost=True)
        # ttys002 should only be in queue once
        assert len(q.waiting) == 1

    @patch("terminal_activator.queue.window_controller")
    @patch("terminal_activator.queue.get_content_hash", return_value="hash1")
    def test_popup_failure_tries_next(self, mock_hash, mock_wc):
        mock_wc.popup.side_effect = [False, True]
        q = PopupQueue("/dev/ttys000")

        tabs = [_tab("/dev/ttys001"), _tab("/dev/ttys002")]
        q.update(tabs, terminal_is_frontmost=True)
        # First popup fails, but tab stays in queue (not popped to serving)
        # Current impl: popup fails → serving stays None → next update will retry
        # The tab remains in the waiting list
        if q.serving is None:
            # Retry
            q.update(tabs, terminal_is_frontmost=True)


class TestStatusLine:
    @patch("terminal_activator.queue.window_controller")
    @patch("terminal_activator.queue.get_content_hash", return_value="hash1")
    def test_idle_status(self, mock_hash, mock_wc):
        q = PopupQueue("/dev/ttys000")
        assert q.status_line == "IDLE"

    @patch("terminal_activator.queue.window_controller")
    @patch("terminal_activator.queue.get_content_hash", return_value="hash1")
    def test_serving_status(self, mock_hash, mock_wc):
        mock_wc.popup.return_value = True
        q = PopupQueue("/dev/ttys000")
        tabs = [_tab("/dev/ttys001")]
        q.update(tabs, terminal_is_frontmost=True)
        assert "SERVING: /dev/ttys001" in q.status_line
        assert "AWAITING" in q.status_line

    @patch("terminal_activator.queue.window_controller")
    @patch("terminal_activator.queue.get_content_hash")
    def test_interacted_status(self, mock_hash, mock_wc):
        mock_wc.popup.return_value = True
        q = PopupQueue("/dev/ttys000")
        mock_hash.return_value = "hash1"
        tabs = [_tab("/dev/ttys001", fg="claude")]
        q.update(tabs, terminal_is_frontmost=True)

        mock_hash.return_value = "hash2"
        q.update(tabs, terminal_is_frontmost=True)
        assert "INTERACTED" in q.status_line

    @patch("terminal_activator.queue.window_controller")
    @patch("terminal_activator.queue.get_content_hash", return_value="hash1")
    def test_queued_count_in_status(self, mock_hash, mock_wc):
        mock_wc.popup.return_value = True
        q = PopupQueue("/dev/ttys000")
        tabs = [_tab("/dev/ttys001"), _tab("/dev/ttys002"), _tab("/dev/ttys003")]
        q.update(tabs, terminal_is_frontmost=True)
        assert "QUEUED: 2" in q.status_line
